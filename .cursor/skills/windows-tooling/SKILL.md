# Skill: Windows File Encoding Workaround

## The Problem

The Write tool and StrReplace tool on Windows PowerShell write files in UTF-16-LE encoding (each ASCII character followed by a null byte). This causes:

1. Python AST parser: `SyntaxError: source code string cannot contain null bytes`
2. pytest assertion rewrite: `SyntaxError: source code string cannot contain null bytes`
3. `uv run ruff check`: Intermittent encoding errors

The Write tool is NOT the issue - the issue is that the tool's output is UTF-16-LE on Windows.

## Detection

Check file encoding:
```python
data = open(path, 'rb').read()
print('Has null:', b'\x00' in data)
# Or check BOM:
print(data[:4].hex())   # UTF-16-LE BOM = 0xff 0xfe 0x?? 0x??
```

## Solutions (in order of preference)

### Solution 1: Python Script (Recommended)

Write a small Python helper script that reads the content and writes it with UTF-8:

```python
# _write.py
content = open(__file__, 'r', encoding='utf-8').read()
# Strip the script wrapper
content = content.split('###CONTENT###', 1)[1].split('###END###', 1)[0]
target = r'<target-path>'
with open(target, 'w', encoding='utf-8') as f:
    f.write(content)
```

Run with: `uv run python _write.py`

### Solution 2: uv run + inspect

If a file is already corrupted (has null bytes), use Python to strip them:

```python
import sys
path = r'<path>'
content = open(path, 'rb').read().replace(b'\x00', b'')
open(path, 'wb').write(content)
```

Note: This approach requires approval since it modifies a file.

### Solution 3: Write to .py file and import

Write a `.py` file using the Write tool (even as UTF-16-LE), then import it from a Python script that opens the file in binary mode, extracts only the UTF-8 payload, and writes it to the real target.

## Why Write Tool Produces UTF-16-LE

PowerShell's default encoding on Windows is UTF-16-LE. The Write tool appears to use PowerShell semantics for file output, which results in UTF-16-LE.

This is a known limitation of the Cursor Write tool on Windows.

## Prevention

Always verify file encoding after using Write tool on Windows:
```python
data = open(path, 'rb').read()
assert b'\x00' not in data, f"{path} has null bytes (UTF-16-LE)"
```

Add this as a post-write check in any workflow that writes Python files.

## Additional Windows Notes

- `make` command does not exist; use `gmake` or `uv run pytest` directly
- Git auto-converts LF to CRLF on Windows (normal behavior, ignore warnings)
- `uv run python <script>` always uses the .venv Python (correct)
- System Python (Anaconda) may differ from uv's Python version
- PowerShell heredoc syntax (`<<'EOF'`) is NOT supported; use Python scripts for multi-line strings
- `&&` and `;` chaining in PowerShell shell commands behaves differently from bash
