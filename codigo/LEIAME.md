# Sprint 3 · Planejamento Integrado de Sondas — código dos resultados

Python 3. Instalar: `pip install pandas openpyxl ortools matplotlib`
Colocar a planilha `Estudo_de_caso_-_cronograma_de_sondas_1.xlsx` nesta pasta.

## Arquivos
| Arquivo | O que faz |
|---|---|
| dados.py | Lê a planilha; data limite efetiva; atribui kits/ANM (n-ésimo kit → n-ésimo poço) |
| modelo.py | Modelo CP-SAT (`resolver`) e heurística gulosa (`gulosa`) |
| heuristica.py | Heurística gulosa comentada (E1) |
| limite.py | Limite inferior com sondas ilimitadas (E0) |
| verificar.py | Checagem independente das restrições + métricas |
| rodar.py / rodar2.py / rodar_aloc.py | Rodam o modelo e salvam a solução em .json |
| figuras.py | Gera os gráficos da pasta fig/ |
| sol_*.json | Soluções já calculadas (não precisa rodar de novo) |

## Como reproduzir os resultados dos slides
```
python limite.py                                  # E0: 38 poços, 5.300 dias, causas
python heuristica.py                              # E1: gera sol_gulosa.json (82 entregues)
python rodar.py brando 450 sol_brando             # E2, partindo da heurística
python rodar2.py brando 450 sol_brando2 sol_brando.json   # E2 refinado (solução usada nos slides)
python rodar.py duro 450 sol_duro                 # E3: ótimo 59 poços no prazo
python figuras.py                                 # gráficos
```
O CP-SAT é paralelo e tem limite de tempo: rodar de novo pode dar solução um pouco diferente.
Os números dos slides vêm dos .json desta pasta (sol_gulosa, sol_brando2, sol_duro), conferidos com verificar.py (0 violações).

## Roteirização (E4)
`roteirizacao.py` trata o problema como VRP com janelas de tempo (sonda = veículo, poço = cliente), resolve com o OR-Tools Routing e passa as rotas por um decodificador que recalcula as datas com todas as regras do modelo base. Solução salva em `sol_vrp.json`.
```
python roteirizacao.py 300
```
