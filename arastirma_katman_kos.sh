#!/bin/sh
cd /home/claude/binance_bot/binance_bot
ko() {  # $1=HAVUZ $2=AKIS $3=UCELE $4=REZERV $5=TP $6=TPL $7=TPS $8=etiket
  for k in 0 1; do
    env HAVUZ=$1 AKIS=$2 UCELE=$3 REZERV=$4 REZ_ESIK=0.015 KAP=0.05 \
        TP=$5 TPL=$6 TPS=$7 SK_DOSYA=/tmp/sk_bar48.pkl REB_GUN=5 FAZ=15 \
        FAZ_KAY=$k python3 g33.py ls 5 > /tmp/m238b/$8_${k}.txt 2>&1
    cp /tmp/g19E_${k}.pkl /tmp/m238b/E$8_${k}.pkl 2>/dev/null
  done
}
#   havuz akis ucele rezerv tp   tpl  tps  etiket
ko  1     0    0     0      0    -1   -1   A_CIPLAK
ko  3     0    0     0      0    -1   -1   B_HAVUZ
ko  3     0.20 0     0      0    -1   -1   C_AKIS
ko  3     0.20 0.40  0      0    -1   -1   D_UCELE
ko  3     0.20 0.40  0.20   0    -1   -1   E_REZERV
ko  3     0.20 0.40  0.20   0.4  0.40 0.20 F_TAM
echo BITTI > /tmp/m238b/DURUM
