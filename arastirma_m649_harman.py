import sys,os; sys.path.insert(0,"/home/claude/binance-carry-bot")
exec(open("arastirma_m649_dogrula.py").read().split("print(U.KOM)")[0])
rk=np.log(TOP).replace([np.inf,-np.inf],np.nan).where(uy).rank(axis=1,pct=True)
g,gl,gs,_=kurq(rk,-1,2,0.2)
# piyasa (evren eşit ağırlık) — long bacağın betası mı?
EW=(r1.where(uy).mean(axis=1)).shift(0); EW=EW[EW.index>=BAS]
print("bacak korelasyonu piyasa ile: long", round(gl.corr(EW*0.5),2), "short", round(gs.corr(EW*-0.5),2), "kitap", round(g.corr(EW),2))
# en iyi günleri at
for k in (0,5,10,20):
    x=g.drop(g.nlargest(k).index); print(f"en iyi {k} gün atılınca yıllık {yil(x):+.1f} Sh {sh(x):.2f}")
print("2026 aylar:", g[g.index>="2026"].groupby(g[g.index>="2026"].index.month).apply(lambda x:(1+x).prod()*100-100).round(0).to_dict())
# carry ile harman (2022-06+), aynı maks düşüşte
c=carry[carry.index>=BAS]; ix=c.index.intersection(g.index); c=c.loc[ix]; b=g.loc[ix]
def m(d):
    e=(1+d).cumprod(); return yil(d), ((e/e.cummax())-1).min()*100, d.min()*100, sh(d)
base=m(c); print(f"carry (T7K+KS 1x) 2022-06+: yıl {base[0]:+.1f} dd {base[1]:.1f} en kötü {base[2]:.2f} Sh {base[3]:.2f}")
for a in (0.1,0.2,0.3):
    d=c*(1-a)+b*a; o=m(d)
    # aynı dd ve en kötü güne ölçekle
    k=1.0
    for kk in np.arange(1.0,3.0,0.01):
        oo=m(d*kk)
        if oo[1]<base[1] or oo[2]<base[2]: break
        k=kk
    print(f"harman %{int(a*100)} kitap: Sh {o[3]:.2f} yıl {o[0]:+.1f} dd {o[1]:.1f} | aynı dd/en kötü günde ×{k:.2f} → yıl {m(d*k)[0]:+.1f}")
