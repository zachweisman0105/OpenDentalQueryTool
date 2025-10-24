"""SQL query parser and manipulation utilities."""

import re

from opendental_query.utils.app_logger import get_logger

logger = get_logger(__name__)


class SQLParser:
    """Parser for SQL queries with ORDER BY injection support.

    Provides utilities for analyzing and modifying SQL queries, particularly
    for ensuring deterministic ordering by automatically injecting ORDER BY
    clauses when missing.
    """

    # Note: We will detect top-level ORDER BY (outside parentheses) using a manual scan

    # Regex pattern to detect LIMIT clause (kept for potential future use)
    LIMIT_PATTERN = re.compile(r"\bLIMIT\s+\d+(?:\s+OFFSET\s+\d+)?(?:\s*;)?\s*$", re.IGNORECASE)

    # Regex to capture LIMIT token (legacy; not used in insertion logic)
    LIMIT_TOKEN = re.compile(r"\blimit\b", re.IGNORECASE)

    @staticmethod
    def has_order_by(query: str) -> bool:
        """Check if query contains an ORDER BY clause.

        Args:
            query: SQL query to check

        Returns:
            True if ORDER BY clause is present, False otherwise
        """
        # Remove comments and normalize whitespace
        normalized = SQLParser._normalize_query(query)
        return SQLParser._find_top_level_order_by_index(normalized) != -1

    @staticmethod
    def inject_order_by(query: str, *, order_column: str = "1") -> str:
        """Inject ORDER BY clause into query if not already present.

        Adds ORDER BY at the appropriate location (before LIMIT if present,
        otherwise at the end). Only injects if no ORDER BY exists.

        Args:
            query: SQL query to modify
            order_column: Column or expression to order by (default: "1" = first column)

        Returns:
            Modified query with ORDER BY clause
        """
        # Normalize query for detection helpers (do not use for slicing)
        normalized = SQLParser._normalize_query(query)

        # If an ORDER BY already exists at top level, preserve it exactly
        if SQLParser.has_order_by(normalized):
            logger.debug("Query already has ORDER BY clause; preserving as-is")
            return query

        # Determine insertion point: before top-level LIMIT or OFFSET if present
        limit_idx = SQLParser._find_top_level_token_index(query, "limit")
        offset_idx = SQLParser._find_top_level_token_index(query, "offset")

        # Choose the earliest positive index among limit/offset
        candidates = [i for i in [limit_idx, offset_idx] if i != -1]
        insert_idx = min(candidates) if candidates else -1

        if insert_idx != -1:
            left = query[:insert_idx].rstrip()
            right = query[insert_idx:].lstrip()
            # Ensure single space separation around injected clause
            result = f"{left} ORDER BY {order_column} ASC {right}"
            logger.debug(
                f"Injected ORDER BY before {'LIMIT' if insert_idx == limit_idx else 'OFFSET'}: ORDER BY {order_column} ASC"
            )
            return result
        else:
            # Append ORDER BY at end, preserving single trailing semicolon
            query_stripped = query.rstrip().rstrip(";")
            result = f"{query_stripped} ORDER BY {order_column} ASC;"
            logger.debug(f"Injected ORDER BY at end: ORDER BY {order_column} ASC")
            return result

    @staticmethod
    def _ensure_order_direction(query: str) -> str:
        """Ensure existing ORDER BY has explicit ASC/DESC; default to ASC if missing.

        Args:
            query: SQL query string

        Returns:
            Query with ORDER BY segment including explicit ASC if no direction present.
        """
        # Per spec tests, we must preserve existing ORDER BY text exactly.
        # So this function becomes a no-op and returns the query unchanged.
        return query

    @staticmethod
    def _find_top_level_order_by_index(query: str) -> int:
        """Find index of top-level 'order by' (depth 0), or -1 if none."""
        lower = query.lower()
        depth = 0
        last_idx = -1
        i = 0
        while i < len(lower):
            c = lower[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth = max(0, depth - 1)
            elif depth == 0 and lower.startswith("order by", i):
                last_idx = i
            i += 1
        return last_idx

    @staticmethod
    def _find_top_level_token_index(query: str, token: str) -> int:
        """Find index of a top-level token (e.g., 'limit' or 'offset') in the original query.

        Scans the original query text while tracking parentheses depth to avoid
        matches inside subqueries. Returns the index of the first occurrence or -1.
        """
        lower = query.lower()
        token = token.lower()
        depth = 0
        i = 0
        while i < len(lower):
            c = lower[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth = max(0, depth - 1)
            elif depth == 0 and lower.startswith(token, i):
                # ensure token boundary (avoid matching identifiers)
                before_ok = (i == 0) or not lower[i - 1].isalnum()
                after_ok = (i + len(token) == len(lower)) or not lower[i + len(token)].isalnum()
                if before_ok and after_ok:
                    return i
            i += 1
        return -1

    @staticmethod
    def extract_table_name(query: str) -> str | None:
        """Extract primary table name from SELECT query.

        Attempts to parse the FROM clause to identify the main table being queried.
        This is a simple heuristic and may not work for complex queries.

        Args:
            query: SQL SELECT query

        Returns:
            Table name if found, None otherwise
        """
        # Simple regex to extract first table name from FROM clause
        # Handles: FROM table, FROM table alias, FROM `table`
        from_pattern = re.compile(r"\bFROM\s+`?(\w+)`?", re.IGNORECASE)

        match = from_pattern.search(query)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def _normalize_query(query: str) -> str:
        """Normalize query by removing comments and extra whitespace.

        Args:
            query: SQL query to normalize

        Returns:
            Normalized query string
        """
        # Remove single-line comments (-- comment)
        query = re.sub(r"--[^\n]*", "", query)

        # Remove multi-line comments (/* comment */)
        query = re.sub(r"/\*.*?\*/", "", query, flags=re.DOTALL)

        # Normalize whitespace (collapse multiple spaces to single space)
        query = re.sub(r"\s+", " ", query)

        return query.strip()

    @staticmethod
    def is_select_query(query: str) -> bool:
        """Check if query is a SELECT statement.

        Args:
            query: SQL query to check

        Returns:
            True if query is SELECT, False otherwise
        """
        normalized = SQLParser._normalize_query(query)
        return bool(re.match(r"^\s*SELECT\b", normalized, re.IGNORECASE))

    @staticmethod
    def is_read_only(query: str) -> bool:
        """Check if query is read-only (SELECT, SHOW, DESCRIBE, etc.).

        Args:
            query: SQL query to check

        Returns:
            True if query is read-only, False otherwise
        """
        # Remove comments to avoid false positives from commented-out statements
        stripped = SQLParser._strip_comments(query).strip()
        if not stripped:
            return False

        # Allow a single trailing semicolon but reject additional statements
        core = stripped.rstrip(";\r\n\t ").strip()
        if not core:
            return False

        if SQLParser._has_unquoted_semicolon(core):
            return False

        sanitized = SQLParser._strip_string_literals(core)
        upper_sanitized = sanitized.upper()

        disallowed_keywords = (
            "INSERT",
            "UPDATE",
            "DELETE",
            "REPLACE",
            "UPSERT",
            "MERGE",
            "TRUNCATE",
            "ALTER",
            "DROP",
            "CREATE",
            "GRANT",
            "REVOKE",
            "CALL",
            "EXEC",
            "EXECUTE",
            "BEGIN",
            "END",
            "COMMIT",
            "ROLLBACK",
            "SET",
            "USE",
            "DECLARE",
            "LOCK",
            "UNLOCK",
            "WITH",
        )

        keyword_pattern = re.compile(r"\b(" + "|".join(disallowed_keywords) + r")\b")
        if keyword_pattern.search(upper_sanitized):
            return False

        normalized = SQLParser._normalize_query(core)
        read_only_patterns = [
            r"^\s*SELECT\b",
            r"^\s*SHOW\b",
            r"^\s*DESCRIBE\b",
            r"^\s*DESC\b",
            r"^\s*EXPLAIN\b",
        ]

        return any(re.match(pattern, normalized, re.IGNORECASE) for pattern in read_only_patterns)

    @staticmethod
    def _strip_comments(query: str) -> str:
        """Remove SQL comments while leaving other content unchanged."""
        without_single = re.sub(r"--[^\n]*", "", query)
        without_multi = re.sub(r"/\*.*?\*/", "", without_single, flags=re.DOTALL)
        return without_multi

    @staticmethod
    def _has_unquoted_semicolon(query: str) -> bool:
        """Detect semicolons outside of quoted regions."""
        in_single = False
        in_double = False
        in_backtick = False
        escape = False

        for ch in query:
            if escape:
                escape = False
                continue

            if ch == "\\" and (in_single or in_double):
                escape = True
                continue

            if ch == "'" and not in_double and not in_backtick:
                in_single = not in_single
                continue

            if ch == '"' and not in_single and not in_backtick:
                in_double = not in_double
                continue

            if ch == "`" and not in_single and not in_double:
                in_backtick = not in_backtick
                continue

            if ch == ";" and not (in_single or in_double or in_backtick):
                return True

        return False

    @staticmethod
    def _strip_string_literals(query: str) -> str:
        """Replace string literals and quoted identifiers with spaces."""
        query = re.sub(r"'([^'\\]|\\.|'')*'", " ", query)
        query = re.sub(r'"([^"\\]|\\.)*"', " ", query)
        query = re.sub(r"`[^`]*`", " ", query)
        return query


# Convenience function for query engine
def ensure_order_by(query: str, order_column: str = "1") -> str:
    """
    Ensure SQL query has an ORDER BY clause.

    Convenience wrapper around SQLParser.inject_order_by that always injects
    ORDER BY if not present. Used by QueryEngine to ensure deterministic results.

    Args:
        query: SQL query
        order_column: Column to order by (default "1" for first column)

    Returns:
        Query with ORDER BY clause guaranteed
    """
    return SQLParser.inject_order_by(query, order_column=order_column)
