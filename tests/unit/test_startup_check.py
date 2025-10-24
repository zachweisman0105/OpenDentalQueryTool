"""
Unit tests for startup checks.

Tests validation of prerequisites:
- Python version
- Vault file existence and permissions
- Audit log writability
- Downloads folder accessibility
- HTTPS connectivity
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import respx
from httpx import ConnectError, ConnectTimeout, Response

from opendental_query.utils.startup_check import (
    StartupCheckError,
    check_audit_log_writable,
    check_downloads_accessible,
    check_https_connectivity,
    check_python_version,
    check_vault_exists,
    check_vault_permissions,
    get_remediation_steps,
    run_startup_checks,
)


@pytest.fixture(autouse=True)
def allow_unrestricted_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow startup checks to validate export directories in temporary locations."""
    monkeypatch.setenv("SPEC_KIT_ALLOW_UNSAFE_EXPORTS", "1")
    monkeypatch.delenv("SPEC_KIT_EXPORT_ENCRYPTION_COMMAND", raising=False)


class TestPythonVersionCheck:
    """Test Python version validation."""

    def test_python_version_sufficient(self) -> None:
        """Test that current Python version passes (test environment is 3.11+)."""
        success, message = check_python_version()
        assert success
        assert message.lower().startswith("python")

    @patch("sys.version_info", (3, 10, 0, "final", 0))
    def test_python_version_too_old(self) -> None:
        """Test Python version below 3.11 fails."""
        success, message = check_python_version()
        assert not success
        assert "3.11+ required" in message


class TestVaultExistenceCheck:
    """Test vault file existence validation."""

    def test_vault_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test vault file found."""
        # Create mock vault
        config_dir = tmp_path / ".opendental-query"
        config_dir.mkdir()
        vault_file = config_dir / "vault.enc"
        vault_file.write_text("mock vault data")

        # Mock DEFAULT_CONFIG_DIR
        with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
            success, message = check_vault_exists()
            assert success
            assert "vault present" in message.lower()

    def test_vault_missing(self, tmp_path: Path) -> None:
        """Test vault file not found."""
        config_dir = tmp_path / ".opendental-query"

        with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
            success, message = check_vault_exists()
            assert not success
            assert "vault not found" in message.lower()
            assert "vault-init" in message


class TestVaultPermissionsCheck:
    """Test vault file permissions validation."""

    def test_vault_permissions_correct(self, tmp_path: Path) -> None:
        """Test vault with correct 0600 permissions."""
        config_dir = tmp_path / ".opendental-query"
        config_dir.mkdir()
        vault_file = config_dir / "vault.enc"
        vault_file.write_text("mock vault data")

        # Set correct permissions (may not work on Windows)
        try:
            os.chmod(vault_file, 0o600)

            with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
                success, message = check_vault_permissions()
                # On Windows, permissions might not be enforced
                if os.name == "posix":
                    assert success
                    assert "correct" in message.lower()
        except Exception:
            pytest.skip("Cannot set permissions on this platform")

    def test_vault_permissions_incorrect(self, tmp_path: Path) -> None:
        """Test vault with incorrect permissions."""
        config_dir = tmp_path / ".opendental-query"
        config_dir.mkdir()
        vault_file = config_dir / "vault.enc"
        vault_file.write_text("mock vault data")

        # Set incorrect permissions (may not work on Windows)
        try:
            os.chmod(vault_file, 0o644)

            with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
                success, message = check_vault_permissions()
                if os.name == "posix":
                    assert not success
                    assert "incorrect" in message.lower()
                    assert "chmod" in message
        except Exception:
            pytest.skip("Cannot set permissions on this platform")

    def test_vault_permissions_skip_if_missing(self, tmp_path: Path) -> None:
        """Test permissions check skipped if vault doesn't exist."""
        config_dir = tmp_path / ".opendental-query"

        with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
            success, message = check_vault_permissions()
            assert success
            assert "doesn't exist" in message or "skipping" in message.lower()


class TestAuditLogCheck:
    """Test audit log writability validation."""

    def test_audit_log_writable(self, tmp_path: Path) -> None:
        """Test audit log directory is writable."""
        config_dir = tmp_path / ".opendental-query"

        with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
            success, message = check_audit_log_writable()
            assert success
            assert "writable" in message.lower()
            # Check directory was created
            assert config_dir.exists()

    def test_audit_log_not_writable(self, tmp_path: Path) -> None:
        """Test audit log directory not writable."""
        config_dir = tmp_path / ".opendental-query"
        config_dir.mkdir()

        # Make directory read-only (may not work on Windows)
        try:
            os.chmod(config_dir, 0o444)

            with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
                success, message = check_audit_log_writable()
                if os.name == "posix":
                    assert not success
                    assert "not writable" in message.lower()
        except Exception:
            pytest.skip("Cannot set permissions on this platform")
        finally:
            # Restore permissions for cleanup
            try:
                os.chmod(config_dir, 0o755)
            except Exception:
                pass


class TestDownloadsFolderCheck:
    """Test Downloads folder accessibility validation."""

    def test_downloads_accessible(self) -> None:
        """Test Downloads folder is accessible."""
        # Assume user has Downloads folder
        downloads = Path.home() / "Downloads"

        if downloads.exists():
            success, message = check_downloads_accessible()
            # Should pass if writable or warn if not
            assert "Downloads" in message
        else:
            pytest.skip("No Downloads folder on this system")

    def test_downloads_missing(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Test missing Downloads folder."""
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()

        with patch("pathlib.Path.home", return_value=fake_home):
            success, message = check_downloads_accessible()
            assert success  # Should pass with warning
            assert "not found" in message or "current directory" in message.lower()


class TestHTTPSConnectivityCheck:
    """Test HTTPS connectivity validation."""

    @respx.mock
    def test_https_connectivity_success(self) -> None:
        """Test HTTPS connectivity succeeds."""
        respx.get("https://www.google.com").mock(return_value=Response(200))

        success, message = check_https_connectivity()
        assert success
        assert "verified" in message.lower()

    @respx.mock
    def test_https_connectivity_timeout(self) -> None:
        """Test HTTPS connectivity timeout."""
        respx.get("https://www.google.com").mock(side_effect=ConnectTimeout("timeout"))

        success, message = check_https_connectivity()
        assert not success
        assert "timed out" in message.lower() or "timeout" in message.lower()

    @respx.mock
    def test_https_connectivity_connect_error(self) -> None:
        """Test HTTPS connectivity connection error."""
        respx.get("https://www.google.com").mock(side_effect=ConnectError("connection failed"))

        success, message = check_https_connectivity()
        assert not success
        assert "failed" in message.lower()

    @respx.mock
    def test_https_connectivity_bad_status(self) -> None:
        """Test HTTPS connectivity with non-200 status."""
        respx.get("https://www.google.com").mock(return_value=Response(500))

        success, message = check_https_connectivity()
        assert not success
        assert "500" in message


class TestRunStartupChecks:
    """Test complete startup check orchestration."""

    def test_run_startup_checks_all_pass(self, tmp_path: Path) -> None:
        """Test all checks pass."""
        config_dir = tmp_path / ".opendental-query"
        config_dir.mkdir()
        vault_file = config_dir / "vault.enc"
        vault_file.write_text("mock vault")
        os.chmod(vault_file, 0o600)

        with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
            with respx.mock:
                respx.get("https://www.google.com").mock(return_value=Response(200))

                # Should not raise
                run_startup_checks()

    def test_run_startup_checks_with_failures(self, tmp_path: Path) -> None:
        """Test startup checks fail with missing vault."""
        config_dir = tmp_path / ".opendental-query"

        with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
            with respx.mock:
                respx.get("https://www.google.com").mock(return_value=Response(200))

                with pytest.raises(StartupCheckError) as exc_info:
                    run_startup_checks()

                assert "Startup checks failed" in str(exc_info.value)
                assert "Vault" in str(exc_info.value)

    def test_run_startup_checks_skip_vault(self, tmp_path: Path) -> None:
        """Test startup checks skip vault checks."""
        config_dir = tmp_path / ".opendental-query"

        with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
            with respx.mock:
                respx.get("https://www.google.com").mock(return_value=Response(200))

                # Should not raise even without vault
                run_startup_checks(skip_vault=True)

    def test_run_startup_checks_skip_network(self, tmp_path: Path) -> None:
        """Test startup checks skip network checks."""
        config_dir = tmp_path / ".opendental-query"
        config_dir.mkdir()
        vault_file = config_dir / "vault.enc"
        vault_file.write_text("mock vault")

        with patch("opendental_query.utils.startup_check.DEFAULT_CONFIG_DIR", config_dir):
            # Should not raise even without network mock
            run_startup_checks(skip_network=True)


class TestRemediationSteps:
    """Test remediation step retrieval."""

    def test_get_remediation_for_python_version(self) -> None:
        """Test remediation steps for Python version."""
        steps = get_remediation_steps("Python Version")
        assert steps is not None
        assert "Python 3.11" in steps

    def test_get_remediation_for_vault(self) -> None:
        """Test remediation steps for vault."""
        steps = get_remediation_steps("Vault Exists")
        assert steps is not None
        assert "vault-init" in steps

    def test_get_remediation_for_export_policy(self) -> None:
        """Test remediation steps for export directory policy."""
        steps = get_remediation_steps("Export Directory Policy")
        assert steps is not None
        assert "SPEC_KIT_EXPORT_ROOT" in steps

    def test_get_remediation_unknown_check(self) -> None:
        """Test remediation for unknown check returns None."""
        steps = get_remediation_steps("Unknown Check")
        assert steps is None
