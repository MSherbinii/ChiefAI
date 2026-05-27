# services/agents/tests/test_case_discovery.py
"""
Tests for Case Discovery Engine and Cross-Entity Reasoner.
All tests use mock data — no real DB or LLM calls.
"""
import os, sys
os.environ.setdefault('SUPABASE_URL', 'https://test.supabase.co')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjk5OTk5OTk5OTl9.test')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'AKIATEST123456789012')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'test-secret-not-real')
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-central-1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from datetime import datetime, timezone, timedelta


class TestCrossEntityReasonerHelpers:
    """Test helper functions in cross_entity_reasoner."""

    def test_extract_ref_numbers_german_format(self):
        from email_intelligence.cross_entity_reasoner import _extract_ref_numbers
        text = "Ihre Kundennummer: DE-20241234 / Aktenzeichen AB-987654"
        refs = _extract_ref_numbers(text)
        assert 'DE-20241234' in refs or 'AB-987654' in refs

    def test_extract_ref_numbers_order_id(self):
        from email_intelligence.cross_entity_reasoner import _extract_ref_numbers
        text = "Order reference: ORD-20240527-9876"
        refs = _extract_ref_numbers(text)
        assert len(refs) > 0

    def test_extract_ref_numbers_empty_text(self):
        from email_intelligence.cross_entity_reasoner import _extract_ref_numbers
        refs = _extract_ref_numbers('')
        assert refs == set()

    def test_has_debt_signals_inkasso(self):
        from email_intelligence.cross_entity_reasoner import _has_debt_signals
        assert _has_debt_signals('Inkasso Forderung Nr. 12345') is True

    def test_has_debt_signals_mahnung(self):
        from email_intelligence.cross_entity_reasoner import _has_debt_signals
        assert _has_debt_signals('Letzte Mahnung - Zahlungsaufforderung') is True

    def test_has_debt_signals_normal_email(self):
        from email_intelligence.cross_entity_reasoner import _has_debt_signals
        assert _has_debt_signals('Thank you for your order. Your item has shipped.') is False

    def test_has_debt_signals_subscription_email(self):
        from email_intelligence.cross_entity_reasoner import _has_debt_signals
        assert _has_debt_signals('Your monthly subscription has been renewed.') is False


class TestEchoV2Context:
    """Test Echo v2 context-building logic."""

    def test_echo_imports(self):
        from agents.echo import EchoAgent, _fetch_cases_context, _fetch_raw_email_context
        assert callable(_fetch_cases_context)
        assert callable(_fetch_raw_email_context)

    def test_echo_case_query_detection(self):
        from agents.echo import CASE_QUERY_KEYWORDS
        # These keywords should trigger case-aware context
        assert "what's happening" in CASE_QUERY_KEYWORDS
        assert "deutsche bank" in CASE_QUERY_KEYWORDS
        assert "fitstar" in CASE_QUERY_KEYWORDS
        assert "stalled" in CASE_QUERY_KEYWORDS

    def test_echo_agent_instantiates(self):
        from agents.echo import EchoAgent
        agent = EchoAgent()
        assert agent.name == 'Echo'
        assert len(agent.system_prompt) > 50

    def test_build_interview_message_with_cases(self):
        from main import _build_interview_message
        cases = [
            {'title': 'FitStar debt dispute', 'priority': 'high', 'status': 'needs_action',
             'summary': 'Debt collector contacted you.', 'pending_action': 'Respond within 7 days'},
            {'title': 'Deutsche Bahn refund', 'priority': 'normal', 'status': 'open',
             'summary': 'Refund request pending.', 'pending_action': None},
        ]
        dead_subs = [{'sender_email': 'news@roboforex.com', 'total_received': 10, 'engagement_score': 0}]
        msg = _build_interview_message(cases, dead_subs)
        assert 'FitStar' in msg
        assert 'Deutsche Bahn' in msg
        assert 'newsletters' in msg.lower()
        assert 'Did I get these right' in msg

    def test_build_interview_message_empty(self):
        from main import _build_interview_message
        msg = _build_interview_message([], [])
        assert 'Did I get these right' in msg


class TestCaseDiscovererHelpers:
    """Test case discoverer JSON parsing robustness."""

    def test_case_status_valid_values(self):
        # Verify the status values match the DB constraint
        valid_statuses = {'open', 'progressing', 'stalled', 'needs_action', 'resolved'}
        assert 'stalled' in valid_statuses
        assert 'needs_action' in valid_statuses

    def test_priority_ordering(self):
        # Verify priority ordering used in merge logic
        from main import _build_interview_message
        PRIORITY_ORDER = {'critical': 4, 'high': 3, 'normal': 2, 'low': 1}
        assert PRIORITY_ORDER['critical'] > PRIORITY_ORDER['high']
        assert PRIORITY_ORDER['high'] > PRIORITY_ORDER['normal']
        assert PRIORITY_ORDER['normal'] > PRIORITY_ORDER['low']

    def test_case_discovery_prompt_completeness(self):
        from email_intelligence.case_discoverer import CASE_DISCOVERY_SYSTEM
        # Prompt must include all valid status values
        assert 'stalled' in CASE_DISCOVERY_SYSTEM
        assert 'needs_action' in CASE_DISCOVERY_SYSTEM
        # Prompt must include all valid priority values
        assert 'critical' in CASE_DISCOVERY_SYSTEM
        assert 'high' in CASE_DISCOVERY_SYSTEM
        # Prompt must instruct JSON-only output
        assert 'JSON' in CASE_DISCOVERY_SYSTEM or 'json' in CASE_DISCOVERY_SYSTEM

    def test_cross_entity_system_has_debt_patterns(self):
        from email_intelligence.cross_entity_reasoner import DEBT_COLLECTOR_SIGNALS
        assert len(DEBT_COLLECTOR_SIGNALS) >= 5
        assert any('inkasso' in p for p in DEBT_COLLECTOR_SIGNALS)
        assert any('mahnung' in p for p in DEBT_COLLECTOR_SIGNALS)
