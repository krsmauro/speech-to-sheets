from speech_to_sheets.extract.schema import Complete, NeedsInfo, Result


def check(result: Result, categories: list[str]) -> Result:
    """Checks in code after Claude. Anything suspicious becomes a question, never a row."""
    if not isinstance(result, Complete):
        return result
    if result.category not in categories:
        return NeedsInfo(f"Which category is this? Options: {', '.join(categories)}")
    if result.amount <= 0:
        return NeedsInfo("How much was it? The amount must be more than zero.")
    return result
