# T7K'YI DEMO HESAPTA DENEMEK (isteğe bağlı; varsayılan T4)

T7K = T6'nın short ayarları (short 40 sa'te bir, short adayları 96 sa funding) + short coin tavanı %8 (T4 gibi)
+ funding fırsatı zayıfken brüt %70'e kadar KÜÇÜLÜR (prim çarpanı; asla 1,0'ı aşmaz, kaldıraç yok).
Kanıt (KAR_HARITASI madde 583-584, canlı gibi giriş + 5 bp, 2020-07..2026-09): getiri T4 ile aynı (yılda −12..+1 puan),
Sharpe +0,2..+0,3, düşüş 1-3 puan sığ, EN KÖTÜ GÜN −13 → −8, −%3 altı gün ~%30 az; −%5 altı gün benzer (2-4 → 3-6).

## Sunucuda
```bash
cd /opt/carry && git pull
[ -f carry_prim.csv ] || cp carry_prim_tohum.csv carry_prim.csv    # prim çarpanı ilk turdan çalışsın
```
`.env`:
```
BINANCE_MODE=demo
CARRY_PROFIL=T7K
```
`.env`'de şunlar VARSA silin: `CARRY_SHORT_ARA_SAAT`, `CARRY_SHORT_TAVAN`, `CARRY_SHORT_FUNDING_WINDOW_H`, `CARRY_PRIM_E`,
`CARRY_PRIM_ALT`, `CARRY_PRIM_UST`, `CARRY_PRIM_REF`, `CARRY_MERDIVEN_PAY`, `CARRY_EVREN_MIN`.
```bash
python3 carry_preflight.py              # "profil T7K", HATA 0
python3 carry_bot.py --dry-run --once   # log: "short penceresi 96 sa", "prim-ölçekli brüt: ... çarpan 0,7..1,0"
sudo systemctl restart carry
```

## Tohum düzeltmesi (madde 590, 2026-10-26)
İlk `carry_prim_tohum.csv` primi yanlış evrenden ölçüyordu (değerler ~%36 küçük) → canlı çarpan ilk aylarda 1,0'a yapışıp
backtest'teki kadar küçülmezdi. Yeni tohum `git pull` ile gelir. Sunucuda `carry_prim.csv` ESKİ tohumdan kopyalandıysa
(bot ona kendi ölçümlerini ekliyor) tohum satırlarını yenisiyle değiştir, botun eklediği satırları KORU:
```bash
python3 - <<'PY'
yeni=[l for l in open("carry_prim_tohum.csv")]; son=float(yeni[-1].split(",")[0])
canli=[l for l in open("carry_prim.csv") if float(l.split(",")[0])>son]
open("carry_prim.csv","w").writelines(yeni+canli); print(len(yeni),"tohum +",len(canli),"canlı satır")
PY
```
`carry_prim.csv` hiç yoksa eskisi gibi: `cp carry_prim_tohum.csv carry_prim.csv`.

## Kaldıraçlı T7K (madde 596) — ÖNCE 1x demo, sonra karar
T7K, T4 (1,0x) ile AYNI en büyük düşüşü 1,10-1,15x kaldıraçta veriyor; en kötü gün ve kötü yıl daha iyi (canlı gibi giriş + 5 bp,
2020-07..2026-09). Bedel: −%5 altı gün 3 → 5-6.
| bakiye | doz | yıllık | maks düşüş | en kötü gün | 1y p1 düşüş | (T4 1,0x) |
|---|---|---|---|---|---|---|
| < 3.500 $ | 1,15 | +303 | −15,2 | −9,1 | −21,7 | +244 · −15,3 · −13,3 · −24,8 |
| ≥ 3.500 $ | 1,10 | +272 | −15,9 | −8,7 | −21,6 | +242 · −16,0 · −13,0 · −25,1 |
(Komisyon kaldıraçla büyür: net ~5 puan düşük.) `.env`:
```
CARRY_PROFIL=T7K
CARRY_GROSS=1.15          # 3.500 $ ve üstünde 1.10
CARRY_DOZ_ONAY=1.15       # CARRY_GROSS ile AYNI değer; yoksa preflight HATA verir (madde 374)
```
Preflight bu iki dozu YALNIZ T7K'da kabul eder. Kapı (madde 276): önce 1x'te demo/canlı ölçüm, sonra doz.

## Geri dönüş
`.env`'den `CARRY_PROFIL=T7K` satırını silin (varsayılan T4) → `sudo systemctl restart carry`.
