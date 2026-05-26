"""
LLM client factory.
Uses Amazon Bedrock if AWS credentials are available, falls back to Anthropic API.
Region: eu-central-1 — uses EU cross-region inference prefixes
# Claude models: eu.anthropic.claude-{haiku,sonnet}-{version}-v{n}:0
# Note: Amazon Nova models require boto3 directly (not compatible with AnthropicBedrock SDK wrapper)
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
# Claude models: eu.anthropic.claude-{haiku,sonnet}-{version}-v{n}:0
ROUTING_MODEL = os.getenv('CHIEF_ROUTING_MODEL', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0')
AGENT_MODEL = os.getenv('CHIEF_AGENT_MODEL', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0')
BRIEF_MODEL = os.getenv('CHIEF_BRIEF_MODEL', 'eu.anthropic.claude-sonnet-4-5-20250929-v1:0')
