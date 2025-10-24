import json

import httpx
import respx
from click.testing import CliRunner

from opendental_query import __version__ as CURRENT_VERSION
from opendental_query.cli.update_cmd import check_update, fetch_latest_release
from opendental_query.constants import (
    EXIT_SUCCESS,
    EXIT_UPDATE_AVAILABLE,
    EXIT_UPDATE_NETWORK_ERROR,
)


def test_fetch_latest_release_parses_version():
    with respx.mock(base_url="https://api.github.com") as mock:
        route = mock.get("/repos/owner/repo/releases/latest").mock(
            return_value=httpx.Response(200, json={"tag_name": "v9.9.9", "body": "Notes"})
        )
        info = fetch_latest_release("owner", "repo", timeout=0.1)
        assert str(info.version) == "9.9.9"
        assert info.body == "Notes"
        assert route.called


def test_check_update_up_to_date(monkeypatch):
    runner = CliRunner()

    with respx.mock(base_url="https://api.github.com") as mock:
        # Latest is equal to current
        mock.get("/repos/github/spec-kit/releases/latest").mock(
            return_value=httpx.Response(200, json={"tag_name": f"v{CURRENT_VERSION}", "body": ""})
        )
        result = runner.invoke(check_update, [])
        assert result.exit_code == EXIT_SUCCESS
        data = json.loads(result.output.strip())
        assert data["status"] == "up-to-date"
        assert data["current"] == CURRENT_VERSION


def test_check_update_available():
    runner = CliRunner()

    with respx.mock(base_url="https://api.github.com") as mock:
        # Latest is higher than current
        mock.get("/repos/github/spec-kit/releases/latest").mock(
            return_value=httpx.Response(200, json={"tag_name": "v999.0.0", "body": ""})
        )
        result = runner.invoke(check_update, [])
        assert result.exit_code == EXIT_UPDATE_AVAILABLE
        data = json.loads(result.output.strip())
        assert data["status"] == "update-available"


def test_check_update_network_error():
    runner = CliRunner()

    with respx.mock(base_url="https://api.github.com") as mock:
        mock.get("/repos/github/spec-kit/releases/latest").mock(
            return_value=httpx.Response(500, json={"message": "error"})
        )
        result = runner.invoke(check_update, [])
        assert result.exit_code == EXIT_UPDATE_NETWORK_ERROR
        data = json.loads(result.output.strip())
        assert data["status"] == "error"
