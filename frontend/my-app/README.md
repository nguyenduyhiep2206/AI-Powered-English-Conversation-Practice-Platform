# Frontend — EnglishFlow (Next.js)

UI learner (dashboard, onboarding, placement, practice) và admin (sách, quiz, lessons).

Root repo: [../../README.md](../../README.md) · Backend API: [../../backend/README.md](../../backend/README.md)

---

## Stack

- Next.js 16 (App Router), React 19, TypeScript
- Tailwind CSS 4, shadcn/ui (Radix)

---

## Cấu trúc chính

```text
frontend/my-app/
├── src/app/            # Routes (dashboard, onboarding, admin, login…)
├── components/         # UI dùng chung (AppHeader, lesson, admin…)
├── lib/                # API clients, auth helpers
├── public/
├── package.json
├── Dockerfile.dev
└── .env.local          # Không commit
```

---

## Prerequisites

- Node.js 20+
- Backend API đang chạy (mặc định `http://localhost:8001`) — xem backend README hoặc `docker compose up api`

---

## Setup

```bash
cd frontend/my-app
npm install
```

Tạo `.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8001
API_URL=http://localhost:8001
NEXT_PUBLIC_APP_URL=http://localhost:3000
NEXT_PUBLIC_ACCESS_TOKEN_EXPIRE_MINUTES=30
NEXT_PUBLIC_REFRESH_TOKEN_EXPIRE_DAYS=7
```

Trong Docker Compose, FE dùng `frontend/my-app/.env.local` qua `env_file`.

---

## Chạy dev

```bash
npm run dev
```

Mở http://localhost:3000

Scripts khác:

```bash
npm run build
npm run start
npm run lint
```

---

## Docker

Từ root repo:

```bash
docker compose up --build frontend
# hoặc full stack:
docker compose up --build
```

Nginx (port `81`) proxy `/` → frontend, `/api/` → API.

---

## Ghi chú

- Client gọi API qua `NEXT_PUBLIC_API_URL` (`lib/api.ts`).
- Server components / middleware có thể dùng `API_URL` hoặc `NEXT_PUBLIC_API_URL`.
- Nghiệp vụ sản phẩm: [../../docs/BUSINESS.md](../../docs/BUSINESS.md)
