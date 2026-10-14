
from pathlib import Path
import json
import os
import time
import uuid
from .storage import private_file

ALLOWED={'event_id','recorded_at_ns','model','latency_ms','prompt_tokens','output_tokens','attempts','success'}
DEFAULT_LOG=Path.home()/'.local/state/vladmir/cognition/metrics.jsonl'

def record_metrics(metrics,cfg):
    if not cfg.get('cognition',{}).get('telemetry',False): return
    data={key:value for key,value in metrics.items() if key in ALLOWED and key not in {'event_id','recorded_at_ns'}}
    data.update(event_id=uuid.uuid4().hex,recorded_at_ns=time.time_ns())
    path=private_file(DEFAULT_LOG)
    fd=os.open(path,os.O_WRONLY|os.O_APPEND|getattr(os,'O_NOFOLLOW',0))
    with os.fdopen(fd,'a',encoding='utf-8') as stream:
        line=json.dumps(data,ensure_ascii=False,allow_nan=False)+'\n'
        if os.fstat(stream.fileno()).st_size+len(line.encode())>1_000_000:return
        stream.write(line)
