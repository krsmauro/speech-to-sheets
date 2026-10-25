import anthropic
from pydantic import ValidationError

from speech_to_sheets.extract.content import build_user_content
from speech_to_sheets.extract.errors import ExtractError, describe_api_error
from speech_to_sheets.extract.inputs import ExampleRow, ExtractionInput
from speech_to_sheets.extract.prompt import build_system_prompt
from speech_to_sheets.extract.schema import Result, build_output_model, to_result

# A cap, not a target: room for low-effort thinking plus a short JSON answer.
MAX_TOKENS = 16000
# Haiku 5.5 defaults to medium effort with thinking on; this task is simple.
EFFORT = "low"


def make_client(api_key: str) -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=2)


def extract(
    client: anthropic.Anthropic,
    request: ExtractionInput,
    categories: list[str],
    examples: list[ExampleRow],
    model: str,
) -> Result:
    """Ask Claude for one sheet row. Raises ExtractError with a message safe to show."""
    output_model = build_output_model(categories)
    output_format = {"type": "json_schema", "schema": output_model.model_json_schema()}
    try:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=build_system_prompt(categories, examples),
            messages=[{"role": "user", "content": build_user_content(request)}],
            output_config={"effort": EFFORT, "format": output_format},
        )
    except anthropic.APIError as error:
        raise ExtractError(describe_api_error(error)) from None
    try:
        return to_result(output_model.model_validate_json(_answer_text(response)))
    except ValidationError:
        raise ExtractError("Claude's answer did not match the expected format") from None


def _answer_text(response: anthropic.types.Message) -> str:
    # Check the stop reason first: after a refusal or a cut-off the text may not be valid JSON.
    if response.stop_reason == "refusal":
        raise ExtractError("Claude declined to process this message")
    if response.stop_reason == "max_tokens":
        raise ExtractError("Claude's answer was cut off before it finished")
    # Read blocks by type: with thinking on, the answer comes after thinking blocks.
    text = "".join(block.text for block in response.content if block.type == "text")
    if not text:
        raise ExtractError("Claude returned no answer")
    return text
