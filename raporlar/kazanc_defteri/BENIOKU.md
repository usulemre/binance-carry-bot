# Kazanç Defteri (backtest)

- `Kazanc_Defteri.pdf` — 54 sayfa: kapak (özet + yıllık tablo + bakiye eğrisi), şu anki bot / 2. aday karşılaştırması
  ve aylık ısı haritaları, her ay için gün gün tablo (şu anki bot · 2. aday T2 · short ara dengeli).
- `kazanc_tablosu.xlsx` — ESKİ sürüm (T60 vs eski bot, merdivenden önce); güncellenmedi.

Seriler (2.000 $ seviyesi, D8 evreni, gerçekçi ağırlık kayması, iki dilim hizasının ortalaması, 20.07.2022 – 30.09.2026):
- **Şu anki bot** = ZSR15P67 — canlı varsayılan: T60 + 24 sa düşüş stop'u + iki taraflı merdiven (madde 469).
- **2. aday T2** = BRP80_CAP_A43 — şu anki bot + merdiven payı 0,80 + short coin tavanı %8 + 4 long / 3 short
  (madde 485-487; canlıda değil, ADAYLAR.md).
- **Short ara dengeli** = D1_SR6 — şu anki bot + short tarafı her gün yeniden seçilir (madde 493-495; 2025-26
  rejimine bağlı, protokol RED, canlıda değil; canlı gibi giriş + 5 bp maliyetle fark küçülür).
- **Eski bot** = KAYMA (T60 öncesi ayarlar), referans.
Backtest sonuçlarıdır, canlı getiri değildir.

Yeniden üretmek: `raporlar/gunluk.pkl` (sütunlar `t1`, `t2`, `sr`, `bot`; `arastirma_m443_kotu_gun_kalkani.seri()` ile
/tmp/m412/M357_{ZSR15P67,BRP80_CAP_A43,D1_SR6,KAYMA}_2000_{0,1}.pkl ortalamaları), sonra bu klasörde `python3 pdf_uret.py`
ve Playwright ile `defter.html` → PDF (A4, arka plan açık).
