"""Unit tests for query command office selection validation.

Tests that invalid office IDs are rejected with clear error messages.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from opendental_query.cli.query_cmd import query_command



class TestOfficeSelectionValidation:
    """Test office selection validation in query command."""

    def test_invalid_office_id_rejected(self, tmp_path: Path) -> None:
        """Test that invalid office IDs are rejected with clear error."""
        runner = CliRunner()

        # Mock vault with 3 offices
        with patch("opendental_query.cli.query_cmd.VaultManager") as mock_vault_cls:
            mock_vault = MagicMock()
            mock_vault_cls.return_value = mock_vault
            mock_vault.is_unlocked.return_value = True

            # Mock vault data with 3 offices
            mock_vault_data = MagicMock()
            mock_vault_data.offices = {
                "office1": MagicMock(customer_key="key1"),
                "office2": MagicMock(customer_key="key2"),
                "office3": MagicMock(customer_key="key3"),
            }
            mock_vault.get_vault.return_value = mock_vault_data

            with patch("opendental_query.cli.query_cmd.ConfigManager") as mock_config_cls:
                mock_config = MagicMock()
                mock_config_cls.return_value = MagicMock(load=lambda: mock_config)
                mock_config.api_developer_key = "dev_key"
                mock_config.api_base_url = "https://api.test.com"

                # Attempt query with invalid office
                result = runner.invoke(
                    query_command,
                    [
                        "--sql",
                        "SELECT 1",
                        "--offices",
                        "office1,invalid_office",
                    ],
                    catch_exceptions=False,
                )

                assert result.exit_code == 1
                assert "Invalid office IDs" in result.output or "invalid" in result.output.lower()
                assert "invalid_office" in result.output

    def test_non_read_only_sql_is_rejected(self, tmp_path: Path) -> None:
        """Ensure mutating SQL statements are rejected before execution."""
        runner = CliRunner()

        with (
            patch("opendental_query.cli.query_cmd.VaultManager") as mock_vault_cls,
            patch("opendental_query.cli.query_cmd.ConfigManager") as mock_config_cls,
            patch("opendental_query.cli.query_cmd.QueryEngine") as mock_engine_cls,
        ):
            mock_vault = MagicMock()
            mock_vault_cls.return_value = mock_vault
            mock_vault.is_unlocked.return_value = True

            mock_vault_data = MagicMock()
            mock_vault_data.offices = {"office1": MagicMock(customer_key="key1")}
            mock_vault.get_vault.return_value = mock_vault_data

            mock_config = MagicMock()
            mock_config_cls.return_value = MagicMock(load=lambda: mock_config)
            mock_config.api_base_url = "https://api.test.com"
            mock_config.vault_path = tmp_path / "vault.enc"

            result = runner.invoke(
                query_command,
                [
                    "--sql",
                    "UPDATE patient SET LName='Smith'",
                    "--offices",
                    "office1",

                ],
                catch_exceptions=False,
            )

            assert result.exit_code == 2
            assert "read-only" in result.output.lower()
            mock_engine_cls.assert_not_called()

    def test_multiple_invalid_offices_listed(self, tmp_path: Path) -> None:
        """Test that multiple invalid office IDs are all listed in error."""
        runner = CliRunner()

        with patch("opendental_query.cli.query_cmd.VaultManager") as mock_vault_cls:
            mock_vault = MagicMock()
            mock_vault_cls.return_value = mock_vault
            mock_vault.is_unlocked.return_value = True

            mock_vault_data = MagicMock()
            mock_vault_data.offices = {
                "office1": MagicMock(customer_key="key1"),
                "office2": MagicMock(customer_key="key2"),
            }
            mock_vault.get_vault.return_value = mock_vault_data

            with patch("opendental_query.cli.query_cmd.ConfigManager") as mock_config_cls:
                mock_config = MagicMock()
                mock_config_cls.return_value = MagicMock(load=lambda: mock_config)

                result = runner.invoke(
                    query_command,
                    [
                        "--sql",
                        "SELECT 1",
                        "--offices",
                        "badoffice1,office1,badoffice2",
                    ],
                    catch_exceptions=False,
                )

                assert result.exit_code == 1
                # Should list both invalid offices
                assert "badoffice1" in result.output and "badoffice2" in result.output

    def test_valid_office_ids_accepted(self, tmp_path: Path) -> None:
        """Test that valid office IDs are accepted."""
        runner = CliRunner()

        with patch("opendental_query.cli.query_cmd.VaultManager") as mock_vault_cls:
            mock_vault = MagicMock()
            mock_vault_cls.return_value = mock_vault
            mock_vault.is_unlocked.return_value = True

            mock_vault_data = MagicMock()
            mock_vault_data.offices = {
                "office1": MagicMock(customer_key="key1"),
                "office2": MagicMock(customer_key="key2"),
                "office3": MagicMock(customer_key="key3"),
            }
            mock_vault.get_vault.return_value = mock_vault_data

            with patch("opendental_query.cli.query_cmd.ConfigManager") as mock_config_cls:
                mock_config = MagicMock()
                mock_config_cls.return_value = MagicMock(load=lambda: mock_config)
                mock_config.api_base_url = "https://api.test.com"
                mock_config.api_developer_key = "dev_key"

                with patch("opendental_query.cli.query_cmd.QueryEngine") as mock_engine_cls:
                    mock_engine = MagicMock()
                    mock_engine_cls.return_value = mock_engine

                    # Mock successful query execution
                    mock_result = MagicMock()
                    mock_result.total_offices = 2
                    mock_result.successful_count = 2
                    mock_result.failed_count = 0
                    mock_result.all_rows = []
                    mock_engine.execute.return_value = mock_result

                    with patch("opendental_query.cli.query_cmd.ProgressIndicator"):
                        result = runner.invoke(
                            query_command,
                            [
                                "--sql",
                                "SELECT 1",
                                "--offices",
                                "office1,office2",

                            ],
                            catch_exceptions=False,
                        )

                        # Should succeed (exit 0)
                        assert result.exit_code == 0

    def test_all_keyword_selects_all_offices(self, tmp_path: Path) -> None:
        """Test that 'ALL' keyword selects all configured offices."""
        runner = CliRunner()

        with patch("opendental_query.cli.query_cmd.VaultManager") as mock_vault_cls:
            mock_vault = MagicMock()
            mock_vault_cls.return_value = mock_vault
            mock_vault.is_unlocked.return_value = True

            mock_vault_data = MagicMock()
            mock_vault_data.offices = {
                "office1": MagicMock(customer_key="key1"),
                "office2": MagicMock(customer_key="key2"),
                "office3": MagicMock(customer_key="key3"),
            }
            mock_vault.get_vault.return_value = mock_vault_data

            with patch("opendental_query.cli.query_cmd.ConfigManager") as mock_config_cls:
                mock_config = MagicMock()
                mock_config_cls.return_value = MagicMock(load=lambda: mock_config)
                mock_config.api_base_url = "https://api.test.com"
                mock_config.api_developer_key = "dev_key"

                with patch("opendental_query.cli.query_cmd.QueryEngine") as mock_engine_cls:
                    mock_engine = MagicMock()
                    mock_engine_cls.return_value = mock_engine

                    mock_result = MagicMock()
                    mock_result.total_offices = 3
                    mock_result.successful_count = 3
                    mock_result.failed_count = 0
                    mock_result.all_rows = []
                    mock_engine.execute.return_value = mock_result

                    with patch("opendental_query.cli.query_cmd.ProgressIndicator"):
                        result = runner.invoke(
                            query_command,
                            [
                                "--sql",
                                "SELECT 1",
                                "--offices",
                                "ALL",

                            ],
                            catch_exceptions=False,
                        )

                        # Should execute query for all 3 offices
                        assert result.exit_code == 0
                        assert "3 office" in result.output

    def test_empty_office_selection_rejected(self, tmp_path: Path) -> None:
        """Test that empty office selection is rejected."""
        runner = CliRunner()

        with patch("opendental_query.cli.query_cmd.VaultManager") as mock_vault_cls:
            mock_vault = MagicMock()
            mock_vault_cls.return_value = mock_vault
            mock_vault.is_unlocked.return_value = True

            mock_vault_data = MagicMock()
            mock_vault_data.offices = {
                "office1": MagicMock(customer_key="key1"),
            }
            mock_vault.get_vault.return_value = mock_vault_data

            with patch("opendental_query.cli.query_cmd.ConfigManager") as mock_config_cls:
                mock_config = MagicMock()
                mock_config_cls.return_value = MagicMock(load=lambda: mock_config)

                result = runner.invoke(
                    query_command,
                    [
                        "--sql",
                        "SELECT 1",
                        "--offices",
                        "  , ,  ",  # Empty after splitting/stripping
                    ],
                    catch_exceptions=False,
                )

                assert result.exit_code == 1
                assert (
                    "No offices selected" in result.output or "no office" in result.output.lower()
                )


class TestInteractiveInput:
    """Interactive query entry behaviour."""

    def test_sql_submission_requires_single_blank_terminator(self, tmp_path: Path) -> None:
        """User should finish SQL input with one blank line before office selection."""
        runner = CliRunner()

        with (
            patch("opendental_query.cli.query_cmd.VaultManager") as mock_vault_cls,
            patch("opendental_query.cli.query_cmd.ConfigManager") as mock_config_cls,
            patch("opendental_query.cli.query_cmd.QueryEngine") as mock_engine_cls,
            patch("opendental_query.cli.query_cmd.ProgressIndicator"),
            patch("opendental_query.cli.query_cmd.CSVExporter"),
            patch("opendental_query.cli.query_cmd.TableRenderer"),
            patch("opendental_query.cli.query_cmd.AuditLogger") as mock_audit_logger_cls,
        ):
            mock_vault = MagicMock()
            mock_vault_cls.return_value = mock_vault
            mock_vault.is_unlocked.return_value = True

            mock_vault_data = MagicMock()
            mock_vault_data.offices = {"office1": MagicMock(customer_key="key1")}
            mock_vault_data.developer_key = "dev_key"
            mock_vault.get_vault.return_value = mock_vault_data

            mock_config = MagicMock()
            mock_config.api_base_url = "https://api.test.com"
            mock_config.api_developer_key = "dev_key"
            mock_config.vault_path = tmp_path
            mock_config_cls.return_value = MagicMock(load=lambda: mock_config)

            mock_engine = MagicMock()
            mock_engine_cls.return_value = mock_engine

            mock_result = MagicMock()
            mock_result.total_offices = 1
            mock_result.successful_count = 1
            mock_result.failed_count = 0
            mock_result.all_rows = []
            mock_result.office_results = []
            mock_engine.execute.return_value = mock_result

            mock_audit_logger = MagicMock()
            mock_audit_logger_cls.return_value = mock_audit_logger

            # SQL followed by single blank line, then office selection "ALL", trailing blank for "Run another query?" prompt
            user_input = "SELECT 1;\n\nALL\n\n"
            result = runner.invoke(
                query_command,
                [],
                input=user_input,
                catch_exceptions=False,
            )

            assert result.exit_code == 0

    def test_user_prompt_can_opt_into_export(self, tmp_path: Path) -> None:
        """Interactive runs should prompt for export and respect confirmation."""
        runner = CliRunner()

        with (
            patch("opendental_query.cli.query_cmd.VaultManager") as mock_vault_cls,
            patch("opendental_query.cli.query_cmd.ConfigManager") as mock_config_cls,
            patch("opendental_query.cli.query_cmd.QueryEngine") as mock_engine_cls,
            patch("opendental_query.cli.query_cmd.ProgressIndicator"),
            patch("opendental_query.cli.query_cmd.CSVExporter") as mock_exporter_cls,
            patch("opendental_query.cli.query_cmd.TableRenderer"),
            patch("opendental_query.cli.query_cmd.AuditLogger") as mock_audit_logger_cls,
        ):
            mock_vault = MagicMock()
            mock_vault_cls.return_value = mock_vault
            mock_vault.is_unlocked.return_value = True

            mock_vault_data = MagicMock()
            mock_vault_data.offices = {"office1": MagicMock(customer_key="key1")}
            mock_vault_data.developer_key = "dev_key"
            mock_vault.get_vault.return_value = mock_vault_data

            mock_config = MagicMock()
            mock_config.api_base_url = "https://api.test.com"
            mock_config.vault_path = tmp_path
            mock_config_cls.return_value = MagicMock(load=lambda: mock_config)

            mock_engine = MagicMock()
            mock_engine_cls.return_value = mock_engine

            mock_result = MagicMock()
            mock_result.total_offices = 1
            mock_result.successful_count = 1
            mock_result.failed_count = 0
            mock_result.all_rows = [{"Office": "office1", "count": 1}]
            mock_result.office_results = []
            mock_engine.execute.return_value = mock_result

            mock_exporter = MagicMock()
            mock_exporter.export.return_value = tmp_path / "export.csv"
            mock_exporter_cls.return_value = mock_exporter

            mock_audit_logger = MagicMock()
            mock_audit_logger_cls.return_value = mock_audit_logger

            user_input = "SELECT 1;\n\nALL\ny\nn\n"
            result = runner.invoke(
                query_command,
                [],
                input=user_input,
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            mock_exporter.export.assert_called_once()
            assert "HIPAA Reminder" in result.output

    def test_export_flag_skips_prompt(self, tmp_path: Path) -> None:
        """--export flag should trigger export without interactive confirmation."""
        runner = CliRunner()

        with (
            patch("opendental_query.cli.query_cmd.VaultManager") as mock_vault_cls,
            patch("opendental_query.cli.query_cmd.ConfigManager") as mock_config_cls,
            patch("opendental_query.cli.query_cmd.QueryEngine") as mock_engine_cls,
            patch("opendental_query.cli.query_cmd.ProgressIndicator"),
            patch("opendental_query.cli.query_cmd.CSVExporter") as mock_exporter_cls,
            patch("opendental_query.cli.query_cmd.TableRenderer"),
            patch("opendental_query.cli.query_cmd.AuditLogger") as mock_audit_logger_cls,
        ):
            mock_vault = MagicMock()
            mock_vault_cls.return_value = mock_vault
            mock_vault.is_unlocked.return_value = True

            mock_vault_data = MagicMock()
            mock_vault_data.offices = {"office1": MagicMock(customer_key="key1")}
            mock_vault_data.developer_key = "dev_key"
            mock_vault.get_vault.return_value = mock_vault_data

            mock_config = MagicMock()
            mock_config.api_base_url = "https://api.test.com"
            mock_config.vault_path = tmp_path
            mock_config_cls.return_value = MagicMock(load=lambda: mock_config)

            mock_engine = MagicMock()
            mock_engine_cls.return_value = mock_engine

            mock_result = MagicMock()
            mock_result.total_offices = 1
            mock_result.successful_count = 1
            mock_result.failed_count = 0
            mock_result.all_rows = [{"Office": "office1", "count": 1}]
            mock_result.office_results = []
            mock_engine.execute.return_value = mock_result

            mock_exporter = MagicMock()
            mock_exporter.export.return_value = tmp_path / "export.csv"
            mock_exporter_cls.return_value = mock_exporter

            mock_audit_logger = MagicMock()
            mock_audit_logger_cls.return_value = mock_audit_logger

            result = runner.invoke(
                query_command,
                [
                    "--sql",
                    "SELECT 1",
                    "--offices",
                    "office1",
                    "--export",
                ],
                catch_exceptions=False,
            )

            assert result.exit_code == 0
            mock_exporter.export.assert_called_once()
            assert "Export results to CSV?" not in result.output
            assert "HIPAA Reminder" in result.output
