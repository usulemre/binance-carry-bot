#!/usr/bin/env bash
# MADDE 680: bir betiği botun servis ortamında (carry kullanıcısı + .env + varsa ŞİFRELİ anahtarlar) çalıştırır.
# Anahtarlar şifrelendikten sonra (anahtar_sifrele.sh) preflight / acil_kapat / defter elle böyle çalıştırılır:
#   sudo /opt/carry/deploy/carry_calistir.sh carry_preflight.py
#   sudo /opt/carry/deploy/carry_calistir.sh acil_kapat.py --evet
#   KL=/opt/carry-AD AD=AD sudo -E /opt/carry/deploy/carry_calistir.sh carry_preflight.py     (çoklu demo)
set -euo pipefail
KL=${KL:-/opt/carry}; AD=${AD:-}; C=carry.env; [ -n "$AD" ] && C="carry-$AD.env"
[ "$(id -u)" = 0 ] || { echo "sudo ile çalıştırın"; exit 1; }
if [ -f "/etc/credstore.encrypted/$C" ]; then
  exec systemd-run --quiet --pipe --wait --collect -p User=carry -p Group=carry -p WorkingDirectory="$KL" \
       -p EnvironmentFile="$KL/.env" -p ImportCredential="$C" /opt/carry/.venv/bin/python "$@"
else
  cd "$KL" && exec sudo -u carry /opt/carry/.venv/bin/python "$@"
fi
