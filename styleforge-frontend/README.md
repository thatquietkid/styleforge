<div align="center">

# 🎨 StyleForge Frontend

### Next.js 16 · React 19 · Tailwind CSS v4 · Framer Motion

[![Next.js](https://img.shields.io/badge/Next.js-16-black?style=flat-square&logo=next.js)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Framer Motion](https://img.shields.io/badge/Framer%20Motion-12-FF0055?style=flat-square&logo=framer)](https://www.framer.com/motion/)
[![Lucide](https://img.shields.io/badge/Lucide%20React-1.16-F56565?style=flat-square)](https://lucide.dev/)

*A high-fidelity fashion interface built for speed, style, and AI-powered creativity.*

</div>

---

## 📂 Project Structure

```
styleforge-frontend/
├── src/
│   └── app/                        # Next.js App Router
│       │
│       ├── page.js                 # 🏠 Landing / Home page
│       ├── layout.js               # Root layout (fonts, global styles)
│       ├── globals.css             # Global styles + Tailwind imports
│       │
│       ├── login/page.js           # 🔐 Login (JWT, Google OAuth, OTP)
│       ├── register/page.js        # 📝 Registration page
│       ├── profile/page.js         # 👤 User dashboard (credits, history)
│       │
│       ├── style-critique/page.js  # 🤖 AI outfit critique (upload → AI analysis)
│       ├── fabric-ai/page.js       # 🧵 Fabric physics simulation
│       ├── outfit-ai/page.js       # 👗 AI outfit generation from prompts
│       ├── virtual-tryon/page.js   # 🪞 Virtual try-on (coming soon)
│       │
│       ├── features/page.js        # ⭐ Platform features overview
│       ├── tailors/page.js         # 👔 Tailor directory
│       ├── studio/page.js          # 🎨 Design studio
│       ├── about/page.js           # ℹ️  About page
│       ├── contact/page.js         # 📬 Contact page
│       │
│       ├── components/
│       │   └── ImageLightbox.js    # Fullscreen image lightbox component
│       │
│       ├── context/
│       │   └── AuthContext.js      # 🔑 Global auth state (JWT storage, user info)
│       │
│       ├── utils/
│       │   └── error.js            # Centralized API error handling
│       │
│       └── api/
│           └── generate/route.js   # Next.js API route (server-side proxy)
│
├── public/                         # Static assets
├── next.config.mjs                 # Next.js configuration
├── tailwind.config.js              # Tailwind CSS v4 config
├── postcss.config.mjs              # PostCSS config
├── eslint.config.mjs               # ESLint rules
├── jsconfig.json                   # Path aliases
└── package.json
```

---

## 🚀 Getting Started

### Prerequisites

- **Node.js 20+** (LTS recommended)
- **npm** or **yarn**
- StyleForge backend running at `http://localhost:8000`

### Installation

```bash
# Navigate to the frontend directory
cd styleforge-frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.local.example .env.local
# or create manually:
echo "NEXT_PUBLIC_AUTH_API_URL=http://localhost:8000" > .env.local
```

### Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Production Build

```bash
npm run build
npm start
```

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_AUTH_API_URL` | ✅ | Backend gateway base URL (e.g. `http://localhost:8000`) |

> All API calls route through the gateway. A single env var is all you need.

---

## 🧠 Key Pages & Features

### 🏠 Landing Page (`/`)
The main marketing page showcasing StyleForge's capabilities. Features animated hero sections, feature highlights, and CTAs to the AI tools.

### 🔐 Authentication (`/login`, `/register`)
Full authentication UI supporting three login methods:
- **Email + Password** — classic JWT login
- **Google OAuth** — one-click sign in
- **OTP (Passwordless)** — receive a one-time code via email

Auth state is managed globally via `AuthContext` — JWT tokens are stored securely and injected into all API requests.

### 🤖 Style Critique (`/style-critique`)
The flagship AI feature:
1. Upload an outfit photo (drag & drop or file picker)
2. Submit — deducts 5 credits
3. Receive a structured markdown critique from the AI covering:
   - **Core Issue** — the single biggest flaw
   - **Aesthetic Breakdown** — color, fit, silhouette, textures
   - **Execution Plan** — actionable garment swaps and styling tips
4. Results are saved to your profile history

### 🧵 Fabric AI (`/fabric-ai`)
Interactive fabric simulation:
- Select fabric type (Silk, Velvet, Denim, Cotton, etc.)
- Adjust color, weight, and stiffness with real-time sliders
- Generate a physics-based fabric drape render
- Save results to your gallery (costs 5 credits)

### 👗 Outfit AI (`/outfit-ai`)
Text-to-outfit generation:
- Describe your desired outfit in natural language
- AI generates a fashion concept image
- Powered by Colab/ComfyUI backend (costs 10 credits)

### 👤 Profile (`/profile`)
Your personal fashion dashboard:
- **Credit balance** and transaction history
- **Style critique history** — browse past AI critiques
- **Image gallery** — all uploaded and generated images
- Account settings and preferences

---

## 🔑 Authentication Flow

```
AuthContext (global state)
│
├── login(email, password)       → POST /api/v1/auth/login
├── loginWithGoogle()            → GET  /api/v1/auth/google
├── requestOTP(email)            → POST /api/v1/auth/otp/request
├── verifyOTP(email, otp)        → POST /api/v1/auth/otp/verify
├── register(data)               → POST /api/v1/auth/register
└── logout()                     → clears JWT from storage
```

JWT tokens are stored in the context and attached as `Authorization: Bearer <token>` headers on all protected API calls.

---

## 📦 Dependencies

### Runtime

| Package | Version | Purpose |
|---------|---------|---------|
| `next` | 16.2.6 | React framework with App Router |
| `react` | 19.2.4 | UI library |
| `react-dom` | 19.2.4 | DOM rendering |
| `framer-motion` | ^12 | Animations and transitions |
| `motion` | ^12 | Motion primitives |
| `lucide-react` | ^1.16 | Icon library |
| `openai` | ^6.39 | OpenAI SDK (for API route proxy) |

### Dev Dependencies

| Package | Purpose |
|---------|---------|
| `tailwindcss` v4 | Utility-first CSS framework |
| `@tailwindcss/postcss` | PostCSS integration |
| `eslint` + `eslint-config-next` | Linting |
| `babel-plugin-react-compiler` | React compiler optimization |

---

## 🎨 Styling

The project uses **Tailwind CSS v4** with the new PostCSS-first configuration approach.

- Global base styles are in `src/app/globals.css`
- Component-level styling is done with Tailwind utility classes directly in JSX
- Animations are handled by **Framer Motion** for complex transitions and **Tailwind** for simpler ones

---

## 🔌 API Integration

All backend calls target `NEXT_PUBLIC_AUTH_API_URL` (the gateway). The pattern across pages:

```js
const response = await fetch(`${process.env.NEXT_PUBLIC_AUTH_API_URL}/api/v1/genai/critique`, {
  method: "POST",
  headers: {
    Authorization: `Bearer ${token}`,
  },
  body: formData,
});

if (!response.ok) {
  // Centralized error handling via src/app/utils/error.js
  throw await parseApiError(response);
}

const data = await response.json();
```

---

## 🐛 Common Issues

**`NEXT_PUBLIC_AUTH_API_URL` not set**
→ Create `.env.local` with `NEXT_PUBLIC_AUTH_API_URL=http://localhost:8000`

**CORS errors in development**
→ Ensure the backend gateway allows `http://localhost:3000` in its CORS config (it does by default).

**Login redirects not working**
→ Check that the backend is running and healthy (`docker compose ps` or `python run_all.py`).

**Build fails on `lucide-react`**
→ Run `npm install` to ensure all packages are installed at the correct versions.

---

## 📝 Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server with hot reload |
| `npm run build` | Create optimized production build |
| `npm start` | Serve the production build |
| `npm run lint` | Run ESLint |