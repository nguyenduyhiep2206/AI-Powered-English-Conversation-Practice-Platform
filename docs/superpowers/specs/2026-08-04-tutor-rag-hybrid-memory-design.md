# Thiết kế: Tutor RAG + Hybrid Memory (book_chunks)

**Ngày:** 2026-08-04  
**Trạng thái:** Accepted  
**Plan:** `docs/superpowers/plans/2026-08-04-tutor-rag-hybrid-memory.md`  
**Phụ thuộc:** AI Tutor text role-play (`2026-08-04-ai-tutor-text-roleplay-design.md` — **topic catalog + off-topic policy**), Mongo `book_chunks` + Voyage embeddings, Redis, `book_skill_sources`  
**Map bài lab:** RAG / chunk-embed-store / RetrievalQA / Memory+RAG / Docker+cache+debug — corpus = sách đã index (thay CSV siêu thị)  

---

## 1. Vấn đề

Tutor text-only gửi scenario + skill titles + transcript → LLM. Hội thoại dài và hỏi kiến thức sách dễ:

1. Phồng token (full history / nhồi unit text).
2. Hallucinate grammar/vocab ngoài sách.
3. Không tận dụng pipeline index đã có (`book_chunks.embedding`).
4. Entry catalog (Promova-like) làm rõ **topic bound** — RAG chỉ hợp lệ trong topic/sách liên quan, không phải open Q&A thế giới.

Bài lab yêu cầu RAG + hybrid memory + Redis cache + debug — mở rộng tutor, không chatbot siêu thị riêng.

---

## 2. Mục tiêu / Không làm

### Mục tiêu

- Khi learner **hỏi kiến thức / giải thích từ sách** trong topic: retrieve Top-K chunks từ Mongo (scope theo skill nếu có).
- Hội thoại dài: **windowed memory**.
- Token hybrid **&lt; 50%** baseline full context (fixture test).
- Redis cache retrieval cho câu hỏi lặp **trong nhánh RAG**.
- Debug mode FE + SSE `debug`.
- Tôn trọng **off-topic policy** của tutor: tin tức/giá vàng **không** retrieve.

### Không làm

- Chroma / FAISS / OpenAI embeddings mới (Mongo + Voyage tương đương đề).
- CSV siêu thị; web search realtime.
- RAG cho mọi câu chào / small-talk trong scene.
- Avatar / voice.

---

## 3. Quyết định

| Chủ đề | Quyết định |
|--------|------------|
| Surface | Cùng session SSE tutor; catalog hoặc roadmap đều vào một chat UI |
| Off-topic trước RAG | Nếu off-topic (giá vàng, news…) → **không** retrieve; prompt redirect-only |
| Khi nào RAG | `needs_rag` **và** không off-topic **và** có scope chunks |
| Corpus | `book_chunks` embedded; ưu tiên unit gắn `target_skill_ids` |
| Embed / retrieve | Voyage + cosine in-process |
| Memory | Opener + last N turns |
| Cache | Redis retrieval payload only |
| Debug | `debug=true` → event `debug` |
| Token test | hybrid ≤ 0.5 × baseline |

---

## 4. Luồng turn

```text
POST .../messages { content, debug? }
  → persist user
  → memory_window
  → if is_off_topic(content):
        retrieved = none; route = off_topic
     elif TUTOR_RAG_ENABLED and needs_rag(content) and has_scope:
        retrieve (+ redis) → retrieved; route = rag
     else:
        route = roleplay
  → stream with system prompt (+ retrieved block if any)
  → meta (off_topic?)
  → debug event?
  → done
```

---

## 5. Retrieve scope

**Có `target_skill_ids` (từ roadmap):**  
`book_skill_sources` → `(book_id, unit_id)` → chunks embedded → cosine Top-K.

**Catalog-only (`target_skill_ids` rỗng):**  
P0: **skip RAG** (role-play thuần) trừ khi `TUTOR_RAG_CATALOG_LEVEL_FALLBACK=true` (mặc định **false**).

Không có chunk → `retrieval_empty`; vẫn role-play.

---

## 6. API / config

Giống tutor API; message body `debug?: bool`.

```text
TUTOR_RAG_ENABLED: bool = True
TUTOR_RAG_TOP_K: int = 4
TUTOR_RAG_MIN_SCORE: float = 0.25
TUTOR_RAG_MAX_CHARS: int = 2500
TUTOR_MEMORY_MAX_TURNS: int = 6
TUTOR_RAG_CACHE_TTL_SECONDS: int = 3600
TUTOR_RAG_ALWAYS_LIGHT: bool = False
TUTOR_RAG_CATALOG_LEVEL_FALLBACK: bool = False
```

---

## 7. Frontend

- Catalog `/ai-tutor` (cards START) — xem tutor role-play spec.
- Chat: Debug toggle + panel (`route`: roleplay|rag|off_topic, chunks, cache, tokens).
- Off-topic: AI redirect in-character; debug hiện `route=off_topic`.

---

## 8. Đo token &lt; 50%

Baseline = full transcript + full unit pack text.  
Hybrid = memory window + Top-K.  
Fixture cố định trong pytest.

---

## 9. Bảo mật

- Không retrieve ngoài scope skill/unit.
- Không tool call tin tức.
- Debug owner-only.

---

## 10. Map báo cáo lab

| Đề | EnglishFlow |
|----|-------------|
| Embeddings data thật | PDF → Voyage |
| Vector DB | Mongo `book_chunks` |
| RAG pipeline | `tutor_rag` |
| Memory hybrid | Window |
| Token &lt; 50% | Test §8 |
| Redis | Retrieval cache |
| Debug UI | Panel |
| Topic bound | Catalog Promova-like + off-topic |

---

## 11. Spec self-review

- [x] Catalog + off-topic gắn với RAG gating  
- [x] Catalog-only RAG default off  
- [x] Không supermarket / Chroma bắt buộc  

---

## Changelog

| Date | Note |
|------|------|
| 2026-08-04 | Draft: adapt lab RAG vào tutor + book_chunks |
| 2026-08-04 | Add topic catalog UX + off-topic gate before retrieve |
