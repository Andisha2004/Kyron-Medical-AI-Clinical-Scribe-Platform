# Security Documentation

## Authentication Approach

The backend authenticates users with email and password and issues a JWT access
token after successful login. The token is stored in an HTTP-only cookie so the
frontend does not need direct access to the token value.

Relevant implementation:

- [backend/app/core/security.py](../backend/app/core/security.py)
- [backend/app/core/config.py](../backend/app/core/config.py)

Important behavior:

- cookie-based session transport
- JWT expiration support
- generic invalid-credential responses
- active-user checks on protected routes

## Authorization Approach

Authorization is enforced in the backend through role-aware dependencies and
resource ownership checks.

Core rules:

- only authenticated users may access protected routes
- provider routes require provider role
- admin routes require admin role
- encounter access is filtered by both encounter id and provider id
- providers cannot read or modify other providers’ encounters or drafts

This reduces the risk of trusting a frontend route or encounter id alone.

## Private RDS

The production deployment design assumes a private PostgreSQL RDS instance that
is reachable only from the EC2 application host or its security group.

Expected production properties:

- RDS `Publicly accessible: No`
- RDS in private subnets only
- inbound `5432/tcp` allowed only from the EC2 security group

Reference:

- [infrastructure/architecture.md](../infrastructure/architecture.md)

## Secret Management

Local development uses ignored `.env` files. Production is designed to load
runtime secrets from AWS rather than commit them to the repository.

Supported runtime secret configuration:

- `AWS_USE_RUNTIME_SECRETS`
- `AWS_SECRETS_MANAGER_SECRET_ID`
- `AWS_PARAMETER_STORE_PATH`

Security expectations:

- no production credentials committed to Git
- EC2 role should have least-privilege read access only
- secrets should never be printed to logs

## Password Hashing

Passwords are hashed with Argon2 through Passlib and are never stored as
plaintext.

Implementation detail:

- `CryptContext(schemes=["argon2"], deprecated="auto")`

This applies to both seeded demo accounts and normal application users.

## Clinical Log Minimization

The system uses structured logging and audit logging, but the intended approach
is to minimize sensitive clinical content in logs.

Guidelines for this repo:

- log operational state, not full notes
- avoid storing full clinical note bodies in audit metadata
- avoid printing secrets or raw tokens
- use synthetic or non-sensitive demo content during development

## Synthetic Demo Data

The repository seed data is synthetic and intended for demonstration only.

Examples:

- demo users with shared development passwords
- fictional patients
- local ICD sample dataset

Do not replace these with real patient-identifying information in a prototype
environment.

## Known Prototype Limitations

This project is a strong prototype, but it is not a production-ready medical
deployment by itself.

Known limitations:

- no claim of HIPAA compliance from this repo alone
- no formal production secret-rotation workflow implemented in-repo
- no production-grade audit retention policy documented yet
- local and mocked AI flows may differ from production vendor behavior
- browser/device microphone permissions and realtime voice behavior depend on
  runtime environment and provider configuration
