# EnglishFlow — Software Requirements Specification (SRS)

| Trường | Giá trị |
|--------|---------|
| **Document ID** | EF-SRS-001 |
| **Version** | 1.2 |
| **Date** | 2026-08-04 |
| **Status** | Draft — engineering baseline |
| **System** | EnglishFlow (web application) |
| **Audience** | Backend/Frontend engineers, QA, tech lead |
| **Related** | As-built: [`SYSTEM_SPEC.md`](./SYSTEM_SPEC.md) · Nghiệp vụ (ngoài SRS): [`BUSINESS.md`](./BUSINESS.md) |

---

## 0. Mục đích tài liệu (engineering)

Tài liệu này định nghĩa **yêu cầu phần mềm** để:

| Vai trò | Dùng SRS để |
|---------|-------------|
| Implementer | Biết module nào phải có, contract hành vi, ràng buộc không được phá |
| Reviewer / Tech lead | So PR với REQ ID; từ chối scope ngoài Won't |
| QA | Viết test case / acceptance từ cột Acceptance & §12 |
| Maintainer | Phân biệt baseline (phải giữ) vs increment P0 (đang đóng) |

**Không** dùng SRS làm pitch sản phẩm, user persona marketing, hay chiến lược cạnh tranh. Phần “người học cần gì” thuộc [`BUSINESS.md`](./BUSINESS.md).

**Nguồn sự thật khi conflict:** code đang chạy + cột Status trong SRS > design cũ trong `docs/superpowers/specs/`.

---

## Mục lục

1. [Bài toán phần mềm](#1-bài-toán-phần-mềm)
2. [Phạm vi hệ thống](#2-phạm-vi-hệ-thống)
3. [Actors & interface](#3-actors--interface)
4. [Thuật ngữ kỹ thuật](#4-thuật-ngữ-kỹ-thuật)
5. [Giả định, ràng buộc, phụ thuộc](#5-giả-định-ràng-buộc-phụ-thuộc)
6. [Yêu cầu chức năng — Baseline](#6-yêu-cầu-chức-năng--baseline)
7. [Yêu cầu chức năng — Increment P0](#7-yêu-cầu-chức-năng--increment-p0)
8. [Yêu cầu phi chức năng](#8-yêu-cầu-phi-chức-năng)
9. [Yêu cầu dữ liệu & persistence](#9-yêu-cầu-dữ-liệu--persistence)
10. [Invariants / quy tắc hệ thống](#10-invariants--quy-tắc-hệ-thống)
11. [Ưu tiên MoSCoW](#11-ưu-tiên-moscow)
12. [Verification & Definition of Done](#12-verification--definition-of-done)
13. [Out of scope (không implement)](#13-out-of-scope-không-implement)
14. [Traceability](#14-traceability)
15. [Changelog](#15-changelog)

---

## 1. Bài toán phần mềm

### 1.1 Problem statement (system under development)

Cần xây dựng và duy trì một **hệ thống phần mềm phân tán** gồm:

1. **API server** (FastAPI) quản lý identity, RBAC, domain state (profile, skills, quiz bank, roadmap, placement attempts, books metadata).
2. **Web clients** (Next.js) cho hai surface: learner và admin.
3. **Pipeline xử lý tài liệu** biến PDF → cấu trúc unit → text chunks (+ embeddings) → liên kết vào skill graph cố định → sinh/duyệt artefact quiz & lesson.
4. **Runtime học** chọn subset skill theo rule (level, coverage, prerequisite, mastery, difficulty floor), cập nhật mastery khi chấm bài, khóa/mở roadmap step.

Bài toán kỹ thuật cần giải:

| ID | Problem | Hệ thống phải |
|----|---------|---------------|
| SP-1 | Gán và lưu trạng thái trình độ user (`current_level`, `placement_score`) trước khi lập path | Survey resolution + placement session + ghi `UserProfile` |
| SP-2 | Lập và duy trì path học cá nhân theo skill graph + mastery, không theo TOC sách | Assemble / get / complete roadmap + replan |
| SP-3 | Ngân hàng item dùng chung cho placement và practice, có vòng đời draft→published | `quiz_questions` / `quiz_passages` + publish gate |
| SP-4 | Ingest PDF an toàn, có state machine sách, không expose PDF cho learner API | Upload → detect → index → Ready; storage riêng |
| SP-5 | Gắn nội dung sách vào catalog skill **có sẵn** (không sinh skill ad-hoc mặc định) | Attach-only sync → `book_skill_sources` |
| SP-6 | Tách cost/latency LLM: generation ở admin-time; learner-path chỉ chấm/đọc published | Flag + service boundaries |

### 1.2 Mục tiêu kỹ thuật baseline (delivered capability)

| ID | Capability | Verify |
|----|------------|--------|
| TC-1 | AuthN/AuthZ đầy đủ cho learner/admin API | Token + 403 đúng permission |
| TC-2 | State machine onboarding: `survey` → (`placement`) → `completed` | `GET /onboarding/status` |
| TC-3 | Placement attempt TOEIC R+W: assemble form, grade, finalize profile | Session endpoints |
| TC-4 | Roadmap assemble/complete với mastery gate 0.7 | `/roadmap*` |
| TC-5 | Practice: serve published items, update mastery | `/quiz*` |
| TC-6 | Book pipeline + attach + generate/publish quiz (± lesson) | `/admin/books|quiz|lessons*` |

### 1.3 Mục tiêu increment P0 (đóng vòng dữ liệu + verify E2E)

P0 không phải “tính năng marketing”. P0 là **increment engineering**: đủ seed/coverage A1 + E2E path chạy được trên môi trường có data thật.

| ID | Deliverable | Verify |
|----|-------------|--------|
| TC-P1 | Catalog A1 seeded; ≥1 book A1 ready + attached | DB + admin APIs |
| TC-P2 | ≥ K skill A1 có coverage + published practice set (K chốt trong ticket; default đề xuất 8) | Query + practice API |
| TC-P3 | E2E automated hoặc scripted: register → onboarding → assemble → answer → complete week | Test/script pass |
| TC-P4 | Lỗi thiếu coverage/scenario/bank trả 4xx + message deterministic | Contract test |

### 1.4 Non-goals (engineering)

Không nằm trong scope implement hiện tại / P0:

- Module speaking / speech recognition (voice-call, STT, TTS, pronunciation score)
- Free-chat learner tab, vocab bank, story, streak/badge APIs (dù có thể còn ORM models)
- **Ngoại lệ P0:** text AI tutor role-play gắn roadmap (`/api/v1/tutor`) — xem §7.4, spec [`2026-08-04-ai-tutor-text-roleplay-design.md`](./superpowers/specs/2026-08-04-ai-tutor-text-roleplay-design.md)
- Seed catalog B1–C1
- Multi-tenant LMS / classroom
- Native mobile clients
- Cam kết độ chính xác placement tương đương kỳ thi TOEIC chính thức

---

## 2. Phạm vi hệ thống

### 2.1 In scope (components)

| Component | Path / stack | Trách nhiệm |
|-----------|--------------|-------------|
| API | `backend/` FastAPI | Domain logic, persistence, jobs nền detect/index/gen |
| Learner UI | `frontend/my-app` routes onboarding/dashboard | Gọi API learner; route guard |
| Admin UI | `frontend/my-app` routes `/admin/*` | Gọi API admin; role gate |
| Postgres | SQLAlchemy + Alembic | System of record quan hệ |
| MongoDB | book chunks | Text + embedding vectors |
| Redis | blocklist, permission cache | Session phụ trợ |
| Object storage | Supabase bucket | PDF binaries |
| LLM / Voyage | external HTTP | Merge/attach/gen/grade/embed |

### 2.2 Explicit out of scope

Xem §13. Models ORM tồn tại nhưng **không** có router learner ⇒ **không** tính là requirement đã giao.

### 2.3 Context diagram

```text
                    ┌─────────────────────────────────────┐
  Browser learner ──┤           Next.js Web               │
  Browser admin ────┤                                     │
                    └─────────────────┬───────────────────┘
                                      │ HTTPS / JSON
                    ┌─────────────────▼───────────────────┐
                    │         FastAPI (/api/v1/*)           │
                    └─┬─────┬─────┬─────┬─────┬───────────┘
                      │     │     │     │     │
                 Postgres Redis Mongo Supabase LLM/Voyage
```

**Boundary rule:** Learner-facing API SHALL NOT stream/download book PDF. PDF I/O chỉ qua admin book services + storage.

---

## 3. Actors & interface

| Actor | Type | Interface |
|-------|------|-----------|
| `LearnerClient` | Human via FE | `/api/v1/auth`, `/onboarding`, `/roadmap`, `/quiz`, `/skills`, `/tutor` |
| `AdminClient` | Human via FE | `/api/v1/admin/*` với permission |
| `AuthService` | System | JWT access + refresh cookie/jti store |
| `StructureJob` | Background | Detect structure sau upload |
| `IndexJob` | Background | Chunk + embed |
| `LlmClient` | External | JSON chat completions |
| `EmbeddingClient` | External | Voyage embed batches |
| `ObjectStore` | External | Put/get/delete PDF |

RBAC roles tối thiểu: `learner`, `admin`. Permission ví dụ: `book:manage`, `scenario:edit`, `report:view_all`.

---

## 4. Thuật ngữ kỹ thuật

| Term | Definition (code-level) |
|------|-------------------------|
| `current_level` | `UserProfileDB.current_level` ∈ CEFR enum |
| `placement_score` | int 1..10; input difficulty floor khi assemble |
| `LearningSkill` | Row `(slug, cefr_level)`; `origin ∈ {catalog, legacy}` |
| `SkillEdge` | Prerequisite `from → to` |
| `Coverage` | ∃ `BookSkillSource` với `is_excluded=false` cho skill |
| `Attach` | Sync ghi sources; **không** INSERT skill mới mặc định |
| `Mastery` | `UserSkillMastery.mastery` ∈ [0,1]; gate complete = **0.7** |
| `Published item` | `QuizQuestion.status=published` (và passage liên quan nếu có) |
| `Book status` | `uploaded \| needs_review \| processing \| ready \| failed` |
| `Baseline` | Capability đã ship; regression = bug |
| `P0` | Increment đóng data+E2E; không phải product roadmap dài |

---

## 5. Giả định, ràng buộc, phụ thuộc

### 5.1 Assumptions

| ID | Assumption |
|----|------------|
| A-1 | Môi trường có Postgres, Redis, Mongo, Supabase credentials, LLM key, Voyage key |
| A-2 | Migration Alembic ở head trước khi chạy seed/attach |
| A-3 | `python -m app.seeds.cefr_ladder_a1_a2` chạy trước sync attach |
| A-4 | Scenarios seed đủ để `GOAL_TO_CATEGORY` resolve khi assemble |
| A-5 | Client là modern browser; không yêu cầu native app |

### 5.2 Constraints

| ID | Constraint |
|----|------------|
| C-1 | Backend: FastAPI + SQLAlchemy async + Alembic |
| C-2 | Frontend: Next.js App Router |
| C-3 | Placement: one completed attempt ⇒ không start attempt mới (chỉ resume `in_progress`) |
| C-4 | Book sync: attach-only lên catalog |
| C-5 | Secrets chỉ qua env; không commit |
| C-6 | Public service functions nên theo orchestrator style (repo rule) |

### 5.3 External dependencies

| ID | Dependency | Failure mode hệ thống phải xử lý |
|----|------------|----------------------------------|
| D-1 | LLM | Gen/grade/attach fail → lỗi rõ; không partial publish âm thầm |
| D-2 | Voyage | Embed pending/retry; book có thể ready text-first tùy implement hiện tại |
| D-3 | Supabase | Upload/detect fail → book không `ready` |
| D-4 | Published TOEIC pool | `assemble_form` thiếu quota → lỗi khi start placement |

---

## 6. Yêu cầu chức năng — Baseline

Format ID: `FR-<AREA>-<nnn>`.  
**Status:** `Implemented` | `Partial` | `Missing`.

### 6.1 Auth & RBAC

| ID | SHALL | Priority | Status | Acceptance |
|----|-------|----------|--------|------------|
| FR-AUTH-001 | API đăng ký tạo user và gắn role `learner` | Must | Implemented | User + role trong DB |
| FR-AUTH-002 | API login phát hành access JWT + refresh (persist jti) | Must | Implemented | Session gọi được protected route |
| FR-AUTH-003 | API refresh cấp access mới khi refresh hợp lệ | Must | Implemented | `POST /auth/token/refresh` |
| FR-AUTH-004 | Logout revoke refresh + blocklist access (Redis) | Must | Implemented | Token cũ 401 |
| FR-AUTH-005 | `GET /auth/me` trả identity + roles/permissions | Must | Implemented | Schema ổn định cho FE |
| FR-AUTH-006 | Admin endpoints enforce permission (vd. `book:manage`) | Must | Implemented | Learner → 403 |

### 6.2 Onboarding state & survey

| ID | SHALL | Priority | Status | Acceptance |
|----|-------|----------|--------|------------|
| FR-ONB-001 | Expose onboarding step: `survey` \| `placement` \| `completed` | Must | Implemented | Khớp profile flags |
| FR-ONB-002 | List active survey questions | Must | Implemented | |
| FR-ONB-003 | Accept survey submit + `level_resolution` payload | Must | Implemented | `survey_done=true` |
| FR-ONB-004 | `beginner` ⇒ set A1 + placement_score + completed (skip placement) | Must | Implemented | |
| FR-ONB-005 | `self_selected` ⇒ set CEFR đã chọn + completed | Must | Implemented | |
| FR-ONB-006 | `placement` ⇒ survey done, step=placement, level chưa finalize | Must | Implemented | |
| FR-ONB-007 | Learner UI/middleware chặn `/dashboard` khi chưa completed | Must | Implemented | Redirect |

### 6.3 Placement subsystem

| ID | SHALL | Priority | Status | Acceptance |
|----|-------|----------|--------|------------|
| FR-PLC-001 | Start/resume attempt; form từ published items có `toeic_part` | Must | Implemented | |
| FR-PLC-002 | Reading quotas r5=30,r6=16,r7=54; section timer | Must | Implemented | `placement/quotas.py` |
| FR-PLC-003 | Grade reading answers; persist attempt answers | Must | Implemented | |
| FR-PLC-004 | Advance reading→writing khi done hoặc timeout | Must | Implemented | |
| FR-PLC-005 | Writing quotas w1=5,w2=2,w3=1; LLM grade theo part scale | Must | Implemented | |
| FR-PLC-006 | Complete: map scores → `current_level` + `placement_score` | Must | Implemented | Attempt `completed` |
| FR-PLC-007 | Enforce one-shot via access-status | Must | Implemented | |
| FR-PLC-008 | Legacy adaptive answer endpoint unavailable (410) | Must | Implemented | |
| FR-PLC-009 | MAY seed mastery từ reading đúng | Should | Implemented | |

### 6.4 Roadmap subsystem

| ID | SHALL | Priority | Status | Acceptance |
|----|-------|----------|--------|------------|
| FR-RM-001 | `POST /roadmap/assemble` build path tại `current_level` từ covered skills | Must | Implemented | 200 + weeks hoặc 400 deterministic |
| FR-RM-002 | Respect prerequisite order + difficulty floor từ `placement_score` | Must | Implemented | Unit/service tests |
| FR-RM-003 | First step `in_progress`; remainder `locked` until unlocked | Must | Implemented | |
| FR-RM-004 | `GET /roadmap` trả path hiện tại | Must | Implemented | |
| FR-RM-005 | Complete chỉ khi step `in_progress` và mastery skill ≥ 0.7 | Must | Implemented | Else 400 |
| FR-RM-006 | Complete triggers `replan_locked_tail` | Must | Implemented | |
| FR-RM-007 | Learner roadmap không phụ thuộc book_id | Must | Implemented | |

### 6.5 Practice / mastery

| ID | SHALL | Priority | Status | Acceptance |
|----|-------|----------|--------|------------|
| FR-QZ-001 | Serve random published questions by `skill_id` without answers | Must | Implemented | |
| FR-QZ-002 | `POST /quiz/answer` grades and updates mastery | Must | Implemented | |
| FR-QZ-003 | Mastery update: prior 0.35; +α0.25 correct; −β0.20 wrong; clamp [0,1] | Must | Implemented | `mastery_service` tests |
| FR-QZ-004 | Practice UI allows repeated attempts until gate | Should | Implemented | |

### 6.6 Learn mini-unit

| ID | SHALL | Priority | Status | Acceptance |
|----|-------|----------|--------|------------|
| FR-LRN-001 | If `LEARN_UNIT_ENABLED` and published lesson ⇒ serve lesson payload | Must | Partial | Default flag **false** |
| FR-LRN-002 | `can_skip` if lesson completed or mastery ≥ 0.7 | Should | Implemented | |
| FR-LRN-003 | Writing feedback MUST NOT mutate mastery | Must | Implemented | |
| FR-LRN-004 | Complete lesson persists `UserLessonProgress` | Must | Implemented | |

### 6.7 Book ingest

| ID | SHALL | Priority | Status | Acceptance |
|----|-------|----------|--------|------------|
| FR-BK-001 | Admin upload PDF + title, `book_type`, `cefr_level` | Must | Implemented | Object stored + row created |
| FR-BK-002 | Auto/manual detect units → structure preview | Must | Implemented | |
| FR-BK-003 | Gate pass ⇒ index ⇒ `ready` | Must | Implemented | |
| FR-BK-004 | Gate fail ⇒ `needs_review`; confirm/retry endpoints | Must | Implemented | |
| FR-BK-005 | Reindex unit / retry embeddings / delete | Should | Implemented | |
| FR-BK-006 | Status ∈ defined enum only | Must | Implemented | |

### 6.8 Attach, generate, publish

| ID | SHALL | Priority | Status | Acceptance |
|----|-------|----------|--------|------------|
| FR-SK-001 | Sync attach units → catalog skills; no default skill INSERT | Must | Implemented | |
| FR-SK-002 | Heuristic exclude appendix/answer key/review/test | Should | Implemented | |
| FR-SK-003 | Generate MCQ drafts grounded primary source | Must | Implemented | status=draft |
| FR-SK-004 | Generate writing drafts W1–W3 | Should | Implemented | |
| FR-SK-005 | Publish selected drafts → published bank | Must | Implemented | |
| FR-SK-006 | Generate + publish skill lesson | Should | Implemented | |
| FR-SK-007 | Maintain `is_primary` source | Should | Implemented | |

### 6.9 Admin survey API

| ID | SHALL | Priority | Status | Acceptance |
|----|-------|----------|--------|------------|
| FR-ASV-001 | CRUD/deactivate survey questions with permission | Could | Partial | API yes; admin FE Missing |

---

## 7. Yêu cầu chức năng — Increment P0

P0 = đóng **data dependencies** + **E2E verification**. Ops checklist là deliverable engineering (runbook), không phải “soft skill”.

### 7.1 Data readiness

| ID | SHALL | Priority |
|----|-------|----------|
| FR-P0-001 | Catalog A1 present; sync SHALL NOT rewrite catalog edges/difficulty | Must |
| FR-P0-002 | ≥1 book with `cefr_level=A1`, status `ready`, attach executed | Must |
| FR-P0-003 | ≥ K A1 skills with coverage AND published practice items (K in release ticket; proposed 8) | Must |
| FR-P0-004 | ≥ M A1 lessons published if Learn enabled (proposed M=3) | Should |
| FR-P0-005 | Either TOEIC published pool meets quotas OR pilot config documents skip via beginner/self_selected only | Must |

### 7.2 E2E path (system-level)

| ID | SHALL | Priority |
|----|-------|----------|
| FR-P0-010 | Path register→survey→(placement\|skip)→assemble yields ≥1 `in_progress` step | Must |
| FR-P0-011 | Answering practice can raise mastery to ≥ 0.7 for that skill | Must |
| FR-P0-012 | Complete step succeeds and replan yields next `in_progress` or empty-eligible terminal state | Must |
| FR-P0-013 | When Learn enabled + lesson published: enforce learn-before-practice unless `can_skip` | Should |

### 7.3 Operability

| ID | SHALL | Priority |
|----|-------|----------|
| FR-P0-020 | Runbook: migrate → seed ladder → seed scenarios → (optional TOEIC seed) → upload → sync → generate → publish | Must |
| FR-P0-021 | Failures for missing coverage/scenarios/bank return explicit error payloads | Must |
| FR-P0-022 | Document actual roadmap horizon behavior (code default `max_steps=30`) vs any UI copy; single source of truth | Must |
| FR-P0-023 | No new routers for free-chat/vocab/story/streak in P0; `/api/v1/tutor` allowed per §7.4 | Must |

### 7.4 AI Tutor text role-play (increment P0)

Spec: [`2026-08-04-ai-tutor-text-roleplay-design.md`](./superpowers/specs/2026-08-04-ai-tutor-text-roleplay-design.md). **Không** phục hồi bảng `chat_*` đã drop.

| ID | SHALL | Priority |
|----|-------|----------|
| FR-TUT-001 | `POST /tutor/sessions` start session từ roadmap step `in_progress`; snapshot ≤3 `target_skill_ids` | Must |
| FR-TUT-002 | `POST /tutor/sessions/{id}/messages` stream assistant reply qua SSE + meta (correction/hint/goal_progress) | Must |
| FR-TUT-003 | `POST /tutor/sessions/{id}/end` trả summary + soft_skill_signals (sync JSON) | Must |
| FR-TUT-004 | Tutor paths MUST NOT write `user_skill_mastery` | Must |
| FR-TUT-005 | Entry FE từ CTA roadmap step `in_progress` → trang chat text | Must |

---

## 8. Yêu cầu phi chức năng

| ID | Category | SHALL | Priority |
|----|----------|-------|----------|
| NFR-001 | Security | Protected routes require valid access token | Must |
| NFR-002 | Security | Passwords hashed; secrets via env | Must |
| NFR-003 | Security | Admin authorization checked server-side | Must |
| NFR-004 | Reliability | Book pipeline errors leave non-success status (`failed`/`needs_review`) | Must |
| NFR-005 | API UX | Domain validation errors → 4xx + stable `detail` | Should |
| NFR-006 | Performance | Assemble interactive path typical &lt; 5s on local/staging sized DB | Should |
| NFR-007 | Observability | LLM/embed failures logged with book/skill ids | Should |
| NFR-008 | Config | `LEARN_UNIT_ENABLED` toggles Learn without migration | Must |
| NFR-009 | Cost isolation | Learner critical path MUST NOT require live quiz generation | Must |
| NFR-010 | Maintainability | Prefer orchestrator + helpers in `app/services` | Should |
| NFR-011 | Compatibility | FE targets current evergreen browsers | Should |

P0 **không** yêu cầu NFR throughput multi-thousand RPS.

---

## 9. Yêu cầu dữ liệu & persistence

### 9.1 Required stores

**Postgres (system of record):** users, RBAC, refresh tokens, profiles, survey questions, books, structure previews, learning_skills, skill_edges, book_skill_sources, quiz_passages, quiz_questions, placement_attempts(+answers), user_skill_mastery, skill_lessons, user_lesson_progress, scenarios, roadmap_steps, user_progress, roadmap_step_skills.

**Mongo:** book chunk documents (+ embedding fields).

**Redis:** access token blocklist; permission cache.

**Object storage:** PDF objects referenced by book rows.

### 9.2 Data rules

| ID | Rule |
|----|------|
| DR-001 | Unique `(slug, cefr_level)` on learning skills |
| DR-002 | Learner practice & placement assemble read `published` only |
| DR-003 | Sync MUST NOT delete `origin=catalog` skills |
| DR-004 | `placement_score` ∈ [1,10] when set |
| DR-005 | `mastery` ∈ [0,1] |
| DR-006 | Book status transitions stay within enum |

### 9.3 Required seeds before P0 verify

| ID | Artefact |
|----|----------|
| DR-010 | Roles/permissions (Alembic) |
| DR-011 | `cefr_ladder_a1_a2` |
| DR-012 | Scenarios seed |
| DR-013 | TOEIC pool seed **if** placement path enabled in verify plan |

---

## 10. Invariants / quy tắc hệ thống

| ID | Invariant |
|----|-----------|
| INV-001 | Learner progress units are skills at a CEFR level, not book documents |
| INV-002 | PDF is input to admin pipeline only; not a learner learning surface |
| INV-003 | Week completion depends on quiz-skill mastery ≥ 0.7, not lesson completion |
| INV-004 | Placement CEFR mapping uses configured score map (min band logic as implemented) |
| INV-005 | Completed placement attempt ⇒ no new start |
| INV-006 | Default skill growth path = attach to catalog, not LLM invent |
| INV-007 | Assemble candidates ⊆ skills with coverage at `current_level` (plus existing filters) |

---

## 11. Ưu tiên MoSCoW

| Priority | Items |
|----------|-------|
| **Must** | Baseline auth, onboarding, roadmap, practice/mastery, book→attach→publish quiz; P0 data+E2E; text AI tutor role-play (`/api/v1/tutor`, §7.4); INV-*; NFR security/cost isolation |
| **Should** | Learn subset, writing gen, explicit error contracts, horizon documentation |
| **Could** | Admin survey FE, richer reindex UX, shortened placement form (riêng ticket) |
| **Won't (P0)** | Voice/STT/TTS/pronunciation, free-chat tab, vocab/story/streak APIs, B1–C1 catalog seed, LMS, native apps |

---

## 12. Verification & Definition of Done

### 12.1 DoD per requirement

1. Behavior matches Acceptance / SHALL.  
2. Automated test added or updated when touching covered domains (mastery, assemble, attach, placement, validate…).  
3. No regression on Baseline Must.  
4. If behavior changes intentionally: update this SRS Status + [`SYSTEM_SPEC.md`](./SYSTEM_SPEC.md).

### 12.2 P0 increment acceptance (engineering gate)

**PASS** khi:

1. Runbook thực thi được trên staging/local shared.  
2. E2E path FR-P0-010..012 pass (test hoặc script có log).  
3. FR-P0-003 thỏa K đã chốt.  
4. Assemble không fail systematically trên dataset P0.

**FAIL** khi:

1. Không có published practice data ⇒ practice path dead.  
2. E2E complete-week không pass trong cửa sổ increment.  
3. Scope creep vào Won't mà gate trên chưa PASS.

FAIL ⇒ freeze feature mới; chỉ fix blocker hoặc archive increment.

---

## 13. Out of scope (không implement)

| Item | Note |
|------|------|
| Adaptive per-item placement | Removed (410) |
| Scheduled placement retake | Removed |
| Default LLM skill creation from TOC | Superseded by attach |
| Free-chat / vocab / story / gamification APIs | ORM may exist; no REQ |
| Voice-call / STT / TTS / pronunciation scoring | P1; text tutor only in P0 |
| Legacy `chat_*` table restore | Superseded by `tutor_*` (§7.4) |
| Admin users FE | Not required |
| Password reset flow | Not Must |
| Official TOEIC score equivalence | Out of scope |
| Offline-first / PWA complete | Out of scope |

---

## 14. Traceability

| Artefact | Role |
|----------|------|
| This file | Requirements / acceptance baseline |
| [`SYSTEM_SPEC.md`](./SYSTEM_SPEC.md) | As-built design detail |
| [`BUSINESS.md`](./BUSINESS.md) | Business narrative (non-normative cho code) |
| `backend/app/api/*.py` | Endpoint implementation |
| `backend/app/services/*.py` | Domain behavior |
| `backend/tests/*` | Automated verification |
| `frontend/my-app/src/app/*` | UI implementation |

REQ ID nên xuất hiện trong ticket/PR khi implement hoặc regression-fix.

---

## 15. Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-07-30 | Initial (product-framed) |
| 1.1 | 2026-07-30 | Rewrite: engineering problem statement, system scope, actors/interfaces, verification gate; tách BUSINESS |
| 1.2 | 2026-08-04 | Narrow Must: text AI tutor role-play (`/api/v1/tutor`, §7.4); voice/free-chat/vocab/story/streak remain Won't |

---

## Phụ lục A — Use cases (technical)

### UC-01 Bootstrap learner path

| Field | Content |
|-------|---------|
| Actors | `LearnerClient`, Auth, Onboarding, Roadmap |
| Pre | DB seeded (roles; ideally scenarios) |
| Main | Register/login → survey resolution → optional placement complete → `POST /roadmap/assemble` → `GET /roadmap` |
| Post | Profile has level; ≥1 progress `in_progress` **or** explicit 400 if data missing |
| Alt | Assemble fails ⇒ error payload (FR-P0-021) |

### UC-02 Mastery gate + replan

| Field | Content |
|-------|---------|
| Actors | `LearnerClient`, Quiz, Mastery, RoadmapProgress |
| Pre | In-progress step linked to `skill_id` |
| Main | Fetch questions → submit answers → mastery ≥ 0.7 → complete step → replan |
| Post | Step completed; new `in_progress` or terminal empty |

### UC-03 Content ingest to bank

| Field | Content |
|-------|---------|
| Actors | `AdminClient`, Book pipeline, SkillGraph, QuizGen |
| Pre | Catalog seeded; admin permission |
| Main | Upload → ready → sync attach → generate drafts → publish |
| Post | Covered skills + published items readable by learner quiz API |

---

## Phụ lục B — Module ↔ REQ map (tóm tắt)

| Module | Primary REQ |
|--------|-------------|
| `api/auth.py` + auth services | FR-AUTH-* |
| `api/onboarding.py` + survey/placement | FR-ONB-*, FR-PLC-* |
| `api/roadmap.py` + assembler/progress | FR-RM-* |
| `api/quiz.py` + mastery | FR-QZ-* |
| `api/skills.py` + lesson | FR-LRN-* |
| `api/admin_books.py` + structure/index | FR-BK-* |
| `api/admin_quiz.py` + skill_graph + gen | FR-SK-* |
| `api/admin_lessons.py` | FR-SK-006, FR-LRN-* |
| `api/tutor.py` + tutor services | FR-TUT-* |

---

*SRS v1.2 — normative cho implementation. Cập nhật version khi đổi Must/Won't hoặc invariant.*
