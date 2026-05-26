"""
Multi-provider LLM strategy — adapted from Jarvis src/llm/provider.ts.

Jarvis defines an LLMProvider interface with chat() + stream() + listModels()
and an LLMManager that wraps a single active provider. Chief's version is
simpler (no streaming interface yet) but follows the same priority logic:

  Priority: Bedrock (if AWS creds present) → Anthropic direct (if API key) → RuntimeError

Key Jarvis patterns preserved:
  • Provider detection at call-time (not import-time) so env vars can be
    injected after module load (test fixtures, Lambda cold starts, etc.)
  • Error classification into canonical buckets (auth / rate_limit / network /
    bad_request / not_found / server / unknown) — mirrors classifyHttpStatus()
    and classifyErrorString() from provider.ts
  • Task-specific model selection: 'routing' uses Haiku, 'brief' uses Sonnet,
    'agent' defaults to Haiku (Jarvis: LLMManager selects model per request)
"""
from __future__ import annotations

import os
import re
from typing import Literal, Optional, Tuple

import anthropic

# ---------------------------------------------------------------------------
# Error classification (adapted from Jarvis provider.ts)
# ---------------------------------------------------------------------------

LLMErrorCode = Literal[
    'auth',         # 401 / 403, invalid API key
    'rate_limit',   # 429, quota exhausted
    'network',      # 502/503/504, timeout, connection refused
    'bad_request',  # 400/422, invalid parameters
    'not_found',    # 404, model not found
    'server',       # generic 5xx
    'unknown',
]


def classify_http_status(status: int) -> LLMErrorCode:
    """Map an HTTP status code to a canonical error bucket."""
    if status in (401, 403):
        return 'auth'
    if status == 429:
        return 'rate_limit'
    if status == 404:
        return 'not_found'
    if status in (400, 422):
        return 'bad_request'
    if status in (502, 503, 504):
        return 'network'
    if status >= 500:
        return 'server'
    return 'unknown'


def classify_error_string(raw: Optional[str]) -> LLMErrorCode:
    """
    Classify an error from its message string when the HTTP status is not
    available. Uses word-boundary regexes to avoid digit false-positives.
    Mirrors Jarvis provider.ts classifyErrorString().
    """
    if not raw:
        return 'unknown'
    s = raw.lower()

    if (
        re.search(r'\b401\b', s) or re.search(r'\b403\b', s)
        or 'unauthorized' in s or 'api key' in s
        or 'invalid_api_key' in s or 'authentication' in s
    ):
        return 'auth'

    if (
        re.search(r'\b429\b', s)
        or 'rate limit' in s or 'too many requests' in s
        or 'quota' in s or 'insufficient_quota' in s
    ):
        return 'rate_limit'

    if (
        re.search(r'\b(502|503|504)\b', s)
        or 'timeout' in s or 'temporarily unavailable' in s
        or 'connection refused' in s or 'network' in s
    ):
        return 'network'

    if (
        re.search(r'\b404\b', s)
        or 'not found' in s or 'model_not_found' in s
    ):
        return 'not_found'

    if (
        re.search(r'\b(400|422)\b', s)
        or 'bad request' in s or 'invalid_request' in s
    ):
        return 'bad_request'

    if re.search(r'\b5\d\d\b', s) or 'internal server error' in s:
        return 'server'

    return 'unknown'


# ---------------------------------------------------------------------------
# Model ID tables
# ---------------------------------------------------------------------------

# EU Bedrock cross-region inference model IDs
BEDROCK_MODELS: dict[str, str] = {
    'routing': os.getenv('CHIEF_ROUTING_MODEL', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'),
    'agent':   os.getenv('CHIEF_AGENT_MODEL',   'eu.anthropic.claude-haiku-4-5-20251001-v1:0'),
    'brief':   os.getenv('CHIEF_BRIEF_MODEL',   'eu.anthropic.claude-sonnet-4-5-20250929-v1:0'),
}

# Anthropic direct API model IDs
ANTHROPIC_MODELS: dict[str, str] = {
    'routing': 'claude-haiku-4-5-20251001',
    'agent':   'claude-haiku-4-5-20251001',
    'brief':   'claude-sonnet-4-6',
}


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

ProviderName = Literal['bedrock', 'anthropic']


def get_client_with_fallback(
    model_override: Optional[str] = None,
) -> Tuple[anthropic.AnthropicBedrock | anthropic.Anthropic, ProviderName]:
    """
    Return (client, provider_name) for the best available LLM provider.

    Priority (mirrors Jarvis LLMManager provider selection):
      1. Amazon Bedrock  — if AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY present
      2. Anthropic direct — if ANTHROPIC_API_KEY present
      3. RuntimeError    — no credentials configured

    Usage::

        client, provider = get_client_with_fallback()
        model = get_model_id('agent')
        response = client.messages.create(model=model, max_tokens=1024, ...)
    """
    has_bedrock = bool(
        os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    has_anthropic = bool(os.getenv('ANTHROPIC_API_KEY'))

    if has_bedrock:
        client = anthropic.AnthropicBedrock(
            aws_region=os.getenv('AWS_DEFAULT_REGION', 'eu-central-1'),
        )
        return client, 'bedrock'

    if has_anthropic:
        client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        return client, 'anthropic'

    raise RuntimeError(
        'No LLM provider configured. '
        'Set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY for Bedrock '
        'or ANTHROPIC_API_KEY for direct API access.'
    )


def get_model_id(task: str) -> str:
    """
    Return the correct model ID for a given task type on the active provider.

    Task types:
      'routing' — fast classification (Haiku)
      'agent'   — standard agent response (Haiku)
      'brief'   — deep synthesis / morning brief (Sonnet)

    Mirrors Jarvis's per-request model selection in LLMManager.
    """
    has_bedrock = bool(
        os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')
    )
    models = BEDROCK_MODELS if has_bedrock else ANTHROPIC_MODELS
    return models.get(task, models['agent'])


# ---------------------------------------------------------------------------
# Convenience re-export matching Chief's existing llm.py interface
# ---------------------------------------------------------------------------

def get_client() -> anthropic.AnthropicBedrock | anthropic.Anthropic:
    """
    Drop-in replacement for llm.get_client().
    New code should prefer get_client_with_fallback() to also get the
    provider name for logging / model selection.
    """
    client, _ = get_client_with_fallback()
    return client
