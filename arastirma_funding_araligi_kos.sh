#!/bin/sh
cd /home/claude/binance_bot/binance_bot
for s in sk_ode48 sk_ode24 sk_ode72 sk_ode120; do
  for k in 0 1; do
    env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 \
        UCELE=0.40 SK_DOSYA=/tmp/${s}.pkl REB_GUN=5 FAZ=15 FAZ_KAY=$k \
        python3 g33.py ls 5 > /tmp/m246/${s}_${k}.txt 2>&1
    cp /tmp/g19E_${k}.pkl /tmp/m246/E${s}_${k}.pkl 2>/dev/null
  done
  echo "$s bitti" >> /tmp/m246/DURUM
done
echo BITTI >> /tmp/m246/DURUM
