# T4'ü DEMO HESAPTA ÇALIŞTIRMA (kullanıcı kararı, 2026-10-25)

T4 = şu anki bot (T60 + 24 sa stop + iki taraflı merdiven) + short 2 günde bir yenileme + short coin tavanı %8 +
merdiven payı 0,80 + evren tabanı 30. Kanıt: ADAYLAR.md, KAR_HARITASI madde 497-522. Kaldıraçsız (CARRY_GROSS 1,0).

## 1) Sunucuda (demo hesabın olduğu makine)
```bash
cd /opt/carry
git pull
pip install -U -r requirements.txt
```
`.env` dosyasında:
```
BINANCE_MODE=demo          # DEMO — gerçek para değil
CARRY_PROFIL=T4            # T4'ün dört ayarı bu satırla gelir
```
`.env`'de şunlar VARSA silin (profil değerlerini ezerler): `CARRY_SHORT_ARA_SAAT`, `CARRY_SHORT_TAVAN`,
`CARRY_MERDIVEN_PAY`, `CARRY_EVREN_MIN`, `CARRY_LONG_STOP`. CARRY_GROSS tanımlıysa 1.0 olmalı.

## 2) Kontrol
```bash
python3 carry_preflight.py          # "profil  T4 (kullanıcı kararı ...)" ve HATA 0 görmelisiniz
python3 carry_bot.py --dry-run --once
```
Kuru çalışmada log'da beklenenler:
- `evren: N sembol ...` (N ≥ 30; eşik yetmezse `evren tabanı: ... eklendi` uyarısı)
- ilk turlardan sonra `short ara dengelemesi: 2 dilimin short tarafı yenilendi (...)` (her turda iki dilim)

## 3) Başlat
```bash
sudo systemctl restart carry
journalctl -u carry -f
```

## 4) Ne ölçülecek (2-4 hafta)
- **Gerçek dolum maliyeti** (ücret + kayma, işlem başı): madde 519'a göre T4'ün avantajı ~15 bp'nin altında belirgin,
  ~29 bp'de sıfır. `carry_sapma.py` / TP defteri ile izlenir.
- **Short ara dengelemesinin devri**: T1'e göre emir sayısı yaklaşık 1,5-2 kat beklenir.
- **Kötü günler**: backtest'te T4'te −%5 altı gün 6 yılda 2 (T1: 7).

## Geri dönüş
`.env`'den `CARRY_PROFIL=T4` satırını silin (varsayılan T60 = şu anki bot) → `sudo systemctl restart carry`.
Dilim defteri uyumludur; ek işlem gerekmez.
