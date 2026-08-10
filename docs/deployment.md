# Mercura Production Deployment Guide

This guide outlines the steps required to deploy the Mercura multi-tenant platform (FastAPI backend, Flutter Web frontend, and PostgreSQL database) to a production environment.

---

## 1. Architecture Overview

In a production environment, the platform is orchestrated as follows:

```
                            [ User Web Browser ]
                                     │
                                     ▼ HTTPS (Port 443)
                            [ Nginx Reverse Proxy ]
                                     │
                 ┌───────────────────┴───────────────────┐
                 ▼                                       ▼
        [ Flutter Web Build ]                    [ FastAPI Backend ]
        (Serves Static Files)                    (Uvicorn on Port 8000)
                                                         │
                                                         ▼
                                                [ PostgreSQL Database ]
                                                (Local or Neon Serverless)
```

- **Nginx:** Acts as a single entry point, serving the static compiled Flutter Web application and reverse-proxying API calls (from `/api/` path) to the FastAPI backend.
- **FastAPI:** Runs via the Uvicorn ASGI server.
- **PostgreSQL:** Neon PostgreSQL (cloud) is recommended for serverless scaling, but a standalone containerized instance can also be used.

---

## 2. Environment Variables

Configure the following variables in the backend environment (e.g., in a `.env` file or cloud dashboard):

| Variable | Description | Example / Default |
|----------|-------------|-------------------|
| `DATABASE_URL` | SQLAlchemy connection string for PostgreSQL | `postgresql+psycopg://user:pass@host:5432/db` |
| `SECRET_KEY` | Secret key used to sign JWT authentication tokens | *Generate a secure cryptographically random key* |
| `ALGORITHM` | JWT signing algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiration time for authentication tokens | `30` |
| `GEMINI_API_KEY` | API Key for Google GenAI AI Assistant (Optional) | *Your Gemini API Key* |

> [!WARNING]
> Never commit active production environment secrets to git. Always use environment variable inject mechanisms provided by your cloud hosting provider.

---

## 3. Docker Compose Deployment (Recommended)

Docker Compose provides the easiest way to launch the entire stack (Database, Backend, and Frontend) in an isolated local or server environment.

### Setup and Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/catherine-elsa-philipose/Mercura.git
   cd Mercura
   ```

2. **Configure environment:**
   Create a `.env` file in the root directory:
   ```bash
   # Generate a secure secret key
   python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))" > .env

   # Add your Gemini API Key for the AI assistant
   echo "GEMINI_API_KEY=your_gemini_api_key_here" >> .env
   ```

3. **Deploy using Docker Compose:**
   ```bash
   docker compose up -d --build
   ```

This command builds the optimized Python-slim backend and multi-stage Flutter Web images, spins up a local PostgreSQL database with a persistent volume, runs DB migrations automatically, and maps the Nginx HTTP server to port `8080` on the host machine.

### Verifying the Stack
- **Frontend App:** Navigate to `http://localhost:8080` in your browser.
- **FastAPI OpenAPI Documentation:** Navigate to `http://localhost:8080/api/docs`.
- **Database Connection:** Connect using any PostgreSQL client to `localhost:5432` with username `mercura_user` and database `mercura_db`.

---

## 4. Cloud Production Deployment (Standalone)

For high-availability and serverless scaling, deploy the components independently:

### A. Database (PostgreSQL)
- Provision a PostgreSQL database instance (e.g., AWS RDS, GCP Cloud SQL, or Neon Serverless PostgreSQL).
- Ensure the database schema is updated by running Alembic migrations:
  ```bash
  cd backend
  alembic upgrade head
  ```

### B. FastAPI Backend
- Deploy the backend container to a container runner (e.g., AWS ECS, GCP Cloud Run, or Azure Container Apps).
- Set the `DATABASE_URL` to point to your production database.
- Configure CPU/Memory scaling triggers (e.g. 50% CPU utilization).

### C. Flutter Web Frontend
- Build the web assets locally or in CI:
  ```bash
  cd frontend
  flutter build web --release --dart-define=API_BASE_URL=/api
  ```
- Upload the contents of the `frontend/build/web` directory to a static site host (e.g., AWS S3, Cloudflare Pages, Vercel, or Firebase Hosting).
- Set up an API gateway or CDN route to forward requests starting with `/api/` to the backend container.

---

## 5. Security Checklist

- [ ] **Enforce HTTPS:** Secure your reverse proxy with SSL/TLS certificates (e.g. using Let's Encrypt / Certbot).
- [ ] **Rotate Secret Keys:** Periodically rotate `SECRET_KEY` and database passwords.
- [ ] **CORS Settings:** In `backend/app/main.py`, restrict `allow_origins` to your production domain name instead of `["*"]`.
- [ ] **Gemini API Restrictions:** Limit your Google GenAI API Key to prevent unauthorized usage or over-billing.
