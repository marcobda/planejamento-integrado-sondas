import json
from modelo import resolver
from verificar import verificar
d=json.load(open('sol_brando.json')); h={int(k):(tuple(v) if v else None) for k,v in d['sol'].items()}
sol,info=resolver(limite=300,hint=h,so_alocar=True)
e,m,*_=verificar(sol); print(info); print(e[:3]); print(m['alocados'],m['nao_alocados'])
json.dump({'sol':{str(k):v for k,v in sol.items()},'info':info,'met':m},open('sol_maxaloc.json','w'),default=str)
