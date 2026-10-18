#!/bin/sh
cd /home/claude/binance_bot/binance_bot
ko() {  # $1=DELIST_UFUK $2=TOL $3=etiket
  for k in 0 1; do
    env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 \
        UCELE=0.40 SK_DOSYA=/tmp/sk_bar48.pkl REB_GUN=5 FAZ=15 FAZ_KAY=$k \
        DELIST_UFUK=$1 TOL=$2 python3 g33.py ls 5 > /tmp/m247/$3_${k}.txt 2>&1
    cp /tmp/g19E_${k}.pkl /tmp/m247/E$3_${k}.pkl 2>/dev/null
  done
  echo "$3 bitti" >> /tmp/m247/DURUM
}
ko 30 0     D30
ko 15 0     D15
ko 60 0     D60
ko 0  0.50  T50
ko 0  0.25  T25
ko 30 0.50  D30T50
echo BITTI >> /tmp/m247/DURUM
