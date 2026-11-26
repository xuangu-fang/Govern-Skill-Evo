"""One small compatibility request, separate from training evidence and costs."""
import os
from pathlib import Path
import requests
from dotenv import load_dotenv
import argparse
import run as campaign
from run import ROOT, freeze_check
from src.skill_evolution.v25 import evolution as ev
from src.skill_evolution.v25.benchmark import using_benchmark
from src.skill_evolution.v25.benchmarks.spreadsheetbench.adapter import SpreadsheetBenchAdapter

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=campaign.OUT)
    campaign.OUT = OUT = parser.parse_args().output.resolve()
    with using_benchmark(SpreadsheetBenchAdapter()):
        load_dotenv(ROOT/'.env',override=True)
        cfg=freeze_check();ev.check_live_environment(cfg)
        p=OUT/'preflight';assert not p.exists();p.mkdir()
        call=cfg['call_config']
        body={k:call[k] for k in ['model','max_tokens','temperature','reasoning_effort','thinking','stream']}
        body['max_tokens']=cfg['actor_profile']['actor_max_output_tokens']
        body['messages']=[{'role':'system','content':'Return the requested literal string.'},
                          {'role':'user','content':'Reply exactly READY.'}]
        ev.save(p/'request.json',{'endpoint':call['endpoint'],'body':body,'timeout_seconds':call['timeout_seconds']})
        ev.save(p/'started.json',{'at':ev.now()})
        try:
            response=requests.post(call['endpoint'],headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']},
                                   json=body,timeout=(10,call['timeout_seconds']),allow_redirects=False)
            ev.save(p/'http_status.json',{'status_code':response.status_code})
            (p/'http_response.txt').write_text(response.text)
            assert response.status_code==200, f'HTTP {response.status_code}; inspect archived response'
            value=response.json();choice=value['choices'][0]
            assert choice['finish_reason']=='stop' and choice['message']['content'].strip()=='READY'
            ev.save(p/'result.json',{'status':'passed','at':ev.now(),'response_model':value.get('model'),
                                   'usage':value.get('usage'),'tested_max_tokens':body['max_tokens'],
                                   'tested_call_parameters':{k:v for k,v in body.items() if k!='messages'},
                                   'task_data_sent':False,'training_calls':0})
            print('Compatibility request passed:',value.get('model'),value.get('usage'),flush=True)
        except BaseException as exc:
            ev.save(p/'result.json',{'status':'failed','at':ev.now(),'error_type':type(exc).__name__,'error':str(exc)})
            raise


if __name__ == '__main__':
    main()
