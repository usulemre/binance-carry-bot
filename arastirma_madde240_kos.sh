#!/bin/sh
cd /home/claude/binance_bot/binance_bot
# A) FUNDING SINYAL PENCERESI (madde 209'dan beri yeniden acilmadi)
for w in 08 24 36 48 60 72; do
  for k in 0 1; do
    env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 \
        UCELE=0.40 SK_DOSYA=/tmp/sk_bar${w}.pkl REB_GUN=5 FAZ=15 FAZ_KAY=$k \
        python3 g33.py ls 5 > /tmp/m240/W${w}_${k}.txt 2>&1
    cp /tmp/g19E_${k}.pkl /tmp/m240/EW${w}_${k}.pkl 2>/dev/null
  done
  echo "pencere $w bitti" >> /tmp/m240/DURUM
done
# B) FIRSAT REZERVI ESIGI (gunluk %)
for e in 0.010 0.012 0.018 0.025; do
  for k in 0 1; do
    env HAVUZ=3 REZERV=0.20 REZ_ESIK=$e KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 \
        UCELE=0.40 SK_DOSYA=/tmp/sk_bar48.pkl REB_GUN=5 FAZ=15 FAZ_KAY=$k \
        python3 g33.py ls 5 > /tmp/m240/R${e}_${k}.txt 2>&1
    cp /tmp/g19E_${k}.pkl /tmp/m240/ER${e}_${k}.pkl 2>/dev/null
  done
  echo "esik $e bitti" >> /tmp/m240/DURUM
done
echo BITTI >> /tmp/m240/DURUM
