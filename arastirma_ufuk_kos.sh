#!/bin/sh
cd /home/claude/binance_bot/binance_bot
for g in 5 2 3 10 15; do
  for k in 0 1; do
    env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 \
        UCELE=0.40 SK_DOSYA=/tmp/sk_bar48.pkl REB_GUN=$g FAZ=15 FAZ_KAY=$k \
        python3 g33.py ls 5 > /tmp/m239/U${g}_${k}.txt 2>&1
    cp /tmp/g19E_${k}.pkl /tmp/m239/EU${g}_${k}.pkl 2>/dev/null
  done
  echo "ufuk $g bitti" >> /tmp/m239/DURUM
done
echo BITTI >> /tmp/m239/DURUM
