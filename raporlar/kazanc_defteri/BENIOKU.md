> **2026-10-26 (madde 575):** üçüncü sütun artık **T6 aday** (standart model serisi Q_T6; önceden T4 merdivensiz). Pickle'larda `sr` = T6.

> **2026-10-25 GÜNCELLEME (madde 534):** T4 kod varsayılanı (asıl bot). İki PDF'te başlık sütunu artık **Asıl bot T4**,
> ikinci sütun **Eski bot T1** (pdf_uret.py t1/t2'yi yer değiştirir; pickle'da t1=T1, t2=T4 kalır). Rakamlar değişmedi.

> **2026-10-25 DÜZELTME (madde 527-528):** iki PDF de düzeltilmiş dolum kuralıyla (MERD_SIRA=1, uzun zemin) yeniden üretildi.
> Seriler: t1 = şu anki bot (Q_T1), t2 = T4 (Q_T4), sr = T4 merdivensiz (Q_T4NL), bot = merdivensiz T60 (U_M0);
> `Kazanc_Defteri.pdf` aynı serilerin 20.07.2022 sonrası kesitidir. Aşağıdaki eski açıklamalar düzeltme öncesine aittir.

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

## Kazanc_Defteri_6_Yil.pdf (uzun zemin, kaldıraçsız)
19.07.2020 – 30.09.2026, 78 sayfa: şu anki bot · **T4 (aday)** · T3 · merdivensiz T60. Veri `raporlar/gunluk_uzun.pkl`
(/tmp/m_uzun/M357_{U_T1,U_T3FN30,U_SR12CAP8,U_M0}_2000_{0,1}), üretim `PDF_PROFIL=uzun python3 pdf_uret.py` + Playwright.
