"""Local HTTP stub only; never contacts any model service."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
import json
import time
import pytest
from src.skill_evolution.v25.benchmarks.spreadsheetbench import transport
from .support import config


@pytest.mark.parametrize('mode',['ok','malformed','unavailable','unauthorized','timeout'])
@pytest.mark.parametrize('actor_max_tokens',[16384,32768,49152])
def test_actual_request_worker(tmp_path,monkeypatch,mode,actor_max_tokens):
    seen=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            seen.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
            if mode=='timeout':time.sleep(2)
            status=503 if mode=='unavailable' else 401 if mode=='unauthorized' else 200
            self.send_response(status);self.send_header('Content-Type','application/json');self.end_headers()
            value={} if mode=='malformed' else {'choices':[{'message':{'content':'synthetic response'},'finish_reason':'stop'}],'usage':{}}
            try:self.wfile.write(json.dumps(value).encode())
            except BrokenPipeError:pass
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    monkeypatch.setenv('OPENAI_API_KEY','offline-placeholder')
    cfg=config(tmp_path/'data',n=1);cfg['call_config']['endpoint']=f'http://127.0.0.1:{server.server_port}/chat/completions'
    cfg['actor_profile']['actor_max_output_tokens']=actor_max_tokens
    directory=tmp_path/'request';directory.mkdir();messages=[{'role':'user','content':'Synthetic transport check'}]
    try:
        if mode=='ok':assert transport.request(messages,directory,5,cfg)['content']=='synthetic response'
        else:
            with pytest.raises(transport.RequestError) as caught:transport.request(messages,directory,1 if mode=='timeout' else 5,cfg)
            assert caught.value.retryable==(mode!='unauthorized')
        assert len(seen)==1 and seen[0]['messages']==messages and seen[0]['max_tokens']==actor_max_tokens
        assert 'offline-placeholder' not in (directory/'request.json').read_text()
    finally:server.shutdown();server.server_close()
