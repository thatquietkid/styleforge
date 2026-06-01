# Styleforge Backend Endpoints — AI Context & Contract Guide

Use this file as a context sheet to feed to AI systems for scaffolding pages, writing network request services, and validating API integrations between frontend and backend.

## Global Settings
- **Base URL:** `http://localhost:8000` (All requests must flow through Gateway)
- **Static Assets:** Serves files under `/uploads/*` at `http://localhost:8000/uploads/<filename>`
- **Standard Error Payload:**
  ```json
  { "detail": "error message", "code": "machine_readable_code" }
  ```
- **Validation Error Payload (`422`):**
  ```json
  {
    "detail": "field_name: Error message",
    "code": "validation_error",
    "fields": [{ "field": "field_name", "message": "Error message" }]
  }
  ```

---

## 1. Authentication Endpoints

### Register User
- **Method & Route:** `POST /api/v1/auth/register`
- **Auth Required:** No
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "securepassword123" // Minimum 8 characters
  }
  ```
- **Response `201` (JSON):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "role": "user",
      "created_at": "2026-05-23T13:20:00Z"
    }
  }
  ```
- **Common Errors:**
  - `409` Conflict (`{"detail": "Email already registered", "code": "email_registered"}`)
  - `422` Validation Error (e.g. password < 8 characters)

---

### Login (Password)
- **Method & Route:** `POST /api/v1/auth/login`
- **Auth Required:** No
- **Headers:** `Content-Type: application/x-www-form-urlencoded`
- **Request Form Body:**
  | Key | Type | Description |
  |---|---|---|
  | `username` | string | Email address of the user |
  | `password` | string | Plain-text password |
- **Response `200` (JSON):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "role": "user",
      "created_at": "2026-05-23T13:20:00Z"
    }
  }
  ```
- **Common Errors:**
  - `401` Unauthorized (`{"detail": "Incorrect email or password", "code": "incorrect_credentials"}`)

---

### Login (OTP Step 1 — Request OTP)
- **Method & Route:** `POST /api/v1/auth/login/otp/request`
- **Auth Required:** No
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "email": "user@example.com"
  }
  ```
- **Response `200` (JSON):**
  ```json
  {
    "detail": "OTP sent to your email address.",
    "code": "otp_sent"
  }
  ```
- **Common Errors:**
  - `503` Service Unavailable (`{"detail": "SMTP mailer down", "code": "smtp_error"}`)

---

### Login (OTP Step 2 — Verify OTP)
- **Method & Route:** `POST /api/v1/auth/login/otp/verify`
- **Auth Required:** No
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "otp": "482931"
  }
  ```
- **Response `200` (JSON):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "email": "user@example.com",
      "role": "user",
      "created_at": "2026-05-23T13:20:00Z"
    }
  }
  ```
  *(Note: automatically registers the user account if they did not exist previously).*
- **Common Errors:**
  - `400` Bad Request (`{"detail": "Invalid or expired OTP", "code": "invalid_otp"}`)

---

### Login via Google OAuth
- **Method & Route:** `POST /api/v1/auth/login/google`
- **Auth Required:** No
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "id_token": "google-id-token-obtained-from-gis-sdk"
  }
  ```
- **Response `200` (JSON):** Token and user object (same structure as Register/Login).
- **Common Errors:**
  - `401` Unauthorized (`{"detail": "Invalid Google token", "code": "invalid_google_token"}`)

---

### Get My Profile
- **Method & Route:** `GET /api/v1/auth/me`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response `200` (JSON):**
  ```json
  {
    "id": 1,
    "email": "user@example.com",
    "role": "user",
    "created_at": "2026-05-23T13:20:00Z"
  }
  ```
- **Common Errors:**
  - `401` Unauthorized (`{"detail": "Invalid or expired token", "code": "token_expired"}`)

---

### Update Profile Info
- **Method & Route:** `PATCH /api/v1/auth/me`
- **Auth Required:** Yes (`Bearer <token>`)
- **Headers:** `Content-Type: application/json`
- **Request Body (Optional / Patchable):**
  ```json
  {
    "email": "newemail@example.com"
  }
  ```
- **Response `200` (JSON):** Updated user profile object.
- **Common Errors:**
  - `409` Conflict (`{"detail": "Email already in use", "code": "email_taken"}`)

---

### Update User Role
- **Method & Route:** `PUT /api/v1/auth/me/role`
- **Auth Required:** Yes (`Bearer <token>`)
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "role": "tailor" // Allowed: "user" | "tailor" ("admin" cannot be self-assigned, "seller" removed)
  }
  ```
- **Response `200` (JSON):** Updated user profile object.
- **Common Errors:**
  - `400` Bad Request (`{"detail": "Invalid role value", "code": "invalid_role"}`)

---

## 2. Catalog (User Images) Endpoints

### Upload Image
- **Method & Route:** `POST /api/v1/catalog/images/upload`
- **Auth Required:** Yes (`Bearer <token>`)
- **Headers:** `Content-Type: multipart/form-data` (Let browser set boundary automatically)
- **Request Body (Form Data):**
  | Key | Type | Description |
  |---|---|---|
  | `file` | Binary File | JPEG, PNG, or WebP format. Maximum size: 5 MB. |
- **Response `201` (JSON):**
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
- **Common Errors:**
  - `413` Payload Too Large (`{"detail": "File size exceeds 5 MB", "code": "file_too_large"}`)
  - `422` Unprocessable Entity (`{"detail": "Unsupported file type", "code": "invalid_file_type"}`)
  - `429` Too Many Requests (`{"detail": "Daily upload quota of 20 images reached", "code": "quota_exceeded"}`)

---

### Get My Images (Uploaded & Generated)
- **Method & Route:** `GET /api/v1/catalog/images/me`
- **Auth Required:** Yes (`Bearer <token>`)
- **Query Parameters (Optional):**
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `image_type` | string | — | Filter by type: `upload` or `generated` |
  | `skip` | integer | `0` | Offset for pagination |
  | `limit` | integer | `20` | Max images to return (range 1-100) |
- **Response `200` (JSON):**
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
      "url": "/uploads/gen_scratch_uuid.png",
      "image_type": "generated",
      "prompt": "futuristic trench coat neon cyan lines cyber fashion",
      "created_at": "2026-05-23T13:52:00Z"
    }
  ]
  ```

---

### Get Image Upload Quota Status
- **Method & Route:** `GET /api/v1/catalog/images/quota`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response `200` (JSON):**
  ```json
  {
    "used": 3,
    "limit": 20,
    "remaining": 17
  }
  ```

---

### Get Single Image Detail
- **Method & Route:** `GET /api/v1/catalog/images/{image_id}`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response `200` (JSON):** Image record (same structure as above upload/list responses).
- **Common Errors:**
  - `404` Not Found (`{"detail": "Image not found or not owned by user", "code": "image_not_found"}`)

---

### Delete Image
- **Method & Route:** `DELETE /api/v1/catalog/images/{image_id}`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response `204`:** No Content (Deletes from DB and cleans file off server storage).
- **Common Errors:**
  - `404` Not Found (`{"detail": "Image not found or not owned by user", "code": "image_not_found"}`)

---

## 3. GenAI Endpoints

### Generate Scratch or Sketch
- **Method & Route:** `POST /api/v1/genai/generate/scratch-or-sketch`
- **Auth Required:** Yes (`Bearer <token>`)
- **Headers:** `Content-Type: multipart/form-data`
- **Request Body (Form Data):**
  | Key | Type | Required | Default / Constraints | Description |
  |---|---|---|---|---|
  | `positive_prompt` | string | Yes | — | Describes the design features to generate |
  | `negative_prompt` | string | No | `"pale fabric, washed out colors..."` | Guidance to avoid low-quality generations |
  | `sketch_file` | Binary File | Yes | JPEG, PNG, WebP · max 5 MB | The hand-drawn outline/blueprint guide |
  | `target_class` | string | No | `"long_sleeve_outwear"` | Garment classification tag |
- **Response `200` (Direct Image Binary):**
  - **Content-Type:** `image/png`
  - **Body:** Raw binary png image stream. 
  - *(Behind the scenes: the generated image is saved automatically to the database under the user's generated collection).*
- **Common Errors:**
  - `400` Bad Request (`{"detail": "positive_prompt cannot be empty.", "code": "validation_error"}`)
  - `413` Payload Too Large (`{"detail": "Sketch file exceeds the 5 MB size limit.", "code": "file_too_large"}`)
  - `422` Unprocessable Entity (`{"detail": "Unsupported file type", "code": "invalid_file_type"}`)
  - `503` Service Unavailable (`{"detail": "Inference backend is offline or lacks GPU.", "code": "backend_unavailable"}`)

---

### Virtual Try-On
- **Method & Route:** `POST /api/v1/genai/generate/virtual-try-on`
- **Auth Required:** Yes (`Bearer <token>`)
- **Headers:** `Content-Type: multipart/form-data`
- **Request Body (Form Data):**
  | Key | Type | Required | Description |
  |---|---|---|---|
  | `person_image` | Binary File | Yes | Image of the model/person (JPEG/PNG/WebP, max 5MB) |
  | `garment_image` | Binary File | Yes | Image of isolated target garment (JPEG/PNG/WebP, max 5MB) |
  | `positive_prompt` | string | No | Optional prompts describing fine-grained changes |
  | `negative_prompt` | string | No | Optional negative guide for high quality output |
  | `target_class` | string | No | Segment category (default: `"long_sleeve_outwear"`) |
- **Response `200` (Direct Image Binary):**
  - **Content-Type:** `image/png`
  - **Body:** Raw binary png image stream.
  - *(Behind the scenes: the try-on result is saved to the database under the user's generated collection).*
- **Common Errors:**
  - `413` Payload Too Large (`{"detail": "person_image/garment_image exceeds 5 MB limit.", "code": "file_too_large"}`)
  - `422` Unprocessable Entity (`{"detail": "Unsupported file type", "code": "invalid_file_type"}`)
  - `500` Internal Error (`{"detail": "Image generation failed.", "code": "generation_error"}`)

---

### GenAI Health Check
- **Method & Route:** `GET /api/v1/genai/health`
- **Auth Required:** No
- **Response `200` (JSON):**
  ```json
  {
    "status": "ok",
    "service": "genai"
  }
  ```

---

## 4. Analytics Endpoints

### Track Telemetry Event
- **Method & Route:** `POST /api/v1/analytics/track`
- **Auth Required:** No (Public event pipeline)
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "service": "frontend",
    "event_type": "image_upload_success", // Common: "page_view" | "design_started" | "role_changed"
    "user_id": 1, // Optional user association
    "payload": {
      "resolution": "1920x1080",
      "upload_duration_ms": 420
    } // Optional custom metadata dict
  }
  ```
- **Response `201` (JSON):**
  ```json
  {
    "status": "ok",
    "event_id": 1205
  }
  ```

---

### Grouped Usage Statistics
- **Method & Route:** `GET /api/v1/analytics/stats/usage`
- **Auth Required:** Yes (`Bearer <token>`)
- **Query Parameters (Optional):**
  | Parameter | Type | Description |
  |---|---|---|
  | `service` | string | Filter event counts to a specific microservice |
- **Response `200` (JSON):**
  ```json
  {
    "stats": [
      { "event_type": "page_view", "count": 1054 },
      { "event_type": "image_upload_success", "count": 210 }
    ]
  }
  ```

---

### Daily Event Breakdown
- **Method & Route:** `GET /api/v1/analytics/stats/daily`
- **Auth Required:** Yes (`Bearer <token>`)
- **Query Parameters:**
  | Parameter | Type | Default | Constraints | Description |
  |---|---|---|---|---|
  | `days` | integer | `7` | Range `1`-`90` | Number of days of historical aggregation |
  | `service` | string | — | — | Filter counts to a specific microservice |
- **Response `200` (JSON):**
  ```json
  {
    "stats": [
      { "day": "2026-05-22", "count": 150 },
      { "day": "2026-05-23", "count": 234 }
    ]
  }
  ```

---

### User Activity Rankings
- **Method & Route:** `GET /api/v1/analytics/stats/users`
- **Auth Required:** Yes (`Bearer <token>`)
- **Query Parameters (Optional):**
  | Parameter | Type | Default | Constraints | Description |
  |---|---|---|---|---|
  | `top` | integer | `10` | Range `1`-`100` | Return the top N most active users |
- **Response `200` (JSON):**
  ```json
  {
    "stats": [
      { "user_id": 1, "events": 850 },
      { "user_id": 3, "events": 431 }
    ]
  }
  ```

---

### Raw Analytics Events Logs
- **Method & Route:** `GET /api/v1/analytics/events`
- **Auth Required:** Yes (`Bearer <token>`)
- **Query Parameters (Optional):**
  | Parameter | Type | Default | Constraints | Description |
  |---|---|---|---|---|
  | `service` | string | — | — | Filter by service name |
  | `event_type` | string | — | — | Filter by event type string |
  | `user_id` | integer | — | — | Filter by specific user ID |
  | `skip` | integer | `0` | ge `0` | Offset |
  | `limit` | integer | `50` | ge `1`, le `200` | Pagination limit |
- **Response `200` (JSON):** Array of raw telemetry objects.

---

## 5. System Audit Endpoints

### Ingest Log (Service-to-Service)
- **Method & Route:** `POST /api/v1/audit/log`
- **Auth Required:** No
- **Headers:** `Content-Type: application/json`
- **Request Body:**
  ```json
  {
    "service_name": "frontend",
    "level": "ERROR", // "DEBUG" | "INFO" | "WARN" | "ERROR" | "CRITICAL"
    "message": "ComfyUI pipeline connection timeout",
    "payload": { "retries": 3, "ip": "127.0.0.1" } // Optional metadata dict
  }
  ```
- **Response `201` (JSON):**
  ```json
  {
    "status": "ok"
  }
  ```

---

### Search System Log Records
- **Method & Route:** `GET /api/v1/audit/search`
- **Auth Required:** Yes (`Bearer <token>`)
- **Query Parameters (Optional):**
  | Parameter | Type | Range | Description |
  |---|---|---|---|
  | `service` | string | — | Match exact service name |
  | `level` | string | — | Match exact log level severity |
  | `message_contains` | string | — | Substring search within log message |
  | `since_minutes` | integer | `1`-`10080` | Restrict logs to the last N minutes |
  | `skip` | integer | ge `0` | Offset |
  | `limit` | integer | `1`-`500` | Max logs to return |
- **Response `200` (JSON):**
  ```json
  [
    {
      "id": 105,
      "service_name": "auth",
      "level": "ERROR",
      "message": "SMTP connection timed out",
      "payload": { "host": "smtp.gmail.com" },
      "created_at": "2026-05-23T13:40:00Z"
    }
  ]
  ```

---

### Log Ingestion stats
- **Method & Route:** `GET /api/v1/audit/stats`
- **Auth Required:** Yes (`Bearer <token>`)
- **Query Parameters (Optional):**
  | Parameter | Type | Default | Range | Description |
  |---|---|---|---|---|
  | `days` | integer | `1` | `1`-`30` | Days of counts to group |
- **Response `200` (JSON):**
  ```json
  {
    "period_days": 1,
    "stats": [
      { "service": "auth", "level": "INFO", "count": 145 },
      { "service": "genai", "level": "ERROR", "count": 2 }
    ]
  }
  ```

---

### Get Single Log Entry Details
- **Method & Route:** `GET /api/v1/audit/logs/{log_id}`
- **Auth Required:** Yes (`Bearer <token>`)
- **Response `200` (JSON):** Audit log record (same structure as search response).
- **Common Errors:**
  - `404` Not Found (`{"detail": "Log not found", "code": "log_not_found"}`)

---

### Purge Old Audit Logs
- **Method & Route:** `DELETE /api/v1/audit/purge`
- **Auth Required:** Yes (`Bearer <token>`)
- **Query Parameters (Optional):**
  | Parameter | Type | Default | Description |
  |---|---|---|---|
  | `older_than_days` | integer | `30` | Delete all system logs older than N days |
- **Response `204`:** No Content

---

### Audit Service Health Check
- **Method & Route:** `GET /api/v1/audit/health`
- **Auth Required:** No
- **Response `200` (JSON):**
  ```json
  {
    "status": "ok",
    "service": "audit"
  }
  ```
