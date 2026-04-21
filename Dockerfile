FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip with mirror (bypasses certificate issues)
RUN pip install --upgrade pip setuptools wheel \
    -i https://mirrors.aliyun.com/pypi/simple/

# Copy project files
COPY . .

# Install Python dependencies with mirror
RUN pip install --no-cache-dir -e ".[dev]" \
    -i https://mirrors.aliyun.com/pypi/simple/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Phase 3: Run tests
# Phase 4: Change to API
CMD ["uvicorn", "dwr_eo_toolkit.api:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]