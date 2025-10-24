"""
Unit tests for retry_with_backoff decorator.

Tests exponential backoff with jitter, retry conditions, and max retries.
"""

import time

import httpx
import pytest

from opendental_query.core.retry import retry_with_backoff


class TestExponentialBackoff:
    """Test exponential backoff timing with jitter."""

    def test_retries_with_exponential_backoff(self) -> None:
        """Should retry with exponentially increasing delays."""
        attempt_times: list[float] = []

        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        def failing_function() -> None:
            attempt_times.append(time.time())
            raise ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            failing_function()

        # Should have made 4 attempts total (initial + 3 retries)
        assert len(attempt_times) == 4

        # Check approximate delays (0.1s, 0.2s, 0.4s with ±25% jitter)
        delays = [attempt_times[i + 1] - attempt_times[i] for i in range(len(attempt_times) - 1)]
        assert 0.075 <= delays[0] <= 0.125  # ~0.1s ±25%
        assert 0.15 <= delays[1] <= 0.25  # ~0.2s ±25%
        assert 0.30 <= delays[2] <= 0.50  # ~0.4s ±25%

    def test_jitter_adds_randomness(self) -> None:
        """Should add ±25% jitter to delay."""
        delays_run1: list[float] = []
        delays_run2: list[float] = []

        @retry_with_backoff(max_retries=2, initial_delay=1.0)
        def failing_function() -> None:
            raise TimeoutError("Timeout")

        # Run 1
        times1: list[float] = []

        def track_times1() -> None:
            times1.append(time.time())
            raise TimeoutError("Timeout")

        decorated1 = retry_with_backoff(max_retries=2, initial_delay=0.1)(track_times1)

        with pytest.raises(TimeoutError):
            decorated1()

        delays_run1 = [times1[i + 1] - times1[i] for i in range(len(times1) - 1)]

        # Run 2
        times2: list[float] = []

        def track_times2() -> None:
            times2.append(time.time())
            raise TimeoutError("Timeout")

        decorated2 = retry_with_backoff(max_retries=2, initial_delay=0.1)(track_times2)

        with pytest.raises(TimeoutError):
            decorated2()

        delays_run2 = [times2[i + 1] - times2[i] for i in range(len(times2) - 1)]

        # Delays should differ due to jitter (very unlikely to be identical)
        # Check at least one delay differs by more than 1ms
        assert any(abs(d1 - d2) > 0.001 for d1, d2 in zip(delays_run1, delays_run2))

    def test_max_delay_cap(self) -> None:
        """Should cap delay at max_delay value."""
        attempt_times: list[float] = []

        @retry_with_backoff(max_retries=10, initial_delay=1.0, max_delay=2.0)
        def failing_function() -> None:
            attempt_times.append(time.time())
            if len(attempt_times) < 5:
                raise ConnectionError("Network error")

        failing_function()  # Should succeed on 5th attempt

        # Check delays are capped at ~2.0s (with jitter)
        delays = [attempt_times[i + 1] - attempt_times[i] for i in range(len(attempt_times) - 1)]

        # Later delays should all be ~2.0s ±25% (not exponentially growing)
        if len(delays) >= 3:
            assert delays[2] <= 2.5  # Max 2.0s + 25% = 2.5s


class TestRetryConditions:
    """Test which exceptions trigger retries."""

    def test_retries_connection_error(self) -> None:
        """Should retry on ConnectionError."""
        attempts = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def flaky_connection() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ConnectionError("Network failure")
            return "success"

        result = flaky_connection()

        assert result == "success"
        assert attempts == 3

    def test_retries_timeout_error(self) -> None:
        """Should retry on TimeoutError."""
        attempts = 0

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def slow_request() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise TimeoutError("Request timed out")
            return "success"

        result = slow_request()

        assert result == "success"
        assert attempts == 2

    def test_retries_5xx_errors(self) -> None:
        """Should retry on HTTP 5xx errors."""
        attempts = 0

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def server_error() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                response = httpx.Response(500, text="Internal Server Error")
                raise httpx.HTTPStatusError(
                    "Server error",
                    request=None,
                    response=response,  # type: ignore
                )
            return "success"

        result = server_error()

        assert result == "success"
        assert attempts == 2

    def test_no_retry_on_401_unauthorized(self) -> None:
        """Should NOT retry on 401 Unauthorized."""
        attempts = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def unauthorized() -> None:
            nonlocal attempts
            attempts += 1
            response = httpx.Response(401, text="Unauthorized")
            raise httpx.HTTPStatusError(
                "Unauthorized",
                request=None,
                response=response,  # type: ignore
            )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            unauthorized()

        assert exc_info.value.response.status_code == 401
        assert attempts == 1  # No retries

    def test_no_retry_on_403_forbidden(self) -> None:
        """Should NOT retry on 403 Forbidden."""
        attempts = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def forbidden() -> None:
            nonlocal attempts
            attempts += 1
            response = httpx.Response(403, text="Forbidden")
            raise httpx.HTTPStatusError(
                "Forbidden",
                request=None,
                response=response,  # type: ignore
            )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            forbidden()

        assert exc_info.value.response.status_code == 403
        assert attempts == 1  # No retries

    def test_no_retry_on_400_bad_request(self) -> None:
        """Should NOT retry on 400 Bad Request."""
        attempts = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def bad_request() -> None:
            nonlocal attempts
            attempts += 1
            response = httpx.Response(400, text="Bad Request")
            raise httpx.HTTPStatusError(
                "Bad Request",
                request=None,
                response=response,  # type: ignore
            )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            bad_request()

        assert exc_info.value.response.status_code == 400
        assert attempts == 1  # No retries

    def test_no_retry_on_404_not_found(self) -> None:
        """Should NOT retry on 404 Not Found."""
        attempts = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def not_found() -> None:
            nonlocal attempts
            attempts += 1
            response = httpx.Response(404, text="Not Found")
            raise httpx.HTTPStatusError(
                "Not Found",
                request=None,
                response=response,  # type: ignore
            )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            not_found()

        assert exc_info.value.response.status_code == 404
        assert attempts == 1  # No retries


class TestMaxRetries:
    """Test max_retries limit."""

    def test_respects_max_retries_limit(self) -> None:
        """Should stop after max_retries attempts."""
        attempts = 0

        @retry_with_backoff(max_retries=5, initial_delay=0.01)
        def always_fails() -> None:
            nonlocal attempts
            attempts += 1
            raise ConnectionError("Persistent failure")

        with pytest.raises(ConnectionError):
            always_fails()

        assert attempts == 6  # Initial + 5 retries

    def test_succeeds_before_max_retries(self) -> None:
        """Should stop retrying once function succeeds."""
        attempts = 0

        @retry_with_backoff(max_retries=10, initial_delay=0.01)
        def eventually_succeeds() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise TimeoutError("Temporary failure")
            return "success"

        result = eventually_succeeds()

        assert result == "success"
        assert attempts == 3  # Stopped after success


class TestDecoratorBehavior:
    """Test decorator preserves function behavior."""

    def test_returns_function_result(self) -> None:
        """Should return decorated function's return value."""

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def get_value() -> int:
            return 42

        result = get_value()

        assert result == 42

    def test_passes_arguments_correctly(self) -> None:
        """Should pass args and kwargs to decorated function."""

        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def add_numbers(a: int, b: int, multiply: int = 1) -> int:
            return (a + b) * multiply

        result = add_numbers(2, 3, multiply=4)

        assert result == 20

    def test_preserves_exceptions_after_max_retries(self) -> None:
        """Should raise original exception after exhausting retries."""

        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def custom_error() -> None:
            raise ValueError("Custom error message")

        with pytest.raises(ValueError, match="Custom error message"):
            custom_error()
