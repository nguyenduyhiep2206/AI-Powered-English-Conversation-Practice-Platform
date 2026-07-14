# Design: Placement test từ quiz bank (sau survey)

**Date:** 2026-07-15  
**Status:** Approved for planning  
**Depends on:** Book quiz roadmap Tasks 1–10 (`docs/superpowers/plans/2026-07-14-book-quiz-roadmap.md`)  
**Aligns with:** `EnglishFlow_FunctionalSpec.md` §2 (Onboarding — Survey & Placement), cập nhật nguồn đề sang `quiz_questions` published

---

## 1. Problem

Sau Task 10, hệ thống đã có:

- Canonical `learning_skills` + `quiz_questions` (draft → publish API)
- Learner quiz answer + `user_skill_mastery`
- `POST /roadmap/assemble` theo CEFR level
- Survey + `GET /onboarding/status` (`survey` → `placement` → `completed`)

Còn thiếu:

1. Admin UI publish draft → `published` (placement chỉ đọc published)
2. API + UI placement thật (`GET …/questions`, `POST …/placement`)
3. Sau placement: ghi `current_level` + seed mastery — **không** tự assemble roadmap

HV không thể hoàn thành onboarding end-to-end dù survey đã xong.

---

## 2. Goals / Non-goals

### Goals

- HV đã `survey_done` làm **đúng 10 câu** placement lấy từ **`quiz_questions` published**
- Chấm theo bảng Spec §2.3 (điểm 0–10 → A1…C1)
- Ghi `placement_score`, `current_level`; cập nhật mastery theo `skill_id` từng câu
- Đặt `onboarding_complete` khi survey + placement xong
- Admin publish draft trên Admin Books (cùng scope)
- Kết quả placement có CTA rõ: tạo lộ trình là **bước riêng sau** (ngoài scope implementation plan chi tiết của doc này, nhưng contract phải không gọi assemble)

### Non-goals

- Adaptive / IRT placement
- Auto-assemble roadmap khi nộp placement
- Retake placement (MVP: `placement_score is not null` → coi như xong)
- Redis cache danh sách câu (Spec ghi TTL 24h — để follow-up)
- Edit/delete câu hỏi trên admin (chỉ list draft + publish)
- Placement từ đề tĩnh seed ngoài bank

---

## 3. Decisions (locked)

| Chủ đề | Quyết định |
|--------|------------|
| Nguồn đề | **B** — chỉ `quiz_questions` với `status=published` |
| Sau nộp | **B** — chỉ level + mastery; user tạo lộ trình sau |
| Chấm điểm | **A** — 10 câu cố định, bảng 0–10 → CEFR như Functional Spec §2.3 |
| Phạm vi | **A** — Admin Publish UI + learner placement API + FE |

**Approach:** Onboarding endpoints đúng Functional Spec; `placement_service` chọn đề từ bank. Không dùng vòng lặp client qua `/quiz/skills/...`. Không tạo bảng `placement_attempts` ở MVP.

---

## 4. User flows

### 4.1 Admin — mở khóa bank cho placement

```text
Book ready → Sync skills → Generate quiz (draft)
  → Publish selected drafts
  → Câu published vào pool placement toàn hệ thống (theo skill.cefr_level)
```

Prerequisite vận hành: đủ published để selector chọn ~2 câu / level A1–C1 (tổng 10). Nếu thiếu → learner GET questions trả lỗi rõ (xem §7).

### 4.2 Learner — sau survey

```text
survey_done && !placement_done
  → GET /api/v1/onboarding/questions  (10 câu, không answer)
  → Làm bài trên /onboarding/placement
  → POST /api/v1/onboarding/placement { answers[] }
  → Server: chấm → placement_score + current_level + apply_answer per skill
  → placement_done / onboarding_complete
  → Màn kết quả: điểm + level; CTA “Tạo lộ trình” / vào dashboard
     (không gọi /roadmap/assemble trong submit)
```

### 4.3 Tạo lộ trình (ngoài luồng submit placement)

User (hoặc UI sau) gọi `POST /api/v1/roadmap/assemble` khi sẵn sàng — dùng `profile.current_level` + mastery đã seed + survey (`goal` / `weak_point`). Spec này chỉ đảm bảo **không** gắn assemble vào placement submit.

---

## 5. Architecture

```text
┌─────────────────┐     publish      ┌──────────────────┐
│ Admin Books FE  │ ───────────────► │ quiz_questions   │
│ BookQuizPanel   │                  │ status=published │
└─────────────────┘                  └────────┬─────────┘
                                              │ sample 10
┌─────────────────┐   GET questions           │
│ Placement FE    │ ◄─────────────────────────┤
│ /onboarding/…   │   POST placement          ▼
└────────┬────────┘                  ┌──────────────────┐
         │                           │ placement_service│
         │                           │  - select_pool   │
         └──────────────────────────►│  - grade batch   │
                                     │  - map CEFR      │
                                     │  - apply_answer  │
                                     │  - update profile│
                                     └──────────────────┘
```

**Units**

| Unit | Responsibility | Depends on |
|------|----------------|------------|
| `placement_service` | Chọn 10 câu; chấm batch; map level; cập nhật profile + mastery | `QuizQuestionDB`, `LearningSkillDB`, `mastery_service`, `UserProfileDB` |
| `admin` publish UI | List draft theo book; gọi publish API có sẵn | `GET/POST …/admin/quiz/…` |
| Onboarding FE | Gate survey→placement; form 10 câu; màn kết quả | `GET/POST onboarding/…`, `onboarding/status` |

---

## 6. API contracts

Giữ path Functional Spec §2.4; payload chi tiết hoá dưới đây. Router gắn vào `app/api/onboarding.py` (đã có `GET /status`).

### 6.1 `GET /api/v1/onboarding/questions`

**Auth:** user đã đăng nhập  
**Gate:** `survey_done == true`; nếu chưa → `400`  
**Nếu đã placement:** `400` hoặc `409` (“Đã hoàn thành placement”)

**Response 200**

```json
{
  "data": {
    "question_count": 10,
    "questions": [
      {
        "id": 101,
        "skill_id": 12,
        "cefr_level": "B1",
        "question_type": "mcq",
        "stem": "...",
        "options": ["a", "b", "c", "d"],
        "difficulty": "medium"
      }
    ]
  }
}
```

Không trả `answer` / `explanation`.

**Lỗi thiếu bank:** `503` (hoặc `400`) với message kiểu:  
`Chưa đủ câu hỏi published cho placement (cần 10 câu trải A1–C1).`

### 6.2 `POST /api/v1/onboarding/placement`

**Auth + gate:** như trên; một lần / user ở MVP.

**Request**

```json
{
  "answers": [
    { "question_id": 101, "answer": "has gone" }
  ]
}
```

- Phải gửi đúng tập `question_id` đã nhận từ GET gần nhất **theo best-effort MVP:** đủ 10 id thuộc pool published; thiếu/thừa → `400`.
- Không bắt buộc session token ở MVP (trade-off: user có thể GET nhiều lần rồi mix id nếu biết id — chấp nhận cho internal MVP; follow-up: placement session id).

**Response 200**

```json
{
  "data": {
    "placement_score": 7,
    "current_level": "B1",
    "correct_count": 7,
    "total": 10,
    "onboarding_complete": true
  }
}
```

**Side effects**

1. `user_profiles.placement_score`, `current_level`  
2. Với mỗi câu: `grade_*` → `apply_answer(user, skill_id, correct)`  
3. Không tạo/sửa `roadmap_steps` / không gọi assembler

### 6.3 Admin (đã có backend)

- `GET /api/v1/admin/quiz/books/{book_id}/questions?status_filter=draft`
- `POST /api/v1/admin/quiz/questions/publish` `{ "question_ids": [...] }`

FE mới chỉ wire UI — không đổi contract trừ khi cần filter `published` (đã hỗ trợ `status_filter`).

---

## 7. Question selection algorithm

**Input:** published questions join `learning_skills` (active) để lấy `cefr_level`.

**Target mix:** 2 câu cho mỗi level trong `{A1, A2, B1, B2, C1}` → 10 câu.

**Ưu tiên loại:** `mcq` trước; nếu thiếu slot thì `cloze` / `fix_grammar`.

**Random:** `ORDER BY random()` trong mỗi bucket level (Postgres).

**Fail-fast:** nếu sau khi fill không đủ 10 → lỗi §6.1 (không trả đề ngắn hơn 10; tránh phá bảng 0–10).

**Cân bằng skill:** trong một level, tránh 2 câu cùng `skill_id` nếu còn lựa chọn khác.

---

## 8. Scoring & CEFR mapping

Chấm từng câu đúng/sai (`correct_count` = số đúng).  
`placement_score = correct_count` (0–10).

| Điểm | `current_level` |
|------|-----------------|
| 0–3 | A1 |
| 4–5 | A2 |
| 6–7 | B1 |
| 8–9 | B2 |
| 10 | C1 |

**Grading rules (MVP)**

- `mcq`: `grade_mcq` hiện có (so khớp strip + lower)
- `cloze` / `fix_grammar`: cùng so khớp chuỗi strip + lower với `answer` lưu DB (không fuzzy)

Feedback từng câu trên UI lúc làm bài: **không bắt buộc**; màn kết quả chỉ cần điểm + level. Có thể trả `per_question` optional trong POST response ở plan chi tiết nếu FE cần — mặc định omit để đơn giản.

---

## 9. Frontend

### 9.1 Admin — Publish trong `BookQuizPanel`

Sau Sync/Generate:

1. Nút / section **Draft questions**: load draft theo `bookId`
2. Checkbox + **Publish selected**
3. Toast/status: “Published N questions”
4. Giữ pattern `authFetch` / `extractErrorMessage` như `admin-quiz.ts`

Mở rộng `lib/admin-quiz.ts`: `listBookQuestions(bookId, status?)`, `publishQuestions(ids)`.

### 9.2 Learner — Placement

- Route: `/onboarding/placement` (CSR), sau survey redirect về đây (thay vì chỉ `/start-onboarding`).
- Gate client: `fetchOnboardingStatus` — nếu `!survey_done` → survey; nếu `placement_done` → dashboard / start.
- UI: progress 1/10…10/10; stem + options (mcq) hoặc input (cloze/fix_grammar).
- Submit toàn bộ một lần (không gọi `/quiz/answer` từng câu trong placement — tránh double mastery; mastery chỉ qua placement submit).
- Result screen: score, level, copy “Bạn có thể tạo lộ trình học khi sẵn sàng” + link dashboard / nút placeholder assemble (wire assemble ở plan/roadmap sau nếu chưa có UI).

Middleware: giữ redirect onboarding khi `!onboarding_complete` như hiện tại.

---

## 10. Data / profile fields (đã có — không migration mới)

| Field | Dùng cho placement |
|-------|-------------------|
| `user_profiles.survey_done` | Gate vào placement |
| `user_profiles.placement_score` | Điểm 0–10; `not null` ⇒ `placement_done` |
| `user_profiles.current_level` | CEFR từ bảng §8 |
| `user_skill_mastery` | Seed từ 10 câu |
| `quiz_questions.status` | Chỉ `published` vào pool |

Không thêm bảng attempt ở MVP.

---

## 11. Error handling

| Case | HTTP | Hành vi |
|------|------|---------|
| Chưa survey | 400 | Message rõ |
| Đã placement | 409 | Không cho làm lại |
| Bank thiếu | 503 | Message hướng admin publish |
| Answers thiếu / id lạ | 400 | Không ghi profile |
| Câu không published | 400 | Từ chối batch |

---

## 12. Testing (acceptance)

**Backend**

- Selector: mock published mix → đúng 10, ~2/level; thiếu 1 level → fail
- Score map: 0,3,4,5,6,7,8,9,10 → level đúng bảng
- Submit: profile cập nhật; mastery rows tăng `attempts`; **không** tạo roadmap steps
- Gate: chưa survey / đã placement

**FE / E2E manual**

1. Admin publish ≥10 câu phủ A1–C1  
2. User mới: survey → placement → thấy 10 câu → submit → level hiện đúng  
3. Status `onboarding_complete`; dashboard vào được  
4. Roadmap chưa có week cho đến khi user (sau) assemble  

---

## 13. Implementation outline (cho writing-plans sau)

1. `placement_service` + unit tests (select + score map)  
2. Wire `GET /onboarding/questions`, `POST /onboarding/placement`  
3. Extend `admin-quiz.ts` + Publish UI trên `BookQuizPanel`  
4. FE `/onboarding/placement` + result; sửa redirect sau survey  
5. Manual checklist §12  

Thứ tự: backend selector/gates trước → admin publish (để có data) → learner FE.

---

## 14. Follow-ups (không trong scope)

- Placement session token / snapshot đề  
- Redis cache questions (Spec §2.4)  
- Retake / admin reset placement  
- Adaptive placement  
- Gắn “Tạo lộ trình” UI gọi `assemble`  
- Fuzzy grade cloze  

---

## 15. Traceability

| Nguồn | Cách cập nhật ý |
|-------|-----------------|
| Functional Spec §2.3–2.4 | Giữ 10 câu + bảng điểm + path API; **đổi** nguồn đề từ tĩnh → published bank |
| Plan 2026-07-14 follow-up #4 | “Diagnostic onboarding lấy câu từ bank” — spec này thực hiện |
| Task 7–9 | Tái dùng mastery + assemble riêng; placement không gọi assemble |
| Task 10 | Bổ sung Publish UI; Sync/Generate giữ nguyên |
