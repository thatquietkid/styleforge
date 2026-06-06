<div align="center">

<img src="https://img.shields.io/badge/StyleForge-AI%20Fashion%20Platform-black?style=for-the-badge&logo=sparkles&logoColor=white" alt="StyleForge" height="50"/>

# ✨ StyleForge

### *Where Artificial Intelligence Meets High Fashion*

**An AI-powered fashion platform that critiques your outfits, simulates fabrics, and generates apparel designs — all from a single, beautifully crafted interface.**

<br/>

[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)

<br/>

[🚀 Get Started](#-quick-start) · [🧠 Features](#-features) · [🏗️ Architecture](#️-architecture) · [📡 API Docs](#-api-documentation) · [🤝 Contributing](#-contributing)

---

</div>

## 🌟 What is StyleForge?

StyleForge is a full-stack, AI-driven fashion platform built for the modern era. Upload an outfit photo and receive a **sharp, editorial-style critique** from an elite AI fashion director. Simulate fabric physics in real-time. Generate entirely new apparel concepts from text prompts. All powered by a robust **microservices backend** and a sleek **Next.js 16** frontend.

> *StyleForge turns AI into your personal Creative Director.*

---

## ✨ Features

### 🤖 AI-Powered Fashion Intelligence
- **Style Critique** — Upload an outfit image and receive a structured editorial breakdown: core issues, aesthetic analysis (color harmony, fit & silhouette, textures), and an actionable execution plan. Powered by **Ollama + Qwen 3.5:9b**.
- **Fabric Simulation** — Simulate how different fabrics (Silk, Velvet, Denim, etc.) drape and behave with real-time parameter controls (weight, stiffness, color). Results rendered and saved as base64 images.
- **Outfit Generation** — Generate entirely new apparel designs from text prompts via a Colab/ComfyUI inference backend.
- **Virtual Try-On** *(coming soon)* — See generated outfits on a model.

### 🔐 Authentication & Identity
- **JWT-based auth** with secure token management
- **Google OAuth 2.0** single sign-on
- **OTP email login** via SMTP (passwordless flow)
- Role-based access control: `user`, `tailor`, `admin`

### 💎 Credit System
- Every user starts with **100 free credits**
- Style Critique costs **5 credits** · Image Generation costs **10 credits**
- Full audit trail of all credit transactions

### 📊 Analytics & Audit
- Structured event tracking across all services
- Searchable audit log for debugging and compliance
- Per-user analytics dashboard

### 🗂️ Image Catalog
- Upload and manage your personal fashion images
- Daily quota system (configurable)
- Serves generated and uploaded images via static file hosting

---

## 🏗️ Architecture

StyleForge is built as a **microservices monorepo** with a unified API gateway as the single entry point.

```
Styleforge/
├── styleforge-frontend/        # Next.js 16 + React 19 + Tailwind v4
│   └── src/app/
│       ├── style-critique/     # AI outfit critique UI
│       ├── fabric-ai/          # Fabric simulation UI
│       ├── outfit-ai/          # Outfit generation UI
│       ├── profile/            # User dashboard & credits
│       ├── login/ register/    # Auth flows (JWT, Google, OTP)
│       └── ...
│
└── styleforge-backend/         # Python FastAPI microservices
    ├── gateway/                # 🚪 Unified API Gateway (port 8000)
    ├── auth/                   # 🔐 Auth service (port 8001)
    ├── catalog/                # 🗂️  Image catalog (port 8002)
    ├── orders/                 # 📦 Orders service (port 8003)
    ├── analytics/              # 📊 Analytics service (port 8004)
    ├── audit/                  # 🔍 Audit log service (port 8005)
    ├── genai/                  # 🤖 AI/ML service (port 8006)
    ├── common/                 # Shared models, DB, config
    ├── alembic/                # Database migrations
    └── docker-compose.yml      # Full stack orchestration
```

### Service Map

| Service    | Port | Responsibility |
|------------|------|----------------|
| **Gateway**    | `8000` | JWT validation, request routing, OpenAPI docs |
| **Auth**       | `8001` | Register, login, Google OAuth, OTP, profile |
| **Catalog**    | `8002` | Image upload, management, quota enforcement |
| **Orders**     | `8003` | Order lifecycle management |
| **Analytics**  | `8004` | Event tracking & aggregated stats |
| **Audit**      | `8005` | Structured log ingestion & search |
| **GenAI**      | `8006` | Style critique (Ollama), fabric sim, generation |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 16, React 19, Tailwind CSS v4, Framer Motion, Lucide React |
| **Backend** | FastAPI 0.136, Python 3.13, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| **Database** | PostgreSQL 15 (asyncpg driver) |
| **AI / ML** | Ollama (Qwen 3.5:9b), Google Colab / ComfyUI for generation |
| **Auth** | JWT (PyJWT), Google OAuth 2.0, OTP via SMTP |
| **Infra** | Docker Compose, Uvicorn, aiosmtplib, httpx |
| **Testing** | pytest, pytest-asyncio |

---

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** installed
- **Node.js 20+** and **npm**
- **Ollama** running locally with `qwen3.5:9b` pulled (`ollama pull qwen3.5:9b`)
- A Google Cloud project with OAuth credentials (optional, for Google login)

### 1. Clone the Repository

```bash
git clone https://github.com/thatquietkid/styleforge.git
cd styleforge
```

### 2. Start the Backend

```bash
cd styleforge-backend

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your JWT_SECRET, Google OAuth credentials, SMTP config, etc.

# Launch all services
docker compose up --build
```

The API gateway will be live at **http://localhost:8000**  
Interactive API docs at **http://localhost:8000/docs**

### 3. Start the Frontend

```bash
cd styleforge-frontend

# Install dependencies
npm install

# Configure environment
echo "NEXT_PUBLIC_AUTH_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```

The app will be live at **http://localhost:3000**

---

## 📡 API Documentation

Once the backend is running, full interactive API documentation is available at:

- **Swagger UI** → `http://localhost:8000/docs`
- **ReDoc** → `http://localhost:8000/redoc`

See [`styleforge-backend/API_REFERENCE.md`](./styleforge-backend/API_REFERENCE.md) for the full endpoint reference.

---

## 🗄️ Database Schema

Key entities managed via SQLAlchemy + Alembic migrations:

| Model | Description |
|-------|-------------|
| `User` | Accounts with JWT auth, Google OAuth, roles, and credit balance |
| `OTPRecord` | Hashed OTP tokens for passwordless email login |
| `Image` | Uploaded and AI-generated images per user |
| `ImageQuota` | Daily upload quota tracking |
| `StyleCritique` | Persisted AI critique responses (markdown) |
| `FabricSimulation` | Fabric sim inputs + rendered base64 output |
| `CreditTransaction` | Full audit trail of all credit movements |
| `AnalyticsEvent` | Service-level event tracking |
| `AuditLog` | Structured operational audit logs |

---

## ⚙️ Environment Variables

### Backend (`.env`)

| Variable | Description |
|----------|-------------|
| `POSTGRES_URL` | PostgreSQL connection string |
| `JWT_SECRET` | Secret key for JWT signing |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth credentials |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS` | Email config for OTP |
| `OLLAMA_BASE_URL` | Local Ollama endpoint |
| `OLLAMA_MODEL` | Model name (e.g. `qwen3.5:9b`) |
| `COLAB_URL` | Ngrok URL of your Colab inference backend |
| `NEW_USER_CREDITS` | Credits granted on signup (default: `100`) |
| `STYLE_CRITIQUE_CREDITS` | Credits per critique (default: `5`) |
| `IMAGE_GENERATION_CREDITS` | Credits per generation (default: `10`) |

### Frontend (`.env.local`)

| Variable | Description |
|----------|-------------|
| `NEXT_PUBLIC_AUTH_API_URL` | Backend gateway URL (e.g. `http://localhost:8000`) |

---

## 🧪 Testing

```bash
cd styleforge-backend

# Run all tests
pytest

# Run specific test suite
pytest tests/test_genai.py -v
pytest tests/test_auth.py -v
```

---

## 📁 Repository Structure

```
styleforge/
├── README.md                    ← You are here
├── styleforge-frontend/
│   ├── README.md                ← Frontend-specific docs
│   └── ...
└── styleforge-backend/
    ├── README.md                ← Backend-specific docs
    └── ...
```

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

---

## 📄 License

This project is licensed under the [MIT License](./LICENSE). See the `LICENSE` file for details.

---

<div align="center">

**Built with ❤️ and a passion for fashion × technology**

*StyleForge — Dress smarter. Create boldly.*

</div>