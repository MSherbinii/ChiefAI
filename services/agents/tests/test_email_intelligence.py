# services/agents/tests/test_email_intelligence.py
"""
Tests for the Email Intelligence Engine v2.
All tests mock Supabase and Gmail API — no real network calls.
"""
import os, sys
os.environ.setdefault('SUPABASE_URL', 'https://test.supabase.co')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjk5OTk5OTk5OTl9.test')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'AKIATEST123456789012')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'test-secret-not-real')
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-central-1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


class TestDeepScannerHelpers:
    """Test _parse_message and helper functions."""

    def test_parse_message_basic(self):
        from email_intelligence.deep_scanner import _parse_message
        msg = {
            'id': 'msg123',
            'threadId': 'thread456',
            'snippet': 'Hello world',
            'labelIds': ['INBOX', 'UNREAD'],
            'internalDate': '1716768000000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'Test User <test@example.com>'},
                    {'name': 'To', 'value': 'me@gmail.com'},
                    {'name': 'Subject', 'value': 'Test Email'},
                    {'name': 'Date', 'value': 'Mon, 27 May 2024 10:00:00 +0000'},
                ],
                'mimeType': 'text/plain',
                'body': {'data': ''},
                'parts': []
            }
        }
        result = _parse_message(msg, 'user-123')
        assert result is not None
        assert result['gmail_id'] == 'msg123'
        assert result['from_email'] == 'test@example.com'
        assert result['from_name'] == 'Test User'
        assert result['subject'] == 'Test Email'
        assert result['is_sent'] is False
        assert result['is_read'] is False
        assert result['processed'] is False

    def test_parse_message_sent(self):
        from email_intelligence.deep_scanner import _parse_message
        msg = {
            'id': 'msg456',
            'threadId': 'thread789',
            'snippet': 'My sent message',
            'labelIds': ['SENT'],
            'internalDate': '1716768000000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'me@gmail.com'},
                    {'name': 'To', 'value': 'other@example.com'},
                    {'name': 'Subject', 'value': 'Re: Something'},
                    {'name': 'Date', 'value': 'Mon, 27 May 2024 10:00:00 +0000'},
                ],
                'mimeType': 'text/plain',
                'body': {'data': ''},
                'parts': []
            }
        }
        result = _parse_message(msg, 'user-123')
        assert result is not None
        assert result['is_sent'] is True
        assert result['is_read'] is True

    def test_parse_message_bare_email(self):
        from email_intelligence.deep_scanner import _parse_message
        msg = {
            'id': 'msg789',
            'threadId': 'thread111',
            'snippet': '',
            'labelIds': ['INBOX'],
            'internalDate': '1716768000000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'noreply@company.de'},
                    {'name': 'To', 'value': 'me@gmail.com'},
                    {'name': 'Subject', 'value': 'Your order'},
                    {'name': 'Date', 'value': 'Mon, 27 May 2024 10:00:00 +0000'},
                ],
                'mimeType': 'text/plain',
                'body': {'data': ''},
                'parts': []
            }
        }
        result = _parse_message(msg, 'user-123')
        assert result is not None
        assert result['from_email'] == 'noreply@company.de'

    def test_parse_message_thread_id(self):
        from email_intelligence.deep_scanner import _parse_message
        msg = {
            'id': 'abc',
            'threadId': 'thread_xyz',
            'snippet': 'test',
            'labelIds': ['INBOX'],
            'internalDate': '1716768000000',
            'payload': {
                'headers': [
                    {'name': 'From', 'value': 'a@b.com'},
                    {'name': 'Subject', 'value': 'S'},
                    {'name': 'Date', 'value': 'Mon, 27 May 2024 10:00:00 +0000'},
                ],
                'body': {'data': ''},
                'parts': []
            }
        }
        result = _parse_message(msg, 'user-123')
        assert result['thread_id'] == 'thread_xyz'
        assert result['user_id'] == 'user-123'


class TestEntityClustererHelpers:
    """Test domain extraction and personal email detection."""

    def test_extract_domain_standard(self):
        from email_intelligence.entity_clusterer import _extract_domain
        assert _extract_domain('user@gmail.com') == 'gmail.com'

    def test_extract_domain_german_bank(self):
        from email_intelligence.entity_clusterer import _extract_domain
        assert _extract_domain('noreply@deutsche-bank.de') == 'deutsche-bank.de'

    def test_extract_domain_property_site(self):
        from email_intelligence.entity_clusterer import _extract_domain
        assert _extract_domain('test@immoscout24.de') == 'immoscout24.de'

    def test_is_personal_email_gmail(self):
        from email_intelligence.entity_clusterer import _is_personal_email
        assert _is_personal_email('gmail.com') is True

    def test_is_personal_email_yahoo_de(self):
        from email_intelligence.entity_clusterer import _is_personal_email
        assert _is_personal_email('yahoo.de') is True

    def test_is_personal_email_t_online(self):
        from email_intelligence.entity_clusterer import _is_personal_email
        assert _is_personal_email('t-online.de') is True

    def test_is_personal_email_bank_not_personal(self):
        from email_intelligence.entity_clusterer import _is_personal_email
        assert _is_personal_email('deutsche-bank.de') is False

    def test_is_personal_email_fitstar_not_personal(self):
        from email_intelligence.entity_clusterer import _is_personal_email
        assert _is_personal_email('fitstar.de') is False


class TestSubscriptionDetectorHelpers:
    """Test unsubscribe link and newsletter subject detection."""

    def test_has_unsubscribe_link_in_snippet(self):
        from email_intelligence.subscription_detector import _has_unsubscribe_link
        snippet = 'Great deals! Click here to unsubscribe from our list.'
        has_unsub, url = _has_unsubscribe_link(snippet, '')
        assert has_unsub is True

    def test_has_unsubscribe_link_german(self):
        from email_intelligence.subscription_detector import _has_unsubscribe_link
        snippet = 'Tolle Angebote! abbestellen: https://shop.de/abbestellen?id=123'
        has_unsub, url = _has_unsubscribe_link(snippet, '')
        assert has_unsub is True

    def test_no_unsubscribe_normal_email(self):
        from email_intelligence.subscription_detector import _has_unsubscribe_link
        snippet = 'Hi Mohamed, please find attached the invoice for your account.'
        has_unsub, url = _has_unsubscribe_link(snippet, '')
        assert has_unsub is False

    def test_newsletter_subject_detected(self):
        from email_intelligence.subscription_detector import _has_newsletter_subject
        assert _has_newsletter_subject('Weekly Newsletter - Top Stories') is True

    def test_digest_subject_detected(self):
        from email_intelligence.subscription_detector import _has_newsletter_subject
        assert _has_newsletter_subject('Your Weekly Digest') is True

    def test_normal_subject_not_newsletter(self):
        from email_intelligence.subscription_detector import _has_newsletter_subject
        assert _has_newsletter_subject('Re: Your Deutsche Bank application') is False

    def test_mahnung_not_newsletter(self):
        from email_intelligence.subscription_detector import _has_newsletter_subject
        assert _has_newsletter_subject('Mahnung - Forderung Nr. 12345') is False

    def test_noreply_triggers_detection(self):
        from email_intelligence.subscription_detector import _has_unsubscribe_link
        content = 'From: noreply@marketing.company.de'
        has_unsub, _ = _has_unsubscribe_link('', content)
        assert has_unsub is True
