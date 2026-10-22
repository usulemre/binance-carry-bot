# Kazanç Defteri (backtest)

- `Kazanc_Defteri.pdf` — 53 sayfa: özet + yıllık tablo, aylık ısı haritası, her ay için gün gün tablo.
- `kazanc_tablosu.xlsx` — Yıllık / Aylık / Günlük / Varsayımlar sayfaları (formüllü; başlangıç bakiyesi ve kaldıraç değiştirilebilir).

Kaynak: g33.py backtest motoru, gerçekçi ağırlık kayması (madde 419), 2.000 $ seviyesi (D8), iki dilim hizasının
ortalaması, 20.07.2022 – 30.09.2026. T60 = madde 442 varsayılanı; "Eski bot" = T60 öncesi ayarlar.
Backtest sonuçlarıdır, canlı getiri değildir.

Yeniden üretmek: günlük seri `gunluk.pkl` (sütunlar `bot`, `t60`; /tmp/m412/M357_{KAYMA,T60}_2000_{0,1}.pkl
ortalamaları) çalışma klasörüne konur; `python3 excel_uret.py` ve `python3 pdf_uret.py` (+ Playwright ile
`defter.html` → PDF, A4, arka plan açık).
