import json, sys
from modelo import resolver
from verificar import verificar
prazo, lim, nome, base = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
d=json.load(open(base)); h={int(k):(tuple(v) if v else None) for k,v in (d['sol'] if 'sol' in d else d).items()}
sol,info=resolver(prazo=prazo,limite=lim,hint=h)
e,m,*_=verificar(sol); print(info); print('erros',e[:3]); print(m)
json.dump({'sol':{str(k):v for k,v in sol.items()},'info':info,'met':m},open(f'{nome}.json','w'),default=str)
