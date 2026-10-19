#!/bin/bash
# MADDE 342 — SIFIRDAN TAM YENİDEN KURULUM, TEK KOMUT, KALDIĞI YERDEN.
#
# NEDEN VAR: 2026-10-19'da konteyner silindi ve zemini elle, adım adım,
# iki kez takılarak yeniden kurdum (madde 335). Depoda kod ve bulgular
# vardı ama HAM VERİ (708 MB) ve /tmp zemini (1,3 GB) yoktu — ikisi de
# .gitignore'da, doğru olan da bu. Eksik olan şey, onları yeniden
# kuracak TEK ve GÜVENİLİR bir zincirdi.
#
# Bu betik yeni bir konteynerde şunu garanti eder: başlat, bırak, dön.
#   - her adım kaldığı yerden devam eder (sembol başına dosya, var olanı atlar)
#   - çekme katmanı CURL (madde 342: urlopen bu ortamda SESSİZCE TIKANIYOR)
#   - son adım PARİTE KAPISI: tutmazsa referans serisi YAZILMAZ
#
# KULLANIM
#     bash yeniden_kurulum.sh            # hepsi
#     bash yeniden_kurulum.sh zemin      # yalniz veri indirmesi
#     bash yeniden_kurulum.sh panel      # yalniz panel + parite
#
# SÜRE: fiyat+taker ~236 MB tek geçişte, funding 79 MB, metrik 92 MB.
# 2026-10-19'da metrik indirmesi tek başına ~1 saat sürdü (587 sembol).
set -u
cd "$(dirname "$0")"
L=/tmp/yeniden_kurulum.log
ADIM="${1:-hepsi}"
say() { echo "[$(date +%H:%M:%S)] $*" | tee -a $L; }

: > $L
say "=== YENIDEN KURULUM BASLADI (adim: $ADIM)"

if [ "$ADIM" = "hepsi" ] || [ "$ADIM" = "zemin" ]; then
  say "--- 1/5 sembol listesi"
  python3 indir_sembol_listesi.py >> $L 2>&1
  say "    $(wc -l < tum_semboller.txt 2>/dev/null) sembol"
  cp -f tum_semboller.txt /tmp/tum_semboller.txt 2>/dev/null

  say "--- 2/5 fiyat + taker (TEK gecis, 3 dilim paralel)"
  for a in 0 300 600; do
    nohup python3 indir_zemin_surdurulebilir.py klines $a $((a+300)) \
      > /tmp/kur_kl_$a.log 2>&1 &
  done
  while pgrep -f '[s]urdurulebilir.py klines' > /dev/null; do
    say "    fiyat $(ls data_genis 2>/dev/null | wc -l) · taker $(ls data_taker_genis 2>/dev/null | wc -l)"
    sleep 120
  done
  say "    bitti: fiyat $(ls data_genis | wc -l) · taker $(ls data_taker_genis | wc -l)"

  say "--- 3/5 funding (3 dilim paralel)"
  for a in 0 300 600; do
    nohup python3 indir_zemin_surdurulebilir.py funding $a $((a+300)) \
      > /tmp/kur_fn_$a.log 2>&1 &
  done
  while pgrep -f '[s]urdurulebilir.py funding' > /dev/null; do
    say "    funding $(ls data_funding_genis 2>/dev/null | wc -l)"
    sleep 120
  done
  say "    bitti: funding $(ls data_funding_genis | wc -l)"
fi

if [ "$ADIM" = "hepsi" ] || [ "$ADIM" = "panel" ]; then
  say "--- 4/5 motor zemini (/tmp/zemin.pkl, panel, hlo, g.py, sk_bar48)"
  python3 yeniden_kur.py >> $L 2>&1
  say "    cikis $?"
  if [ ! -s /tmp/zemin.pkl ]; then
    say "    DURDURULDU: /tmp/zemin.pkl yok - sonraki adimlar anlamsiz"
    exit 1
  fi

  say "--- 5/5 metrik (sembol-gun ciftleri -> indirme -> panel)"
  python3 metrik_kur.py cift >> $L 2>&1
  for a in 0 200 400; do
    nohup python3 indir_metrik_surdurulebilir.py $a $((a+200)) \
      > /tmp/kur_mt_$a.log 2>&1 &
  done
  while pgrep -f '[i]ndir_metrik_surdurulebilir' > /dev/null; do
    say "    metrik $(ls data_metrik 2>/dev/null | wc -l)"
    sleep 120
  done
  python3 indir_metrik_surdurulebilir.py panel >> $L 2>&1
  say "    metrik paneli cikis $?"

  say "--- PARITE KAPISI (hedef: tam +112,3% / Sharpe 3,10 / dd -14,5)"
  bash parite_zinciri.sh
  tail -8 /tmp/parite_zinciri.log | tee -a $L
fi

say "=== BITTI. Parite GECTI ise referans_getiri.csv yazilmistir;"
say "    TUTMADI ise YAZILMAMISTIR - dogrulanmamis zemin uzerine olcum yapilmaz."
say "    Son adim: python3 test_carry_preflight.py  (beklenen: 1108+ kontrol, 0 hata)"
