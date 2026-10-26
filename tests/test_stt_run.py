import sys

import pytest

from speech_to_sheets.stt.errors import SttError
from speech_to_sheets.stt.run import run_tool

PY = sys.executable


def python(code: str, *args: str) -> list[str]:
    return [PY, "-c", code, *args]


def test_returns_stdout_decoded_as_utf8() -> None:
    code = "import sys; sys.stdout.buffer.write('caf\\u00e9 ok'.encode())"
    assert run_tool(python(code), 10, "stt.x") == "café ok"


def test_arguments_are_not_interpreted_by_a_shell() -> None:
    risky = "$(echo hacked); rm -rf x"
    assert run_tool(python("import sys; print(sys.argv[1])", risky), 10, "stt.x") == risky + "\n"


def test_invalid_utf8_is_replaced_not_fatal() -> None:
    code = "import sys; sys.stdout.buffer.write(b'caf\\xe9')"
    assert run_tool(python(code), 10, "stt.x").startswith("caf")


def test_non_zero_exit_reports_the_end_of_stderr() -> None:
    command = python("import sys; sys.stderr.write('x' * 2000 + 'boom'); sys.exit(3)")
    with pytest.raises(SttError, match=r"exit code 3: x+boom$") as caught:
        run_tool(command, 10, "stt.x")
    assert len(str(caught.value).removeprefix(PY)) < 600, "the tool's path may be any length"


def test_error_lines_are_picked_out_of_noisy_stderr() -> None:
    noise = "backend: loaded\n" + "error: input file not found 'x.wav'\n" + "usage: ...\n" * 200
    command = python("import sys; sys.stderr.write(sys.argv[1]); sys.exit(2)", noise)
    with pytest.raises(SttError) as caught:
        run_tool(command, 10, "stt.x")
    assert str(caught.value).endswith("exit code 2: error: input file not found 'x.wav'")


def test_missing_binary_names_the_setting_to_fix() -> None:
    with pytest.raises(SttError, match="check stt.whisper_cli"):
        run_tool(["no-such-tool-for-speech-to-sheets"], 10, "stt.whisper_cli")


def test_timeout_says_which_setting_to_raise() -> None:
    command = python("import time; time.sleep(10)")
    with pytest.raises(SttError, match="stt.timeout_seconds"):
        run_tool(command, 0.2, "stt.x")
