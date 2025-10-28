# 🚀 Quick Start with Command Shortcuts

Welcome! This guide shows you the fastest way to use the OpenDental Query Tool with command shortcuts.

## Installation
```bash
pip install -e .
```

## Your First Query in 3 Steps

### Step 1: Initialize Vault
```bash
VaultInit
```
- Enter a strong master password
- Enter your OpenDental DeveloperKey
- Done! ✅

### Step 2: Add Your First Office
```bash
VaultAdd myoffice
```
- Enter the CustomerKey for your office
- Enter your master password
- Done! ✅

**Pro Tip:** Add multiple offices at once!
```bash
VaultAdd office1,office2,office3
```
- Enter CustomerKey for office1
- Enter CustomerKey for office2
- Enter CustomerKey for office3
- Enter your master password once
- All offices added! ✅

### Step 3: Run Your First Query
```bash
Query
```
- Enter your master password
- Enter your SQL query (e.g., `SELECT COUNT(*) FROM patient`)
- Choose which offices (type `ALL` or specific IDs)
- View your results! ✅

## Common Tasks

### List All Offices
```bash
VaultList
```

### Add Another Office
```bash
VaultAdd office2
```

### Add Multiple Offices at Once
```bash
VaultAdd office2,office3,office4
```
This will prompt you for each office's CustomerKey, then ask for your master password once.

### Run a Quick Query
```bash
Query -s "SELECT PatNum, LName, FName FROM patient LIMIT 10" -o ALL
```

### Export Results to Excel
```bash
Query --export -s "SELECT * FROM appointment WHERE AptDateTime > '2025-10-01'" -o ALL
```

### View Configuration
```bash
ConfigList
```

### Change Settings
```bash
ConfigSet vault.auto_lock_minutes 30
```

### Check for Updates
```bash
Update
```

## Pro Tips 💡

### Tip 1: Use Single-Word Shortcuts for Speed
Instead of typing `opendental-query vault init`, just type `VaultInit`.

**Before:**
```bash
opendental-query vault init                    # 28 characters
opendental-query vault add-office myoffice     # 46 characters
opendental-query vault list-offices            # 40 characters
```

**After:**
```bash
VaultInit           # 9 characters ⚡
VaultAdd myoffice   # 17 characters ⚡
VaultList           # 9 characters ⚡
```

### Tip 2: Mix and Match Styles
Use what feels natural:

```bash
# Interactive work? Use single-word shortcuts:
VaultInit
VaultAdd office1
Query

# Writing a script? Use grouped commands for clarity:
Vault init
Vault add-office office1
Config set vault.auto_lock_minutes 30

# Documentation? Use full commands:
opendental-query vault init
opendental-query query -s "SELECT * FROM patient"
```

### Tip 3: Get Help Anytime
Every command supports `--help`:

```bash
Query --help
VaultInit --help
ConfigSet --help
```

## All Available Shortcuts

### Main Commands
- `Query` - Run SQL queries
- `Vault` - Manage credentials
- `Config` - Manage settings
- `Update` - Check for updates

### Vault Operations
- `VaultInit` - Initialize vault
- `VaultAdd <office>` - Add office
- `VaultRemove <office>` - Remove office
- `VaultList` - List offices
- `VaultUpdateKey` - Update developer key

### Config Operations
- `ConfigGet <key>` - Get setting
- `ConfigSet <key> <value>` - Set setting
- `ConfigList` - List all settings
- `ConfigReset` - Reset settings
- `ConfigPath` - Show config file

## Example Workflows

### Workflow 1: Setup New Environment
```bash
VaultInit
VaultAdd office1,office2,office3  # bulk add multiple offices
VaultList
ConfigList
```

### Workflow 2: Daily Query Routine
```bash
Query -s "SELECT COUNT(*) FROM appointment WHERE AptDateTime = CURDATE()" -o ALL
Query -s "SELECT COUNT(*) FROM patient WHERE DateEntry > DATE_SUB(NOW(), INTERVAL 7 DAY)" -o ALL
```

### Workflow 3: Export Data
```bash
Query --export -s "SELECT * FROM patient WHERE City = 'Seattle'" -o office1,office2
```

### Workflow 4: Maintenance
```bash
VaultList
ConfigList
Update
```

## Need More Help?

- **Full documentation:** [README.md](../README.md)
- **Command reference:** [COMMAND_ALIASES.md](COMMAND_ALIASES.md)
- **Quick reference:** [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Security info:** [SECURITY.md](SECURITY.md)

## Troubleshooting

**Q: Shortcuts not working?**
```bash
# Reinstall the package
pip install -e .
```

**Q: Want to see all available commands?**
```bash
Query --help
Vault --help
Config --help
```

**Q: Forgot a command name?**
Check the [Quick Reference](QUICK_REFERENCE.md) or use `--help` on any command.

---

Happy querying! 🎉
