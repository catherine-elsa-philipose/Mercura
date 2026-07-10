# Mercura Project
# 
# Phase 4: Business Workspaces and Membership Foundation

## Stack
- Frontend: Flutter (Web), Dart, Material 3
- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic, PyJWT, pwdlib[argon2]
- Database: PostgreSQL (Driver: psycopg)

## Concept

### Business Workspaces
A **Business** represents an independent workspace owned by a user account. Examples include "Fresh Mart" or "City Bakery."

### Business Membership
A **BusinessMember** is the join between a User and a Business. Roles belong to the membership, not the User:

```
User A + Fresh Mart = OWNER
User A + City Bakery = STAFF
```

This means one user can belong to multiple workspaces with different roles.

### Roles
- `OWNER` — The creator. Full permissions within the workspace.
- `MANAGER` — Elevated access (future scope).
- `STAFF` — Standard access (future scope).

Role values are validated by Python enum and by a database-level CHECK constraint `ck_business_members_role_valid`.

## Project Structure
- `/backend`: FastAPI backend with SQLAlchemy ORM and Alembic migrations
- `/frontend`: Flutter Web frontend
- `/docs`: Architecture and internship documentation

## Local Setup

### Backend Setup
```bash
cd backend
.venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Configuration
```bash
copy .env.example .env
python scripts/setup_env.py   # generates SECRET_KEY
# edit .env to add DATABASE_URL
```

### Database Migrations
```bash
alembic upgrade head
```

### Running the Server
```bash
uvicorn app.main:app --reload
```
API: http://127.0.0.1:8000  
Docs: http://127.0.0.1:8000/docs

### Running Tests
```bash
python -m pytest tests -v
```

### Frontend
```bash
cd frontend
flutter pub get
flutter run -d chrome
```

## API Endpoints
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Health ping |
| GET | `/health` | No | Service status |
| POST | `/auth/register` | No | Register user |
| POST | `/auth/login` | No | Login, receive JWT |
| GET | `/auth/me` | Yes | Current user profile |
| POST | `/businesses` | Yes | Create workspace (creator → OWNER) |
| GET | `/businesses` | Yes | List caller's memberships |
| GET | `/businesses/{id}` | Yes | Get workspace (member-only) |

## Security Design
- Membership access is backend-enforced. Non-members receive `404 Not Found` to prevent business existence leakage.
- Business creation is atomic: Business + OWNER membership are committed together or rolled back together.
- Roles are checked server-side only. Frontend role display is never trusted.

## Current Status
- **Phase 3**: Authentication Foundation — complete and verified.
- **Phase 4**: Business Workspaces and Membership Foundation — complete and verified.
- **Migrations applied**: `users`, `businesses`, `business_members` tables are live in Neon PostgreSQL.
- **Tests**: 28 passed, 2 skipped (DB integration tests blocked without isolated schema).

## Note
Phase 4 establishes the workspace and membership foundation for future multi-tenancy. Customer, product, inventory, billing, and payment data isolation across tenants does not exist yet — those modules are planned for future phases.

