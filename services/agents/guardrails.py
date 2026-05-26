"""
Input/output guardrails for Chief agents.
Prevents harmful outputs and enforces domain restrictions.
"""
from pydantic import BaseModel
from typing import Optional
import re


class GuardrailResult(BaseModel):
    passed: bool
    violation: Optional[str] = None
    sanitized_input: Optional[str] = None


def check_input_guardrails(message: str, agent_name: str) -> GuardrailResult:
    """
    Check user input before passing to agent.
    Returns GuardrailResult with passed=False if blocked.
    """
    message_lower = message.lower()

    # Block prompt injection attempts
    injection_patterns = [
        r'ignore (all )?previous instructions',
        r'you are now',
        r'pretend (you are|to be)',
        r'forget (everything|your instructions)',
        r'new system prompt',
        r'disregard',
    ]
    for pattern in injection_patterns:
        if re.search(pattern, message_lower):
            return GuardrailResult(
                passed=False,
                violation=f'Prompt injection attempt detected: {pattern}'
            )

    # Domain restrictions per agent
    domain_violations = {
        'Pulse': ['cancel subscription', 'send email', 'bank', 'payment'],
        'Echo': ['workout', 'recovery', 'gym', 'sleep score'],
        'Forge': ['bank balance', 'subscription', 'insurance'],
        'Ledger': ['send email', 'workout', 'thesis'],
    }

    violations = domain_violations.get(agent_name, [])
    for v in violations:
        if v in message_lower:
            return GuardrailResult(
                passed=False,
                violation=f'Out-of-domain request for {agent_name}: {v}'
            )

    return GuardrailResult(passed=True, sanitized_input=message.strip())


def check_output_guardrails(response: str, agent_name: str) -> GuardrailResult:
    """
    Check agent output before returning to user.
    Prevents PII leakage, hallucinated financial advice, etc.
    """
    # Block responses that claim to have sent messages (Echo shouldn't auto-send)
    if agent_name == 'Echo':
        sent_patterns = ['i sent', 'i have sent', 'email sent', 'message sent', 'i emailed']
        for p in sent_patterns:
            if p in response.lower():
                return GuardrailResult(
                    passed=False,
                    violation='Echo claimed to send an email without approval',
                    sanitized_input=response.replace('sent', 'drafted').replace('Sent', 'Drafted')
                )

    # Block financial advice without data
    if agent_name == 'Ledger':
        if 'you should invest' in response.lower() or 'buy' in response.lower()[:50]:
            return GuardrailResult(
                passed=False,
                violation='Ledger giving unsolicited investment advice'
            )

    # Block very short responses that might indicate model confusion
    if len(response.strip()) < 20:
        return GuardrailResult(
            passed=False,
            violation=f'Response too short ({len(response)} chars) - likely model error'
        )

    return GuardrailResult(passed=True)


def evaluate_response_quality(
    user_message: str,
    response: str,
    context: str,
    agent_name: str
) -> dict:
    """
    Score response quality 0-100.
    Used for logging and future RL training signal.
    """
    score = 100
    issues = []

    # Penalize generic responses
    generic_phrases = [
        "i don't have access",
        'i cannot access',
        'as an ai',
        "i'm unable to",
        'unfortunately i',
    ]
    for phrase in generic_phrases:
        if phrase in response.lower():
            score -= 20
            issues.append(f'Generic phrase detected: {phrase}')

    # Penalize if context has data but response doesn't reference it
    if 'recovery' in context and 'recovery' not in response.lower() and agent_name == 'Pulse':
        score -= 15
        issues.append('Pulse response ignores recovery data in context')

    if 'staleness' in context.lower() and 'day' not in response.lower() and agent_name == 'Echo':
        score -= 10
        issues.append('Echo ignores staleness data in context')

    # Reward conciseness (2-4 sentences ideal)
    sentences = [s.strip() for s in response.split('.') if s.strip()]
    if 2 <= len(sentences) <= 5:
        score += 5
    elif len(sentences) > 8:
        score -= 10
        issues.append('Response too verbose')

    # Reward specific numbers
    numbers = re.findall(r'\d+', response)
    if numbers:
        score += 5
    else:
        score -= 5
        issues.append('No specific numbers in response')

    return {
        'score': max(0, min(100, score)),
        'issues': issues,
        'sentence_count': len(sentences),
        'has_numbers': bool(numbers),
    }
