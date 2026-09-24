"""Helpers for classifying OpenAI service errors without inventing replies."""
import re


_QUOTA_OR_UNAVAILABLE_PATTERNS = (
    "429", "resource_exhausted", "quota", "rate limit",
    "503", "unavailable", "high demand", "overloaded",
    "404", "model not found", "not found for api version",
    "403", "permission_denied", "permission denied",
    "timeout", "timed out", "deadline exceeded",
)


def is_quota_or_unavailable_error(error: Exception) -> bool:
    message = str(error).lower()
    return any(pattern in message for pattern in _QUOTA_OR_UNAVAILABLE_PATTERNS)


def strip_raw_error_artifacts(text: str) -> str:
    """Remove recognizable provider error dictionaries from non-advisory text."""
    return re.sub(r"\{[^{}]*'status':\s*'[A-Z_]+'[^{}]*\}", "[technical details omitted]", text)
