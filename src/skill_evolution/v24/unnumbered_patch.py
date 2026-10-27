from .contracts.editor import actual_diff
"""Strict single-file unnumbered diffs; no mutation, repair or fuzzy matching.

All hunks locate against the same frozen source. Callers own semantic outcomes
such as Editor no-change and Preconditioner Keep/withdrawal.
"""
from src.skill_evolution.v24.contracts.editor import _lines, _utf8, NO_NEWLINE
from src.skill_evolution.v24.facts import require

CONTRACT_VERSION = "unnumbered_diff_v1"


def apply_patch(parent, patch):
    require(parent is None or isinstance(parent, str), "Invalid frozen source")
    _utf8(parent or "")
    _utf8(patch)
    source, lines = _lines(parent or ""), _lines(patch)
    header = "--- /dev/null\n" if parent is None else "--- a/SKILL.md\n"
    require(len(lines) >= 3 and lines[:2] == [header, "+++ b/SKILL.md\n"],
            "Expected only the exact SKILL.md diff headers")
    edits, i = [], 2
    while i < len(lines):
        number = len(edits) + 1
        def check(condition, message):
            require(condition, f"Hunk {number}: {message}")

        check(lines[i] == "@@\n", "expected bare @@ header")
        i += 1
        old, new, changed = [], [], False
        while i < len(lines) and lines[i] != "@@\n":
            line = lines[i]
            if line.startswith("@@"):
                raise ValueError(f"Hunk {number + 1}: expected bare @@ header")
            check(line[:1] in (" ", "+", "-") and line.endswith("\n"),
                  "invalid body line or missing framing LF")
            prefix, content = line[0], line[1:]
            changed = changed or prefix != " "
            i += 1
            if i < len(lines) and lines[i] in (NO_NEWLINE, NO_NEWLINE + "\n"):
                content = content[:-1]
                i += 1
            if prefix in (" ", "-"):
                old.append(content)
            if prefix in (" ", "+"):
                new.append(content)
        check(changed and old != new, "must contain an actual change")
        # LF is the only line separator; a no-LF line cannot occur mid-fragment.
        check(all(s.endswith("\n") for s in old[:-1] + new[:-1]),
              "missing-newline marker occurs before fragment EOF")
        if not source:
            check(number == 1 and not old and i == len(lines),
                  "empty source requires one addition-only hunk")
            start = 0
        else:
            check(bool(old), "insertion into nonempty source requires context")
            matches = [at for at in range(len(source) - len(old) + 1)
                       if source[at:at + len(old)] == old]
            check(len(matches) == 1, f"expected one exact source match; found {len(matches)}")
            start = matches[0]
        if edits:
            previous_start, previous_end, _ = edits[-1]
            check(start > previous_start, "source order is not strictly increasing; no reordering")
            check(start >= previous_end, "source region overlaps previous hunk, including context")
        edits.append((start, start + len(old), new))

    # Construct only after every hunk has validated against the frozen source.
    output, cursor = [], 0
    for start, end, replacement in edits:
        output.extend(source[cursor:start])
        output.extend(replacement)
        cursor = end
    output.extend(source[cursor:])
    if not all(line.endswith("\n") for line in output[:-1]):
        number = next(n for n, (_, _, replacement) in enumerate(edits, 1)
                      if any(not line.endswith("\n") for line in replacement))
        raise ValueError(f"Hunk {number}: Missing-newline marker occurs before result EOF")
    candidate = "".join(output)
    require(bool(candidate.strip()) and candidate != (parent or ""),
            f"Hunks 1-{len(edits)} (result): Patch produces empty or unchanged text")
    return candidate
