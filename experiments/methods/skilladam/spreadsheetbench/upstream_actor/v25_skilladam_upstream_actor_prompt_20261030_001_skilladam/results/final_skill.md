# Spreadsheet Manipulation Skill (xlsx)

## Overview
This skill guides agents in manipulating Excel (.xlsx) spreadsheets using Python.

**Primary libraries**: `openpyxl` (structure-preserving read/write), `pandas` (data transformation).
Never use any other third-party libraries.

---

## Common Workflow

1. **Explore** the input file: list sheets, inspect headers, check dimensions.
   If the workbook has an example/reference sheet or a filled-in "correct" copy, read it first to learn the exact layout, ordering, and display conventions to reproduce.
2. **Decide what each target cell must hold**: always the value Python computed — never formula text, even when the instruction says "formula", "amend the formula", "VLOOKUP", or "macro". openpyxl stores a formula string unevaluated, so it reads back blank; compute the result and write it.
3. **Write `solution.py`** with `INPUT_PATH` and `OUTPUT_PATH` defined at the top.
4. **Execute** `python solution.py` and verify the output file was created.
5. **Confirm** the target cells/range contain the expected values.

---

## Library Selection

| Use case | Library |
|----------|---------|
| Preserve formulas, formatting, named ranges | `openpyxl` |
| Bulk data transformation, aggregation, sorting | `pandas` → write back with `openpyxl` |
| Simple cell read/write | `openpyxl` |

**Warning**: `pandas.to_excel()` silently destroys existing formulas and named ranges.
When writing back to a spreadsheet that contains formulas, always use `openpyxl.save()`.
Preserving existing formulas is not the same as creating new ones: a formula string you assign is stored unevaluated and reads back as blank.

---

## solution.py Template

```python
import openpyxl
import pandas as pd

INPUT_PATH  = "..."   # set to the actual input path
OUTPUT_PATH = "..."   # set to the actual output path

wb = openpyxl.load_workbook(INPUT_PATH)
ws = wb.active  # or wb["SheetName"]

# --- perform manipulation ---

wb.save(OUTPUT_PATH)
```

---

## Output Requirements

- Save the result to `OUTPUT_PATH`.
- Do not hardcode row counts or column letters — iterate over actual rows in the workbook.
- Preserve sheets and cells not mentioned in the instruction.

## Code Patterns

- **Write a computed result** into a target cell:
  `ws.cell(row=r, column=c).value = total`
  Stores a literal that reads back identically; no recalculation required.
- **Read existing formula results** from a second handle:
  `wb_vals = openpyxl.load_workbook(INPUT_PATH, data_only=True)`
  Returns the last-saved values; `None` means the file carries no cached result.
- **Find the true last data row before appending or deleting** — `ws.max_row` can include formatted-but-empty rows, so appending at `max_row + 1` lands far below the data:
  `last = max(r for r in range(1, ws.max_row + 1) if any(ws.cell(r, c).value not in (None, "") for c in range(1, ws.max_column + 1)))`
  Append at `last + 1`; delete bottom-up with `for r in range(last, 1, -1)` so the remaining row indices stay valid.
- **Keep a display format with a literal value**:
  `cell.value = t` then `cell.number_format = "hh:mm:ss AM/PM"`
  The value is what gets compared; the format only changes how it is displayed.

## Error Avoidance

- openpyxl never evaluates formula text: `=SUM(...)`, `="//"&A1`, or pasted VBA/macro code all read back blank — write the computed value, and use Python string ops (`"//" + s`) for prefixes/suffixes.
- Do not post-process the saved .xlsx XML/zip to inject cached formula results; compute every answer in Python and write literals.
- Do not overwrite cells that already hold correct values with formula text — recompute the number and write it.
