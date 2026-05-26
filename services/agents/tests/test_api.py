"""
Integration tests for FastAPI endpoints.
All Supabase and Anthropic calls are mocked.
"""
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Set dummy env vars before any imports that read them at module level
os.environ.setdefault('SUPABASE_URL', 'http://localhost')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'test-key')
os.environ.setdefault('ANTHROPIC_API_KEY', 'test-anthropic-key')

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope='module')
def client():
    """Create a TestClient with all external dependencies mocked at import time."""
    mock_sb = MagicMock()
    mock_anthropic_cls = MagicMock()

    with patch('supabase.create_client', return_value=mock_sb), \
         patch('anthropic.Anthropic', return_value=mock_anthropic_cls):
        from main import app
        return TestClient(app)


def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'


def test_chat_endpoint_routes_to_agent(client):
    mock_response = MagicMock()
    mock_response.reply = 'Your recovery score is 72%.'
    mock_response.agent = 'Pulse'
    mock_response.confidence = None

    with patch('main.route_and_handle', new=AsyncMock(return_value=mock_response)):
        response = client.post('/chat', json={
            'message': 'how did I sleep?',
            'history': [],
        })

    assert response.status_code == 200
    data = response.json()
    assert 'reply' in data
    assert 'agent' in data


def test_sync_google_returns_started(client):
    # sync_gmail is fire-and-forget via asyncio.create_task — just check the immediate response
    with patch('main.sync_gmail', new=AsyncMock(return_value=None)):
        response = client.post('/sync/google', json={'user_id': 'test-uuid'})

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'sync_started'


def test_momentum_endpoint_calls_calculator(client):
    mock_result = {
        'total': 68,
        'body': 72,
        'money': 50,
        'work': 65,
        'admin': 80,
        'discipline': 67,
        'reasons': {
            'body': 'recovery 72%',
            'work': '5 commits this week',
            'admin': '0 items pending approval',
        },
        'scored_at': '2026-05-26T08:00:00+00:00',
    }

    with patch('main.calculate_momentum', new=AsyncMock(return_value=mock_result)):
        response = client.post('/score/momentum', json={'user_id': 'test-uuid'})

    assert response.status_code == 200
    data = response.json()
    assert 'total' in data


def test_brief_generate_endpoint(client):
    mock_result = {
        'greeting': 'Good morning, Test.',
        'sections': [],
        'life_debt': {'total': 0, 'items': []},
        'best_move': 'Rest today.',
        'patterns': [],
    }

    with patch('main.generate_morning_brief', new=AsyncMock(return_value=mock_result)):
        response = client.post('/brief/generate', json={
            'user_id': 'test-uuid',
            'user_name': 'Test',
        })

    assert response.status_code == 200
    data = response.json()
    assert 'greeting' in data
