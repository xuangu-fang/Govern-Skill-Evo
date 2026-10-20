"""Offline fake HTTP: ensure failures are archived and never retried."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch,MagicMock
import json,unittest,requests
import control as c

class OnceOnlyTests(unittest.TestCase):
    def exercise(self,content):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);d=root/'cases'/'probe';d.mkdir(parents=True)
            case={'id':'probe','stage':'classification','profile':'v22.unified_dsc.v4','timeout_seconds':600}
            request={'model':'deepseek-v4-pro','messages':[{'role':'user','content':'offline fixture'}]}
            (d/'request.json').write_text(json.dumps(request))
            response=requests.Response();response.status_code=200;response.headers['content-type']='application/json'
            response._content=json.dumps({'model':'offline_fake','choices':[{'finish_reason':'stop','message':{'content':content}}],
                                          'usage':{'prompt_tokens':1,'completion_tokens':1,'total_tokens':2}}).encode()
            session=MagicMock();session.__enter__.return_value=session;session.post.return_value=response
            with patch.object(c,'ROOT',root),patch.object(c,'verify',return_value=0),patch.object(c,'validate',return_value=None),patch.object(c.requests,'Session',return_value=session):
                result=c.run_one(case,'https://offline.invalid/chat/completions','not-a-real-key')
                self.assertEqual(session.post.call_count,1)
                self.assertEqual(result['attempts'],1)
                self.assertTrue((d/'response.json').exists())
                self.assertTrue((d/'attempt.lock').exists())
                with self.assertRaises(FileExistsError):c.run_one(case,'https://offline.invalid/chat/completions','not-a-real-key')
                self.assertEqual(session.post.call_count,1)
            return result
    def test_invalid_content_is_not_repaired_or_retried(self):
        result=self.exercise('reasoning</think>{"groups":[]}')
        self.assertFalse(result['contract_valid']);self.assertFalse(result['production_json'])
        self.assertEqual(result['usage']['total_tokens'],2)
    def test_success_keeps_one_attempt(self):
        result=self.exercise('{"groups":[]}');self.assertTrue(result['contract_valid'])

if __name__=='__main__':unittest.main()
