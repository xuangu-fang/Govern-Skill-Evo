"""Exercise real requests eager body reads without sockets or environment requests."""
import json
from unittest.mock import patch
import pytest
import requests
from urllib3.exceptions import ProtocolError
from src.adapters.alfworld.run_task_upstream import chat
from src.adapters.alfworld.run_task_skill import RecordingSession, run_episode
from src.adapters.alfworld.skill_runtime import load_skill, execution_protocol
from src.adapters.alfworld.response_archive import verify_response_archive
from tests.adapters.alfworld.test_skill_episode import FakeEnvironment


class BrokenBody:
    def stream(self, *args, **kwargs):
        yield b'{"choices":'
        raise ProtocolError('Connection broken: incomplete chunk')


@pytest.mark.parametrize('failure,failures', [
    ('chunked', 1), ('chunked', 3), ('timeout', 1), ('connection', 1),
    ('429', 1), ('length', 1), ('invalid_url', 1),
])
def test_step_retry_and_archive(tmp_path, failure, failures):
    env=FakeEnvironment(win=True); sent=[]
    record={'steps':[], 'won':False,'skill':load_skill(), 'protocol':execution_protocol(50), 'status':'starting'}
    output=tmp_path/'trajectory.json'
    # HTTPAdapter.send is the wire boundary. Session.send consumes response.content
    # before Session.post returns, exactly as in the real non-streaming request.
    def send(request, **kwargs):
        assert env.count==0
        sent.append(json.loads(request.body))
        bad=len(sent)<=failures
        if bad and failure=='timeout':raise requests.Timeout()
        if bad and failure=='connection':raise requests.ConnectionError()
        if bad and failure=='invalid_url':raise requests.exceptions.InvalidURL()
        response=requests.Response();response.status_code=200;response.request=request;response.url=request.url
        if bad and failure=='chunked':
            response.raw=BrokenBody()
        else:
            response.status_code=429 if bad and failure=='429' else 200
            response._content=json.dumps({'choices':[{'finish_reason':'length' if bad and failure=='length' else 'stop',
                'message':{'content':'<action>look</action>'}}],
                'usage':{'prompt_tokens':10,'completion_tokens':5,'total_tokens':15}}).encode()
        return response
    with requests.Session() as session, patch.object(requests.adapters.HTTPAdapter,'send',side_effect=send), \
            patch('src.adapters.alfworld.run_task_upstream.time.sleep'):
        recorder=RecordingSession(session,record,output,archive_responses=True)
        run_episode(env,lambda messages:chat(recorder,'https://example.invalid/chat','unused','test',messages,
                    max_attempts=3,strict_response=True),record,output)
    stopped=failures==3 or failure=='invalid_url'
    assert len(sent)==(failures if stopped else failures+1)
    assert all(body==sent[0] for body in sent)
    assert env.count==(0 if stopped else 1)
    assert len(record['steps'])==1
    assert record['status']==('error' if stopped else 'success')
    attempts=record['steps'][0]['transport_attempts']
    assert len(attempts)==len(sent)
    for attempt in attempts:
        assert attempt['elapsed_seconds']>=0 and attempt['finished_at']
        verify_response_archive(output,attempt)
    if failure in ('chunked','timeout','connection','invalid_url'):
        assert all(a['usage'] is None and a['status']=='error' for a in attempts[:failures])
        assert all('raw_response' not in a for a in attempts[:failures])
    if failure=='chunked':
        assert all(a['error_type']=='ChunkedEncodingError' for a in attempts[:failures])
    assert json.loads(output.read_text())==record
