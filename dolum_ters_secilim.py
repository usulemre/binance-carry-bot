"""Madde 213: GTX DOLMAYAN emirlerde piyasa emrine dusmek KARLI mi?

Dolmayan emir rastgele degil: fiyat pasif limitten UZAKLASTIGI icin
dolmuyor (ters secilim). O yuzden "gecikme maliyeti" genel ortalamayla
(GEC taramasi: 4 saatte 1,1 puan) olculemez - KOSULLU olcmek gerekir.

Yontem: her secilen bacak icin pasif limit = referans fiyat -/+ 5bp.
Bar icinde LOW/HIGH limite dokunduysa DOLDU (maker). Dokunmadiysa
DOLMADI; iki secenek karsilastirilir:
  (a) PIYASA: bar KAPANISINDAN gir (+3bp taker primi)
  (b) BEKLE : bir sonraki barda gir (limit yine 5bp pasif; dolmazsa
              o barin kapanisi alinir - yani beklemenin en kotu hali)

4 SAATLIK BAR SINIRI: bot 6 dakika sonra piyasaya dusuyor, bu olcum
4 SAAT dolmayanlari aliyor. Yani buradaki ters secilim, gercekte
olandan DAHA SERT. Beklemek burada kazaniyorsa, 6 dakikada da kazanir.
"""
import sys; sys.path.insert(0,'/tmp')
from g import *
import numpy as np, pickle
S = pickle.load(open('/tmp/sk_bar48.pkl','rb')).reindex(index=C.index, columns=C.columns).values
OFS = 0.0005      # LIMIT_OFSET
TAKER_PRIM = 0.0003   # 5bp taker - 2bp maker
REBB, NDILIM, GROSS, n = 30, 15, 3.0, 6
adim = REBB // NDILIM

dolmayan = 0; toplam = 0
pi_fiyat, bek_fiyat = [], []
for i in range(1200, len(C) - 3, adim):
    g = np.isfinite(S[i]) & np.isfinite(cv[i]) & U[i]
    ix = np.flatnonzero(g); nn = min(n, len(ix)//2)
    if nn < 4: continue
    sc = rk(S[i][ix]); a = pd.Series(A[i][ix])
    if a.notna().sum() >= 0.5*len(ix):
        sc = 0.8*sc + 0.2*(-a).rank(pct=True).fillna(0.5).values
    o = np.argsort(sc)
    for taraf, sec in ((+1, ix[o[:nn]]), (-1, ix[o[-nn:]])):
        for j in sec:
            ref = cv[i, j]
            if not np.isfinite(ref) or ref <= 0: continue
            # bar i+1'de dolum denemesi
            hi, lo = HV[i+1, j], LV[i+1, j]
            kap = cv[i+1, j]
            if not (np.isfinite(hi) and np.isfinite(lo) and np.isfinite(kap)): continue
            toplam += 1
            if taraf > 0:      # LONG -> pasif ALIS limiti referansin ALTINDA
                limit = ref * (1 - OFS)
                doldu = lo <= limit
            else:              # SHORT -> pasif SATIS limiti referansin USTUNDE
                limit = ref * (1 + OFS)
                doldu = hi >= limit
            if doldu:
                continue
            dolmayan += 1
            # (a) PIYASA: bar i+1 kapanisindan, taker primi ile
            p_piyasa = kap * (1 + taraf * TAKER_PRIM)
            # (b) BEKLE: bar i+2'de yine pasif limit; dolmazsa kapanis
            hi2, lo2, kap2 = HV[i+2, j], LV[i+2, j], cv[i+2, j]
            if not (np.isfinite(hi2) and np.isfinite(lo2) and np.isfinite(kap2)):
                toplam -= 1; dolmayan -= 1; continue
            if taraf > 0:
                l2 = kap * (1 - OFS)
                p_bekle = l2 if lo2 <= l2 else kap2 * (1 + TAKER_PRIM)
            else:
                l2 = kap * (1 + OFS)
                p_bekle = l2 if hi2 >= l2 else kap2 * (1 - TAKER_PRIM)
            # giris fiyatinin KOTULUGU: long icin yuksek kotu, short icin dusuk kotu
            pi_fiyat.append(taraf * (p_piyasa / ref - 1))
            bek_fiyat.append(taraf * (p_bekle / ref - 1))

pi = np.array(pi_fiyat); bk = np.array(bek_fiyat)
print(f"{toplam} bacak-girisi, {dolmayan} tanesi 4 SAATTE DOLMADI "
      f"(%{100*dolmayan/max(1,toplam):.1f})")
print(f"\nDOLMAYANLARDA giris fiyatinin referanstan sapmasi (+ = KOTU):")
print(f"  PIYASA  : ort %{pi.mean()*100:+.4f}   medyan %{np.median(pi)*100:+.4f}")
print(f"  BEKLE   : ort %{bk.mean()*100:+.4f}   medyan %{np.median(bk)*100:+.4f}")
d = pi - bk
print(f"  FARK (piyasa - bekle): ort %{d.mean()*100:+.4f}  "
      f"medyan %{np.median(d)*100:+.4f}")
print(f"  beklemek daha iyi olan oran: %{100*np.mean(d>0):.1f}")
# yillik etki: dolmayan pay x devir x fark
DEVIR = 312.6
pay = dolmayan/max(1,toplam)
print(f"\nYILLIK ETKI (devir {DEVIR:.0f}x, dolmayan pay %{pay*100:.1f}):")
print(f"  piyasa yerine beklemek: %{-DEVIR*pay*d.mean()*100:+.2f} / yil")

# GUVEN ARALIGI: ortalama fat-tail tarafindan suruklenmis olabilir
import numpy as _np
se = d.std(ddof=1)/_np.sqrt(len(d))
print(f"\nORTALAMA FARKIN GUVENILIRLIGI (n={len(d)}):")
print(f"  ort %{d.mean()*100:+.4f}  std %{d.std()*100:.4f}  standart hata %{se*100:.4f}")
print(f"  t = {d.mean()/se:+.2f}   %95 aralik "
      f"[%{(d.mean()-1.96*se)*100:+.4f}, %{(d.mean()+1.96*se)*100:+.4f}]")
rng = _np.random.default_rng(3)
bs = _np.array([rng.choice(d, len(d), replace=True).mean() for _ in range(4000)])
print(f"  bootstrap %5-%95: [%{_np.percentile(bs,5)*100:+.4f}, "
      f"%{_np.percentile(bs,95)*100:+.4f}]  sifiri iceriyor mu: "
      f"{bool(_np.percentile(bs,5)<0<_np.percentile(bs,95))}")
DEVIR=312.6; pay=dolmayan/max(1,toplam)
print(f"\nDUZELTILMIS YILLIK ETKI (isaret duzeltildi):")
print(f"  piyasaya dusmek, beklemeye gore: %{DEVIR*pay*(-d.mean())*100:+.2f}/yil")
print(f"  %95 alt-ust: [%{DEVIR*pay*(-(d.mean()+1.96*se))*100:+.2f}, "
      f"%{DEVIR*pay*(-(d.mean()-1.96*se))*100:+.2f}]")
# gercek harmanlanmis komisyon
print(f"\nHARMANLANMIS KOMISYON:")
print(f"  dolmayan pay %{pay*100:.1f} -> harman = 2bp + %{pay*100:.1f} x 3bp "
      f"= {2 + pay*3:.3f} bp")
print(f"  backtest 2bp varsayiyor -> sapma {pay*3:.3f} bp = "
      f"%{pay*3*1.65:.2f} puan/yil")
