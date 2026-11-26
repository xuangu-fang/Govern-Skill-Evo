"""Review actual V26 answers against the new release, without changing scoring.

The task-specific extraction patterns below describe manually inspected historical
answers. They are counterfactual audit cases, NOT a deployable scoring function.
Changed tasks' old executions are explicitly not evaluations of their new versions.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys
from decimal import Decimal

from .prepare import deny_network
from .prepare_release_20261029 import REVISION, CAMPAIGN, store


FORMAT_CASES = {
    'UID0031': (r'^Around fiscal year (\d{4})\b', 'Year repeated in explanatory prose; grounding remains separate'),
    'UID0044': (r'^(?:Net capital inflow of )?([\d,]+) thousand', 'Requested thousands value plus inflow wording and an equivalent alternate unit'),
    'UID0063': (r'^([\d,]+) thousand U\.S\. dollars', 'Requested thousands value plus unit wording and an equivalent alternate unit'),
    'UID0065': (r'^([\d.]+) percentage points$', 'Percentage-point label; new question clarifies data vintage'),
    'UID0085': (r'^\+?([\d.]+) percentage points$', 'Leading plus and percentage-point label'),
    'UID0122': (r'^([\d.]+) percentage points$', 'Percentage-point label'),
    'UID0228': (r'^([\d,.]+) million INR$', 'Requested numeric magnitude plus currency label; exchange-rate grounding remains unresolved'),
    'UID0086': (r'^([\d.]+)%$', 'Percent sign on a numeric percentage answer'),
    'UID0220': (r'^([\d.]+)%$', 'Percent sign and trailing zero; Candidate 31.3 is NOT equivalent'),
}


def run(root):
    from skilladam.benchmarks.officeqa.evaluation import exact_match, token_f1
    from skilladam.benchmarks.officeqa.tool_runtime import _render_parsed_page
    from src.adapters.officeqa.data import Dataset

    release = root / 'data/officeqa/releases' / REVISION
    old = Dataset(root / 'data/officeqa/prepared_v2')
    new = Dataset(release / 'prepared')
    prep = json.loads((release / 'preparation_report.json').read_text())
    campaign = root / 'experiments/campaigns' / CAMPAIGN
    records, summaries, hashes = [], {}, {}
    for rd in sorted((campaign / 'rounds').glob('R*')):
        summary = {}
        for side in ['parent', 'candidate']:
            path = rd / (side + '_runs') / 'records.json'
            hashes[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
            source = json.loads(path.read_text())
            counts = {'count': len(source), 'original_em': 0, 'latest_gold_old_em': 0,
                      'old_gold_format_counterfactual': 0, 'latest_gold_format_counterfactual': 0}
            for row in source:
                uid, execution = row['task_id'], row['execution']
                answer = execution['answer']
                old_gold = old.rows[uid]['ground_truth']
                new_gold = new.rows[uid]['ground_truth']
                original_score = exact_match(answer, old_gold)
                if execution['metrics'] != {'em': original_score, 'f1': token_f1(answer, old_gold)}:
                    raise ValueError('Historical score reproduction failed')
                canonical = None
                if original_score == 0 and uid in FORMAT_CASES:
                    match = re.search(FORMAT_CASES[uid][0], answer)
                    if match:
                        canonical = match[1].replace(',', '')
                        if Decimal(canonical) != Decimal(old_gold.replace(',', '')):
                            raise ValueError('Reviewed formatting case has a different number')
                old_format = float(Decimal(canonical) == Decimal(old_gold.replace(',', ''))) if canonical else original_score
                latest_score = exact_match(answer, new_gold)
                latest_format = float(Decimal(canonical) == Decimal(new_gold.replace(',', ''))) if canonical else latest_score
                changed = prep['changes'].get(uid, {})
                records.append({
                    'round': rd.name, 'side': side, 'task_id': uid, 'answer': answer,
                    'old_gold': old_gold, 'latest_gold': new_gold,
                    'original_em': original_score, 'latest_gold_old_em': latest_score,
                    'format_only_canonical': canonical,
                    'format_review_note': FORMAT_CASES[uid][1] if canonical else None,
                    'old_gold_format_counterfactual': old_format,
                    'latest_gold_format_counterfactual': latest_format,
                    'changed_fields': sorted(changed),
                    'valid_execution_of_latest_task': not bool(changed),
                })
                for key, value in [('original_em', original_score), ('latest_gold_old_em', latest_score),
                                   ('old_gold_format_counterfactual', old_format),
                                   ('latest_gold_format_counterfactual', latest_format)]:
                    counts[key] += int(value)
            summary[side] = counts
        summary['counterfactual_gate_latest_gold_and_reviewed_format'] = (
            'ACCEPT' if summary['candidate']['latest_gold_format_counterfactual'] >
            summary['parent']['latest_gold_format_counterfactual'] else 'RETAIN')
        summaries[rd.name] = summary

    parsed = root / 'data/officeqa/corrected_v2/treasury_bulletins_parsed/jsons'
    judiciary, year_series = [], {}
    for name, page, year, count in [('1985_03', 22, 1984, 12), ('1986_03', 26, 1985, 12),
                                     ('1987_03', 24, 1986, 12), ('1988_03', 36, 1987, 3)]:
        lines = _render_parsed_page(str(parsed / f'treasury_bulletin_{name}.json'), page).splitlines()
        start = next(i for i, line in enumerate(lines) if line.startswith(f'| {year}-Jan'))
        values = [float(line.strip('|').split('|')[2].strip().replace(',', '')) for line in lines[start:start+count]]
        if len(values) != count:
            raise ValueError('Incomplete monthly series')
        year_series[str(year)] = values
        judiciary.extend(values)
    reserves = []
    for name, page, years in [('1987_12', 69, range(1983, 1987)), ('1992_12', 84, range(1987, 1991))]:
        lines = _render_parsed_page(str(parsed / f'treasury_bulletin_{name}.json'), page).splitlines()
        for year in years:
            line = next(line for line in lines if re.match(rf'^\| {year}r? \|', line))
            reserves.append(float(line.strip('|').split('|')[1].strip().replace(',', '')))
    lines = _render_parsed_page(str(parsed / 'treasury_bulletin_1970_10.json'), 35).splitlines()
    rea = [float(next(line for line in lines if line.startswith(f'| {year} |')).strip('|').split('|')[4].strip().replace(',', ''))
           for year in range(1961, 1971)]
    mean = statistics.mean(rea)
    numeric_reviews = {
        'UID0018': {'monthly_values_by_year': year_series, 'count': len(judiciary),
                    'geometric_mean': math.exp(statistics.mean(math.log(x) for x in judiciary)),
                    'latest_gold': new.rows['UID0018']['ground_truth']},
        'UID0092': {'annual_total_reserves': reserves, 'population_stddev': statistics.pstdev(reserves),
                    'sample_stddev': statistics.stdev(reserves), 'latest_gold': new.rows['UID0092']['ground_truth']},
        'UID0041': {'annual_rea_holdings': rea, 'theil_T_natural_log': statistics.mean(x/mean*math.log(x/mean) for x in rea),
                    'theil_L_natural_log': statistics.mean(math.log(mean/x) for x in rea),
                    'latest_gold': new.rows['UID0041']['ground_truth']},
    }
    for value in numeric_reviews.values():
        value['status'] = 'Recomputed from parsed cited tables; discrepancy confirmed, root cause not proven. Verify original PDF/definition before changing gold.'

    issues = {
        'changed_training_tasks_rerun': {uid: prep['changes'][uid] for uid in sorted(set(new.splits['train'] + new.splits['validation']) & set(prep['changes']))},
        'parsed_numeric_reference_discrepancies': numeric_reviews,
        'chart_evidence_review': ['UID0030', 'UID0031', 'UID0110'],
        'external_operand_or_period_coverage_review': ['UID0150', 'UID0162', 'UID0165', 'UID0213', 'UID0228'],
        'mathematical_definition_review': ['UID0240'],
        'observed_model_numeric_improvements_not_scorer_fixes': ['UID0202', 'UID0229', 'UID0159'],
        'fix_proposal': [
            'Keep the downloaded latest answer key unchanged until source evidence establishes a correction.',
            'Add a numeric-equivalence path only for the observed scalar/year answers, using requested units and decimal comparison; keep legacy EM for audit.',
            'Handle percent/percentage-point labels, thousands separators, optional leading plus/trailing zeros and the observed unit words; do not add broad numerical tolerance.',
            'Review explicitly equivalent alternate-unit parentheticals in UID0044/UID0063 and the explanatory year answer in UID0031; do not use arbitrary number containment.',
            'Use the same corrected success metric in runtime evaluation, Gate and model-visible feedback; do not leave old F1 as contradictory correctness evidence.',
            'Rerun changed questions and sources in a fresh experiment; the tables below only describe rescoring existing outputs, not new-version model performance.',
        ],
    }
    format_records = [x for x in records if x['format_only_canonical'] is not None]
    totals = {side: {key: sum(s[side][key] for s in summaries.values()) for key in
              ['count', 'original_em', 'latest_gold_old_em', 'old_gold_format_counterfactual', 'latest_gold_format_counterfactual']}
              for side in ['parent', 'candidate']}
    if len(records) != 148 or len(format_records) != 13:
        raise ValueError('Unexpected historical audit coverage')
    for path, expected in hashes.items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != expected:
            raise ValueError('Historical training artifact changed')
    result = {
        'scope': 'Actual eight-round training outputs; latest dataset prepared, scorer unchanged; no generation',
        'latest_revision': REVISION, 'source_campaign': str(campaign),
        'records_checked': len(records), 'format_false_negative_records': len(format_records),
        'format_false_negative_task_ids': sorted({x['task_id'] for x in format_records}),
        'totals': totals, 'round_summaries': summaries, 'issues': issues, 'records': records,
        'source_record_sha256': hashes, 'source_records_unchanged': True,
        'limitations': ['Counterfactual scoring is a manually reviewed sample, not a new general scorer.',
                       'Changed tasks require fresh runs; this is not a latest-benchmark evaluation.',
                       'The evolving Parent/Candidate aggregate is not final-Skill test accuracy.',
                       'Matching the answer key does not establish evidence-grounded reasoning.'],
        'scorer_modified': False, 'model_calls': 0, 'experiment_runs': 0,
    }
    out = root / 'artifacts/analysis/officeqa_latest_training_audit_20261029/report.json'
    store(out, result)
    print(json.dumps({'report': str(out), 'format_records': len(format_records), 'format_ids': result['format_false_negative_task_ids'],
                      'totals': totals, 'numeric_reviews': numeric_reviews}, ensure_ascii=False))


if __name__ == '__main__':
    sys.addaudithook(deny_network)
    run(Path(__file__).resolve().parents[3])
