# Thiết kế: Placement adaptive (Busuu-lite)

**Ngày:** 2026-07-23  
**Trạng thái:** Implemented  
**Thay thế / mở rộng:** `docs/superpowers/specs/2026-07-15-placement-from-quiz-bank-design.md` (placement cố định 10 câu)  
**Phụ thuộc:** Bank `quiz_questions` published + `learning_skills`; survey → profile (`weak_point`, `goal`)  
**Bám theo:** Pattern industry (Busuu CAT-lite + Duolingo seed mastery); onboarding EnglishFlow: survey → placement → roadmap

---

## 1. Vấn đề

Placement MVP (`2026-07-15`) đã chạy end-to-end nhưng là form **cố định 10 câu**:

- Mọi học viên đều gặp câu A1–C1 bất kể trình độ (beginner gặp C1; advanced lãng phí thời gian với A1).
- Điểm = số câu đúng (0–10) vừa map CEFR vừa làm floor `placement_score` cho roadmap — **một số mang hai nghĩa**.
- Không khóa attempt: submit chỉ cần 10 `question_id` published, không bắt buộc đúng bộ đề đã được phục vụ.
- Không cho làm lại; copy survey nói “cá nhân hóa” nhưng selector bỏ qua `weak_point`.
- Các app industry (Busuu, Duolingo) dùng bài test **adaptive** ngắn từ item bank nội bộ.

Cần placement đo ability hiệu quả hơn, khóa session, tách CEFR khỏi sub-level floor, bias nhẹ chọn câu theo `weak_point` từ survey — trong khi **`goal` chỉ dùng chọn scenario roadmap**.

---

## 2. Mục tiêu / Ngoài phạm vi

### Mục tiêu

- Placement adaptive: trả lời 1 câu → server cập nhật ước lượng ability → trả câu tiếp hoặc kết thúc.
- Độ dài: **tối thiểu 6**, **tối đa 15** câu; dừng sớm khi confidence đủ cao.
- Nguồn đề: **chỉ** `quiz_questions` `status=published` join `learning_skills` active (cùng bank MVP).
- Lưu attempt + từng câu trả lời; khóa session `in_progress` (resume, không chạy song song).
- Khi xong: ghi `current_level` (CEFR) và `placement_score` (**sub-level 1–10 trong level đó**); seed mastery từ các câu đã làm.
- Retake: cho phép với cooldown (**1 lần hoàn thành / cửa sổ 7 ngày** sau lần completed gần nhất).
- Bias mềm chọn câu chỉ từ **`weak_point`** (ưu tiên `skill_type` khớp khi hòa).
- FE wizard từng câu; deprecate batch `GET /onboarding/questions` + `POST /onboarding/placement`.
- Vẫn **không** tự assemble roadmap khi nộp placement xong.

### Ngoài phạm vi

- Full IRT / CAT với calibrate tham số item (Busuu Part II) — để sau khi có data.
- Bias placement theo **`goal`** (`goal` chỉ còn `pick_scenario` trên roadmap).
- Cache Redis pool câu hỏi.
- Auto-assemble roadmap sau placement.
- Partial-credit / chấm mở ngoài `grade_mcq` hiện có.
- Đổi schema survey / JSON answer động (concern riêng).
- Viết lại level-challenge ngoài việc ghi nhận `placement_score` nghĩa là sub-level 1–10.

---

## 3. Quyết định đã chốt

| Chủ đề | Quyết định |
|--------|------------|
| UX / API | **Adaptive session** (Approach 1): tạo session → vòng trả lời → xong |
| Độ dài | Min **6**, max **15** |
| Stop rule | Dừng nếu `(asked >= 6 AND confidence >= 0.85) OR asked >= 15` |
| Item bank | Chỉ quiz published (không tạo bank placement riêng) |
| Survey → placement | **Chỉ soft bias `weak_point`** |
| Survey → roadmap | **`goal` → scenario**; `weak_point` vẫn tie-break thứ tự skill (đã có) |
| Output profile | `current_level` = CEFR; `placement_score` = sub-level **1–10** (không còn = số câu đúng) |
| Lưu attempt | Bảng mới `placement_attempts` + `placement_attempt_answers` |
| Retake | Cooldown **7 ngày** kể từ lần **completed** gần nhất; `in_progress` thì resume |
| Sau khi nộp | Chỉ level + mastery; user tự assemble roadmap |
| Điểm legacy | Giữ nguyên `placement_score` cũ (có thể = số đúng cũ); attempt mới ghi sub-level thật |

---

## 4. Vai trò survey / placement / roadmap

| Tín hiệu | Placement adaptive | Assemble roadmap |
|----------|--------------------|------------------|
| `weak_point` | Ưu tiên mềm `skill_type` khớp khi chọn câu tiếp | Đã có: ưu tiên skill cùng loại khi xếp path |
| `goal` | **Không dùng** | `pick_scenario` qua `GOAL_TO_CATEGORY` |
| `daily_time_min` / `occupation` | Không dùng | Ngoài spec này (follow-up tùy chọn) |
| Ability | Đo bằng bài adaptive | Tiêu thụ qua `current_level` + floor `placement_score` |

Giá trị `WeakPointEnum` (`grammar`, `vocabulary`, `confidence`, `writing`) không trùng hết `SkillTypeEnum`. Map bias:

| weak_point | skill_type ưu tiên |
|------------|--------------------|
| `grammar` | `grammar` |
| `vocabulary` | `vocabulary` |
| `writing` | `functional` (gần skill sản sinh nhất trong bank); không có thì fallback bất kỳ |
| `confidence` | **không filter skill_type** (tắt soft bias) |

---

## 5. Luồng người dùng

### 5.1 Placement lần đầu (sau survey)

```text
survey_done && chưa completed (hoặc được phép retake)
  → POST /placement/sessions
  → UI hiện câu #1
  → lặp:
       POST .../sessions/{id}/answers { question_id, answer }
       ← { done: false, question } | { done: true, current_level, placement_score, ... }
  → Màn kết quả → CTA assemble roadmap / dashboard
```

### 5.2 Resume

```text
GET /placement/sessions/current
  → nếu in_progress: trả attempt + câu đang chờ trả lời
  → không thì 404 / rỗng
```

### 5.3 Retake

```text
GET retake-status → { allowed, retry_after_at? }
  → nếu allowed: POST /placement/sessions (abandon in_progress cũ nếu có; tạo mới)
  → khi completed: ghi đè profile.current_level + placement_score; seed mastery từ attempt mới
```

Cooldown: `allowed` khi không có `in_progress` cần resume trước, và (chưa từng completed **hoặc** `now - last_completed_at >= 7 days`).

---

## 6. Kiến trúc

```text
Survey (profile.weak_point, profile.goal)
        │
        ▼
┌───────────────────────┐     published      ┌──────────────────┐
│ placement_adaptive    │ ◄──────────────── │ quiz_questions   │
│ engine + sessions API │     join skills    │ + learning_skills│
└──────────┬────────────┘                    └──────────────────┘
           │ complete
           ▼
   user_profiles.current_level
   user_profiles.placement_score (1–10)
   user_skill_mastery (seed)
           │
           ▼
   roadmap assemble (goal→scenario; score→floor)
```

### 6.1 Mô hình ability (không IRT)

- Chỉ số CEFR: `A1=0 … C1=4`.
- State mỗi attempt: `ability_index` (float), `confidence` (0..1), `questions_asked`, `seen_question_ids`.
- Bắt đầu: `ability_index = 1.0` (gần A2), `confidence = 0`.
- Sau mỗi câu đã chấm:
  - `item_level` = index CEFR của skill câu hỏi.
  - Đúng: `ability_index += step * (1 + 0.25 * max(0, item_level - ability_index))`
  - Sai: `ability_index -= step * (1 + 0.25 * max(0, ability_index - item_level))`
  - Clamp `ability_index` trong `[0, 4]`.
  - `step` mặc định **0.45**.
  - Confidence: tăng khi kết quả “khớp” estimate; giảm khi bất ngờ:

```text
surprise = abs(item_level - ability_index_before)
if correct and item_level >= ability_index_before - 0.5: confidence += 0.12 + 0.03 * surprise
if wrong and item_level <= ability_index_before + 0.5: confidence += 0.12 + 0.03 * surprise
else: confidence -= 0.08   # kết quả bất ngờ
confidence = clamp(confidence, 0, 1)
```

### 6.2 Chọn câu tiếp theo

1. Pool = câu published trên skill active, `id` chưa nằm trong `seen`.
2. Target CEFR = `CEFR_ORDER[clamp(round(ability_index), 0, 4)]`.
3. Ưu tiên pool đúng target; hết thì nới `±1` level; vẫn hết → lỗi rõ (bank không đủ).
4. Trong ứng viên, sort key tăng dần:
   - `0` nếu `skill_type` thuộc set ưu tiên từ `weak_point`, else `1`
   - ưu tiên `skill_id` chưa dùng trong attempt
   - random khi hòa
5. Thêm id vào `seen_question_ids`; trả payload public (không lộ đáp án).

### 6.3 Map kết quả khi kết thúc

Khi stop rule kích hoạt:

- `current_level = CEFR_ORDER[clamp(round(ability_index), 0, 4)]`
- Sub-level trong level:  
  `frac = ability_index - floor(ability_index)`  
  `placement_score = clamp(int(frac * 10) + 1, 1, 10)`  
  Plan sẽ chốt bằng unit test (thấp ≈ 1–3, giữa ≈ 4–7, cao ≈ 8–10).
- Ghi `result_level`, `result_sublevel` trên attempt; copy sang profile.
- Seed mastery: mỗi dòng answer gọi `apply_answer(user_id, skill_id, is_correct)` (như MVP), **chỉ khi completed**.

### 6.4 Stop rule

```text
asked = questions_asked  # sau khi ghi câu vừa trả lời
if asked >= 15: finish
elif asked >= 6 and confidence >= 0.85: finish
else: serve next
```

Không bao giờ kết thúc trước 6 câu (dù confidence đã cao).

---

## 7. Mô hình dữ liệu

### 7.1 `placement_attempts`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `id` | BIGSERIAL PK | |
| `user_id` | BIGINT FK users | index |
| `status` | ENUM | `in_progress`, `completed`, `abandoned` |
| `ability_index` | FLOAT | ước lượng hiện tại |
| `confidence` | FLOAT | 0..1 |
| `questions_asked` | INT | |
| `seen_question_ids` | JSON | list[int] |
| `current_question_id` | BIGINT NULL | câu đã serve, đang chờ trả lời |
| `weak_point_bias` | VARCHAR/ENUM NULL | snapshot lúc start |
| `result_level` | CEFR NULL | khi completed |
| `result_sublevel` | SMALLINT NULL | 1–10 khi completed |
| `started_at` | TIMESTAMPTZ | |
| `completed_at` | TIMESTAMPTZ NULL | |

Tối đa một `in_progress` / `user_id` (enforce trong service nếu unique DB bất tiện).

### 7.2 `placement_attempt_answers`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `id` | BIGSERIAL PK | |
| `attempt_id` | FK attempts | |
| `question_id` | FK quiz_questions | |
| `skill_id` | BIGINT | denormalized |
| `cefr_level` | CEFR | denormalized |
| `given_answer` | TEXT | |
| `is_correct` | BOOL | |
| `ability_after` | FLOAT | |
| `confidence_after` | FLOAT | |
| `created_at` | TIMESTAMPTZ | |

Unique `(attempt_id, question_id)`.

### 7.3 Profile

Không thêm cột. Đổi nghĩa chỉ với lần **completed mới**:

- `placement_score`: sub-level 1–10  
- `current_level`: CEFR từ adaptive estimate  

---

## 8. API

Prefix hiện có: `/api/v1/onboarding`.

| Method | Path | Mục đích |
|--------|------|----------|
| `POST` | `/placement/sessions` | Bắt đầu attempt; trả `{ attempt_id, question, progress }` |
| `GET` | `/placement/sessions/current` | Resume `in_progress` |
| `POST` | `/placement/sessions/{attempt_id}/answers` | Chấm + câu tiếp hoặc kết quả cuối |
| `GET` | `/placement/retake-status` | `{ allowed, retry_after_at, has_in_progress }` |

### 8.1 Start session

Điều kiện: `survey_done`; không có `in_progress` khác (hoặc trả về cái đang có); nếu đã completed thì phải được phép retake.

Shape câu hỏi: tái dùng field `placement_public_dict` (`id`, `skill_id`, `cefr_level`, `question_type`, `stem`, `passage`, `options`, `difficulty`).

Progress: `{ asked, min_questions: 6, max_questions: 15 }`.

### 8.2 Submit answer

- `question_id` phải trùng `current_question_id`.
- Chấm bằng `grade_mcq` / `grade_placement_answer` hiện có.
- Ghi answer row; cập nhật ability/confidence; set câu tiếp hoặc clear.
- Nếu xong: commit profile + mastery; `status = completed`.

Lỗi: 400 sai câu / trùng; 403 chưa survey; 409 cooldown / đã completed chưa được retake; 409 attempt không `in_progress`; 400/503 bank không đủ.

### 8.3 Deprecate

Sau khi FE chuyển xong, xóa hoặc trả 410:

- `GET /onboarding/questions`
- `POST /onboarding/placement` (batch)

Ưu tiên cùng PR với FE.

---

## 9. Frontend

- `/onboarding/placement`: wizard 1 câu/màn; start/resume; mỗi lần trả lời POST; progress `asked / max` (ghi chú có thể xong sớm sau 6 câu).
- Màn kết quả: CEFR + sub-level; CTA assemble roadmap (đã có).
- Entry retake: dashboard/settings dùng `retake-status`.
- Copy: adaptive 6–15 câu; không hứa cố định 10 câu.

---

## 10. Migration & tương thích

1. Alembic tạo bảng attempt + enum status.
2. Không rewrite bắt buộc profile cũ.
3. Level challenge tiếp tục ghi `placement_score` 1–10 (đã gần nghĩa sub-level).
4. Docs: đánh dấu flow batch `2026-07-15` bị thay cho learner path.

---

## 11. Kiểm thử

- Unit: cập nhật ability; confidence; cửa sổ CEFR khi pick; ưu tiên `weak_point`; dừng ở 6+0.85 và ở 15; không dừng trước 6.
- API: khóa session; sai `question_id`; cooldown retake; resume; bank thiếu.
- FE smoke: lần đầu + resume giữa chừng.

---

## 12. Phác thảo service

Theo style orchestrator (`service-orchestrator`):

- `placement_session_service.py` — start / resume / answer / retake-status / side effect khi complete  
- `placement_adaptive_engine.py` — pure: `update_ability`, `pick_next`, `should_stop`, `map_to_profile`  
- Giữ helper hữu ích trong `placement_service.py` (`PlacementCandidate`, `load_published_candidates`, `grade_placement_answer`, `placement_public_dict`) hoặc tách module dùng chung — plan quyết định split cụ thể, tránh rewrite big-bang.

---

## 13. Tiêu chí thành công

- Học viên hoàn thành onboarding qua adaptive session, không cần endpoint batch.
- User giả lập mạnh/yếu kết thúc trong 6–15 câu với CEFR hợp lý.
- Assemble roadmap vẫn chạy với `placement_score` sub-level mới.
- Retake bị chặn trong 7 ngày; được phép sau đó.
- `goal` không xuất hiện trong code chọn câu placement.

---

## 14. Follow-up (ngoài scope)

- Wire `daily_time_min` vào độ dài roadmap / reminder.
- Calibrate IRT khi có đủ volume câu trả lời.
- Tag topic/scenario trên quiz item để personalize thêm (không thay đo ability).
