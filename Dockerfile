FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip setuptools wheel
RUN pip install --upgrade pip setuptools wheel \
    -i https://mirrors.aliyun.com/pypi/simple/

# Copy project files EARLY so we can install dependencies
COPY . .

# Install Python dependencies (DO THIS AS ROOT before switching users!)
# Install main dependencies from pyproject.toml
RUN pip install --no-cache-dir -e . \
    -i https://mirrors.aliyun.com/pypi/simple/

# Install dev dependencies (needed for any development tools)
RUN pip install --no-cache-dir -e ".[dev]" \
    -i https://mirrors.aliyun.com/pypi/simple/

# Verify uvicorn is installed
RUN which uvicorn && uvicorn --version

# Create non-root user for security (AFTER pip install!)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Phase 4: Run API
CMD ["uvicorn", "dwr_eo_toolkit.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

































