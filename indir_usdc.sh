#!/bin/bash
# MADDE 387: USDC perp funding (aylik) + 4h klines (aylik), data.binance.vision.
cd "$(dirname "$0")"; mkdir -p data_usdc/fon data_usdc/k4
for s in $(cat data_usdc/semboller.txt); do
  for tur in fon k4; do
    if [ $tur = fon ]; then pre="data/futures/um/monthly/fundingRate/$s/"; else pre="data/futures/um/monthly/klines/$s/4h/"; fi
    curl -sS -m 60 "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix=$pre&delimiter=/" | grep -o "<Key>[^<]*\.zip</Key>" | sed 's#<Key>##;s#</Key>##'
  done
done | xargs -P 8 -n 1 sh -c 'k="$0"; b=$(basename "$k"); case "$k" in *fundingRate*) d=data_usdc/fon;; *) d=data_usdc/k4;; esac; [ -s "$d/$b" ] || curl -sS -f -m 120 --retry 2 -o "$d/$b" "https://data.binance.vision/$k"'
echo "fon $(ls data_usdc/fon | wc -l) k4 $(ls data_usdc/k4 | wc -l)"
