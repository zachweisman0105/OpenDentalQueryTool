# Troubleshooting Guide

Common issues and solutions for the OpenDental Multi-Office Query Tool.

---

## Installation Issues

### ❌ Python Version Too Old

**Error:**
```
ERROR: Python 3.11 or higher is required
Current version: Python 3.9.x
```

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.11+ from python.org
# Or use pyenv:
pyenv install 3.11.5
pyenv local 3.11.5
```

### ❌ Package Installation Fails

**Error:**
```
ERROR: Could not find a version that satisfies the requirement argon2-cffi
```

**Solution:**
```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install with verbose output
pip install -r requirements/base.txt -v

# If specific package fails, install separately
pip install argon2-cffi --no-cache-dir
```

### ❌ Virtual Environment Issues

**Error:**
```
command not found: opendental-query
```

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Reinstall in editable mode
pip install -e .

# Verify installation
which opendental-query  # Should show .venv path
```

---

## Vault Issues

### ❌ Vault Not Found

**Error:**
```
VaultNotFoundError: Vault file not found
```

**Solution:**
```bash
# Check vault path
ls -la ~/.opendental-query/vault.enc

# Initialize vault if missing
opendental-query vault-init

# Custom vault location
export OPENDENTAL_VAULT_PATH="/custom/path/vault.enc"
```

### ❌ Incorrect Master Password

**Error:**
```
Authentication failed: Incorrect password
```

**Solution:**
1. Verify password (check password manager)
2. Check for: spaces, special characters, case sensitivity
3. If password truly lost:
   ```bash
   # CAUTION: This deletes all stored credentials
   rm ~/.opendental-query/vault.enc
   opendental-query vault-init
   # Re-add all offices
   ```

### ❌ Vault Locked Out

**Error:**
```
VaultLockedError: Vault is locked due to failed attempts. Try again in 57 seconds.
```

**Solution:**
```bash
# Wait for lockout period to expire (default: 60 seconds)
# Check audit log for suspicious activity:
tail ~/.opendental-query/audit.jsonl
```

### ❌ Vault Permissions Error (Linux/Mac)

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/home/user/.opendental-query/vault.enc'
```

**Solution:**
```bash
# Fix file permissions
chmod 600 ~/.opendental-query/vault.enc
chmod 700 ~/.opendental-query/

# Verify
ls -la ~/.opendental-query/vault.enc
# Should show: -rw------- (0600)
```

---

## Query Execution Issues

### ❌ Invalid Query Error

**Error:**
```
InvalidQueryError: Only SELECT queries are allowed
```

**Solution:**
```sql
-- ✅ Valid queries
SELECT * FROM patient LIMIT 10
SELECT COUNT(*) FROM appointment
SELECT PatNum, LName FROM patient WHERE PatNum = 123

-- ❌ Invalid queries (not allowed)
UPDATE patient SET LName = 'Smith'  -- No updates
DELETE FROM patient WHERE PatNum = 1  -- No deletes
INSERT INTO patient (LName) VALUES ('Jones')  -- No inserts
DROP TABLE patient  -- No DDL
```

### ❌ Query Timeout

**Error:**
```
QueryTimeoutError: Query exceeded 30 second timeout
```

**Solution:**
```bash
# Increase timeout
opendental-query config set query.timeout_seconds 60

# Or use CLI flag
opendental-query query --timeout 60

# Optimize query:
# - Add WHERE clause to filter rows
# - Add LIMIT to reduce result size
# - Check OpenDental database indexes
```

### ❌ Connection Refused

**Error:**
```
httpx.ConnectError: Connection refused to https://api.opendental.com
```

**Solution:**
```bash
# Check network connectivity
ping api.opendental.com

# Test HTTPS
curl -I https://api.opendental.com

# Check firewall/proxy settings
# Verify OpenDental API is accessible

# Test with simple query
curl -X POST https://api.opendental.com/api/queries \
  -H "Content-Type: application/json" \
  -d '{"DeveloperKey": "xxx", "CustomerKey": "yyy", "SQL": "SELECT 1"}'
```

### ❌ SSL Certificate Verification Failed

**Error:**
```
httpx.SSLError: SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution:**
```bash
# Check if certificate is valid
openssl s_client -connect api.opendental.com:443 -showcerts

# If corporate proxy/firewall:
# Option 1: Install corporate root CA
# Option 2: Disable SSL verification (NOT RECOMMENDED for production)
opendental-query config set network.verify_ssl false
```

### ❌ Authentication Failed (API)

**Error:**
```
HTTP 401: Unauthorized - Invalid DeveloperKey or CustomerKey
```

**Solution:**
1. Verify credentials in vault:
   ```bash
   opendental-query vault-list
   ```

2. Check credentials in OpenDental admin panel

3. Re-add office with correct keys:
   ```bash
   opendental-query vault-remove-office MainOffice
   opendental-query vault-add-office
   # Enter correct CustomerKey
   ```

4. Update DeveloperKey:
   ```bash
   opendental-query vault-update-developer-key
   ```

---

## Data/Result Issues

### ❌ Schema Inconsistency

**Error:**
```
WARNING: Schema inconsistency detected across offices
Office A: [PatNum, LName, FName]
Office B: [PatNum, LName, FName, Email]
```

**Solution:**
```sql
-- Ensure all offices have same OpenDental version
-- Or explicitly select columns:
SELECT PatNum, LName, FName FROM patient

-- Not: SELECT * FROM patient
```

### ❌ Empty Results

**Issue:** Query returns 0 rows across all offices

**Solution:**
1. Test query on single office first:
   ```bash
   opendental-query query --office MainOffice
   ```

2. Check query syntax:
   ```sql
   -- Test with simple query
   SELECT COUNT(*) FROM patient
   ```

3. Verify data exists:
   - Log into OpenDental directly
   - Run query in OpenDental query tool

### ❌ Encoding/Unicode Issues

**Error:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**Solution:**
```bash
# Check terminal encoding
echo $LANG  # Should be UTF-8

# Set UTF-8
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# On Windows:
chcp 65001  # Set PowerShell to UTF-8
```

---

## Export Issues

### ❌ CSV Export Failed

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/path/to/export.csv'
```

**Solution:**
```bash
# Check write permissions
ls -ld ~/Downloads/

# Specify different directory
opendental-query config set export.default_directory "/tmp"

# Or use CLI flag
opendental-query query --export --output /tmp/results.csv
```

### ❌ CSV File Corrupted

**Issue:** Excel shows garbled characters

**Solution:**
```bash
# Export with BOM for Excel compatibility
# (Feature request - manual workaround:)

# Add BOM to CSV
printf '\xEF\xBB\xBF' | cat - export.csv > export_with_bom.csv

# Or open in Excel:
# Data > From Text/CSV > UTF-8 encoding
```

---

## Performance Issues

### ❌ Slow Query Execution

**Issue:** Queries take longer than expected

**Solution:**
1. **Enable parallel execution:**
   ```bash
   opendental-query config set query.parallel_execution true
   ```

2. **Optimize query:**
   ```sql
   -- Add indexes in OpenDental
   CREATE INDEX idx_patient_lname ON patient(LName);
   
   -- Use LIMIT for testing
   SELECT * FROM patient LIMIT 100
   
   -- Avoid SELECT * (specify columns)
   SELECT PatNum, LName, FName FROM patient
   ```

3. **Reduce office count:**
   ```bash
   # Query subset of offices
   opendental-query query --office "MainOffice,BranchA"
   ```

### ❌ High Memory Usage

**Issue:** Tool consumes excessive RAM

**Solution:**
```bash
# Use LIMIT to reduce result size
SELECT * FROM patient LIMIT 1000

# Export directly to CSV (streams results)
opendental-query query --export

# Query offices sequentially (not parallel)
opendental-query config set query.parallel_execution false
```

---

## Logging/Audit Issues

### ❌ Audit Log Too Large

**Issue:** `audit.jsonl` file is large (>100MB)

**Solution:**
```bash
# Run cleanup (removes entries >90 days old)
opendental-query audit cleanup

# Check current size
du -h ~/.opendental-query/audit.jsonl

# Manual cleanup (CAUTION: Affects compliance)
# Keep last 1000 lines:
tail -1000 ~/.opendental-query/audit.jsonl > audit_temp.jsonl
mv audit_temp.jsonl ~/.opendental-query/audit.jsonl
```

### ❌ Cannot Write to Audit Log

**Error:**
```
OSError: [Errno 28] No space left on device
```

**Solution:**
```bash
# Check disk space
df -h

# Free up space or move audit log:
export OPENDENTAL_AUDIT_LOG="/external/drive/audit.jsonl"
```

---

## Configuration Issues

### ❌ Config Not Persisting

**Issue:** Changes revert after restart

**Solution:**
```bash
# Ensure config is saved
opendental-query config set vault.auto_lock_minutes 10
# (Auto-saves)

# Verify config file
cat ~/.opendental-query/config.json

# Check file permissions
chmod 644 ~/.opendental-query/config.json
```

### ❌ Config File Corrupted

**Error:**
```
json.JSONDecodeError: Expecting value: line 1 column 1
```

**Solution:**
```bash
# Backup corrupted config
mv ~/.opendental-query/config.json ~/.opendental-query/config.json.bak

# Reset to defaults
opendental-query config reset --all

# Manually restore settings
opendental-query config set vault.auto_lock_minutes 5
```

---

## Platform-Specific Issues

### Windows

**Issue:** PowerShell encoding errors

**Solution:**
```powershell
# Set UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONUTF8 = "1"

# Add to PowerShell profile:
notepad $PROFILE
# Add: $env:PYTHONUTF8 = "1"
```

**Issue:** Path with spaces

**Solution:**
```powershell
# Use quotes
opendental-query config set export.default_directory "C:\Users\John Doe\Downloads"
```

### macOS

**Issue:** "command not found" after installation

**Solution:**
```bash
# Add to PATH in ~/.zshrc or ~/.bash_profile
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Issue:** Keychain access prompts

**Solution:**
```bash
# Allow Python to access Keychain
# System Preferences > Security & Privacy > Privacy > Full Disk Access
# Add Python and Terminal
```

### Linux

**Issue:** Permission errors with vault file

**Solution:**
```bash
# Ensure proper ownership
sudo chown $USER:$USER ~/.opendental-query/vault.enc
chmod 600 ~/.opendental-query/vault.enc
```

---

## Getting Help

### Diagnostic Information

When reporting issues, include:

```bash
# Python version
python --version

# Package versions
pip list | grep -E "opendental|argon2|cryptography|httpx"

# OS info
uname -a  # Linux/Mac
systeminfo  # Windows

# Config
opendental-query config list

# Recent audit logs
tail -20 ~/.opendental-query/audit.jsonl

# Application log
tail -50 ~/.opendental-query/app.log
```

### Debug Mode

```bash
# Enable verbose logging
opendental-query --verbose query

# Check debug logs
tail -f ~/.opendental-query/app.log

# Python debug
export PYTHONVERBOSE=1
opendental-query query
```

### Common Log Patterns

```bash
# Find authentication failures
grep "AUTHENTICATION_FAILED" ~/.opendental-query/audit.jsonl

# Count queries per office
jq -r '.details.office_count' ~/.opendental-query/audit.jsonl | sort | uniq -c

# Find errors
grep ERROR ~/.opendental-query/app.log | tail -20
```

---

## Known Issues

### Issue: Auto-lock timer doesn't work in some terminals

**Workaround:** Manually lock vault when done:
```bash
opendental-query vault-lock
```

### Issue: Progress bar not visible in CI/CD

**Workaround:** Disable progress bar:
```bash
export OPENDENTAL_NO_PROGRESS=1
```

---

## Still Having Issues?

1. **Check documentation:**
   - README.md
   - SECURITY.md
   - API_REFERENCE.md

2. **Search existing issues:**
   - GitHub Issues
   - Stack Overflow (tag: opendental)

3. **Create new issue:**
   - Include diagnostic information
   - Steps to reproduce
   - Expected vs actual behavior

4. **Contact support:**
   - Email: support@example.com
   - Include logs (redact sensitive info)

---

**Last Updated**: October 2025  
**Version**: 1.0.0
