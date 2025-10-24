# Command Shortcuts - Before & After

## Before (Original Commands Only)

Users had to type the full `opendental-query` prefix for every command:

```bash
# Initialize vault
opendental-query vault init

# Add an office
opendental-query vault add-office office1

# List offices
opendental-query vault list-offices

# Run a query
opendental-query query -s "SELECT * FROM patient LIMIT 10" -o ALL

# List configuration
opendental-query config list

# Check for updates
opendental-query check-update
```

**Character count for common workflow: 294 characters**

## After (With Shortcuts)

### Option 1: Single-Word Shortcuts (Fastest) ⚡

```bash
# Initialize vault
VaultInit

# Add an office
VaultAdd office1

# List offices
VaultList

# Run a query
Query -s "SELECT * FROM patient LIMIT 10" -o ALL

# List configuration
ConfigList

# Check for updates
Update
```

**Character count: 101 characters (66% reduction!)**

### Option 2: CLI Aliases (Good Balance)

```bash
# Initialize vault
opendental-query v init

# Add an office
opendental-query v add office1

# List offices
opendental-query v ls

# Run a query
opendental-query q -s "SELECT * FROM patient LIMIT 10" -o ALL

# List configuration
opendental-query c ls

# Check for updates
opendental-query update
```

**Character count: 199 characters (32% reduction)**

### Option 3: Mixed Approach (Flexible)

Users can mix and match based on context:

```bash
# Use single-word for quick operations
VaultInit
VaultAdd office1

# Use CLI aliases in scripts for clarity
opendental-query v ls
opendental-query q -s "SELECT * FROM patient" -o ALL

# Use full commands in documentation
opendental-query config list
```

## Typing Speed Comparison

Based on average typing speed of 40 WPM (8 characters per second):

| Command | Before | After (Shortcut) | Time Saved |
|---------|--------|------------------|------------|
| Initialize vault | `opendental-query vault init` (28 chars, 3.5s) | `VaultInit` (9 chars, 1.1s) | **2.4 seconds** |
| Add office | `opendental-query vault add-office office1` (46 chars, 5.8s) | `VaultAdd office1` (17 chars, 2.1s) | **3.7 seconds** |
| List offices | `opendental-query vault list-offices` (40 chars, 5.0s) | `VaultList` (9 chars, 1.1s) | **3.9 seconds** |
| Run query | `opendental-query query -s "..."` (30+ chars, 3.8s+) | `Query -s "..."` (13+ chars, 1.6s+) | **2.2+ seconds** |
| List config | `opendental-query config list` (33 chars, 4.1s) | `ConfigList` (10 chars, 1.3s) | **2.8 seconds** |

**Total time saved per workflow: ~15 seconds**

Over 100 uses: **25 minutes saved!** ⏱️

## User Experience Impact

### Before
```bash
$ opendental-query vault list-offices
# Too long to type, easy to make mistakes
# Requires remembering exact command structure
# Slower for interactive use
```

### After
```bash
$ VaultList
# Fast and intuitive
# PascalCase is easy to remember
# Perfect for interactive use

# Or use aliases for scripts:
$ opendental-query v ls
# Short but still namespaced
# Good balance of brevity and clarity
```

## Discoverability

All three methods are well-documented:

1. **Help text** shows full command names for clarity
2. **Tab completion** (when available) shows all options
3. **Documentation** provides comparison tables
4. **Error messages** suggest correct command names

Users can start with full commands and gradually adopt shortcuts as they become more comfortable with the tool.

## Conclusion

The addition of command shortcuts provides:
- ✅ **66% reduction** in typing (single-word shortcuts)
- ✅ **32% reduction** in typing (CLI aliases)
- ✅ **Backward compatibility** (all original commands still work)
- ✅ **Flexibility** (three different styles to choose from)
- ✅ **Better UX** (faster, more intuitive commands)
