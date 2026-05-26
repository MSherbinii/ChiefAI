"""
Knowledge graph entity and relationship extractor.
Adapted from Jarvis's context-graph patterns.
Automatically extracts entities (people, projects, tools) and their
relationships from Gmail threads, GitHub commits, and other sources.
"""
import os
import json
from datetime import datetime, timezone
from supabase import create_client
from pydantic import BaseModel
from typing import Optional
from llm import get_client, AGENT_MODEL

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

EXTRACTION_SYSTEM = """Extract entities and relationships from the provided text.
Return ONLY valid JSON — no prose.

Schema:
{
  "entities": [
    {"type": "person|project|tool|place|concept", "name": "string", "properties": {}}
  ],
  "relationships": [
    {"from": "entity_name", "to": "entity_name", "type": "string"}
  ]
}

Entity type rules:
- person: any human name, professor, supervisor, colleague
- project: thesis, startup name, GitHub repo, course name
- tool: software, framework, service (WHOOP, Notion, GitHub, etc.)
- place: university, company, city, country
- concept: research topic, technical concept

Relationship types:
- supervises: person supervises project/person
- collaborates_with: person works with person
- uses: person/project uses tool
- part_of: project part_of larger project
- located_at: person/project located_at place
- studies_at: person studies_at place

Extract only clearly stated relationships. Maximum 5 entities, 5 relationships.
If nothing meaningful to extract, return {"entities": [], "relationships": []}"""


class ExtractionResult(BaseModel):
    entities: list[dict] = []
    relationships: list[dict] = []
    source: str = ''


async def extract_from_email_thread(
    user_id: str,
    subject: str,
    participants: list[str],
    body_snippet: str = '',
) -> ExtractionResult:
    """
    Extract entities from an email thread.
    Runs after Gmail sync to enrich the knowledge graph.
    """
    text = f"Email subject: {subject}\nParticipants: {', '.join(participants)}\n{body_snippet[:500]}"
    return await _extract_entities(user_id, text, source='gmail')


async def extract_from_commit(
    user_id: str,
    repo: str,
    message: str,
) -> ExtractionResult:
    """Extract entities from a GitHub commit message."""
    text = f"GitHub repo: {repo}\nCommit: {message[:200]}"
    return await _extract_entities(user_id, text, source='github')


async def _extract_entities(user_id: str, text: str, source: str) -> ExtractionResult:
    """
    Core extraction: run LLM to find entities/relationships,
    then upsert to entities + relationships tables.
    """
    try:
        client = get_client()
        response = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=400,
            system=EXTRACTION_SYSTEM,
            messages=[{'role': 'user', 'content': text}],
        )

        raw = response.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()

        data = json.loads(raw)
        result = ExtractionResult(
            entities=data.get('entities', []),
            relationships=data.get('relationships', []),
            source=source,
        )

        await _upsert_to_knowledge_graph(user_id, result)
        return result

    except Exception:
        return ExtractionResult(source=source)


async def _upsert_to_knowledge_graph(user_id: str, result: ExtractionResult) -> None:
    """Persist extracted entities and relationships to Supabase."""
    if not result.entities and not result.relationships:
        return

    try:
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        entity_id_map = {}

        # Upsert entities
        for e in result.entities:
            name = e.get('name', '').strip()
            etype = e.get('type', 'concept')
            if not name:
                continue

            upsert_result = sb.table('entities').upsert({
                'user_id': user_id,
                'type': etype,
                'name': name,
                'properties': e.get('properties', {}),
                'source': result.source,
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }, on_conflict='user_id,type,name').execute()

            if upsert_result.data:
                entity_id_map[name] = upsert_result.data[0]['id']

        # Upsert relationships
        for r in result.relationships:
            from_name = r.get('from', '')
            to_name = r.get('to', '')
            rel_type = r.get('type', 'related_to')

            from_id = entity_id_map.get(from_name)
            to_id = entity_id_map.get(to_name)

            if from_id and to_id:
                sb.table('relationships').upsert({
                    'user_id': user_id,
                    'from_id': from_id,
                    'to_id': to_id,
                    'type': rel_type,
                    'properties': {'source': result.source},
                }, on_conflict='user_id,from_id,to_id,type').execute()

        # Also add facts for each entity relationship
        for e in result.entities:
            name = e.get('name', '')
            if name and entity_id_map.get(name):
                for prop_key, prop_val in (e.get('properties') or {}).items():
                    sb.table('facts').insert({
                        'user_id': user_id,
                        'subject_id': entity_id_map[name],
                        'predicate': prop_key,
                        'object': str(prop_val)[:200],
                        'confidence': 0.8,
                        'source': result.source,
                    }).execute()

    except Exception:
        pass  # Knowledge extraction is enhancement, not critical


async def run_background_extraction(user_id: str) -> dict:
    """
    Run entity extraction over recent communications and commits.
    Called after connector syncs complete.
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Extract from recent communications
    comms = sb.table('lg_communications') \
        .select('subject, participants') \
        .eq('user_id', user_id) \
        .eq('status', 'active') \
        .order('created_at', desc=True) \
        .limit(20) \
        .execute()

    extracted_comms = 0
    for c in (comms.data or []):
        result = await extract_from_email_thread(
            user_id,
            c.get('subject', ''),
            c.get('participants', []),
        )
        if result.entities:
            extracted_comms += 1

    # Extract from recent commits
    commits = sb.table('lg_health') \
        .select('value') \
        .eq('user_id', user_id) \
        .eq('metric', 'github_commit') \
        .order('recorded_at', desc=True) \
        .limit(20) \
        .execute()

    extracted_commits = 0
    for c in (commits.data or []):
        v = c.get('value', {})
        result = await extract_from_commit(
            user_id,
            v.get('repo', ''),
            v.get('message', ''),
        )
        if result.entities:
            extracted_commits += 1

    return {
        'communications_processed': len(comms.data or []),
        'commits_processed': len(commits.data or []),
        'comms_with_entities': extracted_comms,
        'commits_with_entities': extracted_commits,
    }
