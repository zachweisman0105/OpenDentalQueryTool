"""Application-wide constants and configuration values."""

from pathlib import Path
from typing import Final

# Exit Codes (0-49 reserved for application use)
EXIT_SUCCESS: Final[int] = 0
EXIT_GENERAL_ERROR: Final[int] = 1
EXIT_INVALID_ARGS: Final[int] = 2
EXIT_CONFIG_ERROR: Final[int] = 3
EXIT_VAULT_LOCKED: Final[int] = 4
EXIT_VAULT_AUTH_FAILED: Final[int] = 5
EXIT_VAULT_NOT_FOUND: Final[int] = 6
EXIT_NETWORK_ERROR: Final[int] = 7
EXIT_DATABASE_ERROR: Final[int] = 8
EXIT_QUERY_ERROR: Final[int] = 9
EXIT_FILE_ERROR: Final[int] = 10
EXIT_PERMISSION_ERROR: Final[int] = 11
EXIT_TIMEOUT_ERROR: Final[int] = 12
EXIT_VALIDATION_ERROR: Final[int] = 13
EXIT_UPDATE_AVAILABLE: Final[int] = 20
EXIT_UPDATE_NETWORK_ERROR: Final[int] = 21

# Default Paths
DEFAULT_CONFIG_DIR: Final[Path] = Path.home() / ".opendental-query"
DEFAULT_CONFIG_FILE: Final[str] = "config.json"
DEFAULT_VAULT_FILE: Final[str] = "credentials.vault"
DEFAULT_LOG_FILE: Final[str] = "app.log"
DEFAULT_AUDIT_FILE: Final[str] = "audit.jsonl"
DEFAULT_SAVED_QUERIES_FILE: Final[str] = "saved_queries.json"

# Timeouts (in seconds)
DEFAULT_CONNECT_TIMEOUT: Final[int] = 10
DEFAULT_QUERY_TIMEOUT: Final[int] = 300  # 5 minutes
DEFAULT_VAULT_AUTO_LOCK: Final[int] = 900  # 15 minutes

# Security Limits
MAX_PASSWORD_ATTEMPTS: Final[int] = 3
PASSWORD_MIN_LENGTH: Final[int] = 12
ARGON2_TIME_COST: Final[int] = 3
ARGON2_MEMORY_COST: Final[int] = 65536  # 64 MB
ARGON2_PARALLELISM: Final[int] = 4
AES_KEY_SIZE: Final[int] = 256  # bits

# Concurrency Limits
MAX_CONCURRENT_QUERIES: Final[int] = 10
MAX_THREAD_POOL_SIZE: Final[int] = 10

# Logging Configuration
LOG_MAX_BYTES: Final[int] = 10 * 1024 * 1024  # 10 MB
LOG_BACKUP_COUNT: Final[int] = 5
LOG_RETENTION_DAYS: Final[int] = 90

# Output Limits
MAX_COLUMN_WIDTH: Final[int] = 50
MAX_ROWS_DISPLAY: Final[int] = 1000

# Network Configuration
DEFAULT_MYSQL_PORT: Final[int] = 3306
SSL_VERIFY: Final[bool] = True

# Validation Patterns
OFFICE_ID_PATTERN: Final[str] = r"^[a-zA-Z0-9_-]{1,50}$"
