import json, sys
from modelo import resolver
from verificar import verificar
prazo, lim, nome = sys.argv[1], int(sys.argv[2]), sys.argv[3]
g = {int(k): (tuple(v) if v else None) for k, v in json.load(open('sol_gulosa.json')).items()}
sol, info = resolver(prazo=prazo, limite=lim, hint=g)
e, m, *_ = verificar(sol)
print(info); print('erros', e[:5]); print({k: m[k] for k in m})
json.dump({'sol': {str(k): v for k, v in sol.items()}, 'info': info, 'met': m}, open(f'{nome}.json', 'w'), default=str)
