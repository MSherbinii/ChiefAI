"""
Tests for pure scoring logic in scoring/momentum.py.
_clamp is a stateless utility — no mocking needed.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('SUPABASE_URL', 'http://localhost')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'test-key')

from scoring.momentum import _clamp


def test_clamp_normal():
    assert _clamp(75.5) == 75


def test_clamp_below_min():
    assert _clamp(-10) == 0


def test_clamp_above_max():
    assert _clamp(150) == 100
