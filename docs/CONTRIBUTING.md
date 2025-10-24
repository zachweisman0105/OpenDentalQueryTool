# Contributing to OpenDental Multi-Office Query Tool

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Code Standards](#code-standards)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Security](#security)

---

## Code of Conduct

### Our Pledge

We are committed to providing a welcoming and inspiring community for all. We expect all contributors to:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

### Unacceptable Behavior

- Harassment, trolling, or discriminatory language
- Publishing private information without permission
- Professional misconduct or unethical behavior

---

## Getting Started

### Prerequisites

- **Python 3.11+** (3.13 recommended)
- **Git** (2.30+)
- **Basic understanding** of:
  - Python development
  - SQL queries
  - REST APIs
  - Encryption concepts

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork:
git clone https://github.com/YOUR_USERNAME/opendental-query-tool.git
cd opendental-query-tool

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/opendental-query-tool.git
```

---

## Development Setup

### 1. Create Virtual Environment

```bash
# Create virtual environment
python -m venv .venv

# Activate (Linux/Mac)
source .venv/bin/activate

# Activate (Windows PowerShell)
.venv\Scripts\activate

# Activate (Windows CMD)
.venv\Scripts\activate.bat
```

### 2. Install Development Dependencies

```bash
# Install all dependencies including dev tools
pip install -r requirements/dev.txt

# Install pre-commit hooks
pre-commit install
```

### 3. Verify Installation

```bash
# Run tests
pytest tests/

# Check formatting
black --check src/ tests/

# Run linter
ruff check src/ tests/

# Type checking
mypy src/
```

---

## Development Workflow

### 1. Create a Feature Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/your-feature-name
```

**Branch naming conventions:**
- `feature/` - New features
- `bugfix/` - Bug fixes
- `hotfix/` - Urgent production fixes
- `docs/` - Documentation only
- `test/` - Test additions/improvements
- `refactor/` - Code refactoring

### 2. Make Changes

```bash
# Edit code
vim src/opendental_query/core/vault.py

# Run tests frequently
pytest tests/unit/test_vault.py -v

# Format code
black src/ tests/

# Check linting
ruff check src/ tests/
```

### 3. Commit Changes

```bash
# Stage changes
git add src/opendental_query/core/vault.py tests/unit/test_vault.py

# Commit with descriptive message
git commit -m "feat: add vault backup functionality

- Add backup_vault() method to VaultManager
- Include timestamp in backup filename
- Add tests for backup functionality
- Update documentation

Closes #123"
```

**Commit message format:**
```
<type>: <short summary>

<detailed description>

<footer>
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `style` - Formatting, missing semicolons, etc.
- `refactor` - Code restructuring
- `test` - Adding tests
- `chore` - Maintenance tasks

### 4. Push and Create PR

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create Pull Request on GitHub
# Use PR template
```

---

## Testing Guidelines

### Test Structure

```
tests/
├── unit/           # Fast, isolated tests
├── integration/    # Multi-component tests
└── fixtures/       # Test data
```

### Writing Tests

```python
# tests/unit/test_vault.py
import pytest
from opendental_query.core.vault import VaultManager

class TestVaultManager:
    """Test suite for VaultManager."""
    
    def test_vault_initialization(self, tmp_path):
        """Test vault creation with master password."""
        vault_path = tmp_path / "test_vault.enc"
        vault = VaultManager.create_vault(vault_path, "SecurePassword123!")
        
        assert vault.is_locked()
        vault.unlock("SecurePassword123!")
        assert vault.is_unlocked()
    
    def test_add_office_credentials(self, vault_manager):
        """Test adding office credentials."""
        vault_manager.add_office(
            office_name="TestOffice",
            customer_key="test_key_123"
        )
        
        creds = vault_manager.get_office_credential("TestOffice")
        assert creds.customer_key == "test_key_123"
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/unit/test_vault.py

# Run specific test
pytest tests/unit/test_vault.py::TestVaultManager::test_vault_initialization

# Run with coverage
pytest --cov=src/opendental_query --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/
```

### Coverage Requirements

- **Minimum coverage:** 80%
- **New code:** 90% coverage required
- **Critical paths:** 100% coverage (vault, security, audit)

```bash
# Check coverage
pytest --cov=src/opendental_query --cov-report=term-missing

# Generate HTML report
pytest --cov=src/opendental_query --cov-report=html
open htmlcov/index.html
```

---

## Code Standards

### Python Style Guide

We follow **PEP 8** with some modifications:

```python
# Line length: 100 characters (not 79)
# String quotes: Double quotes preferred
# Import order: stdlib, third-party, local

# Good
def execute_query(sql: str, timeout: int = 30) -> QueryResult:
    """Execute SQL query against OpenDental API.
    
    Args:
        sql: SELECT query to execute
        timeout: Query timeout in seconds
        
    Returns:
        QueryResult with data and metadata
        
    Raises:
        InvalidQueryError: If query is not SELECT
        QueryTimeoutError: If query exceeds timeout
    """
    if not sql.strip().upper().startswith("SELECT"):
        raise InvalidQueryError("Only SELECT queries allowed")
    
    return self._execute(sql, timeout)
```

### Type Hints

All public functions must have type hints:

```python
from typing import List, Optional, Dict, Any

def merge_results(
    results: List[QueryResult],
    sort_column: Optional[str] = None
) -> MergedQueryResult:
    """Merge results from multiple offices."""
    ...
```

### Docstrings

Use **Google-style docstrings**:

```python
def add_office(self, office_name: str, customer_key: str) -> None:
    """Add office credentials to vault.
    
    Args:
        office_name: Unique office identifier
        customer_key: OpenDental customer key
        
    Raises:
        VaultLockedError: If vault is locked
        ValueError: If office already exists
        
    Example:
        >>> vault.add_office("MainOffice", "key123")
    """
    ...
```

### Error Handling

```python
# Good: Specific exceptions
try:
    vault.unlock(password)
except VaultLockedError:
    logger.error("Vault locked due to failed attempts")
    raise
except ValueError:
    logger.warning("Invalid password format")
    raise

# Bad: Bare except
try:
    vault.unlock(password)
except:  # Don't do this
    pass
```

### Logging

```python
import logging

logger = logging.getLogger(__name__)

# Use appropriate log levels
logger.debug("Executing query: %s", sql)  # Verbose details
logger.info("Query completed in %.2fs", duration)  # General info
logger.warning("Query timeout approaching")  # Potential issues
logger.error("Query failed: %s", error)  # Errors
logger.critical("Vault corruption detected")  # Critical failures
```

---

## Code Quality Tools

### Black (Formatting)

```bash
# Format code
black src/ tests/

# Check without modifying
black --check src/ tests/

# Configuration in pyproject.toml:
[tool.black]
line-length = 100
target-version = ['py311']
```

### Ruff (Linting)

```bash
# Run linter
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Configuration in pyproject.toml:
[tool.ruff]
line-length = 100
select = ["E", "F", "W", "I", "N", "UP", "S", "B", "A", "C4", "DTZ", "T10", "DJ", "EM", "EXE", "ISC", "ICN", "PIE", "PYI", "PT", "Q", "RSE", "RET", "SIM", "TID", "ARG", "PTH", "ERA", "PD", "PGH", "PL", "TRY", "NPY", "RUF"]
```

### Mypy (Type Checking)

```bash
# Run type checker
mypy src/

# Configuration in pyproject.toml:
[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_configs = true
disallow_untyped_defs = true
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files

# Configuration in .pre-commit-config.yaml:
repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black
  - repo: https://github.com/astral-sh/ruff-pre-commit
    hooks:
      - id: ruff
  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
```

---

## Documentation

### Code Documentation

- **All public APIs** must have docstrings
- **Complex logic** should have inline comments
- **Security-critical code** needs detailed comments

### User Documentation

When adding features, update:

- `README.md` - Quick start and examples
- `docs/API_REFERENCE.md` - API documentation
- `docs/TROUBLESHOOTING.md` - Common issues
- `CHANGELOG.md` - Version history

### Examples

```python
# Good: Clear, documented code
def validate_query(sql: str) -> None:
    """Validate SQL query for security.
    
    Ensures query is SELECT-only and doesn't contain dangerous keywords.
    This is a critical security control to prevent data modification.
    
    Args:
        sql: SQL query to validate
        
    Raises:
        InvalidQueryError: If query is not SELECT or contains forbidden keywords
    """
    # Remove comments and whitespace
    cleaned = self._clean_query(sql)
    
    # Check for SELECT
    if not cleaned.upper().startswith("SELECT"):
        raise InvalidQueryError("Only SELECT queries are allowed")
    
    # Check for forbidden keywords (UPDATE, DELETE, DROP, etc.)
    forbidden = ["UPDATE", "DELETE", "INSERT", "DROP", "ALTER", "CREATE"]
    for keyword in forbidden:
        if keyword in cleaned.upper():
            raise InvalidQueryError(f"Forbidden keyword: {keyword}")
```

---

## Pull Request Process

### Before Submitting

- [ ] All tests pass locally
- [ ] Code is formatted with Black
- [ ] No linting errors (Ruff)
- [ ] Type checking passes (Mypy)
- [ ] Coverage meets requirements (80%+)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated

### PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
- [ ] No new warnings

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks** run (CI/CD)
2. **Code review** by maintainers
3. **Changes requested** (if needed)
4. **Approval** from 1+ maintainers
5. **Merge** to main branch

### After Merge

```bash
# Update your fork
git checkout main
git pull upstream main
git push origin main

# Delete feature branch
git branch -d feature/your-feature-name
git push origin --delete feature/your-feature-name
```

---

## Security

### Reporting Vulnerabilities

**DO NOT** open public issues for security vulnerabilities.

Instead, email: **security@example.com**

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Security Guidelines

- **Never commit secrets** (API keys, passwords)
- **Sanitize logs** (no PHI, no credentials)
- **Test security features** thoroughly
- **Follow HIPAA guidelines** for PHI handling

---

## Questions?

- **GitHub Discussions**: Ask questions
- **GitHub Issues**: Report bugs, request features
- **Email**: dev@example.com

---

**Thank you for contributing!**
