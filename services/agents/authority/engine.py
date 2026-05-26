"""
Authority engine: determines whether an agent tool call is
allowed, notify-only, requires approval, requires confirmation, or denied.

Decision hierarchy (from role YAML):
  autonomous_actions   -> 'allowed'
  requires_approval    -> 'approve_required'
  requires_confirmation-> 'confirm_required'
  denied_tools         -> 'denied'
  anything else        -> 'approve_required'  (safe default)
"""
import yaml
import os
from dataclasses import dataclass
from typing import Literal

AuthorityDecision = Literal['allowed', 'notify', 'approve_required', 'confirm_required', 'denied']

@dataclass
class AuthorityResult:
    decision: AuthorityDecision
    agent: str
    tool_name: str
    reason: str


def _load_role(agent_name: str) -> dict:
    roles_dir = os.path.join(os.path.dirname(__file__), '..', 'roles')
    path = os.path.join(roles_dir, f'{agent_name.lower()}.yaml')
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return yaml.safe_load(f)


def check_authority(agent_name: str, tool_name: str) -> AuthorityResult:
    role = _load_role(agent_name)

    if tool_name in role.get('denied_tools', []):
        return AuthorityResult(
            decision='denied',
            agent=agent_name,
            tool_name=tool_name,
            reason=f'{tool_name} is not permitted for {agent_name}',
        )

    if tool_name in role.get('autonomous_actions', []):
        return AuthorityResult(
            decision='allowed',
            agent=agent_name,
            tool_name=tool_name,
            reason='autonomous action — no approval needed',
        )

    if tool_name in role.get('requires_confirmation', []):
        return AuthorityResult(
            decision='confirm_required',
            agent=agent_name,
            tool_name=tool_name,
            reason='high-risk action requires explicit confirmation',
        )

    if tool_name in role.get('requires_approval', []):
        return AuthorityResult(
            decision='approve_required',
            agent=agent_name,
            tool_name=tool_name,
            reason='action requires user approval before executing',
        )

    # Safe default: unknown tools require approval
    return AuthorityResult(
        decision='approve_required',
        agent=agent_name,
        tool_name=tool_name,
        reason='unknown tool defaults to approval-required',
    )
