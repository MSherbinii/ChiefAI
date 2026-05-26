"""
Admin tool implementations for Clerk agent.
Handles documents, deadlines, German bureaucracy, insurance.
"""
import os
from datetime import datetime, timezone, timedelta
from supabase import create_client
from pydantic import BaseModel
from typing import Optional

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class DocumentInfo(BaseModel):
    id: str
    type: str
    title: Optional[str]
    extracted_fields: dict
    expires_at: Optional[str]
    days_until_expiry: Optional[int]
    source: Optional[str]


class AdminDebt(BaseModel):
    total_items: int
    overdue: list[dict]
    expiring_soon: list[dict]  # within 30 days
    pending_actions: list[dict]


async def get_document_library(user_id: str) -> list[DocumentInfo]:
    """Get all stored documents with expiry status."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.table('lg_documents') \
            .select('id, type, title, extracted_fields, expires_at, source') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(20) \
            .execute()

        now = datetime.now(timezone.utc)
        docs = []
        for r in (result.data or []):
            days_until_expiry = None
            if r.get('expires_at'):
                try:
                    exp = datetime.fromisoformat(str(r['expires_at']))
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    days_until_expiry = (exp - now).days
                except Exception:
                    pass

            docs.append(DocumentInfo(
                id=str(r['id']),
                type=r.get('type', 'unknown'),
                title=r.get('title'),
                extracted_fields=r.get('extracted_fields') or {},
                expires_at=r.get('expires_at'),
                days_until_expiry=days_until_expiry,
                source=r.get('source'),
            ))

        return docs
    except Exception:
        return []


async def find_insurance_number(user_id: str, insurance_type: str = 'health') -> Optional[str]:
    """Look up insurance number from document library."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.table('lg_documents') \
            .select('extracted_fields') \
            .eq('user_id', user_id) \
            .ilike('type', f'%insurance%') \
            .limit(5) \
            .execute()

        for r in (result.data or []):
            fields = r.get('extracted_fields') or {}
            for key in ['insurance_number', 'member_id', 'versicherungsnummer', 'mitgliedsnummer']:
                if fields.get(key):
                    return str(fields[key])

        return None
    except Exception:
        return None


async def get_admin_debt(user_id: str) -> AdminDebt:
    """Calculate total admin debt: overdue items + expiring documents + pending queue."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        # Expiring documents
        docs = await get_document_library(user_id)
        overdue = [d.dict() for d in docs if d.days_until_expiry is not None and d.days_until_expiry < 0]
        expiring_soon = [d.dict() for d in docs if d.days_until_expiry is not None and 0 <= d.days_until_expiry <= 30]

        # Pending admin queue items
        queue = sb.table('approval_queue') \
            .select('title, agent, risk_level, created_at') \
            .eq('user_id', user_id) \
            .eq('status', 'pending') \
            .eq('agent', 'Clerk') \
            .execute()

        pending = queue.data or []

        return AdminDebt(
            total_items=len(overdue) + len(expiring_soon) + len(pending),
            overdue=overdue,
            expiring_soon=expiring_soon,
            pending_actions=pending,
        )
    except Exception:
        return AdminDebt(total_items=0, overdue=[], expiring_soon=[], pending_actions=[])


async def create_admin_draft(
    user_id: str,
    doc_type: str,
    recipient: str,
    content: str,
    reference_number: Optional[str] = None,
) -> dict:
    """Save a drafted admin letter/form to approval queue."""
    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.table('approval_queue').insert({
            'user_id': user_id,
            'agent': 'Clerk',
            'action_type': 'draft_reply',
            'risk_level': 'approve',
            'title': f'Admin draft: {doc_type} to {recipient}',
            'description': content[:300],
            'payload': {
                'doc_type': doc_type,
                'recipient': recipient,
                'content': content,
                'reference_number': reference_number,
            },
            'context_capsule': {
                'sources': ['Document library', 'Insurance card'],
                'reasoning': 'Draft created from extracted document fields',
                'confidence': 'HIGH',
            },
            'status': 'pending',
        }).execute()

        return {'success': True, 'queue_id': result.data[0]['id'] if result.data else None}
    except Exception as e:
        return {'success': False, 'error': str(e)}
