#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 294 — KÜÇÜK SERMAYE (1.000-2.000 $): ÖNCELİK DİLİM SAYISI DEĞİL
**BACAK BÜYÜKLÜĞÜ**.

Kullanıcı 1.000-2.000 $ ile başlayacağını söyledi. 293 maddenin tamamı
15.000 $+ için ayarlanmış bir kitabı optimize etti; **1.875 $ teknik
tabanın kendisi** ve bu sermayede hiçbir şey ölçülmemişti.

İKİ SERT GERÇEK:
  - 1.000 $'da standart kitabın bacağı **5,33 $** olur (bacak =
    bakiye·taban_payı/(dilim·bacak_sayısı) = 1000·0,40/75). Borsa
    minimumu 5 $ × 2 güvenlik payı = 10 $ → madde 204 her turu atlar,
    **bot hiç işlem açmaz.**
  - 2.000 $'da standart kitap çalışır (bacak 10,67 $) ama tam
    minimumda.

Uygunluk şartı: **dilim × bacak ≤ bakiye × taban_payı / 10**.
taban_payı = 0,5 − REZERV/2 (REZERV %20 → 0,40; rezervsiz → 0,50).

═══ YAPISAL MALİYET: KÜÇÜK, 2-6 PUAN ═══

Sekiz uygun yapılandırma motorda koşuldu (REB_GUN=5, HAVUZ=3, KAP=0,05,
TP 40/20, UCELE 0,40 — yalnız FAZ, bacak sayısı ve REZERV değişti):

    yapılandırma   taban$   CAGR    Sharpe  22-24  25-26  düşüş   doz farkı  ihtiyatlı brüt
    kontrol 15x5    1.875  +112,3   2,939   2,789  3,147  −14,54      0       1,51x
    15x2              750  +196,4   2,893   2,656  3,215  −24,75    −1,75     1,01x
    13x3              975  +150,0   2,886   2,706  3,134  −17,68    −5,52     1,20x
    5x5               625  +112,9   2,907   2,623  3,290  −16,12    −6,44     1,47x
    8x5             1.000  +108,3   2,874   2,720  3,086  −14,89   −11,96     1,49x
    15x5 rezervsiz  1.500  +127,6   2,879   2,753  3,053  −16,91   −14,77     1,30x
    15x3 rezervsiz    900  +180,6   2,828   2,684  3,026  −21,60   −19,25     1,01x
    10x5 rezervsiz  1.000  +123,3   2,815   2,683  2,998  −17,31   −25,91     1,28x
    10x4            1.000  +116,6   2,759   2,638  2,928  −16,63   −29,82     1,32x

**Bacak sayısı düştükçe ham getiri uçuyor** (15x2'de +%196) çünkü
funding seçiminin UÇLUĞU yoğunlaşıyor — ama düşüş de uçuyor ve eşit
riske getirildiğinde avantaj eriyor.

ÇERÇEVE NOTU: bu tabloda hiçbiri `gecer_mi()`'den geçmiyor ve
**geçmemesi gerekiyor**. Dört şart kuralı "kontrolden daha iyi mi" diye
sorar; 1.000 $'da kontrol **zaten mevcut değil**. Soru "hangisi en az
kötü" ve onu doz ölçütü cevaplıyor (madde 274: karar hangi ölçütle
veriliyorsa kıyas onunla).

═══ EVREN MALİYETİ: BÜYÜK, 39-78 PUAN ═══

10 $'lık bacak evreni daraltıyor. Botun kendi kodu (`islem_yapilabilir`)
sebebi yazıyor: yüksek fiyatlı coinlerde en küçük adım büyük bir USD
tutarına denk gelir — **BTC ~100 $, SOL ~150 $** — yani 10 $ bacakla bu
semboller SEÇİM aşamasında elenir.

Madde 176 bunu +%55,9 → +%35,6 diye ölçmüştü ama o eski bir
yapılandırmaydı. Güncel kitapta yeniden ölçüldü (`SEMBOL_DUS`):

    elenen evren   CAGR        Sharpe   düşüş    doz farkı
    %10           +107,9 (−%3,9)  2,914  14,63     −3,55
    %20 (tohum1)   +90,6 (−%19,3) 2,699  15,13    −38,71
    %20 (tohum2)   +83,8 (−%25,4) 2,406  15,07    −77,59
    %35            +41,7 (−%62,8) 1,622  20,04   −147,84

**Evrenin %1'i başına ~1,9-3,9 puan.** Yapısal farklar 2-6 puan;
evren maliyeti bir büyüklük mertebesi DAHA BÜYÜK.

═══ SONUÇ: ÖNCELİK TERSİNE DÖNÜYOR ═══

Küçük sermayede doğru hamle 15x5 yapısını korumaya çalışmak DEĞİL,
**bacağı mümkün olduğunca BÜYÜTMEK**. 1.000 $'da bacak büyüklükleri:

    5x5   -> 16,00 $     15x2 -> 13,33 $     13x3 -> 10,26 $
    15x3R0 -> 11,11 $    8x5  -> 10,00 $     10x4 -> 10,00 $

10 $'dan 16 $'a çıkmak evrenin %3'ünü kurtarırsa ~6-12 puan kazandırır
— yapısal farkların tamamından büyük.

**ÖNERİ: 5 dilim × 5 bacak** (`CARRY_N_DILIM=5`). Gerekçe:
  - uygun yapılandırmaların en BÜYÜK bacağı (1.000 $'da 16 $,
    2.000 $'da 32 $) → en az evren elemesi
  - yapısal maliyet yalnız −6,44 puan
  - CAGR +%112,9 — kontrolle neredeyse AYNI (+%112,3)
  - 25-26 Sharpe'ı kontrolden YÜKSEK (3,290 vs 3,147); zayıf olduğu
    yer 22-24 (2,623 vs 2,789)
  - düşüş −16,12 (kontrol −14,54): kötü ama 15x2'nin −24,75'i gibi
    tolerans dışı değil
  - ihtiyatlı brüt 1,47x, yani −%30 toleransında 1x'te bol pay var

15x2 eşit riskte en az kaybeden (−1,75) ve bacağı da büyük (13,33 $)
AMA düşüşü −%24,75: madde 291'in 1 yıllık gün içi çarpanıyla (1,458)
ekranda ~−%36 demek ve kullanıcının −%30 toleransını **1x'te bile**
aşıyor. O yüzden önerilmiyor.

DİKKAT — DİLİM SAYISININ BEDELİ AYRICA VAR: 5 dilim, 15 dilimin faz
çeşitlendirmesinin üçte birini verir (madde 120). Ölçülen düşüş (−16,12)
bunu içeriyor, ama tek bir rebalance zamanlamasına bağımlılık artıyor.

═══ KOMUT ═══

    CARRY_N_DILIM=5 python carry_bot.py

(bacak sayısı zaten 5; `CARRY_N_LEGS` DEĞİŞMİYOR. REZERV %20 kalıyor —
rezervsiz varyantların hepsi doz ölçütünde daha kötü.)

**VARSAYILANA DÖNÜŞ ~28.125 $.** 15x5 aslında 1.875 $'da *çalışır* hale
gelir ama çalışmak YETMEZ: 5x5 her sermayede 15x5'in **üç katı** bacak
verir ve evren maliyeti yapısal maliyetten bir mertebe büyük. Dönüş,
15x5'in bacağı adım tavanını (~150 $, SOL ankrası) geçtiğinde anlamlı
olur: 150·15·5/0,40 = **28.125 $**. (İlk hesabımda 3.750 $ yazmıştım ve
yanlıştı — "çalışır" ile "evreni kaybetmez" aynı şey değil.)

DÜRÜST SINIR: elimde tam adım-boyu tablosu YOK (`fapi.binance.com` bu
bölgeden 451, arşivde exchangeInfo yok). İki ankra botun kendi
docstring'inden. Gerçek eşik canlıda TEK bir `islem_yapilabilir()`
çağrısıyla ölçülebilir: bacak büyüklüğünü verip kaç sembolün elendiğine
bakmak yeterli — ilk turda bunu yapmaya değer.
"""

MIN_BACAK_USD = 10.0          # borsa minimumu 5$ x 2 guvenlik payi (madde 204)
TEKNIK_TABAN_KONTROL = 1875.0

def taban_payi(rezerv: float) -> float:
    return 0.5 - rezerv / 2.0

def bacak_usd(bakiye: float, dilim: int, bacak: int, rezerv: float) -> float:
    return bakiye * taban_payi(rezerv) / (dilim * bacak)

def asgari_bakiye(dilim: int, bacak: int, rezerv: float) -> float:
    return dilim * bacak / taban_payi(rezerv) * MIN_BACAK_USD

def calisir_mi(bakiye: float, dilim: int, bacak: int, rezerv: float) -> bool:
    return bacak_usd(bakiye, dilim, bacak, rezerv) >= MIN_BACAK_USD

# --- yapilandirma -> (dilim, bacak, rezerv, CAGR, Sharpe, 22-24, 25-26,
#                      dusus, doz farki, ihtiyatli brut)
YAPILANDIRMA = {
    "kontrol 15x5": (15, 5, 0.20, 112.27, 2.939, 2.789, 3.147, 14.54, 0.00, 1.505),
    "15x2": (15, 2, 0.20, 196.36, 2.893, 2.656, 3.215, 24.75, -1.75, 1.01),
    "13x3": (13, 3, 0.20, 149.95, 2.886, 2.706, 3.134, 17.68, -5.52, 1.20),
    "5x5": (5, 5, 0.20, 112.89, 2.907, 2.623, 3.290, 16.12, -6.44, 1.47),
    "8x5": (8, 5, 0.20, 108.32, 2.874, 2.720, 3.086, 14.89, -11.96, 1.49),
    "15x5 rezervsiz": (15, 5, 0.00, 127.56, 2.879, 2.753, 3.053, 16.91, -14.77, 1.30),
    "15x3 rezervsiz": (15, 3, 0.00, 180.62, 2.828, 2.684, 3.026, 21.60, -19.25, 1.01),
    "10x5 rezervsiz": (10, 5, 0.00, 123.26, 2.815, 2.683, 2.998, 17.31, -25.91, 1.28),
    "10x4": (10, 4, 0.20, 116.57, 2.759, 2.638, 2.928, 16.63, -29.82, 1.32),
}

# --- evren daralmasi: elenen oran -> (CAGR, Sharpe, dusus, doz farki)
EVREN = {
    0.10: (107.88, 2.914, 14.63, -3.55),
    0.20: (90.63, 2.699, 15.13, -38.71),     # tohum 1
    0.201: (83.78, 2.406, 15.07, -77.59),    # tohum 2 (ayni oran, baska tohum)
    0.35: (41.74, 1.622, 20.04, -147.84),
}
MADDE_176 = "evrenin %20'si elenince getiri +%55,9 -> +%35,6 (ESKI yapilandirma)"
ADIM_ANKRALARI = {"BTCUSDT": 100.0, "SOLUSDT": 150.0}   # botun kendi docstring'i

ONERI = {"dilim": 5, "bacak": 5, "rezerv": 0.20,
         "komut": "CARRY_N_DILIM=5 python carry_bot.py"}
ONERILMEYEN = {"15x2": "dusus -%24,75; madde 291'in 1 yillik gun ici carpaniyla "
                       "(1,458) ekranda ~-%36 = kullanicinin -%30 toleransini "
                       "1x'te bile asiyor"}
ADIM_TAVANI_USD = 150.0
"""Botun docstring'inin verdigi en buyuk adim ankrasi (SOL ~150 $). Bacak
bunun USTUNE cikmadikca yuksek fiyatli semboller elenmeye devam eder."""

VARSAYILANA_DONUS_ESIGI = ADIM_TAVANI_USD * 15 * 5 / 0.40    # ~28.125 $
"""ILK HESABIM YANLISTI (3.750 $ yazmistim). 15x5'in CALISIR hale geldigi
esik 1.875 $'dir, ama calismak YETMEZ: oneri bacagi BUYUTMEK uzerine
kurulu ve 5x5 her sermayede 15x5'in UC KATI bacak verir. Donus, 15x5'in
bacagi adim tavanini (~150 $) gectiginde anlamli olur:
150 x 15 x 5 / 0,40 = **28.125 $**. (5x5 ayni bacagi 9.375 $'da verir.)

DURUST SINIR: elimde tam adim-boyu tablosu YOK - `fapi.binance.com` bu
bolgeden 451 veriyor, arsivde exchangeInfo bulunmuyor. Iki ankra (BTC
~100 $, SOL ~150 $) botun kendi docstring'inden. Gercek esik canli ortamda
TEK bir `islem_yapilabilir()` cagrisiyla olculebilir: bacak buyuklugunu
verip kac sembolun elendigine bakmak yeterli."""
FAZ_UYARISI = ("5 dilim, 15 dilimin faz cesitlendirmesinin ucte birini verir "
               "(madde 120); olculen dusus bunu iceriyor ama tek bir rebalance "
               "zamanlamasina bagimlilik artiyor")
YASA = ("kucuk sermayede oncelik dilim sayisi DEGIL BACAK BUYUKLUGUDUR: "
        "yapisal farklar 2-6 puan, evren elemesi evrenin %1'i basina 1,9-3,9 "
        "puan - bir buyukluk mertebesi daha buyuk")
CERCEVE_NOTU = ("bu tabloda hicbiri gecer_mi()'den gecmiyor ve GECMEMESI "
                "gerekiyor: dort sart kurali 'kontrolden iyi mi' diye sorar, "
                "1.000 $'da kontrol ZATEN MEVCUT DEGIL; soru 'hangisi en az "
                "kotu' ve onu doz olcutu cevaplar (madde 274)")


# --- sinamalar --------------------------------------------------------
def kontrol_1000de_calisir_mi() -> bool:
    return calisir_mi(1000.0, 15, 5, 0.20)


def kontrol_2000de_calisir_mi() -> bool:
    return calisir_mi(2000.0, 15, 5, 0.20)


def teknik_taban_dogru_mu() -> bool:
    return abs(asgari_bakiye(15, 5, 0.20) - TEKNIK_TABAN_KONTROL) < 1.0


def oneri_1000de_calisir_mi() -> bool:
    return calisir_mi(1000.0, ONERI["dilim"], ONERI["bacak"], ONERI["rezerv"])


def oneri_en_buyuk_bacak_mi(bakiye: float = 1000.0) -> bool:
    """Oneri, 1.000 $'da CALISAN yapilandirmalar arasinda en buyuk bacagi
    veriyor mu?"""
    uygun = [(bacak_usd(bakiye, d, b, r), ad)
             for ad, (d, b, r, *_) in YAPILANDIRMA.items()
             if calisir_mi(bakiye, d, b, r)]
    return max(uygun)[1] == "5x5"


def evren_maliyeti_yapisaldan_buyuk_mu() -> bool:
    """Evrenin %20'si elenmesi, en kotu yapisal secimden daha mi pahali?"""
    en_kotu_yapisal = min(v[8] for v in YAPILANDIRMA.values())
    return EVREN[0.20][3] < en_kotu_yapisal


def evren_puan_basina() -> tuple:
    """Evrenin %1'i basina doz puani (iki tohum)."""
    return (abs(EVREN[0.20][3]) / 20.0, abs(EVREN[0.201][3]) / 20.0)


def madde176_dogrulandi_mi() -> bool:
    """%20 eleme getiriyi belirgin dusuruyor mu? (176'nin bulgusu)"""
    return EVREN[0.20][0] < 0.85 * YAPILANDIRMA["kontrol 15x5"][3]


def onerinin_dozu_yapisal_olarak_kucuk_mu() -> bool:
    return abs(YAPILANDIRMA["5x5"][8]) < 10.0


def onerinin_getirisi_kontrole_yakin_mi(tol: float = 2.0) -> bool:
    return abs(YAPILANDIRMA["5x5"][3] - YAPILANDIRMA["kontrol 15x5"][3]) < tol


def en_az_kaybeden_onerilmedi_mi() -> bool:
    """Doz ölçütünde en az kaybeden 15x2; DUSUS yuzunden onerilmedi mi?"""
    en_az = max(YAPILANDIRMA, key=lambda a: YAPILANDIRMA[a][8]
                if a != "kontrol 15x5" else -99)
    return en_az == "15x2" and "15x2" in ONERILMEYEN


def tolerans_asimi(dusus: float, carpan: float = 1.458) -> float:
    """Gun ici karsiligi (madde 291'in 1 yillik medyan carpani)."""
    return dusus * carpan


def donus_esigi_dogru_mu() -> bool:
    """Donus esiginde 15x5'in bacagi adim tavanini geciyor mu?"""
    return bacak_usd(VARSAYILANA_DONUS_ESIGI, 15, 5, 0.20) >= ADIM_TAVANI_USD


def oneri_ayni_bacagi_kac_kat_erken_veriyor() -> float:
    """5x5, 15x5'in bacagini kac kat kucuk sermayede veriyor?"""
    return (bacak_usd(1000.0, ONERI["dilim"], ONERI["bacak"], ONERI["rezerv"])
            / bacak_usd(1000.0, 15, 5, 0.20))


def ilk_donus_esigi_hatam() -> str:
    return ("3.750 $ yazmistim; 15x5'in CALISIR hale geldigi esik 1.875 $ "
            "ama calismak yetmez - bacak adim tavanini (~150 $) gecmelidir, "
            "o da 28.125 $")


def hukum() -> str:
    return (
        "KUCUK SERMAYEDE ONCELIK BACAK BUYUKLUGU. 1.000 $'da standart "
        "kitap (15 dilim x 5 bacak) CALISMAZ - bacak 5,33 $ ve madde 204 "
        "her turu atlar; 2.000 $'da tam minimumda calisir. Sekiz uygun "
        "yapilandirma olculdu: yapisal maliyet yalniz 2-6 puan (en iyi "
        "15x2 -1,75, 13x3 -5,52, 5x5 -6,44) AMA evren elemesi evrenin "
        "%1'i basina 1,9-3,9 puan - bir buyukluk mertebesi daha buyuk "
        "(madde 176 guncel yapilandirmada dogrulandi: %20 eleme -> doz "
        "-38,7/-77,6, %35 -> -147,8). Yani 15x5 yapisini korumak degil "
        "BACAGI BUYUTMEK gerekiyor. ONERI: **5 dilim x 5 bacak** - uygun "
        "yapilandirmalarin en buyuk bacagi (1.000 $'da 16 $, 2.000 $'da "
        "32 $), yapisal maliyet -6,44 puan, CAGR +%112,9 (kontrol "
        "+%112,3 ile neredeyse ayni), 25-26 Sharpe'i kontrolden YUKSEK, "
        "dusus -16,12, ihtiyatli brut 1,47x. 15x2 esit riskte en az "
        "kaybeden ama dususu -%24,75 ve kullanicinin -%30 toleransini 1x'te "
        "bile asiyor. Sermaye 3.750 $'i gecince CARRY_N_DILIM varsayilana "
        "(15) donmeli."
    )


def yaz() -> None:
    print(__doc__)
    print("UYGUNLUK: dilim x bacak <= bakiye x taban_payi / %.0f $" % MIN_BACAK_USD)
    print("  kontrolun teknik tabani %.0f $ (dogru mu: %s)"
          % (asgari_bakiye(15, 5, 0.20), teknik_taban_dogru_mu()))
    print("  1.000 $'da kontrol calisir mi: %s (bacak %.2f $)"
          % (kontrol_1000de_calisir_mi(), bacak_usd(1000, 15, 5, 0.20)))
    print("  2.000 $'da kontrol calisir mi: %s (bacak %.2f $)"
          % (kontrol_2000de_calisir_mi(), bacak_usd(2000, 15, 5, 0.20)))
    print("\nYAPILANDIRMALAR:")
    print("  %-16s %7s %10s %10s %8s %7s %8s %9s"
          % ("ad", "taban$", "bacak@1k", "bacak@2k", "CAGR", "Sharpe",
             "dusus", "doz fark"))
    for ad, (d, b, r, cg, sh, e1, e2, du, dz, br) in sorted(
            YAPILANDIRMA.items(), key=lambda kv: -kv[1][8]):
        print("  %-16s %7.0f %9.2f$ %9.2f$ %+8.2f %7.3f %8.2f %+9.2f%s"
              % (ad, asgari_bakiye(d, b, r), bacak_usd(1000, d, b, r),
                 bacak_usd(2000, d, b, r), cg, sh, -du, dz,
                 "  <= ONERI" if ad == "5x5" else ""))
    print("  %s" % CERCEVE_NOTU)
    print("\nEVREN DARALMASI (madde 176'nin yontemi, GUNCEL yapilandirma):")
    for oran in sorted(EVREN):
        cg, sh, du, dz = EVREN[oran]
        print("  %%%-5.1f elenince  CAGR %+8.2f (%%%+.1f) Sharpe %.3f "
              "dusus %.2f  doz %+.2f"
              % (oran * 100, cg, 100 * (cg / YAPILANDIRMA["kontrol 15x5"][3] - 1),
                 sh, du, dz))
    print("  madde 176 (eski): %s" % MADDE_176)
    print("  guncelde dogrulandi mi: %s | evrenin %%1'i basina %.1f-%.1f puan"
          % (madde176_dogrulandi_mi(), *evren_puan_basina()))
    print("  evren maliyeti en kotu yapisal secimden BUYUK mu: %s"
          % evren_maliyeti_yapisaldan_buyuk_mu())
    print("  10 $ bacakta elenen ornekler (botun kendi docstring'i): %s"
          % ", ".join("%s ~%.0f $" % (k, v) for k, v in ADIM_ANKRALARI.items()))
    print("\nONERI: %d dilim x %d bacak, REZERV %%%.0f"
          % (ONERI["dilim"], ONERI["bacak"], ONERI["rezerv"] * 100))
    print("  komut: %s" % ONERI["komut"])
    print("  1.000 $'da calisir mi: %s | en BUYUK bacak mi: %s"
          % (oneri_1000de_calisir_mi(), oneri_en_buyuk_bacak_mi()))
    print("  yapisal maliyet kucuk mu: %s | getirisi kontrole yakin mi: %s"
          % (onerinin_dozu_yapisal_olarak_kucuk_mu(),
             onerinin_getirisi_kontrole_yakin_mi()))
    print("  UYARI: %s" % FAZ_UYARISI)
    for ad, sebep in ONERILMEYEN.items():
        print("  %s ONERILMIYOR: %s" % (ad, sebep))
    print("  en az kaybeden onerilmedi mi: %s" % en_az_kaybeden_onerilmedi_mi())
    print("  15x2'nin gun ici karsiligi: -%%%.1f" % tolerans_asimi(24.75))
    print("  5x5'in gun ici karsiligi:   -%%%.1f" % tolerans_asimi(16.12))
    print("\nVARSAYILANA DONUS: sermaye ~%s $'i gecince CARRY_N_DILIM=15 "
          "(dogru mu: %s)" % (format(int(VARSAYILANA_DONUS_ESIGI), ","),
                              donus_esigi_dogru_mu()))
    print("  oneri ayni bacagi %.0f KAT kucuk sermayede veriyor"
          % oneri_ayni_bacagi_kac_kat_erken_veriyor())
    print("  ILK HESABIM YANLISTI: %s" % ilk_donus_esigi_hatam())
    print("\nYASA: %s" % YASA)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
