#!/bin/sh
cd /home/claude/binance_bot/binance_bot
while ! grep -q BITTI /tmp/m244/DURUM 2>/dev/null; do sleep 20; done
for s in sk_prim_b01 sk_prim_b06 sk_prim_b12 sk_prim_b18 sk_prim_b30 \
         sk_harman_p25 sk_harman_p50 sk_harman_p75; do
  for k in 0 1; do
    env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 \
        UCELE=0.40 SK_DOSYA=/tmp/${s}.pkl REB_GUN=5 FAZ=15 FAZ_KAY=$k \
        python3 g33.py ls 5 > /tmp/m244/${s}_${k}.txt 2>&1
    cp /tmp/g19E_${k}.pkl /tmp/m244/E${s}_${k}.pkl 2>/dev/null
  done
  echo "$s bitti" >> /tmp/m244/DURUM2
done
echo BITTI2 >> /tmp/m244/DURUM2
