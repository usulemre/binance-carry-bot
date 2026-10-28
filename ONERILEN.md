# ÖNERİLEN AYARI TEK KOMUTLA UYGULA (kullanıcı kararı 2026-10-28, KAR_HARITASI madde 648)

```bash
cd /opt/carry && git pull
sudo ./deploy/onerilen_kur.sh                 # ana bot (/opt/carry, servis carry)
# çoklu demoda bir bot için:  sudo ./deploy/onerilen_kur.sh /opt/carry-T4 carry@T4
```
Betik bakiyeyi borsadan okur (CARRY_SERMAYE_OLCEK varsa onunla çarpar) ve ölçülmüş dozu seçer:

| kitap | ayar | backtest (yıllık, aynı risk) |
|---|---|---|
| < 3.500 $ | T7K 1,15x + koşullu stop | +%315 (2.000 $) |
| 3.500 – 12.500 $ | T7K 1,10x + koşullu stop | +%286 (3.500 $) |
| ≥ 12.500 $ | T6 1,10x + koşullu stop | +%374 (TAM) |

Ne yapar: `.env`'i yedekler (`.env.yedek-ZAMAN`), eski profil / doz / profilin kendi ayarladığı satırları siler, önerilen 4 satırı
yazar (CARRY_PROFIL, CARRY_GROSS, CARRY_DOZ_ONAY, CARRY_LONG_24S_PIYASA=0.03), T7K'da prim dosyasını tohumdan kurar, preflight koşar.
Preflight HATA verirse `.env` eski haline döner ve servis dokunulmaz; geçerse servis yeniden başlar.

Geri almak: `cp /opt/carry/.env.yedek-ZAMAN /opt/carry/.env && sudo systemctl restart carry`.
Bakiye 3.500 $ / 12.500 $ eşiğini geçerse betiği yeniden çalıştırın (doz ölçülmüş değere göre değişir).
Bunlar geçmiş verinin simülasyonudur; canlı sonuç farklı olabilir. Ekim OOS kontrolü (izleme_ekim_oos.py) Kasım başında yine yapılacak.
