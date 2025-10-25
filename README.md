# OpenDental Multi-Office Query Tool

A local, HIPAA-compliant CLI for executing SQL queries across multiple OpenDental office instances simultaneously.

---

## Features

- **HIPAA Compliance:** No PHI logging, encrypted vault, and auditable events  
- **Multi-Office Support:** Run a single SQL query across many offices concurrently  
- **Secure Vault:** Argon2id + AES-256-GCM encryption for credentials  
- **Readable Output:** Table display with optional CSV export  
- **Resilient Networking:** Automatic retry and backoff  
- **Comprehensive Logging:** 30-day app log and 90-day audit log retention  

---

## Requirements

- **Python 3.11 or newer** (3.11, 3.12, or 3.13 supported)  
- OpenDental Remote API with valid DeveloperKey and CustomerKeys  
- HTTPS-accessible OpenDental API endpoint  
- Windows 10+, macOS 13+, or Linux (Ubuntu 20.04+)  
- Internet access to all office endpoints  

---

## Installation

1. **Download and install Python 3.11+** from [python.org/downloads](https://www.python.org/downloads/).  
   - During installation, check “Add Python to PATH.”  
   - Verify installation:  
     ```bash
     python --version
     ```

2. **Clone the repository and install dependencies**:
   ```bash
   git clone https://github.com/zachweisman0105/OpenDentalQueryTool.git
   cd OpenDentalQueryTool
   py -3.11 -m venv .venv
   .venv\Scripts\activate
   pip install -U pip
   pip install -e .
   ```

3. **Run the tool**:
   ```bash
   Query
   VaultInit
   VaultAdd
   ConfigList
   ```

---

## Quick Start

Ensure the virtual environment is activated.  
> See [docs/COMMAND_ALIASES.md](docs/COMMAND_ALIASES.md) for shortcut commands  
> (e.g. `VaultInit` = `opendental-query vault-init`)

### 1. Initialize Vault

```bash
VaultInit
# Prompts:
# - Master password (≥12 chars)
# - Global DeveloperKey
```

### 2. Add Office Credentials

```bash
VaultAdd
# Prompts:
# - Office ID
# - CustomerKey
```

### 3. Run a Query

```bash
Query
# Prompts:
# - Master password
# - SQL query (SELECT only)
# - Office selection (ALL or list)
```

---

## Security

- **Encryption:** Argon2id (64 MB, 3 iterations, 4 threads) + AES-256-GCM  
- **Vault Permissions:** 0600  
- **Auto-Lock:** 15 minutes inactivity  
- **Lockout:** 60 seconds after 3 failed attempts  
- **HTTPS Only:** HTTP requests rejected  
- **Read-Only Enforcement:** Non-SELECT SQL blocked  
- **Audit Logging:** PHI never logged; metadata only  

---

## File Locations

| File | Path | Retention |
|------|------|------------|
| Config | `~/.opendental-query/config.json` | persistent |
| Vault | `~/.opendental-query/credentials.vault` | persistent |
| App Log | `~/.opendental-query/app.log` | 30 days |
| Audit Log | `~/.opendental-query/audit.jsonl` | 90 days |
| CSV Exports | `~/Downloads/` | user-managed |

---

## License

MIT License — see `LICENSE`.

---

## Support

Report issues or feature requests via GitHub Issues.
