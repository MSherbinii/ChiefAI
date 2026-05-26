"""
PydanticAI agent factory for structured outputs.
Wraps the Bedrock/Anthropic client in PydanticAI Agent for type-safe, validated responses.

PydanticAI version: 1.102.0+
Bedrock support: pydantic_ai.models.bedrock.BedrockConverseModel
  - model_name accepts any string (BedrockModelName is Union[str, Literal[...]])
  - region_name passed via a custom boto3 session (provider kwarg)
"""
import os
from typing import TypeVar, Type

from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


def _build_model(model_id: str):
    """
    Return a PydanticAI model object.

    Priority:
    1. BedrockConverseModel via BedrockProvider when AWS credentials are present.
    2. AnthropicModel via AnthropicProvider with direct API key as fallback.
    """
    has_bedrock = bool(
        os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')
    )

    if has_bedrock:
        try:
            from pydantic_ai.models.bedrock import BedrockConverseModel
            from pydantic_ai.providers.bedrock import BedrockProvider

            provider = BedrockProvider(
                aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
                aws_session_token=os.getenv('AWS_SESSION_TOKEN'),
                region_name=os.getenv('AWS_DEFAULT_REGION', 'eu-central-1'),
            )
            return BedrockConverseModel(model_name=model_id, provider=provider)
        except Exception:
            # Bedrock unavailable — fall through to direct Anthropic
            pass

    # Direct Anthropic API fallback
    import anthropic
    from pydantic_ai.models.anthropic import AnthropicModel
    from pydantic_ai.providers.anthropic import AnthropicProvider

    provider = AnthropicProvider(
        anthropic_client=anthropic.AsyncAnthropic(
            api_key=os.getenv('ANTHROPIC_API_KEY')
        )
    )
    return AnthropicModel(model_id, provider=provider)


def create_pydantic_agent(
    result_type: Type[T],
    system_prompt: str,
    model_name: str = None,
):
    """
    Create a PydanticAI Agent configured for structured output.

    Args:
        result_type: Pydantic model class to validate the response against.
        system_prompt: Agent system prompt (context is appended later at run time).
        model_name: Override model ID; defaults to CHIEF_AGENT_MODEL env var.

    Returns:
        pydantic_ai.Agent instance ready for `await agent.run(user_message)`.
    """
    from pydantic_ai import Agent

    model_id = model_name or os.getenv(
        'CHIEF_AGENT_MODEL', 'eu.anthropic.claude-haiku-4-5-20251001-v1:0'
    )
    model = _build_model(model_id)
    return Agent(model, output_type=result_type, system_prompt=system_prompt)


async def run_structured(
    result_type: Type[T],
    system_prompt: str,
    user_message: str,
    context: str = '',
    model_name: str = None,
) -> T:
    """
    Run a PydanticAI agent and return a validated structured result.

    Falls back to raw LLM + JSON parsing if PydanticAI fails, and to a
    field-defaults instance as a last resort so callers always receive a
    properly-typed object — never an exception.

    Args:
        result_type: Pydantic model class for the response.
        system_prompt: Base system prompt for the agent.
        user_message: The user's query.
        context: Optional runtime context appended to the system prompt.
        model_name: Override model ID.

    Returns:
        An instance of result_type.
    """
    full_system = f'{system_prompt}\n\n{context}' if context else system_prompt

    try:
        agent = create_pydantic_agent(result_type, full_system, model_name)
        result = await agent.run(user_message)
        return result.response
    except Exception:
        pass  # Try raw-LLM fallback

    # Fallback 1: raw LLM call with explicit JSON instruction
    try:
        import json
        from llm import get_client, AGENT_MODEL

        client = get_client()
        schema_str = result_type.model_json_schema()
        response = client.messages.create(
            model=AGENT_MODEL,
            max_tokens=512,
            system=(
                full_system
                + '\n\nReturn ONLY valid JSON matching this schema (no prose, no markdown):\n'
                + str(schema_str)
            ),
            messages=[{'role': 'user', 'content': user_message}],
        )

        raw = response.content[0].text.strip()
        # Strip optional ```json ... ``` fences
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()

        data = json.loads(raw)
        return result_type(**data)
    except Exception:
        pass  # Try minimal-defaults fallback

    # Fallback 2: construct a minimal valid instance using field defaults / type hints
    import typing

    fields = result_type.model_fields
    defaults: dict = {}
    for name, field in fields.items():
        if field.default is not None and field.default is not field.PydanticUndefined:
            defaults[name] = field.default
        elif field.default_factory is not None:  # type: ignore[misc]
            defaults[name] = field.default_factory()  # type: ignore[misc]
        else:
            # Infer a sensible zero value from the annotation
            ann = field.annotation
            origin = getattr(ann, '__origin__', None)
            if ann is str or ann == 'str':
                defaults[name] = 'Unable to generate structured response'
            elif ann is int or ann == 'int':
                defaults[name] = 0
            elif ann is float or ann == 'float':
                defaults[name] = 0.0
            elif ann is bool or ann == 'bool':
                defaults[name] = False
            elif origin is list or ann is list:
                defaults[name] = []
            elif origin is dict or ann is dict:
                defaults[name] = {}
            # Optional[X] — leave absent so Pydantic uses its own default=None
    return result_type(**defaults)
