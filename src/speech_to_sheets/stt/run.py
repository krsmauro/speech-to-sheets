import subprocess

from speech_to_sheets.stt.errors import SttError

STDERR_TAIL = 500


def run_tool(command: list[str], timeout: float, setting: str) -> str:
    """Run an external tool without a shell and return its stdout.

    `setting` is the config key that names the tool, so error messages say what to fix.
    """
    name = command[0]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except OSError as error:
        raise SttError(f"cannot run {name} ({error.strerror}); check {setting}") from None
    except subprocess.TimeoutExpired:
        raise SttError(f"{name} took longer than {timeout} s; raise stt.timeout_seconds") from None
    if result.returncode != 0:
        detail = _error_lines(result.stderr)[-STDERR_TAIL:]
        raise SttError(f"{name} failed with exit code {result.returncode}: {detail}")
    return result.stdout


def _error_lines(stderr: str) -> str:
    """The lines that start with "error", else all of stderr.

    whisper-cli prints its error between backend logs and the full help text, so a plain
    tail of stderr would show only help.
    """
    lines = [line.strip() for line in stderr.splitlines()]
    errors = [line for line in lines if line.lower().startswith("error")]
    return "\n".join(errors) if errors else stderr.strip()
