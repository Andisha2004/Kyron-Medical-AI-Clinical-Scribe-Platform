# System Architecture

## Overview

The application follows a client-server architecture.

```text
Users
   │
 HTTPS
   │
Next.js Frontend
   │
REST / SSE / WebSocket
   │
FastAPI Backend
   ├──────────────┐
   │              │
AWS RDS      AI Services
(PostgreSQL)
```

---

# Frontend

Responsibilities:

* Authentication
* Dashboards
* Encounter Workspace
* SOAP Note Editor
* Voice Interface
* ICD-10 Search

---

# Backend

Responsibilities:

* Authentication
* Authorization
* Encounter Management
* SOAP Note Generation
* Voice Processing
* Patient History Retrieval
* Template Management
* Versioning
* Audit Logging

---

# Database

AWS RDS stores:

* Users
* Patients
* Encounters
* Drafts
* Notes
* Note Versions
* Templates
* ICD-10 Codes
* Audit Logs

---

# AI Services

The AI layer is responsible for:

* SOAP note generation
* Voice editing
* Streaming speech-to-text

The backend communicates directly with AI services. The frontend never calls AI services directly.

---

# Request Flow

```text
Provider
   │
Frontend
   │
Backend
   │
Database
   │
AI Service
   │
Backend
   │
Frontend
```

---

# Backend Layers

```text
API
 ↓
Services
 ↓
Repositories
 ↓
Database
```

---

# Security

* HTTPS
* JWT Authentication
* Role-Based Access Control
* Private AWS RDS
* Secrets stored in AWS Secrets Manager

---

# Deployment

```text
Internet
    │
 HTTPS
    │
nginx
    │
FastAPI
    │
AWS RDS
```

---

# Core Workflow

```text
Login
    ↓
Create Encounter
    ↓
Enter Clinical Information
    ↓
Generate SOAP Note
    ↓
Review & Edit
    ↓
Save Note
```
