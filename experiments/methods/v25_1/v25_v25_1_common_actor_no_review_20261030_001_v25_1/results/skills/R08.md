# Spreadsheet Manipulation Skill (xlsx)

## Overview
This skill guides agents in manipulating Excel (.xlsx) spreadsheets using Python.

**Primary libraries**: `openpyxl` (structure-preserving read/write), `pandas` (data transformation).
Never use any other third-party libraries.

---

## Common Workflow

1. **Explore** the input file inside the script: list sheets, inspect headers, check dimensions, and note which cells hold formulas.
2. **Write one complete script** that reads `INPUT_PATH` and writes `OUTPUT_PATH`; the executor binds those variables, so never reassign or hardcode paths.
3. **Self-check inside the script**: reopen the saved `OUTPUT_PATH` with `data_only=True` before the script ends (see "Results a `data_only` read can return").
4. **Confirm** the designated cells/range read back with the expected values.

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

## Reading formulas: keep two loads

- When input cells that feed the calculation may contain formulas (preview cells shown with a leading `=`, totals, derived columns), load the workbook twice: once with `data_only=True` and use only those cached values for every computation, and once normally for all writes and for the final save.
- Never compute or write an output from a value read out of the formula-preserving load that is a formula string such as `=SUM(...)`; such a string must not be stored in an output cell or coerced into a number.
- If a needed input cell is a formula whose `data_only` value is `None`, treat that value as unavailable and obtain it from the cells it references or from other explicit input data instead of silently substituting `0`, an empty string, or the current system date.
- When a cached aggregate or formula result depends on criterion cells holding dates, times, or other bounds, read those bound cells from the `data_only` load before computing the cached result.
- If a bound cell reads as `None` or empty, do not substitute `0`, an empty string, or the current date; obtain the bound from the cells it references or from other explicit input values, and use that same resolved bound in the formula and in the independently computed result.
- For date/time criteria, normalize data cells and bounds to the same Excel serial representation and apply the same boundary/include-exclude rule to the formula and the cached computation.
- Keep the two loads separate in the program: never save the `data_only` workbook and never rely on it to preserve formulas or number formats.

---

## solution.py Template

```python
import openpyxl
import pandas as pd

# INPUT_PATH and OUTPUT_PATH are bound by the executor; do not reassign them.

wb_values = openpyxl.load_workbook(INPUT_PATH, data_only=True)  # cached values for computation
wb        = openpyxl.load_workbook(INPUT_PATH)                  # formulas and formatting for writing

ws        = wb.active  # or wb["SheetName"]
ws_values = wb_values[ws.title]

# --- read inputs from ws_values, write results into ws ---

wb.save(OUTPUT_PATH)

# --- verification: reopen the saved file with data_only=True ---

written = openpyxl.load_workbook(OUTPUT_PATH, data_only=True)
```

---

## Results a `data_only` read can return

Formulas are not recalculated, so a designated cell that holds only a newly written formula reads back as empty.

- Every designated cell whose intended result is a non-empty value must carry a result that a `data_only` read can return; a designated cell whose intended result is blank may remain blank (`None` or an empty string).
- If the task requires a formula in the cell, write the formula and also store its computed result so the saved cell contains both, with that result derived from the workbook's actual input values and consistent with the formula's own references.
- For every designated cell that holds a written formula, compute the intended cached value by mirroring that formula's own branch logic over the workbook's actual input values, including results that are text or blank; when an IF-style formula returns a source text cell on its failing branch, the cached result for that cell is that text value. Do not skip caching merely because the computed result is not numeric.
- Preserve the valid pattern of writing a formula plus its computed cached result when the task requests a formula.
- Where the task only requires the computed result, the designated cells must contain that computed result so a `data_only` read returns it rather than `None`, except where the task calls for a blank result.
- Before finishing, reopen `OUTPUT_PATH` with `data_only=True` and compare every designated cell with the intended value computed in the program, treating an intended blank as `None` or an empty string; if a designated cell reads as `None` or empty when a non-empty value was intended, or otherwise differs from that intended value, fix how the result is stored and save again. Do not replace an intended blank with a placeholder value merely because the cell reads as empty.
- For a cached aggregate, compare the readback with an independent computation for equality; a non-`None` cache is not sufficient evidence. If the readback is `None` or differs from the intended result (for example, because an injected formula cache did not take effect), store the computed result directly in the cell and save again so a `data_only` read returns it. Keep the formula alongside the stored result only when the readback then matches.
- When a requested result is a multi-cell range and formulas are written into multiple rows or cells, compute the intended result for every designated cell, including cells whose intended result is blank.
- Store a cached result for every designated cell whose formula result is non-empty; for cells whose intended result is blank, leave the cell blank rather than inserting a placeholder value.
- Verify the entire designated range after reopening with `data_only=True`, comparing each cell with the intended result; do not verify only the one row where the aggregate is expected to be nonblank.
- When the instruction shows a value only at qualifying rows, determine every intended non-blank cell from the full actual data (it may be a single aggregate cell or each qualifying row) and compute and cache the value for each; keep only the genuinely non-qualifying cells at their intended blank values, and do not assume the value belongs to a single row.
- Apply this check only to the designated output cells and keep unrelated cells, their formulas, and their formatting unchanged.

---

## Editing an existing formula: literal prefix or suffix

- When the requested change to an existing formula cell is the insertion of a literal prefix, suffix, or other literal text, derive the new cached result by applying the same literal edit to that cell's original `data_only` cached value read from the input workbook, then store the resulting string alongside the edited formula.
- For a pure literal insertion into an existing formula, this literal-edit rule takes precedence over branch mirroring: do not re-derive the result by re-evaluating the edited formula's arguments or references.
- Do not reconstruct such a formula's result by re-parsing its argument list when the formula combines function arguments with concatenation operators or escaped quotes; a re-implementation that yields a different string leaves the cell failing a `data_only` read even though the formula text is correct.
- If the input cell has no cached value to transform, keep the edited formula and do not fabricate a placeholder string as its cached result.

---

## Fill-colour restricted edits

- When the instruction restricts a transformation to cells carrying a particular fill colour such as yellow, decide qualification from the fill openpyxl exposes for each candidate cell in any representation it can appear in (explicit rgb, indexed colour, or theme colour resolved to an RGB value), rather than from one representation only.
- Consider both the cell whose value the transformation edits and other cells of the same row when the highlight is applied across the row rather than to the single target cell.
- If the designated answer region contains cells that the task clearly requires to change but the colour test classifies all of them as unhighlighted, treat that as a detection failure: re-examine the sheet's fill data (theme/indexed colours, row-level styling, conditional formatting) and apply the edit to the cells the highlight actually covers.
- Keep the transformation limited to highlighted cells and leave unhighlighted rows in the range unchanged.

---

## Two-axis matrix from two ranked fields

- When the instruction asks to place values into a rectangular matrix or grid block by combining two ranked input fields, resolve which field maps to the block's rows and which to its columns from the worksheet itself, reading any axis labels, index numbers, or header cells directly above the block's first row and directly left of its first column, instead of assuming the first-named field is horizontal.
- When those neighbouring cells show only rank numbers, treat the numbers as fixing each rank's position along its axis and which corner is the lowest rank, and use a field-name label or axis title at the head of an axis (for example Impact or Likelihood) to decide which field belongs to rows versus columns.
- Validate the resolved orientation against every positional example the instruction states; when the only stated example is symmetric (both ranks equal), use the neighbouring axis labels rather than that example alone to decide the mapping.
- Write every cell of the designated block under one consistent mapping, including cells that receive no combined value, and keep each group of identifiers that share the same rank pair joined in that single cell.

---

## Static date results

- When a task asks to display a date result in a cell as a static value rather than a formula, store the date itself as a literal value carrying a date number format instead of converting it to an Excel serial integer or to a single component such as a day-of-month, unless the instruction explicitly asks for a serial number or that component.
- Derive the value from the final entry the instruction designates when the source order is not sequential, leave the source date cells unchanged, and after reopening the saved file with `data_only=True` confirm the designated cell reads back the intended date value.

## Macro-described transformations

- When an instruction describes a VBA/macro approach for changing a worksheet and the deliverable is the modified workbook with a designated answer region, emulate the described sheet transformation directly with `openpyxl`.
- Do not place macro source code or explanatory script text in the answer range; reserve cell content for the worksheet values the macro would produce unless the instruction explicitly asks to store code text in cells.
- For every cell of the designated block, first derive the value the macro's transformation leaves there from the original worksheet data; do not clear or blank the block before computing it, and hold a cell the transformation does not move at its original value rather than replacing it with code text or a placeholder.
- Apply the transformation to the actual rows the macro would affect and verify the designated block reflects the transformed values while cells the transformation does not move and other worksheets remain unchanged.

---

## Respect an existing destination layout

- When the destination sheet already contains an example or partial result (header text, pre-filled labels, repeated blocks, or the rows that will receive output), read that existing content first and treat it as the specification of the output structure: which column receives which data, the order of blocks, and how many physical rows each source record occupies.
- When the destination table already contains row labels and column headers, derive the complete target block from those existing labels and headers; do not infer target row order from the source table.
- Extend that existing structure in place and write only the cells the instruction assigns; do not delete or clear the destination sheet's rows and regenerate a differently structured sequence.
- For every target coordinate in that block, compute the matched value; if no match exists, write the blank, zero, or error result that the lookup is intended to produce instead of leaving a stale or unconsidered value.
- Do not overwrite existing destination row labels with source labels or mirror source rows unless the destination has no labels and the instruction explicitly requires creating them.
- Treat existing content as a shape reference and, where its values are already the required output, preserve them, but still generate and write every record the instruction requires for rows that are not already populated; do not treat existing data as a reason to skip the required expansion.
- After saving, verify every coordinate in the designated target block, not only the coordinates for which a lookup key was found.

---

## Explicit output start position

- When the task instruction specifies an explicit starting cell or row for the output block, treat that cell (or the first column of that row) as the top-left of the block and write the requested headers and records beginning there; do not shift the block up or down to invent a separate header row.
- Leave cells above the specified start unchanged unless the instruction separately assigns them, and verify the entire designated block including its first row.

---

## Append to an existing destination

- When the task asks to consolidate or add data into the first available blank rows, or otherwise append to an existing destination, determine the last used row in the destination columns and write incoming records immediately after it.
- Preserve every existing destination row and its order; do not rewrite, compact, delete, or restart the incoming list at the top of the sheet because existing rows duplicate, partially match, or differ from the source data.
- Continue adding all required records even when some existing rows already contain equivalent values, and keep cells outside the destination block unchanged.
- Existing destination rows that already match the incoming records, including a block left by an earlier consolidation of the same sources, do not satisfy any part of the requested append: keep them where they are and still write the complete incoming record set immediately after the last used row, instead of writing only the records that do not already appear.

---

## Text-phrase matching and normalization

- When a task asks to find a named phrase in text cells, determine the intended match mode: whole-cell equality when the instruction names a specific text and does not say partial/substring, or containment when it says partial/keyword/contains.
- In either mode, normalize the criterion and each candidate cell for case, leading/trailing whitespace, non-breaking spaces, and repeated internal whitespace before comparing; do not rely on raw exact string equality.
- Write the replacement label only on rows that satisfy the normalized match and leave nonmatching target cells at their required blank/original state; preserve unrelated columns and formatting.

---

## Bounded numeric allocation

- When an instruction requires adjusting bounded numeric columns while preserving zero-valued cells, locate the explicit per-column lower and upper bounds before choosing any capacities by searching every worksheet and the full used range (for example labeled constraint cells, header rows or notes, cell comments, defined names, or a dedicated constraints block), including rows and columns outside the main data table.
- Do not infer a column's minimum or maximum from the minimum and maximum of that column's existing data unless the instruction explicitly defines the current values as the bounds, and do not fall back to those observed extremes merely because labeled bounds were not found on the current sheet; using observed data as bounds can make every adjustment capacity zero or otherwise violate the stated constraints.
- Apply the stated adjustment order (for example left-to-right for positive residuals and right-to-left for negative residuals), keep zero-valued cells unchanged, and use the resolved bounds as hard capacities when distributing the residual.

---

## Inventory allocation from limited stock

- When allocating limited incoming stock from an inventory sheet to order lines, aggregate available quantity by the stock key the instruction uses (for example order number together with item or item code) and keep one remaining-stock balance across all target lines that share that key.
- Process those lines in the priority the instruction states, such as FIFO by the order issued date and then the order-line sequence; do not substitute requested delivery date as the ordering key unless the instruction makes it the allocation priority.
- For each line allocate at most its requested quantity and at most the remaining stock, subtract the allocation, and write 0 when no stock remains.
- Verify every designated result cell, including lines that receive zero, and preserve unrelated cells.

---

## Lookup keys: duplicates and unmatched results

- Before writing a lookup result, check whether the normalized key matches more than one source row.
- If duplicates exist, resolve them according to what the task asks: when the instruction states the current lookup yields wrong results and needs the correct per-record value, and the target and source rows share an additional identifying field (for example name, id, or address) that selects a single source row consistent with the target, use that field; otherwise, when the task asks to reproduce the lookup/formula's defined behavior or no additional field distinguishes the rows, retain the first match and do not overwrite it with a later duplicate.
- If no combination of available fields uniquely identifies a row, fall back to the match semantics specified by the task or formula (for example first match) and preserve the corresponding result rather than inventing a value.
- For a lookup whose requested result is an Excel formula (for example VLOOKUP, INDEX/MATCH, or XLOOKUP), write the value that formula would produce for an unmatched key (for example #N/A) rather than silently blanking the cell or writing None, unless the instruction explicitly asks for blank/no result. For a plain data-transfer or merge where no formula semantics apply, a genuinely absent match should keep the result the merge expects (commonly blank/None) instead of a fabricated error value.
- When the task requires a formula, keep the formula and a consistent cached result for both matched and unmatched cells; do not replace the formula with a literal only for unmatched rows.

---

## Output Requirements

- Save the result to `OUTPUT_PATH`.
- Do not hardcode row counts or column letters — iterate over actual rows in the workbook.
- Preserve sheets and cells not mentioned in the instruction.
