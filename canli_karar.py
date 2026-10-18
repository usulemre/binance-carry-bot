"""MADDE 260: ON KAYITLI CANLI KARAR KURALI - gucle kapili, kod olarak.

Proje backtest kararini madde 212'de ON KAYITLI KOD yapti: `gecer_mi()`
yorumlanmaz, kosulur. **Canli karar hic bu hale getirilmemisti.**
`carry_izleme.py` zengin teshis basiyor ve esikleri biliyor, ama `main()`
her halde 0 ile cikiyor - yani gozetimsiz bir 14. gun kontrolu ona karar
baglayamaz; insan okumak zorunda. Madde 217'nin dersi tam buydu: BAYAT
TALIMAT, BAYAT AYARDAN TEHLIKELIDIR - ayari kod denetler, talimati kimse
denetlemez.

Bu modul canli kararin `gecer_mi()`'sidir.

================================================================
1) ASIL YENILIK: GUCLE KAPILI OLCUTLER
================================================================
Madde 216 her canli gozlemin TESPIT GUCUNU olctu. Bir olcut, gucu yeterli
OLMADAN karar verdirmemelidir - yoksa saglikli bir kitabi gurultuyle
durdurursunuz (madde 234'un dersi: saglik kapisi kitabi EN IYI doneminde
kapatacakti).

  gozlem              14 gun  30 gun  60 gun   BAGLAYICI
  funding tahsilati     %100    %100    %100   **14. gunden**
  TP orani LONG          %72     %95    %100   **30. gunden**
  TP orani SHORT         %42     %68     %91   **60. gunden**
  toplam getiri            -     %15       -   **ASLA**

**TOPLAM GETIRI HICBIR ZAMAN KARAR OLCUTU DEGILDIR.** Madde 151 onu 30
gunde %15 guc olarak olctu. Bu kuralin en onemli maddesi, cunku insanin
ilk bakacagi sey tam olarak odur.

Guc esigi: %80. Bir olcut ancak o ufukta gucu >=%80 ise DURDUR/INCELE
verdirebilir; altinda yalnizca BILGI olarak raporlanir.

================================================================
2) DUSUS ZARFI - UFKA GORE (bu turda olculdu)
================================================================
Mevcut alarm esikleri (-%18 INCELE / -%23 DURDUR) madde 231'de 1 YILLIK
p5/p1'den kalibre edilmisti. 14. gunde o esikleri uygulamak farkli bir
sey: madde 243'un SIRALAMA testiyle (ayni gunluk getiriler, siralama
rastgele - cunku gerceklesen yol sansli bir siralama, %84'luk yuzdelik)
20.000 ornek:

  ufuk   P(dd<=-18%)  P(dd<=-23%)   ort dd   p95 dd
  14 gun      %0,00        %0,00     %3,2     %7,0
  30 gun      %0,14        %0,01     %5,0    %10,4
  60 gun      %0,83        %0,12     %6,9    %13,4
  90 gun      %2,13        %0,33     %8,2    %15,3
  180 gun     %5,53        %1,11    %10,5    %18,4
  365 gun     %12,09       %2,81    %13,0    %21,1

365 gun satiri madde 243'un %11,1 / %2,2'sini teyit ediyor (ornekleme
gurultusu icinde) - yontem dogrulandi.

IKI SONUC:
(a) -18/-23 esikleri erken donemde SESSIZDIR: 14. gunde saglikli kitabin
    -18'e inme olasiligi ~%0. Yani erken bir -18, gurultu DEGIL, GERCEK
    ariza isaretidir. Bu yuzden dusus olcutu 1. GUNDEN BAGLAYICIDIR -
    performans olcutu degil, RISK korumasidir.
(b) Ama -18'i beklemek erken donemde cok gec: p95 sutunu daha erken bir
    ray veriyor. 14 gunde saglikli kitabin en kotu dususu %95 olasilikla
    <=%7,0. Bu yuzden EK bir ERKEN UYARI rayi tanimlandi: dusus, o ufkun
    p95'ini asarsa INCELE (durdurma degil - %5 yanlis tetikleme kabul).

================================================================
3) SARTLAR
================================================================
L1  FUNDING TAHSILATI (14. gunden baglayici, guc %100)
    gunluk tahsilat / BEKLENEN_FUNDING_TABAN(0,000653) orani:
      < %50  -> DURDUR  (madde 232: API/hesap tarafinda sorun ara)
      < %80  -> INCELE
      >= %80 -> GECER
    Isaret negatifse (funding ODUYORUZ) -> DURDUR, ufuk ne olursa olsun.
    Bu sart isaret hatasini 8 saatte yakalar; guc kapisi beklemez.

L2  TP ORANI LONG (30. gunden baglayici, guc %95)
    gerceklesen/beklenen (BEKLENEN_TP_LONG=0,088):
      < %50 -> INCELE  (kâr motoru - madde 214 - calismiyor olabilir)
    DURDUR vermez: TP orani kesikli ve dusuk tabanli, tek basina
    durdurmaya yetmez.

L3  TP ORANI SHORT (60. gunden baglayici, guc %91) - ayni esik, INCELE.

L4  DUSUS ZARFI (1. GUNDEN baglayici - RISK korumasi)
      dusus >= %23        -> DURDUR
      dusus >= %18        -> INCELE
      dusus > o ufkun p95 -> INCELE (erken uyari rayi)

L5  TOPLAM GETIRI - **ASLA KARAR OLCUTU DEGIL** (madde 151: %15 guc).
    Yalnizca bilgi olarak raporlanir. Bu sart, kuralin VAR OLMA
    sebeplerinden biridir.

HUKUM: en siddetli sart ne derse o. DURDUR > INCELE > DEVAM.
Cikis kodu: 0 DEVAM · 1 INCELE · 2 DURDUR (gozetimsiz kosum icin).

================================================================
4) NE YAPMAZ
================================================================
Bu modul VERI TOPLAMAZ - `carry_izleme.py` toplar. Burasi yalnizca
KARARDIR, tipki `karar_kurali.py`'nin backtest tarafinda oldugu gibi.
Boylece olcum ile karar ayri kalir ve karar test edilebilir.

Kosum: python3 canli_karar.py --ornek        (ornek senaryolar)
       python3 canli_karar.py --gun 14 --funding 0.00052 --dusus 4.1
"""
import argparse
import sys

# ---------------- madde 216'nin guc tablosu ----------------
GUC = {
    "funding tahsilati": {14: 100.0, 30: 100.0, 60: 100.0},
    "TP orani LONG": {14: 72.0, 30: 95.0, 60: 100.0},
    "TP orani SHORT": {14: 42.0, 30: 68.0, 60: 91.0},
    "toplam getiri": {30: 15.0},
}
GUC_ESIK = 80.0          # bir olcut ancak gucu >=%80 ise karar verdirir

# ---------------- olculmus beklentiler ----------------
BEKLENEN_FUNDING_TABAN = 0.000653      # en kotu rejim tabani (gun/sermaye)
BEKLENEN_FUNDING_GUNLUK = 0.001055     # harman
BEKLENEN_TP_LONG = 0.088
BEKLENEN_TP_SHORT = 0.181
DUSUS_INCELE = 18.0                    # puan, madde 231
DUSUS_DURDUR = 23.0                    # puan, madde 231

# ---------------- madde 260'ta olculen dusus zarfi ----------------
# ufuk: (P(dd<=-18%), P(dd<=-23%), ort dd, p95 dd) - hepsi YUZDE
DUSUS_ZARFI = {
    14: (0.00, 0.00, 3.2, 7.0),
    30: (0.14, 0.01, 5.0, 10.4),
    60: (0.83, 0.12, 6.9, 13.4),
    90: (2.13, 0.33, 8.2, 15.3),
    180: (5.53, 1.11, 10.5, 18.4),
    365: (12.09, 2.81, 13.0, 21.1),
}
MADDE_243_1YIL = (11.1, 2.2)           # teyit referansi

DEVAM, INCELE, DURDUR = "DEVAM", "INCELE", "DURDUR"
_SIDDET = {DEVAM: 0, INCELE: 1, DURDUR: 2}


def baglayici_gun(gozlem: str, esik: float = GUC_ESIK):
    """Bu gozlem kac gunden itibaren KARAR verdirebilir? (guc >= esik)"""
    g = GUC.get(gozlem, {})
    uygun = sorted(u for u, p in g.items() if p >= esik)
    return uygun[0] if uygun else None


def guc_tahmini(gozlem: str, gun: int):
    """gun'e en yakin ALT ufkun gucu (muhafazakar)."""
    g = GUC.get(gozlem, {})
    alt = [u for u in g if u <= gun]
    return g[max(alt)] if alt else None


def zarf(gun: int):
    """gun'e en yakin ALT ufkun dusus zarfi (muhafazakar)."""
    alt = [u for u in DUSUS_ZARFI if u <= gun]
    if not alt:
        return DUSUS_ZARFI[min(DUSUS_ZARFI)]
    return DUSUS_ZARFI[max(alt)]


def canli_gecer_mi(gun: int, funding_gunluk: float = None,
                   tp_long_oran: float = None, tp_short_oran: float = None,
                   dusus: float = None, toplam_getiri: float = None) -> dict:
    """ON KAYITLI CANLI KARAR. Doner: {'hukum', 'sartlar', 'bilgi'}.

    funding_gunluk : gunluk funding / sermaye (ORAN, ornek 0.00052)
    tp_*_oran      : gerceklesen TP orani (ORAN, ornek 0.071)
    dusus          : gerceklesen maks dusus, POZITIF PUAN (ornek 4.1)
    toplam_getiri  : yillik karsiligi, PUAN - YALNIZCA BILGI
    """
    s = {}
    bilgi = []

    # --- L1 funding tahsilati ---
    bg = baglayici_gun("funding tahsilati")
    if funding_gunluk is None:
        s["L1 funding tahsilati"] = (DEVAM, "olcum YOK")
    elif funding_gunluk < 0:
        s["L1 funding tahsilati"] = (
            DURDUR, "FUNDING ODUYORUZ (%.6f) - isaret ters olabilir; guc "
                    "kapisi beklenmez" % funding_gunluk)
    else:
        o = funding_gunluk / BEKLENEN_FUNDING_TABAN
        aciklama = ("tabanin %%%.0f'i (gunluk %.6f vs taban %.6f)"
                    % (o * 100, funding_gunluk, BEKLENEN_FUNDING_TABAN))
        if gun < bg:
            s["L1 funding tahsilati"] = (
                DEVAM, "%s - ama %d. gunden once BAGLAYICI DEGIL (guc %s)"
                       % (aciklama, bg, guc_tahmini("funding tahsilati", gun)))
        elif o < 0.50:
            s["L1 funding tahsilati"] = (DURDUR, aciklama + " - madde 232")
        elif o < 0.80:
            s["L1 funding tahsilati"] = (INCELE, aciklama)
        else:
            s["L1 funding tahsilati"] = (DEVAM, aciklama)

    # --- L2/L3 TP oranlari ---
    for ad, oran, bek in (("L2 TP orani LONG", tp_long_oran, BEKLENEN_TP_LONG),
                          ("L3 TP orani SHORT", tp_short_oran, BEKLENEN_TP_SHORT)):
        gz = ad.split(" ", 1)[1]
        bg2 = baglayici_gun(gz)
        if oran is None:
            s[ad] = (DEVAM, "olcum YOK")
            continue
        o = oran / bek
        aciklama = "beklenenin %%%.0f'i (%.3f vs %.3f)" % (o * 100, oran, bek)
        if bg2 is None or gun < bg2:
            s[ad] = (DEVAM, "%s - %s. gunden once BAGLAYICI DEGIL (guc %s)"
                            % (aciklama, bg2, guc_tahmini(gz, gun)))
        elif o < 0.50:
            s[ad] = (INCELE, aciklama + " - kâr motoru (madde 214)")
        else:
            s[ad] = (DEVAM, aciklama)

    # --- L4 dusus zarfi: 1. GUNDEN baglayici (risk korumasi) ---
    if dusus is None:
        s["L4 dusus zarfi"] = (DEVAM, "olcum YOK")
    else:
        p18, p23, ortalama, p95 = zarf(gun)
        if dusus >= DUSUS_DURDUR:
            s["L4 dusus zarfi"] = (
                DURDUR, "-%.1f puan >= -%.0f (bu ufukta saglikli kitapta "
                        "%%%.2f olasilik)" % (dusus, DUSUS_DURDUR, p23))
        elif dusus >= DUSUS_INCELE:
            s["L4 dusus zarfi"] = (
                INCELE, "-%.1f puan >= -%.0f (olasilik %%%.2f)"
                        % (dusus, DUSUS_INCELE, p18))
        elif dusus > p95:
            s["L4 dusus zarfi"] = (
                INCELE, "-%.1f puan, bu ufkun p95'ini (-%.1f) asiyor - ERKEN "
                        "UYARI rayi (%%5 yanlis tetikleme kabul)" % (dusus, p95))
        else:
            s["L4 dusus zarfi"] = (
                DEVAM, "-%.1f puan, zarf icinde (ort -%.1f / p95 -%.1f)"
                       % (dusus, ortalama, p95))

    # --- L5 toplam getiri: ASLA karar olcutu degil ---
    if toplam_getiri is not None:
        bilgi.append("toplam getiri %+.1f%%/yil - **KARAR OLCUTU DEGIL** "
                     "(madde 151: 30 gunde %%15 guc)" % toplam_getiri)
    s["L5 toplam getiri"] = (DEVAM, "tanim geregi BAGLAYICI DEGIL (madde 151)")

    hukum = max(s.values(), key=lambda t: _SIDDET[t[0]])[0]
    return {"hukum": hukum, "gun": gun, "sartlar": s, "bilgi": bilgi}


def cikis_kodu(h: dict) -> int:
    return _SIDDET[h["hukum"]]


def yaz(h: dict) -> None:
    print("=== ON KAYITLI CANLI KARAR (gun %d) ===" % h["gun"])
    for ad, (d, a) in h["sartlar"].items():
        im = {DEVAM: "  ", INCELE: "[!]", DURDUR: "[!!]"}[d]
        print("  %-3s %-22s%-7s %s" % (im, ad, d, a))
    for b in h["bilgi"]:
        print("  (bilgi) %s" % b)
    print("  %s\n  HUKUM: %s" % ("-" * 60, h["hukum"]))


ORNEKLER = [
    ("14. gun, her sey yerinde", dict(gun=14, funding_gunluk=0.00058,
                                      dusus=3.4, toplam_getiri=+58.0)),
    ("14. gun, funding YARIM", dict(gun=14, funding_gunluk=0.00030,
                                    dusus=3.1, toplam_getiri=+12.0)),
    ("14. gun, funding TERS", dict(gun=14, funding_gunluk=-0.00010, dusus=5.0)),
    ("14. gun, getiri NEGATIF ama funding tam",
     dict(gun=14, funding_gunluk=0.00071, dusus=6.2, toplam_getiri=-40.0)),
    ("14. gun, dusus p95 ustu", dict(gun=14, funding_gunluk=0.00070, dusus=9.1)),
    ("30. gun, TP LONG yarim", dict(gun=30, funding_gunluk=0.00070,
                                    tp_long_oran=0.030, dusus=4.8)),
    ("14. gun, TP LONG yarim (henuz BAGLAYICI DEGIL)",
     dict(gun=14, funding_gunluk=0.00070, tp_long_oran=0.030, dusus=4.8)),
    ("90. gun, dusus -19", dict(gun=90, funding_gunluk=0.00068, dusus=19.0)),
]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ornek", action="store_true", help="ornek senaryolari yaz")
    ap.add_argument("--gun", type=int, default=14)
    ap.add_argument("--funding", type=float, default=None,
                    help="gunluk funding / sermaye (oran)")
    ap.add_argument("--tp-long", type=float, default=None)
    ap.add_argument("--tp-short", type=float, default=None)
    ap.add_argument("--dusus", type=float, default=None, help="POZITIF puan")
    ap.add_argument("--getiri", type=float, default=None, help="yillik, puan")
    a = ap.parse_args()

    if a.ornek:
        print("MADDE 216'NIN GUC TABLOSU VE BAGLAYICI GUNLER\n")
        print("  %-22s%8s%8s%8s   %s"
              % ("gozlem", "14 gun", "30 gun", "60 gun", "BAGLAYICI"))
        for g in GUC:
            t = GUC[g]
            bg = baglayici_gun(g)
            print("  %-22s%8s%8s%8s   %s"
                  % (g, "%%%d" % t[14] if 14 in t else "-",
                     "%%%d" % t[30] if 30 in t else "-",
                     "%%%d" % t[60] if 60 in t else "-",
                     "%d. gunden" % bg if bg else "**ASLA**"))
        print("\nDUSUS ZARFI (madde 260, madde 243'un siralama testiyle)")
        print("  %-8s%13s%13s%10s%10s"
              % ("ufuk", "P(dd<=-18%)", "P(dd<=-23%)", "ort dd", "p95 dd"))
        for u, (a18, a23, o, p) in DUSUS_ZARFI.items():
            print("  %-8d%12.2f%%%12.2f%%%9.1f%%%9.1f%%" % (u, a18, a23, o, p))
        print("  (365 satiri madde 243'un %%%.1f / %%%.1f'ini teyit eder)"
              % MADDE_243_1YIL)
        print("\nORNEK SENARYOLAR\n")
        for ad, kw in ORNEKLER:
            print("--- %s" % ad)
            yaz(canli_gecer_mi(**kw))
            print()
        return 0

    h = canli_gecer_mi(a.gun, a.funding, a.tp_long, a.tp_short, a.dusus, a.getiri)
    yaz(h)
    return cikis_kodu(h)


if __name__ == "__main__":
    sys.exit(main())
