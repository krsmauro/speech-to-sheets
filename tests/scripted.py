from speech_to_sheets.cli.prompts import Prompter


class Script:
    """Scripted answers for a Prompter. Records every question asked and every line said."""

    def __init__(self, *answers: str) -> None:
        self.answers = list(answers)
        self.questions: list[str] = []
        self.said: list[str] = []
        self.prompter = Prompter(self._read, self.said.append)

    def _read(self, question: str) -> str:
        self.questions.append(question)
        if not self.answers:
            raise EOFError(f"no scripted answer for: {question}")
        return self.answers.pop(0)

    @property
    def output(self) -> str:
        return "\n".join(self.said)
