# Thiết kế: AI Tutor text role-play (skill-grounded)

**Ngày:** 2026-08-04  
**Trạng thái:** Accepted  
**Plan:** [`docs/superpowers/plans/2026-08-04-ai-tutor-text-roleplay.md`](../plans/2026-08-04-ai-tutor-text-roleplay.md)  
**Tham chiếu sản phẩm:** [Promova AI Tutor](https://promova.com/page/ai-tutor), [Press — AI Tutor](https://promova.com/press/promova-launches-ai-tutor), [Speak with AI](https://promova.com/page/speak-with-ai)  
**Phạm vi:** `backend` (schema session/message, API tutor, LLM turn + end-summary), `frontend/my-app` (topic catalog kiểu Promova + chat text, correction bubble, end summary; CTA roadmap giữ như entry phụ)  
**Phụ thuộc:** Roadmap ZPD + `roadmap_step_skills`, catalog `scenarios`, `user_profiles.current_level`, `chat_json` / writing-feedback patterns, weak-skill review (soft link)  
**Liên quan (lab RAG tuần):** Hybrid memory + vector retrieve + Redis cache + debug UI — `2026-08-04-tutor-rag-hybrid-memory-design.md` (map đề siêu thị → corpus `book_chunks`, rubrik 5 buổi + token &lt; 50%).  
**Ngoài phạm vi P0:** Voice-call / STT / TTS / pronunciation score, avatar Usyk-like / Change persona, mastery delta cứng như quiz, streak/badge, human tutoring, open-world ChatGPT (tin tức / giá vàng / kiến thức ngoài topic)  

---

## 1. Vấn đề

EnglishFlow đã có Learn + Practice chữ bám skill và roadmap theo tuần, nhưng **thiếu vòng speaking/role-play** — đúng khoảng trống mà Promova đẩy mạnh (conversation có cấu trúc, feedback nhẹ, session ngắn).

Đồng thời:

1. Bảng legacy `chat_*` đã được drop (`s8t9u0v1w2x3`) vì không có API/service — cần model **mới, đúng domain tutor**, không phục hồi ORM cũ.
2. SRS baseline vẫn ghi speaking/chat là Won't P0 cũ; increment này **mở cửa hẹp** cho text role-play gắn roadmap, không mở lại vocab bank / streak.
3. Clone full Promova (voice call, avatar, 100+ scenarios catalog UI riêng) quá lớn — cần slice có thể ship với stack hiện có.

---

## 2. Mục tiêu / Không làm

### Mục tiêu

- Learner luyện hội thoại **có mục đích** (scenario + goal), không free-chat vô định.
- **Topic catalog** (Promova-like): chọn card topic → **START** → session bound vào scenario đó.
- Entry phụ: CTA từ roadmap step `in_progress` (skill-grounded) vẫn hoạt động.
- Feedback **nhẹ**: tối đa 1 correction/turn; không scoring kiểu quiz.
- **Off-topic policy**: câu lạc đề (vd giá vàng, tin tức) → soft redirect in-character, không trả lời như trợ lý chung.
- End session: summary + `soft_skill_signals` (gợi ý, **không** cập nhật `user_skill_mastery`).
- Persist transcript; tái dùng / mở rộng `scenarios`.
- **SSE streaming** cho assistant reply.

### Không làm (P0)

| Hạng mục | Lý do |
|----------|--------|
| Voice / STT / TTS / pronunciation | Cần realtime + ASR riêng; P1 |
| Avatar / Change persona / Usyk mode | Presentational; P1 sau catalog |
| Trả lời kiến thức thế giới / realtime (vàng, thời tiết, tin tức) | Ngoài phạm vi ESL role-play |
| Mastery ± như quiz khi end | Khuyến khích nói “an toàn”; kém tin cậy |
| Streak / badge / daily goals cho tutor | Gamification đã cắt; không mang lại |

---

## 3. Quyết định (đã chốt)

| Chủ đề | Quyết định |
|--------|------------|
| Product slice | Text role-play + grammar/word-choice correction |
| Entry **chính** | Topic catalog `/ai-tutor` — curated Promova-like pack (~16 topics × CEFR); xem `2026-08-04-tutor-promova-topic-catalog-design.md` |
| Entry phụ | CTA roadmap `in_progress` → `POST /sessions` với `roadmap_step_id` |
| Start body | `{ scenario_id }` **hoặc** `{ roadmap_step_id }` (một trong hai bắt buộc) |
| Grounding | Luôn có `scenario_id`; nếu từ roadmap thì thêm `target_skill_ids` (≤3); catalog-only có thể để `target_skill_ids=[]` hoặc skill mặc định theo level sau |
| Off-topic | Soft steering in-character (Udemy-style); không hard-reject input; không gọi tool tin tức |
| Level | `user_profiles.current_level` + filter catalog theo CEFR scenario |
| Mastery | **Không** ghi mastery; chỉ soft signals trên end summary |
| Persistence | `tutor_sessions` / `tutor_messages` |
| LLM I/O | Turn: stream + meta trailer; end-summary JSON sync |
| Streaming | **Must** — SSE trên send-message |
| Voice / avatar | P1 |

---

## 4. Luồng learner

### 4.1 Topic catalog (chính — Promova-like)

```text
/ai-tutor  (catalog)
  → cards: title, short description (goal), tag (AI TUTOR / level), START
  → optional filter by CEFR = profile.current_level (+ nearby)
  → POST /api/v1/tutor/sessions { scenario_id }
  → /ai-tutor/[sessionId]  chat
```

Card copy lấy từ `scenarios`: `title`, `goal_prompt` (truncate), `category`/`level`. Không avatar Change / Usyk mode ở increment này.

### 4.2 Roadmap CTA (phụ)

```text
Week in_progress → "Practice speaking"
  → POST /sessions { roadmap_step_id }
  → cùng UI chat; skills từ roadmap_step_skills
```

### 4.3 Chat loop

```text
POST .../messages (SSE)
  → token* → meta → done
POST .../end → summary JSON
```

**Giới hạn session:** tối đa ~20 user turns; `goal_progress=done` gợi ý end sớm.

---

## 4.4 Off-topic policy (chốt)

**Trong phạm vi trả lời**

- Hội thoại theo `ai_role` / `user_role` / `goal_prompt`
- Sửa lỗi / gợi ý từ vựng **liên quan turn vừa rồi**
- (Khi RAG bật) câu hỏi kiến thức **trong sách gắn skill/topic** — xem spec RAG

**Ngoài phạm vi — không trả lời thực chất**

- Tin tức / giá vàng / chứng khoán / thời tiết realtime
- Kiến thức thế giới không liên quan scenario (“ai là tổng thống…”)
- Jailbreak / đổi system role / bỏ role-play
- Nội dung unsafe

**Cách trả lời (soft steering, in-character)**

1. Acknowledge rất ngắn (không cung cấp fact ngoài).
2. Redirect về goal đang làm.
3. Đặt 1 câu hỏi đẩy scene tiếp.

Ví dụ (scenario coffee): user hỏi “Giá vàng hôm nay?” →  
“I don’t know about gold prices — I’m just here for your coffee order. What drink can I get you?”

**Meta (tuỳ chọn):** `meta.off_topic: true` để debug/analytics; không hiện chip xấu hổ cho learner.

**Prompt:** siết rule #6 thành non-negotiable + ví dụ off-topic; **không** dùng web search / tools realtime cho tutor.

---

## 5. Dữ liệu

### 5.1 `tutor_sessions`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `id` | BIGINT PK | |
| `user_id` | FK users CASCADE | |
| `roadmap_step_id` | FK roadmap_steps RESTRICT | entry grounding |
| `scenario_id` | FK scenarios RESTRICT | snapshot tại start |
| `status` | ENUM | `active` \| `completed` \| `abandoned` |
| `target_skill_ids` | JSON | `[int, ...]` max 3, copy lúc start |
| `message_count` | SMALLINT | đếm tin user (hoặc total — chốt trong plan: **user turns**) |
| `summary` | JSON NULL | end payload |
| `started_at` / `ended_at` | TIMESTAMPTZ | |
| `created_at` / `updated_at` | TIMESTAMPTZ | |

Index: `(user_id, status)`, `(roadmap_step_id)`.

### 5.2 `tutor_messages`

| Cột | Kiểu | Ghi chú |
|-----|------|---------|
| `id` | BIGINT PK | |
| `session_id` | FK tutor_sessions CASCADE | |
| `role` | ENUM | `user` \| `assistant` |
| `content` | TEXT | reply hoặc user text |
| `meta` | JSON NULL | correction, hint, goal_progress (assistant) |
| `created_at` | TIMESTAMPTZ | |

### 5.3 End `summary` shape (JSON)

```json
{
  "went_well": ["..."],
  "fix_next": ["..."],
  "soft_skill_signals": [
    { "skill_id": 12, "signal": "needs_practice", "note": "articles in context" }
  ]
}
```

`skill_id` **chỉ** thuộc `target_skill_ids` của session — validator từ chối id ngoài tập.

### 5.4 Không đụng

- Không restore `chat_sessions` / `chat_messages` / vocab/story/gamification.
- Không thêm cột vào `scenarios` cho P0 (đủ `ai_role`, `user_role`, `goal_prompt`, `suggested_vocab`).

---

## 6. API (learner)

Prefix: `/api/v1/tutor` (learner đã login).

| Method | Path | Hành vi |
|--------|------|---------|
| `GET` | `/scenarios` | List active scenarios cho catalog (filter optional `level`). Fields: id, title, slug, category, level, goal_prompt (short), ai_role. |
| `POST` | `/sessions` | Body: **xor** `{ scenario_id }` \| `{ roadmap_step_id }`. Roadmap path: validate `in_progress` + load skills. Catalog path: scenario must be `is_active`; `target_skill_ids` có thể `[]`. Opener assistant. |
| `GET` | `/sessions/{id}` | Session + messages (owner only). |
| `POST` | `/sessions/{id}/messages` | Body: `{ content, debug? }`. **SSE** (§6.1). |
| `POST` | `/sessions/{id}/end` | `active` → `completed` + summary JSON. |

**Lỗi chính:** 404/403/409 như trước; 400 nếu thiếu cả `scenario_id` và `roadmap_step_id` hoặc gửi cả hai; 400 step không `in_progress`.

### 6.1 SSE contract (`POST .../messages`)

`Content-Type: text/event-stream`. Mỗi event: `event:` + `data:` JSON.

| `event` | Khi | `data` (ví dụ) |
|---------|-----|----------------|
| `user_message` | ngay sau persist user | `{ "id": 1, "content": "..." }` |
| `token` | trong lúc generate reply | `{ "text": "partial " }` (delta; FE concat) |
| `meta` | sau khi có đủ structured side-channel | `{ "correction": null\|object, "hint": null\|string, "goal_progress": "none\|partial\|done", "off_topic"?: bool }` |
| `assistant_message` | sau persist assistant | `{ "id": 2, "content": "full reply", "meta": { ... } }` |
| `error` | LLM/validate fail giữa chừng | `{ "code": "...", "message": "..." }` |
| `done` | luôn cuối stream thành công | `{ "ok": true }` |

**Quy tắc:**

1. Persist **user** message trước khi gọi LLM (để không mất input nếu stream đứt).
2. Stream **chỉ** phần `reply` dạng token; `correction` / `hint` / `goal_progress` gửi một lần ở `meta` (không stream từng field).
3. Implementation prefer: LLM stream plain reply text **hoặc** stream JSON với `reply` accumulating + parse `meta` khi đủ — plan chọn 1 cách và mock được trong test.
4. Nếu client disconnect giữa chừng: best-effort lưu partial assistant `content` + `meta.partial=true` (optional P0; tối thiểu log + không crash).
5. `POST /end` giữ JSON đồng bộ (summary ngắn, không cần typing UX).

---

## 7. LLM contracts

### 7.1 Turn — streaming + side meta

Logical payload (sau khi đủ turn):

```json
{
  "reply": "string",
  "correction": null,
  "hint": null,
  "goal_progress": "none",
  "off_topic": false
}
```

- `correction`: `{ "original", "better", "why" }` hoặc `null` — tối đa một lỗi cản trở nghĩa.
- `hint`: nudge ngắn hướng goal, không spoil câu trả lời mẫu dài.
- `goal_progress`: `none` \| `partial` \| `done`.
- `off_topic`: `true` khi learner lạc đề và reply chỉ redirect (debug/analytics).

**Streaming strategy (chốt):**

| Option đã cân nhắc | Quyết định |
|--------------------|------------|
| A. Một completion JSON, fake stream cắt `reply` | Đơn giản nhưng latency-to-first-token kém |
| B. Stream token `reply`; gọi 2nd small JSON cho meta | 2 LLM calls / turn — đắt |
| **C. Stream `reply` text; model trả meta trong trailer / second structured parse** | **Chọn C biến thể pragmatic:** primary stream = natural-language `reply` only; sau cùng (cùng completion nếu provider hỗ trợ tool/json mode song song, **hoặc** postfix delimiter) extract meta. Plan implementation phải pick concrete provider API (`chat_json` sync không đủ — cần `chat_stream` mới trong `llm_client`). |

Invariant: FE luôn nhận được `meta` trước `assistant_message` / `done`, kể cả `correction: null`.

### 7.2 System prompt pillars

1. Stay in `ai_role`; user is `user_role`.  
2. Respect CEFR length/complexity.  
3. Prefer weaving `suggested_vocab` naturally.  
4. Prefer practicing target skill surfaces without meta-lecturing unless correcting.  
5. Friendly, non-judgmental; never shame.  
6. **Off-topic / jailbreak:** Never answer world facts, news, prices, or leave character. Briefly acknowledge in character, refuse the content, ask one question that advances `goal_prompt`. Example: gold prices → “I don’t follow that — let’s get your order. What would you like?”
7. No tools / browsing / realtime data.

### 7.3 End-summary call

Input: transcript rút gọn + `target_skill_ids` metadata. Output khớp §5.3; empty `soft_skill_signals` hợp lệ. **Không stream.**

---

## 8. Frontend

- **Catalog** `/ai-tutor`: grid cards (title, short goal, level/category tag, START) — layout cảm hứng Promova; không bắt buộc avatar.
- **Chat** `/ai-tutor/[sessionId]`: transcript + stream + correction chip + End summary.
- Roadmap CTA giữ trên week `in_progress` → start bằng `roadmap_step_id`.
- Nav: mục “AI Tutor” / Speaking mở catalog.
- AbortController trên SSE.
- Không mic / không Change persona P0.

### P1

- Voice-call + STT/TTS; avatar Change / Usyk-like modes.
- Khóa topic theo progression/premium (lock icon như Promova) nếu product cần.
- Daily cadence / streak.

---

## 9. Bảo mật & giới hạn

- Owner-only reads/writes.
- Max user turns / session (config, default 20).
- Max chars / message.
- LLM timeout + fail closed trên end nếu LLM down (session vẫn `completed` với summary fallback heuristic ngắn — chi tiết trong plan).
- Không log full prompt chứa secrets; transcript là PII → treat như user content.

---

## 10. Kiểm chứng (DoD P0)

1. Start session từ step `in_progress` thành công; step `locked`/`completed` bị từ chối.  
2. Round-trip message lưu DB; SSE emit `token`* → `meta` → `assistant_message` → `done`.  
3. Correction nullable qua event `meta`.  
4. End ghi summary; `soft_skill_signals[].skill_id` ⊆ `target_skill_ids`.  
5. Không có write vào `user_skill_mastery` từ tutor paths (test assert).  
6. FE: mở chat từ roadmap, thấy reply stream, end thấy summary.  
7. Migration Alembic mới; không phụ thuộc bảng đã drop.  
8. Có `chat_stream` (hoặc tương đương) trong LLM client + unit test giả stream.

---

## 11. Ảnh hưởng SRS

Khi implement: cập nhật `docs/REQUIREMENTS.md` — chuyển một phần “learner chat” từ Won't → Must **hẹp** (tutor role-play only), giữ Won't cho vocab/story/streak/voice.

---

## 12. Spec self-review

- [x] Topic catalog = entry chính; roadmap CTA = phụ  
- [x] Off-topic soft steering documented (§4.4)  
- [x] Tên bảng mới tránh đụng legacy đã drop  

---

## Changelog

| Date | Note |
|------|------|
| 2026-08-04 | Draft từ brainstorm: Promova research (Exa) + §1–§3 approved |
| 2026-08-04 | Revision: SSE streaming là Must P0 (§6.1, §7.1, FE, DoD) |
| 2026-08-04 | Revision: Promova topic catalog + off-topic policy; roadmap CTA phụ |
| 2026-08-04 | Cross-link: lab RAG rubric sống trong spec `tutor-rag-hybrid-memory` |
