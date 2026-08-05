# Design: Band ladder curated (A1+A2) + books attach content

**Date:** 2026-07-30  
**Status:** Accepted  
**Implementation plan:** `docs/superpowers/plans/2026-07-30-band-ladder-book-attach.md`  
**Note:** Catalog seed + attach-only sync shipped. Assembler coverage filter commits with theme-unit work (mixed file). Run migration `o4p5q6r7s8t9` + `python -m app.seeds.cefr_ladder_a1_a2` on live DB before using attach.  
**Depends on:** Skill graph + ZPD roadmap (`2026-07-20-skill-graph-zpd-roadmap-design.md`), adaptive roadmap (`2026-07-24-adaptive-roadmap-design.md`), level-challenge onboarding  
**Supersedes (behavior):** LLM/rule sync that **creates** skills from book units as the primary way to grow the graph  
**Keeps:** `learning_skills`, `skill_edges`, `book_skill_sources`, `user_skill_mastery`, ZPD assemble, quiz/lesson from primary source  

---

## 1. Problem

Hướng hiện tại: admin upload sách `ready` → `sync_skill_graph` → LLM/rule **tạo** skill (+ edges/difficulty) từ unit.

Hệ quả khi mới có 1 sách/level:

- Gần như **1 unit = 1 skill** → sync ít giá trị merge
- Lộ trình phụ thuộc TOC sách, không phải khung nâng band chuẩn
- Thêm sách mới dễ phình / lệch catalog

Mục tiêu product: **nhiều sách tiếng Anh là nguồn nội dung**; roadmap user là **lát cắt trên ladder CEFR** để nâng band (A1 → A2 → …).

---

## 2. Goals / Non-goals

### Goals

- Seed sẵn **catalog skill A1 + A2** (khung cố định) + prerequisite + `difficulty_in_level`
- Đổi sync sách thành **attach-only**: map unit → skill đã có; ghi `book_skill_sources`
- Assemble roadmap chỉ từ skill **cùng `current_level`**, có source hợp lệ (coverage), ZPD + mastery như hiện tại
- Xong band hiện tại → level-challenge → `current_level` mới → assemble roadmap mới (không một path A1→C1)
- Admin (hoặc seed) là nơi thêm skill catalog; sách/AI **không** tự tạo skill mặc định

### Non-goals

- Seed B1–C1 trong MVP này
- Đổi placement / TOEIC flow
- Exam-prep loop B1–C1 (luyện đề → gap) — follow-up riêng
- Neo4j / graph DB
- Bắt buộc admin UI đầy đủ CRUD skill trong MVP (seed script đủ; admin CRUD optional phase 2)
- Copy nguyên văn CEFR/GSE descriptors vào product content (chỉ dùng làm tham chiếu khi soạn catalog)

---

## 3. Decisions (locked)

| Chủ đề | Quyết định |
|--------|------------|
| Chiến lược | **Band ladder curated** + books fill content |
| MVP seed | **A1 + A2** (script seed, không chờ admin dựng tay) |
| Tạo skill mới từ sách | **Cấm mặc định**; unit unmapped → `unmapped` / exclude, không INSERT skill |
| Thêm skill catalog | Seed script (chính) + admin CRUD sau (optional) |
| Nguồn soạn catalog | Cambridge English Grammar Profile (cấu trúc) + CEFR/GSE can-do (tham chiếu outcome); đối chiếu TOC sách uy tín |
| Roadmap user | Một “mùa” trong `current_level`; nâng band qua challenge rồi assemble lại |
| Assemble coverage | Chỉ skill có ≥1 `book_skill_sources` với `is_excluded = false` |
| Edges / difficulty | Thuộc catalog seed; sync sách **không** rewrite toàn graph |
| LLM lúc attach | Chỉ chọn `skill_id` / slug **trong catalog level**; Suggest exclude Review/Test |

---

## 4. Concept

```text
Seed (A1+A2 catalog)          Books (admin upload)
        │                              │
        ▼                              ▼
 learning_skills + edges      attach: unit → skill_id
        │                              │
        └────────────┬─────────────────┘
                     ▼
              book_skill_sources
                     ▼
         assemble ZPD roadmap @ current_level
                     ▼
         (optional) level-challenge → next CEFR
```

- **Seed** = dựng sẵn “kệ” A1 và A2 trong DB  
- **Attach** = AI/rule xếp hàng (unit sách) lên đúng ô  
- **Roadmap** = user lấy vài ô còn yếu trên tầng đang đứng  

---

## 5. Data model

### Giữ bảng hiện có

- `learning_skills` `(slug, cefr_level)` unique  
- `skill_edges` prerequisite  
- `book_skill_sources`  
- `user_skill_mastery`  

### Thêm (tối thiểu)

Trên `learning_skills` (hoặc bảng meta nếu muốn tách):

| Field | Ý nghĩa |
|-------|---------|
| `origin` | `catalog` \| `legacy` (skill cũ từ sync sách) |
| `can_do` (optional Text/nullable) | 1 câu outcome EN ngắn — prompt quiz/lesson |

MVP có thể chỉ dùng `origin`; `can_do` nếu đã có chỗ inject descriptor.

### Catalog size (hướng dẫn, không hard-lock số)

- A1: ~20–30 active skills (grammar-heavy + vài vocab/function)  
- A2: ~20–30 active skills  
- Mỗi level: edges prereq hợp lý (không chỉ linear 1→2→3… nếu tránh được)  
- `difficulty_in_level` 1–10 phân bố để ZPD + `placement_score` vẫn dùng được  

Danh sách slug cụ thể nằm trong seed file / plan implementation — spec này chốt **nguồn + quy mô**, không chốt từng dòng grammar.

---

## 6. Pipeline thay đổi

### 6.1 Seed

- `backend/app/seeds/cefr_ladder_a1_a2.py` (tên cuối cùng theo convention repo)  
- Idempotent upsert theo `(slug, cefr_level)`  
- Upsert edges catalog  
- Đánh `origin=catalog`, `is_active=true`  

### 6.2 Attach book (thay hành vi sync chính)

Đổi `sync_skill_graph` (hoặc wrapper `attach_book_to_ladder`):

1. Load book `ready` + units  
2. Load **catalog skills** cùng `book.cefr_level` (`origin=catalog` hoặc mọi active nếu chưa backfill)  
3. Rule exclude Review/Test/…  
4. LLM: với mỗi unit → `{ unit_index, skill_slug | null, exclude, confidence }` chỉ từ catalog  
5. Fallback rule: `normalize_unit_to_slug` **chỉ match** nếu slug đã có trong catalog; không match → unmapped  
6. Ghi/cập nhật `book_skill_sources`; **không** `_get_or_create_skill` cho slug lạ  
7. Recompute `is_primary`  
8. Return summary: mapped / unmapped / excluded counts  

### 6.3 Assemble

- Giữ `select_skills_for_roadmap` + ZPD  
- Filter thêm: skill phải có coverage (source không excluded)  
- Nếu sau filter không đủ bước: trả lỗi rõ (“Not enough covered skills…”) hoặc path ngắn hơn — **chọn: cho phép path ngắn hơn `max_steps` nếu hết eligible** (đã gần behavior hiện tại khi pool cạn)

### 6.4 Migration legacy

1. Chạy seed A1+A2  
2. Skill cũ không nằm catalog: `origin=legacy`, cân nhắc `is_active=false` sau khi admin/review (MVP: deactivate legacy cùng level nếu slug không trong seed, **hoặc** giữ active đến khi re-attach xong — **chốt: deactivate legacy không có trong seed list sau khi seed + optional rename-map table trong seed**)  
3. Re-run attach cho mọi book `ready` A1/A2  

Chi tiết rename-map (slug cũ → slug catalog) nằm trong seed nếu cần giữ `book_skill_sources` / mastery.

---

## 7. API / Admin

### MVP

- Giữ endpoint sync sách nhưng semantics = attach + response có `unmapped_units[]`  
- Seed chạy offline (CLI / `python -m …`) như scenarios seed  

### Phase 2 (optional)

- Admin CRUD skill catalog  
- UI coverage: skill thiếu sách / unit unmapped  
- Approve map trước khi commit  

---

## 8. Frontend

- Copy roadmap: nhấn mạnh level hiện tại và mục tiêu band kế (A1→A2), không “theo sách X”  
- Skill/source sách: secondary (nếu đã show)  
- Không bắt buộc UI mới cho seed  

---

## 9. Testing

- Seed idempotent: chạy 2 lần không nhân đôi skill  
- Attach: unit map đúng catalog; slug lạ không tạo skill  
- Attach: Review excluded  
- Assemble: skill không có source không vào path  
- User A1 hoàn thành challenge → A2 assemble dùng catalog A2 (khi đã cover)

---

## 10. Rollout phases

1. Migration `origin` (+ optional `can_do`)  
2. Seed A1+A2 + edges  
3. Đổi sync → attach-only  
4. Coverage filter assemble  
5. Legacy deactivate / remap + re-attach books  
6. (Optional) admin coverage UI  

---

## 11. Risks

| Risk | Mitigation |
|------|------------|
| Catalog lệch sách thật → nhiều unmapped | Đối chiếu TOC 1–2 sách A1/A2 khi soạn seed; admin xem `unmapped_units` |
| Catalog quá mỏng → assemble thiếu bước | ~20–30 skill/level; cho phép path ngắn |
| Bản quyền descriptor | Soạn slug/title gốc; không paste GSE/CEFR nguyên văn làm content bán |
| Mastery/skills cũ gãy | Remap table + giữ mastery theo skill_id mới nếu merge |

---

## 12. Success criteria

- [x] DB có catalog A1+A2 ổn định sau seed  
- [x] Upload/sync sách A1 không tăng số `learning_skills` catalog (chỉ tăng sources)  
- [ ] Roadmap user A1 chỉ chứa skill A1 có coverage — *deferred with assembler/theme-unit commit*  
- [ ] Sau promote A2, assemble được path A2 khi sách A2 đã attach — *same*  

---

## 13. Open for implementation plan (not blocking this spec)

- Danh sách slug A1/A2 cụ thể (task trong plan, dựa Grammar Profile)  
- Có bắt buộc human-approve map trước commit hay auto-attach MVP  
- Có expose `GET /skills/coverage?level=A1` ngay phase 1 hay chỉ trong sync response  

**Default MVP:** auto-attach + unmapped trong sync response; coverage API phase 2.
