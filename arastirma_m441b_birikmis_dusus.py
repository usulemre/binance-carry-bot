# MADDE 441b: birikmis (3/6/12 sa) dusus tetikli kesme kurallari ve basit doz dusurmeyle kiyas.
import sys; sys.path.insert(0,'/home/claude/binance-carry-bot')
import arastirma_m441_saatlik_adaylar as Q, arastirma_m440_saatlik_kitap as S
import numpy as np, pandas as pd, itertools
def kural_kum(r, L, E, D_, N):
    c = pd.Series(np.log1p(r)).rolling(L).sum().values
    s = np.ones(len(r)); i = 0
    for i in np.where(c < np.log1p(E))[0]:
        s[i+1:i+1+N] = D_ if D_ < 1 else np.maximum(s[i+1:i+1+N], D_)
    m = np.abs(np.diff(np.r_[1.0, s])) * 0.001
    return s*r - m, s.mean()
for ad in ('KAYMA','T60'):
    for h in (0,1):
        r,_,_ = Q.kitap_saatlik(ad,h); x=r.values
        for L in (3,6,12):
            c=pd.Series(np.log1p(x)).rolling(L).sum().values
            for E in (-0.02,-0.03,-0.05):
                ix=np.where(c<np.log1p(E))[0]; ix=ix[ix+25<len(x)]
                if len(ix)==0: continue
                # tekrarlayan ardışık tetikleri seyrelt
                ix=ix[np.r_[True,np.diff(ix)>L]]
                f=lambda n: np.mean([np.prod(1+x[j+1:j+1+n])-1 for j in ix])*100
                print(f"{ad} h{h} son {L:2d} sa < {E*100:.0f}% ({len(ix):3d} olay): sonraki 3 sa {f(3):+.2f}  12 sa {f(12):+.2f}  24 sa {f(24):+.2f}")
        rows=[]
        IS=r.index<'2025-01-01'
        for L,E,D_,N in itertools.product((3,6,12),(-0.02,-0.03,-0.05),(0.0,0.5),(6,24)):
            row=dict(L=L,E=E*100,brut=D_,saat=N)
            for nm,m in (('IS',IS),('OOS',~IS),('TAM',np.ones(len(x),bool))):
                xx=x[m]; a,o=kural_kum(xx,L,E,D_,N); b=xx*o
                row[nm]=S.YIL(a)-S.YIL(b)
                if nm=='TAM': row['dd_fark']=S.DD(a)-S.DD(b)
            rows.append(row)
        T=pd.DataFrame(rows)
        print(f"  {ad} h{h} BIRIKMIS DUSUSTE KES: {len(T)} kuralin {int((T.TAM>0).sum())}'i pozitif; en iyi {T.TAM.max():+.2f}; dd'yi >1 puan iyilestiren {int((T.dd_fark>1).sum())}")
        print(T.sort_values('TAM',ascending=False).head(3).round(2).to_string(index=False))

print("\n=== dd iyilestiren kurallar vs basit doz dusurme (ayni dd icin getiri kaybi) ===")
for ad in ('KAYMA','T60'):
    for h in (0,1):
        r,_,_ = Q.kitap_saatlik(ad,h); x=r.values
        base_y, base_dd = S.YIL(x), S.DD(x)
        for L,E,D_,N in itertools.product((3,6,12),(-0.02,-0.03,-0.05),(0.0,0.5),(6,24)):
            a,o=kural_kum(x,L,E,D_,N)
            if S.DD(a)-base_dd>1:
                # aynı dd'yi sabit dozla elde etmenin maliyeti
                k=1.0
                for kk in np.arange(1.0,0.5,-0.005):
                    if S.DD(x*kk)>=S.DD(a): k=kk; break
                print(f"{ad} h{h} L{L} E{E*100:.0f} brut{D_} {N}sa: dd {base_dd:.1f}->{S.DD(a):.1f}, yillik {base_y:+.1f}->{S.YIL(a):+.1f} | ayni dd sabit doz {k:.3f}x -> yillik {S.YIL(x*k):+.1f}")
