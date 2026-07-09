"""Regex patterns for dangerous shell commands."""

from __future__ import annotations

import re
from re import Pattern

# Use lookbehind to accept non-word char before the command token
# (so e.g. ' rm -rf /' or beginning-of-string both match).
_B = r"(?:^|(?<=[^A-Za-z0-9_]))"

_RAW = [
    # rm -rf <root>, <home>, or absolute Unix path
    _B + r"rm" + r"\s+-rf?\s+/",
    _B + r"rm" + r"\s+-rf?\s+~",
    _B + r"rm" + r"\s+-rf?\s+\$HOME",
    # Disk/filesystem wipes
    _B + r"format" + r"\s+[a-zA-Z]\s*:",
    _B + r"format\s+/[a-zA-Z0-9_]+",
    _B + r"mkfs(?:\.[a-z0-9]+)?\s+/dev/",
    _B + r"dd\s+if=/dev/\S+\s+of=/dev/",
    # SQL destructive
    _B + r"DROP\s+TABLE",
    _B + r"DELETE\s+FROM",
    _B + r"TRUNCATE",
    # Pipe-to-shell remote execution
    _B + r"curl\s+[^|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh)",
    _B + r"wget\s+[^|]*\|\s*(?:sudo\s+)?(?:sh|bash|zsh)",
    # Permissions and system control
    _B + r"chmod\s+[0-7]{3,4}\s+/",
    _B + r"chown\s+-R",
    _B + r"shutdown",
    _B + r"reboot",
    _B + r"poweroff",
    _B + r"halt",
    # Windows destructive
    _B + r"del\s+/[sSqQ]",
    _B + r"rd\s+/[sS]",
    _B + r"Remove-Item\s+(?:-Recurse|-r)",
    # Fork bomb
    r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:",
    # rm -rf on Windows-style absolute paths
    _B + r"rm\s+-rf?\s+[A-Za-z]:\\",
    _B + r"rm\s+-rf?\s+[A-Za-z]:/",
    # rm -rf on Windows backslash root paths (e.g., rm -rf \Windows\System32)
    _B + r"rm\s+-rf?\s+\\",
]


def _compile(raw: str) -> Pattern[str]:
    return re.compile(raw, re.IGNORECASE)


DANGEROUS_COMMAND_PATTERNS: list[Pattern[str]] = [_compile(p) for p in _RAW]


def is_dangerous_command(command: str) -> bool:
    """Return True if command matches any dangerous pattern."""
    if not command:
        return False
    return any(p.search(command) for p in DANGEROUS_COMMAND_PATTERNS)
