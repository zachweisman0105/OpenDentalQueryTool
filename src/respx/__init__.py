"""Minimal respx-compatible HTTP mocking used for test suite.

This lightweight shim implements the subset of the `respx` API that the test
suite relies on: context/decorator based mocking, route registration helpers
(`get`, `post`, `put`), call tracking, and side effects.  It avoids any network
access by intercepting `httpx.Client.send` and returning pre-configured
responses.
"""

from __future__ import annotations

from contextlib import ContextDecorator
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Iterator, Optional

import httpx

__all__ = ["mock", "get", "post", "put", "delete", "calls"]


class _CallList:
    """Wrapper over call records that provides list semantics and ``last``."""

    def __init__(self, records: list[SimpleNamespace]) -> None:
        self._records = records

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self):
        return iter(self._records)

    def __getitem__(self, index: int) -> SimpleNamespace:
        return self._records[index]

    @property
    def last(self) -> SimpleNamespace:
        if not self._records:
            raise IndexError("No calls have been recorded")
        return self._records[-1]


class Route:
    """Represents a mocked HTTP route."""

    def __init__(
        self,
        router: "MockRouter",
        method: str,
        url: Optional[str] = None,
        *,
        url_startswith: Optional[str] = None,
    ) -> None:
        self._router = router
        self.method = method.upper()
        self._url = url
        self._url_startswith = url_startswith
        self._return_value: httpx.Response | None = None
        self._side_effect_callable: Callable[[httpx.Request], httpx.Response] | None = None
        self._side_effect_iter: Optional[Iterator[httpx.Response]] = None
        self._side_effect_exception: Optional[BaseException] = None
        self._calls: list[SimpleNamespace] = []

    def mock(
        self,
        *,
        return_value: Optional[httpx.Response] = None,
        side_effect: Optional[Callable[[httpx.Request], httpx.Response]] = None,
    ) -> "Route":
        self._return_value = return_value
        self._side_effect_callable = None
        self._side_effect_iter = None
        self._side_effect_exception = None
        if side_effect is not None:
            if callable(side_effect):
                self._side_effect_callable = side_effect  # type: ignore[assignment]
            elif isinstance(side_effect, Iterable):
                self._side_effect_iter = iter(side_effect)
            elif isinstance(side_effect, BaseException):
                self._side_effect_exception = side_effect
            else:
                raise TypeError("Unsupported side_effect type provided to respx route")
        return self

    def matches(self, method: str, url: str) -> bool:
        if self.method != method.upper():
            return False
        if self._url is not None:
            return url == self._url
        if self._url_startswith is not None:
            return url.startswith(self._url_startswith)
        return False

    def _dispatch(self, request: httpx.Request) -> httpx.Response:
        if self._side_effect_exception is not None:
            raise self._side_effect_exception
        if self._side_effect_callable is not None:
            response = self._side_effect_callable(request)
        elif self._side_effect_iter is not None:
            try:
                response = next(self._side_effect_iter)
            except StopIteration as exc:  # pragma: no cover - defensive
                raise RuntimeError("respx side_effect iterator exhausted") from exc
        elif self._return_value is not None:
            response = self._return_value
        else:
            raise RuntimeError(
                f"No response configured for route {self.method} {self._url or self._url_startswith}"
            )

        if not isinstance(response, httpx.Response):
            raise TypeError("Route handler must return an httpx.Response instance")

        # Ensure response is associated with the originating request
        response.request = request

        call = SimpleNamespace(request=request, response=response)
        self._calls.append(call)
        self._router._record_call(call)
        return response

    @property
    def called(self) -> bool:
        return bool(self._calls)

    @property
    def call_count(self) -> int:
        return len(self._calls)

    @property
    def calls(self) -> _CallList:
        return _CallList(self._calls)


_original_client_send = httpx.Client.send
_original_async_client_send = getattr(httpx.AsyncClient, "send", None)
_router_stack: list["MockRouter"] = []
_global_calls: list[SimpleNamespace] = []


def _install_patches() -> None:
    httpx.Client.send = _mock_send  # type: ignore[assignment]
    if _original_async_client_send is not None:
        httpx.AsyncClient.send = _mock_async_send  # type: ignore[assignment]


def _remove_patches() -> None:
    httpx.Client.send = _original_client_send  # type: ignore[assignment]
    if _original_async_client_send is not None:
        httpx.AsyncClient.send = _original_async_client_send  # type: ignore[assignment]


def _active_router() -> "MockRouter":
    if not _router_stack:
        raise RuntimeError("respx mock is not active")
    return _router_stack[-1]


def _find_route(method: str, url: str) -> Optional[Route]:
    for router in reversed(_router_stack):
        route = router._find_route(method, url)
        if route is not None:
            return route
    return None


def _mock_send(self: httpx.Client, request: httpx.Request, *args: Any, **kwargs: Any) -> httpx.Response:
    route = _find_route(request.method, str(request.url))
    if route is None:
        raise AssertionError(f"No respx route registered for {request.method} {request.url}")
    return route._dispatch(request)


async def _mock_async_send(
    self: httpx.AsyncClient, request: httpx.Request, *args: Any, **kwargs: Any
) -> httpx.Response:
    route = _find_route(request.method, str(request.url))
    if route is None:
        raise AssertionError(f"No respx route registered for {request.method} {request.url}")
    return route._dispatch(request)


class MockRouter(ContextDecorator):
    """Router managing a set of mocked HTTP routes."""

    def __init__(self, *, base_url: Optional[str] = None) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self._routes: list[Route] = []
        self._calls: list[SimpleNamespace] = []

    # Context management -------------------------------------------------
    def __enter__(self) -> "MockRouter":
        if not _router_stack:
            _global_calls.clear()
            _install_patches()
        _router_stack.append(self)
        self._routes.clear()
        self._calls.clear()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if _router_stack and _router_stack[-1] is self:
            _router_stack.pop()
        else:
            try:
                _router_stack.remove(self)
            except ValueError:
                pass
        if not _router_stack:
            _remove_patches()
        return False

    # Route registration helpers ----------------------------------------
    def _add_route(
        self,
        method: str,
        url: Optional[str] = None,
        *,
        url__startswith: Optional[str] = None,
    ) -> Route:
        resolved_url, resolved_prefix = self._resolve_targets(url, url__startswith)
        route = Route(self, method, resolved_url, url_startswith=resolved_prefix)
        self._routes.append(route)
        return route

    def _resolve_targets(
        self,
        url: Optional[str],
        url_prefix: Optional[str],
    ) -> tuple[Optional[str], Optional[str]]:
        full_url = url
        prefix = url_prefix

        if self.base_url:
            if full_url and full_url.startswith("/"):
                full_url = f"{self.base_url}{full_url}"
            if prefix and prefix.startswith("/"):
                prefix = f"{self.base_url}{prefix}"
        return full_url, prefix

    def _find_route(self, method: str, url: str) -> Optional[Route]:
        for route in self._routes:
            if route.matches(method, url):
                return route
        return None

    def _record_call(self, call: SimpleNamespace) -> None:
        self._calls.append(call)
        _global_calls.append(call)

    # Public helpers -----------------------------------------------------
    def get(self, url: Optional[str] = None, **lookups: Any) -> Route:
        return self._add_route("GET", url, **lookups)

    def post(self, url: Optional[str] = None, **lookups: Any) -> Route:
        return self._add_route("POST", url, **lookups)

    def put(self, url: Optional[str] = None, **lookups: Any) -> Route:
        return self._add_route("PUT", url, **lookups)

    def delete(self, url: Optional[str] = None, **lookups: Any) -> Route:
        return self._add_route("DELETE", url, **lookups)

    @property
    def calls(self) -> _CallList:
        return _CallList(self._calls)


class Mocker(ContextDecorator):
    """Facade matching the public ``respx.mock`` API."""

    def __init__(self) -> None:
        self._default_router = MockRouter()

    def __enter__(self) -> MockRouter:
        return self._default_router.__enter__()

    def __exit__(self, exc_type, exc, tb) -> bool:
        return self._default_router.__exit__(exc_type, exc, tb)

    def __call__(self, obj: Optional[Callable[..., Any]] = None, **kwargs: Any):
        if callable(obj) and not kwargs:
            return super().__call__(obj)
        return MockRouter(**kwargs)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._default_router, item)


mock = Mocker()


def _route_helper(method: str, url: Optional[str], lookups: dict[str, Any]) -> Route:
    router = _active_router()
    return router._add_route(method, url, **lookups)


def get(url: Optional[str] = None, **lookups: Any) -> Route:
    return _route_helper("GET", url, lookups)


def post(url: Optional[str] = None, **lookups: Any) -> Route:
    return _route_helper("POST", url, lookups)


def put(url: Optional[str] = None, **lookups: Any) -> Route:
    return _route_helper("PUT", url, lookups)


def delete(url: Optional[str] = None, **lookups: Any) -> Route:
    return _route_helper("DELETE", url, lookups)


calls = _CallList(_global_calls)
