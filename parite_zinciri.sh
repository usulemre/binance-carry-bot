#!/bin/bash
# MADDE 335: metrik indirmesi bitince paneli kur, PARITE kos, tutarsa
# referans_getiri.csv uret. Her adim gunluge yazar; hicbir adim
# otekinin basarisini VARSAYMAZ.
cd /home/claude/binance_bot/binance_bot
L=/tmp/parite_zinciri.log
: > $L
echo "=== 1) metrik indirmesinin bitmesi bekleniyor" >> $L
while :; do
  n=$(ls data_metrik 2>/dev/null | wc -l)
  p=$(ps -eo args | grep -c '[s]urdurulebilir')
  echo "   $(date +%H:%M:%S) dosya $n/587 surec $p" >> $L
  [ "$n" -ge 587 ] && break
  [ "$p" -eq 0 ] && break
  sleep 120
done
echo "=== 2) metrik paneli kuruluyor" >> $L
python3 indir_metrik_surdurulebilir.py panel >> $L 2>&1
echo "   cikis $?" >> $L
echo "=== 3) PARITE KOSUSU (hedef: tam +112,3% dd -14,5)" >> $L
env HAVUZ=3 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 UCELE=0.40 \
    REB_GUN=5 FAZ=15 REZERV=0.20 SK_DOSYA=/tmp/sk_bar48.pkl \
    timeout 3000 python3 g33.py ls 5 >> $L 2>&1
echo "   cikis $?" >> $L
echo "=== 4) parite degerlendirmesi + referans serisi" >> $L
python3 - >> $L 2>&1 <<'PY'
import pickle, numpy as np, pandas as pd, carry_denetim as D
E = pickle.load(open("/tmp/g19E_0.pkl", "rb"))
o = D.ozet(E / E.iloc[0])
print("  OLCULEN : %+.2f%%  Sh %.3f  dd %.2f" % (o["yillik"], o["sharpe"], o["maxdd"]))
print("  HEDEF   : +112,27%%  Sh ~3,10  dd -14,54")
tutar = abs(o["yillik"] - 112.27) < 0.6 and abs(o["maxdd"] + 14.54) < 0.6
print("  PARITE  : %s" % ("GECTI" if tutar else "TUTMADI"))
if tutar:
    r = E.pct_change().dropna()
    g = (1 + r).groupby(r.index.date).prod() - 1
    g.index = pd.DatetimeIndex(g.index); g.name = "getiri"
    g.to_csv("referans_getiri.csv", index_label="tarih", float_format="%.17g")
    dd = ((1+g).cumprod()/(1+g).cumprod().cummax()-1).min()*100
    print("  referans_getiri.csv yazildi: %d gun, gunluk dusus %.2f" % (len(g), dd))
else:
    print("  referans_getiri.csv YAZILMADI - dogrulanmamis zemin uzerine olcum yapilmaz")
PY
echo "[ZINCIR-BITTI]" >> $L
