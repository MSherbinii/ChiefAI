import os
import sys
import pytest
from unittest.mock import MagicMock

# Set env vars BEFORE any app imports
os.environ.setdefault('SUPABASE_URL', 'https://test.supabase.co')
os.environ.setdefault(
    'SUPABASE_SERVICE_ROLE_KEY',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'
    '.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjk5OTk5OTk5OTl9'
    '.test-signature-not-real',
)
os.environ.setdefault(
    'NEXT_PUBLIC_SUPABASE_ANON_KEY',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'
    '.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoiYW5vbiIsImlhdCI6MTYwMDAwMDAwMCwiZXhwIjo5OTk5OTk5OTk5fQ'
    '.test-signature-not-real',
)
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'AKIATEST123456789012')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'test-secret-key-not-real-for-testing-only')
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-central-1')
os.environ.setdefault('ANTHROPIC_API_KEY', 'sk-ant-test-key-not-real')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_mock_sb():
    mock_sb = MagicMock()
    chain = MagicMock()
    chain.select.return_value = chain
    chain.insert.return_value = chain
    chain.update.return_value = chain
    chain.upsert.return_value = chain
    chain.delete.return_value = chain
    for method in [
        'eq', 'neq', 'gte', 'lte', 'lt', 'gt', 'ilike', 'is_',
        'not_', 'in_', 'order', 'limit', 'maybe_single', 'single',
    ]:
        setattr(chain, method, MagicMock(return_value=chain))
    chain.execute.return_value = MagicMock(data=None, count=0)
    mock_sb.table.return_value = chain
    mock_sb.rpc.return_value = chain
    return mock_sb


@pytest.fixture(autouse=True)
def mock_supabase(monkeypatch):
    """Patch supabase.create_client globally for all tests so no JWT validation occurs."""
    mock_sb = _make_mock_sb()
    monkeypatch.setattr('supabase.create_client', lambda *a, **kw: mock_sb)
    return mock_sb
