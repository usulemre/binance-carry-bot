#!/usr/bin/env bash
# MADDE 680: Ed25519 API anahtarı üretir (sunucuda). Özel anahtar sunucudan HİÇ çıkmaz; Binance'e yalnız ekrana basılan AÇIK anahtar verilir.
#   sudo /opt/carry/deploy/ed25519_anahtar.sh            -> /opt/carry/keys/binance_ed25519.pem (izin 600, sahibi carry)
# Sonra: Binance (demo / gerçek) -> API Management -> Create API -> "Self-generated" -> aşağıdaki AÇIK anahtarı yapıştır.
# Binance'in verdiği API Key'i .env'e BINANCE_API_KEY olarak yazın; BINANCE_API_SECRET satırını SİLİN ve şunu ekleyin:
#   BINANCE_PRIVATE_KEY_PATH=/opt/carry/keys/binance_ed25519.pem
set -euo pipefail
D=${1:-/opt/carry/keys}; F=$D/binance_ed25519.pem
mkdir -p "$D"; chmod 700 "$D"
if [ -f "$F" ]; then echo "!! $F zaten var (üzerine yazılmadı). Yeni anahtar için önce eskisini taşıyın."; else
  umask 077; openssl genpkey -algorithm ed25519 -out "$F"; fi
id carry >/dev/null 2>&1 && chown -R carry:carry "$D"
chmod 600 "$F"
echo; echo "=== Binance'e yapıştırılacak AÇIK anahtar ==="; openssl pkey -in "$F" -pubout; echo
echo "Özel anahtar: $F (KİMSEYLE paylaşmayın, sohbete yapıştırmayın)"
