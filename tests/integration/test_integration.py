"""
Integration tests for end-to-end query execution workflow.

Tests the complete flow: config → vault → query → render → export
"""

from pathlib import Path

import openpyxl
import pytest
import respx
from httpx import Response

from opendental_query.core.query_engine import QueryEngine
from opendental_query.core.vault import VaultManager
from opendental_query.renderers.excel_exporter import ExcelExporter


@pytest.fixture(autouse=True)
def allow_unrestricted_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow tests to write exports outside hardened directories."""
    monkeypatch.setenv("SPEC_KIT_ALLOW_UNSAFE_EXPORTS", "1")
    monkeypatch.delenv("SPEC_KIT_EXPORT_ENCRYPTION_COMMAND", raising=False)


@pytest.fixture
def temp_config_dir(tmp_path: Path) -> Path:
    """Create temporary config directory."""
    config_dir = tmp_path / ".opendental-query"
    config_dir.mkdir(parents=True)
    return config_dir


@pytest.fixture
def configured_vault(temp_config_dir: Path) -> tuple[VaultManager, str]:
    """Create and initialize a vault with test data."""
    vault_file = temp_config_dir / "test.vault"
    vault_manager = VaultManager(vault_path=vault_file)
    password = "Test@Password123!"

    # Initialize vault (automatically unlocks)
    vault_manager.init(password=password, developer_key="test_dev_key")

    # Add offices (vault is already unlocked after init)
    vault_manager.add_office("office1", "cust_key_1")
    vault_manager.add_office("office2", "cust_key_2")

    return vault_manager, password


class TestEndToEndQueryFlow:
    """Test complete query execution workflow."""

    @respx.mock
    def test_complete_query_workflow(
        self,
        temp_config_dir: Path,
        configured_vault: tuple[VaultManager, str],
    ) -> None:
        """Test end-to-end query execution with all components."""
        vault_manager, password = configured_vault

        # Mock API responses
        base_url = "https://api.example.com"

        # Mock responses for each office - first request has no offset
        respx.put(f"{base_url}/queries/ShortQuery").mock(
            side_effect=[
                Response(200, json={"data": [{"PatNum": "1", "LName": "Smith"}]}),
                Response(200, json={"data": [{"PatNum": "2", "LName": "Jones"}]}),
            ]
        )

        # Execute query
        engine = QueryEngine(max_concurrent=2)

        office_credentials = {
            "office1": ("test_dev_key", "cust_key_1"),
            "office2": ("test_dev_key", "cust_key_2"),
        }

        result = engine.execute(
            sql="SELECT PatNum, LName FROM patient LIMIT 1",
            office_credentials=office_credentials,
            api_base_url=base_url,
            timeout_seconds=30,
        )

        # Verify results
        assert result.total_offices == 2
        assert result.successful_count == 2
        assert result.failed_count == 0
        assert len(result.all_rows) == 2

        # Verify Office column is injected
        assert "Office" in result.all_rows[0]
        assert result.all_rows[0]["Office"] in ["office1", "office2"]

        # Test Excel export
        export_dir = temp_config_dir / "exports"
        exporter = ExcelExporter()
        workbook_path = exporter.export(result.all_rows, output_dir=export_dir)

        # Verify workbook was created
        assert workbook_path.exists()
        assert workbook_path.suffix == ".xlsx"
        assert "opendental_query_" in workbook_path.name

        # Verify workbook content
        workbook = openpyxl.load_workbook(workbook_path)
        sheet = workbook.active
        values = list(sheet.iter_rows(values_only=True))
        assert values[0][:3] == ("Office", "PatNum", "LName")
        assert values[1][0] in {"office1", "office2"}
        row1 = (str(values[1][1]), values[1][2])
        row2 = (str(values[2][1]), values[2][2])
        assert {row1, row2} == {('1', 'Smith'), ('2', 'Jones')}

    @respx.mock
    def test_handles_mixed_success_and_failure(
        self,
        temp_config_dir: Path,
        configured_vault: tuple[VaultManager, str],
    ) -> None:
        """Test workflow with some offices succeeding and some failing."""
        vault_manager, password = configured_vault

        # Mock API responses - one success, one failure
        base_url = "https://api.example.com"

        respx.put(f"{base_url}/queries/ShortQuery").mock(
            side_effect=[
                Response(200, json={"data": [{"PatNum": "1", "LName": "Smith"}]}),
                Response(500, text="Internal Server Error"),
            ]
        )

        # Execute query
        engine = QueryEngine(max_concurrent=2)

        office_credentials = {
            "office1": ("test_dev_key", "cust_key_1"),
            "office2": ("test_dev_key", "cust_key_2"),
        }

        result = engine.execute(
            sql="SELECT PatNum, LName FROM patient LIMIT 1",
            office_credentials=office_credentials,
            api_base_url=base_url,
            timeout_seconds=30,
        )

        # Verify partial results
        assert result.total_offices == 2
        assert result.successful_count == 1
        assert result.failed_count == 1
        assert len(result.all_rows) == 1  # Only successful office

        # Verify Excel export still works with partial results
        export_dir = temp_config_dir / "exports"
        exporter = ExcelExporter()
        workbook_path = exporter.export(result.all_rows, output_dir=export_dir)
        assert workbook_path.exists()


class TestVaultIntegration:
    """Test vault integration scenarios."""

    def test_vault_lifecycle(self, temp_config_dir: Path) -> None:
        """Test complete vault lifecycle: create → add office → lock → unlock → query."""
        vault_file = temp_config_dir / "lifecycle.vault"
        vault_manager = VaultManager(vault_path=vault_file)
        password = "Test@Password123!"

        # Create vault
        vault_manager.init(password=password, developer_key="dev_key_123")
        assert vault_file.exists()

        # Add office (vault is already unlocked after init)
        vault_manager.add_office("MainOffice", "cust_key_main")

        # Lock vault
        vault_manager.lock()
        assert not vault_manager.is_unlocked()

        # Unlock vault
        result = vault_manager.unlock(password)
        assert result is True
        assert vault_manager.is_unlocked()

        # Retrieve credentials
        offices = vault_manager.list_offices()
        assert "MainOffice" in offices
        creds = vault_manager.get_office_credential("MainOffice")
        assert creds.office_id == "MainOffice"
        assert vault_manager.get_developer_key() == "dev_key_123"

    def test_vault_security_lockout(self, temp_config_dir: Path) -> None:
        """Test vault security features: failed attempts and lockout."""
        vault_file = temp_config_dir / "security.vault"
        vault_manager = VaultManager(vault_path=vault_file)
        correct_password = "Test@Password123!"
        wrong_password = "WrongPassword123!"

        # Create vault
        vault_manager.init(password=correct_password, developer_key="dev_key")
        vault_manager.lock()

        # Try wrong password 3 times
        for _ in range(3):
            result = vault_manager.unlock(wrong_password)
            assert result is False

        # Vault should be locked out
        with pytest.raises(ValueError, match="locked"):
            vault_manager.unlock(correct_password)
