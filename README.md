# Planejamento Integrado de Sondas — Campo de Búzios

Código do Projeto de Graduação em Engenharia de Produção (ENG4140, PUC-Rio, 2026.2), desenvolvido no Capstone com o Instituto Tecgraf/PUC-Rio.

**Grupo:** Felipe D'Abreu Sarmento, Leonardo Antunes Orenstein e Marco Buffara de Almeida
**Orientador:** Prof. Igor Tona Peres

O problema é alocar e sequenciar a construção de 100 poços marítimos em 13 sondas, respeitando elegibilidade (MPD), contratos, chegada de kits e ANMs, precedência entre poços (120 dias) e capacidade das frentes de completação.

## Conteúdo (pasta `codigo/`)

| Arquivo | O que faz |
|---|---|
| `dados.py` | Lê a planilha do estudo de caso e faz o pré-processamento (datas, durações por sonda, data limite efetiva, kits por poço) |
| `limite.py` | **E0**: atraso mínimo de cada poço, sem conflito entre poços pelas sondas |
| `heuristica.py` | **E1**: heurística gulosa por data limite efetiva |
| `modelo.py` | **E2 / E3**: modelo de máquinas paralelas em programação por restrições (CP-SAT, OR-Tools) |
| `roteirizacao.py` | **E4**: prova de conceito por roteirização (VRP com janelas de tempo, OR-Tools Routing) + decodificador |
| `verificar.py` | Verificador independente das restrições e cálculo das métricas |
| `rodar.py`, `rodar2.py`, `rodar_aloc.py` | Executam o modelo e salvam as soluções |
| `figuras.py` | Gera os gráficos de `fig/` |
| `sol_*.json` | Soluções usadas no relatório da Sprint 3 |

Detalhes de execução em [`codigo/LEIAME.md`](codigo/LEIAME.md).

## Como rodar

```
pip install pandas openpyxl ortools matplotlib
cd codigo
python limite.py                         # E0
python heuristica.py                     # E1
python rodar.py brando 450 sol_brando    # E2
python rodar.py duro 450 sol_duro        # E3
python roteirizacao.py 300               # E4
```

A planilha do estudo de caso (`Estudo_de_caso_-_cronograma_de_sondas_1.xlsx`) é material do Instituto Tecgraf e **não está no repositório**. Para rodar, coloque-a na pasta `codigo/`.

O CP-SAT é paralelo e tem limite de tempo: rodar de novo pode dar soluções um pouco diferentes. Os números do relatório vêm dos arquivos `sol_*.json` desta pasta, conferidos com `verificar.py` (0 violações).
