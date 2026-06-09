<div align="center">

# ⚙️ StyleForge Backend

### FastAPI Microservices — The Brains Behind the Fashion

[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com/)
[![Ollama](https://img.shields.io/badge/Ollama-Qwen%203.5:9b-black?style=flat-square)](https://ollama.com/)
[![Alembic](https://img.shields.io/badge/Alembic-Migrations-6B5B95?style=flat-square)](https://alembic.sqlalchemy.org/)

</div>

---

## 📐 Architecture Overview

The backend is a **microservices system** with a single unified API gateway. Every client request — from the browser or mobile — enters through the gateway, which validates JWTs, enforces auth, and proxies requests to the appropriate downstream service.

```
Client (Next.js)
       │
       ▼
┌─────────────────────────────┐
│     Gateway  :8000          │  ← JWT validation, routing, OpenAPI
└──────┬──────────────────────┘
       │
  ┌────┴─────────────────────────────────────────┐
  │                                              │
  ▼        ▼         ▼         ▼        ▼       ▼
Auth    Catalog   Analytics  Audit   Orders   GenAI
:8001   :8002     :8004      :8005   :8003    :8006
  │        │         │         │        │       │
  └────────┴─────────┴─────────┴────────┴───────┘
                          │
                    PostgreSQL :5432
```

---

## 📂 Directory Structure

```
styleforge-backend/
│
├── gateway/            # 🚪 Unified entry point — routes all /api/v1/* traffic
├── auth/               # 🔐 Auth service: JWT, Google OAuth, OTP email login
├── catalog/            # 🗂️  Image catalog: upload, list, serve, quota enforcement
├── orders/             # 📦 Order lifecycle management
├── analytics/          # 📊 Event tracking, aggregated statistics
├── audit/              # 🔍 Structured audit log ingestion and search
├── genai/              # 🤖 AI service: Style Critique + Fabric Sim + Generation
│
├── common/             # Shared across all services
│   ├── models.py       # SQLAlchemy ORM models
│   ├── database.py     # Async DB session factory
│   ├── config.py       # Pydantic settings (reads .env)
│   └── audit_client.py # Fire-and-forget audit event helper
│
├── alembic/            # Database migration scripts
│   └── versions/       # Versioned migration files
│
├── tests/              # pytest test suite
├── docker-compose.yml  # Full-stack orchestration
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── run_all.py          # Local dev: spin up all services
├── Makefile            # Convenience commands
└── API_REFERENCE.md    # Full endpoint documentation
```

---

## 🚀 Getting Started

### Option A — Docker Compose (Recommended)

The fastest way to run the entire backend stack.

```bash
# 1. Copy and configure environment
cp .env.example .env
# Open .env and fill in JWT_SECRET, Google OAuth, SMTP, Ollama URL

# 2. Build and launch all services
docker compose up --build

# 3. Verify all containers are healthy
docker compose ps
```

Services will be available at:

| Service | URL |
|---------|-----|
| **API Gateway + Swagger UI** | http://localhost:8000/docs |
| PostgreSQL | `localhost:5432` |

### Option B — Local Development

Requires Python 3.13 and a running PostgreSQL instance.

```bash
# 1. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env appropriately

# 4. Run database migrations
alembic upgrade head

# 5. Start all services (runs each on its own port)
python run_all.py
```

---

## 🔐 Authentication

All protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <your_jwt_token>
```

Obtain a token from:
- `POST /api/v1/auth/register` — email/password registration
- `POST /api/v1/auth/login` — email/password login
- `POST /api/v1/auth/otp/request` + `POST /api/v1/auth/otp/verify` — OTP email login
- `GET /api/v1/auth/google` — Google OAuth 2.0 redirect flow

The gateway injects `x-user-id` and `x-user-role` headers into downstream requests after validating the JWT — services trust these headers directly.

---

## 🤖 GenAI Service

The most feature-rich service. Two main capabilities:

### Style Critique (`POST /api/v1/genai/critique`)
- Accepts a multipart image upload
- Sends the image to **Ollama** running `qwen3.5:9b` locally
- Returns a structured **markdown critique** covering:
  - Core issues with the outfit
  - Aesthetic breakdown (color harmony, fit & silhouette, textures)
  - Actionable execution plan (garment swaps, tailoring tips, accessory refinements)
- **Costs 5 credits** per request
- Response persisted to `style_critiques` table

### Fabric Simulation (`POST /api/v1/genai/fabric-simulation`)
- Accepts fabric type, color, weight, and stiffness parameters
- Generates a simulated fabric render (base64 PNG)
- Result stored in `fabric_simulations` table
- **Costs 5 credits** per request

### Outfit Generation (`POST /api/v1/genai/generate`)
- Text-to-image generation via Colab/ComfyUI backend
- Requires `COLAB_URL` to point to your running inference server
- **Costs 10 credits** per request

---

## 🗄️ Database & Migrations

The database is managed by **SQLAlchemy 2.0** (async via `asyncpg`) with **Alembic** for migrations.

```bash
# Apply all pending migrations
alembic upgrade head

# Roll back one migration
alembic downgrade -1

# Generate a new migration (after editing models.py)
alembic revision --autogenerate -m "describe your change"

# Check current migration state
alembic current
```

### Key Tables

| Table | Description |
|-------|-------------|
| `users` | Accounts: email, hashed password, Google sub, role, credits |
| `otp_records` | Hashed OTPs with expiry for passwordless login |
| `images` | Uploaded and AI-generated images per user |
| `image_quota` | Daily quota tracker (date + count per user) |
| `style_critiques` | Persisted markdown critique responses |
| `fabric_simulations` | Fabric sim parameters + base64 render |
| `credit_transactions` | Full audit trail of credit deductions and top-ups |
| `analytics_events` | Service-level event tracking with JSON payload |
| `audit_logs` | Operational audit logs from all services |

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Database
POSTGRES_URL=postgresql+asyncpg://user:pass@localhost:5432/styleforge_db

# JWT
JWT_SECRET=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# OTP via Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password
SMTP_FROM="StyleForge <noreply@styleforge.com>"

# Ollama (Style Critique)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:9b
OLLAMA_TIMEOUT=420

# Long-running GenAI proxy/backend calls
GENAI_REQUEST_TIMEOUT=420

# Colab / ComfyUI (Outfit Generation)
COLAB_URL=https://your-ngrok-url.ngrok-free.dev

# Credit System
NEW_USER_CREDITS=100
STYLE_CRITIQUE_CREDITS=5
IMAGE_GENERATION_CREDITS=10
DAILY_IMAGE_QUOTA=5

# Microservice URLs (local dev)
AUTH_SERVICE_URL=http://localhost:8001
CATALOG_SERVICE_URL=http://localhost:8002
ORDERS_SERVICE_URL=http://localhost:8003
ANALYTICS_SERVICE_URL=http://localhost:8004
AUDIT_SERVICE_URL=http://localhost:8005
GENAI_SERVICE_URL=http://localhost:8006
```

---

## 🧪 Testing

```bash
# Run the full test suite
pytest

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_genai.py -v
pytest tests/test_auth.py -v
pytest tests/test_catalog.py -v

# Run with async support
pytest --asyncio-mode=auto
```

Test files live in `tests/` and use `pytest-asyncio` for async endpoint testing. A shared `conftest.py` sets up the test database and authentication fixtures.

---

## 📡 API Endpoints Summary

Full documentation is at **`http://localhost:8000/docs`** (Swagger UI) when the stack is running.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/api/v1/auth/register` | ❌ | Create a new account |
| `POST` | `/api/v1/auth/login` | ❌ | Login with email/password |
| `POST` | `/api/v1/auth/otp/request` | ❌ | Request OTP email |
| `POST` | `/api/v1/auth/otp/verify` | ❌ | Verify OTP and get token |
| `GET` | `/api/v1/auth/me` | ✅ | Get current user profile |
| `GET` | `/api/v1/catalog/images` | ✅ | List user's images |
| `POST` | `/api/v1/catalog/upload` | ✅ | Upload an image |
| `POST` | `/api/v1/genai/critique` | ✅ | AI style critique (5 credits) |
| `POST` | `/api/v1/genai/fabric-simulation` | ✅ | Fabric simulation (5 credits) |
| `POST` | `/api/v1/genai/generate` | ✅ | Outfit generation (10 credits) |
| `GET` | `/api/v1/analytics/events` | ✅ | Fetch analytics events |
| `GET` | `/api/v1/audit/logs` | ✅ Admin | Search audit logs |

See [`API_REFERENCE.md`](./API_REFERENCE.md) for the full reference.

---

## 🔧 Makefile Commands

```bash
make up        # docker compose up --build
make down      # docker compose down
make logs      # tail all service logs
make migrate   # alembic upgrade head
make test      # run pytest
```

---

## 🐛 Troubleshooting

**Database connection refused**
→ Ensure PostgreSQL is running and `POSTGRES_URL` is correct. In Docker, the gateway depends on the `db` service being healthy.

**Ollama not responding**
→ Make sure Ollama is running: `ollama serve` and the model is pulled: `ollama pull qwen3.5:9b`. Check `OLLAMA_BASE_URL`.

**Google OAuth not working**
→ Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` and that your OAuth app's redirect URI matches.

**Credits not deducting**
→ Ensure the user making the request has sufficient credits. Critique costs 5, generation costs 10. Top up via the admin endpoint.