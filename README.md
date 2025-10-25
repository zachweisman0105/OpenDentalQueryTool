# OpenDental Multi-Office Query Tool

A local, HIPAA-compliant CLI for executing SQL queries across multiple OpenDental office instances simultaneously.  
Releases are built with PyInstaller—no Python installation required.

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

- OpenDental Remote API with valid DeveloperKey and CustomerKeys  
- HTTPS-accessible OpenDental API endpoint  
- Windows 10+ or macOS 13+  
- Internet access to all office endpoints  

---

## Installation (Standalone Executable)

1. **Download** the binary for your platform from the [Releases](../../releases) page:  
   - **Windows:** `opendental-query.exe`  
   - **macOS:** `MacOSPackage`  

2. **Place** the binary in your preferred directory, e.g.  
   - `C:\Program Files\OpenDentalQuery\` (Windows)  
   - `/Applications/OpenDentalQuery/` (macOS)  

3. **Run** the tool:

   ```powershell
   opendental-query.exe      # Windows
   ./MacOSPackage            # macOS
   ```

4. *(Optional)* Add the directory to your `PATH` for global use.

To update, replace the binary with the latest version.

---

## Quick Start

Ensure the executable is on your `PATH`.

> See [docs/COMMAND_ALIASES.md](docs/COMMAND_ALIASES.md) for command shortcuts  
> (e.g. `VaultInit` = `opendental-query vault-init`)

### 1. Initialize Vault

```bash
vaultinit
# Prompts:
# - Master password (≥12 chars)
# - Global DeveloperKey
```

Default API URL:  
`https://api.opendental.com/api/v1`  
Override with:

```bash
opendental-query config set-api-url https://your-url/api/v1
```

### 2. Add Office Credentials

```bash
vaultadd
# Prompts:
# - Office ID
# - CustomerKey
```

Multiple IDs:

```bash
opendental-query vaultadd office1,office2
```

### 3. Run a Query

```bash
query
# Prompts:
# - Master password
# - SQL query (SELECT only)
# - Office selection (ALL or list)
```

The CLI automatically formats requests for Open Dental’s ShortQuery endpoint.

---

## Examples

### Query All Offices

```bash
query
SQL query: SELECT COUNT(*) FROM appointment WHERE AptDateTime > '2025-10-01'
Select offices: ALL
```

### Query Selected Offices

```bash
query
SQL query: SELECT LName, FName FROM patient LIMIT 10
Select offices: MainOffice,BranchA
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

## Packaging

Executables are produced via PyInstaller (`packaging/pyinstaller/build.py`).  
Each bundle includes the Python runtime and dependencies.  
Currently supported: Windows and macOS (Linux support removed).  

---

## License

MIT License — see `LICENSE`.

---

## Support

Report issues or feature requests via GitHub Issues.

