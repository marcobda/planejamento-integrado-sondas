"""Modelo base (Sprint 3): alocação e sequenciamento das sondas, poço contínuo (sem seriar).

Formulação em programação por restrições (CP-SAT / OR-Tools), com intervalos opcionais
por par poço-sonda, NoOverlap por sonda e Cumulative por frente de completação.
"""
import time
from ortools.sat.python import cp_model
from dados import carregar, duracoes, elegivel, trecho_frente

FOLGA_SUC = 120      # premissa 1 (dias)
CAP_FRENTE = 2       # premissa 7
PEN_ATRASO = 1500    # mil US$/dia de atraso (faturamento adiado de um poço, ~US$ 1,5 mi/dia)
PEN_NAO_ALOC = 2_000_000  # mil US$ por poço não alocado (dominante)


def dados_modelo():
    P, S, _ = carregar()
    W = {int(w.poco): w for w in P.itertuples()}
    R = {int(s.sonda): s for s in S.itertuples()}
    opc = {}  # (poco, sonda) -> dict de parâmetros
    for p, w in W.items():
        for r, s in R.items():
            if not elegivel(w, s):
                continue
            dp, di, du = duracoes(w, s)
            T = dp + di + du
            of, lf = trecho_frente(w, dp, di, du)
            lb = max(s.ini_d,
                     w.r_perf if w.perf > 0 else 0,
                     w.r_cinf - dp,
                     (w.r_csup - dp - di) if w.tipo == 2 else 0,
                     w.r_anm - of)
            if lb + T > s.fim_d:
                continue
            opc[(p, r)] = dict(dp=dp, di=di, du=du, T=T, of=of, lf=lf, lb=lb)
    return W, R, opc


def resolver(prazo='brando', limite=300, hint=None, workers=2, log=False, so_alocar=False):
    W, R, opc = dados_modelo()
    H = max(s.fim_d for s in R.values())
    m = cp_model.CpModel()
    S = {p: m.NewIntVar(0, H, f'S{p}') for p in W}
    x = {k: m.NewBoolVar(f'x{k}') for k in opc}
    u = {p: m.NewBoolVar(f'u{p}') for p in W}
    iv_sonda = {r: [] for r in R}
    iv_frente = {1: [], 2: [], 3: []}
    for (p, r), o in opc.items():
        iv_sonda[r].append(m.NewOptionalFixedSizeIntervalVar(S[p], o['T'], x[p, r], f'i{p}_{r}'))
        m.Add(S[p] >= o['lb']).OnlyEnforceIf(x[p, r])
        m.Add(S[p] + o['T'] <= R[r].fim_d).OnlyEnforceIf(x[p, r])
        if o['lf'] > 0:
            iv_frente[W[p].frente].append(
                m.NewOptionalFixedSizeIntervalVar(S[p] + o['of'], o['lf'], x[p, r], f'f{p}_{r}'))
    for p in W:
        m.Add(sum(x[k] for k in opc if k[0] == p) + u[p] == 1)
    for r in R:
        m.AddNoOverlap(iv_sonda[r])
    for fr, ivs in iv_frente.items():
        m.AddCumulative(ivs, [1] * len(ivs), CAP_FRENTE)

    def soma(p, campo):
        return sum(opc[k][campo] * x[k] for k in opc if k[0] == p)

    E = {p: S[p] + soma(p, 'T') for p in W}
    fim_inf = {p: S[p] + sum((opc[k]['dp'] + opc[k]['di']) * x[k] for k in opc if k[0] == p) for p in W}
    for p, w in W.items():
        if w.pred is not None:
            q = w.pred
            m.AddImplication(u[q], u[p])
            m.Add(S[p] >= fim_inf[q] + FOLGA_SUC).OnlyEnforceIf([u[p].Not(), u[q].Not()])

    atraso = {}
    for p, w in W.items():
        a = m.NewIntVar(0, H, f'a{p}')
        m.Add(a >= E[p] - w.dl_d).OnlyEnforceIf(u[p].Not())
        atraso[p] = a
        if prazo == 'duro':
            m.Add(E[p] <= w.dl_d).OnlyEnforceIf(u[p].Not())

    C = {}
    for r, s in R.items():
        C[r] = m.NewIntVar(s.ini_d, s.fim_d, f'C{r}')
        for (p, rr), o in opc.items():
            if rr == r:
                m.Add(C[r] >= S[p] + o['T']).OnlyEnforceIf(x[p, r])
    custo = sum(int(R[r].tar) * (C[r] - R[r].ini_d) for r in R)
    if so_alocar:
        m.Minimize(sum(u.values()))
    else:
        m.Minimize(custo + PEN_ATRASO * sum(atraso.values()) + PEN_NAO_ALOC * sum(u.values()))

    if hint:
        for p, v in hint.items():
            if v is None:
                m.AddHint(u[p], 1)
                continue
            r, st = v
            m.AddHint(S[p], st)
            m.AddHint(u[p], 0)
            for k in opc:
                if k[0] == p:
                    m.AddHint(x[k], 1 if k[1] == r else 0)

    sv = cp_model.CpSolver()
    sv.parameters.max_time_in_seconds = limite
    sv.parameters.num_search_workers = workers
    sv.parameters.log_search_progress = log
    t = time.time()
    st = sv.Solve(m)
    dt = time.time() - t
    sol = {}
    if st in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for p in W:
            sol[p] = None
            for k in opc:
                if k[0] == p and sv.Value(x[k]):
                    sol[p] = (k[1], sv.Value(S[p]))
    info = dict(status=sv.StatusName(st), obj=sv.ObjectiveValue() if sol else None,
                bound=sv.BestObjectiveBound(), tempo=dt,
                n_var=len(m.Proto().variables), n_res=len(m.Proto().constraints))
    return sol, info


def gulosa():
    """Heurística de referência: poços em ordem de data limite (EDD), cada um na sonda
    elegível que o termina mais cedo, sempre ao fim da fila da sonda."""
    W, R, opc = dados_modelo()
    livre = {r: R[r].ini_d for r in R}
    frente = {1: [], 2: [], 3: []}
    sol = {}
    ordem = sorted(W, key=lambda p: (W[p].dl_ef, p))
    feito = set()
    while ordem:
        p = next(q for q in ordem if W[q].pred is None or W[q].pred in feito)
        ordem.remove(p)
        feito.add(p)
        w = W[p]
        melhor = None
        for (pp, r), o in opc.items():
            if pp != p:
                continue
            t = max(o['lb'], livre[r])
            if w.pred is not None:
                if sol.get(w.pred) is None:
                    continue
                rq, sq = sol[w.pred]
                oq = opc[(w.pred, rq)]
                t = max(t, sq + oq['dp'] + oq['di'] + FOLGA_SUC)
            if o['lf'] > 0:
                while True:
                    a, b = t + o['of'], t + o['of'] + o['lf']
                    pts = sorted({a} | {s0 for s0, e0 in frente[w.frente] if a < s0 < b})
                    conflito = None
                    for pt in pts:
                        ativos = [e0 for s0, e0 in frente[w.frente] if s0 <= pt < e0]
                        if len(ativos) >= CAP_FRENTE:
                            conflito = min(ativos)
                            break
                    if conflito is None:
                        break
                    t += conflito - pt
            if t + o['T'] > R[r].fim_d:
                continue
            chave = (t + o['T'], R[r].tar)
            if melhor is None or chave < melhor[0]:
                melhor = (chave, r, t)
        if melhor is None:
            sol[p] = None
            continue
        _, r, t = melhor
        o = opc[(p, r)]
        sol[p] = (r, t)
        livre[r] = t + o['T']
        if o['lf'] > 0:
            frente[w.frente].append((t + o['of'], t + o['of'] + o['lf']))
    return sol
