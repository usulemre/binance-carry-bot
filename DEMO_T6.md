# T6'YI DEMO HESAPTA DENEMEK (isteğe bağlı; varsayılan T4)

T6 = T4 + short coin tavanı YOK + short'lar 40 saatte bir yenilenir + short adayları 96 saatlik funding ortalamasıyla seçilir.
Kanıt (KAR_HARITASI madde 568-572, canlı gibi giriş + 5 bp, 2020-07..2026-09, kaldıraçsız): T4'e göre yılda +55..+80 puan,
Sharpe ~3,85 → 4,1-4,2, düşüş aynı, en kötü gün −13 → −11; bedel: −%5 altı gün 2-4 → 6-9. Protokol P %87-92 (eşik %95 → RED,
KULLANICI KARARI gerekir).

## Sunucuda
```bash
cd /opt/carry && git pull
```
`.env`:
```
BINANCE_MODE=demo
CARRY_PROFIL=T6
```
`.env`'de şunlar VARSA silin (profili ezerler): `CARRY_SHORT_ARA_SAAT`, `CARRY_SHORT_TAVAN`, `CARRY_SHORT_FUNDING_WINDOW_H`,
`CARRY_MERDIVEN_PAY`, `CARRY_EVREN_MIN`.
```bash
python3 carry_preflight.py              # "profil T6" ve HATA 0
python3 carry_bot.py --dry-run --once   # log'da "short penceresi 96 sa: N sembol"
sudo systemctl restart carry
```
Not: her tur funding geçmişi iki kez çekilir (60 ve 96 sa) — API çağrısı ~2 katı, hız sınırının altında.

## Geri dönüş
`.env`'den `CARRY_PROFIL=T6` satırını silin (varsayılan T4) → `sudo systemctl restart carry`. Dilim defteri uyumlu.
