#!/bin/sh
cd /home/claude/binance_bot/binance_bot
# BAGIMSIZ ESDEGER PLASEBO: %5 rastgele sembol dusurme, farkli tohumlar
for t in 1 2 3 4 5 6 7 8; do
  for k in 0 1; do
    env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 \
        UCELE=0.40 SK_DOSYA=/tmp/sk_bar48.pkl REB_GUN=5 FAZ=15 FAZ_KAY=$k \
        SEMBOL_DUS=0.05 DTOHUM=$t python3 g33.py ls 5 > /tmp/m248/D${t}_${k}.txt 2>&1
    cp /tmp/g19E_${k}.pkl /tmp/m248/ED${t}_${k}.pkl 2>/dev/null
  done
  echo "tohum $t bitti" >> /tmp/m248/DURUM2
done
echo BITTI2 >> /tmp/m248/DURUM2
