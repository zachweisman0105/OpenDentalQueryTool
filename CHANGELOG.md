# Changelog

All notable changes to the OpenDental Multi-Office Query Tool will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **Vault management commands**
  - `VaultClear` / `vault clear` - Remove all offices while keeping vault and DeveloperKey intact
  - `VaultDestroy` / `vault destroy` - Completely delete the vault file
  - CLI aliases: `reset` (for clear) and `delete` (for destroy)
  - Both commands support `-y/--yes` flag to skip confirmation prompts
- **Bulk office addition** - Add multiple offices to vault with a single command
  - Use comma-separated office IDs: `VaultAdd office1,office2,office3`
  - Prompts for each office's CustomerKey, then master password once
  - Shows summary of successful and failed additions
- Single-word command shortcuts for faster typing (e.g., `Query`, `VaultInit`, `ConfigList`)
  - Main shortcuts: `Query`, `Vault`, `Config`, `Update`
  - Vault shortcuts: `VaultInit`, `VaultAdd`, `VaultRemove`, `VaultList`, `VaultUpdateKey`
  - Config shortcuts: `ConfigGet`, `ConfigSet`, `ConfigList`, `ConfigReset`, `ConfigPath`
- CLI subcommand aliases for streamlined usage (e.g., `opendental-query v init`)
  - Top-level aliases: `v` (vault), `c` (config), `q` (query), `update` (check-update)
  - Vault subcommand aliases: `add`, `remove`, `rm`, `list`, `ls`, `update-key`
  - Config subcommand aliases: `ls` (list)
- New `shortcuts.py` module providing entry points for single-word commands
- Comprehensive documentation for all command shortcuts and aliases
- Updated documentation in README.md, quickstart.md, and new COMMAND_ALIASES.md

### Changed
- `opendental-query query` now forwards all SQL statements to the OpenDental API, allowing the server to decide whether a statement is permitted.

### Planned
- Software update checker (GitHub releases integration)
- CI/CD pipeline (automated testing and releases)
- PyPI package distribution
- Automated publishing of PyInstaller-built executables (Windows, macOS, Linux)
- Enhanced Excel UX with openpyxl renderer

---
## [1.0.1] - 2025-10-24

### Added
- PyInstaller build script and packaging docs for creating standalone executables.
- `Query` console entry point as a shorthand for `opendental-query query`.

### Changed
- Audit log now stores SHA256 query hashes only and automatically records hostname, IP address, and a per-session identifier.
- `opendental-query query` enforces read-only SQL (SELECT/SHOW/DESCRIBE/EXPLAIN) and rejects mutating statements before execution.
- Retry backoff logging uses structured warnings with sanitized HTTP context instead of printing raw responses.

---

## [1.0.0] - 2025-01-XX

### Added

#### Core Features
- **Multi-office query execution** across multiple OpenDental databases
- **Secure credential vault** with AES-256-GCM encryption and Argon2id key derivation
- **Interactive CLI** with `vault`, `query`, `config`, and `audit` commands
- **Deterministic result ordering** for consistent multi-office data merging
- **HIPAA-compliant audit logging** with 90-day retention and SHA256 query hashing
- **Auto-lock mechanism** (5-minute default) for vault security
- **Failed authentication protection** (3 attempts → 60-second lockout)
- **Configuration management** with per-user settings persistence

#### Query Features
- SQL query validation (SELECT-only enforcement)
- Parallel query execution across offices
- Query timeout control (30-second default)
- Schema consistency validation
- Empty result handling
- Large result set support
- Unicode and special character handling

#### Export Features
- **Excel export** with table formatting
- **Rich table rendering** in terminal
- Configurable default export directory
- Automatic file timestamp generation

#### Security
- **Vault encryption**: AES-256-GCM with random IV per encryption
- **Key derivation**: Argon2id (time=3, memory=64MB, parallelism=4)
- **Network security**: HTTPS enforcement with TLS 1.2+
- **PHI protection**: No sensitive data in logs (SHA256 hashed queries)
- **Audit trail**: Comprehensive event logging for compliance

#### Documentation
- README.md with quick start guide
- SECURITY.md with HIPAA compliance details
- API_REFERENCE.md with complete Python API documentation
- TROUBLESHOOTING.md with common issues and solutions
- CONTRIBUTING.md with development guidelines

#### Testing
- 323 total tests (295 passing, 91% success rate)
- 66% code coverage
- Comprehensive integration test suite
- Unit tests for all core modules
- Security workflow validation
- Data integrity verification
- Performance benchmarking tests

### Security
- **HIPAA Compliance**: PHI protection, audit logging, encryption at rest
- **Threat Protection**: Credential theft mitigation, brute force prevention, network eavesdropping protection
- **Incident Response**: Documented procedures for compromised credentials

### Developer Experience
- Type hints throughout codebase (mypy strict mode)
- Google-style docstrings
- Black formatting (100-character line length)
- Ruff linting with comprehensive rule set
- Pre-commit hooks for code quality
- pytest with fixtures and parametrization

---

## Development History

### Phase 1: Project Setup
- Repository initialization with Git
- Python 3.11+ requirement
- Virtual environment configuration
- Dependency management (requirements/base.txt, dev.txt, test.txt)
- .gitignore with Python patterns

### Phase 2: Foundational Architecture
- Project structure (`src/opendental_query/`)
- Core modules: `vault`, `query`, `audit`, `config`, `renderer`
- Custom exception hierarchy
- Logging configuration
- Environment variable support

### Phase 3: Vault System (US4)
- VaultManager class with encryption
- Argon2id key derivation
- AES-256-GCM encryption
- Master password authentication
- Office credential storage
- Developer key management
- Vault lock/unlock mechanism
- Failed attempt tracking

### Phase 4: Core Query Engine (US1)
- QueryEngine class
- OpenDental API integration (httpx)
- SQL query validation
- Query execution across multiple offices
- Error handling and retries
- Result data models (QueryResult, MergedQueryResult)
- Schema consistency checks

### Phase 5: Deterministic Ordering (US3)
- Sort key detection from SQL
- Multi-office result merging
- ORDER BY parsing
- Natural sorting implementation
- Edge case handling (empty results, schema mismatches)

### Phase 6: HIPAA Audit Logging (US5)
- AuditLogger class
- JSONL format logging
- 11 event types tracked
- SHA256 query hashing (no PHI in logs)
- 90-day retention policy
- Audit log cleanup command
- Query statistics and reporting

### Phase 7: Subset Query Support (US2)
- --office flag for single/multiple office queries
- Office name validation
- Office list command
- Error handling for invalid office names

### Phase 8: Excel UX (US6)
- TableRenderer with Rich library
- Excel export functionality
- Column formatting
- Large dataset handling
- Export configuration options

### Phase 9: Configuration Management
- ConfigManager class
- JSON config file (~/.opendental-query/config.json)
- `config list`, `set`, `reset` commands
- Default values for all settings
- Type validation
- Environment variable overrides

### Phase 10: Software Updates (US7)
- *(Planned for v1.1.0)*

### Phase 11: Polish and Production Readiness
- Comprehensive test suite
- Security documentation
- API reference documentation
- Troubleshooting guide
- Contributing guidelines
- Code quality enforcement (Black, Ruff, Mypy)

---

## Version Numbering

We use [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: Backwards-compatible functionality additions
- **PATCH**: Backwards-compatible bug fixes

Example: `1.2.3`
- `1` = Major version
- `2` = Minor version
- `3` = Patch version

---

## Release Process

### Pre-release Checklist
1. All tests passing (pytest)
2. Code coverage ≥80%
3. Documentation updated
4. CHANGELOG.md updated
5. Version bumped in `pyproject.toml`
6. Git tag created

### Release Steps
```bash
# 1. Update version
vim pyproject.toml  # Bump version

# 2. Update CHANGELOG
vim CHANGELOG.md  # Move [Unreleased] to [X.Y.Z]

# 3. Commit and tag
git add pyproject.toml CHANGELOG.md
git commit -m "chore: release v1.0.0"
git tag -a v1.0.0 -m "Release version 1.0.0"

# 4. Push
git push origin main --tags

# 5. Build and publish (automated via CI/CD)
```

---

## Upgrade Guide

### From 0.x to 1.0.0

No breaking changes (initial release).

**Fresh Installation:**
```bash
pip install opendental-query-tool

# Initialize vault
opendental-query vault-init

# Add office
opendental-query vault-add-office
```

---

## Support

### Reporting Issues
- **Bugs**: GitHub Issues
- **Security**: security@example.com
- **Questions**: GitHub Discussions

### Compatibility
- **Python**: 3.11, 3.12, 3.13
- **Operating Systems**: Windows 10/11, macOS 11+, Linux (Ubuntu 20.04+)
- **OpenDental API**: Version 24.x+

---

## Contributors

Special thanks to all contributors who helped with this project.

---

## License

Copyright (c) 2025. All rights reserved.

See LICENSE file for details.

---

[Unreleased]: https://github.com/OWNER/opendental-query-tool/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/OWNER/opendental-query-tool/releases/tag/v1.0.0
