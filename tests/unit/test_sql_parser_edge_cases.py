"""
Unit tests for SQL parser ORDER BY injection edge cases.

Tests edge cases including LIMIT/OFFSET clauses, trailing semicolons,
whitespace variations, and preservation of user-specified ORDER BY.
"""

from opendental_query.utils.sql_parser import SQLParser, ensure_order_by


class TestOrderByInjectionEdgeCases:
    """Test ORDER BY injection with various edge cases."""

    def test_order_by_with_limit_clause(self) -> None:
        """Test ORDER BY injection before LIMIT clause."""
        sql = "SELECT * FROM patient LIMIT 10"
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result
        assert result.index("ORDER BY") < result.index("LIMIT")
        assert "LIMIT 10" in result

    def test_order_by_with_offset_clause(self) -> None:
        """Test ORDER BY injection before OFFSET clause."""
        sql = "SELECT * FROM patient OFFSET 100"
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result
        assert result.index("ORDER BY") < result.index("OFFSET")
        assert "OFFSET 100" in result

    def test_order_by_with_limit_and_offset(self) -> None:
        """Test ORDER BY injection before LIMIT OFFSET clause."""
        sql = "SELECT * FROM patient LIMIT 50 OFFSET 100"
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result
        assert result.index("ORDER BY") < result.index("LIMIT")
        assert "LIMIT 50 OFFSET 100" in result

    def test_order_by_with_trailing_semicolon(self) -> None:
        """Test ORDER BY injection with trailing semicolon."""
        sql = "SELECT * FROM patient;"
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result
        # Semicolon should be at the end
        assert result.strip().endswith(";")

    def test_order_by_with_trailing_whitespace(self) -> None:
        """Test ORDER BY injection with trailing whitespace."""
        sql = "SELECT * FROM patient   \n\t  "
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result

    def test_order_by_with_leading_whitespace(self) -> None:
        """Test ORDER BY injection with leading whitespace."""
        sql = "  \n\t  SELECT * FROM patient"
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result

    def test_order_by_with_multiline_query(self) -> None:
        """Test ORDER BY injection with multiline query."""
        sql = """
        SELECT 
            PatNum, 
            LName, 
            FName
        FROM 
            patient
        WHERE 
            Birthdate > '2000-01-01'
        """
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result

    def test_order_by_with_semicolon_and_limit(self) -> None:
        """Test ORDER BY injection with both semicolon and LIMIT."""
        sql = "SELECT * FROM patient LIMIT 10;"
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result
        assert result.index("ORDER BY") < result.index("LIMIT")
        assert result.strip().endswith(";")

    def test_order_by_case_insensitive_limit(self) -> None:
        """Test ORDER BY injection with case-insensitive LIMIT."""
        sql = "SELECT * FROM patient limit 10"
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result
        assert result.index("ORDER BY") < result.lower().index("limit")


class TestOrderByPreservation:
    """Test that user-specified ORDER BY clauses are preserved."""

    def test_preserves_existing_order_by(self) -> None:
        """Test that existing ORDER BY is not modified."""
        sql = "SELECT * FROM patient ORDER BY LName"
        result = ensure_order_by(sql)
        # Should return original SQL unchanged
        assert result == sql
        assert result.count("ORDER BY") == 1

    def test_preserves_order_by_with_asc(self) -> None:
        """Test that existing ORDER BY with ASC is preserved."""
        sql = "SELECT * FROM patient ORDER BY LName ASC"
        result = ensure_order_by(sql)
        assert result == sql
        assert "ORDER BY LName ASC" in result

    def test_preserves_order_by_with_desc(self) -> None:
        """Test that existing ORDER BY with DESC is preserved."""
        sql = "SELECT * FROM patient ORDER BY LName DESC"
        result = ensure_order_by(sql)
        assert result == sql
        assert "ORDER BY LName DESC" in result

    def test_preserves_order_by_multiple_columns(self) -> None:
        """Test that ORDER BY with multiple columns is preserved."""
        sql = "SELECT * FROM patient ORDER BY LName, FName"
        result = ensure_order_by(sql)
        assert result == sql
        assert "ORDER BY LName, FName" in result

    def test_preserves_order_by_with_limit(self) -> None:
        """Test that ORDER BY with LIMIT is preserved."""
        sql = "SELECT * FROM patient ORDER BY LName LIMIT 10"
        result = ensure_order_by(sql)
        assert result == sql
        assert "ORDER BY LName" in result
        assert "LIMIT 10" in result

    def test_preserves_order_by_case_insensitive(self) -> None:
        """Test that ORDER BY detection is case-insensitive."""
        sql = "SELECT * FROM patient order by LName"
        result = ensure_order_by(sql)
        assert result == sql

    def test_preserves_order_by_with_whitespace(self) -> None:
        """Test that ORDER BY with various whitespace is preserved."""
        sql = "SELECT * FROM patient   ORDER   BY   LName"
        result = ensure_order_by(sql)
        # Should preserve the original (no modification)
        assert result == sql

    def test_preserves_order_by_with_table_prefix(self) -> None:
        """Test that ORDER BY with table.column is preserved."""
        sql = "SELECT * FROM patient ORDER BY patient.LName"
        result = ensure_order_by(sql)
        assert result == sql
        assert "ORDER BY patient.LName" in result


class TestComplexQueries:
    """Test ORDER BY injection with complex SQL patterns."""

    def test_subquery_order_by_not_affected(self) -> None:
        """Test that subquery ORDER BY is not modified."""
        sql = "SELECT * FROM (SELECT * FROM patient ORDER BY LName) AS sub"
        result = ensure_order_by(sql)
        # Main query should get ORDER BY, subquery unchanged
        assert "ORDER BY 1 ASC" in result
        # Original subquery ORDER BY should still be there
        assert "ORDER BY LName" in result

    def test_union_queries_get_order_by(self) -> None:
        """Test ORDER BY injection with UNION queries."""
        sql = "SELECT * FROM patient UNION SELECT * FROM provider"
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result

    def test_cte_query_gets_order_by(self) -> None:
        """Test ORDER BY injection with CTE (WITH clause)."""
        sql = """
        WITH cte AS (
            SELECT * FROM patient
        )
        SELECT * FROM cte
        """
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result

    def test_case_expression_doesnt_confuse_parser(self) -> None:
        """Test that CASE expressions don't confuse ORDER BY detection."""
        sql = """
        SELECT 
            CASE 
                WHEN Birthdate > '2000-01-01' THEN 'Young'
                ELSE 'Old'
            END as AgeGroup
        FROM patient
        """
        result = ensure_order_by(sql)
        assert "ORDER BY 1 ASC" in result


class TestSQLParserClass:
    """Test SQLParser class methods directly."""

    def test_inject_order_by_method(self) -> None:
        """Test inject_order_by class method."""
        parser = SQLParser()
        result = parser.inject_order_by("SELECT * FROM patient")
        assert "ORDER BY 1 ASC" in result

    def test_has_order_by_method_positive(self) -> None:
        """Test has_order_by method with ORDER BY present."""
        parser = SQLParser()
        assert parser.has_order_by("SELECT * FROM patient ORDER BY LName")

    def test_has_order_by_method_negative(self) -> None:
        """Test has_order_by method with no ORDER BY."""
        parser = SQLParser()
        assert not parser.has_order_by("SELECT * FROM patient")

    def test_ensure_order_by_function(self) -> None:
        """Test convenience function wraps parser."""
        result = ensure_order_by("SELECT * FROM patient")
        assert "ORDER BY 1 ASC" in result
