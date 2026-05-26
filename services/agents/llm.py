"""
LLM client factory.
Uses Amazon Bedrock if AWS credentials are available, falls back to Anthropic API.
Region: eu-central-1 — uses EU cross-region inference prefixes (eu.amazon.nova-*, eu.anthropic.claude-*)
"""
import os
import anthropic


def get_client() -> anthropic.AnthropicBedrock | anthropic.Anthropic:
    if os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY'):
        return anthropic.AnthropicBedrock(
            aws_region=os.getenv('AWS_DEFAULT_REGION', 'eu-central-1'),
        )
    return anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


# Model IDs — EU Bedrock cross-region inference
# Nova models: eu.amazon.nova-{micro,lite,pro}-v1:0
# Claude fallback: eu.anthropic.claude-haiku-4-5-20251001-v1:0
ROUTING_MODEL = os.getenv('CHIEF_ROUTING_MODEL', 'eu.amazon.nova-micro-v1:0')
AGENT_MODEL = os.getenv('CHIEF_AGENT_MODEL', 'eu.amazon.nova-lite-v1:0')
BRIEF_MODEL = os.getenv('CHIEF_BRIEF_MODEL', 'eu.amazon.nova-pro-v1:0')
