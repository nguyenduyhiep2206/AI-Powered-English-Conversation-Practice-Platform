# Thiết kế: Lộ trình Theme Unit + Lesson densify (Phương án D)

**Ngày:** 2026-08-03  
**Trạng thái:** Accepted
**Plan:** `docs/superpowers/plans/2026-08-03-theme-unit-path-densified-lessons.md`  
**Phụ thuộc:** Band ladder + book attach (`2026-07-30-band-ladder-book-attach-design.md`), skill graph ZPD (`2026-07-20-skill-graph-zpd-roadmap-design.md`), adaptive rolling horizon (`2026-07-24-adaptive-roadmap-design.md`), Learn + Practice bám skill (`2026-08-02-skill-aligned-learn-practice-design.md`)  
**Giữ nguyên (core, không đàm phán):** catalog skill CEFR; sách attach → `book_skill_sources`; assemble/replan từ skill graph + ZPD + mastery; nâng band qua level-challenge; nội dung English→English  

---

## 1. Vấn đề

Catalog A1/A2 (~20–30 skill/band) + một Learn mini-unit + Practice mỗi skill đang giống **checklist admin**, chưa giống app học tiếng:

1. **Mỗi skill quá mỏng** — Babbel/Duolingo ~5–15 phiên nhỏ/chủ đề; ta ~1.
2. **Không có can-do theo tình huống** — learner thấy slug grammar (`past_simple_regular`), không thấy outcome (“Talk about yesterday”).
3. **Claim band lệch depth** — xong ~22 skill A2 ≠ CEFR A2; copy/path gợi ý tiến band khi chưa đủ sâu và chưa có lối thoát trung thực.
4. **Chỉ đi tới** — thiếu kiểu Grammar Review / luyện lại skill yếu như Busuu.

Cần cảm giác product **mà không bỏ** khác biệt: nhiều sách nuôi một ladder CEFR + assemble thích nghi theo skill.

---

## 2. Mục tiêu / Không làm

### Mục tiêu

- **Lộ trình learner** đọc theo Theme **Unit** (can-do) + Learn/Practice dày bên trong, không phải list skill phẳng.
- **Densify** mỗi skill thành chuỗi bài ngắn (MVP: 3 micro-lesson + Practice Practice; L4 tùy chọn sau) trước khi complete week.
- Giữ **skill graph + book attach + ZPD assemble** làm engine lập path; Theme Unit chỉ là **lớp gom nhóm có biên tập** trên catalog.
- **Copy band trung thực:** path = “nền tảng A2”; chỉ gợi ý promote sau **exit challenge**, không viết “bạn đã đạt CEFR A2”.
- **Review** nhẹ cho skill yếu/gần đây (phase 4 trong chương trình này).

### Không làm (chương trình này)

- Gamification kiểu Duolingo (streak/XP/league) làm trục chính
- Thay assemble bằng TOC cố định một cuốn sách
- Listening / speaking / phát âm (để sau)
- Engine spaced-repetition đầy đủ; chỉ review hub nhẹ ở phase 4
- Seed catalog B1–C1
- Claim tương đương chứng chỉ CEFR chính thức
- Regen toàn bộ lesson/quiz lịch sử trong một migration (ops regen theo skill/unit)

---

## 3. Quyết định (đã chốt)

| Chủ đề | Quyết định |
|--------|------------|
| Chiến lược | **D = Theme Unit (B) + densify lesson (A)** trên ladder skill hiện có |
| Nguồn lập path | Vẫn **`learning_skills` + edges + coverage + mastery + ZPD** |
| Theme Unit | Nhóm biên tập: `slug`, `cefr_level`, danh sách `skill_id` có thứ tự, `can_do` (EN), `title` |
| Ai định nghĩa Unit | **Seed/catalog** (cùng ownership với ladder), không suy từ TOC sách |
| Độ hạt assemble (MVP) | Assembler vẫn chọn **skill**; FE (và DTO API) **gom** step theo Theme Unit khi cùng unit |
| Cổng complete | Giữ nghĩa: mastery ≥ 0.7 trên quiz skill của week; densify = thêm Learn/Practice **trước** khi gate dễ đạt |
| Densify lesson | Một skill catalog → **LessonPack**: MVP **3** micro-lesson published + 1 checkpoint Practice (`skill_drill`); L4 sau |
| Hình micro-lesson | Mở rộng hợp đồng skill-aligned: hook tình huống → Notice → Form (grammar) → Meaning → Check → Write → Exit; pack chia sẻ targets, đổi trọng tâm từng L |
| Nâng band | Giữ **level-challenge**; gợi ý challenge khi hết skill eligible / path cạn ở level; copy không nói “CEFR certified” |
| Sách | Pipeline attach không đổi; gen densify vẫn neo primary `book_skill_sources` |
| Review hub | Phase 4: list skill yếu (mastery dưới 0.7 hoặc `updated_at` cũ) + deep-link Practice; không thuật toán SR mới trong MVP densify/unit |

---

## 4. Khái niệm

```text
Catalog skills + edges          Theme Units (seed)
        │                              │
        └──────────┬───────────────────┘
                   ▼
            Unit = skill có thứ tự + can_do
                   │
     Sách attach ──┘── book_skill_sources (không đổi)
                   ▼
         assemble ZPD skills (horizon) ──► gom theo Theme Unit trên UI
                   ▼
         mỗi skill: LessonPack (L1..Ln) → Practice checkpoint → cổng mastery
                   ▼
         path cạn / sẵn sàng → level-challenge → CEFR kế
```

**Khác biệt giữ lại:** sách đổ nội dung vào ladder; path cá nhân từ trạng thái graph — Theme Unit chỉ đổi **cách kể chuyện + độ dày nội dung**.

---

## 5. Mô hình Theme Unit

### 5.1 Dữ liệu

Bảng catalog mới (tên chốt trong plan), ví dụ `learning_theme_units`:

| Field | Ghi chú |
|-------|---------|
| `slug` | Ổn định, unique theo level, ví dụ `a2_talk_about_past` |
| `cefr_level` | A1 / A2 |
| `title` | Hiển thị EN |
| `can_do` | Một câu outcome EN |
| `sort_order` | Thứ tự sư phạm mặc định trong level |
| `is_active` | Ẩn mềm |

Bảng join `theme_unit_skills`:

| Field | Ghi chú |
|-------|---------|
| `theme_unit_id` | FK |
| `skill_id` | FK `learning_skills` |
| `position` | Thứ tự trong unit |
| Unique `(theme_unit_id, skill_id)` | MVP: mỗi skill thuộc **đúng một** Theme Unit |

Seed A1/A2 khoảng ~6–8 Unit mỗi level (minh họa; chốt membership trong plan từ slug hiện có), ví dụ A2:

- Building blocks & connectors  
- Talking about now vs ongoing  
- Talking about the past  
- Experience & recent past (present perfect)  
- Future plans & predictions  
- Advice & obligation  
- Describing & comparing  
- Opinions & travel vocab  

Membership là việc biên tập seed; **mọi** skill catalog active phải thuộc một unit (không orphan).

### 5.2 API / DTO

`GET /roadmap` (và response assemble) thêm field **additive** trên mỗi week/step:

- `theme_unit_slug`, `theme_unit_title`, `theme_unit_can_do`, `theme_unit_position` (vị trí skill trong unit)

Endpoint tổng hợp sau (không bắt buộc MVP): `GET /roadmap/units` — tiến độ theo unit. FE có thể gom từ list week + lịch sử completed.

### 5.3 Tương tác assemble

- **Không đổi** điều kiện `select_skills_for_roadmap` (level, coverage, prereq, ZPD, mastery).
- Rolling horizon giữ (1 in-progress + 2 locked) trừ khi ticket adaptive-roadmap khác đổi.
- Ưu tiên mềm (sau MVP): khi hòa, ưu tiên skill cùng Theme Unit với skill đang học — **không chặn** phase densify/unit UI.

---

## 6. LessonPack densify

### 6.1 Vấn đề một mini-unit

Hiện mỗi skill một JSON lesson. Product D cần **nhiều micro-lesson**/skill mà vẫn align Practice với targets.

### 6.2 Hình dạng

Mỗi skill catalog (ưu tiên grammar MVP):

| Bước | Vai trò | Trọng tâm nội dung |
|------|---------|-------------------|
| L1 | Tình huống + notice | Dialog/tình huống ngắn (~40–80 từ); targets nhẹ |
| L2 | Form + controlled | Bắt buộc `form` với grammar; 1–2 check |
| L3 | Meaning + use | Targets + writing có hướng dẫn |
| L4 (tùy chọn) | Contrast / recycle | So với form liên quan |
| Checkpoint | Practice | Batch `skill_drill` align union targets của pack; mastery như hiện tại |

**Số lượng MVP:** đúng **3** micro-lesson + **1** Practice checkpoint khi skill được densify. L4 để sau.

### 6.3 Lưu trữ (chốt trong plan; ưu tiên dưới)

**Ưu tiên:** thêm `skill_lessons.pack_index` (int, default 0) + unique `(skill_id, pack_index)`. `pack_index=0` tương thích ngược. Learner đi `0..n-1` rồi mở Practice.

**Phương án khác:** một JSON `content.pack = [...]` — ít hàng, khó publish/regen từng phần. Ưu tiên multi-row `pack_index`.

### 6.4 Gen / publish

- Admin: “generate LessonPack” tạo/cập nhật draft L1–L3 cùng skill + primary book source.
- Cổng publish: mỗi micro-lesson qua `normalize` / grammar⇒form; publish pack yêu cầu đủ index published (hoặc lệnh “publish pack”).
- Gen Practice: targets = union surface của mọi lesson pack published; `mode=skill_drill`, align ≥80%.
- Legacy: chỉ có `pack_index=0` vẫn chạy như hiện tại.

### 6.5 UX learner

Thẻ week / skill:

1. Learn · 1/3 → 2/3 → 3/3  
2. Practice (checkpoint)  
3. Complete khi mastery ≥ 0.7  

`can_skip` Learn: giữ luật cũ (đã complete lesson hoặc mastery ≥ 0.7); skip cả pack khi mastery mạnh vẫn OK.

---

## 7. Frontend roadmap

- **Trục chính:** section Theme Unit (title + can-do). Bên dưới: các bước skill (tiến độ densify).
- Không để slug thô làm nhãn hero; hiện **title** skill + can-do unit.
- Copy: “A2 foundation path” / “Hoàn thành skill trong unit để xây nền A2”; không “You’ve achieved CEFR A2” khi complete week.
- Khi không còn skill eligible ở level: CTA **Take level challenge** (API hiện có).

---

## 8. Review hub (phase 4)

- Hiện skill cùng level có mastery dưới 0.7 hoặc lâu chưa practice (`updated_at` đơn giản — không SRS đầy đủ).
- Deep-link Practice nếu có quiz published.
- Gợi ý Review node trong horizon locked — **ngoài** MVP densify/Theme Unit (phase 1–2).

---

## 9. Rollout theo phase

| Phase | Phạm vi | Tiêu chí thoát |
|-------|---------|----------------|
| **0** | Spec + plan | Doc này accepted; có plan triển khai |
| **1** | LessonPack densify (schema + gen + FE Learn chain) cho **một** skill pilot | Spot-check: 3 lesson + drill align cảm giác “có phiên học” |
| **2** | Seed Theme Unit A1/A2 + DTO roadmap + FE gom unit | Home đọc theo unit, không list week phẳng |
| **3** | Ops: regen LessonPack skill ưu tiên trên path A1 đã cover | Ít nhất một Theme Unit đầy đủ (≥3 skill) densify + publish trên live |
| **4** | Review hub nhẹ + copy thoát band | Practice skill yếu vào được từ home |

Không chặn Phase 1 vì chưa có bảng Theme Unit — densify đơn độc đã cải thiện cảm giác product.

---

## 10. Kiểm thử

- Seed: mọi skill A1/A2 active thuộc đúng một Theme Unit; seed idempotent.
- Assemble: vẫn chỉ skill eligible; DTO có metadata unit khi đã map.
- LessonPack: publish pack từ chối nếu thiếu index; learner tôn trọng `pack_index`.
- Alignment: checkpoint drill ≥80% token-align với union targets pack.
- Regression: skill chỉ `pack_index=0` complete week như cũ.
- Copy/FE: không “CEFR certified” khi complete.

---

## 11. Tiêu chí thành công

1. LessonPack skill pilot cảm giác khối học **10–20 phút**, rồi Practice.
2. Roadmap home hiện **Theme Unit + can-do** với seed A1/A2.
3. Invariant core giữ: attach-only catalog, ZPD assemble, mastery ≥ 0.7, level-challenge để promote.
4. Positioning UI rõ: foundation path + challenge tùy chọn — không trao CEFR chính thức.

---

## 12. Điểm mở (đã giải quyết)

| Câu hỏi | Kết luận |
|---------|----------|
| Bỏ sách→skill→graph? | **Không** — D là đóng gói + độ dày |
| Assembler chọn Unit thay skill? | **Không MVP** — chọn skill; gom Unit trên UI/DTO |
| Skill thuộc nhiều Unit? | **Không MVP** — đúng một Unit |
| Bao nhiêu micro-lesson? | **3 + Practice** MVP |
| SRS đầy đủ? | **Không** — phase 4 review nhẹ |
| Streak Duo? | **Ngoài phạm vi** |

---

## 13. Rủi ro

| Rủi ro | Giảm thiểu |
|--------|------------|
| Chi phí ops densify mọi skill | Phase theo path đã cover; legacy 1 lesson OK |
| Biên tập Theme Unit sai | Đối chiếu Grammar Profile + can-do; admin CRUD sau |
| User nhầm Unit = band CEFR | Copy + messaging level-challenge |
| Hòa assemble không giữ unit | Ưu tiên cùng-unit tùy chọn sau MVP |

---

## 14. Việc để sau (tường minh)

- Listening/speaking trong pack  
- Bias assemble mềm để xong Theme Unit đang học  
- Admin CRUD Theme Unit  
- Badge “foundation complete” (badge product ≠ claim CEFR)  
