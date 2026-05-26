"""
Tests for the authority engine pure logic.
No mocking needed — reads from role YAML files only.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from authority.engine import check_authority


def test_pulse_log_workout_allowed():
    result = check_authority('Pulse', 'log_workout')
    assert result.decision == 'allowed'


def test_pulse_generate_gym_plan_approval():
    result = check_authority('Pulse', 'generate_gym_plan')
    assert result.decision == 'approve_required'


def test_pulse_send_email_denied():
    result = check_authority('Pulse', 'send_email')
    assert result.decision == 'denied'


def test_echo_send_email_confirm():
    result = check_authority('Echo', 'send_email')
    assert result.decision == 'confirm_required'


def test_echo_draft_email_approval():
    result = check_authority('Echo', 'draft_email')
    assert result.decision == 'approve_required'


def test_ledger_cancel_subscription_confirm():
    result = check_authority('Ledger', 'cancel_subscription')
    assert result.decision == 'confirm_required'


def test_unknown_agent_defaults_to_approval():
    result = check_authority('UnknownAgent', 'some_tool')
    assert result.decision == 'approve_required'


def test_unknown_tool_defaults_to_approval():
    result = check_authority('Pulse', 'unknown_tool')
    assert result.decision == 'approve_required'
