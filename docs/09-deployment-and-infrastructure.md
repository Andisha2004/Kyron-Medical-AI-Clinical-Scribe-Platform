# Deployment and Infrastructure

## Overview

The application is deployed on AWS using a simple and secure architecture.

The frontend and backend run on an EC2 instance, while PostgreSQL is hosted on AWS RDS.

---

# Infrastructure

```text
                Internet
                    │
                 HTTPS
                    │
                 nginx
                    │
        ┌───────────┴───────────┐
        │                       │
   Next.js Frontend      FastAPI Backend
                                   │
                          AWS RDS PostgreSQL
                                   │
                           AI Service APIs
```

<img width="1536" height="1024" alt="ChatGPT Image Jul 11, 2026, 06_23_55 PM" src="https://github.com/user-attachments/assets/1c3c83ed-85d3-48d8-954b-7a87ab9a1253" />


---

# Components

## Frontend

* Next.js
* React
* TypeScript

Runs behind nginx.

---

## Backend

* FastAPI
* Python

Responsible for:

* Authentication
* Business logic
* Database access
* AI communication

---

## Database

* AWS RDS PostgreSQL

Stores:

* Users
* Patients
* Encounters
* Drafts
* Notes
* Note Versions
* Templates
* Audit Logs

---

## Reverse Proxy

nginx is responsible for:

* HTTPS
* Routing requests
* Serving the frontend
* Forwarding API requests

---

## Security

The application uses:

* HTTPS
* JWT Authentication
* Role-Based Access Control
* Private RDS instance
* AWS Secrets Manager
* Environment variables

---

# Deployment Flow

```text
Developer
     │
 GitHub Repository
     │
 Deploy to EC2
     │
 Start Frontend
     │
 Start Backend
     │
 Connect to AWS RDS
     │
 Application Ready
```

---

# Environment Variables

Examples include:

* Database URL
* JWT Secret
* AI API Keys
* AWS Configuration

Sensitive values are never committed to GitHub.

---

# Future Improvements

Potential future enhancements include:

* Docker
* CI/CD with GitHub Actions
* Load Balancer
* Auto Scaling
* CloudWatch Monitoring
* Redis Caching
