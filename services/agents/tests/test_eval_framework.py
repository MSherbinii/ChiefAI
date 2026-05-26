"""
Tests for the evaluation framework itself (not the LLM responses).
"""
import os, sys
os.environ.setdefault('SUPABASE_URL', 'https://test.supabase.co')
os.environ.setdefault('SUPABASE_SERVICE_ROLE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRlc3QiLCJyb2xlIjoic2VydmljZV9yb2xlIiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjk5OTk5OTk5OTl9.test')
os.environ.setdefault('AWS_ACCESS_KEY_ID', 'AKIATEST123456789012')
os.environ.setdefault('AWS_SECRET_ACCESS_KEY', 'test-secret-key-not-real')
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-central-1')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from eval.test_cases import ALL_TEST_CASES, PULSE_TEST_CASES, ECHO_TEST_CASES, FORGE_TEST_CASES, TestCase


class TestEvalFramework:
    """Test the evaluation framework structure."""

    def test_test_cases_have_required_fields(self):
        for tc in ALL_TEST_CASES:
            assert tc.name, f"Test case missing name"
            assert tc.user_message, f"Test case {tc.name} missing user_message"
            assert tc.mock_context, f"Test case {tc.name} missing mock_context"
            assert tc.expected_agent in ['Pulse', 'Echo', 'Forge', 'Ledger', 'Clerk', 'Scout', 'Chief'], \
                f"Test case {tc.name} has unknown expected_agent: {tc.expected_agent}"
            assert isinstance(tc.must_contain, list), f"Test case {tc.name}: must_contain must be a list"
            assert isinstance(tc.must_not_contain, list), f"Test case {tc.name}: must_not_contain must be a list"
            assert 0 <= tc.min_quality_score <= 100, \
                f"Test case {tc.name}: min_quality_score {tc.min_quality_score} out of range"

    def test_pulse_test_cases_route_to_pulse(self):
        for tc in PULSE_TEST_CASES:
            assert tc.expected_agent == 'Pulse', \
                f"PULSE_TEST_CASES contains non-Pulse case: {tc.name}"

    def test_echo_test_cases_route_to_echo(self):
        for tc in ECHO_TEST_CASES:
            assert tc.expected_agent == 'Echo', \
                f"ECHO_TEST_CASES contains non-Echo case: {tc.name}"

    def test_forge_test_cases_route_to_forge(self):
        for tc in FORGE_TEST_CASES:
            assert tc.expected_agent == 'Forge', \
                f"FORGE_TEST_CASES contains non-Forge case: {tc.name}"

    def test_no_test_cases_require_forbidden_patterns(self):
        """Ensure test cases themselves don't have forbidden patterns in must_contain."""
        forbidden = ['as an ai', 'i cannot', "i don't have"]
        for tc in ALL_TEST_CASES:
            for term in tc.must_contain:
                assert term.lower() not in forbidden, \
                    f"Test {tc.name}: must_contain has forbidden term '{term}'"

    def test_all_test_cases_unique_names(self):
        names = [tc.name for tc in ALL_TEST_CASES]
        assert len(names) == len(set(names)), "Duplicate test case names found"

    def test_minimum_coverage(self):
        """At least 2 test cases per major agent."""
        pulse_count = sum(1 for tc in ALL_TEST_CASES if tc.expected_agent == 'Pulse')
        echo_count = sum(1 for tc in ALL_TEST_CASES if tc.expected_agent == 'Echo')
        forge_count = sum(1 for tc in ALL_TEST_CASES if tc.expected_agent == 'Forge')
        assert pulse_count >= 2, f"Only {pulse_count} Pulse test cases (need >= 2)"
        assert echo_count >= 2, f"Only {echo_count} Echo test cases (need >= 2)"
        assert forge_count >= 1, f"Only {forge_count} Forge test cases (need >= 1)"

    def test_all_test_cases_in_all_list(self):
        """Verify ALL_TEST_CASES aggregates all agent test lists."""
        combined = PULSE_TEST_CASES + ECHO_TEST_CASES + FORGE_TEST_CASES
        assert len(ALL_TEST_CASES) == len(combined), \
            "ALL_TEST_CASES count doesn't match sum of individual lists"

    def test_must_contain_terms_are_lowercase_friendly(self):
        """must_contain terms should match case-insensitively — no regex special chars."""
        import re
        for tc in ALL_TEST_CASES:
            for term in tc.must_contain:
                # Ensure no regex special chars that could break re.search
                try:
                    re.compile(re.escape(term))
                except re.error:
                    pytest.fail(f"Test {tc.name}: must_contain term '{term}' is invalid")

    def test_quality_score_thresholds_reasonable(self):
        """No test case should require a perfect score (would be fragile)."""
        for tc in ALL_TEST_CASES:
            assert tc.min_quality_score <= 90, \
                f"Test {tc.name}: min_quality_score {tc.min_quality_score} is too high (max 90)"
