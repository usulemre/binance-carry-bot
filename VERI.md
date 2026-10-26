# Araştırma verisi (`veri` dalı)

Bu depodaki araştırmanın (KAR_HARITASI.md) kullandığı ham ve işlenmiş veri, **`veri` dalında** parçalara bölünmüş
sıkıştırılmış arşivler olarak durur. Hepsi Binance'in herkese açık piyasa verisidir (data.binance.vision ve REST API);
hesap bilgisi, API anahtarı ya da kişisel işlem kaydı İÇERMEZ.

## İndirme ve açma
```bash
git clone --single-branch --branch veri https://github.com/usulemre/binance-carry-bot binance-carry-veri
cd binance-carry-veri
sha256sum -c SHA256SUMS.txt --quiet -- 2>/dev/null || (cd parca && sha256sum -c ../SHA256SUMS.txt)
for a in ham_uzun_2020_2026 ham_genis_2022_2026 data_5m premium_aralik_derin zemin_uzun_zu; do
  cat parca/$a.tar.xz.part* > $a.tar.xz
done
sha256sum -c TAM_SHA256.txt
# ham veri bot klasörüne:
tar -xJf ham_uzun_2020_2026.tar.xz -C /path/to/binance-carry-bot
tar -xJf ham_genis_2022_2026.tar.xz -C /path/to/binance-carry-bot
# işlenmiş zemin (motor için hazır): /tmp altına
tar -xJf zemin_uzun_zu.tar.xz -C /tmp            # -> /tmp/zu  (sonra ./zemin_sec.sh uzun)
tar -xJf premium_aralik_derin.tar.xz -C /tmp     # -> /tmp/premium, /tmp/aralik.pkl, /tmp/derin_panel.pkl
```

## Arşivler
| arşiv | içerik | dönem |
|---|---|---|
| `ham_uzun_2020_2026` | `data_genis_uzun` (4 sa fiyat mumları), `data_funding_uzun` (funding geçmişi), `data_taker_uzun` (taker hacmi), `data_metrik` (açık pozisyon, long/short oranları), `data_premium_ek`, `data_usdc`, `data_kullanici`, spot listeleme jsonları | 2020-01 .. 2026-09 |
| `ham_genis_2022_2026` | `data_genis`, `data_funding_genis`, `data_taker_genis` (2022+ zemini) | 2022-01 .. 2026-09 |
| `data_5m` | 5 dakikalık mumlar (madde 367 vb.) | seçili dönemler |
| `premium_aralik_derin` | `premium/prim_4h.pkl` (premiumIndexKlines, 4 sa; madde 550), `aralik.pkl` (funding aralığı paneli; madde 552), `derin_panel.pkl` (emir defteri; madde 477) | 2020-01 .. 2026-09 |
| `zemin_uzun_zu` | `/tmp/zu`: motorun hazır zemini — `zemin.pkl`, `panel.pkl`, `hlo.pkl`, `metrik_panel.pkl`, sinyal panelleri `sk_bar{36,48,60,72,96,144}.pkl`, prim harmanları | 2020-01 .. 2026-09 |

Zemini ham veriden yeniden kurmak: `VERI_EK=uzun BAS_YIL=2020 python3 yeniden_kur.py` ve
`VERI_EK=uzun PEN=60 AD=bar60 python3 canli_sinyal_kur.py` (KAR_HARITASI madde 497).

## Sunucu için not
Bot sunucusunun bu dalı indirmemesi için (bir kez):
```bash
git config remote.origin.fetch +refs/heads/main:refs/remotes/origin/main
```
