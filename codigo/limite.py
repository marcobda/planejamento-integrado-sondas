"""Limite inferior de atraso por poço com capacidade infinita de sondas (sem conflito entre poços)."""
from modelo import dados_modelo, FOLGA_SUC

def limite():
    W, R, opc = dados_modelo()
    best = {}
    feito = set(); ordem = sorted(W, key=lambda p: (W[p].dl_ef, p))
    while len(feito) < len(W):
        for p in ordem:
            if p in feito: continue
            q = W[p].pred
            if q is not None and q not in feito: continue
            w = W[p]; cands = []
            for (pp, r), o in opc.items():
                if pp != p: continue
                causas = {'contrato': R[r].ini_d, 'kit perfuração': w.r_perf if w.perf > 0 else 0,
                          'kit completação': max(w.r_cinf - o['dp'], (w.r_csup - o['dp'] - o['di']) if w.tipo == 2 else 0),
                          'ANM': w.r_anm - o['of']}
                if q is not None:
                    causas['predecessor (+120 d)'] = (best[q]['finf'] + FOLGA_SUC) if best[q] else 10**6
                t = max(causas.values()); causa = max(causas, key=causas.get)
                if t + o['T'] <= R[r].fim_d:
                    cands.append((t + o['T'], t + o['dp'] + o['di'], causa, r))
            if cands:
                c = min(cands)
                best[p] = dict(E=c[0], finf=min(x[1] for x in cands), causa=c[2], r=c[3])
            else:
                best[p] = None
            feito.add(p)
    return W, best

if __name__ == '__main__':
    from collections import Counter
    W, best = limite()
    late = {p: b['E'] - W[p].dl_d for p, b in best.items() if b and b['E'] > W[p].dl_d}
    print('inviáveis:', [p for p, b in best.items() if b is None])
    print('atrasados inevitáveis:', len(late), 'soma', sum(late.values()))
    print(Counter(best[p]['causa'] for p in late))
