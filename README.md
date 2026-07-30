# EnglishFlow

Nền tảng học tiếng Anh theo lộ trình cá nhân hóa (CEFR A1–C1): khảo sát → placement (nếu cần) → roadmap skill → Learn / Practice.

Admin nuôi hệ thống bằng sách PDF: upload → detect cấu trúc → index → sync skill → sinh & publish quiz/lesson.

> Học viên **không** học theo từng cuốn sách. Sách là nguồn nguyên liệu; đơn vị học & đánh giá là **skill theo CEFR**.

Chi tiết nghiệp vụ: [`docs/BUSINESS.md`](docs/BUSINESS.md)

---

## Tech stack

| Layer | Công nghệ |
|-------|-----------|
| Frontend | Next.js (App Router), React, Tailwind |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Data | PostgreSQL, Redis, MongoDB |
| Storage / AI | Supabase Storage, OpenAI, Voyage embeddings |
| Dev | Docker Compose, Nginx (proxy) |

---

## Cấu trúc repo

```text
.
├── backend/              # FastAPI API + migrations + tests
├── frontend/my-app/      # Next.js learner + admin UI
├── nginx/                # Reverse proxy (API + FE)
├── docs/                 # Nghiệp vụ, convention, design notes
├── docker-compose.yml
└── README.md             # File này
```

| Đường dẫn | Mô tả |
|-----------|--------|
| [`backend/`](backend/) | API, DB, services — xem [`backend/README.md`](backend/README.md) |
| [`frontend/my-app/`](frontend/my-app/) | UI — xem [`frontend/my-app/README.md`](frontend/my-app/README.md) |
| [`docs/BUSINESS.md`](docs/BUSINESS.md) | Flow learner + pipeline sách → skill |
| [`docs/CONVENTION.md`](docs/CONVENTION.md) | Quy ước code |
| [`docs/GITFLOW.md`](docs/GITFLOW.md) | Git workflow |

---

## Prerequisites

- Docker + Docker Compose
- (Tuỳ chọn local không Docker) Python 3.11+, Node.js 20+

---

## Quick Start (Docker)

1. Tạo env (chưa có file mẫu trong repo — copy từ máy đã setup hoặc tạo mới):

```bash
# Backend — đặt tại backend/.env
# Frontend — đặt tại frontend/my-app/.env.local
```

Biến quan trọng xem mục [Environment](#environment) bên dưới và chi tiết trong README từng app.

2. Chạy toàn bộ stack:

```bash
docker compose up --build
```

3. Mở:

| Service | URL |
|---------|-----|
| Frontend (trực tiếp) | http://localhost:3000 |
| API (trực tiếp) | http://localhost:8001 |
| API docs (Swagger) | http://localhost:8001/docs |
| Nginx (FE + `/api/`) | http://localhost:81 |
| Postgres | `localhost:5431` |
| Redis | `localhost:6381` |
| Mongo | `localhost:27018` |

Health check API: `GET /ping`

---

## Environment

### Backend (`backend/.env`)

Bắt buộc theo `app/core/config.py` (không commit secret):

- App / JWT: `APP_NAME`, `DEBUG`, `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`
- Postgres: `SQLALCHEMY_DATABASE_URL` (+ `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` cho container)
- Redis: `REDIS_HOST`, `REDIS_PORT`
- CORS: `FRONTEND_URL`
- Mongo: `MONGODB_URL`, `MONGODB_DB_NAME`
- Supabase books: `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` hoặc `SUPABASE_SECRET_KEY`
- AI: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, `VOYAGE_API_KEY`

Tuỳ chọn: `LEARN_UNIT_ENABLED` (bật bước Learn mini-unit).

### Frontend (`frontend/my-app/.env.local`)

- `NEXT_PUBLIC_API_URL` — ví dụ `http://localhost:8001` (hoặc qua nginx)
- `API_URL` — URL API phía server (thường giống trên trong Docker)
- `NEXT_PUBLIC_APP_URL` — ví dụ `http://localhost:3000`
- `NEXT_PUBLIC_ACCESS_TOKEN_EXPIRE_MINUTES`, `NEXT_PUBLIC_REFRESH_TOKEN_EXPIRE_DAYS`

---

## Hai phía sản phẩm (tóm tắt)

| Phía | Luồng chính |
|------|-------------|
| **Learner** | Đăng ký → survey → (placement Reading+Writing) → roadmap → Learn / Practice theo skill |
| **Admin** | Upload sách → Ready → sync skill → generate & publish quiz/lesson |

Pipeline sách (một dòng):

```text
Upload PDF → detect unit → index chunks → Ready
  → sync skills → generate quiz/lesson → publish → learner dùng
```

---

## Tài liệu thêm

- Nghiệp vụ đầy đủ: [`docs/BUSINESS.md`](docs/BUSINESS.md)
- Backend setup (venv, Alembic, pytest): [`backend/README.md`](backend/README.md)
- Frontend setup: [`frontend/my-app/README.md`](frontend/my-app/README.md)
