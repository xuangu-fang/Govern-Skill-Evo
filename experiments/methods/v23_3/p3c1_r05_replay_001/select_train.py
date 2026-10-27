"""Read-only identity screening; no environment or model execution for new cases."""
import json
from pathlib import Path
import random
import re
from collections import Counter
from .run import HERE, ROOT, save, now, sha

SEED = 230302
FAMILIES = ['pick_and_place_simple','pick_clean_then_place_in_recep',
            'pick_heat_then_place_in_recep','pick_cool_then_place_in_recep',
            'look_at_obj_in_light','pick_two_obj_and_place']

from experiments.methods.v23_3.archive_io import archive_glob, resolve, raw_path

def main():
    # Inspect metadata/text identities, not final-test trajectories or game solutions.
    seen=set();hits={};scanned=0;truncated=0
    pattern=re.compile(r'trial_T\d{8}_\d{6}_\d+')
    excluded={'test','tests','final','final_test','final_evaluation','eval_test','test_runs'}
    for base in ['artifacts/methods','experiments/methods','docs']:
        for p in archive_glob(ROOT / base, '*', recursive=True):
            if not resolve(p).is_file() or HERE in p.parents or raw_path(HERE) in p.parents or p.suffix not in {'.json','.md'}:continue
            if any(x.lower() in excluded or 'final_test' in x.lower() or 'test_evaluation' in x.lower() for x in p.parts):continue
            # Request/response bodies and game snapshots are not needed for identity screening.
            if p.name in {'http_response.json','response.json','request.json','messages.json','baseline.json','freeze.json','implementation.json'}:continue
            with resolve(p).open('rb') as stream:blob=stream.read(131072)
            scanned+=1;truncated+=resolve(p).stat().st_size>len(blob)
            trials=set(pattern.findall(blob.decode('utf-8',errors='ignore')))
            for trial in trials:
                seen.add(trial);hits.setdefault(trial,[])
                if len(hits[trial])<4:hits[trial].append(str(p.relative_to(ROOT)))
    # Exclude every instance in the original training edition, whether used or merely allocated.
    legacy=ROOT/'benchmarks/alfworld/editions/skillopt_39_18_134/train/items.json'
    for item in json.loads(resolve(legacy).read_text()):
        for trial in pattern.findall(item['gamefile']):
            seen.add(trial);hits.setdefault(trial,[]).append(str(legacy.relative_to(ROOT)))
    data=Path('/Users/didi/.cache/alfworld')
    paths=sorted(archive_glob(data / 'json_2.1.1/train', '*/*/game.tw-pddl'))
    eligible={f:[] for f in FAMILIES};excluded_items=[]
    for p in paths:
        family=p.parent.parent.name.split('-')[0];trial=p.parent.name
        if trial in seen:excluded_items.append({'gamefile':str(p.relative_to(data)),'identity':trial,'sources':hits[trial]});continue
        if family in eligible:eligible[family].append(p)
    rng=random.Random(SEED);selected=[]
    for family in FAMILIES:
        choices=rng.sample(eligible[family],min(2,len(eligible[family])))
        for batch,p in enumerate(choices,1):
            selected.append({'batch':batch,'id':f'train:p3a2_{batch}_{FAMILIES.index(family)+1:02}',
                             'gamefile':str(p.relative_to(data)),'task_type':family,'instance':p.parent.name,
                             'legacy_task_id':None})
    selected.sort(key=lambda x:(x['batch'],FAMILIES.index(x['task_type'])))
    save(HERE/'new_train_cases.json',{'frozen_at':now(),'seed':SEED,'source_root':str(data/'json_2.1.1/train'),
        'selection':'lexicographic canonical game paths; fixed family order; Random(seed).sample two per family; first/second to batches 1/2',
        'identity':'canonical game path plus globally excluded trial identity; IDs here are new experiment-local labels',
        'scanned_files':scanned,'prefix_truncated_files':truncated,'read_limit_bytes':131072,
        'raw_train_count':len(paths),'excluded_count':len(excluded_items),
        'eligible_counts':{k:len(v) for k,v in eligible.items()},'tasks':selected})
    save(HERE/'new_train_exclusions.json',excluded_items)
    rows='\n'.join(f"| {x['batch']} | `{x['id']}` | {x['task_type']} | `{x['gamefile']}` |" for x in selected)
    text=f'''# P3-A2 新 Train 案例预注册

冻结于 {now()}，早于任何本轮 Editor/Actor 输出。未调用新案例的模型、环境 reset 或读取其游戏内容/答案。

## 身份筛选与抽样

原始池只枚举 `/Users/didi/.cache/alfworld/json_2.1.1/train`，共 {len(paths)} 个游戏文件。任务族取目录名，实例取规范路径和 trial ID，不以文件名不同认定独立。排除旧 39 条 Train edition 全部实例及仓库开发归档提及的实例，实际排除 {len(excluded_items)} 个原始 Train 游戏。六族固定顺序为 {', '.join(FAMILIES)}。

种子 {SEED}；规范路径字典序排序；Python Random(seed) 每族不放回抽两条，第一/第二条分别放入批次 1/2；不足不补采其他族。共选 {len(selected)} 条，任务请求将由未来环境初始观察提取，本轮不猜写请求。

排重扫描 artifacts/methods、experiments/methods、docs 的元数据及文本身份，排除显式 Test/final 路径、原始 HTTP 响应、模型请求正文等。读 {scanned} 份文件，每份至多前 131072 字节，{truncated} 份存在未扫描尾部。另完整读取旧 Train items。只读身份，未访问最终 Test 数据目录或运行 Test。详细排除来源见 new_train_exclusions.json。

**暴露边界**：排除 R04/R05/R06 的规范实例（这些也位于不同原始 split），旧 Train edition 和扫描范围内 V23.2/V23.3/P1-R/Memory 来源可定位的实例；不能排除仅用自然语言、另一别名、截断尾部或仓库外记录的先前暴露。因此称“在已核查身份范围内未发现暴露”，不称绝对独立泛化集。

下面的 task_id 是本实验新建的局部 Train 标签，**不是**已有 39 条 edition 的编号；规范 gamefile 为权威身份。未来执行需用独立 manifest/合法输入适配，不能覆盖默认清单或冒用旧编号。

| 批次 | task_id | 任务族 | 规范 gamefile |
|---|---|---|---|
{rows}

## 下一轮固定条件草案（本轮不执行）

两批均优先使用本轮 parent.md 与 memory_v3_integration_001/config/full_payload.json.memory（M1/M2/M3/M6/M7/M8/M9），不吸收本轮或新任务的后验响应。两个批次互不更新 Parent/Memory；若接口不兼容须在未来开跑前重新冻结，不能看输出后更换。

每批先在六条共同任务执行 Parent，再同一 Grouping、一次共同多行 Diagnosis，冻结 Original 后分别 V23 自由更新与 V23.3 Patch，随后同配置 Editor 和配对 Candidate Replay。相同当前证据与历史输入，单次生成不择优。

预算草案：每批 Grouping 1、Diagnosis 1、Preconditioner 2、Editor 2，共 6 次模块调用；最多 18 Episode（6 Parent+6 A+6 B）、900 Actor 决策。两批合计最多 12 模块调用、36 Episode、1800 Actor 决策；技术重试/模型/超时在未来单独冻结，当前未授权执行。合法停点缩减依赖调用，不增补样本。

评价：原生成功、步数、类别与实例覆盖、无信息重复、无效动作、精确目标、必要处理/数量/交付、实际 Skill Diff 和退化；分别报告技术有效性、更新构造及行为结果。保留全部预注册案例，不据胜负筛除；不用于最终 Test 调参。
'''
    (resolve(HERE/'NEW_TRAIN_CASES.md')).write_text(text)
    print('New train cases frozen',len(selected),'excluded',len(excluded_items),flush=True)

if __name__=='__main__':main()
