<!--
SYNC IMPACT REPORT
==================
Version Change: Template → 1.0.0
New Constitution: Initial ratification for OpenDental Multi-Office ShortQuery CLI
Added Sections:
  - Project Identity
  - Core Principles (I-VII)
  - API Contract Requirements
  - CLI Commands Specification
  - Security & Compliance (HIPAA)
  - Concurrency & Performance
  - Data Export & Output
  - Auditing & Logging
  - Error Handling & Codes
  - Governance
Templates Requiring Updates: ✅ Constitution created
Follow-up TODOs: None - all placeholders filled
==================
-->

# OpenDental Multi-Office ShortQuery CLI Constitution

```yaml
project:
  name: "OpenDental Multi-Office ShortQuery CLI"
  description: "Local, HIPAA-Compliant Python CLI for querying OpenDental Remote API across multiple offices"
  runtime: "Python 3.11+"
  deployment: "Local execution only - no cloud/remote components"
  
## Core Principles

### I. HIPAA Compliance (NON-NEGOTIABLE)

**Rules:**
- NO Protected Health Information (PHI) SHALL be logged, cached, or persisted except in user-initiated CSV exports
- All network communication MUST use HTTPS exclusively - HTTP connections SHALL be rejected
- Credential storage MUST use Argon2id key derivation + AES-GCM encryption
- CSV exports MUST use random filenames to prevent predictable file access
- Application MUST run locally only - no cloud components or remote telemetry
- Log retention MUST be limited to 30 days maximum
- Audit logs MUST record all credential access and query executions (metadata only, no PHI)

**Rationale:**
HIPAA mandates strict controls over PHI access, transmission, and storage. This principle ensures
the tool can be used in healthcare environments without creating compliance violations.

### II. OpenDental API Contract

**Rules:**
- API Endpoint: MUST use PUT method to `/queries/ShortQuery?offset={n}`
- Authentication Header: MUST be formatted as `Authorization: ODFHIR {DeveloperKey}/{CustomerKey}`
- DeveloperKey: ONE global key shared across all offices, stored in secure vault
- CustomerKey: PER-OFFICE keys, each stored separately in secure vault with office identifier
- Request Body: MUST contain SQL query string in OpenDental ShortQuery format
- Response Handling: MUST parse JSON response containing query results
- Offset Parameter: MUST be used for pagination when result sets exceed single response limits
- Connection Requirements: MUST enforce HTTPS - reject any HTTP endpoints

**Rationale:**
The OpenDental Remote API has a specific contract that must be honored exactly to ensure
compatibility. Deviation from this contract will result in authentication failures or data corruption.

### III. Resilient Network Operations

**Rules:**
- MUST implement exponential backoff retry logic for all API calls
- Retry parameters:
  - Initial delay: 1 second
  - Maximum retries: 5 attempts
  - Backoff multiplier: 2x
  - Maximum delay: 32 seconds
  - Jitter: ±25% randomization to prevent thundering herd
- Transient errors (5xx, network timeouts, connection errors) MUST trigger retries
- Authentication errors (401, 403) MUST NOT retry - fail immediately
- Client errors (400, 404) MUST NOT retry - fail immediately
- Request timeout: 30 seconds per API call
- Total operation timeout: 5 minutes per office query

**Rationale:**
Healthcare systems may experience intermittent network issues. Exponential backoff ensures
resilience without overwhelming the API server during outages.

### IV. Parallel Multi-Office Execution

**Rules:**
- MUST query multiple offices concurrently using thread pool or async execution
- Maximum concurrent office queries: 10 (configurable)
- Each office query MUST execute independently - one office failure SHALL NOT block others
- Results MUST include an "Office" column identifying the source office for each row
- Office column MUST be prepended as the first column in merged results
- Result merging MUST preserve row order within each office's results
- Result merging MUST clearly separate results from different offices (Office column value)
- Progress indication MUST show per-office query status during execution

**Rationale:**
Multi-office dental practices need to query all locations simultaneously to avoid lengthy
sequential waits. Isolation ensures partial results are always available.

### V. Secure Credential Vault

**Rules:**
- Vault file location: `~/.opendental-query/vault.enc` (user home directory)
- Encryption: AES-256-GCM with authenticated encryption
- Key Derivation: Argon2id with parameters:
  - Memory: 64 MB
  - Iterations: 3
  - Parallelism: 4
  - Salt: 16 bytes (random, stored with vault)
- Master password: User-provided, NEVER stored on disk
- Vault structure:
  ```yaml
  vault:
    developer_key: "global_key_value"
    offices:
      - office_id: "MainOffice"
        customer_key: "office_specific_key"
      - office_id: "BranchOffice"
        customer_key: "office_specific_key"
  ```
- Vault operations:
  - `init`: Create new vault with master password
  - `add-office`: Add new office CustomerKey
  - `remove-office`: Remove office from vault
  - `update-developer-key`: Rotate global DeveloperKey
  - `change-password`: Re-encrypt vault with new master password
- Vault MUST be locked (re-require password) after 15 minutes of inactivity
- Failed password attempts: Lock vault after 3 failures, require 60-second cooldown

**Rationale:**
Healthcare credentials require military-grade protection. Argon2id resists GPU/ASIC attacks,
and AES-GCM provides both confidentiality and integrity.

### VI. Excel-Style Table Rendering

**Rules:**
- Console output MUST render results in a formatted table with:
  - Column headers in BOLD or highlighted
  - Alternating row colors (if terminal supports ANSI colors)
  - Column width auto-sizing based on content (max 50 chars per column)
  - Truncation indicator (`...`) for oversized cells
  - Right-alignment for numeric columns, left-alignment for text
  - Row separator lines every 20 rows for readability
- Color scheme (if supported):
  - Header row: Cyan background, white text
  - Odd rows: Default background
  - Even rows: Dark gray background
  - Error rows: Red background (if query failed for that office)
- Pagination: Display 50 rows per page with `[Press Enter for more, Q to quit]` prompt
- MUST detect terminal capabilities - graceful fallback to plain ASCII if colors unsupported

**Rationale:**
Healthcare professionals need to quickly scan large result sets. Excel-style formatting
provides familiar visual cues and improves data comprehension.

### VII. Automatic CSV Export

**Rules:**
- MUST automatically export ALL query results to CSV after successful execution
- Export location: User's Downloads folder (`~/Downloads` on Linux/Mac, `%USERPROFILE%\Downloads` on Windows)
- Filename format: `opendental_query_{RANDOM_8_CHARS}_{TIMESTAMP}.csv`
  - RANDOM_8_CHARS: Alphanumeric random string (cryptographically secure)
  - TIMESTAMP: ISO 8601 format `YYYYMMDD_HHMMSS`
  - Example: `opendental_query_a7k3m9p2_20251021_143022.csv`
- CSV format:
  - UTF-8 encoding with BOM for Excel compatibility
  - Comma delimiter
  - Double-quote text qualifier
  - Escaped quotes: `""` (double double-quote)
  - Header row included
  - Office column MUST be first column
- Export confirmation MUST display full file path to user
- If Downloads folder inaccessible, fallback to current working directory
- MUST NOT overwrite existing files - always generate unique random filename

**Rationale:**
Random filenames prevent predictable file access (HIPAA requirement). Automatic export ensures
users always have a persistent copy without manual intervention.

## CLI Commands Specification

```yaml
commands:
  query:
    description: "Execute SQL query across one or more offices"
    syntax: "opendental-query query <sql-query> [--offices OFFICE1,OFFICE2] [--all-offices]"
    arguments:
      - sql-query: "SQL query string (required)"
    options:
      - "--offices": "Comma-separated office IDs (default: all configured offices)"
      - "--all-offices": "Explicitly query all offices in vault"
      - "--timeout": "Override default timeout in seconds (default: 300)"
      - "--max-concurrent": "Max concurrent office queries (default: 10)"
      - "--no-export": "Skip automatic CSV export"
      - "--export-path": "Override export directory (default: ~/Downloads)"
    exit_codes:
      0: "Success - all offices queried successfully"
      1: "Partial failure - some offices failed, results available for successful offices"
      2: "Total failure - all offices failed"
      3: "Authentication error - invalid credentials"
      4: "Vault error - cannot access credential vault"
      5: "Network error - cannot connect to API"
      
  vault-init:
    description: "Initialize new credential vault"
    syntax: "opendental-query vault-init"
    behavior:
      - "Prompts for master password (twice for confirmation)"
      - "Prompts for global DeveloperKey"
      - "Creates encrypted vault file"
      - "Validates password strength (min 12 chars, mixed case, numbers, symbols)"
    exit_codes:
      0: "Vault created successfully"
      10: "Vault already exists - use vault-reset to recreate"
      11: "Weak password rejected"
      
  vault-add-office:
    description: "Add office credentials to vault"
    syntax: "opendental-query vault-add-office <office-id> <customer-key>"
    arguments:
      - office-id: "Unique identifier for this office"
      - customer-key: "Office-specific CustomerKey from OpenDental"
    behavior:
      - "Prompts for master password to unlock vault"
      - "Adds office to vault"
      - "Re-encrypts vault"
    exit_codes:
      0: "Office added successfully"
      4: "Vault not found - run vault-init first"
      12: "Office ID already exists"
      13: "Invalid master password"
      
  vault-list-offices:
    description: "List all configured offices (does NOT display keys)"
    syntax: "opendental-query vault-list-offices"
    output: "Table of office IDs with last-used timestamp"
    exit_codes:
      0: "Success"
      4: "Vault not found"
      
  vault-remove-office:
    description: "Remove office from vault"
    syntax: "opendental-query vault-remove-office <office-id>"
    behavior:
      - "Prompts for master password"
      - "Removes office and re-encrypts vault"
    exit_codes:
      0: "Office removed"
      4: "Vault not found"
      14: "Office not found in vault"
      
  vault-update-developer-key:
    description: "Rotate global DeveloperKey"
    syntax: "opendental-query vault-update-developer-key <new-key>"
    behavior:
      - "Prompts for master password"
      - "Updates DeveloperKey and re-encrypts vault"
    exit_codes:
      0: "DeveloperKey updated"
      4: "Vault not found"
      
  check-update:
    description: "Check for new version on GitHub"
    syntax: "opendental-query check-update [--auto-install]"
    behavior:
      - "Polls GitHub repository releases API"
      - "Compares current version with latest release"
      - "Displays changelog if update available"
      - "With --auto-install: downloads and installs update"
    repository: "github.com/{owner}/{repo}"  # Configure during setup
    exit_codes:
      0: "No update available (or update installed successfully)"
      20: "Update available but not installed"
      21: "Update check failed (network error)"
      
  audit-log:
    description: "Display audit log entries"
    syntax: "opendental-query audit-log [--since YYYY-MM-DD] [--office OFFICE_ID]"
    output: "Table of audit events with timestamp, event type, office, user"
    exit_codes:
      0: "Success"
      
  version:
    description: "Display version and build information"
    syntax: "opendental-query version"
    output: "Version number, build date, Python version"
    exit_codes:
      0: "Success"
```

## Security & Compliance (HIPAA)

```yaml
security:
  encryption:
    vault_algorithm: "AES-256-GCM"
    key_derivation: "Argon2id"
    argon2_params:
      memory_mb: 64
      iterations: 3
      parallelism: 4
      salt_bytes: 16
    gcm_params:
      tag_length: 16
      nonce_bytes: 12
      
  network:
    enforce_https: true
    reject_http: true
    tls_minimum_version: "TLSv1.2"
    certificate_validation: true
    timeout_seconds: 30
    
  credentials:
    master_password_requirements:
      min_length: 12
      require_uppercase: true
      require_lowercase: true
      require_digits: true
      require_symbols: true
    lockout_policy:
      max_failed_attempts: 3
      lockout_duration_seconds: 60
    session_timeout_minutes: 15
    
  phi_protection:
    logging:
      level: "INFO"  # Only INFO and ERROR - no DEBUG in production
      retention_days: 30
      prohibited_fields:  # NEVER log these
        - "PatientName"
        - "SSN"
        - "DateOfBirth"
        - "MedicalRecordNumber"
        - "Address"
        - "Phone"
        - "Email"
      log_query_metadata: true  # Log query execution, NOT results
      log_office_ids: true
      log_timestamps: true
      log_error_messages: true  # Error messages only, not PHI
    csv_export:
      random_filename: true
      filename_entropy_bits: 40  # 8 alphanumeric chars
      no_predictable_names: true
      
  audit:
    startup_check: true
    log_events:
      - "vault_unlock"
      - "query_execution"
      - "csv_export"
      - "vault_modification"
      - "failed_authentication"
      - "application_startup"
      - "application_shutdown"
    audit_log_location: "~/.opendental-query/audit.log"
    audit_log_retention_days: 90  # Longer retention for audit trail
    audit_log_format: "JSON Lines (JSONL)"
    audit_log_fields:
      - "timestamp"
      - "event_type"
      - "office_id"
      - "success"
      - "error_code"
      - "user"  # OS username
      - "hostname"
```

## Concurrency & Performance

```yaml
concurrency:
  multi_office:
    executor: "ThreadPoolExecutor"  # or "asyncio" if preferred
    max_workers: 10
    worker_timeout_seconds: 300
    isolation: "complete"  # One office failure does NOT affect others
    
  retry_logic:
    strategy: "exponential_backoff_with_jitter"
    initial_delay_seconds: 1
    max_retries: 5
    backoff_multiplier: 2
    max_delay_seconds: 32
    jitter_percent: 25
    retry_on_status_codes: [500, 502, 503, 504, 429]
    retry_on_exceptions:
      - "ConnectionError"
      - "Timeout"
      - "RequestException"
    no_retry_on_status_codes: [400, 401, 403, 404]
    
  resource_limits:
    max_memory_mb: 512  # Per-office query memory limit
    max_result_rows: 100000  # Per-office result limit
    max_csv_size_mb: 100  # Alert if CSV exceeds this
    
  progress_reporting:
    show_progress_bar: true
    update_interval_seconds: 0.5
    display_per_office_status: true
    display_total_elapsed_time: true
```

## Data Export & Output

```yaml
output:
  console_table:
    renderer: "rich"  # Use Rich library for formatting (or similar)
    styling:
      header_style: "bold cyan on dark_blue"
      odd_row_style: "default"
      even_row_style: "on gray19"
      error_row_style: "bold red on dark_red"
    formatting:
      max_column_width: 50
      truncation_indicator: "..."
      numeric_alignment: "right"
      text_alignment: "left"
      row_separator_interval: 20
    pagination:
      rows_per_page: 50
      prompt: "[Press Enter for more, Q to quit]"
    fallback:
      ascii_only: true  # If terminal doesn't support colors
      
  csv_export:
    auto_export: true
    encoding: "utf-8-sig"  # UTF-8 with BOM for Excel
    delimiter: ","
    quotechar: '"'
    quoting: "MINIMAL"
    line_terminator: "\r\n"  # Windows-style for Excel compatibility
    include_header: true
    office_column_position: "first"
    office_column_name: "Office"
    default_location: "~/Downloads"
    fallback_location: "."  # Current directory
    filename_pattern: "opendental_query_{random}_{timestamp}.csv"
    timestamp_format: "%Y%m%d_%H%M%S"
    random_chars: 8
    random_charset: "abcdefghijklmnopqrstuvwxyz0123456789"
    max_file_size_warning_mb: 100
    
  logging:
    format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: "%Y-%m-%d %H:%M:%S"
    levels: ["INFO", "ERROR"]  # Only these levels in production
    file_location: "~/.opendental-query/app.log"
    rotation:
      max_size_mb: 10
      backup_count: 3
    retention_days: 30
```

## Auditing & Logging

```yaml
audit:
  startup_check:
    enabled: true
    checks:
      - "vault_file_exists"
      - "vault_file_permissions"  # Must be 0600 (user read/write only)
      - "audit_log_writable"
      - "downloads_folder_accessible"
      - "python_version"  # Must be 3.11+
      - "required_packages"
      - "network_connectivity"  # Basic HTTPS test
    on_failure:
      action: "abort_with_error"
      display_remediation_steps: true
      
  audit_log:
    enabled: true
    location: "~/.opendental-query/audit.log"
    format: "jsonl"  # JSON Lines - one JSON object per line
    retention_days: 90
    fields:
      timestamp: "ISO 8601 with timezone"
      event_type: "string (enum)"
      office_id: "string or null"
      query_hash: "SHA256(query) - NOT the query itself"
      success: "boolean"
      error_code: "integer or null"
      duration_ms: "integer"
      user: "OS username"
      hostname: "system hostname"
      
  event_types:
    - "app_start"
    - "app_shutdown"
    - "vault_unlock"
    - "vault_lock"
    - "vault_created"
    - "vault_modified"
    - "office_added"
    - "office_removed"
    - "developer_key_updated"
    - "query_executed"
    - "query_failed"
    - "csv_exported"
    - "auth_failure"
    - "network_error"
    - "update_checked"
    - "update_installed"
    
  prohibited_logging:
    never_log:
      - "master_password"
      - "developer_key"
      - "customer_key"
      - "query_results"  # Only log query hash, NOT content
      - "patient_data"
      - "phi_fields"
    log_metadata_only: true
```

## Error Handling & Codes

```yaml
errors:
  exit_codes:
    # Success
    0: "Success - operation completed successfully"
    
    # Query execution (1-9)
    1: "Partial failure - some offices failed, partial results available"
    2: "Total failure - all offices failed, no results"
    3: "Authentication error - invalid DeveloperKey or CustomerKey"
    4: "Vault error - cannot access or decrypt vault"
    5: "Network error - cannot connect to OpenDental API"
    6: "Invalid query - SQL syntax error or unsupported query"
    7: "Timeout error - query execution exceeded time limit"
    8: "Result size error - results exceed maximum allowed size"
    9: "Export error - CSV export failed"
    
    # Vault operations (10-19)
    10: "Vault already exists"
    11: "Weak password - does not meet requirements"
    12: "Office already exists in vault"
    13: "Invalid master password"
    14: "Office not found in vault"
    15: "Vault corrupted - cannot decrypt"
    16: "Vault file permission error"
    
    # Update operations (20-29)
    20: "Update available but not installed"
    21: "Update check failed - network error"
    22: "Update installation failed"
    
    # System errors (30-39)
    30: "Python version incompatible (requires 3.11+)"
    31: "Missing required dependencies"
    32: "Downloads folder inaccessible"
    33: "Insufficient permissions"
    34: "Disk space error"
    
    # Audit/Compliance (40-49)
    40: "Audit check failed - see remediation steps"
    41: "HTTPS enforcement violation - HTTP endpoint rejected"
    
  error_messages:
    user_friendly: true
    include_remediation: true
    include_error_code: true
    include_timestamp: true
    format: |
      [ERROR {code}] {message}
      
      {remediation_steps}
      
      For more information, see: {documentation_url}
      Time: {timestamp}
      
  exception_handling:
    catch_all_top_level: true
    log_stack_trace: true  # To log file only, NOT to console
    display_user_friendly_message: true
    never_expose_internal_paths: true
    never_expose_credentials: true
    
  network_errors:
    connection_error:
      message: "Cannot connect to OpenDental API. Check network connection and API URL."
      code: 5
    timeout_error:
      message: "Query timed out. Try increasing --timeout or simplifying your query."
      code: 7
    ssl_error:
      message: "SSL/TLS error. Verify server certificate is valid and not expired."
      code: 5
    http_error:
      message: "OpenDental API returned HTTP error {status_code}. Check credentials and query."
      code: 3
```

## Governance

**Amendment Process:**
1. Proposed amendments MUST be documented with rationale and impact analysis
2. All amendments MUST be reviewed for HIPAA compliance impact
3. Version number MUST be incremented according to semantic versioning:
   - MAJOR: Breaking changes to CLI interface, API contract, or security model
   - MINOR: New features, commands, or non-breaking enhancements
   - PATCH: Bug fixes, documentation updates, clarifications
4. Changes requiring code modifications MUST include updated tests
5. Security-related changes REQUIRE additional review and approval

**Compliance Review:**
- HIPAA compliance MUST be verified before every release
- Security audit MUST be conducted quarterly
- All credential handling code MUST undergo security review
- Logging behavior MUST be audited to ensure no PHI leakage
- Third-party dependencies MUST be vetted for security vulnerabilities

**Enforcement:**
- All code MUST pass security linting (bandit, safety)
- All code MUST pass type checking (mypy --strict)
- All code MUST have >90% test coverage
- All commits MUST reference constitution principles in commit messages when relevant
- CI/CD pipeline MUST enforce all governance rules

**Documentation:**
- User documentation MUST include HIPAA compliance guidance
- Developer documentation MUST reference constitution sections
- Security documentation MUST be kept current with threat model
- Runbook MUST include incident response procedures for credential leaks

**Constitution Authority:**
- This constitution supersedes all other project documentation
- Conflicts between constitution and code SHALL be resolved in favor of constitution
- Code that violates constitution MUST be rejected in code review
- Violations SHALL be tracked and remediated within 1 sprint

**Version**: 1.0.0 | **Ratified**: 2025-10-21 | **Last Amended**: 2025-10-21
```
