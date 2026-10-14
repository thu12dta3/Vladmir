
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, asdict
import math
from . import chemistry

@dataclass(frozen=True)
class ToolContract:
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    risk_level: str
    timeout: float
    permissions: tuple[str,...]
    side_effects: tuple[str,...] = ()

@dataclass(frozen=True)
class ActionRequest:
    tool: str
    arguments: dict

class AuthorizationLayer:
    def authorize(self, contract: ToolContract, grants: frozenset[str]):
        if not set(contract.permissions) <= grants: raise PermissionError('Permissão de tool ausente')
        if contract.risk_level != 'READ_ONLY' or contract.side_effects: raise PermissionError('Esta fase só permite leitura/cálculo')

def validate_object(value, schema):
    if not isinstance(value,dict): raise ValueError('Objeto esperado')
    properties=schema.get('properties',{})
    if set(value)-set(properties) or set(schema.get('required',()))-set(value): raise ValueError('Campos inválidos/ausentes')
    for key,item in value.items():
        rule=properties[key]; kind=rule.get('type')
        if kind=='number' and (type(item) not in (int,float) or not math.isfinite(item)): raise ValueError('Número inválido')
        if kind=='integer' and type(item) is not int: raise ValueError('Inteiro inválido')
        if kind=='string' and (not isinstance(item,str) or not item or len(item)>rule.get('maxLength',256)): raise ValueError('Texto inválido')
        if kind=='array' and not isinstance(item,list): raise ValueError('Lista inválida')
        if kind=='boolean' and type(item) is not bool: raise ValueError('Boolean inválido')
        if kind=='object' and not isinstance(item,dict): raise ValueError('Objeto inválido')
        if 'minimum' in rule and item<rule['minimum']: raise ValueError('Valor abaixo do mínimo')
        if 'maximum' in rule and item>rule['maximum']: raise ValueError('Valor acima do máximo')
        if 'enum' in rule and item not in rule['enum']: raise ValueError('Valor fora do enum')

class ToolRegistry:
    def __init__(self): self._entries={}; self.authorization=AuthorizationLayer()
    def register(self, contract: ToolContract, function):
        if contract.name in self._entries: raise ValueError('Tool duplicada')
        if contract.timeout<=0 or not contract.permissions: raise ValueError('Contrato incompleto')
        self.authorization.authorize(contract,frozenset(contract.permissions))
        self._entries[contract.name]=(contract,function)
    def contracts(self): return [asdict(c) for c,_ in self._entries.values()]
    def invoke(self, request: ActionRequest, grants=frozenset()):
        if request.tool not in self._entries: raise ValueError('Tool não registrada')
        c,function=self._entries[request.tool]
        self.authorization.authorize(c,frozenset(grants))
        validate_object(request.arguments,c.input_schema)
        executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='vladmir-tool')
        future=executor.submit(function,**request.arguments)
        try:
            result=future.result(timeout=c.timeout)
            validate_object(result,c.output_schema)
            return result
        except TimeoutError: raise TimeoutError('Tool excedeu o orçamento de tempo') from None
        finally: executor.shutdown(wait=False,cancel_futures=True)

def schema(properties): return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
NUMBER={'type':'number','minimum':0,'maximum':1e12}
POSITIVE={'type':'number','minimum':1e-12,'maximum':1e12}
TEXT={'type':'string','maxLength':256}

def default_registry(knowledge_path=None):
    registry=ToolRegistry()
    outputs={
        'density':{'value':NUMBER,'unit':TEXT},
        'molar_mass':{'formula':TEXT,'value':NUMBER,'unit':TEXT,'atoms':{'type':'object'},'reference':TEXT,'precision':TEXT},
        'stoichiometry':{'value':NUMBER,'unit':TEXT,'assumption':TEXT},
        'unit_conversion':{'value':{'type':'number'},'unit':TEXT},
        'ideal_gas':{'value':NUMBER,'unit':TEXT,'assumption':TEXT},
        'ph_calculation':{'value':{'type':'number'},'unit':TEXT,'assumption':TEXT},
        'periodic_table_lookup':{'symbol':TEXT,'value':NUMBER,'unit':TEXT,'reference':TEXT},
    }
    inputs={
        'density':{'mass':NUMBER,'mass_unit':TEXT,'volume':POSITIVE,'volume_unit':TEXT},
        'molar_mass':{'formula':TEXT},
        'stoichiometry':{'known_moles':NUMBER,'known_coefficient':{'type':'integer','minimum':1,'maximum':1000},'target_coefficient':{'type':'integer','minimum':1,'maximum':1000}},
        'unit_conversion':{'value':{'type':'number','minimum':-1e12,'maximum':1e12},'from_unit':TEXT,'to_unit':TEXT},
        'ideal_gas':{'moles':NUMBER,'temperature_kelvin':POSITIVE,'pressure_pa':POSITIVE},
        'ph_calculation':{'concentration':{'type':'number','minimum':1e-6,'maximum':1}},
        'periodic_table_lookup':{'symbol':TEXT},
    }
    for name,properties in inputs.items():
        registry.register(ToolContract('chemistry.'+name,'Cálculo determinístico educacional: '+name,
                          schema(properties),schema(outputs[name]),'READ_ONLY',1.,('tools.calculate',)),getattr(chemistry,name))
    from .chemical_facts import molecular_formula
    registry.register(ToolContract('chemistry.molecular_formula','Identidade molecular curada com fonte, sem fabricação',
                      schema({'compound':TEXT}),schema({'name':TEXT,'formula':TEXT,'reference':TEXT,'verified_on':TEXT}),
                      'READ_ONLY',1.,('knowledge.read',)),molecular_formula)
    from pathlib import Path
    from .knowledge import KnowledgeStore, DEFAULT_DB
    path=Path(knowledge_path or DEFAULT_DB)
    def knowledge_search(query):
        if not path.exists(): return {'hits':[]}
        with KnowledgeStore(path,read_only=True) as store: return {'hits':[h.to_dict() for h in store.search(query)]}
    def knowledge_stats():
        if not path.exists(): return {'sources':0,'active_sources':0,'chunks':0,'available':False}
        with KnowledgeStore(path,read_only=True) as store:
            data=store.stats(); return {key:data[key] for key in ('sources','active_sources','chunks')} | {'available':True}
    for name,function,inputs,outputs in (
        ('knowledge.search',knowledge_search,{'query':TEXT},{'hits':{'type':'array'}}),
        ('knowledge.stats',knowledge_stats,{}, {'sources':NUMBER,'active_sources':NUMBER,'chunks':NUMBER,'available':{'type':'boolean'}})):
        registry.register(ToolContract(name,'Leitura local de conhecimento',schema(inputs),schema(outputs),'READ_ONLY',1.,('knowledge.read',)),function)
    return registry
