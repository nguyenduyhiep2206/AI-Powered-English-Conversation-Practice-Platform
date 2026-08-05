# Thiết kế: Lesson Q&A Chatbot (RAG dưới bài học)

**Ngày:** 2026-08-05  
**Trạng thái:** Implemented
**Plan:** `docs/superpowers/plans/2026-08-05-lesson-qa-rag.md`  
**Phụ thuộc:** Tutor RAG + Hybrid Memory (`2026-08-04-tutor-rag-hybrid-memory-design.md`), Mongo `book_chunks` + Voyage, Redis retrieval cache, `book_skill_sources`, Lesson mini-unit / practice page, learner CEFR profile  
**Map bài lab:** RetrievalQA surface riêng dưới bài học; corpus = sách đã index theo skill (thay CSV siêu thị)  

---

## 1. Vấn đề

Learner học trên `/dashboard/practice/[skillId]` (LessonMiniUnit) thường muốn **hỏi nghĩa / ngữ pháp / cách dùng** liên quan bài. Hiện chỉ có:

1. AI Tutor role-play (scenario) — không phải Q&A thuần dưới bài.
2. Full lesson content trong UI — không có chỗ hỏi “theo sách” với memory riêng.

Cần chatbot **gắn dưới bài học**: retrieve từ sách trước, rồi đưa chunks vào LLM để trả lời — giảm hallucinate và khớp lab RAG.

---

## 2. Mục tiêu / Không làm

### Mục tiêu

- Panel **“Hỏi về bài học”**: FAB góc phải dưới; **chỉ lúc phase learn** (ẩn khi practice/drill).
- Pipeline mỗi turn: **query → retrieve Top-K → đưa retrieved vào prompt → LLM → response** (+ windowed memory).
- Phạm vi retrieve = mọi unit gắn skill qua `book_skill_sources` (giống Tutor RAG scope theo skill).
- Hội thoại **persist** theo `(user_id, skill_id)`.
- Phong cách **Q&A thuần** (không role-play / không scenario).
- Tái dùng `tutor_rag` (`retrieve_for_session`, `is_off_topic`, `format_retrieved_block`), Redis cache retrieval, memory window helpers.
- Off-topic (tin tức, giá vàng…) → không retrieve; nhắc quay lại bài.
- **CEFR bắt buộc:** lấy level từ learner profile; prompt ràng độ dài câu / vocab theo level.
- **Cite nhẹ cho learner:** khi `route=rag`, UI hiện nguồn ngắn (vd. “Theo Unit 3 – At a restaurant”) từ chunk metadata.
- **Câu hỏi gợi ý (chips):** 3–5 câu liên quan bài; bấm = gửi luôn như tin nhắn user (vẫn đi RAG). Không thay input tự do.

### Không làm

- Gộp vào session AI Tutor role-play / catalog Promova.
- Chroma / FAISS / OpenAI embeddings mới (Mongo + Voyage).
- CSV siêu thị / web search realtime.
- Voice / avatar.
- RAG toàn cục ngoài skill đang học.

---

## 3. Quyết định

| Chủ đề | Quyết định |
|--------|------------|
| Surface | Chat riêng dưới practice lesson; API Lesson Q&A riêng |
| Approach | **A:** service/API mới + reuse `tutor_rag` (không mode=qa trên tutor) |
| Scope retrieve | Units gắn `skill_id` (`book_skill_sources`) |
| Persist | `lesson_qa_sessions` + `lesson_qa_messages`; unique active `(user_id, skill_id)` |
| Personality | Q&A only — giải thích theo sách |
| CEFR | Từ profile learner (fallback A1 nếu thiếu); rule độ dài/vocab trong `lesson_qa_prompt` |
| Khi nào RAG (`should_retrieve`) | **Default retrieve** cho mọi message trừ: (1) off-topic, (2) chào/ack quá ngắn (&lt; ~8 ký tự hoặc `hi`/`ok`/`thanks`…). Không dùng heuristic `needs_rag` lỏng của Tutor — Lesson Q&A là surface hỏi sách |
| Empty retrieve | Vẫn gọi LLM; bắt buộc trả lời kiểu “không tìm thấy trong sách gắn skill” |
| Cite (learner) | Message assistant (hoặc meta FE) kèm `sources: [{unit_title, score}]` khi có chunks |
| Memory | Opener (nếu có) + last N turns |
| Cache | Redis retrieval payload only (reuse pattern tutor) |
| UI | FAB góc phải dưới (`fixed`, z trên lesson window); mở ra panel chat ~400px; cite dưới câu trả lời RAG |
| Visibility | **Chỉ phase learn** — ẩn khi làm bài tập / practice |
| Suggested prompts | 3–5 chips; hiện khi panel mở và transcript trống (hoặc &lt; 1 user turn); ẩn/thu nhỏ sau khi đã chat. Bấm = `POST .../messages` với `content` = text chip |
| Prompt nguồn | **Deterministic từ lesson/skill** (title, objective, targets/vocab trong pack nếu có) + 1–2 template cố định (“What does … mean?”, “Give an example.”). Không gọi LLM để sinh chips ở v1 |
| Transport | SSE stream giống tutor messages |
| P1 (không block v1) | Optionally ghép thêm lesson pack text nếu skill chưa có book chunks — ngoài scope Accepted v1 |

---

## 4. Luồng turn

```text
GET  /api/lessons/{skill_id}/qa
  → ensure session (user + skill)
  → build suggested_prompts (3–5) từ skill + lesson pack
  → return session + messages + suggested_prompts

POST /api/lessons/{skill_id}/qa/messages { content }
  → auth + ownership
  → persist user message
  → memory_window (last N)
  → load cefr_level from learner profile
  → if is_off_topic(content):
        retrieved = none; route = off_topic
     elif LESSON_QA_RAG_ENABLED and should_retrieve(content):
        retrieve_for_session(skill_ids=[skill_id]) (+ redis)
        → retrieved; route = rag | retrieval_empty
     else:
        retrieved = none; route = smalltalk
  → build Q&A system prompt (CEFR rules + Retrieved book context)
  → stream LLM → persist assistant (meta.sources nếu có chunks) → SSE
  → FE hiện cite dưới bubble khi sources nonempty
  → done
```

### `should_retrieve(content)` (Lesson Q&A)

```text
false  nếu blank / chỉ whitespace
false  nếu is_off_topic (được gate trước; không gọi hàm này)
false  nếu length < 8 sau strip, hoặc normalize ∈ {hi, hello, ok, okay, thanks, thank you, yeah, yup}
true   mọi trường hợp còn lại  → luôn retrieve (khác Tutor needs_rag)
```

**Nguyên tắc prompt:** model chỉ được trả lời kiến thức dựa trên block retrieved; không bịa trang sách; câu trả lời khớp CEFR (câu ngắn hơn ở A1–A2).

### Ví dụ prompt (minh họa)

```text
You are a lesson Q&A assistant for an English learner (CEFR A2).
Skill: Booking a table / Making a reservation

CEFR A2 rules: short sentences, high-frequency words; brief VI gloss OK for hard words;
at most one gentle correction if the learner's English blocks meaning.

Answer ONLY using the Retrieved book context below.
If the context is empty or does not contain the answer, say you cannot find it
in the attached book units. Do not invent textbook content.

Retrieved book context:
[1] (Unit 3 – At a restaurant, score=0.81)
A reservation is when you book a table for a future time.
...

Recent chat:
user: What does "reservation" mean?
```

### Cite (learner-facing)

Sau câu trả lời RAG, UI hiện một dòng nguồn, ví dụ:  
`Theo sách: Unit 3 – At a restaurant`  
(lấy từ `meta.sources` / top chunk `unit_title`; tối đa 2–3 titles).

### Suggested prompts (chips)

Ví dụ skill “Making a reservation”, targets gồm *reservation*, *I'd like*:

```text
- What does "reservation" mean?
- How do I use "I'd like to…"?
- Give an example sentence for this lesson.
- What's the difference between "book" and "reserve"?
- How should I start the phone call?
```

Luật:
- Tối đa **5** chips; ưu tiên vocab/targets của pack hiện tại.
- Chip chỉ là shortcut nhập — **cùng pipeline** `POST messages` (RAG + memory).
- Không persist riêng danh sách chips; tái build mỗi `GET .../qa`.

---

## 5. Data model

### `lesson_qa_sessions`

| Column | Type | Notes |
|--------|------|--------|
| id | bigint PK | |
| user_id | FK users | index |
| skill_id | FK learning_skills | index |
| status | enum active\|ended | default active |
| message_count | smallint | user turns |
| created_at / updated_at | timestamptz | |

Constraint: **unique `(user_id, skill_id)`** cho session active (một thread Q&A mỗi skill mỗi user).  
Optional later: soft-clear history (xóa messages, giữ session) qua `DELETE .../qa/messages`.

### `lesson_qa_messages`

| Column | Type | Notes |
|--------|------|--------|
| id | bigint PK | |
| session_id | FK cascade | index |
| role | user\|assistant\|system | |
| content | text | |
| meta | JSON nullable | route, chunk refs/scores, off_topic |
| created_at | timestamptz | |

Không reuse bảng `tutor_sessions` — tách rõ role-play vs Q&A lesson.

---

## 6. API / config

```text
GET  /api/lessons/{skill_id}/qa
     → { session, messages, suggested_prompts: string[3..5] }
POST /api/lessons/{skill_id}/qa/messages   # SSE; content = typed hoặc từ chip
DELETE /api/lessons/{skill_id}/qa/messages  # optional clear history
```

Auth: learner logged-in; chỉ owner.

```text
LESSON_QA_RAG_ENABLED: bool = True
LESSON_QA_TOP_K: int = 4          # hoặc reuse TUTOR_RAG_TOP_K
LESSON_QA_MIN_SCORE: float = 0.25
LESSON_QA_MAX_CHARS: int = 2500
LESSON_QA_MEMORY_MAX_TURNS: int = 6
LESSON_QA_CACHE_TTL_SECONDS: int = 3600
```

Ưu tiên **reuse** settings `TUTOR_RAG_*` nếu không cần tách knob; chỉ thêm flag `LESSON_QA_RAG_ENABLED` và memory turns nếu muốn tune riêng.

---

## 7. Frontend

- Trang: `dashboard/practice/[skillId]` — chỉ khi **learn** (không gắn practice drills).
- **FAB góc phải dưới** “Hỏi về bài học” (`fixed bottom/right`, z ≥ lesson modal) → mở panel floating.
- Load `GET .../qa` khi mở panel (lazy).
- **Chips** `suggested_prompts` phía trên input khi chưa có / ít tin nhắn user; tap gửi luôn; vẫn giữ ô nhập tự do.
- Input + stream SSE; hiện history đã persist.
- Dưới bubble assistant: **cite** khi có `sources`.
- Empty / chưa index: copy rõ — “Chưa có nội dung sách gắn skill này” / “Không tìm thấy trong sách”.
- **Không** có Debug toggle trên UI sản phẩm.

Giữ visual language hiện tại của practice (không landing hero).

---

## 8. Backend modules (dự kiến)

| File | Responsibility |
|------|----------------|
| `models/lesson_qa.py` | Session + message ORM |
| Alembic migration | tables + unique index |
| `services/lesson_qa_prompt.py` | Q&A system + CEFR rules + user payload |
| `services/lesson_qa_service.py` | ensure session, `should_retrieve`, turn orchestrator, SSE, `meta.sources` |
| `services/lesson_qa_suggest.py` | build 3–5 suggested prompts từ skill/pack (pure helper) |
| `services/tutor_rag.py` | **reuse** retrieve / off-topic / format |
| `services/tutor_rag_cache.py` | **reuse** (key có prefix `lesson_qa:`) |
| `services/tutor_memory.py` | **reuse** window + token estimate |
| `api/lesson_qa.py` | routes |
| `frontend/.../LessonQaPanel.tsx` | collapsible chat + chips |
| tests | retrieve wire, off-topic, persist, empty chunks, token window, suggest builder |

Public orchestrator ≤ ~15–20 dòng logic thực (service-orchestrator rule).

---

## 9. Bảo mật

- Chỉ owner đọc/ghi session theo `user_id`.
- Retrieve chỉ scope skill đang request (không nhận skill_id lạ trong body).
- Không tool call / browsing.
- Không expose debug UI cho learner.

---

## 10. Map báo cáo lab

| Đề lab | EnglishFlow Lesson Q&A |
|--------|-------------------------|
| Embeddings data thật | PDF → Voyage → `book_chunks` |
| Vector DB | Mongo |
| RAG pipeline | query → retrieve → LLM (surface mới) |
| Memory + RAG hybrid | Window + retrieved block |
| Redis cache | Retrieval cache |
| Demo “không hallucinate” | Prompt + empty-context rule |
| Docker + FastAPI | Stack hiện có |

Tutor RAG vẫn là surface role-play; **Lesson Q&A** là surface demo “hỏi bài / hỏi sách” rõ ràng hơn cho lab.

---

## 11. Spec self-review

- [x] Không placeholder TBD mơ hồ về approach (A đã chốt)
- [x] Tách bảng khỏi tutor — không mâu thuẫn tutor RAG spec
- [x] Scope skill_units + `should_retrieve` (default retrieve) nhất quán, khác Tutor `needs_rag`
- [x] CEFR từ profile + cite learner-facing
- [x] Suggested prompt chips (3–5, tap = send, deterministic từ skill/pack)
- [x] UI collapsible đã chốt
- [x] Flow RAG → prompt → LLM explicit (kèm ví dụ prompt)
- [x] Scope đủ một plan triển khai; P1 lesson-pack fallback ngoài v1
- [x] Không nhét supermarket chatbot

---

## Changelog

| Date | Note |
|------|------|
| 2026-08-05 | Draft: Lesson Q&A dưới bài học, reuse tutor_rag, approach A |
| 2026-08-05 | Accepted: CEFR bắt buộc, cite learner-facing, làm rõ `should_retrieve` |
| 2026-08-05 | Add suggested question chips (tap-to-send) |
| 2026-08-05 | UI: FAB góc phải; chỉ hiện lúc learn (ẩn practice) |
| 2026-08-05 | Remove product Debug toggle from Lesson Q&A UI |
