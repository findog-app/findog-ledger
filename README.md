# Findog Ledger

Private multi-user system for managing payment obligations, based on the FastAPI full-stack template.

## Current Scope

- Public signup is disabled completely.
- Users are created and managed only by a superuser/admin.
- Login, current-user, password reset, and password change flows remain available.
- Demo `Item` backend/frontend code has been removed.
- Users can create ledgers and share them with other users as owners, editors, or viewers.
- Ledgers include category groups and categories, including their recurrence and payment settings.
- Payment obligations are created for recurring categories and tracked in the ledger data model.
- Counterparty management and external integration/synchronization are not implemented yet.

## Stack

- FastAPI + SQLModel backend
- PostgreSQL database
- React + Vite frontend
- generated OpenAPI client in `frontend/src/client`
- Alembic migrations
- `uv` for backend dependency and command workflow
- Bun for frontend dependency and command workflow

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
