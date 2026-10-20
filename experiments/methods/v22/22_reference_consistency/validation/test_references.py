from copy import deepcopy
import json
import unittest
import fixtures as f
from src.skill_evolution.v22 import reference_rules as r, memory_contract, p1_input, grouped_update as g
from src.skill_evolution.v22.effective_memory import validate_effective_learning, apply_effective_memory, effective_consumption_payload
from src.skill_evolution.v22.compact_update import validate_diagnosis, apply_fusion, validate_editor
from src.skill_evolution.v22.compact_learning import coverage_index, update_response_sources
from tests.skill_evolution.v22 import test_effective_memory as e, test_unified_dsc_mechanism as u

class ReferenceTests(unittest.TestCase):
    def setUp(self):
        fixture=e.EffectiveMemoryTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        self.payload=deepcopy(fixture.payload);self.payload['update_profile']=r.PROFILE
        self.value=fixture.correction()
        self.req=self.payload['plan']['requirements'][0]['id'];self.watch=self.payload['plan']['watch'][0]['id']
        self.value['findings'][0]['about']=['intent']+[r.ref('watch',w['id']) for w in self.payload['plan']['watch']]
        self.old=fixture.payload

    def test_same_reference_in_about_refs_and_provenance(self):
        value=self.value;value['findings'][0]['about'] += [r.ref('requirement',self.req)]
        value['findings'][0]['refs'] += [r.ref('requirement',self.req),r.ref('watch',self.watch)]
        validate_effective_learning(value,self.payload)
        self.assertEqual(coverage_index(value,self.payload)[self.watch]['status'],'addressed_with_limits')
        sources=update_response_sources(self.payload,value['findings'][0])
        self.assertIn(r.ref('requirement',self.req),sources);self.assertIn(r.ref('watch',self.watch),sources)

    def test_wrong_type_unknown_and_bare_rejected(self):
        for ref in ['u1','w1','requirement:missing','watch:missing','effect:old:m1','P1:1','group:any']:
            value=deepcopy(self.value);value['findings'][0]['about']=[ref]
            with self.assertRaises(ValueError):validate_effective_learning(value,self.payload)
        value=deepcopy(self.value);value['findings'][0]['refs']=['watch:missing']
        with self.assertRaises(ValueError):validate_effective_learning(value,self.payload)

    def test_types_do_not_alias_same_local_id(self):
        p=deepcopy(self.payload);p['plan']['watch'][0]['id']=self.req
        catalog=r.learning_objects(p)
        self.assertEqual(catalog[r.ref('requirement',self.req)],('requirement',self.req))
        self.assertEqual(catalog[r.ref('watch',self.req)],('watch',self.req))
        value=deepcopy(self.value);value['findings'][0]['about']=[r.ref('requirement',self.req)]
        self.assertEqual(coverage_index(value,p)[self.req]['status'],'not_assessed')
        value['findings'][0]['about']=[r.ref('watch',self.req)]
        self.assertEqual(coverage_index(value,p)[self.req]['status'],'addressed_with_limits')

    def test_retirement_and_history_preserved(self):
        validate_effective_learning(self.value,self.payload)
        memory=apply_effective_memory(self.payload['memory'],self.value,'new',self.payload)
        self.assertIn('Untested scope must remain unknown.',memory[0]['limits'])
        self.assertEqual(memory[0]['basis'][-1]['finding']['about'],self.value['findings'][0]['about'])
        view=effective_consumption_payload(dict(self.payload,memory=memory))
        self.assertTrue(any(k.endswith('::'+r.ref('watch',self.watch)) for k in view['historical_sources']))
        self.assertEqual(p1_input.decode(p1_input.encode(view)),view)

class ConstructionTests(unittest.TestCase):
    def setUp(self):
        self.fx=u.UnifiedDscMechanismTests();self.fx.setUp();self.addCleanup(self.fx.doCleanups)
        self.data=self.fx.round_fixture(profile=memory_contract.PROFILE)
    def payload(self,key):
        p=deepcopy(self.data[key]);p['update_profile']=r.PROFILE
        if 'binding_sha256' in p:
            from src.adapters.alfworld.skill_runtime import object_digest
            p['binding_sha256']=object_digest({k:v for k,v in p.items() if k!='binding_sha256'})
        return p
    def test_all_messages_p1_and_shapes(self):
        for stage,key in [('diagnosis','current'),('fusion','update'),('editor','update'),('learn','payload')]:
            p=self.payload(key);m=g.grouped_messages(stage,p);view=p1_input.decode(json.loads(m[1]['content']))
            self.assertEqual(p1_input.decode(p1_input.encode(view)),view)
            self.assertIn('Reference contract:',m[0]['content'])
            if stage=='learn':
                self.assertEqual(set(view['reference_contract']['about_objects']),set(r.learning_objects(p)))
                self.assertIn(memory_contract.ADDITION,m[0]['content'])
    def test_diagnosis_fusion_editor_boundary(self):
        p=self.payload('update');plan=p['plan']
        d={'decision':'revise','reason':'evidence','plan':plan}
        wire=r.convert('diagnosis',d,{},outbound=True)
        self.assertEqual(validate_diagnosis(wire,self.payload('current')),d)
        fusion={'decision':'ready','reason':'supported keep','changes':[],'watch_changes':[],'open':[]}
        self.assertEqual(g.compile_update(fusion,p),plan)
        old=self.data['editor'];wire=r.convert('editor',old,p,outbound=True)
        validate_editor(wire,p)
        candidate,result=g.realize_editor(wire,p)
        self.assertEqual(candidate['text'],old['candidate_text'])
        self.assertEqual(result['requirements'],plan['requirements'])
        wrong=deepcopy(wire);wrong['mappings'][0]['requirements']=['watch:u1']
        with self.assertRaises(ValueError):validate_editor(wrong,p)
    def test_changes_and_watch_migration(self):
        p=self.payload('update');old=p['plan']['requirements'][0]['id'];watch=p['plan']['watch'][0]['id']
        for strategy in ['Replace strategy','Expand condition','Narrow condition','Coordinate dependency']:
            value={'decision':'ready','reason':strategy,'changes':[{'from':['requirement:'+old],
                'to':[{'id':'new','text':strategy}],'basis':p['plan']['requirements'][0]['basis'],
                'reason':'current evidence','disposition':'replace'}],
                'watch_changes':[{'from':['watch:'+watch], 'to':[{'id':'newwatch','about':['requirement:new'],'question':'response?'}]}],'open':[]}
            result=g.compile_update(value,p);self.assertEqual(result['requirements'][-1]['id'],'new')
    def test_full_editor_learning_handoff_and_system_freeze(self):
        from src.skill_evolution.v22.train_response_update import normalize_editor
        from src.skill_evolution.v22.continual_runtime import _system_prompts
        d=self.data;p=self.payload('update')
        wire=r.convert('editor',d['editor'],p,outbound=True)
        self.assertEqual(normalize_editor(wire,p),wire)
        candidate,plan=g.realize_editor(wire,p)
        learning=g.prepare_grouped_learning(d['context'],d['grouping'],plan,candidate,
            d['parents'],d['candidates'],d['gate'],editor=wire,profile=r.PROFILE)
        self.assertEqual(learning['update_context']['editor']['mappings'],wire['mappings'])
        view=p1_input.decode(json.loads(g.grouped_messages('learn',learning)[1]['content']))
        self.assertEqual(view['update_context']['editor']['mappings'],wire['mappings'])
        prompts=_system_prompts(f.GROUP_PROMPT.read_text(),profile=r.PROFILE)
        self.assertEqual(set(prompts),{'classification','diagnosis','fusion','main_editor','post_gate_learning'})

    def test_basis_and_refs_do_not_gain_object_permissions(self):
        p=self.payload('update');value={'decision':'ready','reason':'test','changes':[
            {'from':['requirement:'+p['plan']['requirements'][0]['id']], 'to':[],
             'basis':['watch:missing'],'reason':'invalid basis','disposition':'withdraw'}],
             'watch_changes':[],'open':[]}
        with self.assertRaises(ValueError):g.compile_update(value,p)

    def test_old_minimal_actual_messages_exact(self):
        d=f.ROOT/'artifacts/methods/v22/21_memory_contract_minimal/preparation/cases/r2_revision'
        self.assertEqual(g.grouped_messages('learn',f.read(d/'payload.json')),f.read(d/'messages.json'))

    def test_runtime_freezes_overlay_and_inherited_sources(self):
        from tests.skill_evolution.v22 import test_continual_runtime as t
        from src.skill_evolution.v22.continual_runtime import load_bundle,freeze_runtime,check_runtime
        fx=t.ContinualRuntimeTests();fx.setUp();self.addCleanup(fx.doCleanups)
        fx.write_plan(lambda plan:plan.update(update_profile=r.PROFILE))
        freeze=freeze_runtime(load_bundle(fx.plan_path),fx.root/'freeze',offline=True)
        self.assertEqual(freeze['runtime']['contracts']['references'],r.VERSION)
        paths=[x['path'] for x in freeze['sources']]
        self.assertTrue(any('22_reference_consistency' in x and x.endswith('reference_rules.py') for x in paths))
        self.assertIn(str(f.ROOT/'src/skill_evolution/v22/unified_dsc.py'), paths)
        self.assertIn(str(f.ROOT/'experiments/methods/v22/21_memory_contract_minimal/revision/src/skill_evolution/v22/memory_contract.py'), paths)
        check_runtime(freeze)

    def test_failed_archives_stay_failed(self):
        for folder,case in [('20_memory_contract_fix','r1_empty_history'),('20_memory_contract_fix','r2_revision'),('21_memory_contract_minimal','r2_revision')]:
            d=f.ROOT/'artifacts/methods/v22'/folder/'preparation/cases'/case
            value=f.read(d/'parsed.json');p=f.read(d/'payload.json')
            with self.assertRaisesRegex(ValueError,'Unknown about reference'):validate_effective_learning(value,p)
            p['update_profile']=r.PROFILE
            # These contain group abouts or prefixed values; a format migration must
            # not legalize the whole archived output, especially group objects.
            if any(a.startswith('group:') for x in value['findings'] for a in x['about']):
                with self.assertRaises(ValueError):validate_effective_learning(value,p)

if __name__=='__main__':unittest.main()
