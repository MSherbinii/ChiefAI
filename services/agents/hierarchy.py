"""
Agent hierarchy for Chief.
Adapted from Jarvis hierarchy.ts + delegation.ts.

Chief (orchestrator) is the root agent.
Sub-agents (Pulse/Echo/Forge/Ledger/Clerk/Scout) are children.
Tasks can be delegated from Chief → sub-agent with commitment tracking.
"""
import os
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, ConfigDict
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class AgentNode(BaseModel):
    name: str
    parent: Optional[str] = None  # None = root (Chief)
    authority_level: int = 3
    status: str = 'idle'  # idle, active, terminated
    current_task: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


# Static hierarchy definition — Chief owns all sub-agents
AGENT_HIERARCHY = {
    'Chief': AgentNode(name='Chief', parent=None, authority_level=10),
    'Pulse': AgentNode(name='Pulse', parent='Chief', authority_level=4),
    'Echo': AgentNode(name='Echo', parent='Chief', authority_level=5),
    'Forge': AgentNode(name='Forge', parent='Chief', authority_level=4),
    'Ledger': AgentNode(name='Ledger', parent='Chief', authority_level=6),
    'Clerk': AgentNode(name='Clerk', parent='Chief', authority_level=5),
    'Scout': AgentNode(name='Scout', parent='Chief', authority_level=3),
}


def get_primary_agent() -> AgentNode:
    """Returns root agent (Chief)."""
    return AGENT_HIERARCHY['Chief']


def get_children(parent_name: str) -> list[AgentNode]:
    """Returns all direct children of an agent."""
    return [node for node in AGENT_HIERARCHY.values() if node.parent == parent_name]


def get_agent_authority(agent_name: str) -> int:
    """Returns authority level for an agent."""
    return AGENT_HIERARCHY.get(agent_name, AgentNode(name=agent_name)).authority_level


def can_delegate(from_agent: str, to_agent: str, tool_name: str) -> bool:
    """
    Check if from_agent can delegate tool_name to to_agent.
    Child authority must be less than parent authority.
    Mirrors Jarvis's authority inheritance: child_level = min(child, parent - 1)
    """
    from_level = get_agent_authority(from_agent)
    to_level = get_agent_authority(to_agent)
    return to_level < from_level


async def create_commitment(
    user_id: str,
    agent: str,
    what: str,
    why: Optional[str] = None,
    priority: str = 'normal',
    assigned_to: Optional[str] = None,
) -> Optional[str]:
    """
    Create a commitment (task) in the DB.
    Returns the commitment ID.
    Adapted from Jarvis delegation.ts delegateTask().
    """
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.table('commitments').insert({
            'user_id': user_id,
            'agent': agent,
            'what': what,
            'why': why,
            'priority': priority,
            'status': 'pending',
            'assigned_to': assigned_to,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).execute()
        return result.data[0]['id'] if result.data else None
    except Exception:
        return None


async def delegate_task(
    user_id: str,
    from_agent: str,
    to_agent: str,
    task: str,
    why: Optional[str] = None,
    priority: str = 'normal',
) -> dict:
    """
    Delegate a task from one agent to another.
    Adapted from Jarvis delegation.ts delegateTask():
    1. Creates a commitment
    2. Sends an agent_message of type 'task'
    Returns {commitment_id, message_id}
    """
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        # 1. Create commitment
        commitment_id = await create_commitment(
            user_id=user_id,
            agent=to_agent,
            what=task,
            why=why,
            priority=priority,
            assigned_to=to_agent,
        )

        # 2. Send agent message
        msg_result = sb.table('agent_messages').insert({
            'user_id': user_id,
            'from_agent': from_agent,
            'to_agent': to_agent,
            'type': 'task',
            'content': task,
            'priority': priority,
            'requires_response': True,
            'responded': False,
            'commitment_id': commitment_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }).execute()

        msg_id = msg_result.data[0]['id'] if msg_result.data else None

        return {'commitment_id': commitment_id, 'message_id': msg_id, 'delegated_to': to_agent}
    except Exception as e:
        return {'error': str(e)}


async def report_completion(
    user_id: str,
    from_agent: str,
    to_agent: str,
    commitment_id: str,
    result: str,
    success: bool = True,
) -> None:
    """
    Report task completion back to parent agent.
    Adapted from Jarvis delegation.ts reportCompletion():
    1. Updates commitment status
    2. Sends agent_message of type 'report'
    """
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        # Update commitment
        sb.table('commitments').update({
            'status': 'completed' if success else 'failed',
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).eq('id', commitment_id).eq('user_id', user_id).execute()

        # Send report back
        sb.table('agent_messages').insert({
            'user_id': user_id,
            'from_agent': from_agent,
            'to_agent': to_agent,
            'type': 'report',
            'content': result,
            'priority': 'high' if not success else 'normal',
            'requires_response': False,
            'responded': False,
            'commitment_id': commitment_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }).execute()

        # Mark original task message as responded
        sb.table('agent_messages').update({'responded': True}) \
            .eq('user_id', user_id) \
            .eq('to_agent', from_agent) \
            .eq('commitment_id', commitment_id) \
            .eq('type', 'task') \
            .execute()
    except Exception:
        pass


async def get_pending_tasks(user_id: str, agent: str) -> list[dict]:
    """Get all pending tasks assigned to an agent."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.table('commitments') \
            .select('id, what, why, priority, created_at') \
            .eq('user_id', user_id) \
            .eq('assigned_to', agent) \
            .eq('status', 'pending') \
            .order('priority', desc=True) \
            .limit(10) \
            .execute()
        return result.data or []
    except Exception:
        return []
