# BÜYÜK BAKİYE KURULUMU (≳ 12.500 $; kullanıcının 1-5 milyon TL ≈ 20-100 bin $'ı) — T6 1,10x + KOŞULLU STOP

Bu bakiyede bacak her coinin asgari emrini geçer → evrenden hiçbir coin dışlanmaz (TAM evren). Ölçüm (KAR_HARITASI madde 601, 618, 619,
623, 628; gerçekçi model: canlı gibi tek hesap girişi + 5 bp + düzeltilmiş kademe dolumu, 2020-07 → 2026-09, iki hiza):

| kitap (TAM evren) | yıllık | maks düşüş | en kötü gün | −%5 altı gün (6 yıl) |
|---|---|---|---|---|
| T4 1,0x (kod varsayılanı) | +%232 | −%16,6 | −%12,9 | 4 |
| T7K 1,15x + koşullu stop | +%303 | ≈ T4 | −%8,0 | 7 |
| **T6 1,10x + koşullu stop** | **+%374** | ≈ T4 | −%7,7 | 12 |

Kaldıraç dozları T4 1,0x'in maks düşüşünü, en kötü gününü ve 1 yıllık kötü senaryosunu (bootstrap p1) AŞMAYACAK şekilde seçildi
(madde 596 yöntemi). Takas: T6 en çok kazanır ama −%5'lik günü daha SIK yaşar (yılda ~2); T7K daha sakin.
Bunlar geçmiş verinin simülasyonudur; canlı sonuç farklı olabilir.

## Sıra (madde 276 kapısı: önce 1x, sonra kaldıraç)
1. Ekim OOS (madde 617): Kasım başı veri gelince `izleme_ekim_oos.py` — T6 ve T7K "olağan" olmalı.
2. Demo hesapta 1x ile birkaç hafta (dolumlar backtest'le uyuşuyor mu).
3. Sonra 1,10x.

## `.env` (demo)
```
BINANCE_MODE=demo
CARRY_PROFIL=T6
CARRY_LONG_24S_PIYASA=0.03        # koşullu 24 sa stop (madde 622-623)
# kaldıraç, 2. adımdan SONRA:
# CARRY_GROSS=1.10
# CARRY_DOZ_ONAY=1.10
```
`.env`'de şunlar VARSA silin: `CARRY_SHORT_ARA_SAAT`, `CARRY_SHORT_TAVAN`, `CARRY_SHORT_FUNDING_WINDOW_H`, `CARRY_MERDIVEN_PAY`,
`CARRY_EVREN_MIN` (profil ayarlar).
```bash
cd /opt/carry && git pull
python3 carry_preflight.py              # "profil T6", "koşullu 24 sa stop TAMAM", (kaldıraçta) "doz TAMAM", HATA 0
python3 carry_bot.py --dry-run --once
sudo systemctl restart carry
```
Preflight T6'da yalnız 1,10x'i ölçülmüş doz sayar (madde 629); 1,15 ve üstü HATA. Bakiye 12.500 $'ın altına inerse T6 1,10x
ölçülmüş değildir — T7K'ya dönün (DEMO_T7K.md).

## Koşullu stop logda nasıl görünür
- `KOŞULLU 24 SA STOP: XYZ 24 sa −48,0%, piyasa −6,1% -> kapatılıyor` (piyasa çapında çöküş: satış)
- `KOŞULLU 24 SA STOP: XYZ 24 sa −47,0% ama piyasa −0,8% (eşik −3%) -> tutuluyor` (tek coin çöküşü: tutulur; madde 621 otopsisi
  bu coinlerin 3 günde döndüğünü ölçtü)
