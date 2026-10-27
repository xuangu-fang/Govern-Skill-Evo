"""Manual, evidence-based scoring recorded as data; no grading model or network.

Scores are analyst judgments, not keyword grading. Embed each unchanged answer
and the pre-call standard so every judgment can be independently reviewed.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
read = lambda p: json.loads(p.read_text())
DIMS = ['source_binding', 'factual_accuracy', 'applicability', 'conclusion_strength', 'behavior_comparison', 'uncertainty']
GOOD = {
 ('R05','T1'): '正确分别绑定当前 butterknife 合法 go to drawer 2 与历史 candle 非法 go to drawer 8；没有把同一步号当配对。',
 ('R05','T2'): '明确 P8:8 菜单可直接 open cabinet 3、无对应 go 命令，实际合法开柜；保留 Parent 原有能力及无法归因新增指导的边界。',
 ('R05','T3'): '辨识全局 Admissible Actions 与非 desklamp 搜索的章节边界；pillow 两侧成功 5/6，不能用它验证非 desklamp 搜索规则。',
 ('R05','T4'): 'soapbar 未观察/未取得、双方 50 步失败；保留未探索区域与全局可用性未知，未把 soapbottle 当目标。',
 ('R05','T6'): 'apple 14/11、取得前少三步、取得后的五个动作保持；未把搜索节省归为新增温变收益。',
 ('R06','T4'): '历史 butterknife 双方未找到且失败；Parent 操作 knife 而 Candidate 未取近似物体；明确全局不存在未被证明。',
 ('R06','T5'): '保留 plate Parent 取得/加热/13 步成功与 Candidate 未取得/未温变/50 步失败；辨识温变机会不对称。',
 ('R06','T6'): 'tomato 18/10，取得步 13/5，后续五动作一致；整体八步差来自取得前，零新增局部温变收益。',
}

# Overrides are explicit human assessments; 0=unsupported/contradictory,
# 1=partial/ambiguous/material omission, 2=meets criterion, null=N/A.
REVIEWS = {
 ('R05_A',1,'T6'): ({'applicability':1,'conclusion_strength':0}, [
  ('conclusion','Admissible Actions was not exercised because neither run issued an inadmissible command.',
   'opportunity_inference', '没有非法命令不证明合法动作检查未执行；全局规则可能正常遵循，也可能基础行为相同。搜索比较本身正确。')]),
 ('R05_B',1,'T3'): ({'applicability':0,'conclusion_strength':0}, [
  ('conclusion','The pillow pair lies outside the operative scope of both changes;',
   'scope_inference', 'conditions 已读出全局范围，却在结论把 pillow 排除在两项修改之外；没有违规不等于不适用。不是原始标题漏读。')]),
 ('R05_B',1,'T6'): ({'applicability':1,'conclusion_strength':0}, [
  ('conclusion','The Admissible Actions clause was not exercised, since neither run recorded an inadmissible command.',
   'opportunity_inference', '与 A 同类：零违规不能证明规则未执行。')]),
 ('R06_A',1,'T4'): ({'factual_accuracy':1,'conclusion_strength':1}, [
  ('conclusion','This supports a search/absence failure, not a conditioning failure.',
   'ambiguous_absence_and_incomplete_calibration', '保留 cannot prove global absence，但 search/absence failure 仍含混；引用旧 M10 不存在解释却未明确校正。完整 trace 也不等于全部 receptacle 观察可见。')]),
 ('R06_B',1,'T4'): ({'factual_accuracy':0,'conclusion_strength':1,'uncertainty':1}, [
  ('uncertainty','The unobserved middle steps are missing',
   'trace_detail_confusion', '中段完整动作/反馈仍可见，仅详细状态未展开；不能把它说成步骤缺失。not located 的核心结论正确，但未明确校准 M10。')]),
 ('R06_B',1,'T5'): ({'conclusion_strength':1,'uncertainty':1}, [
  ('conclusion','supports M7\'s claim that temperature guidance yields savings conditional on locating the exact target',
   'benefit_inference', '该 pair 支持缺少触发机会，不独立证明获得目标后会节省；旧解释的条件化收益被带入。'),
  ('uncertainty',"Candidate's omitted middle steps",'trace_detail_confusion',
   '详细窗口缺失不等于完整动作序列缺失；此处与 conditions 的 windows 混称，按部分而非动作事实错误评分。')]),
 ('R06_B',1,'T6'): ({'source_binding':0}, [
  ('facts.1.sources','Q2:40','nonexistent_reference','当前 Q2 总共 10 步；同组 Q2:11 也不存在。正文取得5、冷却7、放置10和18/10比较正确，属于引用错误而非动作重写。')]),
 ('R05_A',2,'T2'): ({'behavior_comparison':1}, [
  ('comparison','Later P8 invalid actions show incomplete compliance.',
   'comparison_coverage', '正确识别 Parent 原有直接开柜行为，但评价不稳定遵循时只列 Parent 非法动作，未保留 Candidate Q8:39 非法动作；不能据此判断 Candidate 已可靠遵循。并未明确声称 Candidate 完全遵循，故为部分。')]),
 ('R05_A',2,'T4'): ({'source_binding':1,'factual_accuracy':0}, [
  ('facts.0.text','Observed contents include candle 3, candle 2, soapbottle 2, and spraybottle 2 in cabinet 2',
   'object_location_binding', 'candle 3 在 countertop 1（P8:3）；cabinet 2 在 P8:6 只有 candle 2、soapbottle 2、spraybottle 2。核心 soapbar 未找到/未知结论仍正确，但汇总物体时混写位置。')]),
 ('R05_B',2,'T2'): ({'behavior_comparison':1}, [
  ('facts.2.text','illustrating admissible-list violations the new guidance would discourage.',
   'comparison_coverage', '只列 Parent 后续非法动作，未纳入 Q8:39；还未显式说出 P8:8 的 go to cabinet 3 不在菜单，虽然直接开柜事实及两侧菜单差异正确。')]),
 ('R05_B',2,'T3'): ({'applicability':1,'conclusion_strength':0}, [
  ('conclusion','the pillow pair does not exercise either new clause',
   'opportunity_inference', '已准确读出全局行动约束，但无违规不能推出全局检查条款未被执行。缺少直接 fallback 机会与缺少全局规则执行证据应分开。')]),
 ('R06_A',2,'T4'): ({'applicability':1,'conclusion_strength':1,'uncertainty':1}, [
  ('conditions','each side is a single run under S1_R05/diff',
   'parent_candidate_intervention_ambiguity', '若 under 指两侧都受到该编辑，则错误；Parent 是 pre-edit。语句也可理解为该编辑实验中的双方，故按部分评分。'),
  ('conclusion',"consistent with M10's claim that its rescues depended on the exact target sitting in an uninspected family",
   'historical_calibration_partial', '准确保留未找到与全局未知，但又套用旧 M10 的 rescue 解释；当前失败 Pair 本身不证明此获益条件。未明确纠正旧不存在措辞。'),
  ('uncertainty','many cabinets/countertops were never inspected within the windows shown',
   'coverage_window_ambiguity', '详细窗口未显示不等于未检查；完整 trace 可以检查访问范围。明确保留未知是正确的，未知理由应落在未探索位置和缺失详细状态，而非混称。')]),
 ('R06_A',2,'T5'): ({'conclusion_strength':1}, [
  ('conclusion','the added heat/cool guidance produced no observable effect here',
   'no_opportunity_vs_no_effect', 'Candidate 未温变足以说没有观察到温变执行收益，不足以排除整个编辑对前序搜索的间接影响。后文 search 阶段失败描述正确，结尾亦有限制，按部分处理。')]),
 ('R06_B',2,'T4'): ({'factual_accuracy':1}, [
  ('comparison','completed an invalid-looking placement',
   'action_validity_vs_goal_success', 'knife 的 move 动作是合法执行但不满足 butterknife 任务；invalid-looking 易把动作合法性与目标错误混为一谈。未直接声称反馈 invalid，按部分处理。')]),
 ('R06_B',2,'T6'): ({'factual_accuracy':1,'behavior_comparison':1}, [
  ('comparison','Placement: both went to the closed microwave, opened it once, and moved the tomato in, taking five steps each.',
   'phase_count_boundary', '单独 placement 是 go/open/move 三步；五步是取得后 go fridge/cool/go microwave/open/move 的总和。整体 18/10、取得 13/5 与八步搜索差异均正确。')]),
}

def resolve(obj, path):
    for key in path.split('.'):
        obj = obj[int(key)] if isinstance(obj,list) else obj[key]
    return obj

def build(replicates):
    standards=read(HERE/'private/standard_facts.json')['expected']; rows=[]
    for label in ('R05_A','R05_B','R06_B','R06_A'):
        case=label[:3]
        for rep in replicates:
            path=HERE/f'runs/{label}/attempt_{rep:03}/parsed.json'
            if not path.exists():continue
            for index,a in enumerate(read(path)['answers']):
                question=a['id'];scores=dict.fromkeys(DIMS,2)
                if case=='R05' and question=='T1':scores['applicability']=None
                overrides,issues=REVIEWS.get((label,rep,question),({},[]));scores.update(overrides)
                findings=[]
                for loc,quote,typ,note in issues:
                    val=resolve(a,loc)
                    assert quote in val,(label,rep,question,loc,quote)
                    findings.append({'output_path':f'answers[{index}].{loc}','quote':quote,'type':typ,'assessment':note})
                rows.append({'condition':label,'replicate':rep,'question':question,
                  'output_file':str(path.relative_to(HERE)), 'output_jsonpath':f'answers[{index}]',
                  'scores':scores, 'core_observation':GOOD[case,question], 'findings':findings,
                  'standard':standards[case][question], 'input_file':f'config/{label}/request.json',
                  'original_answer':a})
    return {'method':'Manual analyst assessment after independent pre-call standards; not blinded; no LLM grader; no overall accuracy statistic. All original answers retained.',
            'dimensions':DIMS,'rows':rows}

if __name__=='__main__':
    import sys
    name='initial_evaluation.json' if sys.argv[1:] == ['initial'] else 'evaluation.json'
    data=build([1] if name.startswith('initial') else [1,2])
    p=HERE/name
    if p.exists():assert read(p)==data,'Do not replace earlier assessment silently'
    else:p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(name,len(data['rows']))
