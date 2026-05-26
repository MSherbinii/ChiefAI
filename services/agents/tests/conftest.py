import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_supabase(monkeypatch):
    """Mock Supabase create_client to prevent real DB calls."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.gte.return_value.order.return_value.limit.return_value.maybe_single.return_value.execute.return_value.data = None
    mock_sb.table.return_value.insert.return_value.execute.return_value = MagicMock()
    monkeypatch.setattr('supabase.create_client', lambda *a, **kw: mock_sb)
    return mock_sb
