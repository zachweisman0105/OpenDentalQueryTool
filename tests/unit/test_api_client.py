"""
Unit tests for APIClient.

Tests auth header formatting, request body construction, response parsing,
retry conditions, and OFFSET-based pagination with respx HTTP mocking.
"""

import json
import httpx
import pytest
import respx

from opendental_query.core.api_client import APIClient


class TestAuthHeaderFormatting:
    """Test ODFHIR auth header formatting."""

    @respx.mock
    def test_formats_auth_header_correctly(self) -> None:
        """Should format Authorization header as 'ODFHIR {dev_key}/{cust_key}'."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        # Mock the API endpoint
        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(
                200,
                json={"data": []},
            )
        )

        client.query("SELECT 1", "dev123", "cust456")

        # Verify auth header
        assert route.called
        request = route.calls.last.request
        assert request.headers["Authorization"] == "ODFHIR dev123/cust456"

    @respx.mock
    def test_auth_header_with_special_characters(self) -> None:
        """Should handle special characters in keys."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        client.query("SELECT 1", "dev-key_123", "cust-key_456")

        request = route.calls.last.request
        assert request.headers["Authorization"] == "ODFHIR dev-key_123/cust-key_456"


class TestRequestBodyConstruction:
    """Test request body formatting."""

    @respx.mock
    def test_sends_sql_in_request_body(self) -> None:
        """Should send SQL query in request body."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        sql = "SELECT PatNum, LName FROM patient LIMIT 10"
        client.query(sql, "dev123", "cust456")

        request = route.calls.last.request
        assert request.headers["Content-Type"] == "application/json"
        assert json.loads(request.content) == {"SqlCommand": sql}

    @respx.mock
    def test_sends_correct_content_type(self) -> None:
        """Should set Content-Type to application/json."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        client.query("SELECT 1", "dev123", "cust456")

        request = route.calls.last.request
        assert request.headers["Content-Type"] == "application/json"


class TestResponseParsing:
    """Test JSON response parsing and data extraction."""

    @respx.mock
    def test_parses_json_response(self) -> None:
        """Should parse JSON response and extract data array."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(
                200,
                json=[
                    {"PatNum": "1", "LName": "Smith"},
                    {"PatNum": "2", "LName": "Jones"},
                ],
            )
        )

        result = client.query("SELECT PatNum, LName FROM patient", "dev", "cust")

        assert len(result) == 2
        assert result[0] == {"PatNum": "1", "LName": "Smith"}
        assert result[1] == {"PatNum": "2", "LName": "Jones"}

    @respx.mock
    def test_parses_json_response_with_data_field(self) -> None:
        """Should support legacy payloads that wrap results in a 'data' field."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"Result": "ok"}]},
            )
        )

        result = client.query("SELECT 1", "dev", "cust")

        assert result == [{"Result": "ok"}]

    @respx.mock
    def test_returns_empty_list_for_empty_data(self) -> None:
        """Should return empty list when data array is empty."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        result = client.query("SELECT 1 WHERE 1=0", "dev", "cust")

        assert result == []

    @respx.mock
    def test_raises_error_on_invalid_json(self) -> None:
        """Should raise error if response is not valid JSON."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(200, text="Invalid JSON{")
        )

        with pytest.raises(Exception):  # Could be JSONDecodeError or custom error
            client.query("SELECT 1", "dev", "cust")


class TestPagination:
    """Test OFFSET-based pagination loop."""

    @respx.mock
    def test_fetches_single_page_under_100_rows(self) -> None:
        """Should fetch single page if result has < 100 rows."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(
                200,
                json={"data": [{"id": str(i)} for i in range(50)]},
            )
        )

        result = client.query("SELECT * FROM table", "dev", "cust")

        assert len(result) == 50
        assert route.call_count == 1
        # First request should have no offset parameter
        assert "offset" not in route.calls[0].request.url.params

    @respx.mock
    def test_fetches_multiple_pages_with_offset(self) -> None:
        """Should fetch multiple pages using OFFSET parameter."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        # Use side_effect to return different responses based on call count
        call_count = [0]

        def response_handler(request):
            call_count[0] += 1
            if call_count[0] == 1:
                # Page 1: 100 rows (triggers pagination)
                return httpx.Response(
                    200,
                    json={"data": [{"id": str(i)} for i in range(100)]},
                )
            elif call_count[0] == 2:
                # Page 2: 100 rows (triggers another page)
                return httpx.Response(
                    200,
                    json={"data": [{"id": str(i)} for i in range(100, 200)]},
                )
            else:
                # Page 3: 50 rows (stops pagination)
                return httpx.Response(
                    200,
                    json={"data": [{"id": str(i)} for i in range(200, 250)]},
                )

        respx.put(url__startswith=f"{base_url}/queries/ShortQuery").mock(
            side_effect=response_handler
        )

        result = client.query("SELECT * FROM large_table", "dev", "cust")

        assert len(result) == 250
        assert result[0] == {"id": "0"}
        assert result[99] == {"id": "99"}
        assert result[199] == {"id": "199"}
        assert result[249] == {"id": "249"}

    @respx.mock
    def test_stops_pagination_on_empty_page(self) -> None:
        """Should stop pagination when receiving empty data array."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        # Use side_effect to return different responses
        respx.put(url__startswith=f"{base_url}/queries/ShortQuery").mock(
            side_effect=[
                httpx.Response(
                    200,
                    json={"data": [{"id": str(i)} for i in range(100)]},
                ),
                httpx.Response(200, json={"data": []}),
            ]
        )

        result = client.query("SELECT * FROM table", "dev", "cust")

        assert len(result) == 100


class TestRetryConditions:
    """Test retry behavior for different error conditions."""

    @respx.mock
    def test_retries_on_500_error(self) -> None:
        """Should retry on 500 Internal Server Error."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        # First call fails with 500, second succeeds
        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            side_effect=[
                httpx.Response(500, text="Internal Server Error"),
                httpx.Response(200, json={"data": [{"result": "success"}]}),
            ]
        )

        result = client.query("SELECT 1", "dev", "cust")

        assert len(result) == 1
        assert result[0] == {"result": "success"}
        assert route.call_count == 2

    @respx.mock
    def test_retries_on_503_service_unavailable(self) -> None:
        """Should retry on 503 Service Unavailable."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            side_effect=[
                httpx.Response(503, text="Service Unavailable"),
                httpx.Response(200, json={"data": []}),
            ]
        )

        result = client.query("SELECT 1", "dev", "cust")

        assert result == []
        assert route.call_count == 2

    @respx.mock
    def test_no_retry_on_401_unauthorized(self) -> None:
        """Should NOT retry on 401 Unauthorized."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(401, text="Unauthorized")
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.query("SELECT 1", "dev", "cust")

        assert exc_info.value.response.status_code == 401
        assert route.call_count == 1  # No retries

    @respx.mock
    def test_no_retry_on_403_forbidden(self) -> None:
        """Should NOT retry on 403 Forbidden."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(403, text="Forbidden")
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.query("SELECT 1", "dev", "cust")

        assert exc_info.value.response.status_code == 403
        assert route.call_count == 1

    @respx.mock
    def test_no_retry_on_400_bad_request(self) -> None:
        """Should NOT retry on 400 Bad Request."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(400, text="Bad Request")
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            client.query("SELECT 1", "dev", "cust")

        assert exc_info.value.response.status_code == 400
        assert route.call_count == 1


class TestHTTPSEnforcement:
    """Test HTTPS URL validation."""

    def test_accepts_https_url(self) -> None:
        """Should accept HTTPS URLs."""
        client = APIClient("https://api.example.com")
        assert client.base_url == "https://api.example.com"

    def test_rejects_http_url(self) -> None:
        """Should reject HTTP URLs (insecure)."""
        with pytest.raises(ValueError, match="HTTPS required"):
            APIClient("http://insecure.example.com")

    def test_rejects_url_without_scheme(self) -> None:
        """Should reject URLs without scheme."""
        with pytest.raises(ValueError):
            APIClient("example.com")


class TestTimeoutConfiguration:
    """Test request timeout settings."""

    @respx.mock
    def test_applies_timeout_to_requests(self) -> None:
        """Should apply 30-second timeout to requests."""
        base_url = "https://api.example.com"
        client = APIClient(base_url)

        route = respx.put(f"{base_url}/queries/ShortQuery").mock(
            return_value=httpx.Response(200, json={"data": []})
        )

        client.query("SELECT 1", "dev", "cust")

        # Verify timeout was set (this checks the client config)
        assert client._client.timeout.read == 30.0
