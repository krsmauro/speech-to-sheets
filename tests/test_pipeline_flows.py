from pathlib import Path

from tests.fake_anthropic import answer
from tests.fake_dm import LATE_EVENING
from tests.pipeline_world import (
    ASK_AMOUNT,
    MARKET,
    PHOTO_URL,
    RECEIPT,
    VOICE_URL,
    World,
    photo,
    voice,
)

HOUR = 3600


def test_a_text_message_is_logged_and_confirmed(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET)
    event = world.send("market 12.50")
    assert world.conversation() == "Conversation, oldest first:\nUser: market 12.50"
    assert world.replies == ["Logged in row 4: 14/1/2025 | $12.50 | Food | Market"]
    assert world.new_rows() == [4]
    assert world.status(event) == ("done", 4)


def test_the_confirmation_shows_the_row_as_the_sheet_stores_it(tmp_path: Path) -> None:
    # Claude answered 12.5 and no date; only the sheet's own formats make $12.50 and 14/1/2025.
    world = World(tmp_path, MARKET)
    world.send("market 12.50")
    assert world.sheet.cells[(4, 1)] == 45671  # the serial number written for 2025-01-14
    [confirmation] = world.replies
    assert "14/1/2025 | $12.50" in confirmation
    assert "12.5 " not in confirmation
    assert "2025-01-14" not in confirmation


def test_a_voice_note_reaches_claude_as_a_transcript(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET, files={VOICE_URL: "twelve fifty at the market"})
    world.send(files=(voice(),))
    assert "User (voice note transcript): twelve fifty at the market" in world.conversation()
    assert world.replies[0].startswith("Logged in row 4:")


def test_a_photo_alone_reaches_claude_as_an_image(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET, files={PHOTO_URL: RECEIPT})
    world.send(files=(photo(),))
    image, text = world.claude.calls[0]["messages"][0]["content"]
    assert image["source"]["media_type"] == "image/jpeg"
    assert "only the attached image" in text["text"]
    assert world.replies[0].startswith("Logged in row 4:")


def test_claude_gets_the_categories_and_last_rows_of_the_sheet(tmp_path: Path) -> None:
    world = World(tmp_path, MARKET)
    world.send("market 12.50")
    system = world.claude.calls[0]["system"]
    assert "- Food\n- Transport\n- Pets" in system
    assert "15/3/2023 | $45.20 | Food | Bakery" in system


def test_today_is_the_day_the_thread_started_in_the_sheet_timezone(tmp_path: Path) -> None:
    # Sent at 23:30 in Panama (already the 15th in UTC) and answered the next morning.
    world = World(tmp_path, ASK_AMOUNT, MARKET)
    first = world.send("market", at=LATE_EVENING)
    world.send("12.50", reply_to=first, at=LATE_EVENING + 10 * HOUR)
    for call in world.claude.calls:
        assert "Today is Tuesday 2025-01-14." in call["system"]
    assert world.replies[-1].startswith("Logged in row 4: 14/1/2025")


def test_a_date_claude_read_is_the_one_written(tmp_path: Path) -> None:
    friday = answer(status="complete", amount=40, category="Pets", description="Vet")
    world = World(tmp_path, {**friday, "date": "2025-01-10"})
    world.send("on Friday, forty dollars at the vet")
    assert world.replies == ["Logged in row 4: 10/1/2025 | $40.00 | Pets | Vet"]


def test_a_date_after_the_day_it_was_sent_asks_instead_of_writing(tmp_path: Path) -> None:
    world = World(tmp_path, {**MARKET, "date": "2025-01-20"})
    event = world.send("market 12.50 on the 20th")
    assert world.replies == [
        "Which day was this? I read 2025-01-20, and I can only log expenses up to today."
    ]
    assert world.new_rows() == []
    assert world.status(event) == ("pending", None)
