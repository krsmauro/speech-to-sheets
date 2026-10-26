from collections.abc import Callable

# Returns what is wrong with an answer, or None when it is fine.
Check = Callable[[str], str | None]


class Prompter:
    """Questions on the terminal. Tests pass a scripted `read` and a collecting `write`."""

    def __init__(
        self, read: Callable[[str], str] = input, write: Callable[[str], None] = print
    ) -> None:
        self._read = read
        self.say = write

    def ask(self, question: str, default: str = "", check: Check | None = None) -> str:
        """Ask until the answer passes `check`. A blank answer takes the default."""
        suffix = f" [{default}]" if default else ""
        while True:
            answer = self._read(f"{question}{suffix}: ").strip() or default
            problem = check(answer) if check else None
            if problem is None:
                return answer
            self.say(problem)

    def confirm(self, question: str, default: bool) -> bool:
        hint = "Y/n" if default else "y/N"
        while True:
            answer = self._read(f"{question} [{hint}]: ").strip().casefold()
            if not answer:
                return default
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            self.say("Answer y or n.")

    def choose(self, question: str, options: list[str], default: int | None = None) -> int:
        """Show numbered options and return the index of the one picked."""
        for number, option in enumerate(options, 1):
            self.say(f"  {number}. {option}")

        def in_range(answer: str) -> str | None:
            if answer.isdecimal() and 1 <= int(answer) <= len(options):
                return None
            return f"Type a number from 1 to {len(options)}."

        shown = "" if default is None else str(default + 1)
        return int(self.ask(question, shown, in_range)) - 1
