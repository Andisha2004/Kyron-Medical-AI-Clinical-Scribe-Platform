# API Design

## Overview

The frontend communicates with the backend through REST APIs. Streaming features such as SOAP note generation and voice dictation use Server-Sent Events (SSE) or WebSockets.

Base URL:

```text
/api
```

---

# Authentication

| Method | Endpoint       | Description       |
| ------ | -------------- | ----------------- |
| POST   | `/auth/login`  | Authenticate user |
| POST   | `/auth/logout` | Logout user       |
| GET    | `/auth/me`     | Get current user  |

---

# Patients

| Method | Endpoint           | Description             |
| ------ | ------------------ | ----------------------- |
| GET    | `/patients/search` | Search existing patient |
| POST   | `/patients`        | Create patient          |

---

# Encounters

| Method | Endpoint                    | Description             |
| ------ | --------------------------- | ----------------------- |
| GET    | `/encounters`               | Get provider encounters |
| POST   | `/encounters`               | Create encounter        |
| GET    | `/encounters/{id}`          | Get encounter details   |
| PATCH  | `/encounters/{id}/draft`    | Save encounter draft    |
| POST   | `/encounters/{id}/generate` | Generate SOAP note      |
| POST   | `/encounters/{id}/save`     | Save finalized note     |

---

# Notes

| Method | Endpoint               | Description      |
| ------ | ---------------------- | ---------------- |
| GET    | `/notes/{id}`          | Get note         |
| GET    | `/notes/{id}/versions` | Get note history |

---

# ICD-10

| Method | Endpoint      | Description         |
| ------ | ------------- | ------------------- |
| GET    | `/icd/search` | Search ICD-10 codes |

---

# Templates

| Method | Endpoint          | Description     |
| ------ | ----------------- | --------------- |
| GET    | `/templates`      | List templates  |
| POST   | `/templates`      | Create template |
| PUT    | `/templates/{id}` | Update template |
| DELETE | `/templates/{id}` | Delete template |

---

# Providers

| Method | Endpoint          | Description         |
| ------ | ----------------- | ------------------- |
| GET    | `/providers`      | List providers      |
| POST   | `/providers`      | Create provider     |
| PATCH  | `/providers/{id}` | Deactivate provider |

---

# Voice

| Method    | Endpoint           | Description                 |
| --------- | ------------------ | --------------------------- |
| WebSocket | `/voice/dictation` | Live speech-to-text         |
| WebSocket | `/voice/edit`      | Conversational note editing |

---

# Response Format

Successful responses:

```json
{
  "success": true,
  "data": {}
}
```

Error responses:

```json
{
  "success": false,
  "error": "Description of the error."
}
```

---

# Authentication

Protected endpoints require authentication.

Provider endpoints are accessible only by Providers.

Admin endpoints are accessible only by Admins.

Authorization is enforced by the backend.

---

# API Principles

* RESTful endpoints
* JSON request and response bodies
* Consistent error handling
* Backend validation
* Streaming for real-time features
* Version-friendly design
