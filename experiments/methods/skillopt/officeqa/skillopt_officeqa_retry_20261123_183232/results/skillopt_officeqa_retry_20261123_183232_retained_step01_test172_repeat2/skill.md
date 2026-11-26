# OfficeQA Skill

## Retrieval Discipline
- Start by narrowing to the most likely candidate file before reading long passages.

- Confirm the exact document path before searching. The document tools require the full docs-root path (e.g., `<officeqa-docs>/treasury_bulletin_YYYY_MM.txt`); a bare filename or `**/filename` can return 'no matches' or 'path not allowed'. Run a single glob (`*`, `*.txt`, or `*YYYY*`) to discover the mounted directory/prefix, then reuse that exact full path for every grep/read; stop globbing once a working path is found and do not probe absolute or personal-machine paths. If local path access remains unavailable, use supplied oracle parsed pages and source hints as primary evidence, extracting from them first and using file tools only to confirm or fill gaps.
- Match the retrieval surface to the data shape: some series (e.g., quarterly GDP in the 'Profile of the Economy' narrative) are described only relative to a chart and are not tabulated in text. If targeted searches for the values fail, do not guess and do not chase `.pdf`/`.png`/`.jpg` scans; look for an adjacent data table or figure data elsewhere in the same bulletin, and if none exists state that the series is not textually available. Keep tool turns bounded; prefer a few targeted greps over speculative globbing.
- Prefer targeted search terms that name the exact entity, period, measure, or table concept from the question.
- After a promising match, read only a small surrounding span and verify it matches the requested year, basis, and unit.

- Use source hints and oracle page numbers to jump to the likely table, then grep the exact table title or a distinctive column phrase rather than a generic entity word.
- Search numbers without thousands separators: parsed tables often strip commas and trailing decimal zeros, so grep `3554` not `3,554`.
- When a page holds several tables, or one table has multiple row sections (fiscal year vs. calendar year vs. month) or parallel tables in different units, confirm the section, header hierarchy, row key, measure column, unit, and basis that match the question before extracting any number; ignore adjacent fiscal-year, calendar-year, percent, and total columns unless explicitly named.
- In flattened multi-period tables where period headers are lost, read a short span around the header row to verify row/column mapping instead of assuming the first numeric block is the requested year.
- Use OCR-tolerant matching for dates and labels: try partial tokens or the nearest date (e.g. 12/18 vs. 12/19) and inspect issue or maturity context to confirm the row.

## Evidence Discipline
- Extract the exact value from the retrieved text before doing any arithmetic.
- Keep track of each operand's period, unit, and semantic role so nearby proxy values are not mixed in.
- If the question asks for a transformed or derived quantity, compute only after confirming every operand.

- Read the table title/unit line and every footnote: qualifiers such as 'includes emergency ship construction', 'due or callable 20 years and after', 'population standard deviation', 'nominal', or 'as published in the subsequent quarter' determine which column or value is valid. Never use a figure without checking the footnote that governs it.
- In wide tables with stacked multi-level headers, locate the target column by counting across every header row; confirm the measure's exact basis (e.g., 'net of refunds' is the net column, not gross collections).
- Never substitute a value from memory (exchange rates, CPI/index levels) or from an adjacent period: every operand must be traceable to a retrieved span or the provided oracle parsing. If a required year/measure is genuinely absent from the provided files, state that it is unavailable rather than reusing the nearest year's figure.

## Final Answer Discipline
- Return the final answer only after one last consistency check against the retrieved evidence.
- Copy the final answer from a checked value, not from an unverified intermediate guess.

## Derived-Quantity Discipline
- For regression, geometric mean, coefficient of variation, exponential smoothing, percentile/VaR, currency conversion, or other derived statistics, first list every required input (all raw observations, projection/confidence parameters, and auxiliary rates). Write out the complete ordered operand list with periods and units, confirm the count matches the requested span (e.g., 8 annual values, 39 months), and fix the formula up front (population vs sample standard deviation; product/root vs log-mean).
- When a range spans multiple bulletin issues, take each period from the issue that reports it as a final (not preliminary/estimate) value, and count any overlapping anchor period (e.g. a month-end shown in two issues, or a fiscal year repeated across bulletins) only once; keep units consistent (thousands vs millions) through the whole calculation.
- Auxiliary parameters such as foreign-exchange rates often sit in a separate section or table of the same bulletin (e.g., 'Foreign Exchange Rates', 'Foreign Currency Positions'); search those by concept rather than concluding they are absent.
- For rolling-window questions, reuse overlapping monthly rows and add or remove only the endpoint months. If a table reports cumulative values, difference consecutive rows to obtain monthly changes; for z-score/unusualness questions, use exactly the stated comparison months and compute mean and standard deviation from those increments.
- Prefer a directly stated aggregate in prose over reconstructing it from unrelated table rows.
- Compute step by step, sanity-check magnitude/sign against the data, and re-derive once before answering. Confirm the requested rounding (e.g., three decimals, nearest hundredth, tenths) and unit (percentage points, percent, thousands, billions).
- Never emit a numeric final answer while a required operand is unlocated; keep searching the document or state the missing input instead of guessing a plausible-looking value.
- Respect explicit answer shapes: if the question asks for a bracketed list of N comma-separated values, emit exactly that format inside the final <answer> tag; if a single value, give only that value.
