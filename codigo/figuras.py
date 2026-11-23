import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mp
import pandas as pd
from verificar import verificar
from dados import T0
from limite import limite
from collections import Counter
NAVY='#1F4E6B'; OR='#E69E38'; TEAL='#2A8C82'; INK='#22313C'; GREY='#5F6B76'; GRID='#E6EBEF'; CONTR='#EEF2F5'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':14,'axes.edgecolor':'#C9D3DB','axes.labelcolor':INK,
    'xtick.color':INK,'ytick.color':INK,'axes.spines.top':False,'axes.spines.right':False})
def load(n):
    d=json.load(open(n+'.json')); s=d['sol'] if 'sol' in d else d
    return {int(k):(tuple(v) if v else None) for k,v in s.items()}
def save(n): plt.tight_layout(); plt.savefig('fig/'+n+'.png',dpi=220,facecolor='white'); plt.close()

# F1 causas do atraso inevitável
W,best=limite()
late={p:b['E']-W[p].dl_d for p,b in best.items() if b and b['E']>W[p].dl_d}
c=Counter(best[p]['causa'] for p in late)
nomes={'kit completação':'Kit de completação','predecessor (+120 d)':'Predecessor (+120 dias)','ANM':'Chegada da ANM','kit perfuração':'Kit de perfuração','contrato':'Início de contrato'}
it=sorted(c.items(),key=lambda x:x[1])
fig,ax=plt.subplots(figsize=(10,4.6))
b=ax.barh([nomes[k] for k,_ in it],[v for _,v in it],color=NAVY,height=0.6)
for r,(_,v) in zip(b,it): ax.text(v+0.3,r.get_y()+r.get_height()/2,f'{v} poços',va='center',fontsize=14,color=INK,fontweight='bold')
ax.set_xlim(0,22); ax.set_xticks([]); ax.spines['bottom'].set_visible(False); ax.spines['left'].set_visible(False); ax.tick_params(axis='y',length=0,labelsize=15)
save('f1_causas')

# F2 cenários (small multiples)
R={}
for n,lab in [('sol_gulosa','Heurística\ngulosa'),('sol_brando2','Modelo\n(prazo brando)'),('sol_duro','Modelo\n(prazo duro)')]:
    e,m,*_=verificar(load(n)); assert not e; R[lab]=m
kpis=[('Poços entregues',lambda m:m['alocados'],'{:.0f}'),('Poços atrasados',lambda m:m['n_atrasados'],'{:.0f}'),
      ('Atraso total (dias)',lambda m:m['atraso_total'],'{:,.0f}'),('Custo por poço (US$ mi)',lambda m:m['custo_mi']/m['alocados'],'{:.1f}')]
fig,axs=plt.subplots(1,4,figsize=(15,4.8))
cols=[GREY,NAVY,TEAL]
for ax,(t,f,fmt) in zip(axs,kpis):
    v=[f(m) for m in R.values()]
    bb=ax.bar(list(R.keys()),v,color=cols,width=0.62)
    for r,x in zip(bb,v): ax.text(r.get_x()+r.get_width()/2,x*1.02+max(v)*0.01,fmt.format(x).replace(',','X').replace('.',',').replace('X','.'),ha='center',fontsize=14,fontweight='bold',color=INK)
    ax.set_title(t,fontsize=15,fontweight='bold',color=INK,pad=10); ax.set_yticks([]); ax.spines['left'].set_visible(False)
    ax.set_ylim(0,max(v)*1.18 if max(v)>0 else 1); ax.tick_params(axis='x',labelsize=11.5,length=0)
save('f2_cenarios')

# F3 Gantt da solução principal
e,m,tab,uso,folga=verificar(load('sol_brando2'))
from dados import carregar
P,S,_=carregar()
fig,ax=plt.subplots(figsize=(15,7))
d=lambda t: T0+pd.Timedelta(days=int(t))
for k,s in enumerate(S.itertuples()):
    y=13-k
    ax.barh(y,(s.fim-s.ini).days,left=s.ini,height=0.82,color=CONTR,zorder=1)
    for p,t in tab.items():
        if t['r']!=s.sonda: continue
        col=TEAL if folga[p]>=0 else OR
        ax.barh(y,t['E']-t['S'],left=d(t['S']),height=0.62,color=col,edgecolor='white',lw=1.2,zorder=2)
        if t['E']-t['S']>=70: ax.text(d((t['S']+t['E'])/2),y,str(p),ha='center',va='center',fontsize=8.5,color='white',fontweight='bold',zorder=3)
ax.set_yticks(range(1,14)); ax.set_yticklabels([f'Sonda {int(s)}'+(' · MPD' if mm=='sim' else '') for s,mm in zip(S.sonda[::-1],S.mpd[::-1])],fontsize=12)
ax.xaxis.set_major_locator(mdates.YearLocator()); ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y')); ax.grid(axis='x',color=GRID,zorder=0); ax.tick_params(axis='y',length=0)
ax.legend(handles=[mp.Patch(color=TEAL,label=f'Poço no prazo ({m["alocados"]-m["n_atrasados"]})'),mp.Patch(color=OR,label=f'Poço atrasado ({m["n_atrasados"]})'),mp.Patch(color=CONTR,label='Janela de contrato')],
          loc='upper center',bbox_to_anchor=(0.5,1.09),ncol=3,frameon=False,fontsize=13)
ax.set_xlim(pd.Timestamp('2029-12-01'),pd.Timestamp('2036-05-01'))
save('f3_gantt')

# F4 distribuição da folga
fig,ax=plt.subplots(figsize=(11,4.8))
vals=sorted(folga.values()); import numpy as np
bins=np.arange(-650,751,50)
h,_=np.histogram(vals,bins)
for x0,hh in zip(bins[:-1],h):
    ax.bar(x0+25,hh,width=46,color=OR if x0<0 else TEAL)
ax.axvline(0,color=INK,lw=1.4); ax.text(-12,max(h)*0.97,'data limite',fontsize=12,color=INK,ha='right')
ax.set_xlabel('folga até a data limite (dias)'); ax.set_ylabel('poços'); ax.grid(axis='y',color=GRID); ax.set_axisbelow(True)
save('f4_folga')
print(json.dumps({k:{kk:(vv if not isinstance(vv,float) else round(vv,2)) for kk,vv in v.items() if kk!='nao_alocados'} for k,v in R.items()},indent=0,ensure_ascii=False))
print('folga min/max',min(vals),max(vals),'no prazo',sum(v>=0 for v in vals))
