#!/bin/sh
cd /home/claude/binance_bot/binance_bot
# 2^4 faktoriyel: TPL {0.40,0.50} x HAVUZ {3,4} x UCELE {0.40,0.60} x REZERV {0.20,0.30}
for tpl in 0.40 0.50; do
for hav in 3 4; do
for uce in 0.40 0.60; do
for rez in 0.20 0.30; do
  et="T${tpl}_H${hav}_U${uce}_R${rez}"
  [ -f /tmp/m242/E${et}_1.pkl ] && continue
  for k in 0 1; do
    env HAVUZ=$hav REZERV=$rez REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=$tpl TPS=0.20 \
        UCELE=$uce SK_DOSYA=/tmp/sk_bar48.pkl REB_GUN=5 FAZ=15 FAZ_KAY=$k \
        python3 g33.py ls 5 > /tmp/m242/${et}_${k}.txt 2>&1
    cp /tmp/g19E_${k}.pkl /tmp/m242/E${et}_${k}.pkl 2>/dev/null
  done
  echo "$et bitti" >> /tmp/m242/DURUM
done; done; done; done
echo BITTI >> /tmp/m242/DURUM
