# Contributing to DWR EarthObservation Toolkit

Thank you for your interest in contributing! This document outlines the process and guidelines for contributing to the project.

## Code of Conduct

- Be respectful to all contributors
- Provide constructive feedback
- Focus on ideas, not personalities
- Help others learn and grow

## Getting Started

### 1. Fork & Clone
```bash
git clone https://github.com/ferg-dwr/dwr-eo-toolkit/
cd dwr-eo-toolkit
```

### 2. Set Up Development Environment
```bash
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

pip install -e ".[dev]"
```

### 3. Create Feature Branch
```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

## Development Workflow

### Make Changes
```bash
# Edit files, add features, fix bugs
```

### Run Tests Locally
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_downloads.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Format Code
```bash
# Format with black
black src tests

# Sort imports
isort src tests

# Check with flake8
flake8 src tests
```

### Commit Changes
```bash
git add -A
git commit -m "feat: add new feature"
```

Use conventional commit format:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `test:` Tests
- `refactor:` Code refactoring
- `perf:` Performance improvement
- `chore:` Build/tooling changes
- `ci:` CI/CD changes

Example:
```
feat: implement parallel download with progress tracking

- Add ThreadPoolExecutor for concurrent downloads
- Implement real-time progress callback
- Add unit tests for progress calculation

Closes #42
```

### Push & Create PR
```bash
git push origin feature/your-feature-name
```

Create a Pull Request on GitHub with:
- Clear title describing the change
- Description of what/why/how
- Reference related issues with `Closes #123`
- Screenshots/examples if applicable

## Code Standards

### Python Version
- Python 3.9+
- Use type hints for all public functions
- F-strings for string formatting

### Testing
- Write tests for all new code
- Aim for 90%+ coverage on new code
- Use pytest for test framework
- Use fixtures from `conftest.py`

### Documentation
- Docstrings for all public functions/classes
- Google-style docstrings
- README updates when needed
- Inline comments for complex logic

Example:
```python
def download_granule(
    url: str,
    output_dir: Path,
    timeout: int = 300,
) -> bool:
    """Download a single granule from NASA.
    
    Args:
        url: URL to download from
        output_dir: Directory to save file to
        timeout: Request timeout in seconds (default: 300)
    
    Returns:
        True if successful, False otherwise
    
    Raises:
        ValueError: If URL is invalid
        ConnectionError: If network fails
    
    Example:
        >>> success = download_granule(
        ...     url="https://...",
        ...     output_dir=Path("./data")
        ... )
    """
```

### Code Style
- Black formatting (line length: 88)
- isort for imports
- flake8 for linting
- Type hints required for public APIs

### Commit Size
- Keep commits focused and atomic
- One feature per commit
- Easy to review, easy to revert if needed

## Testing Guidelines

### Unit Tests
```python
def test_download_task_creation():
    """Test DownloadTask can be created with required fields."""
    task = DownloadTask(
        url="https://example.com/file.hdf",
        output_path=Path("/tmp/file.hdf"),
    )
    
    assert task.url == "https://example.com/file.hdf"
    assert task.status == TaskStatus.PENDING
```

### Integration Tests
```python
def test_download_manager_downloads_files(tmp_path):
    """Test DownloadManager successfully downloads multiple files."""
    manager = DownloadManager(max_workers=2)
    granules = [...]
    
    result = manager.download(granules, str(tmp_path))
    
    assert result.successful >= 1
    assert result.failed == 0
```

### Test File Naming
- `test_*.py` for test files
- `*_test.py` also acceptable
- Organize by module being tested

## Pull Request Checklist

Before submitting:
- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] Code formatted (`black src tests`)
- [ ] Imports sorted (`isort src tests`)
- [ ] Linting passes (`flake8 src tests`)
- [ ] Docstrings added for public APIs
- [ ] No debug prints or commented code
- [ ] Updated relevant documentation
- [ ] Commit messages follow convention

## Review Process

1. **Automatic Checks**
   - CI/CD pipeline runs tests
   - Coverage must not decrease
   - All checks must pass

2. **Code Review**
   - At least one maintainer review required
   - Constructive feedback provided
   - Changes requested addressed
   - Approval granted

3. **Merge**
   - PR merged to develop branch
   - Feature branch deleted
   - Commit added to changelog

## Development Tools

### Recommended IDE Extensions (VS Code)
- `ms-python.python`
- `ms-python.vscode-pylance`
- `charliermarsh.ruff`
- `ms-vscode.makefile-tools`
- `mhutchie.git-graph`

### Useful Commands
```bash
# Create virtual environment
python3 -m venv venv

# Activate environment
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Format code
black src tests && isort src tests

# Check code quality
flake8 src tests

# Build documentation
cd docs && make html
```

## Docker Development

### Local Testing in Docker
```bash
docker-compose up --build
docker-compose exec dwr-eo-toolkit pytest tests/ -v
docker-compose down
```

### Building Image
```bash
docker build -t dwr-eo-toolkit:latest .
docker run --rm dwr-eo-toolkit:latest pytest tests/ -v
```

## Reporting Issues

Create an issue for:
- Bug reports
- Feature requests
- Documentation improvements
- Performance concerns

Include:
- Clear description
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Python version, OS, environment
- Error traces/logs

## Documentation

Help improve documentation:
- Fix typos
- Clarify confusing sections
- Add examples
- Improve API documentation
- Update README

## Questions?

- Create a discussion on GitHub
- Open an issue for clarification
- Comment on related PRs
- Check existing documentation

---

## Project Structure for Reference

```
dwr-eo-toolkit/
├── src/dwr_eo_toolkit/
│   ├── download_manager/     ← Phase 3 features
│   ├── core/
│   ├── providers/
│   └── filters/
├── tests/
├── docs/
├── examples/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .github/workflows/
```

## Release Process

Maintainers only:
1. Update version in `pyproject.toml`
2. Update CHANGELOG
3. Merge to main
4. Create git tag: `git tag v0.3.0`
5. Push tag: `git push origin v0.3.0`
6. GitHub Actions builds and pushes Docker image
7. Release notes published

---

Thank you for contributing! 🚀

Your contributions make this project better for everyone.
