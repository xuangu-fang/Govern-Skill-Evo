"""Method-independent observation/state boundaries and predeclared evaluation schedule."""
from copy import deepcopy
from benchmark_v5.core import digest, canonical
from .cases import heldout_cases, world_for, training_ls, training_lg
from .environment import build
from .experience import training_package
from .rules import full_rules

MODEL='deepseek-v4-flash'
SYSTEM='你是授权沙盒业务Agent。仅使用提供的公开请求、工具及经验完成用户任务。经验来自相同稳定服务商版本，但当前案例事实必须核验。授权边界始终公开，不得越权探索。可合理恢复，不得编造状态。请在首次业务写入前记录可选知识预测，最后调用finish并按用户要求准确填写结构化回执。不要把未知规则误当成不可行动，也不要把收件回执说成最终审批。'
LEARNER_SYSTEM='从相同服务商版本的授权沙盒经验归纳可迁移业务规律，写成简洁的执行参考文本。只能依据提供的观察；区分证据、推断和不确定范围，保留边界、例外、金额/时点或资料替代范围。不能访问环境源码、候选参数表或测试案例。不要复述订单ID当成规则。不需要特定Skill/Memory格式。只返回可携带参考文本，不调用工具。'
LIMITS=dict(model_turns=24,tool_calls=60,completion_tokens=32768,cumulative_prompt_tokens=240000,
            max_tokens_per_call=8192,timeout_seconds=180,transport_retries=1,retry_delay_seconds=2,
            state_bytes=65536,learning_calls_per_mechanism=1)


def config():
    return dict(protocol_id='learning-20261010-001',model=MODEL,temperature=0.2,reasoning_effort='high',
        schedule_seed=20261017,workers=2,system_prompt=SYSTEM,learner_prompt=LEARNER_SYSTEM,
        limits=LIMITS,conditions=['zero','raw','processed','oracle'],prefix={'LS1':2,'LG1':4},
        repetitions=1,classification='synthetic_dev_calibration_not_final_blind_test',
        primary='full_service by mechanism and service stratum',
        secondary=['prediction accuracy and coverage','first decision','recoveries','cost'],
        exclusions='Keep all raw outcomes. Separate transport/harness invalid and token/length deviations; never replace a failed job.')


def make_state(kind,condition,observations,content):
    if any(o['feedback_phase']!='authorized_sandbox_case_review' or
           o['world_version']!=('sandbox-settlement-v1' if kind=='LS1' else 'sandbox-evidence-v1') for o in observations):
        raise ValueError('INVALID_EXPERIENCE_OR_WORLD')
    if len(content.encode())>LIMITS['state_bytes']:raise ValueError('LEARNING_STATE_TOO_LARGE')
    body=dict(kind=kind,condition=condition,source_digest=digest(observations),
              experience_count=len(observations),content=content,
              world_version='sandbox-settlement-v1' if kind=='LS1' else 'sandbox-evidence-v1')
    return {**body,'sha256':digest(body)}


def state_content(state,kind,condition):
    if state['sha256']!=digest({k:v for k,v in state.items() if k!='sha256'}):raise ValueError('STATE_CHANGED')
    if state['kind']!=kind or state['condition']!=condition:raise ValueError('STATE_CONDITION_MISMATCH')
    if len(state['content'].encode())>LIMITS['state_bytes']:raise ValueError('STATE_TOO_LARGE')
    return state['content']


def initial_messages(env,state,condition):
    # Explicit projection. No scenario, private world, evaluator, answers or train audit objects.
    content=dict(request=env.request(),experience_reference=state_content(state,env.scenario['kind'],condition))
    return [{'role':'system','content':SYSTEM},{'role':'user','content':canonical(content)}]


def learning_input(kind,observations):
    sample=(training_ls() if kind=='LS1' else training_lg())[0]
    public=build(sample,world_for(kind)).request()
    return [{'role':'system','content':LEARNER_SYSTEM},
            {'role':'user','content':canonical({'world_version':sample['world_version'],
             'public_policy':public.get('policy',public.get('public_policy')),'experience':observations})}]


def jobs():
    import random
    result=[]
    for c in heldout_cases():
        for condition in ('zero','raw','processed','oracle'):
            result.append(dict(id=f'{c["id"]}__{condition}',case_id=c['id'],kind=c['kind'],condition=condition,model=MODEL))
        if c['id'] in ('LS-H2','LS-H4','LG-H3','LG-H4'):
            result.append(dict(id=f'{c["id"]}__prefix',case_id=c['id'],kind=c['kind'],condition='prefix',model=MODEL))
    random.Random(20261017).shuffle(result)
    return result
