#!/bin/bash
# MADDE 367: 5 dakikalik klines, en likit 100 sembol, 2024-01 .. 2026-08.
# curl (madde 342: urlopen bu ortamda tikaniyor), var olan dosyayi atlar,
# 4 paralel. Kullanim: bash indir_5m.sh EVREN_DOSYASI
cd "$(dirname "$0")"; mkdir -p data_5m
EVREN="$1"
aylar=$(python3 -c "
import pandas as pd; print(' '.join(p.strftime('%Y-%m') for p in pd.period_range('2024-01','2026-08',freq='M')))")
for s in $(cat "$EVREN"); do for a in $aylar; do echo "$s $a"; done; done | \
  xargs -P 4 -n 2 sh -c '
    f="data_5m/$0-5m-$1.zip"; [ -s "$f" ] && exit 0
    curl -sS -f -m 120 --retry 2 -o "$f.tmp" \
      "https://data.binance.vision/data/futures/um/monthly/klines/$0/5m/$0-5m-$1.zip" \
      && mv "$f.tmp" "$f" || rm -f "$f.tmp"'
echo "[5M-BITTI] $(ls data_5m | wc -l) dosya"
