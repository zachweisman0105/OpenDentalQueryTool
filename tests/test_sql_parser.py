"""Unit tests for SQL parser utilities."""

from opendental_query.utils.sql_parser import SQLParser


class TestHasOrderBy:
    """Tests for has_order_by method."""

    def test_simple_order_by(self) -> None:
        """Test detection of simple ORDER BY clause."""
        query = "SELECT * FROM patient ORDER BY PatNum"
        assert SQLParser.has_order_by(query)

    def test_order_by_with_direction(self) -> None:
        """Test detection of ORDER BY with ASC/DESC."""
        query = "SELECT * FROM patient ORDER BY PatNum DESC"
        assert SQLParser.has_order_by(query)

    def test_order_by_multiple_columns(self) -> None:
        """Test detection of ORDER BY with multiple columns."""
        query = "SELECT * FROM patient ORDER BY LName, FName ASC"
        assert SQLParser.has_order_by(query)

    def test_no_order_by(self) -> None:
        """Test detection when ORDER BY is missing."""
        query = "SELECT * FROM patient WHERE PatNum > 100"
        assert not SQLParser.has_order_by(query)

    def test_order_by_case_insensitive(self) -> None:
        """Test case-insensitive ORDER BY detection."""
        query = "SELECT * FROM patient order by PatNum"
        assert SQLParser.has_order_by(query)

    def test_order_by_with_limit(self) -> None:
        """Test detection of ORDER BY before LIMIT."""
        query = "SELECT * FROM patient ORDER BY PatNum LIMIT 10"
        assert SQLParser.has_order_by(query)


class TestInjectOrderBy:
    """Tests for inject_order_by method."""

    def test_inject_at_end(self) -> None:
        """Test injecting ORDER BY at query end."""
        query = "SELECT * FROM patient"
        result = SQLParser.inject_order_by(query)

        assert "ORDER BY 1" in result
        assert result.endswith(";")

    def test_inject_before_limit(self) -> None:
        """Test injecting ORDER BY before LIMIT clause."""
        query = "SELECT * FROM patient LIMIT 10"
        result = SQLParser.inject_order_by(query)
        # Accept explicit ASC and ensure ORDER BY comes before LIMIT
        assert "ORDER BY 1" in result
        assert result.lower().index("order by") < result.lower().index("limit")

    def test_inject_before_limit_offset(self) -> None:
        """Test injecting ORDER BY before LIMIT with OFFSET."""
        query = "SELECT * FROM patient LIMIT 10 OFFSET 5"
        result = SQLParser.inject_order_by(query)
        # Accept explicit ASC and ensure ORDER BY comes before LIMIT and OFFSET
        assert "ORDER BY 1" in result
        s = result.lower()
        assert s.index("order by") < s.index("limit") < s.index("offset")

    def test_no_inject_when_exists(self) -> None:
        """Test that ORDER BY is not injected if already present."""
        query = "SELECT * FROM patient ORDER BY PatNum"
        result = SQLParser.inject_order_by(query)

        # Should return original query unchanged
        assert result == query

    def test_custom_order_column(self) -> None:
        """Test injecting custom ORDER BY column."""
        query = "SELECT PatNum, LName FROM patient"
        result = SQLParser.inject_order_by(query, order_column="PatNum")

        assert "ORDER BY PatNum" in result

    def test_inject_with_trailing_semicolon(self) -> None:
        """Test handling queries with trailing semicolons."""
        query = "SELECT * FROM patient;"
        result = SQLParser.inject_order_by(query)

        assert "ORDER BY 1" in result
        assert result.count(";") == 1  # Should only have one semicolon


class TestExtractTableName:
    """Tests for extract_table_name method."""

    def test_simple_from(self) -> None:
        """Test extracting table name from simple FROM clause."""
        query = "SELECT * FROM patient"
        assert SQLParser.extract_table_name(query) == "patient"

    def test_from_with_alias(self) -> None:
        """Test extracting table name with alias."""
        query = "SELECT * FROM patient p"
        assert SQLParser.extract_table_name(query) == "patient"

    def test_from_with_backticks(self) -> None:
        """Test extracting table name with backticks."""
        query = "SELECT * FROM `patient`"
        assert SQLParser.extract_table_name(query) == "patient"

    def test_from_case_insensitive(self) -> None:
        """Test case-insensitive FROM detection."""
        query = "select * from patient"
        assert SQLParser.extract_table_name(query) == "patient"

    def test_no_from_clause(self) -> None:
        """Test handling queries without FROM clause."""
        query = "SELECT 1"
        assert SQLParser.extract_table_name(query) is None


class TestIsSelectQuery:
    """Tests for is_select_query method."""

    def test_simple_select(self) -> None:
        """Test detection of simple SELECT query."""
        query = "SELECT * FROM patient"
        assert SQLParser.is_select_query(query)

    def test_select_case_insensitive(self) -> None:
        """Test case-insensitive SELECT detection."""
        query = "select * from patient"
        assert SQLParser.is_select_query(query)

    def test_insert_not_select(self) -> None:
        """Test that INSERT is not detected as SELECT."""
        query = "INSERT INTO patient (LName) VALUES ('Smith')"
        assert not SQLParser.is_select_query(query)

    def test_update_not_select(self) -> None:
        """Test that UPDATE is not detected as SELECT."""
        query = "UPDATE patient SET LName='Smith' WHERE PatNum=1"
        assert not SQLParser.is_select_query(query)


class TestIsReadOnly:
    """Tests for is_read_only method."""

    def test_select_is_readonly(self) -> None:
        """Test that SELECT is read-only."""
        query = "SELECT * FROM patient"
        assert SQLParser.is_read_only(query)

    def test_show_is_readonly(self) -> None:
        """Test that SHOW is read-only."""
        query = "SHOW TABLES"
        assert SQLParser.is_read_only(query)

    def test_describe_is_readonly(self) -> None:
        """Test that DESCRIBE is read-only."""
        query = "DESCRIBE patient"
        assert SQLParser.is_read_only(query)

    def test_desc_is_readonly(self) -> None:
        """Test that DESC is read-only."""
        query = "DESC patient"
        assert SQLParser.is_read_only(query)

    def test_explain_is_readonly(self) -> None:
        """Test that EXPLAIN is read-only."""
        query = "EXPLAIN SELECT * FROM patient"
        assert SQLParser.is_read_only(query)

    def test_insert_not_readonly(self) -> None:
        """Test that INSERT is not read-only."""
        query = "INSERT INTO patient (LName) VALUES ('Smith')"
        assert not SQLParser.is_read_only(query)

    def test_update_not_readonly(self) -> None:
        """Test that UPDATE is not read-only."""
        query = "UPDATE patient SET LName='Smith'"
        assert not SQLParser.is_read_only(query)

    def test_delete_not_readonly(self) -> None:
        """Test that DELETE is not read-only."""
        query = "DELETE FROM patient WHERE PatNum=1"
        assert not SQLParser.is_read_only(query)

    def test_trailing_semicolon_allowed(self) -> None:
        """Test that trailing semicolon does not invalidate read-only query."""
        query = "SELECT * FROM patient;"
        assert SQLParser.is_read_only(query)

    def test_multi_statement_rejected(self) -> None:
        """Test that multi-statement queries are rejected."""
        query = "SELECT * FROM patient; DELETE FROM patient"
        assert not SQLParser.is_read_only(query)

    def test_cte_rejected(self) -> None:
        """Test that CTE-based queries are rejected."""
        query = "WITH cte AS (SELECT 1) SELECT * FROM cte"
        assert not SQLParser.is_read_only(query)

    def test_keyword_inside_string_literal_allowed(self) -> None:
        """Test that destructive keywords inside string literals do not trip validation."""
        query = "SELECT 'DELETE FROM patient' AS sample_text"
        assert SQLParser.is_read_only(query)


class TestNormalizeQuery:
    """Tests for _normalize_query private method."""

    def test_remove_single_line_comments(self) -> None:
        """Test removal of single-line comments."""
        query = "SELECT * FROM patient -- This is a comment"
        normalized = SQLParser._normalize_query(query)

        assert "--" not in normalized
        assert "comment" not in normalized

    def test_remove_multiline_comments(self) -> None:
        """Test removal of multi-line comments."""
        query = "SELECT * /* comment here */ FROM patient"
        normalized = SQLParser._normalize_query(query)

        assert "/*" not in normalized
        assert "comment" not in normalized

    def test_normalize_whitespace(self) -> None:
        """Test collapsing multiple spaces."""
        query = "SELECT  *    FROM   patient"
        normalized = SQLParser._normalize_query(query)

        assert "  " not in normalized
        assert normalized == "SELECT * FROM patient"
