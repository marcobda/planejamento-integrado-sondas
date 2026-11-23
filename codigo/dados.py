"""Pré-processamento da planilha do estudo de caso (Tecgraf) para o modelo base.

Unidade de tempo: dia. Dia 0 = 01/01/2030 (início dos primeiros contratos).
Custos em mil US$.
"""
import pandas as pd

ARQ = 'Estudo_de_caso_-_cronograma_de_sondas_1.xlsx'  # planilha do Tecgraf na mesma pasta
T0 = pd.Timestamp('2030-01-01')


def dia(ts):
    return int((pd.Timestamp(ts) - T0).days)


def carregar():
    P = pd.read_excel(ARQ, sheet_name='POÇOS', header=5).dropna(subset=['Poço'])
    c = list(P.columns)
    P = P.rename(columns={c[0]: 'poco', c[1]: 'proj', c[2]: 'funcao', c[3]: 'fases', c[4]: 'thd',
                          c[5]: 'bhd', c[6]: 'cinf', c[7]: 'csup', c[8]: 'frente', c[9]: 'tipo',
                          c[10]: 'mpd', c[11]: 'dl', c[12]: 'pred'})
    P['poco'] = P['poco'].astype(int)
    P['pred'] = pd.Series([int(v) if pd.notna(v) else None for v in P['pred']], index=P.index, dtype=object)
    P['perf'] = P['thd'] + P['bhd']
    P['dl_d'] = P['dl'].apply(dia)

    S = pd.read_excel(ARQ, sheet_name='SONDAS').dropna(subset=['Sonda']).iloc[:13, :7]
    S.columns = ['sonda', 'mpd', 'fp', 'fc', 'ini', 'fim', 'tar']
    S['sonda'] = S['sonda'].astype(int)
    S['ini_d'] = S['ini'].apply(dia)
    S['fim_d'] = S['fim'].apply(dia)

    M = pd.read_excel(ARQ, sheet_name='MATERIAIS', header=None)

    def fila(ci):
        return [max(0, dia(v)) for v in M.iloc[5:, ci].tolist() if hasattr(v, 'year') and not pd.isna(v)]

    filas = {
        ('perf', 4): fila(2), ('perf', 5): fila(3),
        ('injetor', 1, 'int'): fila(5), ('injetor', 2, 'inf'): fila(6), ('injetor', 2, 'sup'): fila(7),
        ('produtor', 1, 'int'): fila(8), ('produtor', 2, 'inf'): fila(9), ('produtor', 2, 'sup'): fila(10),
        ('anm', 1): fila(11), ('anm', 2): fila(12), ('anm', 3): fila(13),
    }

    # Premissa de pré-processamento: o n-ésimo kit de cada fila vai para o n-ésimo poço
    # daquela categoria, em ordem de data limite (desempate pelo número do poço).
    # Data limite efetiva (propagada dos sucessores): o predecessor precisa terminar a
    # completação inferior 120 dias antes do início do sucessor (premissa 1).
    tot = dict(zip(P['poco'], P['perf'] + P['cinf'] + P['csup']))
    csup = dict(zip(P['poco'], P['csup']))
    dle = dict(zip(P['poco'], P['dl_d']))
    suc = {}
    for p, q in zip(P['poco'], P['pred']):
        if q is not None:
            suc.setdefault(q, []).append(p)
    mudou = True
    while mudou:
        mudou = False
        for q, ks in suc.items():
            v = min([dle[q]] + [dle[k] - tot[k] - 120 + csup[q] for k in ks])
            if v < dle[q]:
                dle[q] = v; mudou = True
    P['dl_ef'] = P['poco'].map(dle)
    P = P.sort_values(['dl_ef', 'poco']).reset_index(drop=True)
    rel = {p: {} for p in P['poco']}

    def atribuir(mask, chave, campo):
        q = filas[chave]
        pocos = P[mask]['poco'].tolist()
        assert len(q) >= len(pocos), (chave, len(q), len(pocos))
        for k, p in enumerate(pocos):
            rel[p][campo] = q[k]

    for f in (4, 5):
        atribuir(P['fases'] == f, ('perf', f), 'r_perf')
    for fn in ('injetor', 'produtor'):
        atribuir((P['funcao'] == fn) & (P['tipo'] == 1), (fn, 1, 'int'), 'r_cinf')
        atribuir((P['funcao'] == fn) & (P['tipo'] == 2), (fn, 2, 'inf'), 'r_cinf')
        atribuir((P['funcao'] == fn) & (P['tipo'] == 2), (fn, 2, 'sup'), 'r_csup')
    for fr in (1, 2, 3):
        atribuir(P['frente'] == fr, ('anm', fr), 'r_anm')

    for p in rel:
        rel[p].setdefault('r_csup', 0)
    P = P.sort_values('poco').reset_index(drop=True)
    for campo in ('r_perf', 'r_cinf', 'r_csup', 'r_anm'):
        P[campo] = P['poco'].map(lambda p: rel[p][campo])
    return P, S, filas


def duracoes(w, s):
    """Durações (dias) do poço w na sonda s, aplicando os fatores de tempo."""
    p = int(round(w.perf * s.fp))
    i = int(round(w.cinf * s.fc))
    u = int(round(w.csup * s.fc))
    return p, i, u


def elegivel(w, s):
    # Premissa 10: só a perfuração do reservatório exige MPD; poços já perfurados (premissa 9) não.
    if w.mpd == 'S' and w.perf > 0:
        return s.mpd == 'sim'
    return True


def trecho_frente(w, p, i, u):
    """(início relativo, duração) do trecho que usa frente de completação e exige a ANM.
    Tipo 1: completação inteira. Tipo 2: completação superior (premissa 5)."""
    if w.tipo == 1:
        return p, i
    return p + i, u


if __name__ == '__main__':
    P, S, filas = carregar()
    print(P[['poco', 'perf', 'cinf', 'csup', 'tipo', 'frente', 'dl_d', 'r_perf', 'r_cinf', 'r_csup', 'r_anm']].head(12))
    print(S)
