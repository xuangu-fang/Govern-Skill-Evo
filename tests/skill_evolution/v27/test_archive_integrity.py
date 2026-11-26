from unittest.mock import patch
from . import test_offline as original
from .archive_fixture import interrupted_batch, corruptions, damage, snapshot
from .test_actor_recovery import TestDataset
from .support import Dataset, Transport, SKILL, config, response
from src.skill_evolution.v27 import evolution, evaluation, stages
from src.skill_evolution.v27.benchmark import using_benchmark
from src.skill_evolution.v27.benchmarks.lmb import actor, protocol as p, adapter as adapter_module
from src.skill_evolution.v27.benchmarks.lmb.adapter import LMBAdapter
from src.skill_evolution.v27.transport import RequestFailure


class ArchiveIntegrityTests(original.Base):
    def mixed_batch(self, mode):
        data = Dataset(self.root/'data', 2) if mode == 'campaign' else TestDataset(self.root/'data')
        ids = list(data.rows); pending, retried = ids[0], ids[-1]
        transport = Transport(fn=interrupted_batch(pending, retried))
        adapter = LMBAdapter(data, transport, gate_metric=p.EM_GATE if mode == 'campaign' else None)
        method, method_calls = original.CampaignTests.generator(self, no_change='diagnosis')
        root=self.root/'run'; skill=self.root/'skill.md';skill.write_text(SKILL)
        with using_benchmark(adapter), patch.object(evaluation,'TEST_IDS',tuple(ids)):
            if mode == 'campaign':
                start=lambda: evolution.run_campaign(root,config=config(adapter),generate=method)
                resume=lambda: evolution.run_campaign(root,generate=method,resume=True)
                batch=root/'rounds/R01/parent_runs'
            else:
                start=lambda: evaluation.run_evaluation(root,adapter=adapter,skill_file=skill)
                resume=lambda: evaluation.run_evaluation(root,adapter=adapter,skill_file=skill,resume=True)
                batch=root/'batch'
            with self.assertRaises(KeyboardInterrupt): start()
            self.assertFalse((batch/'records.json').exists())
            folder=batch/'actor'/p.digest(retried)
            self.assertEqual(stages.read(folder/'result.json')['api_requests'],2)
            before=transport.calls; before_methods=len(method_calls)
            transport.fn=None
            for name,operation in corruptions():
                with self.subTest(mode=mode,file=name,operation=str(operation)):
                    path=folder/name; saved=path.read_bytes(); damage(path,operation); damaged=snapshot(batch)
                    with patch.object(adapter_module,'ThreadPoolExecutor',side_effect=AssertionError('Started workers before preflight')):
                        self.reject(resume)
                    self.assertEqual(transport.calls,before);self.assertEqual(len(method_calls),before_methods)
                    self.assertEqual(snapshot(batch),damaged)
                    path.write_bytes(saved)
            resume()
            self.assertEqual(transport.calls,before+1)
            pending_result=stages.read(batch/'actor'/p.digest(pending)/'result.json')
            self.assertEqual(pending_result['api_requests'],2)
            resume();self.assertEqual(transport.calls,before+1)

    def test_campaign_all_archive_corruptions_stop_before_pending_requests(self):
        self.mixed_batch('campaign')

    def test_test_all_archive_corruptions_stop_before_pending_requests(self):
        self.mixed_batch('test')

    def test_unfinished_failed_slot_is_audited_before_other_workers(self):
        data=Dataset(self.root/'data',2); transport=Transport(fn=lambda m,d:response(None,'length'))
        adapter=LMBAdapter(data,transport,gate_metric=p.EM_GATE);skill=self.root/'skill.md';skill.write_text(SKILL)
        root=self.root/'batch';ids=list(data.rows)
        with patch.object(actor.time,'sleep',side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                adapter.actor_batch(ids,skill,root,{'split':'train','role':'parent'})
        self.assertFalse(list(root.rglob('result.json')))
        slot=root/'actor'/p.digest(ids[-1])/'attempts/001'
        file=slot/'http_response.txt'
        # Adding a response artifact after the failed receipt also changes its fingerprint.
        file.write_text('unexpected artifact')
        before=transport.calls;transport.fn=None
        with patch.object(adapter_module,'ThreadPoolExecutor',side_effect=AssertionError('Workers started')):
            self.reject(adapter.actor_batch,ids,skill,root,{'split':'train','role':'parent'})
        self.assertEqual(transport.calls,before)
        file.unlink()
        request=slot/'request.json';saved=request.read_bytes();request.unlink()
        with patch.object(adapter_module,'ThreadPoolExecutor',side_effect=AssertionError('Workers started')):
            self.reject(adapter.actor_batch,ids,skill,root,{'split':'train','role':'parent'})
        self.assertEqual(transport.calls,before);request.write_bytes(saved)
        adapter.actor_batch(ids,skill,root,{'split':'train','role':'parent'})
        self.assertEqual(transport.calls,before+2)

    def test_prepared_request_without_started_marker_can_resume_same_slot(self):
        case=Dataset(self.root/'data',1).case('synthetic:000');transport=Transport();root=self.root/'actor'
        original_save=actor.save
        def interrupt(path,value):
            if path.name=='request_started.json':raise KeyboardInterrupt()
            return original_save(path,value)
        with patch.object(actor,'save',side_effect=interrupt),self.assertRaises(KeyboardInterrupt):
            actor.execute(case,SKILL,root,transport)
        self.assertEqual(transport.calls,0)
        result=actor.execute(case,SKILL,root,transport)
        self.assertEqual(result['api_requests'],1);self.assertEqual(transport.calls,1)

    def test_http_and_network_failure_receipts_preserve_retry_classification(self):
        case=Dataset(self.root/'data',1).case('synthetic:000')
        for index,kind in enumerate(('http','json','network')):
            def generate(m,slot):
                if slot.name!='001':return response()
                if kind=='network':raise RequestFailure('ConnectionError')
                body='temporary failure' if kind=='http' else 'invalid JSON'
                status=503 if kind=='http' else 200
                (slot/'http_response.txt').write_text(body)
                stages.save(slot/'http_status.json',{'status_code':status})
                raise RequestFailure('HTTP 503' if kind=='http' else 'Malformed API JSON')
            t=Transport(fn=generate);root=self.root/str(index)
            result=actor.execute(case,SKILL,root,t)
            self.assertEqual(actor.read_completed(case,SKILL,root,p.ACTOR),result)
            self.assertEqual(t.calls,2)
            path=root/'attempts/001/error.json';error=stages.read(path)
            error['error']='wrong classification';stages.save(path,error)
            self.reject(actor.read_completed,case,SKILL,root,p.ACTOR)
