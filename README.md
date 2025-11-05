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
   - On macOS/Linux use `python3.11 -m venv .venv` and `source .venv/bin/activate`.

3. **Verify the CLI entry points (inside the activated virtual environment)**:
    ```bash
    opendental-query --help
    Query --help
    Vault --help
    ```
   These commands confirm the console scripts are installed. Continue with the Quick Start below to configure the vault, offices, and saved queries.

---

## Quick Start

Activate the virtual environment you created during installation (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` on macOS/Linux).

> See [docs/COMMAND_ALIASES.md](docs/COMMAND_ALIASES.md) for shortcut commands and CLI aliases.

### 0. Set the API endpoint (once per environment)

```bash
ConfigList
ConfigSet api_base_url https://your.opendental.server/api/v1
```

- `ConfigList` creates `~/.opendental-query/config.json` the first time it runs.
- The CLI enforces HTTPS; replace the URL with your OpenDental Remote API endpoint.
- You can tune other defaults later, e.g. `ConfigSet vault.auto_lock_minutes 20`.

### 1. Initialize the encrypted vault

```bash
VaultInit
```

- Prompts for the master password (twice) and the shared DeveloperKey.
- Creates `~/.opendental-query/credentials.vault` and leaves it unlocked for the session.

### 2. Add office credentials

```bash
VaultAdd office1
VaultAdd office1,office2,office3
VaultList
```

- Supply one or more office IDs (comma separated). The command prompts for each office's CustomerKey and the vault password if the vault is locked.
- Use `VaultRemove <office>` to revoke access or `VaultUpdateKey` to rotate the DeveloperKey later.

### 3. (Optional) Save queries for reuse

```bash
QuerySave                          # guided prompt to create a saved query
QuerySave list                     # display saved queries and SQL
QuerySave "Monthly Production"     # run a saved query by name
```

- Saved queries can include default office selections and descriptions.
- They are stored alongside the encrypted configuration and history data in `~/.opendental-query`.

### 4. Run a query

```bash
Query                               # interactive prompt for SQL and offices
Query -s "SELECT PatNum, LName FROM patient LIMIT 25" -o ALL --export
Query --saved-query "Monthly Production" --export
QueryProcCode -p D0120              # run the built-in procedure code template
```

- When `--sql/-s` is omitted, `Query` opens a multiline prompt.
- Use `-o office1,office2` or `-o ALL` to select offices.
- Passing `--export` writes results to an Excel workbook in the secure export directory (defaults to `~/Downloads`, or use `SPEC_KIT_EXPORT_ROOT` to override).

### 5. Manage history and persistence

```bash
Persist --table monthly_totals --saved-query "Monthly Production" -o ALL
QueryTable                          # create encrypted history table from a saved query
UpdateTable                         # rerun a saved query and append to its history
TableList                           # show stored history tables with metadata
TableExport                         # export a history table to Excel
TableImport                         # import Excel rows into an existing history table
TableDelete                         # remove stored history for a saved query
```

- History and persistence data are encrypted under `~/.opendental-query`.
- `Persist` appends rows from ad-hoc or saved queries into a named table for downstream reporting.

### Shortcut Reference

All console script shortcuts defined in `pyproject.toml`:

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
| QueryProcCode | `opendental-query query proc-code` | Run the built-in procedure code SQL template |
| QuerySave | `opendental-query saved-query` | Shortcut to the saved-query command group (interactive by default) |
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
