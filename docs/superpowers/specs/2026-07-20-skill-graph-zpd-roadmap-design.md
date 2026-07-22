# Design: Skill graph chung + ZPD roadmap (có LLM)

**Date:** 2026-07-20  
**Status:** Implemented (backend MVP) — 2026-07-20  
**Shipped:** `difficulty_in_level` + LLM refine at book sync; ZPD assemble; `POST /roadmap/steps/{id}/complete`; `GET|POST /onboarding/level-challenge` (+1 CEFR). Smoke suite Tasks 2–7: 25 passed. Manual E2E checklist still recommended on a live env.  
**Depends on:** Placement từ quiz bank (`2026-07-15-placement-from-quiz-bank-design.md`), sync skills hiện tại (`skill_graph_service`, `book_skill_sources`, `skill_edges`)  
**Aligns with:** Approach **A** — một skill graph / CEFR level; cá nhân hóa bằng ZPD + mastery; sách chỉ là nguồn nội dung

---

## 1. Problem

Hệ thống đã có:

- Nhiều sách cùng `cefr_level` (ví dụ 5 sách A1)
- `learning_skills` canonical theo `(slug, cefr_level)`
- `book_skill_sources` map unit sách → skill
- `skill_edges` (prerequisite) — hiện chủ yếu **linear theo thứ tự unit một sách**
- `user_skill_mastery` + `POST /roadmap/assemble`
- Placement: `current_level` (A1…C1) + `placement_score` (0–10)

Còn thiếu để lộ trình **chặt**:

1. Graph **chung** trong một CEFR level (gộp trùng ý nghĩa giữa sách, không chỉ trùng slug rule-based)
2. Prerequisite **sư phạm** hơn “unit kế tiếp trong cùng sách”
3. Độ khó **trong** level (`difficulty_in_level` 1–10) để dùng `placement_score` như sub-level
4. Assembler tôn trọng **prereq + ZPD**, không chỉ “skill yếu sort mastery”

Hệ quả hôm nay: user A1 điểm 3/10 vẫn có thể bị xếp skill cuối A1; thêm sách dễ phình skill trùng nghĩa; lộ trình không đi theo “vùng vừa sức”.

---



## 2. Goals / Non-goals



### Goals

- Khi sync skill graph từ sách `ready`: **tự động** merge vào graph level đó (incremental, không rebuild toàn bộ)
- Dùng **LLM** để: canonical hóa skill, gộp gần nghĩa, gợi ý prerequisite + `difficulty_in_level`
- Rule-based vẫn chạy được khi LLM fail (fallback an toàn)
- `assemble_user_roadmap` chọn 8–12 skill trong **ZPD** dựa trên:
  - `profile.current_level`
  - `profile.placement_score` (sub-level trong CEFR)
  - mastery + `skill_edges` prerequisite
  - `difficulty_in_level`
  - optional boost `weak_point`
- Quiz / excerpt vẫn lấy từ `book_skill_sources` (`is_primary` ưu tiên) — không đổi contract quiz generation cốt lõi
- User cảm thấy level hiện tại **quá dễ / lệch trình độ** có thể **xin lên CEFR kế** qua challenge ngắn (không tự phong level)



### Non-goals

- Neo4j / graph DB riêng
- Bayesian Knowledge Tracing đầy đủ / IRT
- LLM gọi mỗi lần assemble roadmap hoặc mỗi request học
- Chọn “một sách chính” làm spine (Approach B) — đã loại
- Đổi bảng placement 0–10 → CEFR
- Auto-assemble ngay sau nộp placement (giữ quyết định spec 2026-07-15)
- Admin UI chỉnh từng edge bằng tay (có thể follow-up; MVP tin LLM + validate)
- Nhảy nhiều bậc CEFR một lần (A1→B1); free bump không quiz; retake full placement 10 câu (defer — có thể thêm sau)

---



## 3. Decisions (locked)


| Chủ đề               | Quyết định                                              |
| -------------------- | ------------------------------------------------------- |
| Chiến lược lộ trình  | **A** — skill graph chung / CEFR + ZPD theo sub-level   |
| Thêm sách cùng level | **Incremental merge** — không full rebuild mặc định     |
| Vai trò LLM          | **Hybrid** — rule nền + LLM refine khi sync graph       |
| Sub-level            | Dùng lại `placement_score` (0–10) trong `current_level` |
| Mastery gate         | Giữ `MASTERY_STRONG = 0.7`                              |
| Độ dài path          | Giữ 8–12 bước / lần assemble                            |
| LLM fail             | Fallback rule-based sync hiện tại; sách vẫn sync được   |
| Level quá dễ / nhảy CEFR | **Challenge promote +1** — quiz ngắn level đích; đạt mới đổi `current_level` |


---



## 4. Giải thích hướng làm (chi tiết)



### 4.1 Tư duy cốt lõi: sách ≠ lộ trình

**Sai:** User A1 → đọc Sách 1 hết → Sách 2 hết → …

**Đúng:** Hệ thống có **một bản đồ kỹ năng A1**. Mỗi unit trong mỗi sách là **lối vào** một ô trên bản đồ. User đi từ ô này sang ô kia theo prerequisite và độ khó vừa sức.

```text
┌─────────────┐   ┌─────────────┐   ┌─────────────┐
│  Sách Alpha │   │  Sách Beta  │   │ Sách Gamma  │
│ unit "be"   │   │ "I'm/you're"│   │ "Hello name"│
└──────┬──────┘   └──────┬──────┘   └──────┬──────┘
       │                 │                 │
       └────────────┬────┴────────────────┘
                    ▼
            skill: be_present   ← 1 node duy nhất
            difficulty: 2
```



### 4.2 Skill graph gồm những gì?


| Thành phần     | Ý nghĩa                                   | Bảng / field                                |
| -------------- | ----------------------------------------- | ------------------------------------------- |
| **Node**       | Một kỹ năng học được (grammar/vocab/…)    | `learning_skills`                           |
| **Edge**       | `from` phải vững trước `to`               | `skill_edges.relation = prerequisite`       |
| **Source**     | Unit sách cung cấp nội dung/quiz cho node | `book_skill_sources`                        |
| **Difficulty** | Vị trí trong level 1 (đầu) … 10 (cuối)    | `learning_skills.difficulty_in_level` (mới) |
| **Mastery**    | User đã vững node chưa (0…1)              | `user_skill_mastery`                        |


**Ví dụ A1 (rút gọn):**

```text
be_present (diff 2)
    → possessives_family (diff 3)
    → present_simple (diff 5)
         → can_cant (diff 7)
         → past_simple_basic (diff 9)
```



### 4.3 Sub-level và ZPD (vùng vừa sức)

Placement cho user: `current_level = A1`, `placement_score = 3`.

- `3` **không** có nghĩa “đã xong 30% cả A1 một cách tuyệt đối”, nhưng đủ dùng làm **điểm neo** trong thang 1–10 của level đó.
- **ZPD window** (MVP):  
`difficulty ∈ [sub, min(10, sub + window)]` với `window = 2`  
→ với score 3: chỉ skill difficulty **3, 4, 5** (và thỏa prereq).

Thêm điều kiện:

1. Mọi prerequisite có `mastery ≥ 0.7` (hoặc không có prereq)
2. Chính skill đó `mastery < 0.7`
3. `is_active = true`, cùng `cefr_level`

→ User 3/10 **không** bị đẩy vào `past_simple_basic` (diff 9) ngay từ đầu.

### 4.4 Vì sao cần LLM (và giới hạn của LLM)

Rule-based hiện tại (`normalize_unit_to_slug` + alias) **dễ miss**:


| Unit title sách A | Unit title sách B | Rule thường ra | Mong muốn                |
| ----------------- | ----------------- | -------------- | ------------------------ |
| Present simple    | Daily routines    | 2 slug khác    | 1 skill `present_simple` |
| Verb to be        | I'm / you're      | 2 slug         | `be_present`             |
| Can you…?         | Abilities         | 2 slug         | `can_cant`               |


LLM (một lần khi **sync graph sách**) giúp:

1. Map unit → **canonical** `{slug, title, skill_type}`
2. Ưu tiên **reuse** skill đã có cùng CEFR nếu cùng ý
3. Gợi ý **prerequisite** (không chỉ “unit kế tiếp”)
4. Gợi ý **difficulty_in_level** 1–10

LLM **không** dùng để:

- Quyết định tuần học của từng user mỗi request
- Đọc lại toàn bộ PDF mỗi lần assemble
- Xóa/rebuild cả graph level mỗi khi thêm sách



### 4.5 Incremental merge khi thêm sách (không rebuild)

Khi thêm sách A1 thứ 5:

```text
units mới
  → LLM (+ rule) map → skill ids
  → skill mới: INSERT node
  → skill trùng: chỉ thêm book_skill_sources
  → edges: UNION (thêm cạnh mới nếu chưa có)
  → difficulty: cập nhật lại cho skill bị ảnh hưởng
      (ưu tiên median các gợi ý LLM / rule từ mọi source)
  → is_primary: recompute trong nhóm source của skill đó
```

**Không** xóa toàn bộ `learning_skills` / `skill_edges` của A1.

Full rebuild chỉ là thao tác bảo trì (đổi thuật toán, migration) — ngoài happy path.

### 4.6 Lắp lộ trình từ graph

```text
load skills(level=A1) + edges + mastery + placement_score
  → candidates = ZPD filter
  → sort: difficulty ASC, mastery ASC, boost weak_point
  → take 8–12
  → tạo roadmap_steps + unlock tuần trước
  → quiz sau này lấy primary source của skill
```

Re-assemble (user gọi lại API): tính lại ZPD với mastery mới → path tiến sâu hơn trong A1.

### 4.7 User thấy A1 quá dễ — muốn lên A2 ngay

ZPD chỉ điều chỉnh **trong** một CEFR. Khi user **lệch cả level** (A1 quá dễ), không đủ chỉ nới `placement_score`.

**Quyết định:** promote có kiểm chứng, **chỉ +1 bậc** (A1→A2, A2→B1, …; không A1→B1 một phát).

```text
User: "Level này quá dễ" / xin lên A2
  → GET challenge: N câu published thuộc skill CEFR = level đích (A2)
  → User nộp bài
  → Đạt ngưỡng → current_level = A2
       placement_score = map từ điểm challenge (neo ZPD trong A2, thường thấp–trung)
       xóa roadmap cũ (cùng cơ chế clear khi assemble)
       (không bắt buộc auto-assemble — user gọi assemble như sau placement)
  → Trượt → giữ A1; có thể gợi ý re-assemble cửa sổ cao hơn trong A1
```

| Tham số MVP | Giá trị |
|-------------|---------|
| Bậc nhảy | Đúng **một** level trên `CEFR_ORDER` |
| Số câu challenge | **6** (published, skill `cefr_level` = đích) |
| Ngưỡng đậu | **≥ 4/6** (~67%) |
| `placement_score` sau đậu | `max(1, min(10, round(correct/6 * 10)))` — neo ZPD level mới |
| LLM | Không |
| Cooldown / rate limit | Optional: tối đa 1 challenge thành công / level / ngày — defer nếu chưa cần |

**Không làm MVP:** đổi `current_level` chỉ vì user chọn dropdown; assemble `level=A2` mà profile vẫn A1 như “cách chính thức” (tránh dual source of truth).

**Trước khi challenge:** UI/API có thể gợi ý “thử skill khó hơn trong A1” (re-assemble) — không chặn challenge nếu user vẫn muốn lên A2.

---



## 5. User / admin flows



### 5.1 Admin — thêm sách vào graph

```text
Upload → detect structure → sách ready + cefr_level
  → Sync skill graph (API / job hiện có, mở rộng)
       1) rule normalize
       2) LLM refine (batch JSON)
       3) validate + ghi DB (incremental)
  → (giữ nguyên) generate quiz / publish
```

Nếu LLM timeout/error: log warning, **vẫn** commit sync rule-based; đánh dấu metadata (optional) `llm_refined=false` để admin biết.

### 5.2 Learner — sau placement

```text
placement xong: current_level=A1, placement_score=3, mastery đã seed
  → User gọi POST /roadmap/assemble (như hiện tại — không đổi contract ngoài hành vi chọn skill)
  → Nhận 8–12 week trong ZPD
  → Học quiz → mastery tăng → hoàn thành week → unlock
  → (sau) assemble lại khi cần path mới sâu hơn
```

### 5.3 Learner — level quá dễ (challenge promote)

```text
onboarding_complete && muốn lên CEFR kế
  → GET /api/v1/onboarding/level-challenge   (hoặc /profile/level-challenge)
       ?target_level=A2  (optional; default = next(current_level))
  → 6 câu published @ A2 (không lộ answer)
  → POST .../level-challenge { target_level, answers[] }
  → Pass: current_level=A2, placement_score cập nhật, roadmap cũ cleared
  → Fail: 200 với passed=false; profile không đổi
  → User tự assemble lại ở level mới khi sẵn sàng
```

Prerequisite vận hành: đủ ≥6 câu published cho level đích (khác message thiếu bank placement 10 câu A1–C1).

---



## 6. Architecture

```text
                    ┌──────────────────────┐
  Book ready        │ skill_graph_service  │
  structure units ─►│  sync_skills_from_…  │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
     skill_normalize    skill_graph_llm     validate /
     (rule + alias)     (map/merge/edge/    upsert DB
                         difficulty)        edges+sources
                               │
                               ▼
                    learning_skills
                    skill_edges
                    book_skill_sources
                               │
                               ▼
                    roadmap_assembler_service
                    (ZPD + prereq + mastery)
                               │
                               ▼
                    roadmap_steps / user_progress
```


| Unit                                  | Responsibility                                                 |
| ------------------------------------- | -------------------------------------------------------------- |
| `skill_normalize_service`             | Rule clean title + alias slug (fallback + input gợi ý cho LLM) |
| `skill_graph_llm_service` (mới)       | Một call/batch: canonical map, prereqs, difficulty             |
| `skill_graph_service`                 | Orchestrate sync incremental; validate; primary source         |
| `roadmap_assembler_service`           | Đổi `select_skills_for_roadmap` → ZPD + prereq                 |
| `roadmap_progress_service` (mới)      | Complete week khi mastery ≥ 0.7; unlock week sau               |
| `level_challenge_service` (mới)       | Challenge 6 câu → promote +1 CEFR                              |
| `learning_skills.difficulty_in_level` | Cột mới SmallInt 1–10 nullable→backfill                        |


---



## 7. Data model



### 7.1 `learning_skills` — thêm cột


| Column                | Type                                    | Notes                                           |
| --------------------- | --------------------------------------- | ----------------------------------------------- |
| `difficulty_in_level` | `SMALLINT` NULL → NOT NULL sau backfill | 1–10; check constraint hoặc clamp trong service |


Migration: thêm nullable, backfill bằng rule (normalized `unit_index`), default 5 nếu không có source.

### 7.2 Giữ nguyên

- `skill_edges(from_skill_id, to_skill_id, relation='prerequisite')`
- `book_skill_sources` + `is_primary` / `is_excluded`
- `user_profiles.placement_score`, `current_level`
- `user_skill_mastery`



### 7.3 Optional (MVP có thể bỏ)

- `books.skill_graph_llm_at` / flag trên sync response: biết sách đã LLM refine chưa  
- Bảng `skill_graph_llm_runs` audit — **defer** trừ khi cần debug mạnh

---



## 8. LLM contract (sync-time)



### 8.1 Input (tóm tắt)

```json
{
  "cefr_level": "A1",
  "book_title": "…",
  "existing_skills": [
    {"slug": "be_present", "title": "Verb be (present)", "difficulty_in_level": 2}
  ],
  "units": [
    {"unit_index": 0, "title": "Hello! What's your name?", "rule_slug": "hello_whats_your_name"}
  ]
}
```

`existing_skills`: chỉ skill **cùng CEFR** đang active (có thể truncate top-N theo liên quan / toàn bộ nếu A1 còn nhỏ).

### 8.2 Output (schema chặt)

```json
{
  "unit_mappings": [
    {
      "unit_index": 0,
      "slug": "be_present",
      "title": "Verb be (present)",
      "skill_type": "grammar",
      "difficulty_in_level": 2,
      "exclude": false
    }
  ],
  "prerequisites": [
    {"from_slug": "be_present", "to_slug": "present_simple"}
  ]
}
```



### 8.3 Validation (bắt buộc)

- `slug`: `[a-z0-9_]{2,120}`
- `difficulty_in_level`: integer 1–10
- `skill_type`: enum hiện có
- Mỗi `unit_index` map đúng một lần
- `prerequisites`: cả `from`/`to` phải xuất hiện trong mapping **hoặc** `existing_skills`
- Từ chối self-edge; detect cycle đơn giản trên subgraph mới → bỏ cạnh gây cycle
- `exclude: true` → `is_excluded` (vẫn có thể tạo source nhưng không vào path / edge active)



### 8.4 Fallback

- LLM lỗi / JSON invalid / validation fail hàng loạt → dùng pipeline rule hiện tại (`normalize_unit_to_slug` + `build_linear_edges`)
- Difficulty fallback:  
`1 + round(9 * unit_index / max(1, n_units-1))` rồi khi nhiều source: **median** theo skill



### 8.5 Chi phí & tần suất

- **1 batch LLM / lần sync một sách** (không per-unit call)
- Không gọi LLM trong `assemble_user_roadmap`

---



## 9. Thuật toán assemble (ZPD)

Pseudo:

```text
sub = profile.placement_score ?? 1   # clamp 0..10; nếu 0 coi như 1
window = 2
lo, hi = max(1, sub), min(10, sub + window)

skills = active skills where cefr == profile.current_level
mastery[skill] = map or DEFAULT_PRIOR
prereqs = edges where relation == prerequisite  # from → to means from before to

function prereqs_met(skill):
  for each from_id where edge from→skill:
    if mastery[from_id] < MASTERY_STRONG: return false
  return true

candidates = [
  s for s in skills
  if s.difficulty_in_level in [lo, hi]
  and mastery[s] < MASTERY_STRONG
  and prereqs_met(s)
  and not excluded-only  # skill chỉ còn source excluded → bỏ
]

sort candidates by:
  (0 if skill_type == weak_point else 1,
   difficulty_in_level ASC,
   mastery ASC,
   id ASC)

return first max_steps (8..12)
```

**Edge case:** không đủ candidate trong window → nới `hi` dần (+1) tối đa đến 10, vẫn chỉ lấy skill `prereqs_met` và `mastery < STRONG` (tránh roadmap rỗng). Log/metric khi phải nới.

**Edge case:** skill thiếu `difficulty_in_level` → treat as 5 tạm thời + queue backfill.

---



## 10. Ví dụ end-to-end

**Cho trước:** 3 sách A1 đã sync; graph có `be_present(2)`, `possessives(3)`, `present_simple(5)`, `can_cant(7)`, `past_simple(9)`.

**User:** A1, `placement_score=3`, `be_present.mastery=0.75`, còn lại thấp.

**ZPD 3..5:** `possessives`, `present_simple` (nếu prereq `be` đạt).

**Assemble:** Week1 possessives → Week2 present_simple → … (không có can/past).

**Thêm sách 4** có unit “Can you swim?”:

- LLM map → `can_cant` (reuse), difficulty 7, prereq từ `present_simple`
- Graph thêm source; **không** đưa vào path user cho đến khi re-assemble và window/mastery cho phép

---



## 11. API / product impact


| API                      | Đổi gì?                                                  |
| ------------------------ | -------------------------------------------------------- |
| Sync skill graph (admin) | Behavior + optional response fields (`llm_used`, counts) |
| `POST /roadmap/assemble` | Cùng URL; **logic chọn skill** đổi sang ZPD              |
| Placement                | Không đổi (vẫn one-shot onboarding)                      |
| Level challenge (mới)    | GET câu + POST nộp → có thể promote +1 CEFR              |
| Quiz generate/answer     | Không đổi contract; hưởng graph sạch hơn                 |


FE: có thể hiển thị `difficulty_in_level` / giải thích “phù hợp mức placement X” — optional MVP.

---



## 12. Testing

- Unit: validate LLM JSON (slug, cycle drop, difficulty clamp)
- Unit: ZPD select với fixture graph + mastery + score 3 → không lấy diff 9
- Unit: incremental — sync sách 2 không xóa edge sách 1; gộp cùng slug
- Unit: LLM raise → fallback rule vẫn tạo sources
- Unit: `next_cefr_level` / challenge score → placement; pass/fail threshold 4/6
- Integration: assemble 8–12 steps, unlock week 1 in_progress; challenge A2 cập nhật profile

---



## 13. Implementation outline (không phải plan chi tiết)

1. Migration `difficulty_in_level` + backfill rule
2. `skill_graph_llm_service` + prompt/schema
3. Mở rộng `sync_skills_from_preview` (LLM → validate → merge)
4. Đổi `select_skills_for_roadmap` / `assemble_user_roadmap`  
5. Complete week + unlock  
6. Level-challenge promote +1 CEFR  
7. Tests + cập nhật docs ngắn nếu có Functional Spec roadmap section  

Plan: `docs/superpowers/plans/2026-07-20-skill-graph-zpd-roadmap.md`.

---



## 14. Risks & mitigations


| Risk                            | Mitigation                                                                       |
| ------------------------------- | -------------------------------------------------------------------------------- |
| LLM gộp sai hai skill khác nhau | Ưu tiên reuse `existing_skills`; admin có thể re-sync; alias rule vẫn chạy trước |
| Edge cycle / loạn               | Validate + drop cạnh xấu; giữ union, không xóa cạnh cũ hàng loạt                 |
| Roadmap rỗng (window hẹp)       | Nới window có kiểm soát                                                          |
| Chi phí LLM                     | 1 call/sync sách; cache không bắt buộc MVP                                       |
| Difficulty lệch giữa sách       | Median / recompute khi thêm source                                               |


---



## 15. Open questions (không chặn MVP)

1. Re-assemble tự động sau N week hoàn thành vs chỉ manual? → mặc định **manual** (giữ API hiện tại)
2. `placement_score = 0`: clamp thành 1 hay band riêng “absolute beginner”? → MVP **clamp 1**
3. Có cần admin diff UI xem LLM mapping trước khi commit? → **defer**; sync commit ngay + fallback
4. Challenge fail có tăng `placement_score` trong level cũ không? → MVP **không** (chỉ message)
5. Retake full placement thay challenge? → **defer**; challenge +1 đủ cho “A1 quá dễ”

---



## 16. Self-review checklist

- [x] Không còn placeholder TBD cho quyết định đã lock (A, incremental, hybrid LLM)
- [x] Không mâu thuẫn spec placement (assemble vẫn tách khỏi submit placement)
- [x] Scope: graph sync + assemble ZPD; không kéo Neo4j / BKT
- [x] Giải thích hướng làm đủ để implementer hiểu “vì sao” (§4) và “làm gì” (§8–9)