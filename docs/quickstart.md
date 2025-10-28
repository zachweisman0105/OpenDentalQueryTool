# Quickstart Guide

This quickstart walks you through installing, configuring, and running your first query.

> **💡 Command Shortcuts Available!** The tool provides convenient single-word shortcuts.  
> For example: `VaultInit`, `Query`, `ConfigList` instead of full `opendental-query` commands.  
> See [Command Shortcuts Documentation](COMMAND_ALIASES.md) for the complete list.

## 1. Install

- Python 3.11+ required
- Create and activate a virtual environment
- Install the package in editable mode

## 2. Initialize Vault

```bash
# Single-word shortcut (fastest):
VaultInit

# Or grouped command:
Vault init

# Or full command:
opendental-query vault init

# Or CLI alias:
opendental-query v init
```

- Set a strong master password (20+ chars)

## 3. Add Offices

```bash
# Single-word shortcut (fastest):
VaultAdd office1

# Or grouped command:
Vault add-office office1

# Or full command:
opendental-query vault add-office office1

# Or CLI alias:
opendental-query v add office1
```

- Add at least one office with CustomerKey

## 4. Configure (optional)

```bash
# Single-word shortcuts:
ConfigSet network.verify_ssl true
ConfigSet query.timeout_seconds 30

# Or grouped commands:
Config set network.verify_ssl true

# Or CLI aliases:
opendental-query c set network.verify_ssl true
```

## 5. Run a Query

```bash
# Single-word shortcut (fastest):
Query -s "SELECT PatNum, LName, FName FROM patient LIMIT 5"

# Or full command:
opendental-query query -s "SELECT PatNum, LName, FName FROM patient LIMIT 5"

# Or CLI alias:
opendental-query q -s "SELECT PatNum, LName, FName FROM patient LIMIT 5"
```

## 6. Export to Excel

```bash
# Single-word shortcut:
Query --export -s "SELECT * FROM patient LIMIT 100"

# Or CLI alias:
opendental-query q --export -s "SELECT * FROM patient LIMIT 100"
```

## 7. Audit Logs

- Audit logs are stored at `~/.opendental-query/audit.jsonl`

## Common Command Shortcuts

| Task | Single-Word Shortcut | CLI Alias | Full Command |
|------|---------------------|-----------|--------------|
| Initialize vault | `VaultInit` | `opendental-query v init` | `opendental-query vault init` |
| Add office | `VaultAdd office1` | `opendental-query v add office1` | `opendental-query vault add-office office1` |
| List offices | `VaultList` | `opendental-query v ls` | `opendental-query vault list-offices` |
| List configuration | `ConfigList` | `opendental-query c ls` | `opendental-query config list` |
| Execute query | `Query` | `opendental-query q` | `opendental-query query` |
| Check for updates | `Update` | `opendental-query update` | `opendental-query check-update` |

For more details, see [README.md](../README.md) and [SECURITY.md](SECURITY.md).

