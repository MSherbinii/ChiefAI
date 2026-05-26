"""
Voice intent classifier for Chief.
Adapted from Jarvis voice-intent-classifier.ts.

Single cheap LLM call (Haiku) that classifies raw STT transcript
into a structured Intent before routing to the correct agent.

Failure modes are swallowed — any error returns a permissive fallback
that routes to Chief orchestrator. Voice still works even if classifier fails.
"""
import os
import json
from typing import Optional, Literal, get_args
from pydantic import BaseModel, Field
from llm import get_client, ROUTING_MODEL

# Chief's domains (rooms in Jarvis terminology)
Domain = Literal['health', 'communication', 'projects', 'finance', 'admin', 'general']
Verb = Literal['ask', 'log', 'draft', 'create', 'update', 'delete', 'analyze', 'unknown']
Impact = Literal['read', 'write', 'external']

VALID_DOMAINS = set(get_args(Domain))
VALID_VERBS = set(get_args(Verb))
VALID_IMPACTS = set(get_args(Impact))

# Which domain maps to which Chief agent
DOMAIN_TO_AGENT = {
    'health': 'Pulse',
    'communication': 'Echo',
    'projects': 'Forge',
    'finance': 'Ledger',
    'admin': 'Clerk',
    'general': 'Chief',
}

CLASSIFIER_SYSTEM = """You are a voice intent classifier for Chief, a personal life OS.

Given a user's voice transcript, return a single JSON object. Output JSON only — no prose, no code fences.

Schema:
{
  "verb": "ask" | "log" | "draft" | "create" | "update" | "delete" | "analyze" | "unknown",
  "domain": "health" | "communication" | "projects" | "finance" | "admin" | "general",
  "impact": "read" | "write" | "external",
  "subject": "brief string describing what the user wants",
  "confidence": 0.0 to 1.0
}

Domain rules:
- health: anything about recovery, sleep, gym, workout, food, calories, WHOOP, training
- communication: email, reply, professor, thesis supervisor, message, thread, follow-up, draft, write email, compose, send to, inbox, gmail
- projects: thesis, GitHub, commit, deadline, startup, code, repo, Notion
- finance: spending, bank, subscription, afford, budget, salary, Revolut, Sparkasse
- admin: insurance, letter, form, appointment, bureaucracy, TK, document
- general: greetings, general questions, cross-domain

Verb rules:
- log: user is recording something that happened (trained, ate, spent)
- draft: user wants a draft created (email, reply)
- ask: user wants information or analysis
- create: user wants to create something new
- analyze: user wants insight or pattern analysis
- unknown: unclear

Impact rules:
- read: no side effects, information retrieval only
- write: creates or modifies local data (log, create, update)
- external: reaches external services (email, message)

Confidence guidance:
- 0.9+: utterance is clear and unambiguous
- 0.7-0.89: confident, minor ambiguity
- 0.5-0.69: plausibly two readings
- <0.5: unclear, garbled, or cross-domain

Examples:
- "I trained chest today, bench 100kg for 5" -> verb=log, domain=health, impact=write, confidence=0.97
- "What should I train today?" -> verb=ask, domain=health, impact=read, confidence=0.95
- "Draft a reply to my professor" -> verb=draft, domain=communication, impact=external, confidence=0.93
- "How much did I spend this week?" -> verb=ask, domain=finance, impact=read, confidence=0.95
- "I need to push a commit before the deadline" -> verb=ask, domain=projects, impact=read, confidence=0.88
- "Remind me to call the insurance" -> verb=create, domain=admin, impact=write, confidence=0.90
- "Good morning" -> verb=ask, domain=general, impact=read, confidence=0.95
- "Can you draft a reply to my professor about thesis progress?" → verb=draft, domain=communication, impact=write
- "Write an email to my supervisor" → verb=draft, domain=communication, impact=write
- "Reply to my professor" → verb=draft, domain=communication, impact=write"""


class VoiceIntent(BaseModel):
    verb: Verb = 'unknown'
    domain: Domain = 'general'
    impact: Impact = 'read'
    subject: str = ''
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    routed_to: str = 'Chief'  # which agent handles this


FALLBACK_INTENT = VoiceIntent(
    verb='ask',
    domain='general',
    impact='read',
    subject='general query',
    confidence=0.5,
    routed_to='Chief',
)


def classify_voice_intent(transcript: str, conversation_context: str = '') -> VoiceIntent:
    """
    Classify a voice transcript into a structured intent.
    Uses cheapest routing model (Haiku). Falls back gracefully on any error.
    """
    if not transcript or not transcript.strip():
        return FALLBACK_INTENT

    try:
        client = get_client()

        user_content = f'Voice transcript: "{transcript.strip()}"'
        if conversation_context:
            user_content += f'\n\nRecent context: {conversation_context[:300]}'

        response = client.messages.create(
            model=ROUTING_MODEL,
            max_tokens=150,
            system=CLASSIFIER_SYSTEM,
            messages=[{'role': 'user', 'content': user_content}],
        )

        raw = response.content[0].text.strip()
        # Strip markdown fences if present
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()

        data = json.loads(raw)

        raw_verb = data.get('verb', 'unknown')
        raw_domain = data.get('domain', 'general')
        raw_impact = data.get('impact', 'read')

        intent = VoiceIntent(
            verb=raw_verb if raw_verb in VALID_VERBS else 'unknown',
            domain=raw_domain if raw_domain in VALID_DOMAINS else 'general',
            impact=raw_impact if raw_impact in VALID_IMPACTS else 'read',
            subject=str(data.get('subject', ''))[:100],
            confidence=min(max(float(data.get('confidence', 0.5)), 0.0), 1.0),
        )
        intent.routed_to = DOMAIN_TO_AGENT.get(intent.domain, 'Chief')
        return intent

    except Exception:
        # CRITICAL: classifier failure must NOT break voice flow
        return FALLBACK_INTENT


def intent_to_routing_hint(intent: VoiceIntent) -> str:
    """
    Convert a classified intent to a routing hint for the orchestrator.
    Returns the agent name that should handle this message.

    Low confidence (< 0.6) falls back to Chief orchestrator to decide,
    consistent with Jarvis's confidence band routing.
    """
    if intent.confidence < 0.6:
        return 'Chief'
    return intent.routed_to
