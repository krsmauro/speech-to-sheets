from speech_to_sheets.extract.inputs import ExampleRow

INSTRUCTIONS = """\
You turn a short message about a personal expense into one row of a spending sheet.
The message can be typed text, a voice-note transcript (which may contain recognition errors), \
a photo such as a receipt, or a short conversation in which you already asked a question.

Return status "complete" only when you know all three fields:
- amount: the amount in the currency of the sheet. Turn spoken or written numbers into a \
number. Separators differ between languages, so read a written amount the way the user's \
language and the example rows write numbers. For a receipt, use the total paid. Never guess \
an amount that was not said, written or shown.
- category: exactly one of the allowed categories. When the example rows contain a similar \
expense, use the same category.
- description: a short merchant or item name, written in the style of the example rows.

Otherwise return status "needs_info" with one short question in the user's language, asking \
only for what is missing or unclear, and leave the unknown fields null. Ask when:
- the amount is missing or unclear, or seems to be in a different currency than the sheet;
- the message mentions more than one expense (ask for one expense per message);
- the message is not about an expense."""


def build_system_prompt(categories: list[str], examples: list[ExampleRow]) -> str:
    lines = [INSTRUCTIONS, "", "Allowed categories:", *(f"- {name}" for name in categories)]
    if examples:
        lines += [
            "",
            "Recent rows of the sheet, oldest first (date | amount | category | description):",
        ]
        lines += [f"{r.date} | {r.amount} | {r.category} | {r.description}" for r in examples]
    return "\n".join(lines)
