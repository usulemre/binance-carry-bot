# ÖNERİLEN AYAR — test, demo ve canlı hepsinde (kullanıcı kararı 2026-10-29, KAR_HARITASI madde 648 / 656)

## Nasıl çalışır
`.env`'de `CARRY_PROFIL` yoksa ya da `CARRY_PROFIL=ONERILEN` ise bot (ve preflight) her açılışta bakiyeyi okur ve ölçülmüş ayarı seçer:

| kitap (özkaynak × CARRY_SERMAYE_OLCEK) | ayar | backtest (2.000 $ / 3.500 $ / TAM, yıllık) |
|---|---|---|
| < 3.500 $ | T7K 1,15x + koşullu stop | +%315 |
| 3.500 – 12.500 $ | T7K 1,10x + koşullu stop | +%286 |
| ≥ 12.500 $ | T6 1,10x + koşullu stop | +%374 |
| bakiye okunamazsa | T7K 1,0x + koşullu stop (kaldıraçsız) | — |

Log'da açılışta `ÖNERİLEN AYAR (madde 656): kitap … $ -> T7K 1.15x …` ve sonra `önerilen ayar etkin: …` satırı görünür.
Bakiye 3.500 $ / 12.500 $ eşiğini geçerse yeni doz bir sonraki yeniden başlatmada uygulanır (`sudo systemctl restart carry`).
`.env`'de açıkça verilen `CARRY_GROSS` / `CARRY_LONG_24S_PIYASA` korunur. Kapatmak: `CARRY_ONERILEN=0` ya da `CARRY_PROFIL=T4` vb.

## Geçiş (sunucuda, bir kez)
```bash
cd /opt/carry && git pull
sudo ./deploy/onerilen_kur.sh --hepsi      # /opt/carry + bütün /opt/carry-*/ (çoklu demo) kurulumları
# yalnız ana bot:            sudo ./deploy/onerilen_kur.sh
# yalnız bir demo botu:      sudo ./deploy/onerilen_kur.sh /opt/carry-AD carry@AD
```
Betik her kurulumda `.env`'i yedekler (`.env.yedek-ZAMAN`), eski profil / doz satırlarını silip `CARRY_PROFIL=ONERILEN` yazar, preflight
koşar; HATA'da `.env` eski haline döner, yoksa servisi yeniden başlatır. Yeni çoklu demo botu: `sudo ./deploy/coklu_demo_kur.sh AD ONERILEN
"" "" <ölçek>`. `.env`'inde profil satırı hiç olmayan kurulumlar `git pull` + yeniden başlatmayla da geçer.

Geri almak: `cp /opt/carry/.env.yedek-ZAMAN /opt/carry/.env && sudo systemctl restart carry`.
Bunlar geçmiş verinin simülasyonudur; canlı sonuç farklı olabilir. Ekim OOS kontrolü (izleme_ekim_oos.py, madde 650 geri dönüş kuralı) Kasım başında.
