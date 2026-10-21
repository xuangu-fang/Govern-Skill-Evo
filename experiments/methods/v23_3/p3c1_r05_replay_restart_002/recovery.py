"""Finish authorized rounds two and three after the documented handoff interruption."""
import os
import signal
import subprocess
import sys
import time
from . import run
HERE=run.HERE
read,save,now=run.read,run.save,run.now

def verify():
    from .parallel import verify as verify_parallel
    verify_parallel()
    for path,h in read(HERE/'recovery_freeze.json')['files'].items():assert run.previous.original.sha(path)==h,path

def main():
    verify();(HERE/'recovery.claim').open('x').close()
    cfg=read(HERE/'parallel_config.json');prior=read(HERE/'results.json');results=list(prior['results'])
    assert prior['stop_reason']=='non_429_technical_error'
    unusual=[r for r in results if r['status'] not in run.COMPLETE and r.get('last_http_status')!=429]
    assert len(unusual)==1 and unusual[0]['adopted'] and unusual[0]['condition']=='Parent' and unusual[0]['ref']=='P7'
    done={(r['condition'],r['ref']) for r in results if r['status'] in run.COMPLETE}
    spent=sum(r['http_requests'] for r in results);fatal=False;stop='round_limit'
    print('Documented handoff recovery: cooldown 60 seconds before round 2',flush=True);time.sleep(60)
    for round_no in range(2,4):
        folder=HERE/f'attempt_{round_no}';folder.mkdir(exist_ok=True)
        queue=[j for j in run.JOBS if j not in done];active=[];limited=False
        if round_no==1:
            queue.remove(('Parent','P7'))
            active.append({'condition':'Parent','ref':'P7','proc':None,'pid':cfg['adopted_episode_pid'],'adopted':True})
        while active or (queue and not limited and not fatal):
            while queue and len(active)<4 and not limited and not fatal and spent+50*(len(active)+1)<=450:
                c,r=queue.pop(0);log=(folder/f'{c}_{r}.log').open('x')
                proc=subprocess.Popen([run.previous.original.PYTHON,'-B','-m','experiments.methods.v23_3.p3c1_r05_replay_restart_002.run','episode',str(round_no),c,r],cwd=run.ROOT,stdout=log,stderr=subprocess.STDOUT,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
                log.close();active.append({'condition':c,'ref':r,'proc':proc,'pid':proc.pid,'adopted':False})
                print(f'round {round_no}: started {c}/{r}, pid={proc.pid}',flush=True)
            if not active:
                if queue and not limited and not fatal:stop='request_budget_reservation';fatal=True
                break
            for job in active[:]:
                c,r=job['condition'],job['ref'];path=folder/f'episodes/{c}/{r}/trajectory.json';audit=path.parent/'audit.json'
                if job['adopted']:
                    if not audit.exists():
                        try:os.kill(job['pid'],0);continue
                        except ProcessLookupError:pass
                    exitcode=None
                else:
                    exitcode=job['proc'].poll()
                    if exitcode is None:continue
                rec=read(path) if path.exists() else {};status=rec.get('status','setup_error')
                attempts=[t for s in rec.get('steps',[]) for t in s.get('transport_attempts',[])]
                http=attempts[-1].get('http_status') if attempts else None
                row={'round':round_no,'condition':c,'ref':r,'exit':exitcode,'adopted':job['adopted'],'status':status,'last_http_status':http,'http_requests':len(attempts),'trajectory':str(path),'at':now()}
                results.append(row);spent+=len(attempts);active.remove(job)
                if status in run.COMPLETE and exitcode in (None,0):done.add((c,r))
                elif status=='error' and http==429:limited=True
                else:fatal=True;stop='non_429_technical_error'
                print(str(row),flush=True)
            save(HERE/'recovery_progress.json',{'at':now(),'round':round_no,'results':results,'active':[{'condition':j['condition'],'ref':j['ref'],'pid':j['pid']} for j in active],'remaining':[j for j in run.JOBS if j not in done],'spent_http':spent,'stop_scheduling':limited or fatal})
            if active:time.sleep(2)
        if len(done)==len(run.JOBS):stop='all_completed';break
        if fatal:break
        if limited and round_no<3:
            print('HTTP429: cooldown 60 seconds after all in-flight episodes finish',flush=True);time.sleep(60)
    save(HERE/'final_results.json',{'at':now(),'stop_reason':stop,'results':results,'remaining':[j for j in run.JOBS if j not in done],'spent_http':spent,'parallel_user_amendment':True})

if __name__=='__main__':main()
