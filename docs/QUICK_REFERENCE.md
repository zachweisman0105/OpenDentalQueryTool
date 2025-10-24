# Quick Reference Card - Command Shortcuts

## Single-Word Shortcuts (Fastest!)
```bash
Query                    # Execute SQL query
Vault                    # Vault operations
Config                   # Config operations
Update                   # Check for updates

# Direct commands (no subcommands needed):
VaultInit                # Initialize vault
VaultAdd office1         # Add office
VaultList                # List offices
VaultRemove office1      # Remove office
VaultUpdateKey           # Update developer key

ConfigGet key            # Get config value
ConfigSet key value      # Set config value
ConfigList               # List all config
ConfigReset              # Reset config
ConfigPath               # Show config file path
```

## Main Commands (with CLI aliases)
```bash
opendental-query v      # vault
opendental-query c      # config  
opendental-query q      # query
opendental-query update # check-update
```

## Vault Operations
```bash
# Single-word shortcuts:
VaultInit                           # Initialize
VaultAdd office1                    # Add office
VaultAdd office1,office2,office3    # Bulk add offices
VaultList                           # List offices
VaultRemove office1                 # Remove office
VaultUpdateKey                      # Update developer key

# Or use grouped commands:
Vault init
Vault add-office office1
Vault add-office office1,office2,office3  # bulk add
Vault list-offices
Vault remove-office office1
Vault update-developer-key

# Or use CLI aliases:
opendental-query v init
opendental-query v add office1
opendental-query v add office1,office2,office3  # bulk add
opendental-query v ls
opendental-query v rm office1
opendental-query v update-key
```

## Config Operations
```bash
# Single-word shortcuts:
ConfigGet vault.auto_lock_minutes
ConfigSet vault.auto_lock_minutes 30
ConfigList
ConfigReset --all
ConfigPath

# Or use grouped commands:
Config get vault.auto_lock_minutes
Config set vault.auto_lock_minutes 30
Config list
Config reset --all
Config path

# Or use CLI aliases:
opendental-query c get vault.auto_lock_minutes
opendental-query c set vault.auto_lock_minutes 30
opendental-query c ls
```

## Query Operations
```bash
# Interactive query (all methods equivalent):
Query
opendental-query query
opendental-query q

# Direct query:
Query -s "SELECT * FROM patient LIMIT 10" -o ALL
opendental-query q -s "SELECT * FROM patient LIMIT 10" -o ALL

# Query with export:
Query --export -s "SELECT * FROM patient" -o office1,office2
```

## Complete Workflow Examples

### Using Single-Word Shortcuts (Recommended for Speed)
```bash
VaultInit                                      # Initialize vault
VaultAdd myoffice                              # Add office
VaultAdd office1,office2,office3               # Bulk add offices
VaultList                                      # List offices
Query -s "SELECT COUNT(*) FROM patient" -o ALL # Quick query
ConfigList                                     # List config
Update                                         # Check updates
```

### Using CLI Aliases (Good for Scripts)
```bash
opendental-query v init
opendental-query v add myoffice
opendental-query v add office1,office2,office3  # bulk add
opendental-query v ls
opendental-query q -s "SELECT COUNT(*) FROM patient" -o ALL
opendental-query c ls
opendental-query update
```

### Using Full Commands (Most Explicit)
```bash
opendental-query vault init
opendental-query vault add-office myoffice
opendental-query vault list-offices
opendental-query query -s "SELECT COUNT(*) FROM patient" -o ALL
opendental-query config list
opendental-query check-update
```

## Quick Reference Table

| Task | Single-Word | CLI Alias | Full Command |
|------|-------------|-----------|--------------|
| Init vault | `VaultInit` | `opendental-query v init` | `opendental-query vault init` |
| Add office | `VaultAdd office1` | `opendental-query v add office1` | `opendental-query vault add-office office1` |
| List offices | `VaultList` | `opendental-query v ls` | `opendental-query vault list-offices` |
| Run query | `Query -s "..."` | `opendental-query q -s "..."` | `opendental-query query -s "..."` |
| List config | `ConfigList` | `opendental-query c ls` | `opendental-query config list` |
| Check updates | `Update` | `opendental-query update` | `opendental-query check-update` |

---
**Tip:** Use whichever style you prefer - they all work the same way!
