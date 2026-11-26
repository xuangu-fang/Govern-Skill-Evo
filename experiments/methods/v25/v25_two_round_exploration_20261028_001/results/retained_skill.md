# Spreadsheet Manipulation Skill (xlsx)

## Overview
This skill guides agents in manipulating Excel (.xlsx) spreadsheets using Python.

**Primary libraries**: `openpyxl` (structure-preserving read/write), `pandas` (data transformation).
Never use any other third-party libraries.

---

## Common Workflow

The executor runs one complete program per attempt in a fresh directory: there is no
interactive shell, no persistent session, and no reuse of an earlier attempt's files or
variables. `INPUT_PATH` and `OUTPUT_PATH` are bound by the executor. Every program must
both inspect the input and write the result.

1. **Inspect and transform inside the same program**: read the entire original input and
   locate the relevant sheets, header rows, data rows, and columns programmatically,
   rather than relying on the preview or assuming preview positions.
2. **Save the result** to `OUTPUT_PATH` before the program ends.
3. **Re-open the saved output** to confirm the required answer cells were written.

A program that only prints diagnostics, or deliberately raises to expose data, ends
without a saved workbook: it is returned as an output-file or execution error, consumes
one limited execution attempt, and is not a submission. Restrict any inspection-only
program to the rare case where the transformation genuinely cannot be written without
seeing hidden values the program cannot discover itself, and keep such a program as
small as possible.

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

# INPUT_PATH and OUTPUT_PATH are bound by the executor; use them directly.

wb = openpyxl.load_workbook(INPUT_PATH)
ws = wb.active  # or wb["SheetName"]

# --- perform manipulation ---

wb.save(OUTPUT_PATH)
```

---

## Reading Numeric Source Values

Some numbers are stored as formula results. A normal load of the input returns the
formula text (a string) for those cells; loading a second copy with `data_only=True`
returns the cached results instead. Use the `data_only=True` copy to obtain such numbers,
and never coerce a formula string to `0`.

- If a cached value is `None`, that source cell has no usable number in this file:
  exclude it rather than counting it as zero, and derive the required value from the
  remaining source cells or the rule the instruction states.
- Apply this both when gathering input data and when reconstructing report or total
  cells: a `0` produced from unreadable formula text is not evidence that the underlying
  quantity is zero.

---

## Writing Answer Cells

Grading reads the saved workbook's cell values with `data_only=True`, and no formula
recalculation is performed. A cell that holds only a formula string has no stored result
and reads as `None`.

- Every answer cell whose graded content is a value must end the run with a readable
  stored value. By default, write the computed value directly instead of a formula,
  including when the instruction describes a formula rather than requiring that specific
  cell to keep one; grading compares saved values, and a directly written value satisfies
  that comparison.
- Write a formula only when the cell must additionally keep one (for example the
  instruction needs the formula text preserved in the sheet). In that case also store its
  computed result in the saved workbook and confirm the stored result is actually
  readable; if it is not, repair it by writing the computed value directly into that cell.
- Do not replace an existing readable value inside the answer region with a formula that
  has no stored result; a value that is already correct must stay readable after the edit.
- Before the program ends, re-open the saved file with `data_only=True` and confirm each
  answer cell is non-`None` and equal to the value the program computed. If a cell reads
  as `None`, repair the stored result before finishing.

---

## Recomputing Values the Instruction Marks as Wrong

- When the instruction states that an existing formula or value is wrong and asks for the
  correct result, do not reuse that formula's logic as the definition of the answer.
  Compute the requested quantity directly from the source records using the criteria the
  instruction states.
- Criteria that assign several different equality values to the same field can never
  match a single record. When the instruction lists multiple candidate values for one
  field (for example several user IDs or error codes), treat them as alternatives:
  evaluate each candidate and combine the results, unless the instruction requires a
  record to satisfy all of them.
- If a constructed criteria set yields zero for rows whose source records visibly match
  the stated field values, treat the criteria as unsatisfiable and re-derive them before
  writing the results.

## Output Requirements

- Save the result to `OUTPUT_PATH`.
- Do not hardcode row counts or column letters — iterate over actual rows in the workbook.
- Preserve sheets and cells not mentioned in the instruction.
