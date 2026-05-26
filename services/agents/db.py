# services/agents/db.py
"""
Database helpers for safe Supabase queries.
"""
from postgrest.exceptions import APIError


def safe_single(query):
    """Execute a .maybe_single() query, returning an EmptyResult on no-row result instead of raising."""
    class EmptyResult:
        data = None

    try:
        result = query.execute()
        # Supabase maybe_single() returns None directly when no rows found
        if result is None:
            return EmptyResult()
        return result
    except APIError as e:
        # postgrest-py raises APIError with code '204' when maybe_single() finds no rows
        if getattr(e, 'code', None) == '204' or '204' in str(e):
            return EmptyResult()
        raise  # re-raise unexpected errors
