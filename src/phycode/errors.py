"""PhyCode exceptions."""

from __future__ import annotations


class PhyCodeError(Exception):
    """Base exception for all PhyCode errors."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class PathEscapeError(PhyCodeError):
    """Raised when a path operation escapes the allowed workspace root."""

    def __init__(
        self,
        message: str,
        requested: str | None = None,
        root: str | None = None,
    ) -> None:
        super().__init__(message)
        self.requested = requested
        self.root = root


class ConfigError(PhyCodeError):
    """Raised when configuration loading or parsing fails."""

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause
