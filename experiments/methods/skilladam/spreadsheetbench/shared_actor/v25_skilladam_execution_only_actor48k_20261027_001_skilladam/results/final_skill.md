# Spreadsheet Manipulation Skill (xlsx)

## Overview
This skill guides agents in manipulating Excel (.xlsx) spreadsheets using Python.

**Primary libraries**: `openpyxl` (structure-preserving read/write), `pandas` (data transformation).
Never use any other third-party libraries.

---

## Common Workflow

1. **Inspect and produce the answer in a single script — there is no separate exploration turn.** A script that only reads and prints leaves `OUTPUT_PATH` unwritten and scores nothing. List the sheets, read the headers, and check dimensions inside the same script that computes the result, then call `wb.save(OUTPUT_PATH)` before it ends.
2. **Write `solution.py`** with `INPUT_PATH` and `OUTPUT_PATH` defined at the top.
3. **Execute** `python solution.py` and verify the output file was created.
4. **Confirm** the target cells/range contain the expected values.

---

## Library Selection

| Use case | Library |
|----------|---------|
| Preserve formulas, formatting, named ranges | `openpyxl` |
| Bulk data transformation, aggregation, sorting | `pandas` → write back with `openpyxl` |
| Simple cell read/write | `openpyxl` |

**Warning**: `pandas.to_excel()` silently destroys existing formulas and named ranges.
When writing back to a spreadsheet that contains formulas, always use `openpyxl.save()`.

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

---

## Code Patterns

- **Read populated rows, skipping the header**:
  `for row in ws.iter_rows(min_row=data_start, values_only=True):`
  Set `data_start` to the actual first data row: title rows, extra or merged header rows, and blank spacer rows above the header are not data and will shift every output row if included.

- **Write one computed value to a target cell**:
  `ws.cell(row=r, column=c).value = result`
  Targets the answer range cell-by-cell instead of rebuilding the sheet.

- **Pick a sheet by name with a safe fallback**:
  `ws = wb[name] if name in wb.sheetnames else wb.active`
  Avoids mutating the wrong sheet when names differ in case or spacing.

- **Delete rows bottom-up**:
  `for r in sorted(rows_to_delete, reverse=True): ws.delete_rows(r)`
  Keeps earlier row indices valid while deleting.

## Error Avoidance

- Every script must end by computing the requested result and calling `wb.save(OUTPUT_PATH)`; a print-only diagnostic run produces no output workbook, even as a first attempt.
- Assign the computed result for the target cells as a literal value, never as formula text or an XML cached-value injection — openpyxl stores formula strings without recalculating them, so the cell has no readable value.
- Match lookup keys on the same column on both sides; a reference table built from one column must be queried with that same column, not a neighbor.
- Apply every filter the instruction names (region, warehouse, user, date, code); dropping one changes the summed result.
- As a sanity check when filling a fixed-size answer range, compare the number of data rows you detected with the range size — an unexpected mismatch usually means header, title, or blank rows were counted as data, shifting every output row.
