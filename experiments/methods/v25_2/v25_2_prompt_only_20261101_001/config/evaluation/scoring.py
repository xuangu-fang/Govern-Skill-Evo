"""Saved-value scoring, following the local SkillOpt/SkillAdam comparison semantics.

No formula engine and no expected-value strings in the returned score view.
"""
import datetime
import re
import openpyxl
from openpyxl.utils.cell import range_boundaries, get_column_letter


def transform(value):
    if isinstance(value, (bool, int, float)):
        return round(float(value), 2)
    if isinstance(value, datetime.time):
        return str(value)[:-3]
    if isinstance(value, datetime.datetime):
        delta = value-datetime.datetime(1899, 12, 30)
        return round(delta.days+delta.seconds/86400.0, 0)
    if isinstance(value, str):
        try: return round(float(value), 2)
        except ValueError: pass
    return value


def equal(a, b):
    a, b = transform(a), transform(b)
    if a in ('', None) and b in ('', None): return True
    return type(a) is type(b) and a == b


def regions(answer_region):
    # Each region has an explicit sheet and range. A comma before ! belongs to
    # the sheet name; one after the cell range starts the next region. Edge
    # quotes tolerate the existing dataset's loosely quoted coordinates.
    result = [];rest=answer_region.strip()
    while rest:
        match=re.match(r'(.+?)!([^,]+)(?:,|$)',rest)
        if match is None:raise ValueError('Invalid explicit answer region')
        sheet,cells=match.groups();rest=rest[match.end():]
        if not sheet.strip() or not cells.strip():raise ValueError('Invalid explicit answer region')
        sheet = sheet.strip().strip("'\"").replace("''", "'")
        cells = cells.strip().strip("'\"")
        # Dataset shorthand: BD2:308 means BD2:BD308, never an empty range.
        shorthand=re.fullmatch(r'([A-Za-z]+)([1-9][0-9]*):([1-9][0-9]*)',cells)
        if shorthand:
            col,start,end=shorthand.groups();cells=f'{col}{start}:{col}{end}'
        bounds = range_boundaries(cells)
        if re.fullmatch(r'[A-Za-z]+:[A-Za-z]+',cells):
            # Resolve the final row against BOTH workbooks in score().
            if bounds[2]<bounds[0]:raise ValueError('Reversed column range')
            result.append((sheet,(bounds[0],1,bounds[2],None)));continue
        if any(v is None for v in bounds) or min(bounds)<1 or bounds[2] < bounds[0] or bounds[3] < bounds[1]:
            raise ValueError('Invalid bounded answer region')
        result.append((sheet, bounds))
    if not result: raise ValueError('Empty answer region')
    return result


def score(output, answer, answer_region, profile):
    gold = openpyxl.load_workbook(answer, data_only=True)
    pred = None
    try:
        if output is not None: pred = openpyxl.load_workbook(output, data_only=True)
        correct, total, wrong, missing = 0, 0, [], []
        for sheet, (c1, r1, c2, r2) in regions(answer_region):
            if sheet not in gold.sheetnames: raise ValueError('Answer region worksheet missing from reference')
            absent = pred is None or sheet not in pred.sheetnames
            if r2 is None:
                r2=max(gold[sheet].max_row or 1,1 if absent else (pred[sheet].max_row or 1))
            if absent and sheet not in missing: missing.append(sheet)
            for col in range(c1, c2+1):
                for row in range(r1, r2+1):
                    total += 1
                    if not absent and equal(gold[sheet].cell(row,col).value, pred[sheet].cell(row,col).value):
                        correct += 1
                    else: wrong.append(f'{sheet}!{get_column_letter(col)}{row}')
        result = dict(hard=int(correct == total), per_cell_pass_rate=round(correct/total,4),
                      correct_cells=correct, total_cells=total,
                      mismatched_cells=wrong, mismatched_cells_total=len(wrong),
                      missing_sheets=missing, missing_sheets_total=len(missing))
        return result
    finally:
        gold.close()
        if pred is not None: pred.close()


def model_view(result, profile):
    return {**result, 'mismatched_cells': result['mismatched_cells'][:profile['score_coordinate_limit']],
            'missing_sheets': result['missing_sheets'][:profile['score_missing_sheet_limit']]}
