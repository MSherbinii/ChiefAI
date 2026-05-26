"""
Semantic search over the Life Graph using pgvector.
Enables RAG: retrieve relevant Life Graph context for any query.
"""
import os
from typing import Optional
from supabase import create_client
from embeddings import embed_text

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


async def search_entities(user_id: str, query: str, limit: int = 5) -> list[dict]:
    """
    Semantic search over entities (people, projects, tools).
    Returns most relevant entities for a given query.
    """
    embedding = embed_text(query)
    if not embedding:
        return []

    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        # Use pgvector cosine similarity search
        result = sb.rpc('search_entities', {
            'query_embedding': embedding,
            'user_id_filter': user_id,
            'match_count': limit,
        }).execute()
        return result.data or []
    except Exception as e:
        print(f'Vector search_entities failed ({e}), falling back to text search')
        # Fallback: simple text search if vector search fails
        try:
            sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            result = sb.table('entities') \
                .select('id, name, type, properties') \
                .eq('user_id', user_id) \
                .ilike('name', f'%{query[:30]}%') \
                .limit(limit) \
                .execute()
            return result.data or []
        except Exception:
            return []


async def search_communications(user_id: str, query: str, limit: int = 5) -> list[dict]:
    """Semantic search over email/comms threads."""
    embedding = embed_text(query)
    if not embedding:
        return []

    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        result = sb.rpc('search_communications', {
            'query_embedding': embedding,
            'user_id_filter': user_id,
            'match_count': limit,
        }).execute()
        return result.data or []
    except Exception as e:
        print(f'Vector search_communications failed ({e}), falling back to text search')
        # Fallback
        try:
            sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            result = sb.table('lg_communications') \
                .select('thread_id, subject, participants, last_message_at, staleness_days') \
                .eq('user_id', user_id) \
                .ilike('subject', f'%{query[:30]}%') \
                .limit(limit) \
                .execute()
            return result.data or []
        except Exception:
            return []


async def rag_context_for_query(user_id: str, query: str) -> str:
    """
    Full RAG pipeline: embed query → search Life Graph → format as context string.
    Used by agents to enrich their system prompt with relevant data.
    """
    entities = await search_entities(user_id, query, limit=3)
    comms = await search_communications(user_id, query, limit=3)

    context_parts = []

    if entities:
        context_parts.append('RELEVANT PEOPLE/PROJECTS:')
        for e in entities:
            props = e.get('properties') or {}
            email = props.get('email', '')
            context_parts.append(
                f'  - {e["type"]}: {e["name"]}' + (f' ({email})' if email else '')
            )

    if comms:
        context_parts.append('RELEVANT CONVERSATIONS:')
        for c in comms:
            subj = c.get('subject', '(no subject)')[:60]
            days = c.get('staleness_days', 0) or 0
            context_parts.append(f'  - "{subj}" [{days}d old]')

    return '\n'.join(context_parts) if context_parts else ''
