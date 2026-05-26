"""
Tests for pure helper functions in connectors/gmail.py.
No network calls, no Supabase — pure string parsing logic.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Patch env vars before importing the module so create_client isn't called at import time
os.environ.setdefault('SUPABASE_URL', 'http://localhost')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'test-key')

from connectors.gmail import _extract_email_name


def test_extract_email_name_with_display_name():
    name, email = _extract_email_name('John Doe <john@example.com>')
    assert name == 'John Doe'
    assert email == 'john@example.com'


def test_extract_email_name_bare_email():
    name, email = _extract_email_name('john@example.com')
    assert name == 'John'
    assert email == 'john@example.com'


def test_extract_email_name_quoted_name():
    name, email = _extract_email_name('"Prof. Smith" <smith@uni.de>')
    assert name == 'Prof. Smith'
    assert email == 'smith@uni.de'


def test_extract_email_name_dotted_username():
    name, email = _extract_email_name('first.last@uni.de')
    assert name == 'First Last'
    assert email == 'first.last@uni.de'
