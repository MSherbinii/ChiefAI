"""
Evaluation runner for Chief agents.
Runs test cases and measures response quality.
"""
import os
import sys
import asyncio
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from eval.test_cases import ALL_TEST_CASES, TestCase
from guardrails import evaluate_response_quality, check_output_guardrails
from models import ChatRequest, ChatResponse


class EvalResult:
    def __init__(self, test_case: TestCase, response: str, agent: str, quality_score: int, passed: bool, issues: list):
        self.test_name = test_case.name
        self.expected_agent = test_case.expected_agent
        self.actual_agent = agent
        self.response_preview = response[:150]
        self.quality_score = quality_score
        self.passed = passed
        self.issues = issues
        self.agent_correct = agent == test_case.expected_agent

    def to_dict(self):
        return {
            'test_name': self.test_name,
            'expected_agent': self.expected_agent,
            'actual_agent': self.actual_agent,
            'response_preview': self.response_preview,
            'quality_score': self.quality_score,
            'passed': self.passed,
            'agent_correct': self.agent_correct,
            'issues': self.issues,
        }


async def run_test_case(test_case: TestCase, agent_instance) -> EvalResult:
    """Run a single test case against an agent."""
    try:
        request = ChatRequest(
            message=test_case.user_message,
            history=[],
            user_id=None,
        )

        # Override fetch_context to return mock data
        original_fetch = agent_instance.fetch_context
        async def mock_fetch_context(user_id): return test_case.mock_context
        agent_instance.fetch_context = mock_fetch_context

        # Also override fetch_rag_context to return empty (no real DB)
        async def mock_rag(user_id, query): return ''
        agent_instance.fetch_rag_context = mock_rag

        response: ChatResponse = await agent_instance.handle(request)
        agent_instance.fetch_context = original_fetch

        # Evaluate quality
        quality = evaluate_response_quality(
            test_case.user_message,
            response.reply,
            test_case.mock_context,
            response.agent,
        )

        # Check must_contain
        issues = []
        response_lower = response.reply.lower()

        for term in test_case.must_contain:
            if term.lower() not in response_lower:
                issues.append(f'Missing required term: "{term}"')

        for term in test_case.must_not_contain:
            if term.lower() in response_lower:
                issues.append(f'Contains forbidden term: "{term}"')

        if quality['score'] < test_case.min_quality_score:
            issues.append(f'Quality score {quality["score"]} below minimum {test_case.min_quality_score}')

        output_check = check_output_guardrails(response.reply, response.agent)
        if not output_check.passed:
            issues.append(f'Output guardrail failed: {output_check.violation}')

        passed = len(issues) == 0

        return EvalResult(test_case, response.reply, response.agent, quality['score'], passed, issues)

    except Exception as e:
        return EvalResult(test_case, str(e), 'ERROR', 0, False, [f'Exception: {e}'])


async def run_all_evaluations() -> dict:
    """Run all test cases and return summary report."""
    from agents.pulse import PulseAgent
    from agents.echo import EchoAgent
    from agents.forge import ForgeAgent
    from agents.ledger import LedgerAgent
    from agents.clerk import ClerkAgent

    agent_map = {
        'Pulse': PulseAgent(),
        'Echo': EchoAgent(),
        'Forge': ForgeAgent(),
        'Ledger': LedgerAgent(),
        'Clerk': ClerkAgent(),
    }

    results = []
    for test_case in ALL_TEST_CASES:
        agent = agent_map.get(test_case.expected_agent)
        if not agent:
            continue
        print(f'  Running: {test_case.name}...', end=' ', flush=True)
        result = await run_test_case(test_case, agent)
        results.append(result.to_dict())
        status = 'PASS' if result.passed else 'FAIL'
        print(f'{status} (score: {result.quality_score})')

    total = len(results)
    passed = sum(1 for r in results if r['passed'])
    avg_score = sum(r['quality_score'] for r in results) / total if total > 0 else 0

    return {
        'timestamp': datetime.now().isoformat(),
        'total': total,
        'passed': passed,
        'failed': total - passed,
        'pass_rate': round(passed / total * 100, 1) if total > 0 else 0,
        'avg_quality_score': round(avg_score, 1),
        'results': results,
    }


if __name__ == '__main__':
    print('Running Chief agent evaluations...')
    report = asyncio.run(run_all_evaluations())
    print(f'\n=== RESULTS ===')
    print(f'Passed: {report["passed"]}/{report["total"]} ({report["pass_rate"]}%)')
    print(f'Avg quality score: {report["avg_quality_score"]}/100')
    print(f'\nFailed tests:')
    for r in report['results']:
        if not r['passed']:
            print(f'  FAIL {r["test_name"]}')
            for issue in r['issues']:
                print(f'    - {issue}')

    # Save report
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'eval_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f'\nFull report saved to eval_report.json')
