# SUNUCU KURULUMU — sıfırdan çalışan bot (madde 662)

Bot 7/24 açık bir Linux sunucuda çalışır. En küçük paket yeter: 1-2 çekirdek, **2 GB RAM**, 20 GB disk, **Ubuntu 22.04 / 24.04**,
**Ubuntu 24.04 önerilir** (paket sürümleri onun Python'una sabitlendi), ayda ~4-8 $ (Hetzner, DigitalOcean, Vultr…). Konum: Avrupa (Frankfurt, Amsterdam, Helsinki) ya da Asya (Singapur, Tokyo) — **ABD değil**
(Binance ABD IP'lerine vadeli işlem açmıyor).

## 1) Sunucuyu kiralarken
- İşletim sistemi: Ubuntu 24.04. Giriş yöntemi olarak **SSH anahtarı** seçin (firma panelinde "SSH key ekle"). Anahtarınız yoksa
  bilgisayarınızda `ssh-keygen -t ed25519` → `~/.ssh/id_ed25519.pub` içeriğini panele yapıştırın.
- Bağlanın: `ssh root@SUNUCU_IP`

## 2) Tek komutla kurulum
```bash
curl -fsSL https://raw.githubusercontent.com/usulemre/binance-carry-bot/main/deploy/sunucu_kur.sh | sudo bash
# Tailscale (panel için özel ağ) da kurulsun:  ... | sudo TAILSCALE=1 bash
```
(Depo özelse önce `git clone --single-branch --branch main https://github.com/usulemre/binance-carry-bot.git /opt/carry` ve `sudo /opt/carry/deploy/sunucu_kur.sh`.)

Betik şunları yapar ve tekrar çalıştırmak güvenlidir:
- **Güvenlik:** ayrı, giriş yetkisi olmayan `carry` kullanıcısı; güvenlik duvarı (yalnız SSH açık); fail2ban; otomatik güvenlik
  güncellemeleri; SSH anahtarı varsa şifreyle girişi kapatır.
- **Kod:** `/opt/carry`, Python sanal ortamı, PDF rapor için Chromium.
- **Servisler:** bot (`carry`), günlük defter (03:05 TR), günlük rapor (03:15 TR). Hepsi `carry` kullanıcısıyla, sistemin geri kalanı
  salt okunur; bot çökerse 60 sn'de, sunucu yeniden başlarsa kendiliğinden açılır.
- **`.env` şablonu** (izin 600: yalnız bot okuyabilir).

## 3) Binance API anahtarı
Önce **demo**: demo.binance.com → API Management → yeni anahtar.
- İzin: yalnız **Futures**. **Para çekme KAPALI.**
- **IP kısıtlaması:** sunucunun IP'si (anahtar başka yerden çalışmaz).
Binance hesabınızda 2FA, oltalama karşıtı kod ve çekim adresi beyaz listesi açık olsun.

## 4) Anahtarları girin, kontrol edin, başlatın
```bash
sudo nano /opt/carry/.env          # BINANCE_API_KEY / SECRET; demo bakiyesinin bir kısmıyla denemek için CARRY_SERMAYE_OLCEK
cd /opt/carry && sudo -u carry .venv/bin/python carry_preflight.py     # sonda "0 HATA"
sudo systemctl start carry
journalctl -u carry -f              # "önerilen ayar etkin: profil T7K · gross 1.15x" ve "mod=demo"
```

## 5) Günlük
- Pozisyonlar / emirler: Binance (demo) uygulaması → Futures.
- Rapor: `/opt/carry-rapor/demo_defteri.pdf` (her gün 03:15 TR).
- Güncelleme: `cd /opt/carry && sudo -u carry git pull && sudo systemctl restart carry`.
- Durdurma: `sudo systemctl stop carry` (açık pozisyonlar borsada kalır; kâr al / stop emirleri borsada bekler).

### Panel: tarayıcıdan izleme (madde 671)
Kitap grafiği, günlük / aylık getiri, açık pozisyonlar, son olaylar (stop, delist, hata) — her kurulum ayrı sekmede, dakikada bir yenilenir.
**Salt okunur**: emir göndermez, API anahtarlarını yüklemez. Kurulumla gelir ve yalnız sunucunun içinde (`127.0.0.1:8050`) çalışır —
internetten **erişilemez**. Telefondan / bilgisayardan açmak için (bir kez):
1. Telefonunuza ve bilgisayarınıza Tailscale uygulamasını kurun, aynı hesapla girin.
2. Sunucuda: `sudo TAILSCALE=1 ./deploy/sunucu_kur.sh` (ya da `curl -fsSL https://tailscale.com/install.sh | sh`) → `sudo tailscale up`
3. `sudo tailscale serve --bg 8050` → verdiği `https://<sunucu>.<tailnet>.ts.net` adresini telefonda açın (yalnız sizin cihazlarınız görür).
Ek şifre isterseniz: `sudo systemctl edit carry-panel` → `[Service]` altına `Environment=CARRY_PANEL_SIFRE=...` (kullanıcı adı `carry`).
Panel sunucuda değilken (ör. bilgisayarınızda) tek dosyalık görüntü: `.venv/bin/python panel.py --disa-aktar panel.html --klasor /opt/carry`.

### Telegram: telefona bildirim (madde 670, isteğe bağlı)
Kurulursa şunlar telefona gelir: bot başladı · stop / delist kapanışı (ya da kapatılamadı) · sağlık kapısı · üst üste başarısız
tur · her gün özet (kitap, gün %, funding, komisyon) + PDF rapor · **nabız**: bot çöktü ya da 12 saattir tur atmıyorsa (saatlik kontrol).
1. Telegram'da **@BotFather** → `/newbot` → bir ad verin → verdiği **token**'ı kopyalayın.
2. Yeni botunuza Telegram'dan bir mesaj atın (ör. "merhaba").
3. `.env`'e ekleyin: `sudo nano /opt/carry/.env` → `TELEGRAM_TOKEN=...`
4. Chat id: `cd /opt/carry && sudo -u carry .venv/bin/python bildirim.py --chat-id-bul` → çıkan `TELEGRAM_CHAT_ID=...` satırını `.env`'e ekleyin.
5. Deneme: `sudo -u carry .venv/bin/python bildirim.py --dene` → telefona mesaj gelmeli.
6. `sudo systemctl restart carry`.

Bot Telegram'dan **komut almaz** (yalnız mesaj gönderir): telefonunuz ya da Telegram hesabınız ele geçse bile bot yönetilemez.
Çoklu demo: her `/opt/carry-AD/.env`'e aynı iki satır (mesajlar `[AD]` önekiyle gelir). Botu bilerek durduracaksanız
`sudo systemctl disable --now carry` (devre dışı servis için nabız uyarısı gelmez).

## 6) Gerçek hesaba geçiş (demo 2-4 hafta sonra)
`.env`'de `BINANCE_MODE=live`, gerçek hesabın anahtarı (aynı kurallar: yalnız Futures, çekim kapalı, IP kısıtlı), `CARRY_SERMAYE_OLCEK`
satırını silin → preflight → `sudo systemctl restart carry`. Küçük tutarla başlayın.

## 7) Acil durdurma (madde 663)
Hesabın ya da sunucunun ele geçirildiğinden şüphelenirseniz SIRAYLA:
1. **Binance'te API anahtarını SİLİN** (Hesap → API Management). En hızlı ve en etkili adım; sunucuya erişmeden yapılır.
2. Sunucuda: `sudo systemctl stop carry`
3. Pozisyonları kapatın: `cd /opt/carry && sudo -u carry .venv/bin/python acil_kapat.py` (önce listeler) →
   `... acil_kapat.py --evet` (bütün emirleri iptal eder, bütün pozisyonları kapatır, dilim defterini boşaltır). Anahtar silindiyse
   kapatmayı Binance uygulamasından elle yapın.

## 8) Güvenlik kontrol listesi
- [ ] API anahtarı: yalnız Futures, **para çekme kapalı**, **IP kısıtlı** (preflight bunu kontrol eder: canlıda çekim izni açıksa HATA)
- [ ] Binance: 2FA, oltalama karşıtı kod, çekim adresi beyaz listesi
- [ ] **GitHub hesabında 2FA** — sunucu kodu GitHub'dan çeker; GitHub hesabı ele geçirilirse kötü kod sunucuya `git pull` ile girebilir.
      Güncellemeyi yalnız siz elle yaparsınız (otomatik çekme yok).
- [ ] Sunucuya yalnız SSH anahtarıyla giriş (betik anahtar varsa şifreyi kapatır)
- [ ] Panel (eklenirse) internete açık değil, yalnız Tailscale üzerinden
- [ ] `.env` yedeklerini (`.env.yedek-*`) başka yere kopyalamayın; içlerinde anahtar var
Betiğin otomatik yaptıkları: ayrı yetkisiz kullanıcı, kısıtlı servisler, güvenlik duvarı, fail2ban, otomatik güvenlik güncellemeleri,
saat senkronu, log döndürme, paketler sabit sürüm + özet doğrulamasıyla (requirements.lock).
