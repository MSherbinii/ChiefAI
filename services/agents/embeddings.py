"""
Vector embeddings for Life Graph semantic search.
Uses Amazon Bedrock Titan Embeddings v2.
Titan v2 supports 256/512/1024 dims; we use 1024 and zero-pad to 1536
to match the existing vector(1536) pgvector columns.
Falls back to sentence-transformers all-MiniLM-L6-v2 if Bedrock unavailable.
"""
import os
import json
import boto3
from typing import Optional
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'eu-central-1')

_TITAN_MODEL = 'amazon.titan-embed-text-v2:0'
_TITAN_NATIVE_DIMS = 1024   # highest quality Titan v2 supports in eu-central-1
_TARGET_DIMS = 1536          # pgvector column width — we pad shorter vectors

# Cache whether Titan is available (checked on first call)
_titan_available: Optional[bool] = None
_st_model = None  # lazy-loaded sentence transformer


def _pad_to_target(vec: list[float]) -> list[float]:
    """Zero-pad vector to _TARGET_DIMS so pgvector accepts it."""
    if len(vec) >= _TARGET_DIMS:
        return vec[:_TARGET_DIMS]
    return vec + [0.0] * (_TARGET_DIMS - len(vec))


def get_bedrock_client():
    return boto3.client(
        'bedrock-runtime',
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    )


def _embed_titan(text: str) -> Optional[list[float]]:
    """Call Bedrock Titan Embeddings v2 (1024 dims, padded to 1536)."""
    try:
        client = get_bedrock_client()
        response = client.invoke_model(
            modelId=_TITAN_MODEL,
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'inputText': text[:8000],  # Titan max input
                'dimensions': _TITAN_NATIVE_DIMS,
                'normalize': True,
            })
        )
        result = json.loads(response['body'].read())
        return _pad_to_target(result['embedding'])
    except Exception as e:
        print(f'Titan embedding error: {e}')
        return None


def _embed_sentence_transformer(text: str) -> Optional[list[float]]:
    """Fallback: sentence-transformers all-MiniLM-L6-v2 (384 dims), padded to 1536."""
    global _st_model
    try:
        if _st_model is None:
            from sentence_transformers import SentenceTransformer
            _st_model = SentenceTransformer('all-MiniLM-L6-v2')
        vec = _st_model.encode(text[:512]).tolist()
        return _pad_to_target(vec)
    except Exception as e:
        print(f'SentenceTransformer embedding error: {e}')
        return None


def embed_text(text: str) -> Optional[list[float]]:
    """
    Generate 1536-dim embedding.
    Primary: Amazon Titan Embeddings v2 via Bedrock.
    Fallback: sentence-transformers all-MiniLM-L6-v2 (padded to 1536 dims).
    Returns None if all methods fail.
    """
    global _titan_available

    if not text or not text.strip():
        return None

    # Try Titan first (or skip if already known unavailable)
    if _titan_available is not False:
        vec = _embed_titan(text)
        if vec is not None:
            _titan_available = True
            return vec
        else:
            if _titan_available is None:
                print('Titan unavailable — falling back to sentence-transformers')
            _titan_available = False

    # Fallback
    return _embed_sentence_transformer(text)


def embed_batch(texts: list[str]) -> list[Optional[list[float]]]:
    """Embed multiple texts. Returns list of embeddings (None for failures)."""
    return [embed_text(t) for t in texts]


async def update_entity_embeddings(user_id: str) -> dict:
    """
    Populate embedding column for all entities that don't have one yet.
    Embeds: name + type + properties summary
    """
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    # Fetch entities without embeddings
    result = sb.table('entities') \
        .select('id, name, type, properties') \
        .eq('user_id', user_id) \
        .is_('embedding', 'null') \
        .limit(50) \
        .execute()

    updated = 0
    failed = 0
    for entity in (result.data or []):
        # Build text representation for embedding
        props = entity.get('properties') or {}
        props_str = ' '.join(f'{k}: {v}' for k, v in props.items() if v)
        text = f"{entity['type']} {entity['name']} {props_str}".strip()

        embedding = embed_text(text)
        if embedding:
            sb.table('entities') \
                .update({'embedding': embedding}) \
                .eq('id', entity['id']) \
                .execute()
            updated += 1
        else:
            failed += 1

    return {'updated': updated, 'failed': failed}


async def update_communication_embeddings(user_id: str) -> dict:
    """Populate embeddings for recent communications."""
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

    result = sb.table('lg_communications') \
        .select('id, subject, participants') \
        .eq('user_id', user_id) \
        .is_('embedding', 'null') \
        .limit(50) \
        .execute()

    updated = 0
    failed = 0
    for comm in (result.data or []):
        participants_str = ' '.join(comm.get('participants') or [])
        text = f"email thread: {comm.get('subject', '')} from {participants_str}"
        embedding = embed_text(text)
        if embedding:
            sb.table('lg_communications') \
                .update({'embedding': embedding}) \
                .eq('id', comm['id']) \
                .execute()
            updated += 1
        else:
            failed += 1

    return {'updated': updated, 'failed': failed}
