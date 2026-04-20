FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies (with dev tools for testing)
RUN pip install --no-cache-dir -e ".[dev]"

# Create non-root user for security (optional, can comment out for CI)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Default command - run tests
# Phase 3: Runs test suite
# Phase 4: Will run API server (CMD ["uvicorn", "dwr_eo_toolkit.api:app", "--host", "0.0.0.0"])
CMD ["pytest", "tests/", "-v", "--tb=short"]