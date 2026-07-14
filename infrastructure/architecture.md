# AWS Infrastructure Design

## Goal

Deploy the application with a public EC2 reverse proxy and a private RDS
PostgreSQL database while keeping backend ports off the public internet.

## Network layout

```text
Internet
  -> Route 53 / public DNS
  -> EC2 security group (80, 443, optional 22 from your IP only)
  -> EC2 instance in public subnet
  -> nginx
  -> Next.js on localhost:3000
  -> FastAPI on localhost:8000
  -> RDS PostgreSQL in private subnet group
```

## Recommended VPC layout

### Region

- `us-east-1`

### VPC

- One VPC dedicated to the project

### Public subnet

- One public subnet for EC2
- Route table with internet gateway route

### Private database subnets

- Two private subnets in separate availability zones for the RDS subnet group
- No direct public route

### Internet gateway

- Attached to VPC
- Used only by public subnet resources

## Security groups

### EC2 security group

- Allow inbound `80/tcp` from `0.0.0.0/0`
- Allow inbound `443/tcp` from `0.0.0.0/0`
- Allow inbound `22/tcp` only from your IP if SSH is enabled
- Do not allow inbound `3000/tcp`
- Do not allow inbound `8000/tcp`

### RDS security group

- Allow inbound `5432/tcp` only from the EC2 security group
- No public ingress

## Secrets strategy

Preferred production strategy:

- AWS Secrets Manager or SSM Parameter Store
- EC2 IAM role with least-privilege read access
- No production secrets stored in committed `.env` files

Current application support:

- optional runtime secret loading via
  - `AWS_USE_RUNTIME_SECRETS`
  - `AWS_SECRETS_MANAGER_SECRET_ID`
  - `AWS_PARAMETER_STORE_PATH`

## Connection pooling

The backend uses SQLAlchemy async pooling with:

- `DATABASE_POOL_SIZE`
- `DATABASE_MAX_OVERFLOW`
- `DATABASE_POOL_RECYCLE_SECONDS`
- `DATABASE_POOL_PRE_PING`

Recommended production defaults:

```text
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20
DATABASE_POOL_RECYCLE_SECONDS=1800
DATABASE_POOL_PRE_PING=true
```

## Health checks

The API exposes:

- `GET /health`
- `GET /api/health`

These now include:

- service status
- environment
- database status
- database pool configuration summary

## Cost-safe note

This architecture is valid for production discussion and later deployment, but
it is not the recommended path if you want zero cloud spend. For a free
demonstration, keep the app local and use this document as your deployment
blueprint.
