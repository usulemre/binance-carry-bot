#!/bin/sh
cd /home/claude/binance_bot/binance_bot
ko() {  # $1=BRUT_PRIM $2=ALT $3=UST $4=REF $5=PLASEBO $6=etiket
  for k in 0 1; do
    env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 \
        UCELE=0.40 SK_DOSYA=/tmp/sk_bar48.pkl REB_GUN=5 FAZ=15 FAZ_KAY=$k \
        BRUT_PRIM=$1 BRUT_ALT=$2 BRUT_UST=$3 BRUT_REF=$4 BRUT_PLASEBO=$5 \
        python3 g33.py ls 5 > /tmp/m239/$6_${k}.txt 2>&1
    cp /tmp/g19E_${k}.pkl /tmp/m239/E$6_${k}.pkl 2>/dev/null
  done
  echo "$6 bitti" >> /tmp/m239/DURUM2
}
#   e    alt  ust  ref  plasebo etiket
ko  1.0  0.3  1.5  180  0       P_e10
ko  0.5  0.3  1.5  180  0       P_e05
ko  1.5  0.3  1.5  180  0       P_e15
ko  1.0  0.3  1.5  90   0       P_ref90
ko  1.0  0.3  1.5  365  0       P_ref365
ko  1.0  0.5  1.5  180  0       P_alt05
ko  1.0  0.3  2.0  180  0       P_ust20
ko  1.0  0.3  1.5  180  1       P_PLASEBO_ters
ko  1.0  0.3  1.5  180  2       P_PLASEBO_karis
# eksik ufuklari tamamla
env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 UCELE=0.40 \
    SK_DOSYA=/tmp/sk_bar48.pkl REB_GUN=10 FAZ=15 FAZ_KAY=0 python3 g33.py ls 5 > /tmp/m239/U10_0.txt 2>&1
cp /tmp/g19E_0.pkl /tmp/m239/EU10_0.pkl
env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 UCELE=0.40 \
    SK_DOSYA=/tmp/sk_bar48.pkl REB_GUN=15 FAZ=15 FAZ_KAY=1 python3 g33.py ls 5 > /tmp/m239/U15_1.txt 2>&1
cp /tmp/g19E_1.pkl /tmp/m239/EU15_1.pkl
echo BITTI >> /tmp/m239/DURUM2
