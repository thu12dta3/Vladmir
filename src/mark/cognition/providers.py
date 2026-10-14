
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
import base64
import copy
import json
import logging
import time
import urllib.request
from ..vision import image_base64
from ..vision_quality import prepare_frame
from ..conversation_context import validated_history
from ..core.context import CoreContext

log = logging.getLogger('vladmir.brain')

@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    system: str | None = None
    image: object = None
    images: tuple[str, ...] = ()
    num_predict: int | None = None
    output_format: object = None
    thinking_mode: str = 'NORMAL'
    history: tuple[dict, ...] = ()
    context: CoreContext = field(default_factory=CoreContext.create)

@dataclass(frozen=True)
class ModelMetrics:
    model: str
    latency_ms: float
    prompt_tokens: int
    output_tokens: int
    attempts: int
    success: bool
    fallback_from: str | None = None
    fallback_reason: str | None = None

@dataclass(frozen=True)
class ModelResponse:
    text: str
    metrics: ModelMetrics

class ModelProvider(ABC):
    def describe(self): return {}
    def set_keep_alive(self, seconds): raise NotImplementedError("Provider sem lifecycle implementado")
    @abstractmethod
    def generate(self, request: ModelRequest) -> ModelResponse: ...

class OllamaProvider(ModelProvider):

    def __init__(self, cfg): self.cfg = cfg; self.last_metrics = None
    def set_keep_alive(self, seconds):
        payload={'model':self.cfg['ollama']['model'],'messages':[],'stream':False,'keep_alive':seconds}
        req=urllib.request.Request(self.cfg['ollama']['url'].rstrip('/')+'/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        timeout=min(int(self.cfg['ollama'].get('timeout',180)),180) if seconds<0 else 10
        with urllib.request.urlopen(req,timeout=timeout): pass
    def describe(self):
        req=urllib.request.Request(self.cfg['ollama']['url'].rstrip('/')+'/api/show',data=json.dumps({'model':self.cfg['ollama']['model']}).encode(),headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req,timeout=5) as response: data=json.load(response).get('details',{})
            return {key:data.get(key,'UNKNOWN') for key in ('parameter_size','quantization_level','family')}
        except (OSError,ValueError): return {'parameter_size':'UNKNOWN','quantization_level':'UNKNOWN'}
    def generate(self, request):
        started = time.perf_counter()
        cfg = self.cfg
        messages = []
        if request.system: messages.append({'role':'system', 'content':request.system})
        messages.extend(validated_history(request.history))
        msg = {'role':'user', 'content':request.prompt}
        images = ([image_base64(request.image)] if request.image else []) + list(request.images)
        if images:
            prepared = []
            for encoded in images:
                try:
                    data = base64.b64decode(encoded, validate=True)
                    prepared.append(base64.b64encode(prepare_frame(data)).decode('ascii'))
                except (ValueError, TypeError):
                    raise ValueError('A imagem está corrompida ou excede os limites de resolução.') from None
            msg['images'] = prepared
        messages.append(msg)
        ollama_cfg = cfg['ollama']
        options = {
            'temperature': 0.2 if request.output_format else float(ollama_cfg.get('temperature', 0.7)),
            'top_p': float(ollama_cfg.get('top_p', 0.8)),
            'top_k': int(ollama_cfg.get('top_k', 20)),
            'repeat_penalty': float(ollama_cfg.get('repeat_penalty', 1.0)),
            'num_ctx': int(ollama_cfg.get('num_ctx', 8192)),
            'num_predict':int(request.num_predict or ollama_cfg.get('num_predict',2048)),
        }
        payload = {'model':ollama_cfg['model'], 'stream':False,
                   'think': bool(cfg['ollama'].get('think',False)),
                   'keep_alive': ollama_cfg.get('keep_alive',0), 'messages':messages,
                   'options':options}
        if request.output_format: payload['format'] = request.output_format
        unfinished = False
        prompt_tokens = output_tokens = 0
        for attempt in range(2):
            if attempt: payload['messages'][-1]['content'] = request.prompt + '\n\nForneça agora a resposta final, sem raciocínio.'
            req = urllib.request.Request(cfg['ollama']['url'].rstrip('/') + '/api/chat', data=json.dumps(payload).encode(), headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(req, timeout=int(cfg['ollama']['timeout'])) as response:
                result = json.load(response)
            prompt_tokens += int(result.get('prompt_eval_count',0))
            output_tokens += int(result.get('eval_count',0))
            content = result.get('message',{}).get('content','').strip()


            structured = False
            if request.output_format:
                try: structured = isinstance(json.loads(content),(dict,list))
                except (ValueError,TypeError): pass
            if not structured and ('<think>' in content or '</think>' in content):
                unfinished |= '<think>' in content and '</think>' not in content
                content = content.rsplit('</think>',1)[-1].strip() if '</think>' in content else ''
            self.last_metrics = ModelMetrics(payload['model'],(time.perf_counter()-started)*1000,prompt_tokens,output_tokens,attempt+1,bool(content))
            if content: return ModelResponse(content,self.last_metrics)
            log.warning('Ollama retornou resposta vazia; tentativa %d de 2.',attempt+1)
        fallback = cfg.get('models',{}).get('call')
        if (cfg.get('cognition',{}).get('empty_fallback',True)
                and payload['model']==cfg.get('models',{}).get('chat')
                and isinstance(fallback,str) and fallback and fallback!=payload['model']):
            from ..model_state import ModelSession
            local=copy.deepcopy(cfg);local['ollama']['model']=fallback;local['ollama']['think']=False
            local.setdefault('cognition',{})['empty_fallback']=False
            session=ModelSession(local);provider=OllamaProvider(local)
            try:
                session.wake()
                reply=provider.generate(request)
                metrics=replace(reply.metrics,latency_ms=(time.perf_counter()-started)*1000,
                    prompt_tokens=prompt_tokens+reply.metrics.prompt_tokens,
                    output_tokens=output_tokens+reply.metrics.output_tokens,
                    attempts=2+reply.metrics.attempts,fallback_from=payload['model'],fallback_reason='empty_final')
                self.last_metrics=metrics
                return ModelResponse(reply.text,metrics)
            except Exception:
                failed=provider.last_metrics
                self.last_metrics=ModelMetrics(fallback,(time.perf_counter()-started)*1000,
                    prompt_tokens+(failed.prompt_tokens if failed else 0),
                    output_tokens+(failed.output_tokens if failed else 0),
                    2+(failed.attempts if failed else 0),False,
                    fallback_from=payload['model'],fallback_reason='empty_final')
                raise
            finally:
                session.sleep()
        if unfinished: raise RuntimeError('Ollama retornou raciocínio sem resposta final; o texto foi bloqueado por segurança.')
        raise RuntimeError('Ollama não retornou uma resposta final após duas tentativas.')

LocalQwenProvider = OllamaProvider
PROVIDERS = {'ollama': OllamaProvider}

def get_provider(cfg) -> ModelProvider:
    name = cfg.get('cognition',{}).get('model_provider','ollama')
    if name not in PROVIDERS: raise ValueError('ModelProvider não registrado')
    return PROVIDERS[name](cfg)
