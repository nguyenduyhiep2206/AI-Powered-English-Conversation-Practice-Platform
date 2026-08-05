"""Admin HTTP smoke: lesson publish gate + skill_drill quiz gen/publish.

Mints a JWT for a temporary admin smoke user (role=admin) and hits the same
HTTP endpoints the admin UI uses. Prints structural JSON only.

  docker compose exec -T api \\
    python -m scripts.admin_skill_drill_smoke --skill-id 229 --book-id 43

Optional LLM lesson regen (slow): omit --skip-lesson-llm
"""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

import httpx
from sqlalchemy import insert, select

from app.core.database import AsyncSessionLocal
from app.models.auth import RoleDB, user_roles_table
from app.models.user import UserDB
from app.utils.jwt_handler import create_access_token
from app.utils.password_hash import get_password_hash

SMOKE_EMAIL = "admin.smoke@example.com"
SMOKE_PASSWORD = "AdminSmoke123!"
SMOKE_USERNAME = "admin_smoke"


async def _ensure_smoke_admin() -> int:
    async with AsyncSessionLocal() as db:
        user = (
            await db.execute(select(UserDB).where(UserDB.email == SMOKE_EMAIL))
        ).scalar_one_or_none()
        if user is None:
            user = UserDB(
                email=SMOKE_EMAIL,
                username=SMOKE_USERNAME,
                password_hash=get_password_hash(SMOKE_PASSWORD),
                full_name="Admin Smoke",
                is_active=True,
            )
            db.add(user)
            await db.flush()
        else:
            user.password_hash = get_password_hash(SMOKE_PASSWORD)
            user.is_active = True

        role = (
            await db.execute(select(RoleDB).where(RoleDB.name == "admin"))
        ).scalar_one_or_none()
        if role is None:
            raise SystemExit("Role 'admin' not found — seed roles first")

        existing = (
            await db.execute(
                select(user_roles_table.c.user_id).where(
                    user_roles_table.c.user_id == user.id,
                    user_roles_table.c.role_id == role.id,
                )
            )
        ).first()
        if existing is None:
            await db.execute(
                insert(user_roles_table).values(user_id=user.id, role_id=role.id)
            )

        await db.commit()
        return int(user.id)


def _auth_headers(user_id: int) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def _request(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    headers: dict[str, str],
    body: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    res = await client.request(method, path, headers=headers, json=body)
    try:
        data = res.json()
    except Exception:
        data = {"raw": (res.text or "")[:500]}
    return res.status_code, data


async def main(skill_id: int, book_id: int, count: int, skip_lesson_llm: bool) -> None:
    user_id = await _ensure_smoke_admin()
    headers = _auth_headers(user_id)
    summary: dict[str, Any] = {"skill_id": skill_id, "book_id": book_id}

    async with httpx.AsyncClient(base_url="http://127.0.0.1:8001", timeout=180.0) as client:
        # Prove auth works
        code, data = await _request(client, "GET", "/api/v1/admin/lessons/skills", headers)
        summary["list_lessons_status"] = code
        if code >= 400:
            summary["list_lessons_error"] = data
            print(json.dumps(summary, indent=2, default=str))
            raise SystemExit(1)

        if not skip_lesson_llm:
            code, data = await _request(
                client,
                "POST",
                f"/api/v1/admin/lessons/skills/{skill_id}/generate",
                headers,
            )
            summary["lesson_generate_status"] = code
            if code >= 400:
                summary["lesson_generate_error"] = data
            else:
                lesson = data.get("data") if isinstance(data, dict) else {}
                content = (lesson or {}).get("content") or {}
                form = content.get("form") or {}
                summary["lesson_draft"] = {
                    "status": (lesson or {}).get("status"),
                    "has_form": bool(form),
                    "form_rows": len(form.get("rows") or []),
                    "has_hook": bool(content.get("hook")),
                    "n_targets": len(content.get("targets") or []),
                }

        code, data = await _request(
            client,
            "POST",
            f"/api/v1/admin/lessons/skills/{skill_id}/publish",
            headers,
        )
        summary["lesson_publish_status"] = code
        if code >= 400:
            summary["lesson_publish_error"] = data
        else:
            lesson = data.get("data") if isinstance(data, dict) else {}
            content = (lesson or {}).get("content") or {}
            form = content.get("form") or {}
            summary["lesson_published"] = {
                "status": (lesson or {}).get("status"),
                "has_form": bool(form),
                "form_rows": len(form.get("rows") or []),
            }

        code, data = await _request(
            client,
            "POST",
            f"/api/v1/admin/quiz/skills/{skill_id}/generate",
            headers,
            {"count": count, "mode": "skill_drill"},
        )
        summary["quiz_generate_status"] = code
        rows: list[dict[str, Any]] = []
        if code >= 400:
            summary["quiz_generate_error"] = data
        else:
            raw = data.get("data") if isinstance(data, dict) else []
            rows = [r for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []
            summary["quiz_drafts"] = {
                "n": len(rows),
                "types": [r.get("question_type") for r in rows],
                "modes": [(r.get("task_brief") or {}).get("mode") for r in rows],
                "item_kinds": [
                    (r.get("task_brief") or {}).get("item_kind") for r in rows
                ],
            }

        ids = [int(r["id"]) for r in rows if r.get("id") is not None]
        if ids:
            code, data = await _request(
                client,
                "POST",
                "/api/v1/admin/quiz/questions/publish",
                headers,
                {"question_ids": ids},
            )
            summary["quiz_publish_status"] = code
            summary["quiz_publish"] = (
                data.get("data") if isinstance(data, dict) else data
            )

    print(json.dumps(summary, indent=2, default=str))
    print(
        json.dumps(
            {
                "playwright_login": {
                    "identifier": SMOKE_EMAIL,
                    "password": SMOKE_PASSWORD,
                }
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-id", type=int, default=229)
    parser.add_argument("--book-id", type=int, default=43)
    parser.add_argument("--count", type=int, default=6)
    parser.add_argument(
        "--skip-lesson-llm",
        action="store_true",
        help="Skip LLM lesson generate; publish existing + gen skill_drill quiz",
    )
    args = parser.parse_args()
    asyncio.run(main(args.skill_id, args.book_id, args.count, args.skip_lesson_llm))
