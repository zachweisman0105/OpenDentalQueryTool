# Command Shortcuts

This document lists all available command shortcuts for the OpenDental Query Tool CLI.

## Single-Word Command Shortcuts

The tool provides convenient single-word commands that you can invoke directly without typing the full `opendental-query` prefix.

### Main Command Shortcuts

| Shortcut | Equivalent Full Command | Description |
|----------|------------------------|-------------|
| `Query` | `opendental-query query` | Execute SQL query across multiple offices |
| `Vault` | `opendental-query vault` | Manage encrypted credential vault |
| `Config` | `opendental-query config` | Manage application configuration settings |
| `Update` | `opendental-query check-update` | Check for software updates |

### Vault Command Shortcuts

| Shortcut | Equivalent Full Command | Description |
|----------|------------------------|-------------|
| `VaultInit` | `opendental-query vault init` | Initialize a new encrypted vault |
| `VaultAdd` | `opendental-query vault add-office` | Add office credentials to vault |
| `VaultRemove` | `opendental-query vault remove-office` | Remove office credentials from vault |
| `VaultList` | `opendental-query vault list-offices` | List all offices in vault |
| `VaultUpdateKey` | `opendental-query vault update-developer-key` | Update DeveloperKey in vault |
| `VaultClear` | `opendental-query vault clear` | Remove all offices from vault |
| `VaultDestroy` | `opendental-query vault destroy` | Completely delete the vault file |

### Config Command Shortcuts

| Shortcut | Equivalent Full Command | Description |
|----------|------------------------|-------------|
| `ConfigGet` | `opendental-query config get` | Get a configuration value |
| `ConfigSet` | `opendental-query config set` | Set a configuration value |
| `ConfigList` | `opendental-query config list` | List all configuration settings |
| `ConfigReset` | `opendental-query config reset` | Reset configuration to default values |
| `ConfigPath` | `opendental-query config path` | Show the path to the configuration file |

## Usage Examples

### Using Main Shortcuts
```bash
# Instead of:
opendental-query query -s "SELECT * FROM patient LIMIT 10"

# Simply type:
Query -s "SELECT * FROM patient LIMIT 10"

# Instead of:
opendental-query vault init

# Simply type:
Vault init
# or even shorter:
VaultInit
```

### Vault Operations
```bash
# Initialize vault
VaultInit

# Add an office
VaultAdd office1

# Add multiple offices at once (bulk add)
VaultAdd office1,office2,office3

# List all offices
VaultList

# Remove an office
VaultRemove oldoffice

# Update developer key
VaultUpdateKey

# Or use the grouped shortcut:
Vault init
Vault add-office office1
Vault add-office office1,office2,office3  # bulk add
Vault list-offices
```

### Config Operations
```bash
# Get a value
ConfigGet vault.auto_lock_minutes

# Set a value
ConfigSet vault.auto_lock_minutes 30

# List all configuration
ConfigList

# Reset to defaults
ConfigReset --all

# Show config path
ConfigPath

# Or use the grouped shortcut:
Config get vault.auto_lock_minutes
Config set vault.auto_lock_minutes 30
Config list
```

### Query Operations
```bash
# Interactive query
Query

# Direct query
Query -s "SELECT * FROM patient LIMIT 10" -o ALL

# Query with export
Query --export -s "SELECT * FROM patient" -o office1,office2
```

### Update Check
```bash
# Check for updates
Update
```

## CLI Subcommand Aliases

In addition to single-word shortcuts, the CLI also supports short aliases when using the full command structure:

### Top-Level Command Aliases

| Alias | Full Command | Description |
|-------|--------------|-------------|
| `v` | `vault` | Manage encrypted credential vault |
| `c` | `config` | Manage application configuration settings |
| `q` | `query` | Execute SQL query across multiple offices |
| `update` | `check-update` | Check for software updates |

### Vault Subcommand Aliases

| Alias | Full Command | Description |
|-------|--------------|-------------|
| `add` | `add-office` | Add office credentials to vault |
| `remove` | `remove-office` | Remove office credentials from vault |
| `rm` | `remove-office` | Remove office credentials from vault (alternative) |
| `list` | `list-offices` | List all offices in vault |
| `ls` | `list-offices` | List all offices in vault (alternative) |
| `update-key` | `update-developer-key` | Update DeveloperKey in vault |
| `reset` | `clear` | Remove all offices from vault |
| `delete` | `destroy` | Completely delete the vault file |

### Config Subcommand Aliases

| Alias | Full Command | Description |
|-------|--------------|-------------|
| `ls` | `list` | List all configuration settings |

### Examples with Aliases
```bash
# Using CLI aliases:
opendental-query v init
opendental-query v add office1
opendental-query v add office1,office2,office3  # bulk add
opendental-query v ls
opendental-query c ls
opendental-query q -s "SELECT * FROM patient LIMIT 10" -o ALL

# Using single-word shortcuts:
VaultInit
VaultAdd office1
VaultAdd office1,office2,office3  # bulk add
VaultList
ConfigList
Query -s "SELECT * FROM patient LIMIT 10" -o ALL
```

## Summary: Three Ways to Run Commands

There are three equivalent ways to run any command:

### 1. Full Command (Most Explicit)
```bash
opendental-query vault init
opendental-query vault add-office office1
opendental-query config list
opendental-query query -s "SELECT * FROM patient LIMIT 10"
```

### 2. CLI Aliases (Short but Still Namespaced)
```bash
opendental-query v init
opendental-query v add office1
opendental-query c ls
opendental-query q -s "SELECT * FROM patient LIMIT 10"
```

### 3. Single-Word Shortcuts (Fastest)
```bash
VaultInit
VaultAdd office1
ConfigList
Query -s "SELECT * FROM patient LIMIT 10"
```

## Notes

- All three methods are equivalent and produce the same results
- Single-word shortcuts are fastest for interactive use
- Full commands are clearest for scripts and documentation
- CLI aliases provide a middle ground
- All shortcuts are case-sensitive and use PascalCase (e.g., `VaultInit`, not `vaultinit`)
- Original full commands always work and are displayed in help messages
