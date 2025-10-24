# Bulk Add Offices Feature

## Overview

The `vault add-office` command now supports adding multiple offices at once by providing comma-separated office IDs. This saves time and requires entering the master password only once.

## Usage

### Single Office (Original)
```bash
VaultAdd office1
```

### Multiple Offices (New)
```bash
VaultAdd office1,office2,office3
```

## How It Works

1. **Enter office IDs** - Provide comma-separated office identifiers as the argument
2. **Provide CustomerKeys** - The tool will prompt for each office's CustomerKey
3. **Enter master password** - Enter your master password once (not per office)
4. **View results** - See a summary of successful and failed additions

## Example Session

```bash
$ VaultAdd office1,office2,office3

Adding 3 office(s) to vault

CustomerKey for office1: ****************************************
CustomerKey for office2: ****************************************
CustomerKey for office3: ****************************************

Master password: ********

✓ Added credentials for office: office1
✓ Added credentials for office: office2
✓ Added credentials for office: office3

Summary: 3/3 office(s) added successfully
```

## Error Handling

If an office already exists or there's an error, the tool will:
- Continue adding other offices
- Show which offices failed
- Display a summary at the end

### Example with Errors
```bash
$ VaultAdd office1,office2,office3

Adding 3 office(s) to vault

CustomerKey for office1: ****************************************
CustomerKey for office2: ****************************************
CustomerKey for office3: ****************************************

Master password: ********

✗ Failed to add office1: Office already exists
✓ Added credentials for office: office2
✓ Added credentials for office: office3

Summary: 2/3 office(s) added successfully
Failed offices: office1
```

## Benefits

✅ **Faster setup** - Add multiple offices in one command
✅ **Less typing** - Enter master password only once
✅ **Better UX** - Clear prompts and summary
✅ **Error resilient** - Continues even if one office fails
✅ **Works everywhere** - Available in all command variants

## Command Variants

All three command styles support bulk add:

### 1. Single-Word Shortcut
```bash
VaultAdd office1,office2,office3
```

### 2. Grouped Command
```bash
Vault add-office office1,office2,office3
```

### 3. Full CLI
```bash
opendental-query vault add-office office1,office2,office3
opendental-query v add office1,office2,office3  # with alias
```

## Tips

### No Spaces After Commas
```bash
# Good:
VaultAdd office1,office2,office3

# Also works (spaces are trimmed):
VaultAdd office1, office2, office3
```

### Mix with Single Adds
You can still add offices one at a time:
```bash
VaultAdd office1              # Add one
VaultAdd office2,office3      # Add two more
VaultAdd office4              # Add another
```

### Large Batch Setup
For initial setup with many offices:
```bash
# Add 10 offices at once
VaultAdd office1,office2,office3,office4,office5,office6,office7,office8,office9,office10
```

## Use Cases

### Initial Setup
Setting up a new installation with multiple offices:
```bash
VaultInit
VaultAdd main,branch1,branch2,branch3,branch4
VaultList
```

### Adding New Locations
Adding several new office locations:
```bash
VaultAdd downtown,uptown,eastside,westside
```

### Migration
Moving from another system and need to add many offices:
```bash
VaultAdd office1,office2,office3,office4,office5,office6,office7,office8
```

## See Also

- [Command Shortcuts](COMMAND_ALIASES.md) - All available shortcuts
- [Quick Reference](QUICK_REFERENCE.md) - Quick command reference
- [Getting Started](GETTING_STARTED_SHORTCUTS.md) - Getting started guide
