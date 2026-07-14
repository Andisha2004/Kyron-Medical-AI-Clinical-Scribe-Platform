# Phase 12 Infrastructure

This folder contains the production-facing infrastructure artifacts for the
Kyron Medical Clinical Assistant project.

Important:

- The repository is now AWS-ready, but it does not automatically provision AWS.
- This is intentional so the project can remain cost-safe during development.
- The default working environment remains local Docker + local PostgreSQL.

## Cost-safe recommendation

If your goal is to keep the system working without introducing AWS charges,
stop at the local environment and use this folder as a deployment blueprint.

The infrastructure files here are meant to help you:

- explain a production architecture in interviews and demos
- deploy later if you choose
- avoid improvising nginx/systemd/secrets decisions

## Production target architecture

```text
Internet
  -> EC2 public entry point
  -> nginx
  -> Next.js and FastAPI on localhost
  -> private RDS PostgreSQL
```

## What is included here

- `nginx/kyron.conf`
  - reverse proxy for frontend, backend, SSE, and WebSocket routes
- `systemd/kyron-api.service`
  - FastAPI process management
- `systemd/kyron-frontend.service`
  - Next.js process management
- `scripts/deploy.sh`
  - baseline EC2 deployment script
- `scripts/check-infra.sh`
  - quick verification checklist for a live EC2 host
- `architecture.md`
  - AWS network and deployment design
- `.env.production.example`
  - production-safe variable template with no secrets

## Cost notes

This phase is where real AWS costs can begin.

Potential cost sources include:

- EC2 runtime
- RDS runtime and storage
- NAT Gateway if you use one
- public IPv4 / data transfer
- Route 53 domain and DNS

If you want a fully cost-free version, use:

- local Docker PostgreSQL
- local frontend/backend processes
- local nginx only if you want to test reverse proxying
- no AWS deployment

## Suggested production region

Default assumption in this repo:

- `us-east-1`

Reason:

- already matches backend defaults
- common AWS region with broad service availability
- easy to explain during a demo

This is a practical default, not a guarantee of the lowest possible price.
