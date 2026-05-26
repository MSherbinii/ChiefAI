# services/agents/db.py
"""
Database helpers for safe Supabase queries.
"""
from postgrest.exceptions import APIError


def safe_single(query):
    """Execute a .maybe_single() query, returning None on empty result instead of raising."""
    try:
        result = query.execute()
        return result
    except APIError as e:
        # postgrest-py raises APIError with code '204' when maybe_single() finds no rows
        if getattr(e, 'code', None) == '204' or '204' in str(e):
            # Return a mock result object with data=None
            class EmptyResult:
                data = None
            return EmptyResult()
        raise  # re-raise unexpected errors
