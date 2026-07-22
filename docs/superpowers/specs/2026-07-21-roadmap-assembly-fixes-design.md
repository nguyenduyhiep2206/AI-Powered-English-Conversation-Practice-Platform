# Design: Sửa 2 lỗi chặn `assemble_user_roadmap`

**Date:** 2026-07-21
**Status:** Implemented — 2026-07-21
**Scope:** `backend/app/services/roadmap_assembler_service.py`, `backend/app/seeds/scenarios.py`, tests
**Depends on:** `2026-07-20-skill-graph-zpd-roadmap-design.md` (ZPD assemble MVP)

---

## 1. Problem

Tạo roadmap (`POST /api/v1/roadmap/assemble` → `assemble_user_roadmap`) thất bại với **2 `ValueError`** khác nhau, chặn toàn bộ luồng "Create my path":

1. `"No weak skills left to assemble the roadmap at this level."`
   — do `select_skills_for_roadmap` trả về rỗng.
2. `"No scenarios yet — seed scenarios before assembling the roadmap."`
   — do `pick_scenario` không tìm được scenario active nào.

Cả hai reproduce với user thật: `user_id=1`, `current_level=A1`, `placement_score=3`, `weak_point=vocabulary`, `goal=daily_conversation`.

---

## 2. Root cause (có bằng chứng từ DB)

### 2.1 Raise #1 — selection rỗng

Dữ liệu A1 thực tế: 10 skill `id 48…57`, `difficulty_in_level = 1…10` (mỗi độ khó 1 skill), tạo thành **chuỗi prerequisite tuyến tính**:

```
48(diff1) → 49(diff2) → 50(diff3) → … → 57(diff10)
```

`user_skill_mastery` của user 1: 5 dòng, **0 dòng ≥ 0.7** (`MASTERY_STRONG`).

Thuật toán cũ (`select_skills_for_roadmap`):

- Lọc prereq **cứng** theo mastery hiện tại (`_prereqs_met`): mọi skill có prereq chưa master đều bị loại ⇒ chỉ còn **skill gốc 48** (diff 1).
- Cửa sổ độ khó `[lo, hi]` với `lo = placement_score = 3`; vòng widen **chỉ tăng `hi`** lên 10, **không hạ `lo`**.
- Skill 48 (diff 1) `< lo=3` ⇒ bị loại vĩnh viễn ⇒ danh sách rỗng ⇒ raise.

Tức là 2 lỗi con cộng hưởng: **(a)** prereq lọc cứng làm sụp chuỗi về 1 skill gốc, **(b)** biên dưới cửa sổ độ khó loại luôn skill gốc đó.

### 2.2 Raise #2 — không có scenario

Bảng `scenarios` **rỗng hoàn toàn** (0 dòng). `pick_scenario` thử: category theo goal → theo level → bất kỳ active, đều `None` ⇒ raise. Đây là **thiếu seed data**, không phải bug logic. `learning_skills` đã có 47 dòng nhưng `scenarios` chưa từng được seed (theo spec, scenarios là content admin CRUD).

---

## 3. Decision

Hướng xử lý raise #1 được chốt với user: **sequential-aware selection** (thay vì chỉ nới cửa sổ độ khó).

Lý do: cấu trúc roadmap (`unlock_condition = complete_week_{n-1}`, status `locked`/`in_progress`) cho thấy path là **chuỗi tuần tự dựng sẵn**. Vậy skill 49 nên là "Week 2 (locked)" chứ không nên bị loại chỉ vì skill 48 chưa được master — prereq định **thứ tự**, không phải điều kiện eligibility tại thời điểm assemble.

Các phương án đã cân nhắc & loại:
- *Minimal (nới cửa sổ 2 chiều)*: unblock nhưng chuỗi tuyến tính vẫn chỉ ra 1 week.
- *Sửa seed data (nới chuỗi prereq)*: không làm thuật toán robust; dữ liệu khác vẫn có thể vỡ.

---

## 4. Changes

### 4.1 `select_skills_for_roadmap` — viết lại theo sequential-aware

Ngữ nghĩa mới:

- **Placement = floor:** skill có `difficulty_in_level < placement_score` được coi là **đã biết** (không dạy lại) và thỏa prereq. → ZPD quyết định **điểm bắt đầu**.
- **Known ban đầu** = skill mastery ≥ `MASTERY_STRONG` **hoặc** dưới floor.
- **Prereq thỏa** khi tất cả prereq nằm trong `known` (đã master/known **hoặc** đã được chọn ở week trước) → chuỗi prereq **trải thành các tuần liên tiếp**.
- **Dựng greedy:** lặp chọn skill eligible có `order_key` nhỏ nhất `(difficulty, weak_point_match, mastery, id)`, thêm vào path + `known`, tới khi đủ `max_steps` hoặc hết eligible (deadlock/cycle → dừng an toàn).

Gỡ bỏ: helper `_prereqs_met` (lọc cứng, không còn dùng) và hằng `ZPD_WINDOW` + tham số `window` (không còn dùng ceiling).

Ví dụ (user 1, A1, placement 3): floor=3 ⇒ 48/49 coi như known; path = `50→51→…→57` = **8 tuần** (diff 3→10).

### 4.2 Seed scenarios

Thêm seed idempotent `backend/app/seeds/scenarios.py`:

- Mỗi CEFR level (A1–C1) × 4 category mà `GOAL_TO_CATEGORY` map tới (`small_talk`, `job_interview`, `travel`, `custom`) = **20 scenario**; `goal_prompt` điều chỉnh theo tone từng level.
- Upsert theo `slug` (`ON CONFLICT (slug) DO UPDATE`) ⇒ chạy lại an toàn.
- Chạy: `python -m app.seeds.scenarios` (đã chạy trong container `api`).

Đảm bảo mọi goal của learner đều có category match tại level của họ; fallback trong `pick_scenario` vẫn còn tác dụng.

> Ghi chú: đây là **baseline content** để unblock. Muốn nội dung phong phú/đúng giáo trình hơn thì mở rộng `_TEMPLATES` rồi chạy lại (upsert cập nhật).

---

## 5. Behavior changes & test impact

Ngữ nghĩa selection đổi ⇒ 2 test cũ (mã hoá hành vi lọc-cứng) được cập nhật, thêm 1 regression:

| Test | Trước | Sau |
|------|-------|-----|
| `test_prereq_chain_unfolds_into_later_weeks` (đổi từ `test_zpd_score_3_khong_lay_diff_9`) | diff-9 bị loại (prereq chưa master) | diff-9 vào path như week sau khi prereq đã ở week trước → `ids == [2,3,4]` |
| `test_prereq_becomes_earlier_week_instead_of_dropped` (đổi từ `test_prereq_chua_dat_thi_bo`) | dependent bị loại | prereq thành week trước → `ids == [1,2]` |
| `test_linear_chain_builds_sequential_path` (mới) | — | chuỗi tuyến tính không sụp về 1 week; start ở floor → `ids == [3,4,5,6]` |
| `test_max_steps_van_ton_trong`, `test_bo_qua_skill_da_manh` | pass | vẫn pass (không đổi) |

---

## 6. Verification

- Unit: `test_roadmap_assembler_service` + `test_roadmap_query_service` + `test_roadmap_progress_service` = **7 passed**.
- Read-only trên DB thật (user 1): `select_skills_for_roadmap` trả **8 skill** (trước là 0), thứ tự diff 3→10.
- DB sau seed: **20 scenario active** phủ đủ 5 level × 4 category; user 1 (goal→`small_talk`, A1) có `small_talk-a1`.
- Lint: sạch cho các file đã sửa.

---

## 7. Files touched

- `backend/app/services/roadmap_assembler_service.py` — rewrite `select_skills_for_roadmap`; gỡ `_prereqs_met`, `ZPD_WINDOW`.
- `backend/app/seeds/__init__.py`, `backend/app/seeds/scenarios.py` — seed scenarios idempotent (mới).
- `backend/tests/test_roadmap_assembler_service.py` — cập nhật 2 test + thêm 1 regression.

---

## 8. Follow-ups (out of scope)

- Nội dung scenario chất lượng hơn (LLM-generate hoặc admin CRUD) thay baseline.
- Cân nhắc gắn **scenario khác nhau theo từng week/skill** thay vì 1 scenario/level cho cả path.
- Xử lý dữ liệu prereq có **cycle** rõ ràng hơn (hiện dừng an toàn nhưng im lặng).
