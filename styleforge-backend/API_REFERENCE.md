# Styleforge Backend — Frontend Integration Guide

> **Base URL (all environments):** `http://localhost:8000`  
> **All requests must go through the Gateway on port 8000.** Direct calls to individual service ports (8001–8006) bypass authentication and quota enforcement.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Authentication](#authentication)
3. [Errors & Status Codes](#errors--status-codes)
4. [Auth Endpoints](#auth-endpoints)
5. [Catalog Endpoints — User Images](#catalog-endpoints--user-images)
6. [Analytics Endpoints](#analytics-endpoints)
7. [Audit Endpoints](#audit-endpoints)
8. [GenAI Endpoints](#genai-endpoints)
9. [Frontend Integration Cheatsheet](#frontend-integration-cheatsheet)
10. [Running the Stack](#running-the-stack)

---

## Architecture Overview

```
Browser / Next.js Frontend
        │
        ▼  (port 8000)
┌──────────────────┐
│   Gateway Service │  JWT verify • Quota check • CORS • Static upload server
└────────┬─────────┘
         │ proxies to →
  ┌──────┼───────┬────────┬────────┐
  ▼      ▼       ▼        ▼        ▼
Auth  Catalog Analytics Audit    GenAI
8001   8002    8004     8005     8006
  │      │       │        │        │
  └──────┴───────┴───┬────┴────────┘
                     ▼
                 PostgreSQL
```

All traffic enters via the Gateway. The gateway:
- Validates JWT tokens before forwarding requests to downstream microservices.
- Enforces daily image upload and generation quotas.
- Serves uploaded and generated files statically at `/uploads/`.
- Injects `x-user-id` and `x-user-role` headers into upstream requests.
- Handles CORS allowing credentials and requests from standard ports (e.g. `localhost:3000`).

---

## Authentication

### Token Format

All protected endpoints require a `Bearer` token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

### Token Lifecycle

| Setting | Default |
|---|---|
| Algorithm | HS256 |
| Expiry | 30 minutes |
| Token type | `bearer` |

### Storing the Token (Frontend)

```ts
// After login/register, store the token:
localStorage.setItem('sf_token', data.access_token)

// Attach to every authenticated request:
headers: {
  'Authorization': `Bearer ${localStorage.getItem('sf_token')}`
}
```

### Public Endpoints (no token required)

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/login/otp/request`
- `POST /api/v1/auth/login/otp/verify`
- `POST /api/v1/auth/login/google`
- `POST /api/v1/analytics/track`
- `GET  /api/v1/audit/health`
- `GET  /api/v1/genai/health`
- `GET  /uploads/*` (Static uploaded & generated files)

---

## Errors & Status Codes

All gateway and microservice error responses return a standardized, structured JSON schema:

```json
{
  "detail": "Human-readable error message explaining the failure",
  "code": "machine_readable_error_code"
}
```

If it is a `422 Unprocessable Entity` validation error, the gateway returns:
```json
{
  "detail": "field_name: Error description message",
  "code": "validation_error",
  "fields": [
    {
      "field": "field_name",
      "message": "Error description message"
    }
  ]
}
```

### Response Status Codes

| Code | Meaning | When you'll see it |
|---|---|---|
| `200` | OK | Successful `GET`, `PATCH`, `PUT` requests |
| `201` | Created | Successful `POST` (registration, image upload, event tracking) |
| `204` | No Content | Successful `DELETE` (purging logs, deleting an image) |
| `400` | Bad Request | Invalid inputs, bad configuration, or missing active parameters |
| `401` | Unauthorized | Missing, invalid, or expired JWT token |
| `404` | Not Found | Requested entity, image, or microservice does not exist |
| `409` | Conflict | Email already registered, or key constraint violated |
| `413` | Payload Too Large | Image/sketch file size exceeds 5 MB limit |
| `422` | Validation Error | Invalid request payload (failed schema checks) |
| `429` | Too Many Requests | Daily quota exceeded (uploads or generations) |
| `500` | Internal Server Error | Unexpected crash or bug inside backend microservices |
| `503` | Service Unavailable | Upstream microservice or database is offline/unreachable |

---

## Auth Endpoints

### Register

```http
POST /api/v1/auth/register
Content-Type: application/json
```

**Request Body:**

```json
{
  "email": "alice@example.com",
  "password": "mySecurePass123"
}
```

> [!IMPORTANT]
> Password must be **at least 8 characters** long.

**Response `201`:**

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "alice@example.com",
    "role": "user",
    "created_at": "2026-05-23T13:20:00Z"
  }
}
```

**Errors:** `409` (Email already registered) · `422` (Validation failed)

---

### Login (Email + Password)

```http
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded
```

> [!NOTE]
> Uses OAuth2 standard form encoding — **not** raw JSON.

**Form Fields:**

| Field | Value |
|---|---|
| `username` | User's email address |
| `password` | Plain-text password |

**Example (fetch):**

```ts
const res = await fetch('/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({ username: email, password }),
})
```

**Response `200`:**

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "alice@example.com",
    "role": "user",
    "created_at": "2026-05-23T13:20:00Z"
  }
}
```

**Errors:** `401` (Incorrect credentials)

---

### Login via OTP (Step 1 — Request OTP)

```http
POST /api/v1/auth/login/otp/request
Content-Type: application/json
```

**Request Body:**

```json
{
  "email": "alice@example.com"
}
```

**Response `200`:**

```json
{
  "detail": "OTP sent to your email address.",
  "code": "otp_sent"
}
```

> [!TIP]
> This service acts as an SMTP mailer. Make sure to populate SMTP environment variables (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`) for actual deliveries.

**Errors:** `503` (SMTP service misconfigured)

---

### Login via OTP (Step 2 — Verify OTP)

```http
POST /api/v1/auth/login/otp/verify
Content-Type: application/json
```

**Request Body:**

```json
{
  "email": "alice@example.com",
  "otp": "482931"
}
```

**Response `200`:**

```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "alice@example.com",
    "role": "user",
    "created_at": "2026-05-23T13:20:00Z"
  }
}
```

> [!NOTE]
> If the user doesn't exist yet, a brand new account is **automatically created** upon successful OTP verification.

**Errors:** `400` (Invalid OTP / OTP expired)

---

### Login via Google OAuth

```http
POST /api/v1/auth/login/google
Content-Type: application/json
```

**Request Body:**

```json
{
  "id_token": "<Google ID token from frontend OAuth flow>"
}
```

> Use Google's standard web identity SDK to obtain a client-side ID token, then feed it here for signature verification.

**Response `200`:** Same structure as standard logins.

**Errors:** `401` (Invalid or expired Google token)

---

### Get Current User Profile 🔒

```http
GET /api/v1/auth/me
Authorization: Bearer <token>
```

**Response `200`:**

```json
{
  "id": 1,
  "email": "alice@example.com",
  "role": "user",
  "created_at": "2026-05-23T13:20:00Z"
}
```

**Errors:** `401` (Unauthorized)

---

### Update User Profile 🔒

```http
PATCH /api/v1/auth/me
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body (Optional / Patchable):**

```json
{
  "email": "newemail@example.com"
}
```

**Response `200`:** Returns the updated user profile object.

**Errors:** `401` (Unauthorized) · `409` (Email already in use)

---

### Update User Role 🔒

```http
PUT /api/v1/auth/me/role
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "role": "tailor"
}
```

> [!NOTE]
> Allowed role values are `user` and `tailor`. The `admin` role cannot be self-assigned. The old `seller` role has been removed.

**Response `200`:** Returns the updated user profile object with the new role.

**Errors:** `400` (Invalid role) · `401` (Unauthorized)

---

## Catalog Endpoints — User Images

> [!IMPORTANT]
> Uploading images is subject to a quota limit of **20 uploads per user per day**. The gateway enforces this boundary prior to routing requests to the catalog microservice.

### Upload an Image 🔒

```http
POST /api/v1/catalog/images/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form Fields:**

| Field | Type | Constraints | Description |
|---|---|---|---|
| `file` | File | JPEG, PNG, WebP only · max 5 MB | Image to be uploaded |

**Example (fetch):**

```ts
const formData = new FormData()
formData.append('file', fileInput.files[0])

const res = await fetch('/api/v1/catalog/images/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
})
```

**Response `201`:**

```json
{
  "id": 42,
  "user_id": 1,
  "url": "/uploads/img_42_uuid.png",
  "image_type": "upload",
  "prompt": null,
  "created_at": "2026-05-23T13:45:00Z"
}
```

> [!TIP]
> To display this image on your frontend, concatenate the gateway base URL: `http://localhost:8000/uploads/img_42_uuid.png`.

**Errors:** `413` (File size > 5 MB) · `422` (Unsupported file type) · `429` (Daily quota exceeded)

---

### Get My Images 🔒

```http
GET /api/v1/catalog/images/me?image_type=upload&skip=0&limit=20
Authorization: Bearer <token>
```

**Query Parameters (Optional):**

| Param | Type | Default | Description |
|---|---|---|---|
| `image_type` | string | — | Filter by image type (`upload` or `generated`) |
| `skip` | integer | `0` | Skip first N images for pagination |
| `limit` | integer | `20` | Max results to return (max `100`, default `20`) |

**Response `200`:**

```json
[
  {
    "id": 42,
    "user_id": 1,
    "url": "/uploads/img_42_uuid.png",
    "image_type": "upload",
    "prompt": null,
    "created_at": "2026-05-23T13:45:00Z"
  },
  {
    "id": 43,
    "user_id": 1,
    "url": "/uploads/gen_vton_uuid.png",
    "image_type": "generated",
    "prompt": "virtual try-on (long_sleeve_outwear)",
    "created_at": "2026-05-23T13:50:00Z"
  }
]
```

---

### Get Quota Status 🔒

```http
GET /api/v1/catalog/images/quota
Authorization: Bearer <token>
```

**Response `200`:**

```json
{
  "used": 3,
  "limit": 20,
  "remaining": 17
}
```

---

### Get Single Image 🔒

```http
GET /api/v1/catalog/images/{image_id}
Authorization: Bearer <token>
```

**Response `200`:**

```json
{
  "id": 42,
  "user_id": 1,
  "url": "/uploads/img_42_uuid.png",
  "image_type": "upload",
  "prompt": null,
  "created_at": "2026-05-23T13:45:00Z"
}
```

**Errors:** `404` (Not found or not owned by you)

---

### Delete an Image 🔒

```http
DELETE /api/v1/catalog/images/{image_id}
Authorization: Bearer <token>
```

> [!WARNING]
> Only the image owner is allowed to delete an image. This deletes the DB record and removes the file permanently from the server disk.

**Response `204` No Content**

**Errors:** `404` (Not found or not owned by you)

---

## Analytics Endpoints

> Telemetry and behavioral analytics. Event tracking is **public** (no auth) to allow seamless fire-and-forget submission from the client side. Aggregated statistics require authentication.

### Track an Event

```http
POST /api/v1/analytics/track
Content-Type: application/json
```

**Request Body:**

```json
{
  "service": "frontend",
  "event_type": "page_view",
  "user_id": 1,
  "payload": {
    "path": "/gallery",
    "referrer": "/login"
  }
}
```

**Response `201`:**

```json
{
  "status": "ok",
  "event_id": 99
}
```

---

### Grouped Usage Statistics 🔒

```http
GET /api/v1/analytics/stats/usage?service=frontend
Authorization: Bearer <token>
```

**Response `200`:**

```json
{
  "stats": [
    { "event_type": "page_view", "count": 450 },
    { "event_type": "image_upload_success", "count": 120 }
  ]
}
```

---

### Daily Activity Trend 🔒

```http
GET /api/v1/analytics/stats/daily?days=7
Authorization: Bearer <token>
```

**Response `200`:**

```json
{
  "stats": [
    { "day": "2026-05-22", "count": 42 },
    { "day": "2026-05-23", "count": 87 }
  ]
}
```

---

### Most Active Users 🔒

```http
GET /api/v1/analytics/stats/users?top=10
Authorization: Bearer <token>
```

**Response `200`:**

```json
{
  "stats": [
    { "user_id": 1, "events": 210 },
    { "user_id": 3, "events": 98 }
  ]
}
```

---

### Raw Event Log 🔒

```http
GET /api/v1/analytics/events?service=frontend&limit=10
Authorization: Bearer <token>
```

**Response `200`:** Returns a filterable list of raw event objects.

---

## Audit Endpoints

> Structured logging and system audits. Log submission is public for service-to-service ingestion; analytical reads require authentication.

### Ingest a Log Entry (Service-to-Service)

```http
POST /api/v1/audit/log
Content-Type: application/json
```

**Request Body:**

```json
{
  "service_name": "frontend",
  "level": "ERROR",
  "message": "Failed to upload sketch file",
  "payload": {
    "file_size": 6291456,
    "user_id": 1
  }
}
```

> [!NOTE]
> Valid levels: `DEBUG` · `INFO` · `WARN` · `ERROR` · `CRITICAL`

**Response `201`:** `{ "status": "ok" }`

---

### Search Audit Logs 🔒

```http
GET /api/v1/audit/search?service=auth&level=ERROR&since_minutes=60
Authorization: Bearer <token>
```

**Response `200`:**

```json
[
  {
    "id": 1,
    "service_name": "auth",
    "level": "ERROR",
    "message": "SMTP connection timed out",
    "payload": { "host": "smtp.gmail.com" },
    "created_at": "2026-05-23T13:40:00Z"
  }
]
```

---

### System Logs stats 🔒

```http
GET /api/v1/audit/stats?days=1
Authorization: Bearer <token>
```

**Response `200`:** Returns counts of logs grouped by service and severity level.

---

### Get Single Log Entry 🔒

```http
GET /api/v1/audit/logs/{log_id}
Authorization: Bearer <token>
```

**Response `200`:** Details of the single log event.

---

### Purge Old Audit Logs 🔒

```http
DELETE /api/v1/audit/purge?older_than_days=30
Authorization: Bearer <token>
```

**Response `204` No Content**

---

### Audit Service Health Check

```http
GET /api/v1/audit/health
```

**Response `200`:**

```json
{
  "status": "ok",
  "service": "audit"
}
```

---

## GenAI Endpoints

> Processing high-fashion designs, sketch conversions, and virtual apparel mapping using ComfyUI and external inference pipelines.
> 
> **Important architectural change:** These endpoints generate images **synchronously** and respond directly with the raw `image/png` binary content. They also save the generated images under the user's account inside the shared DB.

### Generate Scratch or Sketch 🔒

```http
POST /api/v1/genai/generate/scratch-or-sketch
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form Fields:**

| Field | Type | Required | Default / Constraints | Description |
|---|---|---|---|---|
| `positive_prompt` | string | ✅ | — | Style description of the garment to generate |
| `negative_prompt` | string | ❌ | `"pale fabric, washed out colors..."` | Refines quality and prevents washed out traits |
| `sketch_file` | File | ✅ | JPEG, PNG, WebP · max 5 MB | The base drawing/blueprint of the garment |
| `target_class` | string | ❌ | `"long_sleeve_outwear"` | Classification tag for semantic region mapping |

**Response `200`:**
- Content-Type: `image/png`
- Body: **Raw binary png image data.**

**Errors:** `400` (Empty positive prompt) · `413` (Sketch > 5 MB) · `422` (Unsupported file type) · `503` (Inference backend offline/no GPU)

---

### Virtual Try-On 🔒

```http
POST /api/v1/genai/generate/virtual-try-on
Authorization: Bearer <token>
Content-Type: multipart/form-data
```

**Form Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `person_image` | File | ✅ | Main image of the model/person trying on the garment (JPEG/PNG/WebP, max 5MB) |
| `garment_image` | File | ✅ | Image of the isolated target apparel product (JPEG/PNG/WebP, max 5MB) |
| `positive_prompt` | string | ❌ | Extra instruction description to guide fabric, fit, or details |
| `negative_prompt` | string | ❌ | Negative prompt guidance to avoid distortions |
| `target_class` | string | ❌ | Segment class of the garment to overlay (default: `"long_sleeve_outwear"`) |

**Response `200`:**
- Content-Type: `image/png`
- Body: **Raw binary png image data.**

**Errors:** `413` (Files > 5 MB) · `422` (Unsupported image format) · `500` (ComfyUI workflow failure)

---

### GenAI Service Health Check

```http
GET /api/v1/genai/health
```

**Response `200`:**

```json
{
  "status": "ok",
  "service": "genai"
}
```

---

## Frontend Integration Cheatsheet

### 1. Axios Interceptor with Global Auth & Error Parsing (TypeScript)

```ts
import axios from 'axios'

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000',
})

// Attach JWT token automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('sf_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Global response / error normalization
api.interceptors.response.use(
  (res) => res,
  (err) => {
    // Session expired or token manipulated
    if (err.response?.status === 401) {
      localStorage.removeItem('sf_token')
      window.location.href = '/login'
    }
    
    // Normalise error return structure
    const backendError = err.response?.data;
    const errorMessage = backendError?.detail || "An unexpected error occurred.";
    const errorCode = backendError?.code || "network_error";
    
    return Promise.reject({
      message: errorMessage,
      code: errorCode,
      status: err.response?.status,
      fields: backendError?.fields || []
    })
  }
)

export default api
```

---

### 2. Handling Direct Binary Image Responses

Since `scratch-or-sketch` and `virtual-try-on` return raw binary data instead of URLs, the frontend needs to fetch them as a **Blob** and convert them to an Object URL for rendering:

```tsx
import React, { useState } from 'react'
import api from './api'

export function TryOnComponent() {
  const [loading, setLoading] = useState(false)
  const [resultImage, setResultImage] = useState<string | null>(null)

  const handleVirtualTryOn = async (personFile: File, garmentFile: File) => {
    setLoading(true)
    const formData = new FormData()
    formData.append('person_image', personFile)
    formData.append('garment_image', garmentFile)
    formData.append('target_class', 'long_sleeve_outwear')

    try {
      const response = await api.post('/api/v1/genai/generate/virtual-try-on', formData, {
        responseType: 'blob', // IMPORTANT: Tell axios to capture binary response
      })

      // Convert binary Blob to an object URL that <img> can read
      const blobUrl = URL.createObjectURL(response.data)
      setResultImage(blobUrl)
    } catch (err: any) {
      alert(`Generation Failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      {/* ... File inputs and buttons ... */}
      {loading && <p>Generating fashion design...</p>}
      {resultImage && (
        <img src={resultImage} alt="Virtual Try-On Result" className="rounded-lg shadow-xl" />
      )}
    </div>
  )
}
```

---

### 3. Displaying Uploaded & Generated Images

To display images returned from `/api/v1/catalog/images/me`, make sure to prefix them with the backend host:

```tsx
const BACKEND_HOST = 'http://localhost:8000'

// image.url is e.g. "/uploads/img_42_uuid.png"
const displayUrl = `${BACKEND_HOST}${image.url}`
```

---

## Running the Stack

```bash
# Start all microservices in the background
cd styleforge-backend
docker-compose up -d --build

# Run database migrations
docker exec -it styleforge_auth alembic upgrade head

# Watch live gateway logs to debug routing
docker logs -f styleforge_gateway
```

### Service Port Map

| Service | Internal Port | External Port | Notes |
|---|---|---|---|
| **Gateway** | `8000` | `8000` | **The single exposed entry-point for frontends** |
| Auth | `8001` | — | Internal routing only |
| Catalog | `8002` | — | Internal routing only |
| Analytics | `8004` | — | Internal routing only |
| Audit | `8005` | — | Internal routing only |
| GenAI | `8006` | — | Internal routing only |
| PostgreSQL | `5432` | `5432` | Accessible for database debugging |
