# Deployment Guide

## Quick Start with Docker Compose

The easiest way to get started is using Docker Compose, which includes both the API and PostgreSQL database.

### Prerequisites
- Docker and Docker Compose installed
- NASA Earthdata credentials

### Setup Steps

1. **Clone and navigate to the project:**
```bash
git clone https://github.com/ferg-dwr/dwr-eo-toolkit.git
cd dwr-eo-toolkit
```

2. **Create environment file:**
```bash
cp .env.example .env
```

3. **Edit `.env` with your values:**
```bash
# Database
POSTGRES_DB=dwr_eo_toolkit_dev
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://postgres:your_secure_password@postgres:5432/dwr_eo_toolkit_dev

# API
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=your_secret_key_here

# NASA Earthdata
EARTHDATA_TOKEN=your_60day_token_here

# Logging
LOG_LEVEL=INFO
PYTHONUNBUFFERED=1
```

4. **Start Docker services:**
```bash
docker compose up --build
```

The API will be available at `http://localhost:8000`

### Verify Installation

**Check API health:**
```bash
curl http://localhost:8000/health
```

**View API documentation:**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

**Access database:**
```bash
docker compose exec postgres psql -U postgres -d dwr_eo_toolkit_dev
```

## Environment Variables Reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `EARTHDATA_TOKEN` | Yes | - | NASA Earthdata 60-day token |
| `SECRET_KEY` | Yes | - | FastAPI secret key for sessions |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity (DEBUG, INFO, WARNING) |
| `API_HOST` | No | `0.0.0.0` | API binding address |
| `API_PORT` | No | `8000` | API port |
| `POSTGRES_DB` | No | `dwr_eo_toolkit_dev` | PostgreSQL database name |
| `POSTGRES_USER` | No | `postgres` | PostgreSQL user |
| `POSTGRES_PASSWORD` | Yes | - | PostgreSQL password |

## Production Deployment

### Docker Image

Build and push to Docker Hub:
```bash
docker build -t fergdwr/dwr-eo-toolkit:latest .
docker push fergdwr/dwr-eo-toolkit:latest
```

### Environment-Specific Configuration

For production, update the Dockerfile to:
- Remove `--reload` flag from uvicorn
- Use official PyPI mirrors
- Only install production dependencies
- Add health checks

### Kubernetes (Future)

Kubernetes manifests are planned for Phase 4C. See [issue #43](https://github.com/ferg-dwr/dwr-eo-toolkit/issues/43).

## Database Migrations

Migrations are handled by Alembic. To run migrations:

```bash
# Using Docker Compose
docker compose exec dwr-eo-toolkit alembic upgrade head

# Or directly
alembic upgrade head
```

## Troubleshooting

**Port already in use:**
```bash
# Change port in docker-compose.yml
# Or kill existing process
lsof -i :8000
kill -9 <PID>
```

**Database connection failed:**
- Check `DATABASE_URL` format
- Verify PostgreSQL is running: `docker compose logs postgres`
- Check credentials in `.env`

**API startup errors:**
- Check logs: `docker compose logs dwr-eo-toolkit`
- Verify all required environment variables are set
- Ensure database migrations ran successfully