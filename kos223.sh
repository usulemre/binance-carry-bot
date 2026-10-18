#!/bin/sh
# MADDE 223: REBALANCE_HOURS yeniden acilis taramasi.
# Kabul edilmis yapilandirma (madde 222 sonrasi): 5+5 bacak, HAVUZ=3,
# REZERV=0.20, TPL=0.40, TPS=0.20, UCELE=0.40, SK_DOSYA=sk_bar48.
# Tur araligi 8 saatte SABIT tutulur (FAZ=REB/2), yani dilim sayisi
# tutma suresiyle birlikte degisir - canli botun yapisi da boyle
# (N_DILIM = REBALANCE_HOURS / 8).
cd /home/claude/binance_bot/binance_bot
env HAVUZ=3 REZERV=0.20 REZ_ESIK=0.015 KAP=0.05 TP=0.4 TPL=0.40 TPS=0.20 UCELE=0.40 SK_DOSYA=/tmp/sk_bar48.pkl "$@" python3 g33.py ls 5
