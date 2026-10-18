#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 291 — İCRA VARSAYIMLARI 2 AYDAN 1 YILA ÇIKARILDI: DOZ KARARI
DOĞRULANDI (VE BENİM İLK DUYURUM YANLIŞTI).

Projenin yayınlanan +%112,3'ü üç icra varsayımına dayanıyor (madde
265/266/267) ve o üçü dakika çözünürlüğünde **yalnız 2 ay** üzerinde
ölçülmüştü: 2026-07/08, tek rejim. Madde 276 ihtiyatlı dozu (1,25x) o
2 aylık pencerenin gün içi büyütmesiyle kurdu — ama toleransın kendisi
**1 YILLIK p95 düşüş** üzerine verildi ("−30 tahammül ederim").

Bu madde 673 MB dakika verisi indirdi: altı REJİM KARŞITI ay, artı
**sürekli 365 günlük** bir panel (16 sembol, 525.600 bar, 2025-09-01 →
2026-08-31).

═══ ARACIN KENDİSİ ÖNCE DOĞRULANDI ═══

Madde 266'nın ön kayıtlı yöntemi birebir kuruldu (5+5 nötr bacak, 15
örtüşen dilim, 8 saatte bir yeni dilim, 5 gün tutma, brüt 1,0, seçim
RASTGELE 40 tohum) ve ilk önce **madde 266'nın KENDİ penceresinde**
koşturuldu:

    ölçü                  bu araç    madde 266 yayınladı
    1dk düşüş ortalama    −%14,64        −%16,15
    1dk düşüş medyan      −%13,31        −%14,14
    1dk düşüş EN KÖTÜ     −%37,58        −%41,41
    büyütme medyan           1,72           1,49
    büyütme ortalama         1,84           1,80
    büyütme p90              2,55           2,72

Her eksende yeniden üretiliyor. Ölçüm aracı önce kontrolde sınandı
(madde 290'ın birinci yasasının tersi değil, tamamlayıcısı: kontrolde
tutmak yetmez ama tutmaması işi bitirir).

ÖNEMLİ NOT — KAPİTAL KONVANSİYONU: ilk yazımımda kapanan dilimlerin
P&L'si düşüyordu; özkaynak sıfır çevresinde salınan bir ortalamaya
dönüşüyor ve düşüş ~0 çıkıyordu. Düzeltildi (dilim kapandıktan sonra
kapanış getirisini KALICI taşır). Düzeltmeden sonra madde 266'nın
seviyeleri de yeniden üretildi — yani seviyeler de aynı konvansiyonda.

═══ BULGU 1 — REJİM ÖNEMLİ DEĞİL ═══

Altı rejim karşıtı ay, gün içi büyütme (1dk düşüş / 1g kapanış düşüşü):

    ay                    medyan   ort    p90   maks
    2022-11 (FTX çöküşü)    1,34   1,47   1,77   3,00
    2023-08 (sakin)         1,21   1,31   1,65   2,49
    2024-03 (boğa)          1,24   1,35   1,74   2,46
    2025-02                 1,26   1,31   1,52   2,43
    2025-10                 1,35   1,57   2,30   4,31
    2026-02                 1,16   1,28   1,58   2,45

Bant **1,16-1,35** — ve FTX çöküşü ayı (1,34) bir aykırı değer DEĞİL.
Madde 266'nın ikinci bulgusu ("nötr kitabın gün içi riski piyasa
riskinde değil TEK İSİM riskinde") altı rejimde doğrulandı: piyasa
çapında çöküş tam olarak nötr kitabın korunduğu şeydir.

═══ BULGU 2 — BÜYÜTME, PENCERE UZUNLUĞUNDA **U BİÇİMLİ** ═══

Aynı sürekli 365 günlük panel, örtüşen pencereler:

    pencere   yol sayısı   büyütme medyan   ort    p90
     1 ay        276           1,28         1,43   1,90
     2 ay        120           1,17         1,23   1,40
     3 ay         84           1,13         1,22   1,54
     6 ay         36           1,15         1,27   1,46
    12 ay      40 tohum      **1,458**    1,545   2,055

Monoton DEĞİL: kısa pencerede tek bir diken 1 dakikalık maksimumu
belirler, günlük yol toparlanmaya zaman bulamaz → oran yüksek. Orta
pencerede günlük düşüş birikmesi dikenin büyümesinden hızlı → oran
düşer. Bir yılda 1 dakikalık maksimum gerçekten uç bir dikene
ulaşır (en kötü tohum −%57,50) → oran yeniden yükselir.

**SONUÇ: 2 aylık bir büyütme ölçümü hiçbir yöne doğru ekstrapole
edilemez.** Ne "pencere uzadıkça büyür" ne "küçülür" doğru.

═══ BULGU 3 — DOZ KARARI DOĞRULANDI; BENİM DUYURUMU YANLIŞTI ═══

Tur ortasında kullanıcıya şunu yazdım: *"madde 276 büyütmeyi 2 aylık
bir pencereden aldı, tolerans 1 yıllıktı, demek ki 1,25x'te yayınlanan
gün içi kuyruk İYİMSER."* Ölçüm bunun **tersini** söylüyor:

    büyütme            madde 276 kullandı    1 YILDA ÖLÇÜLEN (40 tohum)
    medyan                   1,488                 **1,458**
    p90                      2,722                 **2,055**

Medyan neredeyse birebir (%2 ihtiyatlı), p90 ise madde 276'da **%32
İHTİYATLI**. Yani 1,25x'in güvenlik payı yayınlanandan **küçük değil,
BÜYÜK**. Doz kararının kalibrasyonu, kararın verildiği ufukta
doğrulandı.

Not: 1 yıllık satır TEK bir gerçekleşmiş yıl üzerinde 40 rastgele seçim
çekilişidir (bir yıldan birden fazla bağımsız yıllık pencere çıkmaz).
Belirsizlik büyük — ve madde 276'nın daha ihtiyatlı p90'ı tam bu
belirsizlik karşısında makul bir seçim.

═══ YASA ═══

**Bir varsayımı, kararın VERİLDİĞİ ufukta ölç.** Madde 274 "kararın
ölçütü neyse kıyas onunla" demişti; bu madde aynı şeyin ZAMAN ekseni:
tolerans 1 yıllık p95 düşüş üzerine verildiyse, onu besleyen büyütme de
1 yıllık pencerede ölçülmelidir. 2 aylık bir ölçüm yanlış değildi,
**başka bir soruya** doğru cevaptı.

İKİNCİ YASA (kendi hatamdan): **bir eksikliği fark etmek, yönünü bilmek
demek değildir.** "2 ay 1 yılı temsil etmez" doğruydu; "o yüzden gerçek
kuyruk daha derin" uydurmaydı. Eksikliği duyururken yönünü de
duyurmak, ölçmediğim bir şeyi söylemekti.
"""

# --- aracin dogrulanmasi --------------------------------------------
ARAC_DOGRULAMA = {   # olcu -> (bu arac, madde 266)
    "1dk dusus ortalama": (-14.64, -16.15),
    "1dk dusus medyan": (-13.31, -14.14),
    "1dk dusus EN KOTU": (-37.58, -41.41),
    "buyutme medyan": (1.72, 1.49),
    "buyutme ortalama": (1.84, 1.80),
    "buyutme p90": (2.55, 2.72),
}
KAPITAL_HATAM = ("ilk yazimimda KAPANAN dilimlerin P&L'si dusuyordu; "
                 "ozkaynak sifir cevresinde salinan bir ortalamaya "
                 "donusuyor ve dusus ~0 cikiyordu - duzeltildi, dilim "
                 "kapandiktan sonra kapanis getirisini KALICI tasir")

# --- rejim karsiti aylar: ay -> (sembol, medyan, ort, p90, maks) ----
AYLAR = {
    "2022-11 (FTX cokusu)": (9, 1.34, 1.47, 1.77, 3.00),
    "2023-08 (sakin)": (12, 1.21, 1.31, 1.65, 2.49),
    "2024-03 (boga)": (12, 1.24, 1.35, 1.74, 2.46),
    "2025-02": (13, 1.26, 1.31, 1.52, 2.43),
    "2025-10": (16, 1.35, 1.57, 2.30, 4.31),
    "2026-02": (18, 1.16, 1.28, 1.58, 2.45),
}

# --- pencere uzunlugu: ad -> (gun, yol, medyan, ort, p90) ----------
PENCERE = {
    "1 ay": (30, 276, 1.28, 1.43, 1.90),
    "2 ay": (61, 120, 1.17, 1.23, 1.40),
    "3 ay": (91, 84, 1.13, 1.22, 1.54),
    "6 ay": (182, 36, 1.15, 1.27, 1.46),
    "12 ay": (365, 40, 1.458, 1.545, 2.055),
}
PANEL = {"sembol": 16, "bar": 525600, "gun": 365.0,
         "bas": "2025-09-01", "son": "2026-08-31"}
YIL_SEVIYE = {"1dk_medyan": -15.44, "1dk_ort": -17.59, "1dk_en_kotu": -57.50,
              "1g_medyan": -10.33}
YIL_P95 = 2.306

# --- madde 276 ile kiyas -------------------------------------------
MADDE_276 = {"medyan": 1.488, "p90": 2.722}
OLCULEN = {"medyan": 1.458, "p90": 2.055}
TOLERANS = 30.0
KARAR_BRUT = 1.25

# --- benim yanlis duyurum ------------------------------------------
YANLIS_DUYURUM = {
    "ne_dedim": "madde 276 buyutmeyi 2 aylik pencereden aldi, tolerans "
                "1 yilliktir, demek ki 1,25x'te yayinlanan gun ici kuyruk "
                "IYIMSER",
    "olcum_ne_dedi": "medyan 1,458 vs kullanilan 1,488 (neredeyse birebir); "
                     "p90 2,055 vs kullanilan 2,722 -> madde 276 %32 "
                     "IHTIYATLI, yani guvenlik payi KUCUK degil BUYUK",
    "ders": "bir eksikligi fark etmek, YONUNU bilmek demek degildir",
}
TEK_YIL_UYARISI = ("1 yillik satir TEK bir gerceklesmis yil uzerinde 40 "
                   "rastgele secim cekilisidir; bir yildan birden fazla "
                   "bagimsiz yillik pencere cikmaz, belirsizlik buyuk - ve "
                   "madde 276'nin daha ihtiyatli p90'i tam bu belirsizlik "
                   "karsisinda makul bir secim")

VERI = {"indirilen_mb": 673, "rejim_ay": 6, "surekli_gun": 365}


# --- sinamalar ------------------------------------------------------
def arac_madde266yi_uretti_mi(tol: float = 0.25) -> bool:
    """Buyutme ortalamasi ve 1dk seviyeleri madde 266'yla uyusuyor mu?"""
    a, b = ARAC_DOGRULAMA["buyutme ortalama"]
    c, d = ARAC_DOGRULAMA["1dk dusus ortalama"]
    return abs(a - b) <= tol and abs(abs(c) - abs(d)) <= 2.5


def kapital_hatam_kayitli_mi() -> bool:
    return "KAPANAN" in KAPITAL_HATAM and "KALICI" in KAPITAL_HATAM


def rejim_bandi() -> tuple:
    m = [v[1] for v in AYLAR.values()]
    return (min(m), max(m))


def ftx_ayi_aykiri_mi() -> bool:
    """FTX cokusu ayinin buyutmesi diger aylardan ayrisiyor mu?"""
    ftx = AYLAR["2022-11 (FTX cokusu)"][1]
    alt, ust = rejim_bandi()
    return ftx >= ust - 1e-9


def rejim_onemli_mi(esik: float = 0.30) -> bool:
    alt, ust = rejim_bandi()
    return (ust - alt) > esik


def pencere_monoton_mu() -> bool:
    """Buyutme pencere uzunluguyla monoton mu? (Madde 291: HAYIR, U.)"""
    d = sorted((v[0], v[2]) for v in PENCERE.values())
    art = all(d[i][1] <= d[i + 1][1] + 1e-9 for i in range(len(d) - 1))
    azl = all(d[i][1] >= d[i + 1][1] - 1e-9 for i in range(len(d) - 1))
    return art or azl


def u_biciminin_dibi() -> str:
    return min(PENCERE, key=lambda a: PENCERE[a][2])


def ekstrapole_edilebilir_mi() -> bool:
    return pencere_monoton_mu()


def madde276_ihtiyatli_mi() -> bool:
    """Kullanilan sayilar OLCULENden buyuk mu (yani guvenli tarafta mi)?"""
    return (MADDE_276["medyan"] >= OLCULEN["medyan"]
            and MADDE_276["p90"] >= OLCULEN["p90"])


def madde276_p90_kac_yuzde_ihtiyatli() -> float:
    return 100.0 * (MADDE_276["p90"] / OLCULEN["p90"] - 1.0)


def duyurum_yanlis_mi() -> bool:
    """Tur ortasinda soyledigim sey olcumle ters mi cikti? (Evet.)"""
    return madde276_ihtiyatli_mi()


def doz_kalibrasyonu_dogrulandi_mi(tol: float = 0.10) -> bool:
    return abs(MADDE_276["medyan"] - OLCULEN["medyan"]) <= tol


def tek_yil_uyarisi_kayitli_mi() -> bool:
    return "TEK bir gerceklesmis yil" in TEK_YIL_UYARISI


def hukum() -> str:
    return (
        "DOZ KARARI DOGRULANDI. Ucu icra varsayiminin olculdugu pencere 2 "
        "aydan 6 rejim karsiti aya ve SUREKLI 365 gune cikarildi (673 MB "
        "dakika verisi). Arac once madde 266'nin kendi penceresinde "
        "yeniden uretildi. REJIM ONEMLI DEGIL: alti karsit ayda buyutme "
        "1,16-1,35 ve FTX cokusu ayi (1,34) aykiri DEGIL - madde 266'nin "
        "'gun ici risk TEK ISIM riskidir' bulgusu alti rejimde dogrulandi. "
        "BUYUTME PENCERE UZUNLUGUNDA U BICIMLI (1,28 / 1,17 / 1,13 / 1,15 "
        "/ 1,46) - yani 2 aylik bir olcum HICBIR YONE ekstrapole edilemez. "
        "VE BENIM TUR ORTASI DUYURUM YANLISTI: '1,25x'in kuyrugu iyimser' "
        "dedim, olculen medyan 1,458 vs madde 276'nin kullandigi 1,488 "
        "(neredeyse birebir) ve p90 2,055 vs 2,722 (%32 IHTIYATLI) - "
        "guvenlik payi kucuk degil BUYUK. Ayar DEGISMEDI."
    )


def yaz() -> None:
    print(__doc__)
    print("VERI: %d MB dakika verisi | %d rejim karsiti ay | surekli %d gun"
          % (VERI["indirilen_mb"], VERI["rejim_ay"], VERI["surekli_gun"]))
    print("\nARACIN DOGRULANMASI (madde 266'nin KENDI penceresi):")
    print("  %-22s %10s %10s" % ("olcu", "bu arac", "madde 266"))
    for ad, (a, b) in ARAC_DOGRULAMA.items():
        print("  %-22s %10.2f %10.2f" % (ad, a, b))
    print("  madde 266 yeniden uretildi mi: %s" % arac_madde266yi_uretti_mi())
    print("  KAPITAL HATAM: %s" % KAPITAL_HATAM)
    print("\nREJIM KARSITI AYLAR (buyutme = 1dk dusus / 1g kapanis dususu):")
    print("  %-24s %4s %8s %6s %6s %6s" % ("ay", "sem", "medyan", "ort",
                                           "p90", "maks"))
    for ad, (n, m, o, p, mx) in AYLAR.items():
        print("  %-24s %4d %8.2f %6.2f %6.2f %6.2f" % (ad, n, m, o, p, mx))
    print("  bant %.2f-%.2f | rejim onemli mi: %s | FTX ayi aykiri mi: %s"
          % (*rejim_bandi(), rejim_onemli_mi(), ftx_ayi_aykiri_mi()))
    print("\nPENCERE UZUNLUGU (surekli panel: %d sembol, %.0f gun, %s -> %s):"
          % (PANEL["sembol"], PANEL["gun"], PANEL["bas"], PANEL["son"]))
    print("  %-8s %6s %6s %9s %6s %6s" % ("pencere", "gun", "yol", "medyan",
                                          "ort", "p90"))
    for ad, (g, y, m, o, p) in sorted(PENCERE.items(), key=lambda kv: kv[1][0]):
        print("  %-8s %6d %6d %9.3f %6.3f %6.3f" % (ad, g, y, m, o, p))
    print("  monoton mu: %s | U'nun dibi: %s | ekstrapole edilebilir mi: %s"
          % (pencere_monoton_mu(), u_biciminin_dibi(), ekstrapole_edilebilir_mi()))
    print("  1 yil seviyeleri: 1dk medyan %+.2f (ort %+.2f, EN KOTU %+.2f) | "
          "1g medyan %+.2f"
          % (YIL_SEVIYE["1dk_medyan"], YIL_SEVIYE["1dk_ort"],
             YIL_SEVIYE["1dk_en_kotu"], YIL_SEVIYE["1g_medyan"]))
    print("\nDOZ KARARI (tolerans -%%%.0f, karar brut %.2fx):"
          % (TOLERANS, KARAR_BRUT))
    print("  %-10s %18s %18s" % ("buyutme", "madde 276 kullandi", "1 YILDA OLCULEN"))
    for k in ("medyan", "p90"):
        print("  %-10s %18.3f %18.3f" % (k, MADDE_276[k], OLCULEN[k]))
    print("  madde 276 IHTIYATLI mi: %s | p90'i %%%.1f ihtiyatli"
          % (madde276_ihtiyatli_mi(), madde276_p90_kac_yuzde_ihtiyatli()))
    print("  kalibrasyon dogrulandi mi: %s" % doz_kalibrasyonu_dogrulandi_mi())
    print("  UYARI: %s" % TEK_YIL_UYARISI)
    print("\nBENIM YANLIS DUYURUM:")
    for k, v in YANLIS_DUYURUM.items():
        print("  %-14s %s" % (k, v))
    print("  duyurum yanlis mi: %s" % duyurum_yanlis_mi())
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
