#!/usr/bin/env bash
# ÇOKLU DEMO KURULUMU (COKLU_DEMO.md). Kullanım: sudo ./deploy/coklu_demo_kur.sh AD PROFIL [GROSS] [KOSULLU] [OLCEK]
#   AD       klasör / servis adı (ör. T7KKS)        PROFIL  T4 | T6 | T7K | T60
#   GROSS    kaldıraç (varsayılan 1.0; T7K 1.15, T6 1.10 yalnız ≳12.500 $ kitapta)
#   KOSULLU  koşullu 24 sa stop eşiği (0 = kapalı, 0.03 önerilen)
#   OLCEK    CARRY_SERMAYE_OLCEK (kitap $ / demo özkaynak; varsayılan 1.0)
set -euo pipefail
AD=${1:?AD}; PROFIL=${2:?PROFIL}; GROSS=${3:-1.0}; KS=${4:-0}; OLCEK=${5:-1.0}
KAYNAK=/opt/carry; HEDEF=/opt/carry-$AD
[ -d "$KAYNAK/.git" ] || { echo "$KAYNAK bulunamadı (ana kurulum)"; exit 1; }
if [ ! -d "$HEDEF" ]; then git clone --quiet "$KAYNAK" "$HEDEF"; else git -C "$HEDEF" pull --quiet; fi
if [ ! -f "$HEDEF/.env" ]; then
  cat > "$HEDEF/.env" <<ENV
# $AD — AYRI demo hesabının anahtarları (başka botla PAYLAŞMAYIN)
BINANCE_MODE=demo
BINANCE_API_KEY=BURAYA
BINANCE_API_SECRET=BURAYA
CARRY_PROFIL=$PROFIL
CARRY_GROSS=$GROSS
$( [ "$GROSS" != "1.0" ] && echo "CARRY_DOZ_ONAY=$GROSS" )
CARRY_LONG_24S_PIYASA=$KS
CARRY_SERMAYE_OLCEK=$OLCEK
ENV
  echo ">> $HEDEF/.env yazıldı — API anahtarlarını doldurun"
fi
[ "$PROFIL" = "T7K" ] && [ ! -f "$HEDEF/carry_prim.csv" ] && cp "$HEDEF/carry_prim_tohum.csv" "$HEDEF/carry_prim.csv"
mkdir -p /opt/carry-rapor
cp "$KAYNAK"/deploy/carry@.service "$KAYNAK"/deploy/carry-defter@.service "$KAYNAK"/deploy/carry-defter@.timer \
   "$KAYNAK"/deploy/carry-rapor.service "$KAYNAK"/deploy/carry-rapor.timer /etc/systemd/system/
systemctl daemon-reload
echo ">> kontrol: (cd $HEDEF && python3 carry_preflight.py)"
echo ">> başlat:  systemctl enable --now carry@$AD carry-defter@$AD.timer carry-rapor.timer"
