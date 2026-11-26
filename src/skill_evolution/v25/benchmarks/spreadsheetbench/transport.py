"""One live request per child process; parent imposes an absolute wall timeout."""
import json
import os
from pathlib import Path
import subprocess
import sys
from ...storage import write_record


class RequestError(RuntimeError):
    def __init__(self, message, retryable=True):
        super().__init__(message); self.retryable=retryable


def request(messages, directory, timeout, config):
    directory=Path(directory)
    public={'messages':messages,'call_config':{**config['call_config'],'max_tokens':config['actor_profile']['actor_max_output_tokens']},'timeout':timeout}
    write_record(directory/'request.json',public)
    try:
        proc=subprocess.run([sys.executable,'-m',__name__,'--once',str(directory)],capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RequestError('API request timed out') from exc
    if (directory/'response.json').exists():return json.loads((directory/'response.json').read_text())
    if (directory/'request_error.json').exists():
        error=json.loads((directory/'request_error.json').read_text())
        raise RequestError(error['error'],error['retryable'])
    raise RequestError(f'API worker exited {proc.returncode} without a saved response',False)


def once(directory):
    import requests
    from urllib.parse import urlsplit
    directory=Path(directory);saved=json.loads((directory/'request.json').read_text());cfg=saved['call_config']
    key=os.environ.get('OPENAI_API_KEY')
    if not key:raise RequestError('OPENAI_API_KEY is not configured',False)
    body={k:cfg[k] for k in ('model','max_tokens','temperature','reasoning_effort','thinking','stream')}
    body['messages']=saved['messages']
    with requests.Session() as session:
        if '.intra.' in (urlsplit(cfg['endpoint']).hostname or ''):session.trust_env=False
        raw=session.post(cfg['endpoint'],headers={'Authorization':f'Bearer {key}'},json=body,
                         timeout=(min(10,saved['timeout']),saved['timeout']),allow_redirects=False)
    write_record(directory/'http_status.json',{'status_code':raw.status_code})
    if not 200<=raw.status_code<300:
        raise RequestError(f'API returned HTTP {raw.status_code}',raw.status_code in (408,429,500,502,503,504))
    try:
        data=raw.json();choice=data['choices'][0]
        result={'content':choice['message'].get('content') or '', 'finish_reason':choice['finish_reason'],
                'response_model':data.get('model'),'usage':data.get('usage')}
        if not isinstance(result['content'],str):raise ValueError()
    except (ValueError,KeyError,TypeError,IndexError) as exc:raise RequestError('Malformed API response') from exc
    write_record(directory/'response.json',result)


if __name__=='__main__':
    folder=Path(sys.argv[2])
    try:once(folder)
    except Exception as exc:
        retryable=isinstance(exc,RequestError) and exc.retryable
        if type(exc).__name__ in ('Timeout','ReadTimeout','ConnectTimeout','ConnectionError','ChunkedEncodingError'):retryable=True
        write_record(folder/'request_error.json',{'error':str(exc) if isinstance(exc,RequestError) else type(exc).__name__,'retryable':retryable})
        sys.exit(1)
