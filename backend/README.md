# Backend — EnglishFlow API

FastAPI service: auth, onboarding/placement, roadmap, quiz, lessons, admin books/quiz/lessons.

Root repo README: [../README.md](../README.md) (Docker toàn stack). File này dành cho làm việc **trong `backend/`**.

---

## Stack

- Python 3.11, FastAPI, Uvicorn
- SQLAlchemy + Alembic (PostgreSQL)
- Redis (cache / session helpers)
- MongoDB (book chunks / indexing)
- Supabase Storage (PDF sách)
- OpenAI (quiz / lesson / writing), Voyage (embeddings)

---

## Cấu trúc thư mục

```text
backend/
├── main.py                 # FastAPI entry (`app`)
├── app/
│   ├── api/                # Routers (auth, onboarding, admin_*, quiz, skills…)
│   ├── core/               # config, DB, Redis, Mongo, security
│   ├── models/             # SQLAlchemy models
│   ├── schemas/            # Pydantic request/response
│   ├── repositories/       # Data access
│   ├── services/           # Business logic
│   ├── seeds/              # Seed helpers
│   └── utils/
├── alembic/                # Migrations
├── alembic.ini
├── scripts/                # One-off scripts (vd. seed placement)
├── tests/
├── requirements.txt
├── Dockerfile
└── .env                    # Local secrets (không commit)
```

---

## Prerequisites

- Python 3.11+
- Postgres, Redis, Mongo đang chạy (khuyến nghị: `docker compose up db redis mongo` từ root repo)
- File `backend/.env` đã điền đủ biến (xem [Environment](#environment))

---

## Admin ops flow

**Preferred Admin UI:** **Books** (upload → index) → **Attach** (`/admin/quiz`, sync catalog) → **Skills** workspace (lesson → skill_drill → publish).

- Generate/publish lesson and drills in **Skills workspace** (`/admin/skills/{id}`): `GET /api/v1/admin/skills/{id}/workspace`.
- Attach page is for catalog sync / re-enrich, not dual-path drill generate.
- Skills list badges: `GET /api/v1/admin/lessons/skills` includes `quiz_draft_count`, `quiz_published_count`, `has_book_source`.

### Learn lesson → Practice skill_drill

1. Publish a Learn lesson for the skill (grammar requires `form` with ≥2 rows).
2. `POST /api/v1/admin/quiz/skills/{skill_id}/generate` with body `{"count": 6}` — default `mode=skill_drill`.
3. Publish drafts: `POST /api/v1/admin/quiz/questions/publish` with `question_ids`. Misaligned skill_drill items are skipped (`skipped_alignment`).
4. For classic TOEIC Parts 5–7: pass `"mode": "toeic"` on generate.

Breaking note: generate defaults to `skill_drill` (not TOEIC). Use `mode=toeic` explicitly when needed.

---

## Setup local (không Docker API)

```bash
cd backend

python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

Đảm bảo `SQLALCHEMY_DATABASE_URL`, `REDIS_*`, `MONGODB_URL` trỏ đúng host/port khi chạy ngoài Compose.

Port map Compose mặc định:

| Service | Host port |
|---------|-----------|
| Postgres | `5431` → 5432 |
| Redis | `6381` → 6379 |
| Mongo | `27018` → 27017 |

---

## Environment

File: `backend/.env` (cùng thư mục với `main.py` khi chạy Uvicorn trong container/local).

Nhóm biến chính (từ `app/core/config.py`):

| Nhóm | Biến |
|------|------|
| App | `APP_NAME`, `DEBUG` |
| JWT | `SECRET_KEY`, `ALGORITHM` (mặc định HS256), `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS` |
| Postgres | `SQLALCHEMY_DATABASE_URL` (+ `POSTGRES_*` cho container DB) |
| Redis | `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `PERMISSION_CACHE_TTL_SECONDS` |
| CORS | `FRONTEND_URL` |
| Books | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` hoặc `SUPABASE_SECRET_KEY`, `SUPABASE_BOOK_BUCKET`, `MAX_BOOK_UPLOAD_MB` |
| Mongo | `MONGODB_URL`, `MONGODB_DB_NAME` |
| AI | `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, `VOYAGE_API_KEY` |
| Feature | `LEARN_UNIT_ENABLED` (Learn mini-unit; mặc định `false` trong code) |
| Lesson targets | `LEARN_LESSON_MIN_TARGETS` / `LEARN_LESSON_MAX_TARGETS` (mặc định `4` / `7`) |

Không commit `.env` chứa secret.

---

## Chạy server

```bash
cd backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

- API: http://localhost:8001  
- Swagger: http://localhost:8001/docs  
- Health: http://localhost:8001/ping  

Trong Docker Compose, service `api` đã dùng lệnh tương đương (port `8001`).

---

## Database migrations (Alembic)

Chạy **từ thư mục `backend/`**:

```bash
# Tạo revision mới (sau khi đổi models)
alembic revision --autogenerate -m "mô tả thay đổi"

# Áp dụng tới head
alembic upgrade head

# Xem lịch sử
alembic history
```

Trong container:

```bash
docker compose exec api alembic upgrade head
```

---

## Tests

```bash
cd backend
source venv/bin/activate
pytest
# hoặc một file:
pytest tests/test_lesson_service.py -q
```

Trong container:

```bash
docker compose exec api pytest
```

---

## Scripts hữu ích

```bash
# Ví dụ seed placement TOEIC (xem file để biết tham số / điều kiện)
python scripts/seed_toeic_placement.py
```

Chạy khi API + DB đã sẵn sàng và env hợp lệ.

---

## Chạy bằng Docker (chỉ backend + infra)

Từ **root repo**:

```bash
docker compose up --build db redis mongo api
```

Full stack (kèm FE + nginx): xem [root README](../README.md).

---

## Liên kết

- Nghiệp vụ (sách → skill → quiz/lesson): [../docs/BUSINESS.md](../docs/BUSINESS.md)
- Quy ước code: [../docs/CONVENTION.md](../docs/CONVENTION.md)
- Frontend: [../frontend/my-app/README.md](../frontend/my-app/README.md)
