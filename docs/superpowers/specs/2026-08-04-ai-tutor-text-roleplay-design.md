# Thiết kế: AI Tutor text role-play (skill-grounded)

**Ngày:** 2026-08-04  
**Trạng thái:** Accepted — ready for implementation  
**Plan:** `docs/superpowers/plans/2026-08-04-ai-tutor-text-roleplay.md`  
**Tham chiếu sản phẩm:** [Promova AI Tutor](https://promova.com/page/ai-tutor), [Press — AI Tutor](https://promova.com/press/promova-launches-ai-tutor), [Speak with AI](https://promova.com/page/speak-with-ai)  
**Phạm vi:** `backend` (schema session/message, API tutor, LLM turn + end-summary), `frontend/my-app` (CTA roadmap → trang chat text, correction bubble, end summary)  
**Phụ thuộc:** Roadmap ZPD + `roadmap_step_skills`, catalog `scenarios`, `user_profiles.current_level`, `chat_json` / writing-feedback patterns, weak-skill review (soft link)  
**Ngoài phạm vi P0:** Voice-call / STT / TTS / pronunciation score, avatar, free-chat tab độc lập, mastery delta cứng như quiz, streak/badge, human tutoring  

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
- Session **grounded** vào roadmap step đang `in_progress` + 1–3 skill target của step.
- Feedback **nhẹ**: tối đa 1 correction/turn; không scoring kiểu quiz.
- End session: summary + `soft_skill_signals` (gợi ý, **không** cập nhật `user_skill_mastery`).
- Persist transcript để resume / audit; tái dùng `scenarios` hiện có.
- **SSE streaming** cho assistant reply để UX gần chat realtime (Promova-like feel trên text).

### Không làm (P0)

| Hạng mục | Lý do |
|----------|--------|
| Voice / STT / TTS / pronunciation | Cần realtime + ASR riêng; P1 |
| Avatar / “feels like a call” UI | Presentational; sau khi core chat ổn |
| Tab AI Tutor catalog độc lập | Dễ lệch path học; P1 entry phụ |
| Mastery ± như quiz khi end | Khuyến khích nói “an toàn”; kém tin cậy |
| Streak / badge / daily goals cho tutor | Gamification đã cắt; không mang lại |

---

## 3. Quyết định (đã chốt)

| Chủ đề | Quyết định |
|--------|------------|
| Product slice | Text role-play + grammar/word-choice correction |
| Entry | CTA từ roadmap step `in_progress` → start session |
| Grounding | `scenario` của step + target skills từ `roadmap_step_skills` |
| Level | `user_profiles.current_level` (A1–C1) điều khiển độ dài/complexity prompt |
| Mastery | **Không** ghi mastery; chỉ soft signals trên end summary |
| Persistence | Bảng mới `tutor_sessions` / `tutor_messages` (không tái dùng tên `chat_*`) |
| LLM I/O | Turn: stream text + meta JSON cuối turn; end-summary vẫn 1-shot structured JSON |
| Streaming | **Must P0** — SSE trên send-message |
| Voice roadmap | Ghi P1 trong §8; không block P0 |

---

## 4. Luồng learner

```text
Dashboard roadmap
  → Step in_progress → CTA "Practice speaking"
  → POST /tutor/sessions { roadmap_step_id }
  → UI /dashboard/ai-tutor/[sessionId]
       loop:
         user types message
         POST .../messages (Accept: text/event-stream)
           → SSE: token deltas của reply, rồi event `meta` (correction/hint/goal_progress), rồi `done`
       End:
         POST .../end → summary + soft_skill_signals (JSON, không stream)
         → modal; optional link Weak skills review
```

**Giới hạn session:** tối đa ~20 message turns (user+assistant pairs config), hoặc `goal_progress=done` gợi ý end sớm. Session `abandoned` nếu idle quá lâu (job/cron optional P0.5; P0 có thể chỉ client-end).

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

Prefix gợi ý: `/api/tutor` (permission learner đã login).

| Method | Path | Hành vi |
|--------|------|---------|
| `POST` | `/sessions` | Body: `{ roadmap_step_id }`. Validate step thuộc user progress `in_progress`. Resolve scenario + target skills. Tạo session `active`. Optionally seed 1 assistant opener. |
| `GET` | `/sessions/{id}` | Session + messages (owner only). |
| `POST` | `/sessions/{id}/messages` | Body: `{ content }`. **SSE stream** (xem §6.1). Append user msg trước stream; append assistant sau khi stream xong (hoặc partial + error flag). |
| `POST` | `/sessions/{id}/end` | Chỉ `active` → `completed`; 1 LLM summary call (JSON); persist `summary`. Không SSE. |

**Lỗi chính:** 404 session, 403 không owner, 409 session không `active`, 400 step không `in_progress` / quá message limit, 502 LLM fail (không mất user message đã lưu — retry policy trong plan).

### 6.1 SSE contract (`POST .../messages`)

`Content-Type: text/event-stream`. Mỗi event: `event:` + `data:` JSON.

| `event` | Khi | `data` (ví dụ) |
|---------|-----|----------------|
| `user_message` | ngay sau persist user | `{ "id": 1, "content": "..." }` |
| `token` | trong lúc generate reply | `{ "text": "partial " }` (delta; FE concat) |
| `meta` | sau khi có đủ structured side-channel | `{ "correction": null\|object, "hint": null\|string, "goal_progress": "none\|partial\|done" }` |
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
  "goal_progress": "none"
}
```

- `correction`: `{ "original", "better", "why" }` hoặc `null` — tối đa một lỗi cản trở nghĩa.
- `hint`: nudge ngắn hướng goal, không spoil câu trả lời mẫu dài.
- `goal_progress`: `none` \| `partial` \| `done`.

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
6. Refuse jailbreak / out-of-scenario unsafe content briefly then redirect.

### 7.3 End-summary call

Input: transcript rút gọn + `target_skill_ids` metadata. Output khớp §5.3; empty `soft_skill_signals` hợp lệ. **Không stream.**

---

## 8. Frontend

- CTA trên step/WeekNode khi `in_progress` (copy English product UI theo app hiện tại).
- Route: `/dashboard/tutor/[sessionId]`.
- UI: transcript, text input, **render token stream** vào bubble assistant đang gõ, rồi gắn correction chip khi `meta` tới; nút End → modal summary.
- AbortController: Cancel dừng đọc SSE (server best-effort).
- Nếu có soft signals → deep-link tới weak-skills review hiện có (nếu surface đã có); không block nếu thiếu.
- Không avatar, không mic P0.

### P1 (ghi nhận — không implement trong plan P0)

- Voice-call UX + STT/TTS + pronunciation tips (Promova-like).
- Tab catalog scenarios độc lập + daily cadence.
- Optional soft mastery hint channel (vẫn không hard delta nếu chưa có calibration).

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

- [x] Không còn placeholder TBD cho quyết định P0 cốt lõi  
- [x] Không mâu thuẫn §2 vs §3 (mastery soft-only)  
- [x] Scope một slice; full Promova deferred §8  
- [x] Tên bảng mới tránh đụng legacy đã drop  
- [ ] Plan + tests chi tiết — thuộc `writing-plans` sau approve  

---

## Changelog

| Date | Note |
|------|------|
| 2026-08-04 | Draft từ brainstorm: Promova research (Exa) + §1–§3 approved |
| 2026-08-04 | Revision: SSE streaming là Must P0 (§6.1, §7.1, FE, DoD) |
