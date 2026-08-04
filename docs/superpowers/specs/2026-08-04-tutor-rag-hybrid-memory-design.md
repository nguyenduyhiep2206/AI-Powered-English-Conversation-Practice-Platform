# Thiết kế: Tutor RAG + Hybrid Memory (book_chunks)

**Ngày:** 2026-08-04  
**Trạng thái:** Draft — chờ review  
**Plan:** `docs/superpowers/plans/2026-08-04-tutor-rag-hybrid-memory.md`  
**Phụ thuộc:** AI Tutor text role-play P0 (`2026-08-04-ai-tutor-text-roleplay-design.md`), Mongo `book_chunks` + Voyage embeddings, Redis, `book_skill_sources`  
**Map bài lab:** RAG / chunk-embed-store / RetrievalQA / Memory+RAG / Docker+cache+debug — corpus = sách đã index (thay CSV siêu thị)  

---

## 1. Vấn đề

Tutor P0 chỉ gửi scenario + skill titles + transcript → LLM. Hội thoại dài và hỏi kiến thức sách dễ:

1. Phồng token (full history / nhồi unit text).
2. Hallucinate grammar/vocab ngoài sách.
3. Không tận dụng pipeline index đã có (`book_chunks.embedding`).

Bài lab yêu cầu RAG + hybrid memory + Redis cache + debug — phù hợp mở rộng tutor, không làm chatbot siêu thị riêng.

---

## 2. Mục tiêu / Không làm

### Mục tiêu

- Khi learner **hỏi kiến thức / giải thích từ sách** (hoặc bật “grounded”): retrieve Top-K chunks từ Mongo gắn skill tuần hiện tại → inject vào prompt.
- Hội thoại dài: **windowed memory** (opener + N turn gần ± optional rolling summary) — không gửi full transcript.
- Token estimate (prompt chars / approx tokens) **&lt; 50%** so với baseline “full transcript + full unit pack” trên cùng fixture hội thoại dài (đo trong test/script).
- Redis cache cho câu hỏi lặp (normalize query → cached answer + retrieval meta).
- Debug mode FE: hiện retrieved chunks, scores, memory window, cache hit, token estimate.
- Config: `TOP_K`, similarity threshold, max inject chars.

### Không làm

- Chroma / FAISS / OpenAI embeddings mới (tương đương: Mongo + Voyage đã có; ghi rõ trong báo cáo lab).
- CSV siêu thị.
- Voice / đổi mastery từ RAG.
- Atlas `$vectorSearch` bắt buộc trên máy local (tùy môi trường): mặc định **in-process cosine** trên subset đã filter theo `book_id`/`unit_id`; nếu Atlas có sẵn thì có thể swap adapter sau.

---

## 3. Quyết định

| Chủ đề | Quyết định |
|--------|------------|
| Surface | Mở rộng AI Tutor (cùng session SSE) |
| Khi nào RAG | Heuristic router: câu hỏi kiến thức / chứa keyword giải thích / `?` + skill terms; **hoặc** luôn retrieve nhẹ Top-K=2 nếu `TUTOR_RAG_ALWAYS_LIGHT` |
| Corpus | `book_chunks` `embed_status=embedded` của unit gắn `target_skill_ids` qua `book_skill_sources` |
| Embed query | `embedding_service.embed_texts([query])` (Voyage) |
| Retrieve | Filter by book/unit ids → cosine similarity → Top-K, drop dưới `TUTOR_RAG_MIN_SCORE` |
| Memory | Opener + last `TUTOR_MEMORY_MAX_TURNS` user/assistant pairs; strip meta from history |
| Hybrid prompt | system = roleplay rules + **Retrieved context** block + CEFR/skills; user = windowed transcript |
| Cache | Redis key `tutor:rag:{hash(normalized_q + skill_ids + lang)}` TTL cấu hình; chỉ cache nhánh “Q&A grounded”, không cache pure small-talk |
| Debug | SSE event `debug` (chỉ khi `debug=true` trên POST message) + FE panel |
| Baseline đo token | Script/test: `estimate_tokens(full)` vs `estimate_tokens(hybrid)` |

---

## 4. Luồng turn (cập nhật)

```text
POST .../messages { content, debug? }
  → persist user
  → build memory_window from transcript
  → route = needs_rag(content)?
       yes → embed query → retrieve → (redis get/set) → context_block
       no  → context_block empty
  → system = build_turn_system_prompt(..., retrieved=context_block)
  → stream reply + meta
  → if debug: emit event "debug" { route, cache_hit, chunks[], memory_chars, prompt_chars, approx_tokens }
  → done
```

Pure role-play (greeting, “yes”, short replies) skip RAG để giữ latency/cost.

---

## 5. Retrieve scope

Cho session với `target_skill_ids`:

1. Query `book_skill_sources` → tập `(book_id, unit_id)` primary/attached.
2. Load Mongo chunks: `book_id ∈ …`, `unit_id ∈ …` (hoặc unit slug), `embed_status=embedded`, projection `{text, embedding, book_id, unit_id, chunk_id}`.
3. Nếu không có chunk: fallback không RAG + hint debug `retrieval_empty`.
4. Cosine(query_vec, chunk.embedding); giữ score ≥ threshold; Top-K; truncate tổng text ≤ `TUTOR_RAG_MAX_CHARS`.

---

## 6. API / SSE bổ sung

- `POST /sessions/{id}/messages` body thêm optional `debug: bool` (default false).
- Event mới: `debug` (chỉ khi debug) — **sau** `meta` hoặc trước `done`, không lẫn vào transcript persist.
- Không đổi schema bảng Postgres bắt buộc; optional JSON `meta.debug` trên assistant message nếu muốn audit (P0: chỉ SSE).

Config (`config.py`):

```text
TUTOR_RAG_ENABLED: bool = True
TUTOR_RAG_TOP_K: int = 4
TUTOR_RAG_MIN_SCORE: float = 0.25
TUTOR_RAG_MAX_CHARS: int = 2500
TUTOR_MEMORY_MAX_TURNS: int = 6
TUTOR_RAG_CACHE_TTL_SECONDS: int = 3600
TUTOR_RAG_ALWAYS_LIGHT: bool = False
```

---

## 7. Frontend

- Toggle **Debug** trên trang tutor → gửi `debug: true`.
- Panel phụ: list chunk (score, unit, snippet), cache hit badge, memory window size, approx tokens.
- Không hiện debug mặc định cho learner thường.

---

## 8. Đo “giảm &lt; 50% token”

Fixture hội thoại dài (vd 15 turns) + 1 câu hỏi grounded:

| Mode | Prompt composition |
|------|-------------------|
| Baseline | Full transcript + pack toàn bộ unit text (như “tuần 6 full context”) |
| Hybrid | Memory window + Top-K chunks |

`approx_tokens = ceil(chars / 4)` đủ cho lab; log cả hai trong debug/script. Acceptance: hybrid ≤ 0.5 × baseline trên fixture cố định trong test.

---

## 9. Bảo mật

- Retrieve chỉ chunks thuộc sách đã gắn skill session (không mở all books).
- Debug chỉ owner session.
- Cache key không chứa raw PII ngoài query đã normalize; TTL ngắn.

---

## 10. Map báo cáo lab (nộp thầy)

| Yêu cầu đề | Chứng minh trong EnglishFlow |
|------------|------------------------------|
| Embeddings từ data thật | PDF → chunks → Voyage (pipeline sẵn) |
| Vector DB | Mongo `book_chunks.embedding` |
| RAG pipeline | `tutor_rag.py` retrieve + inject |
| Memory hybrid | Windowed transcript |
| Token &lt; 50% | Test/script §8 |
| Redis cache | Hit trên câu hỏi lặp |
| Debug UI | Tutor debug panel |
| Docker | compose hiện có |

Ghi chú ethodology: “OpenAI Embedding/Chroma trong slide ≡ Voyage/Mongo trong hệ thống production của nhóm.”

---

## 11. Spec self-review

- [x] Không TBD quyết định P0  
- [x] Tách khỏi supermarket CSV  
- [x] Không phá tutor P0 khi `TUTOR_RAG_ENABLED=false`  
- [ ] Plan task chi tiết — file plan kèm theo  

---

## Changelog

| Date | Note |
|------|------|
| 2026-08-04 | Draft: adapt lab RAG vào tutor + book_chunks |
