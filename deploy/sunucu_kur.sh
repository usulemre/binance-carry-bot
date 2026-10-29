#!/usr/bin/env bash
# MADDE 662 — SUNUCU KURULUMU (tek komut; Ubuntu 22.04 / 24.04). KURULUM_SUNUCU.md
#   curl -fsSL https://raw.githubusercontent.com/usulemre/binance-carry-bot/main/deploy/sunucu_kur.sh | sudo bash
#   (ya da depoyu klonlayıp: sudo ./deploy/sunucu_kur.sh)
# Yapar: güvenlik (ayrı 'carry' kullanıcısı, güvenlik duvarı, fail2ban, otomatik güvenlik güncellemeleri, SSH'de şifreyle girişi
# — yalnız anahtar varsa — kapatma), kod (/opt/carry, Python sanal ortamı, PDF için Chromium), servisler (bot + günlük defter + rapor;
# hepsi yetkisiz kullanıcıyla, sistem salt okunur), .env şablonu (izin 600), isteğe bağlı Tailscale.
# Tekrar çalıştırmak güvenlidir (var olanı bozmaz; .env'e dokunmaz).
set -euo pipefail
DEPO=${CARRY_DEPO:-https://github.com/usulemre/binance-carry-bot.git}
KOK=/opt/carry
[ "$(id -u)" = 0 ] || { echo "sudo ile çalıştırın"; exit 1; }
. /etc/os-release; echo ">> sistem: $PRETTY_NAME"

echo ">> 1/7 paketler"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq git python3 python3-venv python3-pip ufw fail2ban unattended-upgrades curl ca-certificates logrotate >/dev/null

echo ">> 2/7 kullanıcı 'carry' (giriş kabuğu yok)"
id carry >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/carry --shell /usr/sbin/nologin carry

echo ">> 3/7 kod: $KOK"
if [ -d "$KOK/.git" ]; then sudo -u carry git -C "$KOK" pull --quiet || echo "!! git pull başarısız — mevcut kodla devam"
else git clone --quiet "$DEPO" "$KOK"; fi
mkdir -p /opt/carry-rapor
chown -R carry:carry "$KOK" /opt/carry-rapor
chmod +x "$KOK"/deploy/*.sh

echo ">> 4/7 Python sanal ortamı + bağımlılıklar + PDF için Chromium"
[ -x "$KOK/.venv/bin/python" ] || sudo -u carry python3 -m venv "$KOK/.venv"
sudo -u carry "$KOK/.venv/bin/pip" install -q --upgrade pip
# MADDE 663: SABİTLENMİŞ sürümler + özet (hash) doğrulaması (requirements.lock; Python 3.12 = Ubuntu 24.04). Bir paketin kötü niyetli /
# bozuk yeni sürümü sunucuya sessizce giremez. Başka Python'da (22.04 = 3.10) sabitsiz requirements.txt'ye düşülür (uyarıyla).
if [ "$("$KOK/.venv/bin/python" -c 'import sys;print("%d.%d"%sys.version_info[:2])')" = "3.12" ] && [ -f "$KOK/requirements.lock" ]; then
  sudo -u carry "$KOK/.venv/bin/pip" install -q --require-hashes -r "$KOK/requirements.lock"
else
  echo "!! Python 3.12 değil (Ubuntu 24.04 önerilir): sabitlenmemiş requirements.txt kuruluyor"
  sudo -u carry "$KOK/.venv/bin/pip" install -q -r "$KOK/requirements.txt" playwright
fi
"$KOK/.venv/bin/python" -m playwright install-deps chromium >/dev/null 2>&1 || echo "!! chromium sistem kütüphaneleri kurulamadı (PDF olmayabilir, HTML rapor yine çıkar)"
sudo -u carry env PLAYWRIGHT_BROWSERS_PATH="$KOK/.pw" "$KOK/.venv/bin/python" -m playwright install chromium >/dev/null 2>&1 \
  || echo "!! chromium indirilemedi (PDF olmayabilir, HTML rapor yine çıkar)"

echo ">> 5/7 .env (anahtarlar) — yoksa şablon, izin 600"
if [ ! -f "$KOK/.env" ]; then
  cat > "$KOK/.env" <<'ENV'
# Binance DEMO hesabı (demo.binance.com -> API Management). Yalnız "Futures" izni; PARA ÇEKME KAPALI; IP kısıtlaması: bu sunucunun IP'si.
BINANCE_MODE=demo
BINANCE_API_KEY=BURAYA
BINANCE_API_SECRET=BURAYA
# Önerilen ayar (madde 656): bakiyeye göre otomatik.
CARRY_PROFIL=ONERILEN
# Demo bakiyesinin yalnız bir kısmını kullanmak için: denenecek tutar / demo bakiyesi (ör. 2000 / 5000 = 0.4). Gerçek hesapta SİLİN.
# CARRY_SERMAYE_OLCEK=0.4
ENV
fi
chown carry:carry "$KOK/.env"; chmod 600 "$KOK/.env"

echo ">> 6/7 servisler"
cp "$KOK"/deploy/carry.service "$KOK"/deploy/carry@.service "$KOK"/deploy/carry-defter.service "$KOK"/deploy/carry-defter.timer \
   "$KOK"/deploy/carry-defter@.service "$KOK"/deploy/carry-defter@.timer "$KOK"/deploy/carry-rapor.service "$KOK"/deploy/carry-rapor.timer \
   /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now carry-defter.timer carry-rapor.timer >/dev/null
systemctl enable carry >/dev/null   # anahtarlar girilince: sudo systemctl start carry

echo ">> 7/7 güvenlik"
# MADDE 663: saat senkronu (Binance imzalı istekler saat kayarsa -1021 ile reddedilir) ve log döndürme (disk dolmasın)
timedatectl set-ntp true 2>/dev/null || true
cat > /etc/logrotate.d/carry <<'LR'
/opt/carry/carry_bot.log /opt/carry-*/carry_bot.log {
    weekly
    rotate 12
    compress
    missingok
    notifempty
    copytruncate
    su carry carry
}
LR
ufw allow OpenSSH >/dev/null; ufw --force enable >/dev/null
systemctl enable --now fail2ban >/dev/null
dpkg-reconfigure -f noninteractive unattended-upgrades >/dev/null 2>&1 || true
# SSH: şifreyle girişi YALNIZ en az bir yetkili anahtar varsa kapat (yoksa kendinizi dışarıda bırakırsınız)
if ls /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null | xargs -r grep -l "ssh-" >/dev/null 2>&1; then
  mkdir -p /etc/ssh/sshd_config.d
  printf "PasswordAuthentication no\nKbdInteractiveAuthentication no\nPermitRootLogin prohibit-password\nMaxAuthTries 3\nX11Forwarding no\n" > /etc/ssh/sshd_config.d/90-carry.conf
  systemctl reload ssh 2>/dev/null || systemctl reload sshd 2>/dev/null || true
  echo "   SSH: şifreyle giriş kapatıldı (yalnız anahtar)"
else
  echo "!! SSH anahtarı bulunamadı: şifreyle giriş AÇIK bırakıldı. Anahtar ekleyip betiği tekrar çalıştırın (KURULUM_SUNUCU.md)."
fi
if [ "${TAILSCALE:-0}" = 1 ]; then
  command -v tailscale >/dev/null || curl -fsSL https://tailscale.com/install.sh | sh
  echo "   Tailscale: 'sudo tailscale up' ile bu sunucuyu hesabınıza bağlayın"
fi

cat <<SON

KURULUM TAMAM. Sıradaki adımlar:
  1) Anahtarları girin:   sudo nano $KOK/.env
  2) Kontrol:             cd $KOK && sudo -u carry .venv/bin/python carry_preflight.py     (sonda '0 HATA')
  3) Başlat:              sudo systemctl start carry
  4) İzle:                journalctl -u carry -f
Rapor her gün 03:15 (TR): /opt/carry-rapor/demo_defteri.pdf
SON
