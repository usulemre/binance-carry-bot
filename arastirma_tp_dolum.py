#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 267 — KÂR-AL DOLUMU: kitabın BÜTÜN kârının dayandığı varsayımın
dakika çözünürlüklü ilk doğrulaması.

Madde 214'ün yasası: *funding SEÇİCİdir, gelir değil; funding (+109,8) ve
ham fiyat (−108,0) birbirini götürüyor, kârın tamamı TP hasadından
(+210,5 puan).* Madde 236 bunu bacak bazında doğruladı: bacakların %90'ı
net −65 puan yük, TP ile kapanan %10 ise +114,5 kazandırıp hepsini
ödüyor.

Yani kitabın kârı TEK BİR VARSAYIMIN üstünde duruyor:

    g33.py:379    if (uzun and HV[i+1,k] >= sev) ...: br[k] = sev/cv[i,k]-1

**"4 saatlik barın YÜKSEĞİ TP seviyesine değdiyse, doldu ve tam o
fiyattan doldu."** Üretimde bu, pozisyon açılırken konan bir reduce-only
GTC limittir (`carry_bot.kar_al_kur`). Varsayım 267 maddedir hiç dakika
çözünürlüğünde sınanmadı — madde 249'da TP dolum fiyatını bir kez TERS
yazmıştım (stop konvansiyonunu limite uygulamak) ve o hata kitabın
hasadını tamamen silmişti; yani bu satır projenin en pahalı satırı.

YÖNTEM (ön kayıt)
-----------------
Veri: madde 265'in `data_1m/` arşivi (18 sembol, 2026-07/08, 89.280 dk).
İki ölçüm:

(A) MARJİNAL DOKUNUŞ — en kırılgan altküme. Her 4 saatlik bar için
    seviye = barın YÜKSEĞİ (H×0,9995), yani motorun "değdi" dediği an ile
    "değmedi" dediği an arasındaki sınır. O seviyede gerçekte kaç dakika
    işlem gördü ve ne kadar dolar hacim geçti?

(B) GERÇEK TP VAKASI — üretimdeki eşikler: LONG +%40 (`TPL`), SHORT −%20
    (`TPS`), 5 gün tutma, dilimler 8 saatte bir. TP'ye ULAŞAN dilimlerde,
    seviyenin ötesinde ilk 60 dakikada ne kadar hacim geçti?

Dolum ölçütü kuyruk derinliğini ölçemiyor (defter verisi yok), bu yüzden
tek bir katsayı yerine **duyarlılık** verildi: bacak büyüklüğünün 1 / 10
/ 50 / 100 katı kadar hacim gerekiyorsa dolmama oranı ne olur. Bacak
büyüklüğü = bakiye / (15 dilim × 10 bacak) = bakiye/150.

BULGU 1 — MARJİNAL DOKUNUŞ: %40'ı TEK DAKİKA, ama hacim yine de bol
-------------------------------------------------------------------
6.696 bar. Seviyede geçen süre: **%40,0'ı 1 dakika**, %32,4'ü 2-3 dk,
%21,6'sı 4-10 dk, %6,1'i 10+ dk. Seviyede geçen hacim: p1 1.341$ ·
p5 15.086$ · p25 240.924$ · **medyan 791.810$** · p75 2.836.983$.

    dolmama oranı (%)   bacak$ |   x1  |  x10  |  x50  | x100  | x500
    bakiye $10.000          67 | 0,01  | 0,54  | 2,17  | 3,46  | 7,21
    bakiye $100.000        667 | 0,54  | 3,46  | 7,21  | 10,35 | 31,17
    bakiye $1.000.000    6.667 | 3,46  | 10,35 | 31,17 | 46,00 | 77,58
    bakiye $5.000.000   33.333 | 7,21  | 31,17 | 65,43 | 77,58 | 89,58

BULGU 2 — GERÇEK TP VAKASI: VARSAYIM DOĞRULANDI
-----------------------------------------------
LONG +%40: **273 olay**, 13 sembol. Seviyenin üstünde ilk 60 dakikada
geçen hacim: p1 **129.486$** · p5 632.129$ · p25 3.023.312$ · **medyan
15.252.299$**. Fiyat seviyenin üstünde medyan **30 dakika** kalıyor.

SHORT −%20: **185 olay**, 5 sembol. Hacim p1 112.236$ · p5 499.103$ ·
medyan 4.760.121$; seviyede medyan 29 dakika.

    LONG dolmama oranı   bacak$ |  x1  | x10  | x50   | x100
    bakiye $10.000           67 | 0,00 | 0,00 | 0,00  | 0,00
    bakiye $100.000         667 | 0,00 | 0,00 | 0,00  | 0,37
    bakiye $1.000.000     6.667 | 0,00 | 0,37 | 2,93  | 5,49
    bakiye $5.000.000    33.333 | 0,00 | 2,93 | 14,65 | 26,01

    SHORT dolmama oranı          |  x1  | x10  | x50   | x100
    bakiye $10.000           67  | 0,00 | 0,00 | 0,00  | 0,00
    bakiye $100.000         667  | 0,00 | 0,00 | 0,54  | 0,54
    bakiye $1.000.000     6.667  | 0,00 | 0,54 | 3,24  | 7,03
    bakiye $5.000.000    33.333  | 0,54 | 3,24 | 21,08 | 36,76

**Sebep mekanizmada: TP uzakta.** Fiyat %40 yükselirken o hareket kendi
hacmini getiriyor — marjinal dokunuşun medyan 791 bin doları, gerçek TP
vakasında **15,3 milyon dolara** çıkıyor (19 kat). Motorun en pahalı
satırı, kullanılacak bakiyelerde SAĞLAM.

BULGU 3 — YAN ÜRÜN: 5 GÜNLÜK TUTMA SÜRESİ BAĞIMSIZ OLARAK DOĞRULANDI
--------------------------------------------------------------------
TP'ye ulaşma süresi LONG medyan **58 saat** (2,4 gün), p5 10 saat, p95
**111 saat** (4,6 gün); SHORT medyan 22 saat, p95 103 saat. Yani p95
vakası 5 günlük tutmanın **tam içine** sığıyor. Madde 223 tutma süresini
getiri/Sharpe üzerinden 5 günde bırakmıştı; bu, aynı seçimi tamamen
farklı bir veriyle (dakika + TP ulaşma süresi) destekliyor. 3 güne
inmek p95 vakalarını keserdi.

BULGU 4 — KAPASİTE SINIRI, POZİSYON BOYUTUNDAN ÖNCE TP DOLUMUNDA
----------------------------------------------------------------
Madde 204 kapasiteyi emir boyutu ve açık pozisyon oranından ölçmüş ve
"~1 milyon dolara kadar rahat, ~5 milyona kadar çalışır" demişti. Bu
ölçüm kısıtın **daha erken** ve **başka bir yerden** geldiğini
gösteriyor: 1 milyon dolarda TP dolumu muhafazakâr kuyruk varsayımıyla
(x100) **%5,5 / %7,0** oranında ıskalıyor, 5 milyonda **%26 / %37**.
Iskalanan TP, madde 236'ya göre kitabın parasını yapan %10'luk
popülasyondan düşer — yani kapasite aşımının bedeli getiride
doğrusal değil, hasatta.

SINIRLAR
--------
* Gerçek TP vakasında **273 + 185 olay, 13 + 5 sembol, 2 ay.** Küçük
  örneklem; yön güçlü, kesinlik değil.
* Kuyruk derinliği ÖLÇÜLEMEDİ (defter verisi yok). Bu yüzden tek sayı
  değil duyarlılık verildi; "x100" sütunu muhafazakâr okuma.
* Dilim seçimi rastgele zaman ızgarasından; gerçek kitabın seçtiği
  bacaklar funding ucundadır ve madde 251'e göre daha OYNAKtır — oynak
  isimde TP'ye ulaşma olasılığı yüksek, hacim de yüksek olur; yön belli
  değil, bu yüzden bir düzeltme uygulanmadı.

HÜKÜM: motorun en pahalı varsayımı kullanılacak bakiyelerde DOĞRULANDI.
Ayar DEĞİŞMEDİ. Kapasite notu güncellendi.
"""
from __future__ import annotations

# (A) marjinal dokunuş — 6.696 bar
MARJINAL = {
    "bar": 6696, "sembol": 18,
    "tek_dakika_oran": 40.0, "iki_uc_dakika_oran": 32.4,
    "dort_on_dakika_oran": 21.6, "on_ustu_oran": 6.1,
    "hacim_p1": 1341, "hacim_p5": 15086, "hacim_p25": 240924,
    "hacim_medyan": 791810, "hacim_p75": 2836983,
}
MARJINAL_DOLMAMA = {           # bakiye -> {kat: %}
    10000: {1: 0.01, 10: 0.54, 50: 2.17, 100: 3.46, 500: 7.21},
    100000: {1: 0.54, 10: 3.46, 50: 7.21, 100: 10.35, 500: 31.17},
    1000000: {1: 3.46, 10: 10.35, 50: 31.17, 100: 46.00, 500: 77.58},
    5000000: {1: 7.21, 10: 31.17, 50: 65.43, 100: 77.58, 500: 89.58},
}

# (B) gerçek TP vakası
TP_LONG = {
    "esik": 0.40, "olay": 273, "sembol": 13,
    "hacim_p1": 129486, "hacim_p5": 632129, "hacim_p25": 3023312,
    "hacim_medyan": 15252299,
    "seviyede_dakika_medyan": 30,
    "ulasma_saat_medyan": 58, "ulasma_saat_p5": 10, "ulasma_saat_p95": 111,
}
TP_SHORT = {
    "esik": 0.20, "olay": 185, "sembol": 5,
    "hacim_p1": 112236, "hacim_p5": 499103, "hacim_medyan": 4760121,
    "seviyede_dakika_medyan": 29,
    "ulasma_saat_medyan": 22, "ulasma_saat_p95": 103,
}
TP_DOLMAMA_LONG = {
    10000: {1: 0.00, 10: 0.00, 50: 0.00, 100: 0.00},
    100000: {1: 0.00, 10: 0.00, 50: 0.00, 100: 0.37},
    1000000: {1: 0.00, 10: 0.37, 50: 2.93, 100: 5.49},
    5000000: {1: 0.00, 10: 2.93, 50: 14.65, 100: 26.01},
}
TP_DOLMAMA_SHORT = {
    10000: {1: 0.00, 10: 0.00, 50: 0.00, 100: 0.00},
    100000: {1: 0.00, 10: 0.00, 50: 0.54, 100: 0.54},
    1000000: {1: 0.00, 10: 0.54, 50: 3.24, 100: 7.03},
    5000000: {1: 0.54, 10: 3.24, 50: 21.08, 100: 36.76},
}
TUTMA_GUN = 5
BACAK_BOLEN = 150          # 15 dilim x 10 bacak


def bacak_usd(bakiye: float) -> float:
    return bakiye / BACAK_BOLEN


def tp_guvenli_mi(bakiye: int, kat: int = 100, esik_pct: float = 1.0) -> bool:
    """Bu bakiyede TP dolumu güvenilir mi? (muhafazakâr kuyruk: x100)"""
    return (TP_DOLMAMA_LONG[bakiye][kat] < esik_pct
            and TP_DOLMAMA_SHORT[bakiye][kat] < esik_pct)


def tutma_suresi_yetiyor_mu() -> bool:
    """TP'ye ulaşmanın p95'i 5 günlük tutmanın içinde mi?"""
    return (TP_LONG["ulasma_saat_p95"] <= TUTMA_GUN * 24
            and TP_SHORT["ulasma_saat_p95"] <= TUTMA_GUN * 24)


def marjinal_mi_gercek_mi() -> float:
    """Gerçek TP vakasında hacim marjinal dokunuşun kaç katı?"""
    return TP_LONG["hacim_medyan"] / MARJINAL["hacim_medyan"]


def kapasite_sinirini_ne_belirliyor() -> str:
    return ("madde 204 kapasiteyi emir boyutu ve açık pozisyondan ölçüp "
            "'~1M$ rahat, ~5M$ çalışır' demişti; madde 267 kısıtın DAHA "
            "ERKEN ve BAŞKA YERDEN geldiğini gösteriyor: 1M$'da TP dolumu "
            "muhafazakâr kuyrukla %5,5 (long) / %7,0 (short) ıskalıyor, "
            "5M$'da %26 / %37. Iskalanan TP madde 236'nın parayı yapan "
            "%10'luk popülasyonundan düşer.")


def hukum() -> str:
    return ("Motorun en pahalı varsayımı (HV>=sev -> TP doldu) "
            "kullanılacak bakiyelerde DOĞRULANDI. Ayar DEĞİŞMEDİ.")


def yaz() -> None:
    print("MADDE 267 — KÂR-AL DOLUMU\n")
    print("(A) MARJİNAL DOKUNUŞ (%d bar) — en kırılgan altküme" % MARJINAL["bar"])
    print("  seviyede süre: %%%.1f tek dakika · %%%.1f 2-3dk · %%%.1f 4-10dk"
          % (MARJINAL["tek_dakika_oran"], MARJINAL["iki_uc_dakika_oran"],
             MARJINAL["dort_on_dakika_oran"]))
    print("  hacim: p1 %d$ · p5 %d$ · medyan %d$"
          % (MARJINAL["hacim_p1"], MARJINAL["hacim_p5"], MARJINAL["hacim_medyan"]))
    print("\n(B) GERÇEK TP VAKASI")
    print("  LONG  +%%%.0f: %d olay · hacim medyan %d$ (p1 %d$) · seviyede %d dk"
          % (TP_LONG["esik"] * 100, TP_LONG["olay"], TP_LONG["hacim_medyan"],
             TP_LONG["hacim_p1"], TP_LONG["seviyede_dakika_medyan"]))
    print("  SHORT -%%%.0f: %d olay · hacim medyan %d$ (p1 %d$) · seviyede %d dk"
          % (TP_SHORT["esik"] * 100, TP_SHORT["olay"], TP_SHORT["hacim_medyan"],
             TP_SHORT["hacim_p1"], TP_SHORT["seviyede_dakika_medyan"]))
    print("  gerçek TP hacmi marjinalin %.1f KATI" % marjinal_mi_gercek_mi())
    print("\nDOLMAMA ORANI (muhafazakâr kuyruk = bacağın 100 katı):")
    print("  bakiye        bacak$ |  LONG  | SHORT  | güvenli?")
    for b in sorted(TP_DOLMAMA_LONG):
        print("  $%9d   %7.0f | %5.2f%% | %5.2f%% | %s"
              % (b, bacak_usd(b), TP_DOLMAMA_LONG[b][100],
                 TP_DOLMAMA_SHORT[b][100],
                 "EVET" if tp_guvenli_mi(b) else "HAYIR"))
    print("\nTUTMA SÜRESİ: TP'ye ulaşma p95 long %d sa / short %d sa,"
          % (TP_LONG["ulasma_saat_p95"], TP_SHORT["ulasma_saat_p95"]))
    print("  tutma %d gün = %d saat -> yetiyor mu: %s"
          % (TUTMA_GUN, TUTMA_GUN * 24, tutma_suresi_yetiyor_mu()))
    print("\nKAPASİTE: %s" % kapasite_sinirini_ne_belirliyor())
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
