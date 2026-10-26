from speech_to_sheets.extract.inputs import ExtractionInput, Turn
from speech_to_sheets.pipeline import texts
from speech_to_sheets.pipeline.bundle import Bundle, bundle
from speech_to_sheets.slack.message import Message, SlackFile
from tests.pipeline_world import RECEIPT, FakeFiles

VOICE = SlackFile("clip", "audio/mp4", "slack_audio", 1000, "https://files.slack.com/clip")
PHOTO = SlackFile("img", "image/jpeg", "", 1000, "https://files.slack.com/img")


def sent(ts: str, text: str = "", files: tuple = (), bot: bool = False) -> Message:
    return Message("D1", ts, "UBOT" if bot else "U1", text, from_bot=bot, files=files)


def test_the_whole_thread_in_order_with_photos_and_transcripts() -> None:
    thread = [
        sent("1", "lunch", (PHOTO,)),
        sent("2", "How much?", bot=True),
        sent("3", "", (VOICE,)),
    ]
    files = FakeFiles({PHOTO.url: RECEIPT, VOICE.url: "twelve fifty"})
    assert bundle(thread, thread[-1], files) == Bundle(
        ExtractionInput(
            turns=(
                Turn("user", "lunch"),
                Turn("bot", "How much?"),
                Turn("user", "twelve fifty", voice=True),
            ),
            images=(RECEIPT,),
        )
    )


def test_the_newest_message_is_read_only_once() -> None:
    thread = [sent("1", "", (VOICE,))]
    files = FakeFiles({VOICE.url: "lunch 12"})
    bundle(thread, thread[0], files)
    assert files.read == [VOICE.url], "a voice note is transcribed once per message"


def test_when_the_newest_message_has_nothing_to_read_nothing_else_is_downloaded() -> None:
    thread = [sent("1", "", (PHOTO,)), sent("2", "How much?", bot=True), sent("3", "", (VOICE,))]
    files = FakeFiles({PHOTO.url: RECEIPT, VOICE.url: None})
    result = bundle(thread, thread[-1], files)
    assert result.unusable == texts.NO_SPEECH
    assert files.read == [VOICE.url]


def test_text_is_trimmed_and_empty_bot_messages_are_left_out() -> None:
    thread = [sent("1", "  lunch 12 \n"), sent("2", "", bot=True)]
    result = bundle(thread, thread[0], FakeFiles({}))
    assert result.request.turns == (Turn("user", "lunch 12"),)
