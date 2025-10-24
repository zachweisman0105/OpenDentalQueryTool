"""CLI command for checking software updates via GitHub Releases."""

from __future__ import annotations

import json
from dataclasses import dataclass

import click
import httpx
from packaging.version import Version
from packaging.version import parse as parse_version

from opendental_query import __version__
from opendental_query.constants import (
    EXIT_SUCCESS,
    EXIT_UPDATE_AVAILABLE,
    EXIT_UPDATE_NETWORK_ERROR,
)
from opendental_query.utils.audit_logger import AuditLogger

GITHUB_API = "https://api.github.com"
DEFAULT_OWNER = "github"
DEFAULT_REPO = "spec-kit"


@dataclass(frozen=True)
class ReleaseInfo:
    tag_name: str
    body: str

    @property
    def version(self) -> Version:
        # Strip leading 'v' if present
        return parse_version(self.tag_name.lstrip("v"))


def fetch_latest_release(owner: str, repo: str, timeout: float = 5.0) -> ReleaseInfo:
    url = f"{GITHUB_API}/repos/{owner}/{repo}/releases/latest"
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, headers={"Accept": "application/vnd.github+json"})
        resp.raise_for_status()
        data = resp.json()
        return ReleaseInfo(tag_name=data.get("tag_name", "0.0.0"), body=data.get("body", ""))


@click.command(name="check-update")
@click.option("--owner", default=DEFAULT_OWNER, show_default=True, help="GitHub repo owner")
@click.option("--repo", default=DEFAULT_REPO, show_default=True, help="GitHub repository name")
@click.option("--timeout", default=5.0, show_default=True, help="HTTP timeout in seconds")
@click.option("--auto-install", is_flag=True, help="Attempt auto-install (not yet implemented)")
@click.pass_context
def check_update(
    ctx: click.Context, owner: str, repo: str, timeout: float, auto_install: bool
) -> int:
    """Check for a newer released version and report status.

    Exit codes:
      - 0  up-to-date
      - 20 update available
      - 21 network/API error
    """
    audit = AuditLogger()
    current = parse_version(__version__)

    try:
        release = fetch_latest_release(owner, repo, timeout)
        latest = release.version
        available = latest > current

        # Audit event
        audit.log(
            "UPDATE_CHECKED",
            success=True,
            details={
                "current_version": str(current),
                "latest_version": str(latest),
                "update_available": available,
                "owner": owner,
                "repo": repo,
            },
        )

        if available:
            click.echo(
                json.dumps(
                    {
                        "status": "update-available",
                        "current": str(current),
                        "latest": str(latest),
                    }
                )
            )
            ctx.exit(EXIT_UPDATE_AVAILABLE)

        click.echo(
            json.dumps({"status": "up-to-date", "current": str(current), "latest": str(latest)})
        )
        ctx.exit(EXIT_SUCCESS)

    except httpx.HTTPError as e:
        audit.log(
            "UPDATE_CHECKED",
            success=False,
            error=str(e),
            details={"current_version": str(current), "owner": owner, "repo": repo},
        )
        click.echo(json.dumps({"status": "error", "error": str(e)}))
        ctx.exit(EXIT_UPDATE_NETWORK_ERROR)

    finally:
        if auto_install:
            click.echo("Auto-install not yet implemented, please update manually.")
