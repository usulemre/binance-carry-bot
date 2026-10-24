#!/bin/sh
# Motor zemini seçici (madde 497): ./zemin_sec.sh 22  -> 2022+ (varsayılan), ./zemin_sec.sh uzun -> 2020+
case "$1" in 22) K=/tmp/z22;; uzun) K=/tmp/zu;; *) echo "kullanim: $0 22|uzun"; exit 1;; esac
for f in zemin.pkl panel.pkl hlo.pkl g.py sk_bar60.pkl sk_bar48.pkl metrik_panel.pkl; do cp -p "$K/$f" "/tmp/$f"; done
echo "zemin: $1"
