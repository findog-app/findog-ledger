# Findog Ledger

Private multi-user payment-obligation system based on the FastAPI full-stack template.

This repository is currently in the foundation phase. The template demo domain has been removed and the codebase is being prepared for the later implementation of:

- auth and user administration
- categories
- counterparties
- obligations
- integration status and sync event handling

## Current Scope

- Public signup is disabled completely.
- Users are created and managed only by a superuser/admin.
- Login, current-user, password reset, and password change flows remain available.
- Demo `Item` backend/frontend code has been removed.
- Backend structure now separates `api`, `core`, `models`, `schemas`, `repositories`, and `services`.
- Placeholder modules exist for the future payment-obligation bounded contexts without fake business logic.

## Stack

- FastAPI + SQLModel backend
- PostgreSQL database
- React + Vite frontend
- generated OpenAPI client in `frontend/src/client`
- Alembic migrations
- `uv` for backend dependency and command workflow

## Local Development

- Backend development uses `uv` from [`backend/`](./backend/README.md).
- The project currently targets an external PostgreSQL instance configured through `.env`.
- Docker Compose and local workflow details are in [`development.md`](./development.md).
- Frontend development notes are in [`frontend/README.md`](./frontend/README.md).

## User Management Rules

- Only existing users can log in.
- Only superusers can create users.
- Only superusers can list users.
- Only superusers can update other users, including activation/deactivation.
- Regular users can only manage their own profile/password endpoints.

## Migrations

- The demo `item` table is removed by Alembic migration `b1e4c8d5e2f1_remove_demo_item_domain`.
- Fresh databases should be created through Alembic, not through ad hoc table creation.

## Verification

Backend verification completed with:

```bash
cd backend
uv run pytest tests/api/routes tests/crud tests/scripts
```

Frontend build/codegen verification requires the Node workspace dependencies to be installed locally.
