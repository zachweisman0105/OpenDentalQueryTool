"""Query execution data models."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class OfficeQueryStatus(str, Enum):
    """Status of an office query execution."""

    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


class QueryRequest(BaseModel):
    """Request to execute a SQL query against office databases.

    Attributes:
        query: SQL query to execute
        office_ids: List of office IDs to query (empty list = all offices)
        timeout_seconds: Query timeout in seconds
        add_order_by: Whether to inject ORDER BY if missing
    """

    query: str = Field(..., min_length=1, description="SQL query to execute")
    office_ids: list[str] = Field(
        default_factory=list, description="Office IDs to query (empty = all offices)"
    )
    timeout_seconds: int | None = Field(default=None, ge=1, description="Query timeout in seconds")
    add_order_by: bool = Field(default=True, description="Inject ORDER BY if missing")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "SELECT PatNum, LName, FName FROM patient LIMIT 10",
                    "office_ids": ["main-office", "branch-office"],
                    "timeout_seconds": 300,
                    "add_order_by": True,
                }
            ]
        }
    }


class QueryResult(BaseModel):
    """Result of executing a query against a single office database.

    Attributes:
        office_id: Office identifier this result belongs to
        success: Whether query executed successfully
        error: Error message if query failed
        rows: List of result rows (each row is a dict)
        row_count: Number of rows returned
        columns: List of column names
        execution_time_ms: Query execution time in milliseconds
        timestamp: When the query was executed
    """

    office_id: str | None = Field(default=None, description="Office identifier")
    success: bool | None = Field(default=None, description="Query execution success status")
    error: str | None = Field(default=None, description="Error message if query failed")
    rows: list[dict[str, Any]] = Field(default_factory=list, description="Query result rows")
    row_count: int = Field(default=0, ge=0, description="Number of rows returned")
    columns: list[str] = Field(default_factory=list, description="Column names")
    execution_time_ms: float = Field(
        default=0.0, ge=0.0, description="Query execution time in milliseconds"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Query execution timestamp"
    )

    def has_data(self) -> bool:
        """Check if result contains any rows.

        Returns:
            True if rows exist, False otherwise
        """
        return self.row_count > 0

    def get_summary(self) -> str:
        """Get a summary string of the query result.

        Returns:
            Human-readable summary of the result
        """
        if self.success:
            return f"{self.office_id}: {self.row_count} rows in {self.execution_time_ms:.2f}ms"
        else:
            return f"{self.office_id}: ERROR - {self.error}"

    model_config = {
        "extra": "allow",
        "json_schema_extra": {
            "examples": [
                {
                    "office_id": "main-office",
                    "success": True,
                    "error": None,
                    "rows": [
                        {"PatNum": 1, "LName": "Smith", "FName": "John"},
                        {"PatNum": 2, "LName": "Doe", "FName": "Jane"},
                    ],
                    "row_count": 2,
                    "columns": ["PatNum", "LName", "FName"],
                    "execution_time_ms": 45.3,
                    "timestamp": "2025-10-21T10:30:00Z",
                }
            ]
        },
    }


class OfficeQueryResult(BaseModel):
    """Result of executing a query against a single office.

    Used by QueryEngine for parallel execution tracking.

    Attributes:
        office_id: Office identifier
        status: Query execution status (SUCCESS, ERROR, TIMEOUT)
        rows: Query result rows
        row_count: Number of rows returned
        error_message: Error message if status is ERROR or TIMEOUT
    """

    office_id: str = Field(..., description="Office identifier")
    # Make status optional with a default to improve ergonomics in tests
    status: OfficeQueryStatus = Field(
        default=OfficeQueryStatus.SUCCESS, description="Query execution status"
    )
    rows: list[dict[str, Any]] = Field(default_factory=list, description="Result rows")
    row_count: int = Field(default=0, ge=0, description="Number of rows")
    error_message: str | None = Field(default=None, description="Error message if failed")


class MergedQueryResult(BaseModel):
    """Merged results from multiple offices.

    Combines results from parallel office queries with metadata about success/failure.

    Attributes:
        office_results: Individual results from each office
        all_rows: All rows merged together with Office column injected
        total_offices: Total number of offices queried
        successful_count: Number of offices that completed successfully
        failed_count: Number of offices that failed or timed out
        schema_consistent: Whether all offices returned consistent schemas
    """

    office_results: list[OfficeQueryResult] = Field(..., description="Per-office results")
    all_rows: list[dict[str, Any]] = Field(..., description="Merged rows with Office column")
    total_offices: int = Field(..., ge=0, description="Total offices queried")
    successful_count: int = Field(..., ge=0, description="Successful queries")
    failed_count: int = Field(..., ge=0, description="Failed queries")
    schema_consistent: bool = Field(..., description="Schema consistency flag")
