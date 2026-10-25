from pydantic import ValidationError


class ConfigError(Exception):
    """Configuration is missing or invalid. The message is safe to show to the user."""


def describe(error: ValidationError) -> list[str]:
    """One line per problem. Never includes the offending value, which may be a secret."""
    problems = error.errors(include_input=False, include_url=False)
    return [f"{'.'.join(str(part) for part in p['loc'])}: {p['msg']}" for p in problems]
