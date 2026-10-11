"""Independent v19 orchestration. Memory head is the sole commit authority.

Engineering transports may be injected; real entrypoint uses frozen benchmark v4
and isolated private Monitor. No Monitor trajectories or scores reach learners.
"""
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
import uuid

from .edit_tracking_v19 import encode,digest
from .evolution_replay_v19 import (_load,_save,_file_digest,_lock,run_parent_evolution,
                                    load_parent_experiences,run_candidate_replay)
from .experience_cards_v17 import build_experience_cards
from .grouping_campaign_v19 import run_campaign_grouping
from .memory_generation_v19 import run_memory_generation
from .attribution_dispatch_v19 import run_attribution
from .memory_store_v19 import (initialize_memory,load_memory,commit_round_memory,require,
                               _durable_save,_sync_directory)
from .monitor_campaign_v19 import run_private_monitor,load_private_monitor

ROOT=Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class CampaignTransports:
    grouping: object=None
    diagnosis: object=None
    editor: object=None
    attribution: object=None
    memory_review: object=None
    reconciliation: object=None
    issue_fusion: object=None
    evidence_review: object=None


def campaign_config(*,pilot=False,max_workers=8,generation_protocol="legacy",attribution_protocol="pair"):
    require(type(pilot) is bool and type(max_workers) is int and 1<=max_workers<=32,'invalid campaign options')
    require(generation_protocol in ('legacy','separated','local'),'unknown generation protocol')
    require(attribution_protocol in ('pair','legacy'),'unknown Attribution protocol')
    config = {'schema_version':'campaign_config_v19.1','mode':'PILOT' if pilot else 'FORMAL',
            'round_limit':2 if pilot else 4,'max_workers':max_workers,'max_grouping_chars':400000,
            'retrieval':{'query':'','edit_ids':[], 'max_rounds':None,'max_memory_chars':None,'max_input_chars':None}}
    if generation_protocol!='legacy':
        config['generation_protocol']=generation_protocol
    if attribution_protocol != 'legacy':
        config['attribution_protocol']=attribution_protocol
    return config


def source_manifest():
    paths=sorted((ROOT/'src/skill_evolution').glob('*v19.py'))+[ROOT/'scripts/run_v19_v4.py',ROOT/'scripts/run_v19.py',ROOT/'scripts/migrate_v19_memory_restart.py',ROOT/'scripts/migrate_v19_attribution_memory.py',ROOT/'scripts/migrate_v19_review_repair.py']
    return {str(p.relative_to(ROOT)):_file_digest(p) for p in paths}


def _binding(config,run_id,initial_skill,evolution,monitor):
    require(type(run_id) is str and bool(run_id.strip()) and type(initial_skill) is str,'run identity/initial Skill required')
    require(config==campaign_config(pilot=config.get('mode')=='PILOT',max_workers=config.get('max_workers'),generation_protocol=config.get('generation_protocol','legacy'),attribution_protocol=config.get('attribution_protocol','legacy')),
            'campaign config differs from v19 protocol')
    evo,mon=evolution.manifest(),monitor.manifest()
    require(evo['schema_version']=='evolution_manifest_v19.1' and mon['schema_version']=='monitor_manifest_v19.1',
            'Evolution/Monitor manifests required')
    require(not set(evo['task_ids']) & set(mon['task_ids']),'Evolution and Monitor tasks overlap')
    require(evo['seed']==mon['seed'],'Evolution and Monitor seed mismatch')
    return {'schema_version':'campaign_binding_v19.1','run_id':run_id,'config':config,
            'initial_skill':initial_skill,'initial_skill_sha256':digest(initial_skill),
            'evolution_manifest':evo,'monitor_manifest':mon,'source_files':source_manifest()}


def _round_result(row):
    record=row['record']
    return {'round_id':record['round_id'],'status':'COMMITTED','decision':record['gate_decision'],
            'memory_ref':{'artifact_id':record['memory_record_id'],'sha256':digest(encode(record))},
            'retained_skill_sha256':record['retained_skill_ref']['sha256']}


def _round_result_record(record):
    return {'round_id':record['round_id'],'status':'COMMITTED','decision':record['gate_decision'],
            'memory_ref':{'artifact_id':record['memory_record_id'],'sha256':digest(encode(record))},
            'retained_skill_sha256':record['retained_skill_ref']['sha256']}


def _report_after_commit(snapshot, *, output, round_root, commit_ref, ledger):
    """Extend the already loaded compact snapshot without replaying the archive.

    The final round's archive is trusted by ``commit_round_memory``.  Only its
    record, attribution summary, and the new head are read here; historical
    replay files are deliberately not traversed again.
    """
    report=campaign_report(snapshot,status='RUNNING')
    record=_load(output/'memory'/'rounds'/commit_ref['sha256']/'record.json')
    edits=ledger.payload['edits']
    attribution=_load(round_root/'attribution'/'attributions.json')['records']
    prior={e['edit_id']:(r['record']['gate_decision'],r)
           for r in snapshot.rounds for e in r['edits']}
    links=[]
    for edit in edits:
        for link in edit['related_history']:
            decision,old=prior[link['prior_edit_id']]
            links.append({'new_edit_id':edit['edit_id'],'prior_edit_id':link['prior_edit_id'],
                'relation':link['relation'],'origin_gate_decision':decision,
                'historical_effects':[a['effect'] for a in old['attribution']['records']
                                      if 'effect' in a and link['prior_edit_id'] in a['edit_ids']],
                'interpretation':'REAUTHORIZED_INTENT_NOT_PROVEN_CORRECTION'})
    head=_load(output/'memory'/'head.json')
    counts=Counter(report['attribution_effect_counts'])
    counts.update(a['effect'] for a in attribution if 'effect' in a)
    report.update(committed_rounds=report['committed_rounds']+1,
                  memory_head_ref=head['memory_ref'],
                  retained_skill_sha256=head['retained_skill_ref']['sha256'],
                  rounds=report['rounds']+[_round_result_record(record)],
                  cross_round_links=report['cross_round_links']+links,
                  attribution_effect_counts=dict(counts))
    return report


def _finalize_committed_campaign(output, *, round_limit):
    """Finalize from compact commit publications, without loading Memory replay."""
    output=Path(output)
    report_path=output/'campaign.json'
    if not report_path.exists():
        return None
    report=_load(report_path)
    if report.get('status') not in ('RUNNING','COMPLETE') or report.get('committed_rounds') != round_limit:
        return None
    rounds=report.get('rounds')
    require(type(rounds) is list and len(rounds)==round_limit,
            'committed campaign report is incomplete')
    head=_load(output/'memory'/'head.json')
    require(head.get('revision')==round_limit and head.get('memory_ref')==report.get('memory_head_ref'),
            'committed campaign head/report mismatch')
    for index,expected in enumerate(rounds,1):
        require(_load(output/f'round-{index:02d}'/'round_result.json')==expected,
                'round publication changed')
    if report.get('status')=='COMPLETE':
        return report
    result={**report,'status':'COMPLETE','stop_reason':'ROUND_LIMIT'}
    _save(report_path,result)
    return result


def campaign_report(snapshot,*,status,stop_reason=None):
    rows=snapshot.rounds
    old={e['edit_id']:(r['record']['gate_decision'],r) for r in rows for e in r['edits']}
    changes=[]
    for row in rows:
        for edit in row['edits']:
            for link in edit['related_history']:
                decision,prior=old[link['prior_edit_id']]
                changes.append({'new_edit_id':edit['edit_id'],'prior_edit_id':link['prior_edit_id'],
                    'relation':link['relation'],'origin_gate_decision':decision,
                    'historical_effects':[a['effect'] for a in prior['attribution']['records']
                                          if 'effect' in a and link['prior_edit_id'] in a['edit_ids']],
                    'interpretation':'REAUTHORIZED_INTENT_NOT_PROVEN_CORRECTION'})
    return {'schema_version':'campaign_report_v19.1','status':status,'stop_reason':stop_reason,
            'committed_rounds':len(rows),'memory_head_ref':snapshot.head['memory_ref'],
            'retained_skill_sha256':snapshot.head['retained_skill_ref']['sha256'],
            'rounds':[_round_result(r) for r in rows], 'cross_round_links':changes,
            'attribution_effect_counts':dict(Counter(a['effect'] for r in rows for a in r['attribution']['records'] if 'effect' in a)),
            'evidence_boundary':'EVOLUTION_ONLY_EXCEPT_WHOLE_PACKAGE_GATE_DECISION',
            'validity_claim':'OBSERVED_ARTIFACTS_NOT_METHOD_EFFECTIVENESS'}


def _recover_commits(output,snapshot,monitor,limit):
    require(len(snapshot.rounds)<=limit,'memory exceeds configured round limit')
    for i,row in enumerate(snapshot.rounds):
        round_id=f'round-{i+1:02d}'
        require(row['record']['round_id']==round_id,'committed round sequence mismatch')
        root=output/round_id
        receipt=load_private_monitor(snapshot.history[i].ledger,backend=monitor,
                                      artifact_dir=root/'monitor_private',history=snapshot.history[:i])
        require(receipt['decision']==row['record']['gate_decision'],'Memory decision differs from verified private Gate')
        expected=_round_result(row)
        if (root/'round_result.json').exists():
            require(_load(root/'round_result.json')==expected,'round publication changed')
        else:
            _save(root/'round_result.json',expected)


def run_campaign_v19(*,output,config,run_id,initial_skill,evolution_backend,monitor_backend,
                     resume=False,transports=None,event_hook=None,source_recovery=None,entrypoint=None):
    """Run bounded rounds; completed commit recovery never reruns a learner.

    event_hook is an engineering fault-injection/observability callback receiving
    only stage and round ID, never Monitor evidence. Config/source/version drift
    rejects resume before model dispatch. Failed responses are not auto-repaired.
    """
    require(type(resume) is bool,'resume must be boolean')
    transports=transports or CampaignTransports()
    output=Path(output)
    def current_binding():
        current=_binding(config,run_id,initial_skill,evolution_backend,monitor_backend)
        if entrypoint is not None:
            current['entrypoint']=entrypoint
        return source_recovery.campaign_binding(current) if source_recovery is not None else current
    require(source_recovery is None or resume,'source recovery requires explicit resume')
    bound=current_binding()
    def event(stage,round_id):
        print(f'{round_id} {stage}',flush=True)
        if event_hook is not None:
            event_hook(stage,round_id)
    with _lock(output):
        if output.exists():
            require(resume,'existing campaign requires explicit resume')
            require(_load(output/'binding.json')==bound,'campaign config/source/runtime changed')
            existing_report=_load(output/'campaign.json') if (output/'campaign.json').exists() else None
            if existing_report is not None and existing_report.get('status')=='RUNNING':
                finalized=_finalize_committed_campaign(output,round_limit=config['round_limit'])
                if finalized is not None:
                    return finalized
        else:
            require(not resume,'resume requires existing campaign')
            pending=output.with_name('.'+output.name+'.initialize-'+uuid.uuid4().hex)
            pending.mkdir(parents=True)
            _durable_save(pending/'binding.json',bound)
            initialize_memory(store_dir=pending/'memory',run_id=run_id,initial_skill=initial_skill)
            pending.rename(output)
            _sync_directory(output.parent)
        if source_recovery is not None:
            source_recovery.verify_reused_artifacts(output)
        snapshot=load_memory(output/'memory')
        _recover_commits(output,snapshot,monitor_backend,config['round_limit'])
        if snapshot.head['revision']==config['round_limit']:
            # Recovery may observe the final atomic commit before its report was published.
            _save(output/'campaign.json',campaign_report(snapshot,status='RUNNING'))
            return _finalize_committed_campaign(output,round_limit=config['round_limit'])
        stage='START';round_id=None
        try:
            for index in range(snapshot.head['revision']+1,config['round_limit']+1):
                require(current_binding()==bound,
                        'campaign implementation/config changed during execution')
                round_id=f'round-{index:02d}';root=output/round_id
                root.mkdir(parents=True,exist_ok=True)
                parent=snapshot.head['retained_skill']
                stage='PARENT_EVOLUTION';event(stage,round_id)
                run_parent_evolution(run_id=run_id,round_id=round_id,parent_skill=parent,backend=evolution_backend,
                    artifact_dir=root/'parent_evolution',resume=(root/'parent_evolution').exists(),max_workers=config['max_workers'])
                sources,scope=load_parent_experiences(run_id=run_id,round_id=round_id,parent_skill=parent,
                    backend=evolution_backend,artifact_dir=root/'parent_evolution')
                batch=build_experience_cards(sources,scope=scope,max_input_chars=config['max_grouping_chars'])
                stage='GROUPING';event(stage,round_id)
                grouping=run_campaign_grouping(batch,scope=scope,artifact_dir=root/'grouping',
                    transport=transports.grouping,resume=(root/'grouping').exists())
                stage='MEMORY_GENERATION';event(stage,round_id)
                retrieval={**config['retrieval'],'edit_ids':tuple(config['retrieval']['edit_ids'])}
                if config.get('generation_protocol') in ('separated','local'):
                    from .separated_generation_v19 import run_separated_generation
                    def generation_event(name):
                        nonlocal stage
                        stage=name;event(stage,round_id)
                    generation=run_separated_generation(store_dir=output/'memory',backend=evolution_backend,
                        parent_dir=root/'parent_evolution',round_id=round_id,grouping_result=grouping,
                        artifact_dir=root/'generation',diagnosis_transport=transports.diagnosis,
                        memory_review_transport=transports.memory_review,reconciliation_transport=transports.reconciliation,
                        editor_transport=transports.editor,resume=(root/'generation').exists(),event_hook=generation_event,
                        local_protocol=config.get('generation_protocol')=='local',fusion_transport=transports.issue_fusion,
                        evidence_review_transport=transports.evidence_review)
                else:
                    generation=run_memory_generation(store_dir=output/'memory',backend=evolution_backend,
                        parent_dir=root/'parent_evolution',round_id=round_id,grouping_result=grouping,
                        artifact_dir=root/'generation',diagnosis_transport=transports.diagnosis,
                        editor_transport=transports.editor,resume=(root/'generation').exists(),**retrieval)
                if generation.candidate_skill is None:
                    require(generation.status in ('NO_UPDATE','UNABLE'),'unexpected generation stop')
                    result=campaign_report(snapshot,status='COMPLETE',stop_reason=generation.status)
                    result['stopped_round']=round_id
                    _save(output/'campaign.json',result)
                    return result
                stage='CANDIDATE_EVOLUTION';event(stage,round_id)
                run_candidate_replay(generation.ledger,backend=evolution_backend,parent_dir=root/'parent_evolution',
                    artifact_dir=root/'candidate_evolution',history=snapshot.history,max_workers=config['max_workers'],
                    resume=(root/'candidate_evolution').exists())
                stage='ATTRIBUTION';event(stage,round_id)
                run_attribution(generation.ledger,backend=evolution_backend,parent_dir=root/'parent_evolution',
                    replay_dir=root/'candidate_evolution',artifact_dir=root/'attribution',history=snapshot.history,
                    transport=transports.attribution,resume=(root/'attribution').exists(),
                    protocol=config.get('attribution_protocol','legacy'))
                stage='MONITOR_GATE';event(stage,round_id)
                gate=run_private_monitor(generation.ledger,backend=monitor_backend,artifact_dir=root/'monitor_private',
                    history=snapshot.history,max_workers=config['max_workers'],resume=(root/'monitor_private').exists())
                stage='BEFORE_COMMIT';event(stage,round_id)
                commit_ref=commit_round_memory(generation.ledger,store_dir=output/'memory',expected_head_ref=snapshot.head['memory_ref'],
                    backend=evolution_backend,parent_dir=root/'parent_evolution',replay_dir=root/'candidate_evolution',
                    attribution_dir=root/'attribution',gate_result=gate)
                stage='AFTER_COMMIT';event(stage,round_id)
                if index == config['round_limit']:
                    report=_report_after_commit(snapshot,output=output,round_root=root,
                                                commit_ref=commit_ref,ledger=generation.ledger)
                    _save(root/'round_result.json',report['rounds'][-1])
                    _save(output/'campaign.json',report)
                    result=_finalize_committed_campaign(output,round_limit=config['round_limit'])
                    require(result is not None,'committed campaign report finalization failed')
                    return result
                snapshot=load_memory(output/'memory')
                _save(root/'round_result.json',_round_result(snapshot.rounds[-1]))
                _save(output/'campaign.json',campaign_report(snapshot,status='RUNNING'))
            result=_finalize_committed_campaign(output,round_limit=config['round_limit'])
            require(result is not None,'committed campaign report finalization failed')
            return result
        except BaseException as exc:
            # Commit may already have succeeded. Always derive progress from the
            # authoritative memory head, never a stale Python list or report.
            current=load_memory(output/'memory')
            result=campaign_report(current,status='INCOMPLETE')
            result.update(failed_stage=stage,active_round=round_id,error_type=type(exc).__name__)
            _save(output/'campaign.json',result)
            raise


def preflight_campaign(*,evolution_backend,monitor_backend,initial_skill,config,artifact_dir):
    """All task environments × three Skill deployment modes, zero model calls."""
    root=Path(artifact_dir)
    root.mkdir(parents=True,exist_ok=False)
    skills=(initial_skill,'','- Verify applicable conditions before acting.\n')
    evo=evolution_backend.preflight(artifact_dir=root/'evolution',skills=skills)
    mon=monitor_backend.preflight(artifact_dir=root/'monitor_private',skills=skills)
    result={'status':'PREFLIGHT','mode':config['mode'],'round_limit':config['round_limit'],
        'evolution_tasks':evo['task_count'],'monitor_tasks':mon['task_count'],
        'prepared_instances':evo['prepared_instances']+mon['prepared_instances'],'model_calls':0,
        'max_agent_rollouts':config['round_limit']*2*(evo['task_count']+mon['task_count'])}
    _save(root/'preflight.json',result)
    return result
