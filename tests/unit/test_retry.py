"""
Unit tests for retry_with_backoff decorator.

Tests exponential backoff with jitter, retry conditions, and max retries.
"""

import random
import time

import httpx
import pytest

from opendental_query.core.retry import retry_with_backoff


@pytest.fixture(autouse=True)
def _disable_real_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid actual sleeping to keep tests fast and deterministic."""
    monkeypatch.setattr(time, "sleep", lambda *_args, **_kwargs: None)

class TestExponentialBackoff:
    """Test exponential backoff timing with jitter."""

    def test_retries_with_exponential_backoff(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should retry with exponentially increasing delays."""
        recorded: list[tuple[float, float]] = []

        def _fake_sleep(delay: float, jitter: float) -> None:
            jitter_amount = delay * jitter
            actual_delay = delay + random.uniform(-jitter_amount, jitter_amount)
            recorded.append((delay, actual_delay))

        monkeypatch.setattr("opendental_query.core.retry._sleep_with_jitter", _fake_sleep)

        attempts = 0

        @retry_with_backoff(max_retries=3, initial_delay=0.1)
        def failing_function() -> None:
            nonlocal attempts
            attempts += 1
            raise ConnectionError("Network error")

        with pytest.raises(ConnectionError):
            failing_function()

        assert attempts == 4
        base_delays = [delay for delay, _ in recorded]
        assert base_delays == [pytest.approx(0.1), pytest.approx(0.2), pytest.approx(0.4)]
        for base, actual in recorded:
            lower = base * 0.75
            upper = base * 1.25
            assert lower <= actual <= upper

    def test_jitter_adds_randomness(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should add ±25% jitter to delay."""
        jitter_values = iter([1.0, -1.0, 0.5, -0.5])

        def _fake_uniform(a: float, b: float) -> float:
            factor = next(jitter_values)
            return factor * abs(b)

        monkeypatch.setattr("opendental_query.core.retry.random.uniform", _fake_uniform)

        recorded: list[float] = []

        def _capture_sleep(duration: float) -> None:
            recorded.append(duration)

        monkeypatch.setattr(time, "sleep", _capture_sleep)

        @retry_with_backoff(max_retries=2, initial_delay=0.1)
        def always_timeout() -> None:
            raise TimeoutError("Timeout")

        with pytest.raises(TimeoutError):
            always_timeout()

        with pytest.raises(TimeoutError):
            always_timeout()

        expected = [0.125, 0.15, 0.1125, 0.175]
        assert len(recorded) == len(expected)
        for actual, expected_value in zip(recorded, expected, strict=True):
            assert actual == pytest.approx(expected_value, rel=1e-6)
        first_run = recorded[:2]
        second_run = recorded[2:]
        assert first_run != second_run

    def test_max_delay_cap(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Should cap delay at max_delay value."""
        recorded: list[float] = []

        def _fake_sleep(delay: float, jitter: float) -> None:
            jitter_amount = delay * jitter
            actual_delay = delay + random.uniform(-jitter_amount, jitter_amount)
            recorded.append(actual_delay)

        monkeypatch.setattr("opendental_query.core.retry._sleep_with_jitter", _fake_sleep)

        attempts = 0

        @retry_with_backoff(max_retries=10, initial_delay=1.0, max_delay=2.0)
        def failing_function() -> None:
            nonlocal attempts
            attempts += 1
            if attempts < 5:
                raise ConnectionError("Network error")

        failing_function()  # Should succeed on 5th attempt

        assert attempts == 5
        assert recorded[-1] <= 2.5  # 2.0s + 25% jitter cap


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
