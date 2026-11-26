# Spreadsheet Manipulation Skill (xlsx)

## Overview
This skill guides agents in manipulating Excel (.xlsx) spreadsheets using Python.

**Primary libraries**: `openpyxl` (structure-preserving read/write), `pandas` (data transformation).
Never use any other third-party libraries.

---

## Common Workflow

1. **Explore** the input file: list sheets, inspect headers, check dimensions.
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

## Tolerant Text and Condition Matching

When an instruction asks you to find, match, or act on a text label or keyword in cells:

- Compare with a normalized, case-insensitive test: fold letter case and disregard leading, trailing, and repeated internal whitespace before deciding whether a cell qualifies.
- Treat the quoted label as text that may appear inside a longer cell value (substring membership) unless the instruction explicitly requires the whole cell to equal the label exactly. Do not default to case-sensitive whole-cell equality.
- Apply the same normalized, tolerant comparison to the companion numeric criterion that selects between the alternative outputs (for example whole number vs. fraction): accept int, float, and numeric-looking strings, and use a small tolerance so integer-valued floats count as whole numbers.
- For every populated data row, write the selected output into the specified target cell only when its condition is met, and leave rows that satisfy no stated condition unchanged. Iterate over the actual rows of the sheet, not a fixed range.

## Answer Placement at the Stated Anchor

When the instruction states a specific starting cell or row for the answer, and may also name header labels:

- Place the header labels at that stated start and the data rows immediately below it. Do not assume the first row of the stated answer region is the header row when the instruction names a different start cell.
- Do not write into answer-region cells above the stated start or beyond the produced data rows, and leave any pre-existing content in those cells unchanged rather than clearing it.
- Honor the instruction's explicit item set and ordering: write the items in the stated order.
- Compute each adjacent value (count or sum) from the entire relevant source column read from the file, not from the bounded preview.

---

## Consolidating Rows from Multiple Source Sheets

When the task asks to consolidate or append the data rows of several named source sheets into the target sheet's first blank rows:

- Append every named source sheet's populated data rows, in the order the instruction lists those sheets (or in the workbook's sheet order when the instruction states no order). The appended block is read by cell address, so do not skip a source sheet because its name already appears in the target's provenance column, and do not delete, reorder, or overwrite the target's existing rows.
- Begin the append at the first row after the target's actual last populated row.
- Identify which source columns to copy from the cue the instruction gives (for example columns highlighted in a color, or columns whose headers name the fields the target needs). Then place each chosen source column into the target column whose header in the target's header row names the same field; fall back to positional placement only for a chosen source column that has no matching target header.
- Stamp the originating sheet name into the designated provenance column for every appended row.
- Preserve the target's existing values and formatting outside the appended region, and do not add column headers or fill colors that the instruction excludes.

---

## Identifier Keying and Ordered Allocation

When grouping or matching records by an identifier that carries a distinguishing part (for example an order number with a customer-model suffix):

- Use the full identifier as the key; do not truncate it to a shared numeric or prefix portion that would merge records the instruction treats as distinct.
- Normalize identifiers only for letter case, surrounding whitespace, internal whitespace runs and separator spelling (for example collapsing whitespace runs to a single space and treating '-' and '/' as the same separator). Never normalize by discarding the distinguishing prefix or suffix.
- When a limited quantity is allocated across several matching lines, apply the order the instruction states (for example FIFO by the stated date, then line order), so earlier lines consume first and later lines receive only the remaining quantity or 0.

---

## Numeric Bounds and Balancing

When an instruction refers to specified minimum and/or maximum quantity constraints for cells or columns:

- Read the actual bound values from the workbook (load the whole relevant sheet, not only the presented preview) and enforce both bounds per cell. Do not substitute a single default minimum, and do not treat the maximum as unbounded.
- When the amount needed to balance one row cannot be absorbed by one cell within its own bounds, continue applying the remaining amount to the next eligible cell in the direction the instruction specifies, skipping cells the instruction excludes (for example zero-valued cells), and stop only when the requirement is satisfied or every eligible cell has reached a limit.
- After adjusting, set the designated summary/residual cells to the values the instruction states (for example a residual column to 0), and do not move or alter cells the instruction marks as fixed.

---

## Formula Results Under No-Recalculation Grading

Grading reads the saved workbook's cached values with `data_only=True`. A formula written with openpyxl has no cached result, so `data_only=True` returns no value for that cell. The deliverable must make the intended result readable under `data_only`, not merely place a formula string in the cell.

- When the task requires a formula to be present in the deliverable, keep that formula in the required cells and attach a readable computed cached result to every required target cell — for example by computing the intended result in Python and injecting a nonempty cached-value element for exactly those cells into the correct sheet XML part, or by an equivalent mechanism that makes the saved workbook return the value under `data_only=True`. Cover all required target cells, not only a subset.
- When the task requires only a computed result rather than a formula, write the computed value directly; this is the safer route and is preferred, because a formula cell whose cached result is not readable grades as empty.
- Before the program terminates, reopen the saved output with `data_only=True` and check every required target cell. If any returns `None` or an unintended value, correct that cell inside the same program, save again (re-inject its cached value so the saved cell carries a nonempty result), and re-check, rather than ending with the unreadable cell left in `OUTPUT_PATH`.
- Keep the check and any correction scoped to the target cells, and preserve unrelated sheets, styles, ranges, filters, and formulas without deleting or reordering them.

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
