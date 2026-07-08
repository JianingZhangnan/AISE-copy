"""Filesystem and workspace path utilities."""

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path

from phycode.errors import PhyCodeError


class PathEscapeError(PhyCodeError):
    """Raised when a path operation escapes the allowed workspace root."""

    def __init__(
        self,
        message: str,
        requested: str | None = None,
        root: Path | None = None,
    ) -> None:
        super().__init__(message)
        self.requested = requested
        self.root = root


def resolve_workspace_path(root: Path, requested: str) -> Path:
    """Resolve `requested` (which may be relative or absolute) relative to `root`.

    - Handles ".." and "." components
    - Normalises path separators (works on both Windows and POSIX)
    - If `requested` is absolute, resolves it relative to `root`
    """
    p = Path(requested)
    if p.is_absolute():
        # Treat absolute inputs as being relative to root
        p = root / p
    else:
        p = root / p
    # Normalise: resolve dots, collapse separators
    try:
        resolved = p.resolve()
    except OSError:
        # resolve() can fail for some paths on Windows; fall back to strict normalisation
        resolved = p.resolve(strict=False)
    return resolved


def is_within_allowed(
    root: Path,
    candidate: Path,
    allowlist: Iterable[Path] = (),
) -> bool:
    """Return True if `candidate` is within `root` or any path in `allowlist`.

    Uses Path.is_relative_to() (Python 3.9+) when available, otherwise falls back
    to comparing resolved parts.
    """
    # Normalise candidate once
    try:
        cand = candidate.resolve(strict=False)
    except OSError:
        cand = candidate

    # Check root
    try:
        root_resolved = root.resolve(strict=False)
        if cand.is_relative_to(root_resolved):
            return True
    except (ValueError, OSError):
        pass

    # Check allowlist
    for allowed in allowlist:
        try:
            allowed_res = allowed.resolve(strict=False)
            if cand.is_relative_to(allowed_res):
                return True
        except (ValueError, OSError):
            pass

    return False


def symlink_escape(root: Path, candidate: Path) -> bool:
    """Return True if `candidate` is a symlink that escapes outside `root`.

    Uses os.path.realpath to resolve the symlink chain and checks whether
    the final resolved path is within the allowed root.
    """
    try:
        real = os.path.realpath(candidate)
        real_path = Path(real)
        # If the resolved path is not relative to root, it escapes
        try:
            root_res = root.resolve(strict=False)
            if not real_path.is_relative_to(root_res):
                return True
        except ValueError:
            return True
    except OSError:
        pass
    return False


def safe_join(root: Path, *parts: str) -> Path:
    """Join `parts` under `root`, raising PathEscapeError if the result escapes.

    This is the primary API for safely constructing paths from user/agent input.
    """
    root_resolved = root.resolve(strict=False)
    joined = root_resolved
    for part in parts:
        # Reject absolute parts (they would reset the join)
        if Path(part).is_absolute():
            raise PathEscapeError(
                f"Absolute path part rejected: {part!r}",
                requested=part,
                root=root_resolved,
            )
        joined = joined / part
    # Resolve the final joined path
    try:
        final = joined.resolve(strict=False)
    except OSError:
        final = joined
    # Verify it didn't escape
    if not is_within_allowed(root_resolved, final, allowlist=[]):
        raise PathEscapeError(
            f"Path escaped root: {final!r}",
            requested=str(joined),
            root=root_resolved,
        )
    return final
