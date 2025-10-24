# Documentation Index

Welcome to the OpenDental Multi-Office Query Tool documentation.

---

## 📚 Documentation Files

### User Documentation

- **[README.md](../README.md)** - Quick start guide and basic usage
  - Installation instructions
  - Quick start (4 steps)
  - Basic query examples
  - Table rendering examples

- **[SECURITY.md](SECURITY.md)** - Security and HIPAA compliance
  - Security architecture (encryption, auto-lock, authentication)
  - HIPAA compliance details (PHI protection, audit trail)
  - Network security (HTTPS, TLS, API authentication)
  - Threat model and limitations
  - Best practices for secure usage
  - Audit and monitoring procedures
  - Incident response procedures
  - Security testing verification

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
  - Installation issues
  - Vault problems (locked, permissions, authentication)
  - Query execution errors
  - Data/result issues
  - Export problems
  - Performance tuning
  - Platform-specific issues (Windows, macOS, Linux)
  - Diagnostic commands
  - Getting help

### Developer Documentation

- **[API_REFERENCE.md](API_REFERENCE.md)** - Complete Python API documentation
  - Core modules (VaultManager, QueryEngine, ConfigManager, AuditLogger)
  - Renderers (TableRenderer, CSVExporter)
  - Data models (QueryResult, MergedQueryResult, etc.)
  - Exceptions
  - CLI commands
  - Configuration keys
  - Environment variables
  - Testing guide

- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contribution guidelines
  - Code of conduct
  - Development setup (virtual environment, dependencies, tools)
  - Development workflow (branching, commits, PR process)
  - Testing guidelines (writing tests, coverage requirements)
  - Code standards (Python style, type hints, docstrings)
  - Code quality tools (Black, Ruff, Mypy, pre-commit)
  - Documentation requirements
  - Security reporting

### Project Documentation

- **[CHANGELOG.md](../CHANGELOG.md)** - Version history
  - Release notes
  - Version numbering (semantic versioning)
  - Release process
  - Upgrade guides
  - Compatibility information

---

## 🚀 Quick Links

### Getting Started
1. Read [README.md](../README.md) for installation and quick start
2. Follow the 4-step quick start guide
3. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if issues arise

### For Users
- **Security concerns?** → [SECURITY.md](SECURITY.md)
- **Something not working?** → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **API usage?** → [API_REFERENCE.md](API_REFERENCE.md)

### For Developers
- **Want to contribute?** → [CONTRIBUTING.md](CONTRIBUTING.md)
- **Need API docs?** → [API_REFERENCE.md](API_REFERENCE.md)
- **Check version history?** → [CHANGELOG.md](../CHANGELOG.md)

### For Compliance Officers
- **HIPAA compliance?** → [SECURITY.md](SECURITY.md) (sections: HIPAA Compliance, Audit and Monitoring)
- **Audit procedures?** → [SECURITY.md](SECURITY.md) (section: Audit and Monitoring)
- **Incident response?** → [SECURITY.md](SECURITY.md) (section: Incident Response)

---

## 📖 Documentation by Topic

### Installation & Setup
- [README.md](../README.md) - Installation
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Installation Issues
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development Setup

### Security & Compliance
- [SECURITY.md](SECURITY.md) - Complete security guide
- [API_REFERENCE.md](API_REFERENCE.md) - AuditLogger API
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Security Issues

### Query Execution
- [README.md](../README.md) - Basic Queries
- [API_REFERENCE.md](API_REFERENCE.md) - QueryEngine API
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Query Issues

### Configuration
- [API_REFERENCE.md](API_REFERENCE.md) - Configuration Keys
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Configuration Issues

### Testing
- [CONTRIBUTING.md](CONTRIBUTING.md) - Testing Guidelines
- [API_REFERENCE.md](API_REFERENCE.md) - Testing Section

---

## 💡 Documentation Standards

All documentation follows these principles:

1. **User-Focused**: Written for the target audience (users, developers, compliance officers)
2. **Practical**: Includes examples, commands, and step-by-step instructions
3. **Complete**: Covers all aspects of the topic
4. **Accurate**: Tested and verified against current implementation
5. **Maintainable**: Easy to update as features change

---

## 🤝 Contributing to Documentation

Found an error? Want to improve documentation? See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Documentation Checklist
- [ ] Is the content accurate?
- [ ] Are code examples tested?
- [ ] Are commands OS-specific where needed?
- [ ] Is the language clear and concise?
- [ ] Are there enough examples?
- [ ] Is it well-organized?

---

## 📞 Getting Help

- **Questions**: GitHub Discussions
- **Bugs**: GitHub Issues
- **Security**: security@example.com
- **General**: dev@example.com

---

**Last Updated**: 2025  
**Version**: 1.0.0
