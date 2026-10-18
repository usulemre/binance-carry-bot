#!/bin/sh
cd /home/claude/binance_bot/binance_bot
for k in 0 1; do
  env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 \
      UCELE=0.40 SK_DOSYA=/tmp/sk_reversal.pkl REB_GUN=5 FAZ=15 FAZ_KAY=$k \
      python3 g33.py ls 5 > /tmp/m241/REV_${k}.txt 2>&1
  cp /tmp/g19E_${k}.pkl /tmp/m241/EREV_${k}.pkl 2>/dev/null
done
echo "reversal bitti" >> /tmp/m241/DURUM
# UCELE kapali geri donus: uc hareket elemesi geri donusu BUDUYOR mu?
for k in 0 1; do
  env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 \
      UCELE=0 SK_DOSYA=/tmp/sk_reversal.pkl REB_GUN=5 FAZ=15 FAZ_KAY=$k \
      python3 g33.py ls 5 > /tmp/m241/REVU_${k}.txt 2>&1
  cp /tmp/g19E_${k}.pkl /tmp/m241/EREVU_${k}.pkl 2>/dev/null
done
echo BITTI >> /tmp/m241/DURUM
