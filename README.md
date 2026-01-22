# Mount Abu E-Token Management System

Smart Digital Token Allocation for New Construction & Renovation

## Overview

This is a comprehensive e-governance solution for the Mount Abu Municipal Council to manage construction material tokens digitally.

## Project Structure

```
AbuCitiServ/
├── docs/                    # Documentation
│   ├── PRD.md              # Product Requirements Document
│   ├── API_SPECIFICATION.md # API Documentation
│   └── DATABASE_SCHEMA.md  # Database Schema
│
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Config, security, database
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── services/       # Business logic
│   └── README.md
│
├── frontend/               # (To be added) Next.js Dashboard
│
└── mobile/                 # (To be added) Flutter App
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Backend API | FastAPI (Python 3.11+) |
| Database | PostgreSQL 15 |
| Frontend | Next.js 14 (planned) |
| Mobile | Flutter (planned) |

## Key Features

1. **Digital Token Management** - QR-based construction material tokens
2. **Multi-Authority Workflow** - SDM, CMS, JEN, Land, Legal, ATP, Naka
3. **Automatic Blacklisting** - 3 consecutive rejections = auto-blacklist
4. **Real-time Tracking** - Application status and Naka entry monitoring
5. **Bilingual Support** - English and Hindi

## Quick Start

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install poetry
poetry install
cp .env.example .env
# Edit .env with your database credentials
uvicorn app.main:app --reload
```

### Access

- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Documentation

- [Product Requirements (PRD)](docs/PRD.md)
- [API Specification](docs/API_SPECIFICATION.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)

## License

Proprietary - Mount Abu Municipal Council
