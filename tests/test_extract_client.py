import base64
from datetime import date
from decimal import Decimal

from speech_to_sheets.extract.client import extract
from speech_to_sheets.extract.inputs import ExampleRow, ExtractionInput, Image, Turn
from speech_to_sheets.extract.schema import Complete, NeedsInfo
from tests.fake_anthropic import FakeClient, answer, reply

CATEGORIES = ["Food", "Transport"]
EXAMPLES = [ExampleRow("01/10/2026", "$45.20", "Food", "Market")]
TODAY = date(2026, 10, 25)
COMPLETE = answer(status="complete", amount=12.5, category="Food", description="Market")


def run(client: FakeClient, request: ExtractionInput) -> Complete | NeedsInfo:
    return extract(client, request, CATEGORIES, EXAMPLES, "claude-haiku-5-5", TODAY)


def text_input(text: str, voice: bool = False) -> ExtractionInput:
    return ExtractionInput(turns=(Turn("user", text, voice),))


def test_request_follows_haiku_5_5_rules() -> None:
    client = FakeClient(reply(COMPLETE))
    run(client, text_input("market 12.50"))
    call = client.calls[0]
    assert call["model"] == "claude-haiku-5-5"
    assert call["output_config"]["effort"] == "low"
    assert not {"temperature", "top_p", "top_k", "thinking"} & call.keys()
    assert [m["role"] for m in call["messages"]] == ["user"], "no assistant prefill"
    assert "- Transport" in call["system"] and "Market" in call["system"]
    assert "Today is Sunday 2026-10-25." in call["system"]


def test_category_enum_in_the_schema_comes_from_the_sheet() -> None:
    client = FakeClient(reply(COMPLETE))
    run(client, text_input("market 12.50"))
    output_format = client.calls[0]["output_config"]["format"]
    assert output_format["type"] == "json_schema"
    category = output_format["schema"]["properties"]["category"]["anyOf"][0]
    assert category["enum"] == CATEGORIES


def test_spoken_amount_transcript_reaches_claude_and_decimal_comes_back() -> None:
    client = FakeClient(reply(COMPLETE))
    result = run(client, text_input("twelve fifty at the market", voice=True))
    text = client.calls[0]["messages"][0]["content"][-1]["text"]
    assert "User (voice note transcript): twelve fifty at the market" in text
    assert result == Complete(Decimal("12.5"), "Food", "Market", TODAY)


def test_missing_amount_becomes_a_question() -> None:
    question = answer(status="needs_info", category="Food", question="How much was it?")
    result = run(FakeClient(reply(question)), text_input("lunch"))
    assert result == NeedsInfo("How much was it?")


def test_image_is_sent_before_the_text() -> None:
    client = FakeClient(reply(COMPLETE))
    receipt = Image("image/jpeg", b"\xff\xd8 not a real photo")
    run(client, ExtractionInput(images=(receipt,)))
    image_block, text_block = client.calls[0]["messages"][0]["content"]
    assert image_block["source"]["media_type"] == "image/jpeg"
    assert base64.b64decode(image_block["source"]["data"]) == receipt.data
    assert "only the attached image" in text_block["text"]


def test_a_date_claude_read_replaces_today() -> None:
    receipt_day = answer(
        status="complete", amount=12.5, category="Food", description="Market", date="2026-10-22"
    )
    result = run(FakeClient(reply(receipt_day)), text_input("market 12.50 on Thursday"))
    assert result == Complete(Decimal("12.5"), "Food", "Market", date(2026, 10, 22))
