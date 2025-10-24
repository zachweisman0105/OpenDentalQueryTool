# OpenDental Query Tool - Development Commands (PowerShell)
# Usage: .\make.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

function Show-Help {
    Write-Host "OpenDental Query Tool - Development Commands" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Setup:" -ForegroundColor Yellow
    Write-Host "  install          Install package in production mode"
    Write-Host "  install-dev      Install package with development dependencies"
    Write-Host ""
    Write-Host "Testing:" -ForegroundColor Yellow
    Write-Host "  test             Run all tests"
    Write-Host "  test-unit        Run unit tests only"
    Write-Host "  test-integration Run integration tests only"
    Write-Host "  coverage         Run tests with coverage report"
    Write-Host ""
    Write-Host "Code Quality:" -ForegroundColor Yellow
    Write-Host "  lint             Run ruff linter"
    Write-Host "  format           Format code with black"
    Write-Host "  format-check     Check code formatting without changes"
    Write-Host "  type-check       Run mypy type checker"
    Write-Host "  security         Run bandit security scanner"
    Write-Host "  quality          Run all code quality checks"
    Write-Host ""
    Write-Host "Build:" -ForegroundColor Yellow
    Write-Host "  clean            Remove build artifacts"
    Write-Host "  build            Build distribution packages"
    Write-Host "  build-exe        Build standalone executable with PyInstaller"
    Write-Host "  docs             Generate documentation"
    Write-Host ""
    Write-Host "Utilities:" -ForegroundColor Yellow
    Write-Host "  pre-commit       Install pre-commit hooks"
    Write-Host "  update-deps      Update requirements files"
}

function Install-Package {
    Write-Host "Installing package..." -ForegroundColor Green
    pip install -e .
}

function Install-Dev {
    Write-Host "Installing development dependencies..." -ForegroundColor Green
    pip install -r requirements/dev.txt
    pip install -e .
}

function Run-Tests {
    Write-Host "Running all tests..." -ForegroundColor Green
    pytest tests/ -v
}

function Run-UnitTests {
    Write-Host "Running unit tests..." -ForegroundColor Green
    pytest tests/unit/ -v
}

function Run-IntegrationTests {
    Write-Host "Running integration tests..." -ForegroundColor Green
    pytest tests/integration/ -v
}

function Run-Coverage {
    Write-Host "Running tests with coverage..." -ForegroundColor Green
    pytest tests/ --cov=opendental_query --cov-report=html --cov-report=term
    Write-Host "Coverage report: htmlcov\index.html" -ForegroundColor Cyan
}

function Run-Lint {
    Write-Host "Running linter..." -ForegroundColor Green
    ruff check src/ tests/
}

function Run-LintFix {
    Write-Host "Running linter with auto-fix..." -ForegroundColor Green
    ruff check --fix src/ tests/
}

function Run-Format {
    Write-Host "Formatting code..." -ForegroundColor Green
    black src/ tests/
}

function Check-Format {
    Write-Host "Checking code formatting..." -ForegroundColor Green
    black --check src/ tests/
}

function Run-TypeCheck {
    Write-Host "Running type checker..." -ForegroundColor Green
    mypy src/
}

function Run-Security {
    Write-Host "Running security scanner..." -ForegroundColor Green
    bandit -c pyproject.toml -r src/
}

function Run-Quality {
    Write-Host "Running all quality checks..." -ForegroundColor Green
    Check-Format
    Run-Lint
    Run-TypeCheck
    Run-Security
    Write-Host "All quality checks passed!" -ForegroundColor Green
}

function Clean-Build {
    Write-Host "Cleaning build artifacts..." -ForegroundColor Green
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue build, dist, *.egg-info, htmlcov, .pytest_cache, .coverage, coverage.xml
    Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -File -Include *.pyc,*.pyo | Remove-Item -Force -ErrorAction SilentlyContinue
}

function Build-Package {
    Write-Host "Building package..." -ForegroundColor Green
    Clean-Build
    python -m build
    twine check dist/*
}

function Build-Executable {
    Write-Host "Building standalone executable..." -ForegroundColor Green
    python packaging/pyinstaller/build.py
}

function Show-Docs {
    Write-Host "Documentation is in docs/ directory:" -ForegroundColor Cyan
    Write-Host "  - README.md"
    Write-Host "  - SECURITY.md"
    Write-Host "  - API_REFERENCE.md"
    Write-Host "  - TROUBLESHOOTING.md"
    Write-Host "  - CONTRIBUTING.md"
}

function Install-PreCommit {
    Write-Host "Installing pre-commit hooks..." -ForegroundColor Green
    pre-commit install
    Write-Host "Pre-commit hooks installed!" -ForegroundColor Green
}

function Update-Dependencies {
    Write-Host "Updating requirements files..." -ForegroundColor Green
    pip-compile requirements/base.in -o requirements/base.txt
    pip-compile requirements/dev.in -o requirements/dev.txt
    pip-compile requirements/test.in -o requirements/test.txt
}

# Command dispatcher
switch ($Command.ToLower()) {
    "help" { Show-Help }
    "install" { Install-Package }
    "install-dev" { Install-Dev }
    "test" { Run-Tests }
    "test-unit" { Run-UnitTests }
    "test-integration" { Run-IntegrationTests }
    "coverage" { Run-Coverage }
    "lint" { Run-Lint }
    "lint-fix" { Run-LintFix }
    "format" { Run-Format }
    "format-check" { Check-Format }
    "type-check" { Run-TypeCheck }
    "security" { Run-Security }
    "quality" { Run-Quality }
    "clean" { Clean-Build }
    "build" { Build-Package }
    "build-exe" { Build-Executable }
    "docs" { Show-Docs }
    "pre-commit" { Install-PreCommit }
    "update-deps" { Update-Dependencies }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Run '.\make.ps1 help' for available commands" -ForegroundColor Yellow
        exit 1
    }
}
