"""Clean, user-facing request errors (no stack traces)."""


class RequestError(ValueError):
    """The request itself is empty, malformed or garbage. Carries a plain message."""
