#!/usr/bin/env bash
# ÖNERİLEN AYARA GEÇ (madde 648 / 656; ONERILEN.md). Kullanım:
#   sudo ./deploy/onerilen_kur.sh                       ana bot (/opt/carry, servis carry)
#   sudo ./deploy/onerilen_kur.sh /opt/carry-AD carry@AD  tek bir çoklu-demo botu
#   sudo ./deploy/onerilen_kur.sh --hepsi               /opt/carry + bütün /opt/carry-*/ kurulumları (test / demo / canlı)
# Madde 656'dan beri bot önerilen ayarı KENDİSİ seçer: .env'de CARRY_PROFIL yoksa ya da ONERILEN ise açılışta bakiyeyi okur
# (< 3.500 $ T7K 1,15x · 3.500-12.500 $ T7K 1,10x · ≥ 12.500 $ T6 1,10x; hepsi koşullu stop 0,03). Bu betik .env'den eski profil /
# doz / profilin ayarladığı satırları siler, CARRY_PROFIL=ONERILEN yazar, preflight koşar; HATA'da .env geri döner, yoksa servis yeniden başlar.
set -euo pipefail

tek() {
  local KLASOR=$1 SERVIS=$2
  echo "=== $KLASOR ($SERVIS)"
  cd "$KLASOR"
  [ -f .env ] || { echo "!! $KLASOR/.env yok — atlandı"; return 0; }
  git pull --quiet || echo "!! git pull başarısız — mevcut kodla devam"
  local YEDEK=.env.yedek-$(date +%Y%m%d-%H%M%S)
  cp .env "$YEDEK"
  grep -vE '^(CARRY_PROFIL|CARRY_GROSS|CARRY_DOZ_ONAY|CARRY_LONG_24S_PIYASA|CARRY_ONERILEN|CARRY_SHORT_ARA_SAAT|CARRY_SHORT_TAVAN|CARRY_SHORT_FUNDING_WINDOW_H|CARRY_MERDIVEN_PAY|CARRY_EVREN_MIN)=' "$YEDEK" > .env || true
  cat >> .env <<ENV
# ÖNERİLEN AYAR ($(date +%F); madde 656 — bot bakiyeye göre her açılışta seçer; ONERILEN.md)
CARRY_PROFIL=ONERILEN
ENV
  set +e; python3 carry_preflight.py; local RC=$?; set -e
  if [ $RC -ne 0 ]; then
    cp "$YEDEK" .env
    echo "!! preflight HATA verdi — .env eski haline döndü ($YEDEK). Servis değişmedi."
    return 1
  fi
  systemctl restart "$SERVIS" || echo "!! $SERVIS yeniden başlatılamadı (servis kurulu mu?)"
  echo ">> uygulandı. Eski .env: $KLASOR/$YEDEK"
  echo ">> izle: journalctl -u $SERVIS -f   ('önerilen ayar etkin' satırı)"
  echo ">> geri al: cp $KLASOR/$YEDEK $KLASOR/.env && systemctl restart $SERVIS"
}

if [ "${1:-}" = "--hepsi" ]; then
  HATA=0
  [ -d /opt/carry ] && { tek /opt/carry carry || HATA=1; }
  for d in /opt/carry-*/; do
    d=${d%/}; [ -f "$d/carry_bot.py" ] || continue
    tek "$d" "carry@${d#/opt/carry-}" || HATA=1
  done
  exit $HATA
fi
tek "${1:-/opt/carry}" "${2:-carry}"
