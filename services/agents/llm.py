"""
LLM client factory.
Uses Amazon Bedrock if AWS credentials are available, falls back to Anthropic API.
Region: eu-central-1

Available models on Bedrock eu-central-1:
  ULTRA-CHEAP (routing/classification):
    zai.glm-4.7-flash           — Z.AI GLM-4 Flash (~50x cheaper than Haiku)
    amazon.nova-micro-v1:0      — Amazon Nova Micro (~20x cheaper, needs eu. prefix)
    meta.llama3-2-3b-instruct   — Meta Llama 3.2 3B (~100x cheaper)

  CHEAP + CAPABLE (agent responses):
    amazon.nova-lite-v1:0       — Amazon Nova Lite (~5x cheaper than Haiku)
    qwen.qwen3-32b-v1:0         — Alibaba Qwen3 32B (~10x cheaper than Haiku)
    eu.anthropic.claude-haiku-4-5-20251001-v1:0  — Claude Haiku (current default)

  QUALITY (synthesis, case discovery, Echo):
    qwen.qwen3-235b-a22b-2507-v1:0  — Alibaba Qwen3 235B MoE (~3x cheaper than Sonnet)
    eu.anthropic.claude-sonnet-4-6  — Claude Sonnet 4.6 (newest, best quality)
    eu.anthropic.claude-sonnet-4-5-20250929-v1:0  — Claude Sonnet 4.5 (current default)

Note: Amazon Nova + Anthropic cross-region models use eu. prefix.
      Qwen, GLM, Meta models use their base IDs in eu-central-1.
"""
import os
import anthropic


def get_client() -> anthropic.AnthropicBedrock | anthropic.Anthropic:
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        return anthropic.AnthropicBedrock(
            aws_region=os.getenv('AWS_DEFAULT_REGION', 'eu-central-1'),
        )
    return anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


def get_boto3_client():
    """Get raw boto3 bedrock-runtime client for non-Anthropic models (Qwen, GLM, Nova)."""
    import boto3
    return boto3.client(
        'bedrock-runtime',
        region_name=os.getenv('AWS_DEFAULT_REGION', 'eu-central-1'),
    )


async def invoke_cheap_model(prompt: str, model_id: str = None, max_tokens: int = 200) -> str:
    """
    Invoke a non-Anthropic Bedrock model via boto3 Converse API.
    Used for ultra-cheap routing and classification tasks.
    Falls back to Haiku if model unavailable.
    """
    import asyncio
    if model_id is None:
        model_id = ROUTING_MODEL_CHEAP

    try:
        bedrock = get_boto3_client()
        resp = bedrock.converse(
            modelId=model_id,
            messages=[{'role': 'user', 'content': [{'text': prompt}]}],
            inferenceConfig={'maxTokens': max_tokens},
        )
        return resp['output']['message']['content'][0]['text'].strip()
    except Exception:
        # Fallback to Anthropic Haiku
        client = get_client()
        resp = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=max_tokens,
            messages=[{'role': 'user', 'content': prompt}],
        )
        return resp.content[0].text.strip()


# ─── Model IDs ────────────────────────────────────────────────────────────────

# Ultra-cheap: for routing (just picks one word), entity type classification
ROUTING_MODEL_CHEAP = os.getenv('CHIEF_ROUTING_CHEAP', 'zai.glm-4.7-flash')

# Cheap + capable: for agent responses (Pulse, Forge, Ledger, Clerk, Scout)
AGENT_MODEL_CHEAP = os.getenv('CHIEF_AGENT_CHEAP', 'qwen.qwen3-32b-v1:0')

# Current defaults (Anthropic via Bedrock — keep for Echo + Brief which need Sonnet quality)
ROUTING_MODEL = os.getenv('CHIEF_ROUTING_MODEL', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0')
AGENT_MODEL = os.getenv('CHIEF_AGENT_MODEL', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0')
BRIEF_MODEL = os.getenv('CHIEF_BRIEF_MODEL', 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0')

# To switch to cheaper models, set env vars:
#   CHIEF_ROUTING_MODEL=zai.glm-4.7-flash
#   CHIEF_AGENT_MODEL=qwen.qwen3-32b-v1:0
#   CHIEF_BRIEF_MODEL=qwen.qwen3-235b-a22b-2507-v1:0
