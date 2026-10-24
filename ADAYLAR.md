# AYAR ADAYLARI — sıralı kayıt

Kullanıcı kararı (2026-10-24): araştırma bundan sonra İKİ taban üzerinden yürür — her yeni deneme ikisine de
uygulanır ve ikisine karşı ölçülür (`arastirma_tabanlar.py`).

| sıra | ad | ne | durum | 2.000 $ backtest (kaymalı, iki hiza) |
|---|---|---|---|---|
| 1 | **ZSR15P67** — şu anki bot | T60 + 24 sa düşüş stop'u −%45 + iki taraflı merdiven (long ⅔ @ +%45 / kalan +%60, short ⅔ @ −%15 / kalan −%20) | CANLI VARSAYILAN (madde 469) | +%249,3/yıl · Sh 3,83 · dd −%17,4 · en kötü gün −%5,45 · −%5 altı 3 gün |
| 2 | **BRP80_CAP_A43** — 2. en büyük aday | 1 numara + merdiven payı 0,80 + short coin tavanı %8 (hesap düzeyi) + 4 long / 3 short | PLATO (madde 487, 4/4 komşu) · protokol RED P %76-86 (madde 486) · **2020-21 yeni dönemde TUTMADI (madde 497: −15 / eşitVol −14) → "2022-26'ya özel"** · KULLANICI KARARI | +%256,1/yıl · Sh 4,00 · dd −%13,4 · en kötü gün −%5,53 · −%5 altı 1 gün · eşit oynaklıkta +19,2 |

2 numarayı bota almak için gerekenler: `CARRY_MERDIVEN_PAY` 0,667 → 0,80 (mevcut düğme); short bacak sayısı (yeni
düğme, 3); short coin başına tavan %8 (yeni düğme — bot 15 dilimi tek hesapta tuttuğu için doğal olarak hesap düzeyi);
preflight profili + testler. Bekleyen doğrulama: Ekim 2026 gerçek verisiyle OOS (Kasım başı).

Diğer kayıtlı kullanıcı kararları: kaldıraç 1,25x (madde 458/478 tablosu), 24 sa stop'u isteğe bağlı yapmak.

## Ekim 2026 OOS izleme listesi (madde 492, ön kayıt — `izleme_ekim_oos.py`)
Tem-Eyl 2026'da tabandan iyi görünen ama ön kaydı geçemeyen kollar Ekim gerçek verisinde TEK seferde ölçülecek
(karar vermez; T2 vs T1 kanıtını güçlendirir/zayıflatır): kademe geri alımı (iki taraf / yalnız short, madde 491),
short kademe −%18 (madde 488), short ara dengelemesi S_REB 1 g / 2 g (madde 493-495, 2025-26 rejim etkisi), defterle long seçimi DR50/CK50 (madde 479, defter verisi indirilirse).

## Short ara dengelemesi (S_REB, madde 493-498) — kullanıcı kararı adayı
Şu anki bot + short tarafı her 2 günde bir yeniden seçilir (long'lar 5 günde bir). 2020-21 / 2022-24 / 2025-26 üç dönemin
üçünde de yıllık ve Sharpe'ta önde (madde 497), canlı gibi giriş + 5 bp maliyette de (madde 494). AMA en büyük düşüş
~5 puan derin (2021 çöküşü) → uzun zemin protokolü RED, P %49-74 (madde 498). Getiri +46..+61 puan/yıl (muhafazakar).

## T1 + short 2 g'de bir + short tavan %8 (madde 500-501) — EN GÜÇLÜ kullanıcı kararı adayı
6 yıllık uzun zeminde (2020-07..2026-09) üç dönemin üçünde önde; canlı gibi giriş + 5 bp ile protokolde dört şart 16/16
hücrede GEÇTİ, düşüş her hücrede sığ, yalnız P %68-82 (eşik %95). Getiri +17..+26 puan/yıl (muhafazakar), Sharpe
+0,13..+0,47, −%5 altı gün 7 → 3, en kötü gün −13,6 → −11,6 (uzun zemin, standart model).

Bota eklendi (varsayılan KAPALI): açmak için `.env`'e `CARRY_SHORT_ARA_SAAT=48` ve `CARRY_SHORT_TAVAN=0.08`. Testler: `test_carry_short_ara.py`.
