![Python](https://img.shields.io/badge/Python-3.12-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-336791)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.x-red)
![Flutter](https://img.shields.io/badge/Flutter-Web-02569B)
![License](https://img.shields.io/badge/License-MIT-green)

# Mercura

## Current Version

**Version:** v0.6.0

**Status:** Completed through Phase 6 – Products & Inventory Foundation

---

## Project Overview

Mercura is a production-oriented multi-tenant Business Operations and Commerce Platform designed for small and medium-sized businesses.

It enables businesses to securely manage workspaces, employees, customers, products, inventory, and future billing operations while ensuring complete tenant isolation and role-based access control.

The backend is built with FastAPI, SQLAlchemy, Alembic, and PostgreSQL, while the frontend is being developed using Flutter Web.


## Features

### Authentication
- JWT Authentication
- Secure Password Hashing (Argon2)
- User Registration & Login
- Protected API Endpoints

### Multi-Tenant Business Management
- Business Workspaces
- Business Memberships
- Role-Based Access Control (OWNER, MANAGER, STAFF)
- Tenant Isolation

### Customer Management
- Customer CRUD Operations
- Customer Search
- Pagination
- Customer Soft Deactivation

### Product & Inventory Management
- Product CRUD Operations
- Product Search
- SKU & Barcode Support
- Inventory Tracking
- Stock Adjustment History
- Low Stock Detection
- Atomic Inventory Updates

### Developer Experience
- FastAPI Interactive Swagger UI
- SQLAlchemy ORM
- Alembic Database Migrations
- Unit Testing with Pytest
- PostgreSQL (Neon)

## Project Architecture
```
                    Mercura
                        │
        ┌───────────────┴────────────────┐
        │                                │
   Flutter Web Frontend          FastAPI Backend
                                         │
                          ┌──────────────┴──────────────┐
                          │                             │
                     SQLAlchemy ORM             Alembic Migrations
                          │
                    PostgreSQL (Neon)
```

The backend follows a layered architecture:

- **API Layer** – FastAPI routes and request handling
- **Schemas Layer** – Pydantic request/response validation
- **Models Layer** – SQLAlchemy ORM models
- **Database Layer** – PostgreSQL with Alembic migrations
- **Authentication Layer** – JWT + Role-Based Access Control

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

## Repository Structure
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

## Current Progress

| Phase | Status |
|-------|--------|
| Phase 0 – Planning | ✅ Complete |
| Phase 1 – Backend Foundation | ✅ Complete |
| Phase 2 – Authentication | ✅ Complete |
| Phase 3 – Business Workspace | ✅ Complete |
| Phase 4 – Business Foundation | ✅ Complete |
| Phase 5 – Customer Management | ✅ Complete |
| Phase 6 – Products & Inventory Foundation | ✅ Complete |
| Phase 7 – Billing & Payments | 🚧 Planned |
| Phase 8 – Dashboard & Analytics | 🚧 Planned |
| Phase 9 – Flutter + AI Business Assistant | 🚧 Planned |
| Phase 10 – Production & Deployment | 🚧 Planned |

### Phase 6 Summary

- ✅ Multi-tenant architecture implemented
- ✅ JWT Authentication & RBAC
- ✅ Business workspace management
- ✅ Customer management
- ✅ Product management
- ✅ Inventory tracking with stock adjustments
- ✅ Low-stock detection
- ✅ Alembic database migrations
- ✅ Swagger/OpenAPI documentation
- ✅ Backend test suite (78 passed, 4 skipped)
  ## Roadmap

### ✅ Completed
- Authentication
- Business Workspaces
- Customer Management
- Product Management
- Inventory Foundation

### 🚧 Next
- Billing & Payments

### 📅 Future
- Dashboard & Analytics
- Flutter Web Frontend
- AI Business Assistant
- Docker Deployment
- CI/CD Pipeline

## License

This project is licensed under the MIT License.
