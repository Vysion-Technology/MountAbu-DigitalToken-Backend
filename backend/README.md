# Mount Abu E-Token Management System - Backend

## Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 15
- **Authentication**: JWT + OTP
- **No Redis/RabbitMQ needed** - Simple stack for ~500 requests/year

## Quick Start

### 1. Setup Environment

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install poetry
poetry install
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your database credentials
```

### 3. Setup Database

```bash
# Create PostgreSQL database
createdb mountabu_etoken

# Run migrations (on first run, tables auto-create in dev mode)
```

### 4. Run Development Server

```bash
# Using uvicorn directly
uvicorn app.main:app --reload --port 8000

# Or using poetry
poetry run uvicorn app.main:app --reload --port 8000
```

### 5. Access API

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API route handlers
│   │       │   ├── auth.py
│   │       │   ├── users.py
│   │       │   ├── applications.py
│   │       │   ├── tokens.py
│   │       │   ├── blacklist.py
│   │       │   └── reports.py
│   │       ├── deps.py         # Dependencies (auth)
│   │       └── router.py       # API router
│   ├── core/
│   │   ├── config.py           # Settings
│   │   ├── database.py         # DB connection
│   │   └── security.py         # JWT, passwords
│   ├── models/
│   │   └── models.py           # SQLAlchemy models
│   ├── schemas/
│   │   └── schemas.py          # Pydantic schemas
│   ├── services/
│   │   ├── application_service.py
│   │   ├── blacklist_service.py
│   │   ├── token_service.py
│   │   └── sms_service.py
│   └── main.py                 # FastAPI app
├── tests/
├── alembic/                    # Migrations
├── pyproject.toml
├── .env.example
└── README.md
```

## Key Features

### 1. Authentication
- OTP-based login for applicants (mobile)
- Password + OTP for authorities (email)
- JWT access/refresh tokens

### 2. Application Workflow
- Create, list, view applications
- Authority actions: approve, reject, forward
- Timeline tracking

### 3. Token Management
- Auto-generate tokens on approval
- QR code generation
- Share tokens with drivers
- Naka checkpoint scanning

### 4. Blacklist System (Critical Feature)
- **Auto-blacklist after 3 consecutive rejections**
- Warning issued at 2 rejections
- Counter resets on approval
- Manual whitelist by SDM/CMS only

## API Endpoints Summary

| Category | Endpoints |
|----------|-----------|
| Auth | `POST /auth/login`, `/verify-otp`, `/refresh`, `/logout` |
| Users | `GET/PUT /users/profile`, `GET /users/authorities` |
| Applications | `POST/GET /applications`, `GET /:id`, `POST /:id/approve`, `POST /:id/reject`, `POST /:id/forward` |
| Tokens | `GET /tokens`, `GET /:id`, `POST /:id/share`, `POST /tokens/scan` |
| Blacklist | `GET /blacklist`, `GET /:userId/history`, `POST /:userId/whitelist` |
| Reports | `GET /reports/applications`, `/tokens`, `/vehicles` |

## Development

```bash
# Format code
black app/
ruff check app/ --fix

# Type checking
mypy app/

# Run tests
pytest
```

## Deployment

```bash
# Production run
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

# With Docker
docker build -t mountabu-api .
docker run -p 8000:8000 mountabu-api
```
