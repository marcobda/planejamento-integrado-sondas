"""Heurística gulosa (experimento E1) — cópia comentada da função gulosa() de modelo.py.

Ideia: atender primeiro o poço com a data limite (efetiva) mais cedo e colocá-lo na sonda
onde ele TERMINA mais cedo. Decide um poço por vez e nunca volta atrás (por isso "gulosa").
"""
from modelo import dados_modelo, FOLGA_SUC, CAP_FRENTE


def gulosa():
    # W: poços, R: sondas, opc: pares (poço, sonda) viáveis com durações e data mínima de início (lb)
    W, R, opc = dados_modelo()

    livre = {r: R[r].ini_d for r in R}   # dia em que cada sonda fica livre (começa no início do contrato)
    frente = {1: [], 2: [], 3: []}       # completações já agendadas em cada frente: (início, fim)
    sol = {}                             # resultado: poço -> (sonda, dia de início) ou None
    feito = set()

    # 1) Ordena os poços pela data limite efetiva (EDD = earliest due date); empate pelo número do poço
    ordem = sorted(W, key=lambda p: (W[p].dl_ef, p))

    while ordem:
        # 2) Pega o primeiro poço da fila cujo predecessor já foi decidido (premissa 1)
        p = next(q for q in ordem if W[q].pred is None or W[q].pred in feito)
        ordem.remove(p)
        feito.add(p)
        w = W[p]
        melhor = None

        # 3) Testa o poço em cada sonda elegível
        for (pp, r), o in opc.items():
            if pp != p:
                continue

            # início = o mais tarde entre: sonda livre e materiais/contrato prontos (lb)
            t = max(o['lb'], livre[r])

            # regra dos 120 dias: sucessor só começa 120 dias após o fim da completação inferior do predecessor
            if w.pred is not None:
                if sol.get(w.pred) is None:      # predecessor ficou de fora -> sucessor também fica
                    continue
                rq, sq = sol[w.pred]
                oq = opc[(w.pred, rq)]
                t = max(t, sq + oq['dp'] + oq['di'] + FOLGA_SUC)

            # premissa 7: no máximo 2 completações ao mesmo tempo na mesma frente.
            # Se lotar, empurra o início até abrir vaga.
            if o['lf'] > 0:
                while True:
                    a, b = t + o['of'], t + o['of'] + o['lf']          # janela que o poço usaria na frente
                    pts = sorted({a} | {s0 for s0, e0 in frente[w.frente] if a < s0 < b})
                    conflito = None
                    for pt in pts:
                        ativos = [e0 for s0, e0 in frente[w.frente] if s0 <= pt < e0]
                        if len(ativos) >= CAP_FRENTE:
                            conflito = min(ativos)                    # primeira completação que libera vaga
                            break
                    if conflito is None:
                        break
                    t += conflito - pt

            # o poço inteiro tem que caber dentro do contrato da sonda
            if t + o['T'] > R[r].fim_d:
                continue

            # 4) Critério de escolha: termina mais cedo; empate -> diária mais barata
            chave = (t + o['T'], R[r].tar)
            if melhor is None or chave < melhor[0]:
                melhor = (chave, r, t)

        # 5) Nenhuma sonda serve -> poço não alocado
        if melhor is None:
            sol[p] = None
            continue

        # 6) Fixa a decisão: poço vai pro fim da fila da sonda escolhida
        _, r, t = melhor
        o = opc[(p, r)]
        sol[p] = (r, t)
        livre[r] = t + o['T']
        if o['lf'] > 0:
            frente[w.frente].append((t + o['of'], t + o['of'] + o['lf']))

    return sol


if __name__ == '__main__':
    from verificar import verificar
    sol = gulosa()
    erros, met, *_ = verificar(sol)
    print('violações:', len(erros))
    print(met)
    import json
    json.dump({str(k): v for k, v in sol.items()}, open('sol_gulosa.json', 'w'))
