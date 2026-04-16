# Development Guide

See CONTRIBUTING.md for contribution guidelines.

## Quick Start

```bash
git clone https://github.com/ferg-dwr/dwr-eo-toolkit/
cd dwr-eo-toolkit
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

## Docker Development

```bash
docker-compose up --build
docker-compose exec dwr-eo-toolkit pytest tests/ -v
```

For more details, see CONTRIBUTING.md
