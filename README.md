# OpenDental Multi-Office Query Tool

A local, HIPAA-compliant CLI for executing SQL queries across multiple OpenDental office instances simultaneously.

---

## Features

- **HIPAA Compliance:** No PHI logging, encrypted vault, and auditable events  
- **Multi-Office Support:** Run a single SQL query across many offices concurrently  
- **Secure Vault:** Argon2id + AES-256-GCM encryption for credentials  
- **Readable Output:** Table display with optional Excel export  
- **Resilient Networking:** Automatic retry and backoff  
- **Comprehensive Logging:** 30-day app log and 90-day audit log retention  
- **Encrypted History:** Persist query runs and external data imports into an encrypted SQLite archive  

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
# - Master password
# - Global DeveloperKey

### 2. Add Office Credentials

```bash
VaultAdd
# Prompts:
# - Office ID
# - CustomerKey

### 3. Run a Query

```bash
Query
# Prompts:
# - Master password
# - SQL query
# - Office selection (ALL or list)
```

### 4. Store Results in History

```bash
QueryTable
# Prompts for a saved query, runs it, and creates the encrypted table

UpdateTable
# Runs a saved query again and appends the new rows to its existing history table

TableImport
# Prompts for a saved query with history and imports rows from Excel

TableExport
# Prompts for a saved query with history and writes it to Excel (.xlsx)
TableList
# Shows stored history tables with metadata and SQL previews

TableDelete
# Prompts for a saved query with history and deletes its stored table
```

### Shortcut Reference

| Shortcut | Equivalent CLI | Description |
|----------|----------------|-------------|
| Vault | `opendental-query vault` | Open the secure vault command group |
| VaultInit | `opendental-query vault init` | Initialize the credential vault |
| VaultAdd | `opendental-query vault add-office` | Add an office credential to the vault |
| VaultRemove | `opendental-query vault remove-office` | Remove an office credential |
| VaultList | `opendental-query vault list-offices` | List offices stored in the vault |
| VaultUpdateKey | `opendental-query vault update-developer-key` | Rotate the shared DeveloperKey |
| VaultClear | `opendental-query vault clear` | Remove all office credentials without destroying the vault |
| VaultDestroy | `opendental-query vault destroy` | Permanently delete the vault |
| Query | `opendental-query query` | Launch the interactive query runner |
| QuerySave | `opendental-query saved-query` | Manage saved queries via shortcut command |
| Persist | `opendental-query persist` | Run a query and append results to the encrypted history |
| Config | `opendental-query config` | Access configuration utilities |
| ConfigGet | `opendental-query config get` | Read an individual configuration value |
| ConfigSet | `opendental-query config set` | Update a configuration value |
| ConfigList | `opendental-query config list` | List all configuration settings |
| ConfigReset | `opendental-query config reset` | Reset configuration to defaults |
| ConfigPath | `opendental-query config path` | Display the active configuration file path |
| Update | `opendental-query check-update` | Check for CLI updates |
| QueryTable | `opendental-query history create-table` | Build a history table from a saved query |
| UpdateTable | `opendental-query history run` | Re-run a saved query and append results |
| TableImport | `opendental-query history import-table` | Import Excel data into a history table |
| TableList | `opendental-query history list-tables` | List stored history tables |
| TableExport | `opendental-query history export` | Export history rows to Excel |
| TableDelete | `opendental-query history delete` | Delete an existing history table |

opendental-query history run --sql "<your query>" --offices ALL
# Persists the results to an encrypted per-query table

opendental-query history import path\to\file.xlsx --saved-query "Monthly Production"
# Adds rows from CSV/Excel using the query text as the table key

---

## Security

- **Encryption:** Argon2id (64 MB, 3 iterations, 4 threads) + AES-256-GCM  
- **Vault Permissions:** 0600  
- **Auto-Lock:** 15 minutes inactivity  
- **Lockout:** 60 seconds after 3 failed attempts  
- **HTTPS Only:** HTTP requests rejected  
- **Audit Logging:** PHI never logged; metadata only  

---

## File Locations

| File | Path | Retention |
|------|------|------------|
| Config | `~/.opendental-query/config.json` | persistent |
| Vault | `~/.opendental-query/credentials.vault` | persistent |
| App Log | `~/.opendental-query/app.log` | 30 days |
| Audit Log | `~/.opendental-query/audit.jsonl` | 90 days |
| Excel Exports | `~/Downloads/` | user-managed |

---

## License

MIT License — see `LICENSE`.

---

## Support

Report issues or feature requests via GitHub Issues.

