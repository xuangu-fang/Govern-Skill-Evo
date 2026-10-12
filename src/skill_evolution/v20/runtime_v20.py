"""Concrete v20 round and post-generation wiring.

This module keeps the campaign orchestration small while making every stage
explicit: frozen Parent Evolution, current discovery, v20 Fusion, local review
and editing, Candidate replay, private Monitor/Gate, and a compact Memory
update.  Model calls are checkpointed through the existing v19 call helper;
private benchmark artifacts never enter the Memory update.
"""
from dataclasses import dataclass
from pathlib import Path

from ..v19.edit_tracking_v19 import encode, digest
from ..v19.evolution_replay_v19 import _load, _save, run_parent_evolution, load_parent_experiences
from ..v19.memory_generation_v19 import _call, _prepared
from ..v17.experience_cards_v17 import build_experience_cards
from ..v19.current_diagnosis_v19 import build_current_diagnosis_inputs, validate_current_findings
from ..v19.review_prompt_v19 import build_current_diagnosis_request
from .grouping_campaign_v20 import run_campaign_grouping_v20
from .issue_fusion_v20 import build_issue_fusion_input
from .issue_fusion_prompt_v20 import build_issue_fusion_request, check_fusion_response
from .evidence_review_v20 import EvidenceArchive, build_evidence_archive, merge_evidence_archives, validate_evidence_archive
from .local_generation_v20 import build_generation_input
from .campaign_v20 import CampaignRejected


@dataclass(frozen=True)
class V20RuntimeTransports:
    grouping: object = None
    current_diagnosis: object = None
    fusion: object = None
    evidence_review: object = None
    editor: object = None


def build_v20_memory_update(ctx, generation, candidate_summary, gate):
    """Create the minimal structural attempt update for generated edits.

    Semantic issue matching remains Fusion's responsibility.  This helper only
    attaches each generated edit to the selected Memory issue and preserves the
    current finding/generation references for the next local review.
    """
    source = ctx['audit']['source']
    proposals = {item['proposal_issue_id']: item
                 for item in source['fusion_result']['issues']
                 if item['decision'] == 'PROPOSE'}
    proposal_by_memory_issue = {}
    for proposal in proposals.values():
        for issue_ref in proposal.get('memory_issue_refs', []):
            proposal_by_memory_issue.setdefault(issue_ref, proposal)
    existing = {item['issue_id']: item for item in ctx['memory'].memory['issues']}
    review_by_proposal = {
        item['proposal_id']: item for item in ctx['audit'].get('reviews', [])
        if isinstance(item, dict) and item.get('proposal_id')
    }

    def compact(value, limit=700):
        text = ' '.join(str(value or '').split())
        return text if len(text) <= limit else text[:limit - 1] + '…'

    def approach(edit):
        detail = compact(edit.get('after_text'))
        if detail:
            return f"{edit['operation']} Parent guidance: {detail}"
        return edit['operation'] + ' selected Parent rule'

    def assessment(proposal):
        total = candidate_summary.get('task_count')
        success = candidate_summary.get('success_count')
        compliant = candidate_summary.get('compliance_count')
        replay = (f"Candidate replay observed success {success}/{total}, "
                  f"compliance {compliant}/{total}; ") if total else ''
        review = review_by_proposal.get(proposal.get('proposal_issue_id'))
        review_note = ''
        if review:
            review_note = ('Evidence Review ' + review['verdict'] + ': ' +
                           compact(review['reason'], 420) + '; ')
            gap = review.get('gap')
            if isinstance(gap, dict) and gap.get('statement'):
                review_note += 'reviewed gap: ' + compact(gap['statement'], 300) + '; '
        return compact(replay + review_note + 'private Gate decision was ' + gate['decision'] +
                       '; edit-specific effect remains unresolved.', 1000)

    by_issue = {}
    for edit in generation.get('edits', []):
        refs = list(edit.get('memory_issue_refs', []))
        if not refs:
            refs = [item['proposal_issue_id'] for item in proposals.values()
                    if set(edit.get('current_finding_refs', [])) & set(item['current_finding_refs'])]
        for issue_ref in refs:
            proposal = proposals.get(issue_ref) or proposal_by_memory_issue.get(issue_ref)
            existing_issue = existing.get(issue_ref)
            if proposal is None and existing_issue is not None:
                proposal = {'proposal_issue_id': issue_ref, 'issue_statement': existing_issue['problem'],
                            # An old issue source may refer to a prior archive
                            # that is not loaded in this round. The stable issue
                            # identity is the resolvable fallback; do not copy a
                            # stale source into a new attempt.
                            'current_finding_refs': []}
            if proposal is None:
                continue
            source_refs = list(proposal.get('current_finding_refs', [])) or [
                proposal['proposal_issue_id']]
            row = by_issue.setdefault(issue_ref, {'proposal': proposal, 'attempts': [], 'source_refs': []})
            row['source_refs'].extend(ref for ref in source_refs if ref not in row['source_refs'])
            row['attempts'].append({'new_attempt_key': ctx['round_id'] + ':' + edit['edit_id'],
                'approach': approach(edit),
                'assessment': assessment(proposal),
                'edit_refs': [edit['edit_id']], 'source_refs': source_refs})
    updates = []
    for issue_ref, row in sorted(by_issue.items()):
        proposal = row['proposal']
        if issue_ref in existing:
            updates.append({'issue_id': issue_ref, 'source_refs': row['source_refs'],
                            'attempts': row['attempts']})
        else:
            updates.append({'new_issue_key': issue_ref,
                'problem': proposal['issue_statement'],
                'source_refs': row['source_refs'] or [proposal['proposal_issue_id']],
                'attempts': row['attempts']})
    return {'schema_version': 'issue_memory_update_v20.1', 'run_id': ctx['run_id'],
            'round_id': ctx['round_id'], 'issues': updates}


def _call_json(path, request, transport):
    raw = _call(Path(path), _prepared(request), transport)
    if not isinstance(raw, str):
        raise CampaignRejected('model transport must return JSON text')
    return raw


def _current_findings(*, root, requests, transport):
    findings = []
    for index, request in enumerate(requests):
        prompt = build_current_diagnosis_request(request)
        raw = _call_json(root / f'current-{index:03d}', prompt, transport)
        result = validate_current_findings(raw, request=request)
        _save(root / f'current-{index:03d}-findings.json', result.payload)
        findings.append(result)
    return tuple(findings)


def _finding_records(findings):
    """Project validated current Findings into durable archive records."""
    records = []
    for result in findings:
        payload = result.payload if hasattr(result, 'payload') else result
        for finding in payload['findings']:
            records.append({
                'ref': finding['finding_id'],
                'kind': 'FINDING',
                'statement': finding['statement'],
                'evidence_refs': list(finding['evidence_refs']),
                'counterevidence_refs': (list(finding['evidence_refs'])
                                         if finding['kind'] == 'COUNTEREVIDENCE' else []),
                'edit_refs': [],
                'source_refs': [],
            })
    return records


def _fusion_records(fusion_result):
    """Make proposal identities resolvable when a historical issue has no new Finding."""
    records = []
    for issue in fusion_result.payload['issues']:
        if issue['decision'] != 'PROPOSE':
            continue
        records.append({
            'ref': issue['proposal_issue_id'],
            'kind': 'REVIEW',
            'statement': issue['issue_statement'],
            'evidence_refs': [],
            'counterevidence_refs': [],
            'edit_refs': [],
            'source_refs': list(issue['current_finding_refs']),
        })
    return records


def _saved_round_archive(round_root):
    """Load a saved archive, with a one-time fallback for round-01 artifacts."""
    saved = round_root / 'evidence-archive.json'
    if saved.exists():
        return validate_evidence_archive(EvidenceArchive(encode(_load(saved))))
    generation = round_root / 'generation-input.json'
    if not generation.exists():
        return None
    payload = _load(generation).get('archive')
    if not isinstance(payload, dict):
        return None
    # Older v20 rounds persisted the event archive inside generation-input but
    # omitted the Finding records that Memory later referenced. Reconstruct
    # those records from their validated current Findings checkpoints.
    records = dict(payload.get('records', {}))
    for path in sorted(round_root.glob('current-*-findings.json')):
        result = _load(path)
        for record in _finding_records((result,)):
            existing = records.get(record['ref'])
            if existing is not None:
                if existing != record:
                    raise CampaignRejected('historical Finding record conflict')
            else:
                records[record['ref']] = record
    repaired = dict(payload)
    repaired['records'] = records
    archive = validate_evidence_archive(EvidenceArchive(encode(repaired)))
    audit = round_root / 'generation' / 'generation-audit.json'
    if audit.exists():
        result = _load(audit).get('result', {})
        edits = result.get('edits', []) if isinstance(result, dict) else []
        if edits:
            archive = merge_evidence_archives(
                archive, build_evidence_archive(run_id=payload['run_id'], edits=edits))
    return archive


def _historical_archives(round_root):
    """Return committed prior-round archives without expanding the model view."""
    parent = round_root.parent
    archives = []
    for candidate in sorted(parent.glob('round-*')):
        if candidate == round_root or not candidate.is_dir():
            continue
        try:
            if int(candidate.name.rsplit('-', 1)[1]) >= int(round_root.name.rsplit('-', 1)[1]):
                continue
        except (ValueError, IndexError):
            continue
        archive = _saved_round_archive(candidate)
        if archive is not None:
            archives.append(archive)
    return tuple(archives)


def build_v20_round_factory(*, benchmark, transports=None):
    """Build the real campaign ``round_factory`` for a frozen benchmark adapter."""
    transports = transports or V20RuntimeTransports()

    def factory(ctx):
        root = Path(ctx['root'])
        root.mkdir(parents=True, exist_ok=True)
        parent_dir = root / 'parent_evolution'
        run_parent_evolution(run_id=ctx['run_id'], round_id=ctx['round_id'],
                             parent_skill=ctx['parent_skill'], backend=benchmark.evolution,
                             artifact_dir=parent_dir, max_workers=benchmark.config['max_workers'],
                             resume=parent_dir.exists())
        sources, scope = load_parent_experiences(run_id=ctx['run_id'], round_id=ctx['round_id'],
                                                  parent_skill=ctx['parent_skill'],
                                                  backend=benchmark.evolution, artifact_dir=parent_dir)
        batch = build_experience_cards(sources, scope=scope)
        grouping = run_campaign_grouping_v20(
            batch, scope=scope, artifact_dir=root / 'grouping',
            transport=transports.grouping,
            resume=(root / 'grouping').exists())
        requests = build_current_diagnosis_inputs(run_id=ctx['run_id'], round_id=ctx['round_id'],
                                                   parent_skill=ctx['parent_skill'],
                                                   backend=benchmark.evolution,
                                                   parent_dir=parent_dir,
                                                   grouping_result=grouping)
        findings = _current_findings(root=root, requests=requests,
                                     transport=transports.current_diagnosis)
        fusion_input = build_issue_fusion_input(
            memory=ctx['memory'], current_requests=requests, current_findings=findings,
            parent_skill=ctx['parent_skill'], run_id=ctx['run_id'], round_id=ctx['round_id'])
        fusion_request = build_issue_fusion_request(fusion_input)
        raw_fusion = _call_json(root / 'issue-fusion', fusion_request, transports.fusion)
        fusion_result = check_fusion_response(raw_fusion, request=fusion_input, wire=True)
        _save(root / 'issue-fusion-result.json', fusion_result.payload)
        experiences = [e for request in requests for e in request.payload['experiences']]
        contexts = [c for request in requests for c in request.payload['contexts']]
        current_archive = build_evidence_archive(
            run_id=ctx['run_id'], experiences=experiences, contexts=contexts,
            records=_finding_records(findings) + _fusion_records(fusion_result))
        archive = merge_evidence_archives(*_historical_archives(root), current_archive)
        _save(root / 'evidence-archive.json', archive.payload)
        source = build_generation_input(memory=ctx['memory'], fusion_input=fusion_input,
                                       fusion_result=fusion_result,
                                       parent_skill=ctx['parent_skill'], archive=archive,
                                       current_requests=requests, current_findings=findings)
        _save(root / 'generation-input.json', source.payload)
        generation_audit = None
        audit_path = root / 'generation' / 'generation-audit.json'
        if audit_path.exists():
            generation_audit = _load(audit_path)
        return {'source': source, 'generation_audit': generation_audit,
                'review_transport': transports.evidence_review,
                'editor_transport': transports.editor}

    return factory


def build_v20_post_generation(*, benchmark, memory_update=None):
    """Build the real Candidate replay + private Gate callback.

    ``memory_update`` is deliberately a caller-owned semantic mapper.  The
    runtime supplies the complete generation and private benchmark summaries;
    it does not infer issue meaning from Gate labels.
    """
    def post(ctx):
        generation = ctx['audit']['result']
        candidate = ctx['candidate_skill']
        archive_path = Path(ctx['root']) / 'evidence-archive.json'
        if archive_path.exists() and generation.get('edits'):
            archive = EvidenceArchive(encode(_load(archive_path)))
            archive = merge_evidence_archives(
                archive, build_evidence_archive(run_id=ctx['run_id'], edits=generation['edits']))
            _save(archive_path, archive.payload)
        candidate_summary = benchmark.run_candidate_evolution(
            run_id=ctx['run_id'], round_id=ctx['round_id'],
            parent_skill=ctx['parent_skill'], candidate_skill=candidate,
            parent_dir=Path(ctx['root']) / 'parent_evolution',
            artifact_dir=Path(ctx['root']) / 'candidate_evolution')
        attribution = benchmark.build_local_attribution(
            generation=generation, candidate_summary=candidate_summary)
        _save(Path(ctx['root']) / 'local-attribution.json', attribution)
        gate = benchmark.run_private_gate_v20(
            run_id=ctx['run_id'], round_id=ctx['round_id'],
            parent_skill=ctx['parent_skill'], candidate_skill=candidate,
            artifact_dir=Path(ctx['root']) / 'monitor_private')
        update = (memory_update(ctx, generation, candidate_summary, gate)
                  if memory_update is not None else
                  build_v20_memory_update(ctx, generation, candidate_summary, gate))
        return {'gate': gate, 'memory_update': update,
                'candidate_summary': candidate_summary, 'attribution': attribution}

    return post
