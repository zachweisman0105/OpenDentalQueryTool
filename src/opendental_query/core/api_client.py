"""
API client for OpenDental FHIR API.

Handles HTTP communication, authentication, pagination, and retries.
"""

from typing import Any, Callable

import httpx
import orjson

from opendental_query.core.retry import retry_with_backoff


class APIClient:
    """Client for OpenDental FHIR API queries."""

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        """
        Initialize API client.

        Args:
            base_url: OpenDental API base URL (must be HTTPS)
            timeout: Request timeout in seconds (default: 30.0)

        Raises:
            ValueError: If base_url is not HTTPS
        """
        if not base_url.startswith("https://"):
            if base_url.startswith("http://"):
                raise ValueError(
                    f"HTTPS required for API base URL. Found insecure HTTP: {base_url}"
                )
            raise ValueError(f"Invalid API base URL. Must start with https://: {base_url}")

        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=httpx.Timeout(timeout),
            verify=True,  # Enforce SSL certificate verification
        )

    def __del__(self) -> None:
        """Close HTTP client on cleanup."""
        if hasattr(self, "_client"):
            self._client.close()

    @retry_with_backoff(max_retries=5, initial_delay=1.0)
    def query(
        self,
        sql: str,
        developer_key: str,
        customer_key: str,
        *,
        progress_callback: Callable[[int], None] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute SQL query against OpenDental API with pagination.

        Automatically handles OFFSET-based pagination, fetching all pages
        until receiving < 100 rows.

        Args:
            sql: SQL SELECT query to execute
            developer_key: OpenDental DeveloperKey
            customer_key: OpenDental CustomerKey for specific office

        Returns:
            List of result rows as dictionaries

        Raises:
            httpx.HTTPStatusError: On HTTP errors (4xx/5xx)
            ValueError: On invalid response format
        """
        all_rows: list[dict[str, Any]] = []
        offset = 0

        while True:
            # Build request URL with optional offset parameter
            url = f"{self.base_url}/queries/ShortQuery"
            if offset > 0:
                url += f"?Offset={offset}"

            # Build auth header: ODFHIR {dev_key}/{cust_key}
            headers = {
                "Authorization": f"ODFHIR {developer_key}/{customer_key}",
                "Content-Type": "application/json",
            }

            # Send PUT request with SQL in JSON payload (per API spec)
            response = self._client.put(
                url,
                json={"SqlCommand": sql},
                headers=headers,
            )

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text.strip()
                if detail:
                    raise httpx.HTTPStatusError(
                        f"{exc} - Response body: {detail}",
                        request=exc.request,
                        response=exc.response,
                    ) from exc
                raise

            # Parse JSON response
            try:
                response_data = orjson.loads(response.content)
            except orjson.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON response: {e}") from e

            # Extract data array
            if isinstance(response_data, list):
                rows = response_data
            elif isinstance(response_data, dict):
                data = response_data.get("data")
                if data is None:
                    data = response_data.get("Data")
                if not isinstance(data, list):
                    raise ValueError(
                        "Response missing 'data' array or it is not a list"
                    )
                rows = data
            else:
                raise ValueError(f"Unexpected JSON payload type: {type(response_data)}")

            # Add rows to result
            all_rows.extend(rows)
            if progress_callback is not None:
                try:
                    progress_callback(len(all_rows))
                except Exception:
                    # Progress callbacks must never break query execution
                    pass

            # Stop pagination if we got < 100 rows
            if len(rows) < 100:
                break

            # Move to next page
            offset += len(rows)

        return all_rows

    def close(self) -> None:
        """Explicitly close the HTTP client."""
        self._client.close()
