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

## Answer Values and Formula Results

- When designated answer cells must show results computed from other cells or sheets (sums, lookups, per-row calculations, conditional text, or formatted times and amounts), compute each result in Python from the full input workbook and write the literal result to the target cell.
- Formulas are not recalculated in this environment. A formula written by `openpyxl` is saved without a cached result and reads as empty with `data_only=True`; an answer cell containing only formula text has no value.
- Even when the instruction is phrased as a request for a formula, store the result that formula would produce in the designated answer cell. Formula text alone does not provide the requested result.
- When cells that feed an answer computation themselves contain formulas, obtain their evaluated values by loading a second workbook copy with `data_only=True` (using cached results where present) or by reproducing the formula logic in Python. Never treat formula text as its numeric result.
- Apply the requested display number format (time, currency, percentage, etc.) to the stored literal values.
- Preserve existing formulas, cells, and sheets outside the designated answer region; replace only the answer-region formulas or values that the instruction targets.

### Answer Region Layout

- When the task specifies an expected answer position or answer region, treat those cells as the authoritative output location and extent: populate every requested row and column inside that range, including its final rows, except that rows above an explicitly named start cell are left unchanged as described next.
- When the instruction explicitly names where the answer begins (for example, 'put the answer from I3 with the headers'), treat that named cell as the first written row even if the designated answer region starts above it. Write the requested header row at that named cell and the data rows directly beneath it, leave the region rows above the named start unchanged (blank if originally blank), and do not shift the table up to the region's first row or extend the written block beyond the region's last row. Keep the stated header text and the stated item/row ordering exactly as given.
- When no explicitly named start cell applies, if the answer region includes an existing header cell, keep or use that header in place and write the corresponding output values below it in the same column or range rather than shifting computed data into adjacent columns.
- Do not truncate a fixed answer range to a shorter last row inferred from one key column. For every target row in the region, write the rule-based result or the task-appropriate blank/default instead of leaving unrelated or stale content.
- When the instruction explicitly states which output column or cell receives which kind of content, that stated assignment governs the values written there, even if an example row already present in or adjacent to the answer region shows the opposite arrangement.
- For that conflicting placement aspect only, treat the pre-existing example row as illustrative and repopulate the designated region according to the instruction's stated assignment; keep the example's other, non-conflicting information, such as row pairing, which source records belong in the region, or an existing header cell.
- When the instruction states no such assignment, keep deriving placement from the surrounding headers or example layout, including keeping an existing header cell in place.
- When the instruction asks for a count of qualifying records in a row-by-row list, shown "next to the last" qualifying row, and the designated answer region covers those same rows, do not reduce the result to a single global count in one cell of the region. Derive the grouping from the list's own data (for example a repeated caller, session, or call identifier) and write each group's count at that group's last qualifying row, leaving the other region rows blank. If no field distinguishes groups, follow the instruction's explicit placement wording rather than inventing additional non-empty output cells.

### Source Detail Columns and Lookup Keys

- When the instruction states that related detail data continues to the right of a named column or may occupy a variable number of columns, determine the full contiguous detail or result column block from headers and the used range. Do not limit processing to a fixed number of columns such as four.
- Use all discovered detail columns in positional mappings so that a value located in a later column receives its actual position rather than being treated as missing.
- When matching records using only a subset of the available fields, check whether multiple source records share that lookup key rather than silently overwriting earlier entries in a dictionary.
- If duplicate partial keys exist and both source and target contain additional shared contextual fields, use those fields or the target row's context to select the corresponding source record. If no distinguishing fields exist, follow the instruction for multiple matches instead of collapsing them without notice.
- Keep exact-key matching when the key is unique, and do not add unrelated fields that are absent from either the source or target data.
- When recognizing columns or records from header values that are numeric or date-like, accept both native numeric or date cell values and equivalent text representations after trimming and normalization.
- Do not require an int or float cell type to recognize a day, month, year, or similar header. Failing to recognize such text headers must not produce an empty column set or zero totals.
- Use this normalization only for matching and column discovery. Keep computed result values in their required numeric or date type and apply any requested number formats.

### Rolling and Trailing-Window Aggregates

- When computing a rolling or trailing-window aggregate keyed to each row's date, select contributing source rows by comparing their dates with window bounds computed from the current row's date across the whole data column, not only rows that sit above the current row in the sheet.
- Include every source row whose date falls inside those bounds, including rows with the same date that appear below the current row, and derive the lower bound from the period the instruction states (one year earlier for a 12-month or one-year window) rather than from a fixed row count.
- Write the computed average as a literal numeric value for every row of the designated answer region that has a date and at least one contributing value, keeping the requested number format.

### Table Copies by Row and Column Labels

- When copying values between tables by matching row labels and column labels (INDEX/MATCH-style), compare labels after stripping surrounding whitespace and ignoring case, and compare numeric-looking labels by their numeric value, so formatting differences do not make an existing label look absent.
- Determine each table's key row and key column from where its own labels actually sit in that table instead of assuming one fixed offset that must hold for both tables.
- Leave a destination cell empty only after that normalized comparison fails to find the source label, and do not let label-formatting differences suppress the copied block.

### Shared-Pool Allocation Across Order Lines

- When several order lines consume one shared incoming-stock pool for the same order and part, allocate cumulatively in the data's line sequence — ascending order-line value, falling back to row position when line values are missing or equal — instead of ordering the lines by requested delivery date or issued date.
- Use the earliest-issued date and requested-delivery date to identify or prioritize orders, not to reorder the lines within one order/part group; in particular, do not let a later line of the same order take stock ahead of an earlier line because its requested delivery date is sooner.
- Cap each line's allocation at the smaller of its requested quantity and the stock still remaining in that pool, keep the remaining balance inside the same order/part group, and write a numeric 0 for lines that receive no stock.

## Numeric Zeros and Blank Cells

- When the instruction asks for a display convention on numeric results (for example, a hyphen instead of a zero, or a currency, percent, or time appearance), keep the computed value numeric and express the convention through `cell.number_format`. For a hyphen-at-zero look, use a number format whose zero section displays a hyphen.
- Distinguish a computed numeric zero from a blank or no-data cell: keep zero-valued totals as numeric `0` even when the instruction asks for hyphen-at-zero display, and use the number format for that display. Write a literal hyphen (text) only for a cell that has no data at all when the instruction asks for a visible hyphen in empty cells. Do not convert numeric zeros to text.
- Do not change the value type of numeric result columns; write text only where the target column is genuinely textual or the instruction explicitly asks for a visible hyphen in a no-data cell.

## Output Requirements

- Save the result to `OUTPUT_PATH`.
- Do not hardcode row counts or column letters — iterate over actual rows in the workbook.
- Preserve sheets and cells not mentioned in the instruction.
