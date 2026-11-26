import difflib

import re

from ..facts import require

HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?: [^\n]*)?\n")


NO_NEWLINE = "\\ No newline at end of file"


def _lines(value):
    """Split only on LF; preserve CR, whitespace and missing final LF exactly."""
    parts = value.split("\n")
    return [part + "\n" for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def _utf8(value):
    require(isinstance(value, str) and "\0" not in value, "Expected UTF-8 text without NUL")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Invalid UTF-8 text") from exc


def apply_patch(parent, patch):
    """Apply exact declared old/new coordinates; never search, normalize or repair."""
    require(parent is None or isinstance(parent, str), "Invalid Parent")
    _utf8(parent or "")
    _utf8(patch)
    source, lines = _lines(parent or ""), _lines(patch)
    old_header = "--- /dev/null\n" if parent is None else "--- a/SKILL.md\n"
    require(len(lines) >= 3 and lines[:2] == [old_header, "+++ b/SKILL.md\n"],
            "Expected only the exact SKILL.md unified diff headers")
    i, cursor, output = 2, 0, []
    while i < len(lines):
        match = HUNK.fullmatch(lines[i])
        require(match is not None, "Invalid hunk header or unexpected patch content")
        start_old, count_old, start_new, count_new = (int(v) if v is not None else 1 for v in match.groups())
        require((count_old == 0 or start_old > 0) and (count_new == 0 or start_new > 0)
                and count_old + count_new > 0, "Invalid hunk range")
        old_at = start_old - 1 if count_old else start_old
        new_at = start_new - 1 if count_new else start_new
        require(cursor <= old_at <= len(source) and old_at + count_old <= len(source),
                "Hunk outside Parent or overlaps a previous hunk")
        output.extend(source[cursor:old_at])
        require(new_at == len(output), "Hunk result position differs from declared new position")
        i += 1
        old, new = [], []
        while len(old) < count_old or len(new) < count_new:
            require(i < len(lines), "Truncated hunk")
            line = lines[i]
            require(line[:1] in (" ", "+", "-") and line.endswith("\n"), "Invalid hunk body line")
            prefix, content = line[0], line[1:]
            i += 1
            if i < len(lines) and lines[i] in (NO_NEWLINE, NO_NEWLINE + "\n"):
                content = content[:-1]  # Remove only diff framing LF, not data CR/space.
                i += 1
            if prefix in (" ", "-"):
                old.append(content)
            if prefix in (" ", "+"):
                new.append(content)
            require(len(old) <= count_old and len(new) <= count_new, "Hunk line counts differ")
        require(source[old_at:old_at + count_old] == old, "Parent context/deletion text differs at declared position")
        output.extend(new)
        cursor = old_at + count_old
    output.extend(source[cursor:])
    require(all(line.endswith("\n") for line in output[:-1]), "Missing-newline marker occurs before result EOF")
    candidate = "".join(output)
    require(bool(candidate.strip()) and candidate != (parent or ""), "Patch produces empty or unchanged Candidate")
    return candidate


def actual_diff(parent, candidate):
    """Derive an auditable diff, including standard EOF markers, from exact texts."""
    chunks = difflib.unified_diff(_lines(parent or ""), _lines(candidate),
                                  fromfile="/dev/null" if parent is None else "a/SKILL.md", tofile="b/SKILL.md")
    return "".join(line if line.endswith("\n") else line + "\n" + NO_NEWLINE + "\n" for line in chunks)


def _read_text(path):
    return path.read_bytes().decode("utf-8")  # No universal newline conversion.


def _write_text(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(value.encode("utf-8"))
    temporary.replace(path)

