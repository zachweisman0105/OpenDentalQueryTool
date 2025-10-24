"""Audit logging data models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    """Audit log entry for tracking security-relevant events.

    Attributes:
        timestamp: When the event occurred (ISO 8601 UTC)
        event_type: Type of event (vault_unlock, vault_lock, query_execute, etc.)
        user: System username who performed the action
        office_id: Office identifier if applicable
        success: Whether the action succeeded
        details: Additional event-specific details
        ip_address: Optional IP address of the client
        error: Optional error message if action failed
    """

    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp in UTC"
    )
    event_type: str = Field(..., min_length=1, description="Type of audit event")
    user: str = Field(..., min_length=1, description="System username")
    office_id: str | None = Field(default=None, description="Office identifier if applicable")
    success: bool = Field(..., description="Action success status")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional event details")
    ip_address: str | None = Field(default=None, description="Client IP address")
    hostname: str | None = Field(default=None, description="Hostname that generated the event")
    session_id: str | None = Field(
        default=None, description="Unique identifier for the CLI session emitting the event"
    )
    error: str | None = Field(default=None, description="Error message if failed")

    def to_jsonl(self) -> str:
        """Convert audit entry to JSONL format (single-line JSON).

        Returns:
            JSON string representation for JSONL file
        """
        import orjson

        # Use orjson for fast serialization with datetime support
        json_bytes = orjson.dumps(
            self.model_dump(), option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_UTC_Z
        )
        return json_bytes.decode("utf-8")

    @classmethod
    def from_jsonl(cls, line: str) -> "AuditEntry":
        """Parse audit entry from JSONL line.

        Args:
            line: JSON string from JSONL file

        Returns:
            Parsed AuditEntry object
        """
        import orjson

        data = orjson.loads(line)
        return cls(**data)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "timestamp": "2025-10-21T10:30:00Z",
                    "event_type": "query_execute",
                    "user": "johndoe",
                    "office_id": "main-office",
                    "success": True,
                    "details": {
                        "query_hash": "5d6bcb1a02c9377b5d32b9e2edfdc80fe3cfbec5aac6ed444f2b358d96484f5b",
                        "row_count": 1,
                        "execution_time_ms": 23.5,
                    },
                    "ip_address": "192.168.1.50",
                    "hostname": "reporting-ws-01",
                    "session_id": "c5c82ad2c9aa4b0b8b5d5b4c0ad87512",
                    "error": None,
                }
            ]
        }
    }
