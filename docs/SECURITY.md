## Security Guide

**OpenDental Multi-Office Query Tool - Security Documentation**

## Overview

This tool is designed with HIPAA compliance and security as top priorities. This document describes the security features, best practices, and compliance considerations.

---

## 🔒 Security Architecture

### Credential Storage

**Vault Encryption:**
- **Master Password**: User-provided password protecting the vault
  - Minimum 12 characters
  - Must include: uppercase, lowercase, numbers, symbols
  - Hashed with **Argon2id** (memory-hard KDF)
    - Time cost: 3 iterations
    - Memory cost: 64 MB
    - Parallelism: 4 threads
  - Generates 256-bit encryption key

- **Vault File Encryption**: **AES-256-GCM**
  - Authenticated encryption (prevents tampering)
  - Unique nonce per encryption operation
  - Stored in: `~/.opendental-query/vault.enc`
  - File permissions: `0600` (owner read/write only on Unix)

**What's Encrypted:**
- OpenDental DeveloperKey (global API credential)
- CustomerKeys for each office
- Office metadata

**What's NOT Encrypted:**
- Audit logs (no PHI, only hashed queries)
- Configuration files (no secrets)
- Application logs (no credentials)

### Auto-Lock Mechanism

**Automatic Vault Locking:**
- Default: 5 minutes of inactivity
- Configurable: `vault.auto_lock_minutes`
- Forces re-authentication for continued access
- Protects against unattended sessions

### Failed Authentication Protection

**Lockout Policy:**
- **3 failed password attempts** → 60-second lockout
- Counter resets on successful unlock
- Prevents brute-force attacks
- All attempts logged to audit trail

---

## 📝 HIPAA Compliance

### PHI Protection

**No PHI in Logs:**
- SQL queries are **SHA256-hashed** before logging
- Office identifiers and directory paths are hashed before persistence (no raw office IDs or filesystem paths)
- Original query text never written to audit log
- Query results never logged
- Patient names, SSNs, DOBs never touch logs

**Audit Trail:**
- Location: `~/.opendental-query/audit.jsonl`
- Format: JSON Lines (one event per line)
- Contents:
  - Event type (vault_unlock, query_execute, etc.)
  - Timestamp (UTC, ISO 8601)
  - System username
  - Success/failure status
  - Query hash (`query_hash` SHA256 digest, never plaintext SQL)
  - Office token list/count (hashed identifiers only)
  - File metadata (hashed export path, row/office counts)
  - Hostname, best-effort source IP, and per-session identifier for operator traceability

**Log Retention:**
- **90-day automatic retention**
- Older entries auto-deleted on cleanup
- Complies with HIPAA minimum requirements
- Cleanup: `opendental-query audit-cleanup`

### Data Flow

```
User Input → Memory → Network (HTTPS) → OpenDental API
                ↓
            (No disk writes)
                ↓
         Display → Terminal
                ↓
         Export → CSV (user-controlled location)
```

**Key Points:**
- Query results only in memory
- No temporary files with PHI
- CSV export requires explicit user opt-in (`--export` flag or interactive confirmation)
- Export metadata is logged without plaintext paths (hashed directory + filename)

---

## 🌐 Network Security

### HTTPS Enforcement

**TLS/SSL Requirements:**
- All API calls over HTTPS only
- Certificate validation enabled by default
- Minimum TLS 1.2 (httpx default)
- No insecure HTTP allowed

**Startup Validation:**
- Connectivity check to `https://www.google.com` on launch
- Verifies HTTPS stack working
- Fails fast if network issues

### API Authentication

**OpenDental API:**
- DeveloperKey: Global credential (per developer)
- CustomerKey: Per-office credential
- Both required for API access
- Transmitted in request body (HTTPS-encrypted)

---

## 🛡️ Threat Model

### Protected Against

✅ **Credential Theft from Disk**
- Vault encrypted with strong password
- Argon2id prevents offline attacks
- AES-256-GCM prevents file modification

✅ **Brute Force Attacks**
- Lockout after 3 failed attempts
- Argon2id makes each attempt expensive
- Auto-lock prevents unattended access

✅ **PHI Exposure in Logs**
- Queries hashed (SHA256)
- Results never logged
- Audit trail contains no PHI

✅ **Network Eavesdropping**
- HTTPS enforcement
- TLS encryption for all API calls

✅ **Unauthorized Access**
- Master password required
- Auto-lock on inactivity
- Per-session vault unlocking

### Limitations

⚠️ **Memory Dumps**
- Credentials and results in RAM while unlocked
- Mitigation: Auto-lock, minimize unlock time

⚠️ **Keyloggers**
- Master password entered at keyboard
- Mitigation: Use OS-level security (antivirus, EDR)

⚠️ **Social Engineering**
- Master password can be phished
- Mitigation: User training, password manager

⚠️ **Clipboard Monitoring**
- Query results may be copied to clipboard
- Mitigation: Clear clipboard after use

---

## 🔐 Best Practices

### Password Management

**Master Password:**
- **Use a password manager** (LastPass, 1Password, Bitwarden)
- Minimum 20+ characters recommended
- Unique (not reused from other services)
- Rotate quarterly or after personnel changes

**Example Strong Password:**
```
Correct-Horse-Battery-Staple-2025!
```

**Weak Passwords to Avoid:**
```
❌ Password123!
❌ Opendental2025
❌ Admin@123
```

### Access Control

**Workstation Security:**
- Lock screen when away (`Win+L` / `Ctrl+Cmd+Q`)
- Enable full-disk encryption (BitLocker / FileVault)
- Use antivirus and keep updated
- Enable firewall

**Multi-User Systems:**
- Each user has own OS account
- Separate vault per user
- File permissions enforced (Unix: `0600`)

### Query Safety

**SQL Injection Prevention:**
- Tool does NOT prevent SQL injection
- User is responsible for query safety
- Recommend: Use parameterized queries if available in OpenDental API

**Read-Only Enforcement:**
- CLI rejects mutating SQL (INSERT/UPDATE/DELETE/REPLACE, temp tables, etc.)
- Allowed commands: `SELECT`, `SHOW`, `DESC/DESCRIBE`, `EXPLAIN`
- Non-compliant statements exit with error code 2 and no API call is made

**Query Review:**
- Review queries before execution
- Avoid `SELECT *` (specify columns)
- Use `LIMIT` clauses for testing
- Test on single office first

### Export Security

**CSV Files:**
- Export to encrypted drive only
- Delete after use if possible
- Never email PHI-containing CSVs
- If must share: Use encrypted email (S/MIME, PGP)

**File Locations:**
- Default: `~/Downloads/`
- Recommendation: Temporary, encrypted folder
- Set in config: `export.default_directory`

---

## 📊 Audit and Monitoring

### Audit Log Review

**Regular Review:**
- Weekly review of audit logs
- Look for: unauthorized access attempts, unusual queries
- Tool: `opendental-query audit-show`

**Key Events to Monitor:**
```json
{
  "event_type": "AUTHENTICATION_FAILED",
  "timestamp": "2025-10-22T14:30:00Z",
  "user": "john.doe",
  "success": false
}
```

**Red Flags:**
- Multiple failed auth attempts
- Queries at unusual hours
- Queries from unexpected users
- High query volume

### Compliance Reporting

**HIPAA Audit Trail Requirements:**
✅ Who: `user` field (OS username)
✅ What: `event_type` (action performed)
✅ When: `timestamp` (UTC, ISO 8601)
✅ Success: `success` field (true/false)
✅ Query identifier: `query_hash` (SHA256)

**Export Audit Logs:**
```bash
# All events
cat ~/.opendental-query/audit.jsonl

# Filter for failed auth
jq 'select(.event_type == "AUTHENTICATION_FAILED")' ~/.opendental-query/audit.jsonl

# Count queries per user
jq -r '.user' ~/.opendental-query/audit.jsonl | sort | uniq -c
```

---

## 🚨 Incident Response

### Suspected Compromise

**If master password compromised:**
1. Immediately delete vault: `rm ~/.opendental-query/vault.enc`
2. Reinitialize with new password
3. Re-add all office credentials
4. Rotate OpenDental API keys (contact OpenDental support)
5. Review audit logs for unauthorized queries

**If API keys compromised:**
1. Contact OpenDental support to revoke keys
2. Generate new DeveloperKey and CustomerKeys
3. Update vault with new credentials
4. Review OpenDental audit logs for API usage

**If workstation compromised:**
1. Disconnect from network
2. Run full malware scan
3. If malware found: Consider full wipe/reinstall
4. Rotate all credentials (master password, API keys)
5. Review all audit logs since suspected compromise

---

## 🧪 Security Testing

### Verify Encryption

**Test vault encryption:**
```bash
# Create vault
opendental-query vault-init
# Password: TestPassword123!
# DeveloperKey: secret_key_12345

# Verify vault file encrypted
hexdump -C ~/.opendental-query/vault.enc | head

# Should see random bytes, NOT plaintext "secret_key_12345"
```

**Test auto-lock:**
```bash
# Unlock vault
opendental-query query
# Wait 5 minutes (default timeout)
# Try another query - should prompt for password again
```

### Verify Audit Logging

**Test PHI protection:**
```bash
# Run query with PHI
opendental-query query
# SQL: SELECT PatNum, LName, FName FROM patient WHERE PatNum = 123

# Check audit log
cat ~/.opendental-query/audit.jsonl | tail -1 | jq .

# Verify:
# - "query_hash" present (64-char hex)
# - "LName", "FName", "123" NOT present
```

---

## 📚 References

- **HIPAA Security Rule**: https://www.hhs.gov/hipaa/for-professionals/security/
- **NIST Password Guidelines**: https://pages.nist.gov/800-63-3/sp800-63b.html
- **Argon2 Specification**: https://tools.ietf.org/html/rfc9106
- **AES-GCM**: https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-38d.pdf

---

## 💬 Questions or Concerns?

If you have security questions or want to report a vulnerability:

- **Email**: security@example.com
- **Responsible Disclosure**: 90-day disclosure window
- **PGP Key**: Available on request

---

**Last Updated**: October 2025  
**Version**: 1.0.0


### CSV Export Controls

The CLI enforces secure export behavior by default:

- Exports are disabled unless the operator uses `--export` or confirms interactively after reviewing results.
- Export destinations must reside in `~/Downloads`, the default config directory, or an administrator-approved root set via `SPEC_KIT_EXPORT_ROOT`.
- Set `SPEC_KIT_ALLOW_UNSAFE_EXPORTS=1` only for testing or non-production environments.
- Optional encryption automation can be configured with `SPEC_KIT_EXPORT_ENCRYPTION_COMMAND` to wrap CSV files in an organization-specific tool.

