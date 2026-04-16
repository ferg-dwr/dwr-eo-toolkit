# Development Guide

See CONTRIBUTING.md for contribution guidelines.

## Quick Start

```bash
git clone https://github.com/yourusername/nasa-eo-data.git
cd nasa-eo-data
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

## Docker Development

```bash
docker-compose up --build
docker-compose exec nasa-eo-data pytest tests/ -v
```

For more details, see CONTRIBUTING.md
