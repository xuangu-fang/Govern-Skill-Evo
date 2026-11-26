"""Read-only progress and usage over durable Actor/method request slots."""
from pathlib import Path
from .stages import read
from .benchmarks.lmb.actor import usage_view
from .benchmarks.lmb.prompting import PROMPT_VERSIONS


def cost_summary(campaign):
    root=Path(campaign);actor=[];method=[]
    for side in ('parent_runs','candidate_runs'):
        for slot in (root/'rounds').glob(f'R*/{side}/actor/*/attempts/*'):
            if (slot/'request_started.json').exists():
                actor.append(usage_view(read(slot/'response.json') if (slot/'response.json').exists() else {}))
    for name in PROMPT_VERSIONS:
        for slot in (root/'rounds').glob(f'R*/{name}/attempts/*'):
            if (slot/'request_started.json').exists():
                method.append(usage_view(read(slot/'response.json') if (slot/'response.json').exists() else {}))
    result={'actor_http_requests':len(actor),'module_http_requests':len(method),'tool_calls_committed':0}
    for key in ('input_tokens','output_tokens','total_tokens','reasoning_tokens'):
        values=[v[key] for v in actor+method if v[key] is not None]
        result[key]={'known_sum':sum(values),'unknown_requests':len(actor)+len(method)-len(values)}
    return result

def status(campaign):
    root=Path(campaign);state=read(root/'state.json');stop=read(root/'stop.json') if (root/'stop.json').exists() else None
    return {'state':state,'cost':cost_summary(root),'last_stop':stop,
            'currently_stopped':bool(stop and state['next_round']<=stop['round']),'integrity_verified':False}
