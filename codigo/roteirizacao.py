"""Prova de conceito: o problema das sondas visto como roteirização (VRP com janelas de tempo).

Analogia
  veículo  = sonda (sai no início do contrato e precisa voltar até o fim do contrato)
  cliente  = poço (tempo de atendimento = duração do poço naquela sonda)
  rota     = sequência de poços que a sonda constrói
  janela   = o poço não pode começar antes dos kits/ANM chegarem;
             a data limite entra como janela "mole" (penalidade por dia de atraso)
  custo    = diária da sonda × dias pagos (span da rota) + penalidades

Etapa 1 – OR-Tools Routing escolhe a sonda e a ORDEM dos poços de cada sonda.
Etapa 2 – um "decodificador" recalcula as datas exatas de cada rota com as regras completas
          (durações por sonda, kits, ANM, 120 dias, frente com no máx. 2 completações)
          e o verificar.py confere a solução, igual aos experimentos E1–E3.

Uso: python roteirizacao.py [segundos]
"""
import json, sys, time
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from modelo import dados_modelo, FOLGA_SUC, CAP_FRENTE, PEN_ATRASO, PEN_NAO_ALOC
from verificar import verificar


def roteirizar(limite=120):
    W, R, opc = dados_modelo()
    pocos = sorted(W)
    sondas = sorted(R)
    no = {p: k + 1 for k, p in enumerate(pocos)}        # nó 0 = "depósito" fictício
    H = max(s.fim_d for s in R.values())

    man = pywrapcp.RoutingIndexManager(len(pocos) + 1, len(sondas), 0)
    rt = pywrapcp.RoutingModel(man)

    # tempo de "atendimento" do poço depende da sonda (fatores de tempo)
    cbs = []
    for v, r in enumerate(sondas):
        def transito(i, j, r=r):
            a = man.IndexToNode(i)
            if a == 0:
                return 0
            o = opc.get((pocos[a - 1], r))
            return o['T'] if o else 0
        cbs.append(rt.RegisterTransitCallback(transito))
    rt.AddDimensionWithVehicleTransits(cbs, H, H, False, 'Tempo')
    tempo = rt.GetDimensionOrDie('Tempo')

    for v, r in enumerate(sondas):
        s = R[r]
        tempo.CumulVar(rt.Start(v)).SetValue(int(s.ini_d))       # paga desde o início do contrato
        tempo.CumulVar(rt.End(v)).SetMax(int(s.fim_d))           # tem que terminar no contrato
        rt.SetFixedCostOfVehicle(0, v)
        tempo.SetSpanCostCoefficientForVehicle(int(s.tar), v)    # diária × dias pagos

    for p in pocos:
        idx = man.NodeToIndex(no[p])
        elig = [v for v, r in enumerate(sondas) if (p, r) in opc]
        rt.VehicleVar(idx).SetValues([-1] + elig)   # só sondas elegíveis (-1 = fora)
        # janela de início: o mais cedo possível entre as sondas elegíveis (kits, ANM, contrato)
        lb = min(opc[(p, sondas[v])]['lb'] for v in elig) if elig else 0
        tempo.CumulVar(idx).SetMin(int(lb))
        # data limite como janela mole: penaliza início depois de (data limite - duração)
        if elig:
            T = min(opc[(p, sondas[v])]['T'] for v in elig)
            tempo.SetCumulVarSoftUpperBound(idx, max(0, int(W[p].dl_d - T)), PEN_ATRASO)
        rt.AddDisjunction([idx], PEN_NAO_ALOC)                   # poço pode ficar de fora (penalidade)

    # regra dos 120 dias entre predecessor e sucessor (pode estar em sondas diferentes)
    sol = rt.solver()
    for p in pocos:
        q = W[p].pred
        if q is None:
            continue
        ip, iq = man.NodeToIndex(no[p]), man.NodeToIndex(no[q])
        dmin = min(o['dp'] + o['di'] for (pp, r), o in opc.items() if pp == q)
        sol.Add(rt.ActiveVar(ip) <= rt.ActiveVar(iq))
        sol.Add(tempo.CumulVar(ip) + H * (1 - rt.ActiveVar(ip)) >= tempo.CumulVar(iq) + dmin + FOLGA_SUC)

    prm = pywrapcp.DefaultRoutingSearchParameters()
    prm.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    prm.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    prm.time_limit.seconds = limite
    t0 = time.time()
    a = rt.SolveWithParameters(prm)
    dt = time.time() - t0
    if a is None:
        return None, dict(status='sem solução', tempo=dt)

    rotas = {}
    for v, r in enumerate(sondas):
        i, seq = rt.Start(v), []
        while not rt.IsEnd(i):
            n = man.IndexToNode(i)
            if n:
                seq.append(pocos[n - 1])
            i = a.Value(rt.NextVar(i))
        rotas[r] = seq
    return rotas, dict(status='ok', obj=a.ObjectiveValue(), tempo=round(dt, 1))


def decodificar(rotas):
    """Dá datas exatas a cada rota, respeitando todas as regras do modelo base.
    A cada passo olha o próximo poço da fila de cada sonda, calcula o início mais cedo
    possível (sonda livre, kits/ANM, 120 dias do predecessor, vaga na frente) e agenda
    o que começa primeiro. A ordem dentro de cada sonda é a da rota. Poço que não cabe
    no contrato, ou cujo predecessor ficou de fora, sai."""
    W, R, opc = dados_modelo()
    livre = {r: R[r].ini_d for r in R}
    frente = {1: [], 2: [], 3: []}
    sol = {p: None for p in W}
    fila = {r: list(seq) for r, seq in rotas.items()}
    decidido = set()

    def inicio(p, r):
        w, o = W[p], opc[(p, r)]
        t = max(o['lb'], livre[r])
        q = w.pred
        if q is not None:
            rq, sq = sol[q]; oq = opc[(q, rq)]
            t = max(t, sq + oq['dp'] + oq['di'] + FOLGA_SUC)
        if o['lf'] > 0:
            while True:
                a_, b_ = t + o['of'], t + o['of'] + o['lf']
                pts = sorted({a_} | {s0 for s0, e0 in frente[w.frente] if a_ < s0 < b_})
                conf = None
                for pt in pts:
                    at = [e0 for s0, e0 in frente[w.frente] if s0 <= pt < e0]
                    if len(at) >= CAP_FRENTE:
                        conf = min(at); break
                if conf is None:
                    break
                t += conf - pt
        return t

    while any(fila.values()):
        cand = []
        for r, f in fila.items():
            if not f:
                continue
            p, q = f[0], W[f[0]].pred
            if q is not None and q not in decidido:
                continue                                   # espera o predecessor ser decidido
            if q is not None and sol[q] is None:
                cand.append((-1, r, p)); continue          # predecessor ficou de fora -> sai
            cand.append((inicio(p, r), r, p))
        if not cand:                                       # travou (ciclo de espera): descarta uma cabeça
            r = next(r for r, f in fila.items() if f)
            decidido.add(fila[r].pop(0)); continue
        t, r, p = min(cand)
        fila[r].pop(0); decidido.add(p)
        o = opc[(p, r)]
        if t < 0 or t + o['T'] > R[r].fim_d:
            continue
        sol[p] = (r, t)
        livre[r] = t + o['T']
        if o['lf'] > 0:
            frente[W[p].frente].append((t + o['of'], t + o['of'] + o['lf']))
    return sol


if __name__ == '__main__':
    lim = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    rotas, info = roteirizar(lim)
    print('roteirização:', info)
    if rotas:
        sol = decodificar(rotas)
        erros, met, *_ = verificar(sol)
        print('violações:', len(erros), erros[:5])
        print({k: met[k] for k in ('alocados', 'n_atrasados', 'atraso_total', 'custo_mi', 'utilizacao', 'ocioso', 'nao_alocados')})
        for r, seq in rotas.items():
            print(f'sonda {r:2d}:', ' → '.join(map(str, seq)))
        json.dump({'rotas': {str(k): v for k, v in rotas.items()}, 'sol': {str(k): v for k, v in sol.items()},
                   'info': info, 'met': met}, open('sol_vrp.json', 'w'), default=str)
