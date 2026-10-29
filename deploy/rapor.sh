#!/bin/sh
# MADDE 662: günlük rapor — defteri olan bütün kurulumlar (ana /opt/carry + /opt/carry-*). carry-rapor.service çağırır.
set -e
cd /opt/carry-rapor
ARG=""
for d in /opt/carry/ /opt/carry-*/; do
  [ -f "$d/carry_bot.py" ] && [ -f "$d/defter/gunluk.jsonl" ] && ARG="$ARG --klasor $d"
done
[ -n "$ARG" ] || { echo "rapor: henüz defter yok"; exit 0; }
exec /opt/carry/.venv/bin/python /opt/carry/carry_gunluk_defter.py rapor $ARG --cikti /opt/carry-rapor/demo_defteri.html --pdf
