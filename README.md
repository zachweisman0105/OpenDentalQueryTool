# OpenDental Multi-Office Query Tool

A local, HIPAA-compliant CLI tool for executing SQL queries across multiple OpenDental office instances simultaneously.  
Releases ship as self-contained binaries built with PyInstaller—no Python installation required.

## Features

- **HIPAA Compliant**: Zero PHI logging, encrypted credential storage, and full audit trails  
- **Multi-Office Support**: Run the same query across all or selected offices in parallel  
- **Secure Vault**: Argon2id + AES-256-GCM encryption for credentials  
- **Excel-Style Output**: Rich table rendering with optional CSV export  
- **Resilient Networking**: Automatic retries with backoff and jitter  
- **Comprehensive Logging**: 90-day audit log retention with hardened defaults  

## Requirements

- OpenDental Remote API access with valid credentials  
- HTTPS-accessible OpenDental API endpoint  
- Windows 10+ or macOS 13+  
- Network connectivity to every office queried  

## Installation (Standalone Executable)

1. Download the latest binary for your operating system from the [Releases](../../releases) page:  
   - **Windows:** `opendental-query-windows.exe`  
   - **macOS:** `opendental-query-macos`  
   - **Linux:** `opendental-query-linux`  

2. Place the file in your preferred directory, such as:  
   - `C:\Program Files\OpenDentalQuery\` (Windows)  
   - `/Applications/OpenDentalQuery/` (macOS)  

3. **Windows:**  
   - Run directly via PowerShell or Command Prompt:  
     ```powershell
     opendental-query-windows.exe
     ```

   **macOS:**  
   - Make the file executable and remove quarantine:  
     ```bash
     chmod +x opendental-query-macos
     xattr -d com.apple.quarantine ./opendental-query-macos
     ./opendental-query-macos
     ```

4. (Optional) Add the directory to your `PATH` to run the command globally.

To update, replace the old binary with the new release file.

## Quick Start

The commands below assume `opendental-query` (or `opendental-query.exe`) is available on your shell `PATH`. If it is not, prefix each command with the full path to the executable.

### 1. Initialize Configuration

```bash
opendental-query config set-api-url https://api.opendental.com
```

### 2. Initialize Vault

```bash
opendental-query vault-init

# Prompts:
# - Master password (min 12 chars, mixed case, numbers, symbols)
# - Global DeveloperKey
```

### 3. Add Office Credentials

```bash
opendental-query vault-add-office

# Prompts:
# - Office ID (e.g., "MainOffice", "BranchA")
# - CustomerKey for that office
```

### 4. Execute a Query

```bash
opendental-query query

# Prompts:
# - Master password (to unlock vault)
# - SQL query (SELECT only)
# - Office selection (ALL or comma-separated IDs)
```

The CLI formats requests according to Open Dental's ShortQuery endpoint, so no manual JSON payload construction is required.

## Usage Examples

### Query All Offices

```bash
$ opendental-query query
Master password: ********
SQL query: SELECT COUNT(*) FROM appointment WHERE AptDateTime > '2025-10-01'
Select offices (ALL or comma-separated IDs): ALL

Executing query across 5 offices... done

Results:
Office       | count
------------ | -----
MainOffice   | 234
BranchA      | 156
BranchB      | 189
Downtown     | 267
Uptown       | 198

Export results to CSV? [y/N]: n
```

### Query Specific Offices

```bash
$ opendental-query query
Master password: ********
SQL query: SELECT PatientNum, LName, FName FROM patient LIMIT 10
Select offices (ALL or comma-separated IDs): MainOffice,BranchA

# Results limited to the selected offices
```

## Security

- **Encryption**: Argon2id (64MB memory, 3 iterations, 4 parallelism) + AES-256-GCM
- **Vault Permissions**: 0600 (user read/write only)
- **Auto-Lock**: 15-minute inactivity timeout
- **Lockout Protection**: 60-second cooldown after 3 failed password attempts
- **HTTPS Only**: HTTP endpoints rejected with error
- **Read-Only Enforcement**: CLI rejects non-read-only SQL commands before execution
- **No PHI Logging**: Query text is hashed before persistence and audit events include host/IP/session metadata only

## File Locations

- **Config**: `~/.opendental-query/config.json`
- **Vault**: `~/.opendental-query/vault.enc`
- **Application Log**: `~/.opendental-query/app.log` (30-day retention)
- **Audit Log**: `~/.opendental-query/audit.log` (90-day retention, JSONL format)
- **CSV Exports**: `~/Downloads/` (fallback to current directory)

## How the Standalone Package Is Produced

Every downloadable executable is created with PyInstaller, bundling the Python runtime and all dependencies into a single file per operating system. Maintainers who need to regenerate the package can run the PyInstaller build script documented under `packaging/pyinstaller/`, but end users only need to download and run the published bundle.

## License

MIT License - see `LICENSE` for details.

## Support

For issues, feature requests, or questions, please file an issue on the GitHub repository.
