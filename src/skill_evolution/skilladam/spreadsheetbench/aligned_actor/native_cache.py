"""Reuse completed native requests in aligned-Actor and trajectory-feedback runs."""
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import json


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def read(path):
    return json.loads(path.read_text())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def cached_native(native,bridge,cfg,opt,output,key):
    """Save successful native logical requests; never expand SDK/patch budgets."""
    from skilladam.methods.skilladam import _generation_payload,_generation_from_payload
    class Backend(native.backend_type(bridge)):
        def __init__(self):
            super().__init__(cfg,opt,output,optimizer=native.native_transport(bridge,cfg,opt,output,api_key=key))
            self.indices=defaultdict(int)
        def generate(self,request):
            pair=(self.iteration,request.stage);number=self.indices[pair];self.indices[pair]+=1
            path=output/'logical_calls'/f'{self.iteration:03}_{request.stage}_{number:03}'
            signature={'stage':request.stage,'messages':[dict(m) for m in request.messages],
                       'context':asdict(request.context),'metadata':dict(request.metadata)}
            # Native metadata may include read-only mapping proxies.
            import json
            signature=json.loads(json.dumps(signature,default=dict))
            if (path/'request.json').exists():require(read(path/'request.json')==signature,'Logical input changed')
            else:save(path/'request.json',signature)
            if (path/'success.json').exists():return _generation_from_payload(read(path/'success.json'))
            require(not (path/'started.json').exists(),'Preserved failed/in-flight logical request; explicit recovery required')
            save(path/'started.json',{'at':now()})
            try:
                result=self.optimizer.generate(request)
                if request.stage=='momentum_update':self.validate_output(request,result)
                save(path/'success.json',_generation_payload(result))
                return result
            except BaseException as exc:
                save(path/'failure.json',{'at':now(),'error_type':type(exc).__name__});raise
    return Backend()
