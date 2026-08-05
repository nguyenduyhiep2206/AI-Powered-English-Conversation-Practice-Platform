# Thiết kế: AI Tutor goal × CEFR topic catalog (curated)

**Ngày:** 2026-08-04  
**Trạng thái:** Draft — chờ review  
**Plan:** `docs/superpowers/plans/2026-08-04-tutor-promova-topic-catalog.md`  
**Phụ thuộc:** AI Tutor text role-play, tutor RAG, `scenarios` seed, `GOAL_TO_CATEGORY` / `GoalEnum`, weak-skill review  
**Tham chiếu sản phẩm (Exa research):**  
- [Busuu Conversations](https://www.busuu.com/en/languages/language-learning-with-busuu-conversations) — Speak tab + conversation gắn lesson; **level CEFR**; topic theo life/work/travel  
- [Promova AI Tutor / Features](https://promova.com/page/promova-features) — role-play; **topics based on goals** (work, travel, culture, relationships); CEFR courses A1–C1  
- [Promova Speak with AI](https://promova.com/page/speak-with-ai) — tình huống thật (interview, airport, groceries…)  
- [Duolingo Video Call / content pipeline](https://blog.duolingo.com/ai-and-video-call/) + offline/online split — content **curated offline**, serve-time = rank/adapt CEFR, không LLM sinh catalog lúc mở app  
- Pearson GSE / workplace tracks — cùng theme, **mức khó theo level**  
- ESL speaking topic banks — A1 concrete (family, food, routine); B1+ opinion/abstract  

---

## 1. Vấn đề

Pack “copy 16 card Promova” + chỉ sort theo goal **chưa đủ**: learner goal=work vẫn thấy Animals / Clothes ngang hàng Coffee nếu chỉ reorder nhẹ. Industry thực tế:

| Pattern | Ý nghĩa cho EnglishFlow |
|---------|-------------------------|
| Busuu | Catalog Speak **có thể tập trung work**; đồng thời entry gắn lesson vừa học |
| Promova | Onboarding goal → personalize; AI Tutor topics **theo goals**; track Travel / Business riêng |
| Duolingo | **Không** generate topic list online; CEFR + purpose trong prompt; memory/facts cá nhân hóa lượt chat |
| ESL banks | **Topic set khác nhau theo CEFR** (không chỉ đổi tone cùng 16 title) |

Vậy catalog cần **filter/composition theo goal + CEFR**, không chỉ list tĩnh giống screenshot.

---

## 2. Mục tiêu / Không làm

### Mục tiêu

- Curated seed (không AI sinh 12 scenario / user).
- **CEFR:** topic có `min_level` / `max_level` (eligibility), không clone mù 16×5 nếu A1 không phù hợp “negotiate remote politics”.
- **Goal:** mỗi topic có `goal_tags`; catalog mặc định = **Primary for your goal** + optional **Explore more**.
- **Skill path:** Recommended từ weak skills / linked slugs (Busuu “from lesson”).
- Roadmap `pick_scenario` vẫn pick active + category.

### Không làm (P0)

- LLM generate catalog per user  
- Cover image / long-session badge  
- Full admin CRUD UI  
- Sentiment-adaptive / Duolingo-style fact memory (P1 chat, không phải catalog)

---

## 3. Quyết định (đã chỉnh sau Exa)

| Chủ đề | Quyết định |
|--------|------------|
| Nguồn | Curated seed offline (Duolingo-style split) |
| Promova list | Dùng làm **corpus ví dụ**, không hard-wire 1:1 làm toàn catalog mọi goal |
| Composition | Seed **topic bank** (~24–32 base) tagged bởi goal + CEFR range; runtime **compose ~10–16 cards** cho user |
| CEFR | `min_cefr` / `max_cefr` trên template; row materialize chỉ trong range (hoặc seed mọi level nhưng `is_active` theo range) |
| Goal UX | Default tab/section: topics có `goal_tags` chứa goal learner; section 2: Explore (còn lại cùng level) |
| Personalize rank | Trong Primary: weak-skill hits → order_index; Explore: weaker ranking |
| Skill link | `linked_skill_slugs` optional; START resolve ≤3 ids |
| Legacy 4-slug | Deactivate như trước |

---

## 4. Map GoalEnum → goal_tags

EnglishFlow `GoalEnum` → tags trên topic (multi-tag OK):

| GoalEnum | Primary tags | Gợi ý topic clusters |
|----------|--------------|----------------------|
| `job_interview` / work-like (`work` nếu có) | `work` | interview, arrange meeting, sick leave, office small talk, email oral |
| `travel` | `travel` | hotel, airport/plane, groceries, around town, coffee/restaurant, directions |
| `daily_conversation` | `daily` | home, morning, family, food, clothes, neighbour |
| `family` (nếu survey) | `daily`, `social` | family describe, plans with family |
| `culture` | `social`, `daily` | small talk, animals/pets, clothes, food culture |
| `school` | `study`, `daily` | morning routine, arrange study meet, not feeling well |
| `challenge` / `other` | `daily`, `social` | balanced daily + social |

`GOAL_TO_CATEGORY` giữ cho **roadmap assembler**; catalog dùng `goal_tags` phong phú hơn 4 `ScenarioCategoryEnum`.

Category enum (roadmap) vẫn gán mỗi topic: `job_interview` | `travel` | `small_talk` | `custom` để assembler không gãy.

---

## 5. Topic bank (mẫu — không phải “chỉ đúng list Promova”)

### 5.1 Core pool (gộp Promova list + lỗ hổng theo goal)

Mỗi dòng: `base_slug`, title, blurb, `goal_tags`, `category`, `min_cefr`–`max_cefr`.

**Travel-leaning**

| base | title | tags | CEFR |
|------|-------|------|------|
| hotel-check-in | Hotel check-in | travel | A1–B2 |
| coffee-dialogue | Coffee dialogue | travel, daily | A1–B1 |
| around-town | Around town | travel, daily | A1–B1 |
| plane-small-talk | Small talk on the plane | travel, social | A2–B2 |
| buying-groceries | Buying groceries | travel, daily | A1–B1 |
| airport-problem | Delayed flight / lost bag (P0 optional) | travel | A2–B2 |

**Work-leaning**

| base | title | tags | CEFR |
|------|-------|------|------|
| job-interview-basics | Job interview basics | work | A2–C1 |
| arrange-meeting | Arrange a meeting | work | A2–B2 |
| not-feeling-well | Not feeling well (tell manager) | work | A2–B1 |
| workplace-small-talk | Small talk with a colleague | work, social | A2–B2 |

**Daily / social**

| base | title | tags | CEFR |
|------|-------|------|------|
| things-at-home | Things at home | daily | A1–A2 |
| food-and-drinks | Food and drinks | daily | A1–A2 |
| my-morning | My morning | daily | A1–A2 |
| my-family | My family | daily, social | A1–A2 |
| telling-family | Telling about your family | daily, social | A1–B1 |
| clothes-colors | What are you wearing? | daily | A1–A2 |
| broken-ac | A broken air conditioner | daily | A2–B1 |
| animals-around-us | Animals around us | daily, social | A1–A2 |
| meeting-neighbour | Meeting a new neighbour | social, daily | A1–A2 |

### 5.2 Quy tắc materialize theo CEFR

- Chỉ tạo row `scenarios` cho level L nếu `min_cefr ≤ L ≤ max_cefr`.
- Tone/`goal_prompt` vẫn theo `_LEVEL_TONE[L]` (clone trong range).
- Hệ quả: A1 catalog **không** gồm “Job interview basics” nếu min=A2; C1 **không** chỉ thấy “Things at home” nếu max=A2 — đúng hướng ESL banks.

### 5.3 Compose runtime (~10–16 cards)

```text
level = profile.current_level
goal  = profile.goal → primary_tags

candidates = active scenarios WHERE level == L

primary = filter(candidates, goal_tags ∩ primary_tags ≠ ∅)
explore = candidates − primary

sort primary by (weak_skill_hits DESC, order_index)
sort explore by order_index

return primary (cap 12) + explore (cap 6)   # FE: 2 sections
# Nếu primary < 6: backfill từ explore cùng category map
```

`recommended = true` nếu trong primary **và** (weak hit > 0 hoặc rank ≤ 3).

---

## 6. Schema

```text
scenarios.linked_skill_slugs  JSON null   # ["articles-a1", ...]
scenarios.theme_tags          JSON null   # ["home","food"] chips P1
scenarios.goal_tags           JSON null   # ["travel","work","daily","social","study"]
# min/max CEFR: encode via seed only creating in-range rows; optional columns later
```

Migration: 3 JSON columns (goal_tags bắt buộc cho pack mới).

---

## 7. API / service

`GET /api/v1/tutor/scenarios`:

- Query optional `section` không cần P0 — trả flat list **đã sắp** + field `section: "primary" | "explore"` và `recommended`.
- Logic compose §5.3.
- Không trả topic ngoài CEFR (không có row).

`POST /sessions` `{ scenario_id }`: resolve `linked_skill_slugs` → ≤3 ids.

Roadmap: không đổi; `pick_scenario` dùng category + active.

---

## 8. Frontend `/ai-tutor`

Hai khối (Promova/Busuu-inspired):

1. **For your goal** — `section=primary` (copy theo goal: “For work”, “For travel”…).  
2. **More topics** — `explore`.

Card: title, description, level, Recommended badge. Không ảnh P0.

---

## 9. Seed / ops

```bash
python -m app.seeds.scenarios
```

- Upsert theo `slug = f"{base}-{level}"` chỉ khi level in range.  
- Deactivate legacy: `small_talk-*`, `job_interview-*`, `travel-*`, `custom-*` (4 template cũ).  
- Đảm bảo mỗi CEFR vẫn có ≥1 active / mỗi `ScenarioCategoryEnum` cần cho assembler.

---

## 10. Spec self-review

- [x] Không còn “copy nguyên list Promova cho mọi user”  
- [x] Goal = filter composition, không chỉ sort nhẹ  
- [x] CEFR = eligibility range + tone, không clone mù  
- [x] Vẫn curated / offline (Busuu+Duolingo pattern)  
- [x] Exa citations trong header  

---

## Changelog

| Date | Note |
|------|------|
| 2026-08-04 | Draft v1: Promova list + sort only |
| 2026-08-04 | **v2 (Exa):** goal_tags + CEFR ranges + primary/explore compose; Promova list = corpus không phải single hard catalog |
