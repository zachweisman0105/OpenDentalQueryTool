# API Reference

**OpenDental Multi-Office Query Tool - Python API Documentation**

This document describes the Python API for programmatic use of the tool's components.

---

## Core Modules

### `opendental_query.core.vault`

#### `VaultManager`

Manages encrypted credential storage.

**Class:** `VaultManager(vault_path: Path, audit_log_path: Optional[Path] = None)`

**Methods:**

```python
def init(password: str, developer_key: str) -> None:
    """Initialize a new vault with master password.
    
    Args:
        password: Master password (no enforced complexity requirements)
        developer_key: OpenDental DeveloperKey (global API credential)
        
    Raises:
        ValueError: If password doesn't meet strength requirements
        VaultAlreadyExistsError: If vault file already exists
    """

def unlock(password: str) -> bool:
    """Unlock the vault with master password.
    
    Args:
        password: Master password
        
    Returns:
        True if unlock successful, False otherwise
        
    Raises:
        VaultLockedError: If vault is locked due to failed attempts
        VaultNotFoundError: If vault file doesn't exist
    """

def lock() -> None:
    """Lock the vault, clearing credentials from memory."""

def is_unlocked() -> bool:
    """Check if vault is currently unlocked."""

def add_office(office_id: str, customer_key: str) -> None:
    """Add office credentials to vault.
    
    Args:
        office_id: Unique identifier for the office
        customer_key: OpenDental CustomerKey for this office
        
    Raises:
        VaultLockedError: If vault is not unlocked
        OfficeAlreadyExistsError: If office_id already in vault
    """

def remove_office(office_id: str) -> None:
    """Remove office credentials from vault.
    
    Args:
        office_id: Office identifier to remove
        
    Raises:
        VaultLockedError: If vault is not unlocked
        OfficeNotFoundError: If office_id not in vault
    """

def list_offices() -> List[str]:
    """List all office IDs in vault.
    
    Returns:
        List of office identifiers
        
    Raises:
        VaultLockedError: If vault is not unlocked
    """

def get_developer_key() -> str:
    """Get the global DeveloperKey.
    
    Returns:
        DeveloperKey string
        
    Raises:
        VaultLockedError: If vault is not unlocked
    """

def get_office_credential(office_id: str) -> VaultCredentials:
    """Get credentials for a specific office.
    
    Args:
        office_id: Office identifier
        
    Returns:
        VaultCredentials object with office_id and customer_key
        
    Raises:
        VaultLockedError: If vault is not unlocked
        OfficeNotFoundError: If office_id not in vault
    """
```

**Example Usage:**

```python
from pathlib import Path
from opendental_query.core.vault import VaultManager

# Initialize new vault
vault = VaultManager(Path("~/.opendental-query/vault.enc").expanduser())
vault.init("MySecurePassword123!", "dev_key_abcdef")

# Add offices
vault.add_office("MainOffice", "customer_key_123")
vault.add_office("BranchA", "customer_key_456")

# Lock and unlock
vault.lock()
success = vault.unlock("MySecurePassword123!")
if success:
    offices = vault.list_offices()
    print(f"Available offices: {offices}")
```

---

### `opendental_query.core.query_engine`

#### `QueryEngine`

Executes SQL queries across multiple OpenDental offices in parallel.

**Class:** `QueryEngine(vault_manager: VaultManager, config: ConfigManager, audit_logger: AuditLogger)`

**Methods:**

```python
def execute_query(
    query: str, 
    office_ids: Optional[List[str]] = None,
    timeout_seconds: int = 30
) -> MergedQueryResult:
    """Execute SQL query across offices in parallel.
    
    Args:
        query: SQL query to execute
        office_ids: List of office IDs to query (None = all offices)
        timeout_seconds: Per-office query timeout
        
    Returns:
        MergedQueryResult with aggregated results
        
    Raises:
        VaultLockedError: If vault is not unlocked
        NoOfficesError: If no offices to query
    """

def validate_query(query: str) -> bool:
    """Validate that query is safe to execute.
    
    Args:
        query: SQL query string
        
    Returns:
        True if query is valid (SELECT only), False otherwise
    """
```

**Example Usage:**

```python
from opendental_query.core.query_engine import QueryEngine
from opendental_query.core.vault import VaultManager
from opendental_query.core.config import ConfigManager
from opendental_query.utils.audit_logger import AuditLogger

vault = VaultManager(vault_path)
vault.unlock("password")

config = ConfigManager(config_dir)
audit = AuditLogger(audit_log_path)

engine = QueryEngine(vault, config, audit)

# Execute query across all offices
result = engine.execute_query(
    "SELECT PatNum, LName FROM patient LIMIT 10",
    office_ids=None,  # All offices
    timeout_seconds=30
)

print(f"Total rows: {result.total_rows}")
print(f"Successful offices: {result.successful_count}")
print(f"Failed offices: {result.failed_count}")

for row in result.all_rows:
    print(row)
```

---

### `opendental_query.core.config`

#### `ConfigManager`

Manages application configuration.

**Class:** `ConfigManager(config_dir: Path)`

**Methods:**

```python
def get(key: str, default: Any = None) -> Any:
    """Get configuration value by key.
    
    Args:
        key: Dot-notation key (e.g., "vault.auto_lock_minutes")
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """

def set(key: str, value: Any) -> None:
    """Set configuration value.
    
    Args:
        key: Dot-notation key
        value: Value to set (bool, int, float, str)
    """

def save() -> None:
    """Persist configuration to disk."""

def to_dict() -> dict:
    """Export configuration as dictionary."""

def reset_to_defaults() -> None:
    """Reset all configuration to default values."""
```

**Configuration Keys:**

```python
# Vault settings
vault.auto_lock_minutes: int = 5          # Auto-lock timeout
vault.failed_attempts_limit: int = 3     # Lockout threshold
vault.lockout_duration_seconds: int = 60 # Lockout duration

# Query settings
query.timeout_seconds: int = 30           # Per-office query timeout
query.parallel_execution: bool = True     # Execute in parallel
query.max_retries: int = 3                # Retry failed queries

# Export settings
export.default_directory: str = "~/Downloads"
export.include_office_column: bool = True  # Add Office column to export
export.timestamp_format: str = "%Y%m%d_%H%M%S"

# Logging settings
logging.level: str = "INFO"                # DEBUG, INFO, WARNING, ERROR
logging.audit_retention_days: int = 90     # Audit log retention

# Network settings
network.verify_ssl: bool = True            # Verify HTTPS certificates
network.retry_backoff_factor: float = 2.0  # Exponential backoff multiplier
```

---

### `opendental_query.utils.audit_logger`

#### `AuditLogger`

HIPAA-compliant audit logging. Every event automatically records:

- System hostname and best-effort IP address
- A per-process session identifier (`session_id`)
- UTC timestamp and caller username
- Query fingerprints (`query_hash`) instead of raw SQL

**Class:** `AuditLogger(audit_file: Path)`

**Methods:**

```python
def log_vault_created() -> None:
    """Log vault creation event."""

def log_vault_unlocked() -> None:
    """Log successful vault unlock."""

def log_vault_locked() -> None:
    """Log vault lock event."""

def log_office_added(office_name: str) -> None:
    """Log office addition."""

def log_office_removed(office_name: str) -> None:
    """Log office removal."""

def log_query_executed(sql: str, offices: List[str]) -> None:
    """Log query execution (query is hashed, not stored plaintext).
    
    Args:
        sql: SQL query (will be SHA256-hashed)
        offices: List of office IDs queried
    """

def log_export_created(export_path: Path, row_count: int) -> None:
    """Log export creation."""

def log_authentication_failed(reason: str) -> None:
    """Log failed authentication attempt."""

def log_vault_lockout() -> None:
    """Log vault lockout event."""

def cleanup_old_entries() -> None:
    """Remove audit entries older than retention period (90 days)."""
```

**Audit Log Format:**

```json
{
  "timestamp": "2025-10-22T14:30:00.123456+00:00",
  "event_type": "QUERY_EXECUTED",
  "user": "john.doe",
  "hostname": "reporting-ws-01",
  "ip_address": "10.20.30.40",
  "session_id": "c5c82ad2c9aa4b0b8b5d5b4c0ad87512",
  "success": true,
  "details": {
    "query_hash": "5d6bcb1a02c9377b5d32b9e2edfdc80fe3cfbec5aac6ed444f2b358d96484f5b",
    "office_count": 3
  }
}
```

---

### `opendental_query.renderers.table`

#### `TableRenderer`

Rich console table rendering.

**Class:** `TableRenderer()`

**Methods:**

```python
def render(query_result: MergedQueryResult) -> str:
    """Render query results as formatted table.
    
    Args:
        query_result: Query results to render
        
    Returns:
        Formatted table string with ANSI colors
    """
```

---

### `opendental_query.renderers.excel_exporter`

#### `ExcelExporter`

Export query results to formatted Excel workbooks.

**Class:** `ExcelExporter(output_dir: Path | None = None)`

**Methods:**

```python
def export(
    rows: list[dict[str, Any]],
    output_dir: Path | None = None,
) -> Path:
    """Export query results to an Excel workbook.
    
    Args:
        rows: Rows to export
        output_dir: Optional target directory (defaults to secure Downloads directory)
        
    Returns:
        Path to created workbook
    """
```

---

## Data Models

### `opendental_query.models.query`

```python
class QueryResult(BaseModel):
    """Result from a single office query."""
    office_id: str
    success: bool
    error: Optional[str]
    rows: List[Dict[str, Any]]
    row_count: int
    columns: List[str]
    execution_time_ms: float

class MergedQueryResult(BaseModel):
    """Merged results from multiple offices."""
    office_results: List[OfficeQueryResult]
    all_rows: List[Dict[str, Any]]
    total_offices: int
    successful_count: int
    failed_count: int
    schema_consistent: bool
```

### `opendental_query.models.vault`

```python
class VaultCredentials(BaseModel):
    """Office credentials from vault."""
    office_id: str
    customer_key: str

class VaultMetadata(BaseModel):
    """Vault metadata."""
    version: int
    created_at: datetime
    failed_attempts: int
    locked_until: Optional[datetime]
```

---

## Exceptions

```python
# Vault exceptions
class VaultError(Exception):
    """Base exception for vault errors."""

class VaultNotFoundError(VaultError):
    """Vault file not found."""

class VaultAlreadyExistsError(VaultError):
    """Vault already exists."""

class VaultLockedError(VaultError):
    """Vault is locked."""

class InvalidPasswordError(VaultError):
    """Invalid master password."""

class OfficeNotFoundError(VaultError):
    """Office not found in vault."""

class OfficeAlreadyExistsError(VaultError):
    """Office already exists in vault."""

# Query exceptions
class QueryError(Exception):
    """Base exception for query errors."""

class InvalidQueryError(QueryError):
    """Invalid SQL query."""

class QueryTimeoutError(QueryError):
    """Query execution timeout."""

class NoOfficesError(QueryError):
    """No offices to query."""
```

---

## CLI Commands

### Vault Management

```bash
# Initialize vault
opendental-query vault-init

# Add office
opendental-query vault-add-office

# Remove office
opendental-query vault-remove-office <office_id>

# List offices
opendental-query vault-list

# Lock vault
opendental-query vault-lock
```

### Query Execution

```bash
# Execute query
opendental-query query [OPTIONS]

Options:
  --office TEXT       Office IDs to query (comma-separated, or ALL)
  --timeout INTEGER   Query timeout in seconds (default: 30)
  --export            Export results to Excel
  --output PATH       Output Excel file path
```

### Configuration

```bash
# Get config value
opendental-query config get <key>

# Set config value
opendental-query config set <key> <value>

# List all config
opendental-query config list

# Reset config
opendental-query config reset [--all]

# Show config file path
opendental-query config path
```

### Audit Logs

```bash
# Show recent audit events
opendental-query audit show [--limit 50]

# Cleanup old entries (>90 days)
opendental-query audit cleanup

# Export audit log
opendental-query audit export <output_file>
```

---

## Environment Variables

```bash
# Override config directory
export OPENDENTAL_CONFIG_DIR="/path/to/config"

# Override vault path
export OPENDENTAL_VAULT_PATH="/path/to/vault.enc"

# Override audit log path
export OPENDENTAL_AUDIT_LOG="/path/to/audit.jsonl"

# Set log level
export OPENDENTAL_LOG_LEVEL="DEBUG"  # DEBUG, INFO, WARNING, ERROR
```

---

## Testing

### Running Tests

```bash
# All tests
pytest tests/

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With coverage
pytest tests/ --cov=opendental_query --cov-report=html
```

### Test Fixtures

```python
@pytest.fixture
def temp_vault(tmp_path):
    """Create temporary vault for testing."""
    vault_path = tmp_path / "test.vault"
    vault = VaultManager(vault_path)
    vault.init("TestPassword123!", "test_dev_key")
    yield vault
    vault.lock()

@pytest.fixture
def mock_api_response():
    """Mock OpenDental API response."""
    return {
        "rows": [{"PatNum": 1, "LName": "Smith"}],
        "columns": ["PatNum", "LName"]
    }
```

---

**Last Updated**: October 2025  
**Version**: 1.0.0
