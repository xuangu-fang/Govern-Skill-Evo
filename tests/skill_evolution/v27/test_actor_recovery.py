"""Completed evidence must be audited before any resume request is scheduled."""
from unittest.mock import patch

from . import test_offline as original
from .support import Dataset, Transport, SKILL, Case, config, response
from src.skill_evolution.v27 import evolution, evaluation, stages
from src.skill_evolution.v27.benchmark import using_benchmark
from src.skill_evolution.v27.benchmarks.lmb import actor, protocol as p
from src.skill_evolution.v27.benchmarks.lmb import adapter as adapter_module
from src.skill_evolution.v27.benchmarks.lmb.adapter import LMBAdapter


class TestDataset(Dataset):
    __test__=False
    def __init__(self,root):
        super().__init__(root,124)
        self.splits={'train':[],'validation':[],'test':list(self.rows)}
    def case(self,uid):
        case=super().case(uid)
        return Case(case.case_id,case.payload,case.reference,{'split':'test','source_split':'test'})


class ActorRecoveryTests(original.Base):
    def snapshot(self,root):
        return {p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def assert_damaged_resume_stops(self,batch,task,transport,resume,*,aggregate=True):
        folder=batch/'actor'/p.digest(task)
        variants=[['result.json'],['result.json','attempts/001/response.json']]
        if aggregate:variants.append(['result.json','attempts/001/response.json','trajectory.json'])
        for names in variants:
            with self.subTest(missing=names):
                removed={name:(folder/name).read_bytes() for name in names}
                for name in names:(folder/name).unlink()
                before=transport.calls;snapshot=self.snapshot(batch)
                for _ in range(2):
                    self.reject(resume)
                    self.assertEqual(transport.calls,before)
                    self.assertEqual(self.snapshot(batch),snapshot)
                for name,content in removed.items():(folder/name).write_bytes(content)

    def test_campaign_parent_and_candidate_partial_batch_archive_loss(self):
        for side,point in (('parent_runs','grouping'),('candidate_runs','pairs')):
            data=Dataset(self.root/'data',2);t=Transport();a=LMBAdapter(data,t,gate_metric=p.EM_GATE)
            gen,calls=original.CampaignTests.generator(self);root=self.root/side
            def hook(stage):
                if stage==point:raise KeyboardInterrupt()
            with using_benchmark(a):
                with self.assertRaises(KeyboardInterrupt):
                    evolution.run_campaign(root,config=config(a),generate=gen,hook=hook)
                batch=root/'rounds/R01'/side
                # Per-task completion survived, but the batch aggregate did not.
                (batch/'records.json').unlink();method_count=len(calls)
                self.assert_damaged_resume_stops(batch,'synthetic:000',t,
                    lambda:evolution.run_campaign(root,generate=gen,resume=True),aggregate=False)
                self.assertEqual(len(calls),method_count)
                before=t.calls
                evolution.run_campaign(root,generate=gen,resume=True)
                # The parent case may now execute its previously unstarted candidate batch.
                self.assertEqual(t.calls-before,2 if side=='parent_runs' else 0)

    def test_completed_test_resume_audits_batch_completion_without_requests(self):
        data=TestDataset(self.root/'data');ids=tuple(data.rows);t=Transport();a=LMBAdapter(data,t)
        skill=self.root/'skill.md';skill.write_text(SKILL);root=self.root/'test'
        with using_benchmark(a),patch.object(evaluation,'TEST_IDS',ids):
            result=evaluation.run_evaluation(root,adapter=a,skill_file=skill)
            self.assertEqual(result['completed'],124)
            self.assert_damaged_resume_stops(root/'batch',ids[0],t,
                lambda:evaluation.run_evaluation(root,adapter=a,skill_file=skill,resume=True))
            before=t.calls
            self.assertEqual(evaluation.run_evaluation(root,adapter=a,skill_file=skill,resume=True),result)
            self.assertEqual(t.calls,before)

    def test_mixed_campaign_batch_validates_completed_before_pending_requests(self):
        data=Dataset(self.root/'data',2);pending='synthetic:001'
        def interrupted(messages,directory):
            if directory.parent.parent.name==p.digest(pending):raise KeyboardInterrupt()
            return response()
        t=Transport(fn=interrupted);a=LMBAdapter(data,t,gate_metric=p.EM_GATE)
        gen,_=original.CampaignTests.generator(self,no_change='diagnosis');root=self.root/'mixed'
        with using_benchmark(a):
            with self.assertRaises(KeyboardInterrupt):evolution.run_campaign(root,config=config(a),generate=gen)
            batch=root/'rounds/R01/parent_runs';self.assertFalse((batch/'records.json').exists())
            t.fn=None
            self.assert_damaged_resume_stops(batch,'synthetic:000',t,
                lambda:evolution.run_campaign(root,generate=gen,resume=True),aggregate=False)
            before=t.calls
            evolution.run_campaign(root,generate=gen,resume=True)
            self.assertEqual(t.calls-before,1)
            result=stages.read(batch/'actor'/p.digest(pending)/'result.json')
            self.assertEqual(result['api_requests'],2)
            self.assertEqual(stages.read(batch/'actor'/p.digest(pending)/'attempts/001/error.json')['status'],'unknown')
            before=t.calls;evolution.run_campaign(root,generate=gen,resume=True);self.assertEqual(t.calls,before)

    def test_unfinished_test_request_recovers_with_original_attempt_budget(self):
        data=TestDataset(self.root/'data');ids=tuple(data.rows);pending=ids[-1]
        def interrupted(messages,directory):
            if directory.parent.parent.name==p.digest(pending):raise KeyboardInterrupt()
            return response()
        t=Transport(fn=interrupted);a=LMBAdapter(data,t);skill=self.root/'skill.md';skill.write_text(SKILL)
        root=self.root/'test_partial'
        with using_benchmark(a),patch.object(evaluation,'TEST_IDS',ids):
            with self.assertRaises(KeyboardInterrupt):evaluation.run_evaluation(root,adapter=a,skill_file=skill)
            self.assertFalse((root/'batch/records.json').exists())
            t.fn=None
            self.assert_damaged_resume_stops(root/'batch',ids[0],t,
                lambda:evaluation.run_evaluation(root,adapter=a,skill_file=skill,resume=True),aggregate=False)
            before=t.calls
            result=evaluation.run_evaluation(root,adapter=a,skill_file=skill,resume=True)
            self.assertEqual(result['completed'],124);self.assertEqual(t.calls-before,1)
            self.assertEqual(result['actor_requests'],125)
            saved=stages.read(root/'batch/actor'/p.digest(pending)/'result.json')
            self.assertEqual(saved['api_requests'],2)

    def test_unfinished_saved_response_recovers_without_resending(self):
        for kind in ('response','http','result'):
            data=Dataset(self.root/'data',1);t=Transport();a=LMBAdapter(data,t,gate_metric=p.EM_GATE)
            root=self.root/kind;gen,_=original.CampaignTests.generator(self,no_change='diagnosis')
            if kind=='response':
                # Interrupt after response.json is durable, before result/trajectory exist.
                with using_benchmark(a),patch.object(actor,'parse_response',side_effect=KeyboardInterrupt):
                    with self.assertRaises(KeyboardInterrupt):evolution.run_campaign(root,config=config(a),generate=gen)
            elif kind=='http':
                def http_interrupted(messages,directory):
                    stages.save(directory/'http_status.json',{'status_code':200})
                    stages.save(directory/'http_response.txt',response())
                    raise KeyboardInterrupt()
                t.fn=http_interrupted
                with using_benchmark(a):
                    with self.assertRaises(KeyboardInterrupt):evolution.run_campaign(root,config=config(a),generate=gen)
            else:
                original_freeze=adapter_module.freeze
                def before_trajectory(path,value,**kwargs):
                    if path.name=='trajectory.json':raise KeyboardInterrupt()
                    return original_freeze(path,value,**kwargs)
                with using_benchmark(a),patch.object(adapter_module,'freeze',side_effect=before_trajectory):
                    with self.assertRaises(KeyboardInterrupt):evolution.run_campaign(root,config=config(a),generate=gen)
            before=t.calls;t.fn=None
            with using_benchmark(a):evolution.run_campaign(root,generate=gen,resume=True)
            self.assertEqual(t.calls,before)
            result=stages.read(root/'rounds/R01/parent_runs/actor'/p.digest('synthetic:000')/'result.json')
            self.assertEqual(result['api_requests'],1)

    def test_direct_actor_trajectory_marker_blocks_archive_loss(self):
        data=Dataset(self.root/'data',1);t=Transport();a=LMBAdapter(data,t,gate_metric=p.EM_GATE)
        skill=self.root/'skill.md';skill.write_text(SKILL);batch=self.root/'batch'
        with using_benchmark(a):a.actor_batch(list(data.rows),skill,batch,{'split':'train','role':'parent'})
        folder=batch/'actor'/p.digest('synthetic:000')
        (folder/'result.json').unlink();(folder/'attempts/001/response.json').unlink()
        before=t.calls;snapshot=self.snapshot(folder)
        self.reject(actor.execute,data.case('synthetic:000'),SKILL,folder,t)
        self.assertEqual(t.calls,before);self.assertEqual(self.snapshot(folder),snapshot)

    def _assert_pending_first_completed_last(self,mode,corruption):
        root=self.root/mode;root.mkdir()
        data=Dataset(root/'data',3) if mode=='campaign' else TestDataset(root/'data')
        ids=list(data.rows);pending=ids[0];completed=ids[-1];sent=[]
        def interrupted(messages,directory):
            task_hash=directory.parent.parent.name;sent.append(task_hash)
            if task_hash==p.digest(pending):raise KeyboardInterrupt()
            return response()
        t=Transport(fn=interrupted)
        a=LMBAdapter(data,t,gate_metric=p.EM_GATE if mode=='campaign' else None)
        gen,_=original.CampaignTests.generator(self,no_change='diagnosis')
        skill=root/'skill.md';skill.write_text(SKILL);run=root/'run'
        with using_benchmark(a),patch.object(evaluation,'TEST_IDS',tuple(ids)):
            if mode=='campaign':
                start=lambda:evolution.run_campaign(run,config=config(a),generate=gen)
                resume=lambda:evolution.run_campaign(run,generate=gen,resume=True)
                batch=run/'rounds/R01/parent_runs'
            else:
                start=lambda:evaluation.run_evaluation(run,adapter=a,skill_file=skill)
                resume=lambda:evaluation.run_evaluation(run,adapter=a,skill_file=skill,resume=True)
                batch=run/'batch'
            with self.assertRaises(KeyboardInterrupt):start()
            self.assertFalse((batch/'records.json').exists())
            folder=batch/'actor'/p.digest(completed)
            self.assertTrue((folder/'trajectory.json').is_file())
            result_bytes=(folder/'result.json').read_bytes()
            raw_bytes=(folder/'attempts/001/response.json').read_bytes()
            if corruption=='missing_result_and_response':
                (folder/'result.json').unlink();(folder/'attempts/001/response.json').unlink()
                expected_error='Missing completed Actor result'
            else:
                # The last task has only result as a completion marker; its raw response stays valid.
                (folder/'trajectory.json').unlink()
                value=stages.read(folder/'result.json');value['content']='CORRUPTED'
                stages.save(folder/'result.json',value)
                expected_error='Completed Actor result differs from response archive'
            def succeeds(messages,directory):
                sent.append(directory.parent.parent.name);return response()
            t.fn=succeeds;before=t.calls;sent_before=len(sent);snapshot=self.snapshot(batch)
            for _ in range(2):
                # Reject before even constructing the executor, independently of thread scheduling.
                with patch.object(adapter_module,'ThreadPoolExecutor',side_effect=AssertionError('Workers started before archive validation')):
                    with self.assertRaisesRegex(ValueError,expected_error):resume()
                self.assertEqual(t.calls,before);self.assertEqual(len(sent),sent_before)
                self.assertEqual(self.snapshot(batch),snapshot)
            (folder/'result.json').write_bytes(result_bytes)
            (folder/'attempts/001/response.json').write_bytes(raw_bytes)
            # Leave trajectory absent in the result-only case: valid result recovery must still work.
            resumed=resume()
            self.assertEqual(t.calls-before,1)
            self.assertEqual(sent[sent_before:],[p.digest(pending)])
            pending_folder=batch/'actor'/p.digest(pending)
            self.assertEqual(stages.read(pending_folder/'result.json')['api_requests'],2)
            self.assertEqual(stages.read(pending_folder/'attempts/001/error.json')['status'],'unknown')
            self.assertEqual(stages.read(folder/'result.json')['api_requests'],1)
            self.assertTrue((folder/'trajectory.json').is_file())
            if mode=='test':
                self.assertEqual(resumed['completed'],124);self.assertEqual(resumed['actor_requests'],125)
            else:self.assertEqual(resumed['status'],'complete')
            before=t.calls;resume();self.assertEqual(t.calls,before)

    def test_pending_first_damaged_completed_last_blocks_all_workers(self):
        for mode in ('campaign','test'):
            with self.subTest(entry=mode):
                self._assert_pending_first_completed_last(mode,'missing_result_and_response')

    def test_corrupt_result_only_completion_blocks_all_workers(self):
        for mode in ('campaign','test'):
            with self.subTest(entry=mode):
                self._assert_pending_first_completed_last(mode,'corrupt_result_only')
