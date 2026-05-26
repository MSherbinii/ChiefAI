"""
Document OCR and field extraction using Claude Vision.
Clerk agent uses this to extract fields from uploaded document images.
"""
import os
import json
import base64
import httpx
from datetime import datetime, timezone
from pydantic import BaseModel
from typing import Optional
from supabase import create_client
from llm import get_client, BRIEF_MODEL  # Use Sonnet for vision tasks

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')


class DocumentExtractRequest(BaseModel):
    user_id: str
    storage_path: str
    doc_type: str
    file_url: str


class ExtractedDocument(BaseModel):
    doc_type: str
    title: Optional[str] = None
    extracted_fields: dict = {}
    expires_at: Optional[str] = None
    confidence: str = 'medium'
    summary: str = ''


EXTRACTION_PROMPTS = {
    'insurance_card': """Extract these fields from the health insurance card:
- insurance_number (Versicherungsnummer / Mitgliedsnummer)
- insurance_company (Krankenkasse name)
- holder_name
- valid_until (expiry date if shown)
- policy_type

Return JSON with these exact keys. Use null for missing fields.""",

    'letter': """Extract these fields from the letter:
- sender (organization or person name)
- recipient
- date (letter date)
- subject (Betreff)
- reference_number (Aktenzeichen / Vorgangsnummer)
- deadline (any deadline mentioned)
- required_action (what the recipient needs to do)
- return_address

Return JSON with these exact keys. Use null for missing fields.""",

    'id': """Extract these fields from the ID/passport:
- full_name
- date_of_birth
- nationality
- document_number
- valid_until
- issuing_country

Return JSON with these exact keys. Use null for missing fields.""",

    'contract': """Extract these fields from the contract:
- parties (list of parties involved)
- contract_type
- start_date
- end_date
- key_obligations (list of 2-3 key points)
- cancellation_notice_period

Return JSON with these exact keys. Use null for missing fields.""",

    'default': """Extract all important fields from this document.
Return JSON with field names as keys. Include:
- document_type
- key dates
- important names/numbers
- any deadlines or obligations"""
}


async def extract_document_fields(req: DocumentExtractRequest) -> ExtractedDocument:
    """
    Use Claude Vision to extract structured fields from a document image.
    Falls back gracefully if the image can't be processed.
    """
    try:
        # Download the image
        async with httpx.AsyncClient() as http:
            img_resp = await http.get(req.file_url, timeout=30)
            img_bytes = img_resp.content
            content_type = img_resp.headers.get('content-type', 'image/jpeg')

        # Base64 encode for Claude
        img_b64 = base64.standard_b64encode(img_bytes).decode('utf-8')

        # Get extraction prompt
        prompt = EXTRACTION_PROMPTS.get(req.doc_type, EXTRACTION_PROMPTS['default'])

        client = get_client()
        response = client.messages.create(
            model=BRIEF_MODEL,  # Sonnet for vision
            max_tokens=800,
            messages=[{
                'role': 'user',
                'content': [
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': content_type,
                            'data': img_b64,
                        }
                    },
                    {
                        'type': 'text',
                        'text': prompt + '\n\nReturn ONLY valid JSON. No prose.',
                    }
                ]
            }]
        )

        raw = response.content[0].text.strip()
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()

        fields = json.loads(raw)

        # Parse expiry date if present
        expires_at = None
        for key in ['valid_until', 'end_date', 'expiry']:
            if fields.get(key):
                try:
                    from dateutil.parser import parse as parse_date
                    expires_at = parse_date(str(fields[key])).isoformat()
                except Exception:
                    pass
                break

        # Generate title
        title = (
            fields.get('insurance_company') or
            fields.get('sender') or
            fields.get('contract_type') or
            req.doc_type.replace('_', ' ').title()
        )

        # Save to lg_documents
        sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        sb.table('lg_documents').insert({
            'user_id': req.user_id,
            'type': req.doc_type,
            'title': title,
            'extracted_fields': fields,
            'source': 'upload',
            'storage_path': req.storage_path,
            'expires_at': expires_at,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }).execute()

        return ExtractedDocument(
            doc_type=req.doc_type,
            title=title,
            extracted_fields=fields,
            expires_at=expires_at,
            confidence='high',
            summary=f'Extracted {len(fields)} fields from {req.doc_type.replace("_", " ")}',
        )

    except Exception as e:
        # Save failed extraction attempt
        try:
            sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
            sb.table('lg_documents').insert({
                'user_id': req.user_id,
                'type': req.doc_type,
                'extracted_fields': {'error': str(e)[:200]},
                'source': 'upload',
                'storage_path': req.storage_path,
                'created_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception:
            pass

        return ExtractedDocument(
            doc_type=req.doc_type,
            extracted_fields={},
            confidence='low',
            summary=f'Extraction failed: {str(e)[:100]}',
        )
