#!/usr/bin/env bash
# MADDE 680: .env'deki BINANCE anahtar satırlarını (API key / secret / özel anahtar parolası) systemd ile ŞİFRELER ve
# .env'den siler. Servis başlarken systemd çözer ve yalnız o sürecin görebildiği geçici bir dizine koyar; diskte düz metin anahtar
# kalmaz (yedek / disk kopyası ele geçse bile okunamaz; şifre bu sunucuya bağlıdır, TPM varsa ona).
#   sudo /opt/carry/deploy/anahtar_sifrele.sh                  ana bot
#   sudo /opt/carry/deploy/anahtar_sifrele.sh /opt/carry-AD AD  çoklu demo botu
# Geri almak: sudo systemd-creds decrypt /etc/credstore.encrypted/carry.env - >> /opt/carry/.env ; sudo rm /etc/credstore.encrypted/carry.env
# Gerekli: Ubuntu 24.04 (systemd ≥ 254). Anahtarı değiştirmek için: satırları .env'e geri yazıp betiği tekrar çalıştırın.
set -euo pipefail
KL=${1:-/opt/carry}; AD=${2:-}
AdC=carry.env; [ -n "$AD" ] && AdC="carry-$AD.env"
[ "$(id -u)" = 0 ] || { echo "sudo ile çalıştırın"; exit 1; }
command -v systemd-creds >/dev/null || { echo "!! systemd-creds yok (Ubuntu 24.04 gerekir)"; exit 1; }
V=$(systemctl --version | awk 'NR==1{print $2}'); [ "$V" -ge 254 ] || { echo "!! systemd $V < 254: ImportCredential desteklenmiyor"; exit 1; }
ENV=$KL/.env; DESEN='^(BINANCE_API_KEY|BINANCE_API_SECRET|BINANCE_PRIVATE_KEY_PASS)='
# Telegram / dış nabız satırları DÜZ kalır: nabız, rapor ve paket servisleri onları .env'den okur (sızarsa en kötü: size mesaj atılır)
GIZLI=$(grep -E "$DESEN" "$ENV" | grep -v '=BURAYA$' || true)
[ -n "$GIZLI" ] || { echo "!! $ENV içinde şifrelenecek gizli satır yok (zaten şifreli olabilir)"; exit 1; }
mkdir -p /etc/credstore.encrypted; chmod 700 /etc/credstore.encrypted
printf '%s\n' "$GIZLI" | systemd-creds encrypt --name="$AdC" - "/etc/credstore.encrypted/$AdC"
YEDEK=$(mktemp); cp "$ENV" "$YEDEK"
grep -vE "$DESEN" "$YEDEK" > "$ENV"; printf '# gizli satırlar şifrelendi: /etc/credstore.encrypted/%s (madde 680)\n' "$AdC" >> "$ENV"
shred -u "$YEDEK" 2>/dev/null || rm -f "$YEDEK"
echo ">> şifrelendi: /etc/credstore.encrypted/$AdC ($(printf '%s\n' "$GIZLI" | wc -l) satır); .env'den silindi"
echo ">> yeniden başlatın: sudo systemctl daemon-reload && sudo systemctl restart ${AD:+carry@$AD}${AD:-carry}"
