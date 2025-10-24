"""
QueryEngine for parallel multi-office query execution.

Uses ThreadPoolExecutor to execute SQL queries across multiple offices concurrently,
with per-office timeouts, independent failure handling, result merging, and schema validation.
"""

import concurrent.futures
from collections.abc import Callable
from typing import Any

from opendental_query.core.api_client import APIClient
from opendental_query.models.query import (
    MergedQueryResult,
    OfficeQueryResult,
    OfficeQueryStatus,
)
from opendental_query.utils.sql_parser import ensure_order_by


class QueryEngine:
    """
    Executes queries across multiple offices in parallel.

    Features:
    - ThreadPoolExecutor-based parallel execution with configurable concurrency
    - Per-office timeouts (default 5 minutes)
    - Independent failure handling (one office failure doesn't affect others)
    - Result merging with Office column injection
    - Schema consistency validation across offices
    - Automatic SQL ORDER BY injection for deterministic results
    """

    def __init__(self, max_concurrent: int = 10) -> None:
        """
        Initialize QueryEngine.

        Args:
            max_concurrent: Maximum number of concurrent office queries (default 10)
        """
        self.max_concurrent = max_concurrent

    def execute(
        self,
        sql: str,
        office_credentials: dict[str, tuple[str, str]],
        api_base_url: str,
        timeout_seconds: float = 300.0,
        progress_callback: Callable[[OfficeQueryResult], None] | None = None,
        row_progress_callback: Callable[[str, int], None] | None = None,
    ) -> MergedQueryResult:
        """
        Execute SQL query across multiple offices in parallel.

        Args:
            sql: SQL query to execute
            office_credentials: Dict mapping office_id -> (developer_key, customer_key)
            api_base_url: Base URL for OpenDental API
            timeout_seconds: Timeout per office in seconds (default 300 = 5 minutes)
            progress_callback: Optional callable invoked as each office completes
            row_progress_callback: Optional callable invoked with (office_id, total_rows)
                each time additional rows are fetched

        Returns:
            MergedQueryResult with all results and metadata

        Raises:
            ValueError: If schema is inconsistent across offices
        """
        # Preprocess SQL with ORDER BY injection
        processed_sql = ensure_order_by(sql)

        # Execute queries in parallel
        office_results: list[OfficeQueryResult] = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
            # Submit all office queries
            future_to_office: dict[concurrent.futures.Future[OfficeQueryResult], str] = {}

            for office_id, (dev_key, cust_key) in office_credentials.items():
                future = executor.submit(
                    self._execute_single_office,
                    office_id=office_id,
                    sql=processed_sql,
                    developer_key=dev_key,
                    customer_key=cust_key,
                    api_base_url=api_base_url,
                    timeout_seconds=timeout_seconds,
                    row_progress_callback=row_progress_callback,
                )
                future_to_office[future] = office_id

            # Wait for all futures with timeout
            done, not_done = concurrent.futures.wait(
                future_to_office.keys(),
                timeout=timeout_seconds,
            )

            # Collect results from completed futures
            for future in done:
                office_id = future_to_office[future]
                try:
                    result = future.result(timeout=0)  # Already done, no wait
                    office_results.append(result)
                    self._notify_progress(progress_callback, result)
                except Exception as e:
                    # Unexpected error getting result
                    error_result = OfficeQueryResult(
                        office_id=office_id,
                        status=OfficeQueryStatus.ERROR,
                        rows=[],
                        row_count=0,
                        error_message=f"Failed to retrieve result: {str(e)}",
                    )
                    office_results.append(error_result)
                    self._notify_progress(progress_callback, error_result)

            # Handle timed-out futures
            for future in not_done:
                office_id = future_to_office[future]
                future.cancel()
                timeout_result = OfficeQueryResult(
                    office_id=office_id,
                    status=OfficeQueryStatus.TIMEOUT,
                    rows=[],
                    row_count=0,
                    error_message=f"Query exceeded timeout of {timeout_seconds}s",
                )
                office_results.append(timeout_result)
                self._notify_progress(progress_callback, timeout_result)

        # Validate schema consistency
        self._validate_schema_consistency(office_results)

        # Merge results with Office column injection
        merged_rows = self._merge_results(office_results)

        # Build MergedQueryResult
        successful_results = [r for r in office_results if r.status == OfficeQueryStatus.SUCCESS]
        failed_results = [r for r in office_results if r.status != OfficeQueryStatus.SUCCESS]

        return MergedQueryResult(
            office_results=office_results,
            all_rows=merged_rows,
            total_offices=len(office_credentials),
            successful_count=len(successful_results),
            failed_count=len(failed_results),
            schema_consistent=True,  # We validate this earlier
        )

    def _execute_single_office(
        self,
        office_id: str,
        sql: str,
        developer_key: str,
        customer_key: str,
        api_base_url: str,
        timeout_seconds: float,
        row_progress_callback: Callable[[str, int], None] | None = None,
    ) -> OfficeQueryResult:
        """
        Execute query for a single office.

        Args:
            office_id: Office identifier
            sql: SQL query (already preprocessed)
            developer_key: API developer key
            customer_key: API customer key
            api_base_url: Base URL for API
            timeout_seconds: Timeout in seconds

        Returns:
            OfficeQueryResult with status and data
        """
        try:
            # Create API client
            client = APIClient(base_url=api_base_url, timeout=timeout_seconds)

            try:
                # Execute query
                def _handle_progress(total_rows: int) -> None:
                    if row_progress_callback is not None:
                        try:
                            row_progress_callback(office_id, total_rows)
                        except Exception:
                            # Never allow progress reporting to break execution
                            pass

                query_kwargs = {
                    "sql": sql,
                    "developer_key": developer_key,
                    "customer_key": customer_key,
                }
                if row_progress_callback:
                    query_kwargs["progress_callback"] = _handle_progress

                rows = client.query(**query_kwargs)

                return OfficeQueryResult(
                    office_id=office_id,
                    status=OfficeQueryStatus.SUCCESS,
                    rows=rows,
                    row_count=len(rows),
                    error_message=None,
                )

            finally:
                client.close()

        except concurrent.futures.TimeoutError:
            return OfficeQueryResult(
                office_id=office_id,
                status=OfficeQueryStatus.TIMEOUT,
                rows=[],
                row_count=0,
                error_message=f"Query exceeded timeout of {timeout_seconds}s",
            )

        except Exception as e:
            return OfficeQueryResult(
                office_id=office_id,
                status=OfficeQueryStatus.ERROR,
                rows=[],
                row_count=0,
                error_message=str(e),
            )

    @staticmethod
    def _notify_progress(
        callback: Callable[[OfficeQueryResult], None] | None,
        result: OfficeQueryResult,
    ) -> None:
        """Safely invoke the progress callback if provided."""
        if callback is None:
            return

        try:
            callback(result)
        except Exception:
            # Swallow callback errors to avoid disrupting query execution.
            pass

    def _validate_schema_consistency(self, office_results: list[OfficeQueryResult]) -> None:
        """
        Validate that all successful results have the same schema.

        Args:
            office_results: List of office results

        Raises:
            ValueError: If schemas are inconsistent
        """
        successful_results = [r for r in office_results if r.status == OfficeQueryStatus.SUCCESS]

        if len(successful_results) < 2:
            return  # Nothing to compare

        # Get schema from first non-empty result
        reference_schema: set[str] | None = None
        reference_office: str | None = None

        for result in successful_results:
            if result.rows:
                reference_schema = set(result.rows[0].keys())
                reference_office = result.office_id
                break

        if reference_schema is None:
            return  # All results are empty

        # Compare all other results
        for result in successful_results:
            if not result.rows:
                continue  # Skip empty results

            current_schema = set(result.rows[0].keys())
            if current_schema != reference_schema:
                raise ValueError(
                    f"Schema mismatch between offices. "
                    f"Office '{reference_office}' has columns {sorted(reference_schema)}, "
                    f"but office '{result.office_id}' has columns {sorted(current_schema)}"
                )

    def _merge_results(self, office_results: list[OfficeQueryResult]) -> list[dict[str, Any]]:
        """
        Merge results from all offices and inject Office column.

        Args:
            office_results: List of office results

        Returns:
            List of merged rows with Office column as first column
        """
        merged_rows: list[dict[str, Any]] = []

        for result in office_results:
            if result.status != OfficeQueryStatus.SUCCESS:
                continue

            for row in result.rows:
                # Inject Office column as first key
                merged_row = {"Office": result.office_id}
                merged_row.update(row)
                merged_rows.append(merged_row)

        return merged_rows
