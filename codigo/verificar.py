"""Checagem independente de uma solução e cálculo das métricas de avaliação."""
from dados import carregar, duracoes, elegivel, trecho_frente

FOLGA_SUC, CAP_FRENTE = 120, 2


def verificar(sol):
    P, S, _ = carregar()
    W = {int(w.poco): w for w in P.itertuples()}
    R = {int(s.sonda): s for s in S.itertuples()}
    erros, tab = [], {}
    for p, v in sol.items():
        if v is None:
            continue
        r, st = v
        w, s = W[p], R[r]
        dp, di, du = duracoes(w, s)
        of, lf = trecho_frente(w, dp, di, du)
        tab[p] = dict(r=r, S=st, E=st + dp + di + du, fim_inf=st + dp + di, dp=dp, di=di, du=du, of=of, lf=lf)
        if not elegivel(w, s): erros.append(f'{p}: sonda {r} sem MPD')
        if st < s.ini_d or st + dp + di + du > s.fim_d: erros.append(f'{p}: fora do contrato da sonda {r}')
        if w.perf > 0 and st < w.r_perf: erros.append(f'{p}: perfuração antes do kit')
        if st + dp < w.r_cinf: erros.append(f'{p}: completação antes do kit')
        if w.tipo == 2 and st + dp + di < w.r_csup: erros.append(f'{p}: compl. superior antes do kit')
        if st + of < w.r_anm: erros.append(f'{p}: completação antes da ANM')
    for r in R:
        ivs = sorted((t['S'], t['E'], p) for p, t in tab.items() if t['r'] == r)
        for (a1, b1, p1), (a2, b2, p2) in zip(ivs, ivs[1:]):
            if a2 < b1: erros.append(f'sonda {r}: {p1} e {p2} sobrepostos')
    for fr in (1, 2, 3):
        ivs = [(t['S'] + t['of'], t['S'] + t['of'] + t['lf']) for p, t in tab.items() if W[p].frente == fr and t['lf'] > 0]
        for a, _ in ivs:
            if sum(1 for a2, b2 in ivs if a2 <= a < b2) > CAP_FRENTE: erros.append(f'frente {fr}: >2 em {a}')
    for p, w in W.items():
        if w.pred is not None and p in tab:
            if w.pred not in tab: erros.append(f'{p}: predecessor {w.pred} não alocado')
            elif tab[p]['S'] < tab[w.pred]['fim_inf'] + FOLGA_SUC: erros.append(f'{p}: folga de 120 d com {w.pred}')

    # métricas
    custo, prod, pago, uso = 0, 0, 0, {}
    for r, s in R.items():
        js = [t for t in tab.values() if t['r'] == r]
        if not js:
            uso[r] = dict(C=None, pago=0, prod=0, custo=0, n=0); continue
        C = max(t['E'] for t in js)
        pr = sum(t['E'] - t['S'] for t in js)
        uso[r] = dict(C=C, pago=C - s.ini_d, prod=pr, custo=s.tar * (C - s.ini_d), n=len(js))
        custo += uso[r]['custo']; prod += pr; pago += C - s.ini_d
    folga = {p: W[p].dl_d - t['E'] for p, t in tab.items()}
    atrasados = [p for p, f in folga.items() if f < 0]
    met = dict(alocados=len(tab), nao_alocados=sorted(p for p, v in sol.items() if v is None),
               custo_mi=custo / 1000, dias_pagos=pago, dias_prod=prod, ocioso=pago - prod,
               utilizacao=prod / pago if pago else 0,
               n_atrasados=len(atrasados), atraso_total=-sum(folga[p] for p in atrasados),
               atraso_max=-min(folga.values()) if atrasados else 0,
               folga_media=sum(folga.values()) / len(folga) if folga else 0,
               folga_mediana=sorted(folga.values())[len(folga) // 2] if folga else 0,
               sondas_usadas=sum(1 for v in uso.values() if v['n']))
    return erros, met, tab, uso, folga
