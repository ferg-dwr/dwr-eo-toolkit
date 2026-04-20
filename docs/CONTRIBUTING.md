# Contributing to DWR EarthObservation Toolkit

Thank you for your interest in contributing!

This document outlines the process and guidelines for contributing to the project.

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
pytest tests/ --cov=src/dwr_eo_toolkit --cov-report=html
```

## Code Style

We use **Ruff** for all code quality checks - linting, formatting, and import sorting in one tool.

### Formatting & Linting

```bash
# Auto-format code
ruff format src tests

# Check for linting issues
ruff check src tests

# Auto-fix linting issues
ruff check --fix src tests
```

**Configuration:**
- Line length: 100 characters
- Target Python version: 3.8+
- Rules: E, F, W, I, N, UP (see `pyproject.toml` for details)

### Type Hints

Type hints are **required for public APIs**:

```python
# ✅ Good - public method with type hints
def execute(self) -> DownloadResult:
    """Execute the download session."""
    return self.download_all()

# ✅ Good - public function with types
def format_bytes(size_bytes: int) -> str:
    """Format bytes to human-readable string."""
    return f"{size_bytes / 1024 / 1024:.2f} MB"

# ❌ Bad - no return type
def execute(self):
    return self.download_all()
```

**Type checking:**
```bash
mypy src/dwr_eo_toolkit
```

### Pre-Push Checklist

Before pushing to GitHub, run:

```bash
# Format and lint
ruff format src tests
ruff check src tests

# Type check
mypy src/dwr_eo_toolkit

# Run all tests with coverage
pytest tests/ -v --cov=src/dwr_eo_toolkit --cov-report=term-missing
```

Or use our pre-push script:
```bash
./scripts/pre-push-check.sh
```

**Expected:**
- ✅ All formatting passed
- ✅ All linting passed
- ✅ All type hints valid
- ✅ All tests pass
- ✅ Coverage >= 85%

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
- `style:` Code formatting

Example:
```
feat: implement batch download manager

- Add BatchDownloadManager for parallel session execution
- Support pause/resume/cancel operations
- Track progress across multiple sessions
- Add 10 comprehensive unit tests

Closes #45
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
- Python 3.8+
- Use type hints for all public functions and methods
- F-strings for string formatting
- Docstrings for all public APIs

### Testing

- Write tests for all new code
- Aim for 90%+ coverage on new code
- Use pytest for test framework
- Use fixtures from `conftest.py`
- One test = one behavior (single assertion focus)

**Test file naming:**
- `test_*.py` for test files
- Place in `tests/` directory

**Test structure (AAA pattern):**
```python
def test_batch_manager_adds_session(batch_manager, mock_session):
    """Test adding a session to batch manager."""
    # ARRANGE
    initial_count = len(batch_manager.sessions)
    
    # ACT
    batch_manager.add_session(mock_session)
    
    # ASSERT
    assert len(batch_manager.sessions) == initial_count + 1
```

### Documentation

- Docstrings for all public functions/classes
- Google-style docstrings
- README updates when needed
- Inline comments for complex logic only
- Update CONTRIBUTING.md if process changes

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
        ...     url="https://example.com/file.hdf",
        ...     output_dir=Path("./data")
        ... )
        >>> print(success)
        True
    """
```

### Commit Size

- Keep commits focused and atomic
- One feature per commit
- Easy to review, easy to revert if needed
- Each commit should pass all tests

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

### Using Fixtures

Use pytest fixtures for test setup:

```python
@pytest.fixture
def batch_manager():
    """Create a BatchDownloadManager for testing."""
    return BatchDownloadManager(max_concurrent_sessions=2)

@pytest.fixture
def mock_session():
    """Create a mock DownloadSession."""
    session = DownloadSession()
    for i in range(3):
        task = DownloadTask(...)
        session.add_task(task)
    return session

# Use them in tests:
def test_add_session(batch_manager, mock_session):
    batch_manager.add_session(mock_session)
    assert len(batch_manager.sessions) == 1
```

## Pull Request Checklist

Before submitting:
- [ ] All tests pass locally (`pytest tests/ -v`)
- [ ] Code formatted (`ruff format src tests`)
- [ ] Linting passes (`ruff check src tests`)
- [ ] Type checking passes (`mypy src/dwr_eo_toolkit`)
- [ ] Coverage >= 85% for new code
- [ ] Docstrings added for public APIs
- [ ] No debug prints or commented code
- [ ] No accidental changes to other files
- [ ] Updated relevant documentation
- [ ] Commit messages follow convention

## Review Process

1. **Automatic Checks (GitHub Actions)**
   - CI/CD pipeline runs tests
   - Linting and formatting checks
   - Type checking validation
   - Coverage must not decrease
   - All checks must pass ✅

2. **Code Review**
   - At least one maintainer review required
   - Constructive feedback provided
   - Changes requested addressed
   - Approval granted

3. **Merge**
   - PR merged to develop branch
   - Feature branch deleted
   - Commit added to changelog (if applicable)

## Development Tools

### Recommended IDE Extensions (VS Code)
- `ms-python.python` - Python extension
- `ms-python.vscode-pylance` - Type checking
- `charliermarsh.ruff` - Ruff integration
- `ms-vscode.makefile-tools` - Makefile support
- `mhutchie.git-graph` - Git visualization

### Useful Commands
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests with coverage report
pytest tests/ --cov=src/dwr_eo_toolkit --cov-report=html

# Format code with Ruff
ruff format src tests

# Check code quality with Ruff
ruff check src tests

# Type checking with mypy
mypy src/dwr_eo_toolkit

# Pre-push checklist
./scripts/pre-push-check.sh
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
- Questions or clarifications

Include:
- Clear description
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Python version, OS, environment
- Error traces/logs

## Questions?

- Create a discussion on GitHub
- Open an issue for clarification
- Comment on related PRs
- Check existing documentation
- Review previous issues and PRs

---

## Project Structure for Reference

```
dwr-eo-toolkit/
├── src/dwr_eo_toolkit/
│   ├── download_manager/     Phase 3 batch operations
│   ├── core/                 Core utilities
│   ├── providers/            Data providers
│   └── filters/              Query filters
├── tests/                    Test suite
├── docs/                     Documentation
├── examples/                 Example scripts
├── scripts/                  Utility scripts
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml            Project configuration
├── CONTRIBUTING.md           This file
├── README.md
└── .github/workflows/        GitHub Actions
```

## Release Process

Maintainers only:
1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create pull request to main
4. Get approval and merge
5. Create git tag: `git tag v0.4.0`
6. Push tag: `git push origin v0.4.0`
7. GitHub Actions builds and pushes Docker image
8. Release notes published on GitHub Releases

---

## Key Technologies

- **Python 3.8+** - Implementation language
- **Ruff** - Code quality (linting, formatting, imports)
- **MyPy** - Static type checking
- **Pytest** - Test framework
- **ThreadPoolExecutor** - Parallel downloads
- **APScheduler** - Download scheduling
- **FastAPI** - Web service API (Phase 3 Week 4)

## Further Reading

- [Python Style Guide (PEP 8)](https://www.python.org/dev/peps/pep-0008/)
- [Type Hints (PEP 484)](https://www.python.org/dev/peps/pep-0484/)
- [Docstring Conventions](https://www.python.org/dev/peps/pep-0257/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Pytest Documentation](https://docs.pytest.org/)

---

Thank you for contributing! 🚀