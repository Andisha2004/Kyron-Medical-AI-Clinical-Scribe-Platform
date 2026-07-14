# Developer Setup

This document provides the exact commands to run the project locally.

## Clone

```bash
git clone https://github.com/Andisha2004/Kyron-Medical-AI-Clinical-Scribe-Platform.git
cd Kyron-Medical-AI-Clinical-Scribe-Platform
```

## Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

## Install Backend Dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

## Configure Environment Files

```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

## Start PostgreSQL

```bash
docker compose -f infrastructure/docker-compose.yml up -d postgres
```

## Run Migrations

```bash
cd backend
source .venv/bin/activate
./.venv/bin/alembic upgrade head
cd ..
```

## Seed Demo Data

```bash
cd backend
source .venv/bin/activate
./.venv/bin/python scripts/seed_demo.py
cd ..
```

## Start Backend

```bash
cd backend
source .venv/bin/activate
./.venv/bin/uvicorn app.main:app --reload
```

## Start Frontend

Open another terminal:

```bash
cd frontend
npm run dev
```

## Run Tests

### Backend

```bash
cd backend
source .venv/bin/activate
./.venv/bin/pytest tests -q
```

### Frontend static checks

```bash
cd frontend
npm run check
```

### Frontend end-to-end tests

```bash
cd frontend
npm run test:e2e
```

## Optional Demo Bootstrap Shortcut

If you need a fast schema bootstrap in a disposable demo database, use:

```bash
cd backend
source .venv/bin/activate
./.venv/bin/python scripts/bootstrap_demo_database.py
```

This is helpful for demo preparation, but Alembic remains the main migration
path.
