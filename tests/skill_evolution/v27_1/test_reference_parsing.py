"""Mathematical object names must not become source permissions or routing IDs."""
from copy import deepcopy
from src.skill_evolution.v27_1 import diagnosis, preconditioner, replay, facts, evolution
from src.skill_evolution.v27_1.execution_references import references
from .runtime_support import Base
from .support import bind, Generator
from .test_editor import offline


def run(ref):
    return {'ref':ref, 'initial':{'ref':ref+':0'}, 'attempts':[{'ref':ref+':1'}],
            'outcome':{'ref':ref+':outcome'}}


class ReferenceParsingTests(Base):
    def setUp(self):
        super().setUp(); offline(self)
        self.plan = {'goal':'Preserve hypotheses.', 'updates':[
            {'id':'u1', 'text':'Preserve hypotheses.', 'basis':['P1:1']}]}
        self.runs = [run('P1'),run('P2')]

    def check_all(self, prose):
        proposal = {'decision':'revise','reason':prose,'plan':deepcopy(self.plan)}
        proposal['plan']['goal'] = proposal['plan']['updates'][0]['text'] = prose
        diagnosis._validate_output(proposal, {'runs':self.runs})
        preconditioner._compile({'adjustments':[{'target':'u1','action':'REPLACE',
            'text':prose,'reason':prose}]}, {'plan':self.plan,'runs':self.runs,'memory':{'rounds':[]}})
        replay._validate_output({'entries':[{'knowledge':[{'task_id':'task','update_id':'u1','text':prose}]}]},
            {'pairs':[{'task_id':'task','parent':'P1','candidate':'Q1'}],
             'runs':[run('P1'),run('Q1')], 'edits':[{'update_id':'u1','patch':'nonempty'}], 'plan':self.plan})

    def test_bare_math_names_accepted_in_all_prose_fields(self):
        for prose in ('For groups G1 and G2, preserve hypotheses.',
                      'For groups G_1 and G_2, preserve hypotheses.',
                      'Compare polynomials P12 and Q12.',
                      'Compare P1 and P2, Q1 and Q2, and the quotient P1/P2.',
                      'Let `G1`, `P12` and `Q12` denote mathematical objects.'):
            with self.subTest(prose=prose):
                self.check_all(prose)
                self.assertEqual(references(prose), set())
        diagnosis._validate_output({'decision':'no_change','reason':'G1 and P12 are sufficient.','plan':None},
                                   {'runs':self.runs})

    def test_explicit_sources_still_checked_in_all_modules(self):
        self.check_all('Compare the observed result P1:1 and `Evidence:P1`.')
        for token in ('P99:1','`Evidence:P99`','`Group:G1`','Group:G1','`Memory:M1`',
                      '`Check:c1`','R03/P1','R03/P1:1','R03/diff','campaign_R03/P1'):
            with self.subTest(token=token):
                for module in ('diagnosis','preconditioner','replay'):
                    # Each independent call must reject; not only the first module.
                    value='Use '+token
                    if module=='diagnosis':
                        fn=lambda: diagnosis._validate_output({'decision':'no_change','reason':value,'plan':None},{'runs':self.runs})
                    elif module=='preconditioner':
                        fn=lambda: preconditioner._compile({'adjustments':[{'target':'u1','action':'KEEP','text':None,'reason':value}]},
                                                         {'plan':self.plan,'runs':self.runs,'memory':{'rounds':[]}})
                    else:
                        fn=lambda: replay._validate_output({'entries':[{'knowledge':[{'task_id':'task','update_id':None,'text':value}]}]},
                            {'pairs':[{'task_id':'task','parent':'P1','candidate':'Q1'}], 'runs':[run('P1'),run('Q1')],
                             'edits':[{'update_id':'u1','patch':'nonempty'}], 'plan':self.plan})
                    self.reject(fn)

    def test_structured_basis_cannot_become_math_prose(self):
        for basis in (['G1'],['P12'],['Q12'],['P1/P2'],['`Evidence:P1`']):
            value={'decision':'revise','reason':'Preserve conditions.','plan':deepcopy(self.plan)}
            value['plan']['updates'][0]['basis']=basis
            self.reject(diagnosis._validate_output,value,{'runs':self.runs})
        for basis in (['P1'],['P1:1'],['P1','P2']):
            value={'decision':'revise','reason':'Preserve conditions.','plan':deepcopy(self.plan)}
            value['plan']['updates'][0]['basis']=basis
            diagnosis._validate_output(value,{'runs':self.runs})

    def test_explicit_lists_ranges_and_history_keep_permissions(self):
        self.assertEqual(references('P1:1/P2:outcome'), {'P1:1','P2:outcome'})
        self.assertEqual(references('P1:0-1'), {'P1:0','P1:1'})
        self.assertIn('R03/P1:1',references('R03/P1:1'))
        self.reject(references,'P1:1-P2:3')
        self.reject(references,'P1:3-1')

    def test_namespace_permissions_and_other_task_replay_remain_strict(self):
        payload = {'plan':self.plan,'runs':[run('P1')],
                   'memory':{'rounds':[{'entries':[{'id':'M1'}]}]}}
        item = {'target':'u1','action':'KEEP','text':None,
                'reason':'Use `Memory:M1`, `Update:u1` and `Evidence:P1`.'}
        preconditioner._compile({'adjustments':[item]}, payload)
        for token in ('`Memory:M2`','`Update:u2`','`Evidence:P2`','P2:1',
                      'Evidence:P1','`Evidence: P1`','``Evidence:P1``'):
            self.reject(preconditioner._compile, {'adjustments':[{**item,'reason':token}]},payload)
        for uid in ('P12:1', 'R03/P1'):
            typed_payload = deepcopy(payload)
            typed_payload['plan']['updates'][0]['id'] = uid
            typed_item = {**item, 'target':uid, 'reason':f'Preserve `Update:{uid}` and P1:1.'}
            preconditioner._compile({'adjustments':[typed_item]}, typed_payload)
            self.reject(preconditioner._compile, {'adjustments':[{**typed_item,
                'reason':typed_item['reason']+' Check P2:1.'}]}, typed_payload)
        view = {'pairs':[{'task_id':'task','parent':'P1','candidate':'Q1'}],
                'runs':[run('P1'),run('Q1'),run('P2'),run('Q2')],
                'edits':[{'update_id':'u1','patch':'nonempty'}], 'plan':self.plan}
        def output(prose):
            return {'entries':[{'knowledge':[{'task_id':'task','update_id':'u1','text':prose}]}]}
        replay._validate_output(output('Compare `Evidence:diff`, `Evidence:Q1` and `Update:u1`.'),view)
        for token in ('`Evidence:P2`','Q2:outcome','`Memory:M1`','`Update:u2`'):
            self.reject(replay._validate_output, output(token),view)

    def test_math_prose_completes_each_stage_once_without_corrective_retry(self):
        import json
        _, _, adapter, config = bind(self.root/'fixture', rounds=1, size=2, mode='gain')
        generator = Generator(count=1)
        suffix = ' For groups G1/G2 and polynomials P12 and Q12, preserve hypotheses.'
        def generate(name, *args):
            response = generator(name, *args)
            value = json.loads(response['content'])
            if name == 'diagnosis':
                value['reason'] += suffix
                value['plan']['goal'] += suffix
                value['plan']['updates'][0]['text'] += suffix
            elif name == 'preconditioner':
                value['adjustments'][0]['reason'] += suffix
            elif name == 'replay':
                for item in value['entries'][0]['knowledge']: item['text'] += suffix
            response['content'] = json.dumps(value)
            return response
        root = self.root/'campaign'
        with adapter.using():
            self.assertEqual(evolution.run_campaign(root, config=config, generate=generate)['status'],'complete')
        self.assertEqual(generator.calls,['diagnosis','preconditioner','editor','replay'])
        for name in generator.calls:
            attempts = root/'rounds/R01'/name/'attempts'
            self.assertEqual([p.name for p in attempts.iterdir()],['001'])
            self.assertFalse((attempts/'001/error.json').exists())

    def test_plan_routing_uses_basis_and_explicit_prose_not_math_or_ids(self):
        data,_,adapter,_=bind(self.root/'fixture',rounds=1,size=3)
        with adapter.using():
            folder=self.root/'parents'
            records=adapter.actor_batch(data.batches()[0],self.skill,folder,{'split':'train','role':'parent'})
            adapter.register_archive(folder)
            saved=facts.build_parent_bundle(records,'R01')
            value={'decision':'revise','reason':'Preserve P3:1.','plan':deepcopy(self.plan)}
            update=value['plan']['updates'][0]
            update['id']='P3/P2'; update['text']='Compare polynomials P1 and P2, and P1/P3.'
            update['basis']=['P1']
            value['plan']['goal']='For groups G1 and G2, compare P12 and Q12.'
            def selected():
                completed=diagnosis.diagnosis_call(saved).complete(value)
                return [r['ref'] for r in preconditioner.preconditioner_input(completed,{'rounds':[]})['runs']]
            self.assertEqual(selected(),['P1'])
            value['plan']['goal']+=' Preserve `Evidence:P2`.'
            self.assertEqual(selected(),['P1','P2'])
            update['text']+=' Check P3:outcome.'
            self.assertEqual(selected(),['P1','P2','P3'])
