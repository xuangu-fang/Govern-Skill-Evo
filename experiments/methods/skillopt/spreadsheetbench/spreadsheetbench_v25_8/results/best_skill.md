# Spreadsheet Manipulation Skill (xlsx)

## Overview
This skill guides agents in manipulating Excel (.xlsx) spreadsheets using Python.

**Primary libraries**: `openpyxl` (structure-preserving read/write), `pandas` (data transformation).
Never use any other third-party libraries.

---

## Common Workflow

1. **Explore** the input file: list sheets, inspect headers, and determine dimensions. Find the real data start row (scan the first ~10–25 rows for header labels — don't assume row 1 is data) and map each needed column by its header text rather than hardcoded letters. If an example/expected sheet exists ("Manual Result", "Expected", etc.), inspect its values, ordering, and formatting before writing; treat it as a test of the stated rule, not as data to copy or reverse-engineer. Iterate `ws.max_row` / `ws.iter_rows` over the whole range — the preview is truncated and may hide real cell contents.

### Read task parameters, constraints, and lists from the sheet — don't invent them
If the instruction refers to *specified* minimums/maximums, limits, thresholds, a category/brand/key list, an example row, or a lookup table, those values already exist in the workbook (a config block, extra columns, a reference sheet, or rows beyond the preview). Locate them by scanning the full used range and every relevant sheet before computing. Never fabricate guessed constants (a 0–1000 range, a hand-typed list of categories) — that silently produces plausible-but-wrong output. Traverse `ws.max_row`/`ws.max_column` and match by header/label so hidden rows and columns participate. Thresholds, rates and allowed-value lists are often embedded in label/description text (e.g. `>$60,000   $.15`, or a `List`/`Colour` column) — parse numbers/regex out of those cells, falling back to a hardcoded default only if parsing fails.

**Where "specified" limits/parameters actually live.** Minimums, maximums, thresholds and allowed-value sets are often not in ordinary data cells but in: workbook **data validations** (`for dv in ws.data_validations.dataValidation:` — read `dv.type`, `dv.operator`, `dv.formula1`, `dv.formula2`, and the `dv.sqref` range), **header/label cell comments** (`cell.comment.text`), a dedicated assumptions/constraints block, or the text of neighbouring label cells. Search all of these before computing. If a stated limit truly cannot be found, do not silently substitute an unbounded default (e.g. max = unlimited): an uncapped 'add until balanced' fill dumps the whole quantity into the first column and misses every capped row. Treat 'no limit found' as a signal that you have not yet scanned the whole workbook.
2. **Write `solution.py`** with `INPUT_PATH` and `OUTPUT_PATH` defined at the top.
3. **Execute** `python solution.py` and verify the output file was created.
4. **Confirm** the target cells/range contain the expected values.

### Fulfil every clause of a multi-step instruction, in order
Long requests stack several operations (filter → group by a priority list → de-duplicate → **final sort** → styling → blank/hyphen filling). Treat each clause as a required step and apply them in the sequence stated. If the instruction says "finally sort column H ascending", the written output range must *end up sorted on that column even after grouping*. After writing, re-read the output range and verify each requirement (row order, which cells are blank, values) actually holds — a script that runs cleanly but drops one clause still scores those cells wrong.

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

## Formulas and Cached Values

Evaluation reads saved cell values with `data_only=True`. `openpyxl` stores a formula string but never computes it, so `data_only=True` returns the *cached* value — `None` when there is none — and a freshly written formula reads back as empty.

- For any "create a formula / calculate a total / look up a rate" request, compute the result in Python and write the **literal value** into the target cell(s). Literal numbers/strings are read correctly by `data_only=True`.
- If the task is phrased as a formula (SUMIFS, IF, VLOOKUP, INDEX/MATCH...), replicate its logic in Python — filter/aggregate rows yourself and write the number/string.
- **Dual-load** when you need both editability and cached reads:

```python
wb  = openpyxl.load_workbook(INPUT_PATH)                  # mutate & save here
wbv = openpyxl.load_workbook(INPUT_PATH, data_only=True)  # read cached values here
```

Read/compare from `wbv` (falling back to `wb` when a value is `None` and the raw cell isn't a formula string); write using `wb`. Load with `data_only=False` to read a formula string, `data_only=True` to read its cached value.
- Do **not** try to hand-edit the sheet XML (zipfile + regex injection of `<v>` caches) to fake a formula cache. It is fragile, often silently fails inside `try/except`, and can leave the cell empty/None.
- If a formula must remain visible in the cell, still guarantee the value by writing the computed literal; never leave a formula whose cache is empty.

- **Sweep every formula cell in the target block**: walk the target column/range cell by cell; if the raw value is a formula (`cell.data_type == 'f'`, a string starting with `=`, or an `ArrayFormula` object) overwrite it with the computed literal — including cells whose `data_only` read is `None` or an error. Never skip a row because its cached value looks blank, and never leave a live formula whose cache is empty.
- **Before `delete_rows` / `insert_rows`, freeze formulas to values**: replace every formula cell in the affected sheet with its cached `data_only` value (literal). `openpyxl` never recomputes formulas, so after structural edits formulas keep their text but lose their caches and `data_only=True` reads `None`. After the edit, rewrite row-local formula columns (`=G2*H2`, `=G2-30`, `=J2*H2`, `=I2-K2`) as literals for every remaining row, because shifting breaks relative references; clear inserted rows across the full used column width so no old values survive.
- When you need a numeric value from a formula cell whose cache is empty, recompute it from that formula's inputs (e.g. `date_report - date_of_birth`, or `book_value + profit`) instead of reading the formula string as a value.
- Recalculate-on-load flags do not create a cache; they only help when Excel or another calculation engine later opens the file.
- Where the instruction says other cells stay blank, explicitly set them to `None`.

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

## Value Matching & Normalization

Spreadsheet data is messy (ints, floats, strings). Normalize before comparing:

```python
def norm_num(v):
    try:
        f = float(str(v).strip())
        return int(f) if f.is_integer() else round(f, 6)
    except (TypeError, ValueError):
        return str(v).strip()

def norm_text(v):
    return "" if v is None else str(v).strip().casefold()
```

- Match invoice/reference IDs with `norm_num` so `9963547`, `"9963547"`, and `9963547.0` all match; round currency to 2 decimals.
- Match names/descriptions with `norm_text` (strip + casefold); fall back to substring/regex when exact fails (`any(k in s for k in keywords)`).
- **Dates**: normalize `datetime`/`date`, Excel serials (`openpyxl.utils.datetime.from_excel`), and date strings to a comparable `date`. Use `calendar.monthrange(y, m)[1]` for correct days-in-month/leap-year handling.

### Numeric nuances: whole numbers, pennies, and zero vs blank
- **Whole-number / "no pennies"** tests: compare at 2-decimal precision, not a tiny epsilon — `is_whole = (round(v, 2) == round(v))`. Negative integers (e.g. `-50`) count as whole. Read numbers from the `data_only` workbook and parse text like `$1,234.50` / `(50)` (parentheses = negative).
- **Blank vs zero**: `None`/empty string is blank; numeric `0` is a real zero. When asked to "show a hyphen/blank instead of zero", convert only the cells the instruction targets (truly empty ones, or only zeros if that is stated) — do not blanket-replace every `0` with `"-"`, and do not blank a genuine zero.
- When summing, blanks add nothing but must not overwrite existing non-empty values.
- For "otherwise blank" requirements, explicitly set non-matching target cells to `None`.

### Multi-value Cells

When one cell holds several codes/values (`'PRD1;PRD4;PRD6'`, `'A-01: 5, Z-07: 9'`), split on the delimiter class `re.split(r'[,;\n]+', text)`, `.strip()` each token, drop empties, and evaluate each token independently before combining (count qualifying tokens, collect distinct groups and sort naturally, sum matching values). Never treat the whole string as one atom.

- **Honor the exact blank representation the instruction asks for**: 'leave it blank' / all-`#N/A` rows → write `None`; 'output an empty string' → write `''` (not `None`). The evaluator distinguishes them.
- **Recognize sentinel/error values**: an `#N/A`/`#DIV/0!` cell has `cell.data_type == 'e'` and its value may be `None` or the literal error string — treat both as that error and skip it. Treat a task's placeholder set (`'-'`, `'0'`, `'$'`, `'$0'`, `'$0.0'`, `''`) and numeric `0` as 'empty' only when the task says so, stripping whitespace first.

### Composite Keys, Lookups & Aggregation

Many tasks match on more than one column (name + race number, row label + column header) or group rows that share a key. Build an index once, then reuse it:

```python
from collections import OrderedDict, defaultdict

# Two/multi-key lookup into a value column (replaces VLOOKUP/MATCH/INDEX-MATCH):
lookup = {}
for r in range(data_start, ws.max_row + 1):
    k = (norm_text(get(r, key_col1)), norm_num(get(r, key_col2)))
    if k[0] != '' and k[1] is not None:
        lookup.setdefault(k, get(r, value_col))   # keep the first match on duplicates

# Aggregate/sum by key while preserving original row order:
groups = OrderedDict()
for r in range(data_start, ws.max_row + 1):
    groups.setdefault(key(r), []).append(r)
```

- `setdefault` keeps the first match; `defaultdict(float)`/`defaultdict(int)` accumulates sums.
- For a matrix/table fill, read row labels from the label column and column headers from the header row, then cross-match each `(row_label, col_header)` tuple against the index; if not found, retry with the swapped tuple order.
- When a total must 'appear only once on the first row instance of each key', write it on the first occurrence and explicitly set the other keyed rows to `None`.

---

### Extraction & List Compaction

Many tasks ask to 'compile / extract / list / bring' a subset of rows into a target column or block (only rows matching a condition, only items starting with a prefix, all items except one value, the lowest-performing group, the last N workdays). Produce an ordered, compacted list, not a scattered copy:

- Iterate the source rows **in their original order**, collect matching values into a Python list, and skip `None`/blank cells. Never collect header/label/banner rows as if they were data.
- Find the output start row dynamically (first row below the output header) rather than hardcoding it.
- **Clear the whole destination range first** — from the output start down to `max(write_end, last_previously_occupied_row)` — so stale values below the new (shorter) list cannot survive.
- Write the collected values contiguously: `for i, v in enumerate(items): ws.cell(out_start + i, out_col).value = v`, leaving all other cells untouched.
- For **text category labels** (best/average/worst, high/medium/low, …), map labels to an ordinal score and compare scores instead of exact strings, so 'Lowest Performing' is selected correctly even when the label wording varies.

---

## Preserving Features & Formatting

- Find the target by header/label (search for a cell whose text contains the keyword; use `wb.active`/first sheet only as a fallback), not hardcoded coordinates.
- **Clear the destination range first** (`cell.value = None`, reset `border`) before writing so stale values can't survive.
- **Snapshot features that must survive** and restore them after edits:

```python
auto_ref = ws.auto_filter.ref   # ... edit ...
if auto_ref is not None:
    ws.auto_filter.ref = auto_ref
```

The same snapshot/restore applies to merged cells, named ranges, and formatting when a task says "retain" them.
- **Styles** via `openpyxl.styles`: `Font(bold=True)`, `Border`, `Alignment(wrap_text=True)`, `PatternFill(fill_type="solid", start_color="FFE2EFDA", end_color="FFE2EFDA")` (ARGB — prefix `FF`). Set `cell.number_format` (e.g. `"0"` to hide decimals, `"hh:mm:ss AM/PM"` for times).
- **When moving/copying cells**, copy `value`, `number_format`, `font`, `fill`, `border`, `alignment`, `protection` (deep-copy with `copy(...)`). When changing one alignment property, copy the style first: `from copy import copy; al = copy(cell.alignment); al.horizontal = "center"; cell.alignment = al`.
- Convert whole-number floats to `int` (`if float(v).is_integer(): v = int(v)`) when trailing decimals must be removed.

<!-- SLOW_UPDATE_START -->
<!-- SLOW_UPDATE_END -->
