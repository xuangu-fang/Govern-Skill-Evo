# Spreadsheet Manipulation Skill (xlsx)

## Overview
This skill guides agents in manipulating Excel (.xlsx) spreadsheets using Python.

**Primary libraries**: `openpyxl` (structure-preserving read/write), `pandas` (data transformation).
Never use any other third-party libraries.

---

## Common Workflow

1. **Inspect** the input workbook within the generated program: list sheets, inspect headers, dimensions, formulas, and cell types as needed.
2. **Transform and save** in the same program: perform the requested changes and save the modified workbook to `OUTPUT_PATH`.
3. **Verify and repair** by reopening the saved workbook when useful; you may save, reopen, and re-save within the same program. If target values are missing or wrong, repair and save again before finishing.

When a workbook task requires changing cells, the program must perform any needed inspection and the requested transformation in the same execution, then save the modified workbook to `OUTPUT_PATH`. Do not submit a program whose only effect is printing worksheet contents, listing formulas, or saving an unchanged copy. Use runtime inspection only to choose values, ranges, or formulas within that same program; do not rely on printed output being available for a later attempt. The first normally terminated program that produces an openable workbook at `OUTPUT_PATH` is final, so it must contain the complete requested transformation.

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

# INPUT_PATH and OUTPUT_PATH are supplied by the executor.

wb = openpyxl.load_workbook(INPUT_PATH)
ws = wb.active  # or wb["SheetName"]

# --- perform manipulation ---

wb.save(OUTPUT_PATH)
```

---

## Formula Cells and Cached Results

- When the instruction requires a formula, write the formula text and also provide its cached result in the same cell. Grading reads saved cell values with `data_only=True`, and no formula recalculation occurs.
- Store the cached result with the correct value type (numeric, text, boolean, or error) and preserve any required number or display format.
- `openpyxl` does not calculate formulas. If `openpyxl` alone saves only the formula, ensure the saved worksheet XML contains both the formula and its cached value rather than dropping the formula.
- After saving, reopen `OUTPUT_PATH` with `data_only=True` and verify that each formula cell you wrote returns the intended value. Repair any missing or incorrect cached result before the program finishes.
- Do not replace a required formula with a value-only cell. If no live formula is required, a computed value may be written directly.

## Color-Gated Row Formulas

- When a task asks to apply a formula or transformation only to rows highlighted with a color, determine the highlight from the row's own fill and from fills stored on the row's data cells, including cells other than the designated answer cell. Read the target fill's actual color attributes, such as foreground, indexed, or theme color, rather than checking only the answer cell or relying on a fill-type label alone.
- Treat a header, legend, or isolated cell outside the row's data block as descriptive context, not as proof that a data row is highlighted.
- Apply the formula or transformation only to rows whose row-level fill or row/data cells carry the target highlight. Leave every non-highlighted row unchanged, including its existing formulas and saved cached values.
- When a modified formula cell also needs a saved cached result, derive that cached value by applying the stated transformation to the cell's existing cached or displayed result when one is available; otherwise evaluate the original formula faithfully. For a prefix transformation, prepend the literal prefix to that result so the cached value agrees with the rewritten formula. Do not write a changed cached value for a row that was not modified.

## Target Table Column Mapping

- When a target table's columns are driven by header/category keys, resolve each target column's key from its actual header cell when that header names a source category, and write that column's formula or cached result.
- When the block's header row does not supply usable per-column category names (for example a single generic label such as "Sales", or blank header cells), derive the mapped columns from the distinct source categories themselves: assign one block column per distinct category, in the order the categories first appear in the source data or in the order the instruction specifies, and write the category name into that column's header cell when it is not already there so the header-referencing formula and its cached result agree.
- Leave a column's answer cells empty or unchanged when no source category can be assigned to it, such as columns beyond the number of distinct source categories or a column whose header names something that is not a source category while no category remains to assign; never compute such a column with an empty key and never store a numeric zero there.
- Still apply any explicitly requested formatting to the full specified answer range, including formatting-only blank cells.
- A computed numeric zero is valid only when a valid category key was resolved and the source calculation legitimately totals to zero.

## Date-Derived Day Numbers

- When an instruction asks for a static number derived from a date and refers to the 'number of the last day' or similar wording about a day number, identify the last applicable entry in the referenced date range as the final non-empty entry in row order. When the instruction says the final entry controls non-sequential dates, do not use the maximum or latest date.
- Write that entry's calendar day-of-month integer. Use an Excel date serial only when the instruction explicitly asks for the date value or serial number; do not substitute a full serial for a requested day number.

## Next-Row/Date Formula Guards

- When the instruction says a formula must not calculate after the last applicable row because no next row/date exists, make the formula's own guard test the next boundary cell or next row's key, not only the current row's blank status.
- For rows where the next boundary is absent, write the task-specified blank/no-result cached value; for rows with a next boundary, continue using that next boundary as the window end.

## Derived Row Totals

When the requested answer is a per-row derived total and the same input row already contains the component totals in adjacent cells, compute the row result from those saved component values instead of re-deriving the components from raw source sheets with guessed filters. Recompute from raw source data only when the instruction explicitly asks to change those component values or when the row's component cells are blank or incomplete. Preserve the original row order and do not overwrite component cells unless the task requires it.

## Open-at-Period-End Counts

- When the requested metric counts records 'still open by the end of' a month or other period, use the period end as the closure cutoff: count a record only if it was created on or before the period end and either has no closure date or has a closure date after the period end.
- Do not count a record as open at period end merely because its closure date is on or after the period start. When an instruction contains both an end-of-period headline and a looser interval description, reconcile the count toward the end-of-period outcome.

## Empty Cells and Numeric Zeros

When an instruction calls for a hyphen for empty cells, apply the hyphen only to cells whose source or computed result is actually blank or empty, or when the instruction explicitly says every zero should display as a hyphen. Do not convert an existing numeric zero or a computed zero total into a text hyphen merely because it equals zero. Preserve numeric zeros so saved-value comparisons remain correct.

## Output Requirements

- Save the result to `OUTPUT_PATH`.
- Do not hardcode row counts or column letters — iterate over actual rows in the workbook.
- Preserve sheets and cells not mentioned in the instruction.
