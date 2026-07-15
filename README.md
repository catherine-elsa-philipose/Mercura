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
| **Customers** | | | |
| POST | `/businesses/{bid}/customers` | Yes (OWNER, MANAGER, STAFF) | Create customer |
| GET | `/businesses/{bid}/customers` | Yes | List/search customers (paginated) |
| GET | `/businesses/{bid}/customers/{cid}` | Yes | Get customer by ID |
| PATCH | `/businesses/{bid}/customers/{cid}` | Yes (OWNER, MANAGER, STAFF) | Update customer details |
| PATCH | `/businesses/{bid}/customers/{cid}/deactivate` | Yes (OWNER, MANAGER) | Deactivate customer |
| **Products** | | | |
| POST | `/businesses/{bid}/products` | Yes (OWNER, MANAGER) | Create product |
| GET | `/businesses/{bid}/products` | Yes | List/search products (paginated) |
| GET | `/businesses/{bid}/products/low-stock` | Yes | List low-stock products (paginated) |
| GET | `/businesses/{bid}/products/{pid}` | Yes | Get product by ID |
| PATCH | `/businesses/{bid}/products/{pid}` | Yes (OWNER, MANAGER, STAFF) | Update product details |
| PATCH | `/businesses/{bid}/products/{pid}/deactivate` | Yes (OWNER, MANAGER) | Deactivate product |
| POST | `/businesses/{bid}/products/{pid}/stock` | Yes (OWNER, MANAGER, STAFF) | Record stock adjustment (updates stock atomically) |
| GET | `/businesses/{bid}/products/{pid}/stock` | Yes | List stock adjustment history (paginated) |

## Security Design
- Membership access is backend-enforced. Non-members receive `404 Not Found` to prevent business existence leakage.
- Business creation is atomic: Business + OWNER membership are committed together or rolled back together.
- Roles are checked server-side only. Frontend role display is never trusted.

## Current Status
- **Phase 3**: Authentication Foundation — complete and verified.
- **Phase 4**: Business Workspaces and Membership Foundation — complete and verified.
- **Phase 5**: Customers Module — complete and verified.
- **Phase 6**: Products & Inventory Module — complete and verified.
- **Migrations applied**: All migrations up to `stock_adjustments` table are live in Neon PostgreSQL.
- **Tests**: 78 passed, 4 skipped (DB integration tests blocked without isolated schema).

## Note
Phase 4, 5, and 6 establish the core multi-tenant data structures, customer records, and product/inventory tracking. Billing and payment data isolation across tenants is planned for future phases.

