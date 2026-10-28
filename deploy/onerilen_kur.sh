#!/usr/bin/env bash
# ÖNERİLEN AYARI UYGULA (ONERILEN.md). Kullanım: sudo ./deploy/onerilen_kur.sh [KLASOR] [SERVIS]
#   KLASOR  bot kurulumu (varsayılan /opt/carry)      SERVIS  systemd servisi (varsayılan carry; çoklu demoda carry@AD)
# Bakiyeyi borsadan okur, ölçülmüş dozu seçer (KAR_HARITASI 596 / 623 / 629):
#   < 3.500 $            T7K 1,15x + koşullu stop
#   3.500 - 12.500 $     T7K 1,10x + koşullu stop
#   ≥ 12.500 $ (TAM)     T6  1,10x + koşullu stop
# .env yedeklenir (.env.yedek-ZAMAN), preflight HATA verirse yedek GERİ yüklenir ve servis yeniden başlatılmaz.
set -euo pipefail
KLASOR=${1:-/opt/carry}; SERVIS=${2:-carry}
cd "$KLASOR"
[ -f .env ] || { echo "$KLASOR/.env yok"; exit 1; }
git pull --quiet || echo "!! git pull başarısız — mevcut kodla devam"

BAKIYE=$(python3 - <<'PY'
import sys, logging
logging.disable(logging.CRITICAL)
import config, carry_bot as cb
from exchange_client import ExchangeClient
c = ExchangeClient(config.API_KEY, config.API_SECRET, mode=getattr(config, "MODE", "demo"))
b = cb._sermaye_oku_ham(c)
print(f"{b:.2f}" if b else "")
PY
) || BAKIYE=""
[ -n "$BAKIYE" ] || { echo "!! bakiye okunamadı (API anahtarı / bağlantı?) — hiçbir şey değiştirilmedi"; exit 1; }
OLCEK=$(grep -E '^CARRY_SERMAYE_OLCEK=' .env | tail -1 | cut -d= -f2 || true); OLCEK=${OLCEK:-1.0}
KITAP=$(python3 -c "print(round($BAKIYE*$OLCEK,2))")

read PROFIL GROSS < <(python3 -c "
k=$KITAP
print('T6 1.10' if k>=12500 else 'T7K 1.10' if k>=3500 else 'T7K 1.15')")
echo ">> kitap $KITAP \$ → $PROFIL ${GROSS}x + koşullu stop (0.03)"

YEDEK=.env.yedek-$(date +%Y%m%d-%H%M%S); cp .env "$YEDEK"
# profilin kendisi ayarladığı / eski elle ayarlar: sil, sonra önerileni yaz
grep -vE '^(CARRY_PROFIL|CARRY_GROSS|CARRY_DOZ_ONAY|CARRY_LONG_24S_PIYASA|CARRY_SHORT_ARA_SAAT|CARRY_SHORT_TAVAN|CARRY_SHORT_FUNDING_WINDOW_H|CARRY_MERDIVEN_PAY|CARRY_EVREN_MIN)=' "$YEDEK" > .env
cat >> .env <<ENV
# ÖNERİLEN AYAR ($(date +%F), kitap $KITAP \$; deploy/onerilen_kur.sh — ONERILEN.md)
CARRY_PROFIL=$PROFIL
CARRY_GROSS=$GROSS
CARRY_DOZ_ONAY=$GROSS
CARRY_LONG_24S_PIYASA=0.03
ENV
[ "$PROFIL" = "T7K" ] && [ ! -f carry_prim.csv ] && cp carry_prim_tohum.csv carry_prim.csv

set +e; python3 carry_preflight.py; RC=$?; set -e
if [ $RC -ne 0 ]; then
  cp "$YEDEK" .env
  echo "!! preflight HATA verdi — .env eski haline döndü ($YEDEK). Servis değişmedi."
  exit 1
fi
systemctl restart "$SERVIS"
echo ">> uygulandı: $PROFIL ${GROSS}x + koşullu stop. Eski .env: $KLASOR/$YEDEK"
echo ">> izle: journalctl -u $SERVIS -f   (KOŞULLU 24 SA STOP satırları)"
echo ">> geri al: cp $KLASOR/$YEDEK $KLASOR/.env && systemctl restart $SERVIS"
