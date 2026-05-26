"""
Agent tool execution gate - adapted from Jarvis orchestrator pattern.

Every tool call in Chief passes through this gate before executing.

Jarvis source: src/agents/orchestrator.ts → executeTool()
Key patterns preserved:
  1. Emergency stop check (Jarvis: emergencyController.canExecute())
  2. Bypass for approval-mechanism tool itself (Jarvis: request_approval bypass)
  3. Authority decision via engine (Jarvis: authorityEngine.checkAuthority())
  4. Audit log ALWAYS, regardless of outcome (Jarvis: auditTrail.log())
  5. Denied  → hard stop with reason string
  6. Approval required → queue it, return AWAITING_APPROVAL sentinel
  7. Execute → cap result at MAX_TOOL_OUTPUT_CHARS (Jarvis: MAX_TOOL_RESULT_CHARS = 6000)
"""
import os
import asyncio
import inspect
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from pydantic import BaseModel
from supabase import create_client

from authority.engine import check_authority, AuthorityResult

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

# Mirrors Jarvis's MAX_TOOL_RESULT_CHARS = 6000
MAX_TOOL_OUTPUT_CHARS = 6000

# Sentinel returned when an action is queued for approval (mirrors Jarvis)
AWAITING_APPROVAL = '[AWAITING_APPROVAL]'

# Tools that ARE the approval mechanism — gating them would recurse
APPROVAL_BYPASS_TOOLS = {'request_approval', 'approve_action', 'deny_action'}

# Category mapping: tool name prefix → action category (mirrors audit.py)
_CATEGORY_MAP = {
    'log_': 'health',
    'read_health': 'health',
    'generate_gym': 'health',
    'draft_email': 'communication',
    'send_email': 'communication',
    'read_email': 'communication',
    'detect_stale': 'communication',
    'read_github': 'projects',
    'analyze_commit': 'projects',
    'suggest_next': 'projects',
    'read_transaction': 'finance',
    'detect_subscription': 'finance',
    'cancel_subscription': 'finance',
    'affordability': 'finance',
    'read_document': 'admin',
    'extract_document': 'admin',
    'draft_reply': 'admin',
}


class ToolCallRequest(BaseModel):
    """Encapsulates everything needed to gate + execute a single tool call."""

    user_id: str
    agent: str
    tool_name: str
    tool_args: dict = {}
    tool_fn: Optional[Any] = None  # The actual callable to invoke

    class Config:
        arbitrary_types_allowed = True


class GateResult(BaseModel):
    """Result returned by execute_through_gate()."""

    executed: bool
    output: str
    awaiting_approval: bool = False
    denied: bool = False
    queue_item_id: Optional[str] = None


async def execute_through_gate(req: ToolCallRequest) -> GateResult:
    """
    Every agent tool call must pass through this gate.

    Mirrors Jarvis's AgentOrchestrator.executeTool() authority gate sequence:
      1. Emergency stop (if global kill-switch is set)
      2. Bypass for approval-mechanism tools
      3. Authority decision
      4. Audit log (always)
      5. Denied → return hard stop
      6. Approval required → queue, return AWAITING_APPROVAL
      7. Execute → cap output at MAX_TOOL_OUTPUT_CHARS
    """
    # 1. Emergency stop — honour CHIEF_EMERGENCY_STOP env var
    if os.getenv('CHIEF_EMERGENCY_STOP', '').lower() in ('1', 'true', 'yes', 'paused'):
        return GateResult(
            executed=False,
            denied=True,
            output='[SYSTEM PAUSED] All tool execution is suspended.',
        )

    # 2. Bypass for the approval-mechanism tools themselves
    #    (Jarvis: if (toolCall.name === 'request_approval') → execute directly)
    if req.tool_name in APPROVAL_BYPASS_TOOLS:
        return await _execute_direct(req)

    # 3. Authority decision
    auth = check_authority(req.agent, req.tool_name)

    # 4. Audit log — always, regardless of outcome (Jarvis: auditTrail.log())
    _log_to_audit(req, auth, executed=False)

    # 5. Denied → hard stop
    if auth.decision == 'denied':
        return GateResult(
            executed=False,
            denied=True,
            output=f'[AUTHORITY DENIED] Cannot execute {req.tool_name}: {auth.reason}',
        )

    # 6. Approval / confirmation required → queue, return sentinel
    #    (Jarvis: approvalManager.createRequest() + onApprovalNeeded callback)
    if auth.decision in ('approve_required', 'confirm_required'):
        queue_id = await _queue_for_approval(req, auth)
        return GateResult(
            executed=False,
            awaiting_approval=True,
            output=(
                f'{AWAITING_APPROVAL} Action "{req.tool_name}" queued for approval. '
                f'Reason: {auth.reason}. Queue ID: {queue_id or "unknown"}'
            ),
            queue_item_id=queue_id,
        )

    # 7. Allowed → execute, cap output
    return await _execute_direct(req, auth=auth)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _execute_direct(
    req: ToolCallRequest,
    auth: Optional[AuthorityResult] = None,
) -> GateResult:
    """Execute the tool function and cap its output."""
    if not req.tool_fn or not callable(req.tool_fn):
        # No function provided — treat as a read-only pass-through
        return GateResult(executed=True, output='ok')

    try:
        if inspect.iscoroutinefunction(req.tool_fn):
            result = await req.tool_fn(**req.tool_args)
        else:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: req.tool_fn(**req.tool_args)
            )

        output = str(result)
        if len(output) > MAX_TOOL_OUTPUT_CHARS:
            output = output[:MAX_TOOL_OUTPUT_CHARS] + f'\n... (truncated, was {len(str(result))} chars)'

        # Update audit entry with success (best-effort)
        if auth is not None:
            _log_execution_result(req, output)

        return GateResult(executed=True, output=output)

    except Exception as exc:
        error_str = str(exc)
        if auth is not None:
            _log_execution_error(req, error_str)
        return GateResult(
            executed=False,
            output=f'Tool execution failed: {error_str}',
        )


async def _queue_for_approval(
    req: ToolCallRequest,
    auth: AuthorityResult,
) -> Optional[str]:
    """
    Insert a row into approval_queue and return its ID.
    Mirrors Jarvis's approvalManager.createRequest() + Supabase insert.
    """
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        risk = 'confirm' if auth.decision == 'confirm_required' else 'approve'
        result = sb.table('approval_queue').insert({
            'user_id': req.user_id,
            'agent': req.agent,
            'action_type': req.tool_name,
            'risk_level': risk,
            'title': f'{req.agent}: {req.tool_name}',
            'description': f'Args: {str(req.tool_args)[:200]}',
            'payload': req.tool_args,
            'context_capsule': {
                'sources': [f'{req.agent} agent'],
                'reasoning': auth.reason,
                'confidence': 'HIGH',
            },
            'status': 'pending',
        }).execute()
        return result.data[0]['id'] if result.data else None
    except Exception:
        return None


def _resolve_category(tool_name: str) -> str:
    """Map a tool name to an action category string."""
    for prefix, cat in _CATEGORY_MAP.items():
        if tool_name.startswith(prefix):
            return cat
    return 'general'


def _log_to_audit(
    req: ToolCallRequest,
    auth: AuthorityResult,
    executed: bool,
) -> None:
    """
    Write an audit_trail row for every gate invocation.
    Mirrors Jarvis: auditTrail.log() called before execution regardless of outcome.
    Never raises — audit logging must not crash the main flow.
    """
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        sb.table('audit_trail').insert({
            'user_id': req.user_id,
            'agent': req.agent,
            'tool_name': req.tool_name,
            'action_category': _resolve_category(req.tool_name),
            'authority_decision': auth.decision,
            'executed': executed,
            'input_data': req.tool_args,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass


def _log_execution_result(req: ToolCallRequest, output: str) -> None:
    """Best-effort update to mark the most recent audit row as executed."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        sb.table('audit_trail').update({
            'executed': True,
            'output_data': {'result': output[:500]},
        }).eq('user_id', req.user_id) \
          .eq('tool_name', req.tool_name) \
          .eq('executed', False) \
          .execute()
    except Exception:
        pass


def _log_execution_error(req: ToolCallRequest, error: str) -> None:
    """Best-effort update to mark the most recent audit row with an error."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        sb.table('audit_trail').update({
            'executed': False,
            'error': error[:200],
        }).eq('user_id', req.user_id) \
          .eq('tool_name', req.tool_name) \
          .eq('executed', False) \
          .execute()
    except Exception:
        pass
