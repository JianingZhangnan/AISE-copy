"""T02: Filesystem and workspace path utilities tests.

RED phase: these tests must fail because src/phycode/paths.py does not exist yet.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from phycode.paths import (
    resolve_workspace_path,
    is_within_allowed,
    symlink_escape,
    safe_join,
    PathEscapeError,
)
from phycode.errors import PhyCodeError


class TestResolveWorkspacePath:
    def test_resolve_workspace_path_strips_relative_dots(self, tmp_path: Path) -> None:
        """./sub/file" resolved relative to root should give root/sub/file."""
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "file").write_text("hello")
        result = resolve_workspace_path(tmp_path, "./sub/file")
        assert result == tmp_path / "sub" / "file"

    def test_resolve_workspace_path_normalises_separators(self, tmp_path: Path) -> None:
        """Forward slashes should be normalised on Windows."""
        result = resolve_workspace_path(tmp_path, "foo/bar/baz")
        assert result == tmp_path / "foo" / "bar" / "baz"

    def test_resolve_workspace_path_absolute_input(self, tmp_path: Path) -> None:
        """Absolute paths should be resolved relative to root."""
        abs_path = tmp_path / "existing.txt"
        abs_path.write_text("x")
        result = resolve_workspace_path(tmp_path, str(abs_path))
        assert result == abs_path


class TestSafeJoin:
    def test_safe_join_blocks_parent_escape(self, tmp_path: Path) -> None:
        """safe_join(root, '..', 'evil') must raise PathEscapeError."""
        with pytest.raises(PathEscapeError):
            safe_join(tmp_path, "..", "evil")

    def test_safe_join_allows_nested(self, tmp_path: Path) -> None:
        """safe_join should allow deeply nested safe paths."""
        result = safe_join(tmp_path, "a", "b", "c")
        assert result == tmp_path / "a" / "b" / "c"

    def test_safe_join_blocks_absolute_path_injection(self, tmp_path: Path) -> None:
        """An absolute path in parts must raise PathEscapeError."""
        abs_path = tmp_path / "injected"
        with pytest.raises(PathEscapeError):
            safe_join(tmp_path, str(abs_path))

    def test_safe_join_symlink_within_root_ok(self, tmp_path: Path) -> None:
        """A symlink that stays within root is allowed."""
        target = tmp_path / "symlink_dir"
        target.mkdir()
        link = tmp_path / "link"
        try:
            link.symlink_to(target)
        except OSError:
            pytest.skip("symlink creation not supported on this platform")
        result = safe_join(tmp_path, "link")
        assert result == tmp_path / "link"


class TestSymlinkEscape:
    def test_symlink_escape_detected_outside_root(self, tmp_path: Path) -> None:
        """A symlink pointing outside the allowed root should be detected."""
        target = tmp_path / "outside"
        target.mkdir()
        link_dir = tmp_path / "sub"
        link_dir.mkdir()
        link = link_dir / "escape"
        try:
            link.symlink_to(target)
        except OSError:
            pytest.skip("symlink creation not supported on this platform")
        assert symlink_escape(tmp_path, link) is True

    def test_symlink_escape_allows_inside(self, tmp_path: Path) -> None:
        """A symlink pointing inside the root should NOT be flagged."""
        target = tmp_path / "inside_target"
        target.mkdir()
        link_dir = tmp_path / "sub"
        link_dir.mkdir()
        link = link_dir / "inside"
        try:
            link.symlink_to(target)
        except OSError:
            pytest.skip("symlink creation not supported on this platform")
        assert symlink_escape(tmp_path, link) is False


class TestIsWithinAllowed:
    def test_is_within_allowed_respects_extra_root(self, tmp_path: Path) -> None:
        """Candidate within allowlist should return True even if outside root."""
        root = tmp_path
        extra_root = tmp_path / "extra"
        extra_root.mkdir()
        allowed_path = extra_root / "file.txt"
        result = is_within_allowed(root, allowed_path, allowlist=[extra_root])
        assert result is True

    def test_is_within_allowed_rejects_outside(self, tmp_path: Path) -> None:
        """Candidate outside both root and allowlist should return False."""
        root = tmp_path
        other = tmp_path.parent / "totally_other"
        result = is_within_allowed(root, other, allowlist=[])
        assert result is False

    def test_is_within_allowed_default_empty_allowlist(self, tmp_path: Path) -> None:
        """With empty allowlist, only paths within root are allowed."""
        child = tmp_path / "child" / "file"
        child.parent.mkdir()
        child.write_text("x")
        assert is_within_allowed(tmp_path, child, allowlist=[]) is True

        sibling = tmp_path.parent / "sibling"
        assert is_within_allowed(tmp_path, sibling, allowlist=[]) is False


class TestPathEscapeError:
    def test_path_escape_error_is_phycode_error(self) -> None:
        """PathEscapeError should inherit from PhyCodeError."""
        assert issubclass(PathEscapeError, PhyCodeError)

    def test_path_escape_error_message(self) -> None:
        """PathEscapeError should carry a message."""
        err = PathEscapeError("path escaped", requested="foo", root=Path("/root"))
        assert "escaped" in str(err)
