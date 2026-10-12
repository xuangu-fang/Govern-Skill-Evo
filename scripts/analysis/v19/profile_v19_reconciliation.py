"""Profile an archived Reconciliation request and rebuild its reference view offline."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',type=Path,required=True)
    parser.add_argument('--input',type=Path,required=True,help='Full persisted reconciliation-input.json')
    parser.add_argument('--output',type=Path,required=True,help='New report directory; never a Pilot directory')
    args=parser.parse_args()
    from src.skill_evolution.v19.edit_tracking_v19 import encode, digest
    from src.skill_evolution.v19.evidence_projection_v19 import expand
    from src.skill_evolution.v19.review_contract_v19 import MemoryReviewInput, HistoricalReviews
    from src.skill_evolution.v19.reconciliation_v19 import build_reconciliation_input
    from src.skill_evolution.v19.reconciliation_prompt_v19 import build_reconciliation_request
    from src.skill_evolution.v19.reconciliation_profile_v19 import profile_request
    from src.skill_evolution.v19.memory_generation_v19 import _prepared
    from src.skill_evolution.v19.memory_store_v19 import require
    old=json.loads(args.request.read_text()); full=json.loads(args.input.read_text())
    wire=json.loads(old['user_prompt']); canonical=expand(wire)
    if canonical.get('schema_version')=='reconciliation_evidence_view_v19.1':
        require(canonical['reconciliation_input_ref']=='RECONCILIATION_INPUT/'+digest(encode(full)),
                'request/input binding mismatch')
    else:
        require(all(canonical.get(k)==v for k,v in full.items()),'request/input binding mismatch')
    new_input=build_reconciliation_input(review_request=MemoryReviewInput(encode(full['review_input'])),
        historical_reviews=HistoricalReviews(encode(full['historical_reviews'])),
        additional_evidence_refs=full.get('additional_evidence_refs',()))
    new=_prepared(build_reconciliation_request(new_input))
    before,after=profile_request(old),profile_request(new)
    report={'source_request':str(args.request.resolve()),'source_input':str(args.input.resolve()),
            'source_input_sha256':digest(args.input.read_text()),'before':before,'after':after,
            'saved_proxy_tokens':before['proxy_input_tokens']-after['proxy_input_tokens'],
            'reduction_fraction':1-after['proxy_input_tokens']/before['proxy_input_tokens'],
            'execution':'OFFLINE_NO_MODEL_CALL_NO_PILOT_MUTATION'}
    require(not args.output.exists(),'report output must be new')
    args.output.mkdir(parents=True)
    (args.output/'profile.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    lines=['# Reconciliation 输入构成与引用视图（离线）','',
           '所有 token 数均为 cl100k_base 本地估算，不是网关实际计量；不能由此证明超时原因。','',
           '| 指标 | 原请求 | 新请求 |','|---|---:|---:|']
    for key in ('proxy_input_tokens','user_prompt_tokens','system_prompt_tokens','response_format_tokens','user_characters'):
        lines.append(f'| {key} | {before[key]:,} | {after[key]:,} |')
    lines += ['',f'输入估算减少 {report["saved_proxy_tokens"]:,} token（{report["reduction_fraction"]:.1%}）。输出上限仍为 96,000，超时仍为 300 秒。',
              '', '## 各部分占用','', '下表为发送内容的独立 JSON 片段估算；共享正文只计一次。与完整 user 字符串分词的差额单列，不能把片段估算当作网关计费。','',
              '| 部分 | 原请求 token | 新请求 token |','|---|---:|---:|']
    keys=list(before['sections'])+[k for k in after['sections'] if k not in before['sections']]
    for key in keys:
        b=before['sections'].get(key,{}).get('section_proxy_tokens',0)
        a=after['sections'].get(key,{}).get('section_proxy_tokens',0)
        lines.append(f'| {key} | {b:,} | {a:,} |')
    lines += [f'| JSON 分段/边界差额 | {before["section_serialization_residual"]:,} | {after["section_serialization_residual"]:,} |',
              '', '## 数据边界','',
              '- 全量保留 Current Findings 和 Historical Reviews；按全部引用载入当前事件、历史审阅事件和原归因的 Parent/Candidate 事件。',
              '- 轨迹身份与监督标签每条轨迹一份；事件正文按原引用唯一保存。相关上下文的政策行完整保留，正文不重复附带整份政策。',
              '- 不发送完整 Memory 回放、重复的历史原响应、整条历史轨迹引用目录。持久化原始证据不变。',
              '- 不足以判断时 DEFER 并声明所需引用；额外上下文通过 additional_evidence_refs 显式加入并改变输入摘要，不绕过来源闭合。',
              '- 本报告没有模型调用，不证明超时已消失或方法效果改善；旧请求不能被静默覆盖后 resume。','']
    (args.output/'profile.md').write_text('\n'.join(lines))
    print(json.dumps({'report':str((args.output/'profile.md').resolve()),
                      'before':before['proxy_input_tokens'],'after':after['proxy_input_tokens'],
                      'reduction_fraction':report['reduction_fraction']}))


if __name__=='__main__':main()
