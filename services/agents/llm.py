"""
LLM client factory.
Uses Amazon Bedrock if AWS credentials are available, falls back to Anthropic API.
"""
import os
import anthropic


def get_client() -> anthropic.AnthropicBedrock | anthropic.Anthropic:
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        return anthropic.AnthropicBedrock()
    return anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


# Model IDs — Bedrock versions preferred, Anthropic fallback
ROUTING_MODEL = os.getenv('CHIEF_ROUTING_MODEL', 'us.amazon.nova-micro-v1:0')
AGENT_MODEL = os.getenv('CHIEF_AGENT_MODEL', 'us.amazon.nova-lite-v1:0')
BRIEF_MODEL = os.getenv('CHIEF_BRIEF_MODEL', 'us.amazon.nova-pro-v1:0')
