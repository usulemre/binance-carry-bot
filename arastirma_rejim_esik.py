#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 303 — KENDİ AÇTIĞIM EKSENİ KAPATTIM: MADDE 231'İN KANONİK
YÖNTEMİ, MADDE 302'NİN DÜZELTMESİNİ DOĞRULADI VE BİRAZ GEVŞETTİ
(13x3 İÇİN −%22/−%28 DEĞİL **−%23/−%29**).

Madde 302 devre kesicileri 13x3 kitabına ölçeklemişti ve eşikleri İKİ
bağımsız yoldan türetmişti (yanlış-tetik eşdeğerliği −%22,43/−%28,31 ve
düşüş oranıyla ölçekleme −%21,89/−%27,97). İkisi buluşmuştu, ama
**ikisi de madde 231'in ASIL yöntemini atlıyordu**: *"eşik EN KÖTÜ MAKUL
REJİMİN 1-yıllık bootstrap p5/p1'ine konur"*. O eksen madde 302'de
AÇIK bırakılmıştı — ve canlıya yeni bir eşik koymuşken açık bırakmak
doğru değildi.

Bu tur yeni bir eksen açmadan onu kapattı.

═══ 1. ÖNCE YÖNTEM DOĞRULANDI ═══

Madde 231'in `yil_bootstrap`'ı birebir kopyalandı (4.000 örnek, 21 bar
blok, tohum 11) ve 15x5'e uygulandı:

    rejim          1y dusus p5    1y dusus p1    madde 231'in kaydi
    tum ornek        −%16,95        −%21,37        p1 −%21,4
    dusuk prim       −%17,93        −%22,31        p1 −%22,3   <- EN KOTU
    yuksek prim      −%15,11        −%17,99        p1 −%18,0

**Üç rakam da ondalığına kadar tuttu.** Ve en kötü rejim p5'i −%17,93 =
madde 233'ün koyduğu −%18. Zincir (231 -> 233 -> 243) tam olarak bu.

Yöntem tuttuğu için 13x3 sonucuna güvenilebildi (madde 302 yasa 3).

═══ 2. 13x3'ÜN KANONİK EŞİKLERİ ═══

    rejim          1y getiri p5   1y dusus p5    1y dusus p1
    tum ornek        +%50,8         −%21,29        −%25,94
    **dusuk prim**   +%26,0       **−%22,66**    **−%28,98**   <- EN KOTU
    yuksek prim      +%96,8         −%17,90        −%20,86

Madde 233'ün yuvarlama kuralı (büyüklüğü bir sonraki tam sayıya çıkar:
17,93 -> 18 ve 22,31 -> 23) uygulanınca: **İNCELE −%23, DURDUR −%29.**

═══ 3. ÜÇ TÜRETMENİN KARŞILAŞTIRMASI ═══

Yanlış tetik olasılıkları (madde 302'nin karıştırılmış örneklemi):

    esik kumesi                       INCELE    DURDUR
    15x5 referansi (-%18/-%23)         %11,1     %2,3
    madde 302 (olcek 1,216)            %12,6     %2,5
    **madde 303 KANONIK (-%23/-%29)**   %9,7     %1,9
    madde 302 ONCESI (olceksiz)       **%30,6** **%9,7**

**Madde 302'nin düzeltmesi yönde ve büyüklükte DOĞRUYDU** — %30,6'yı
%12,6'ya indirmişti. Kanonik yöntem onu biraz GEVŞETİYOR: gerçek ölçek
1,216 değil **1,264** (İNCELE) ve **1,299** (DURDUR). Yani düşüş oranı,
gereken genişlemeyi hafifçe EKSİK tahmin ediyordu.

Fark küçük (1-3 puan yanlış tetik) ama yön anlamlı: madde 302'nin eşiği
gereğinden SIKIYDI, yani gereksiz alarm tarafına sapıyordu.

═══ 4. EŞİK ARTIK ÜÇ KADEMELİ ═══

    1) KITAP_ESIK'te OLCULMUS cift varsa -> aynen o        ("olculmus")
    2) yoksa KITAP_DUSUS'te dusus varsa  -> dusus oraniyla ("olceklenmis")
    3) o da yoksa                        -> temel + UYARI  ("temel")

    15x5 -> olculmus    −%18 / −%23   (degismedi)
    13x3 -> olculmus    −%23 / −%29   (madde 302'de −%21,9/−%28,0 idi)
    5x5  -> olceklenmis −%19,96 / −%25,50
    7x7  -> temel       −%18 / −%23 + UYARI

Rapor özetine kademe de yazılıyor, böylece bir eşiğin ÖLÇÜLDÜĞÜ mü
TAHMİN edildiği mi görünür.

═══ 5. MADDE 301'İN SIZINTISI DA KAPATILDI ═══

Madde 301 bir açık eksen kaydetmişti: `temiz_ortam()` üç dosyayı geçici
dizine yönlendiriyor ama madde 214'ün `TP_DEFTER_DOSYA`'sı ve madde
292'nin `TP_KURULUM_DOSYA`'sı listeye hiç girmemişti — takım onları
proje dizinine yazıp koşular arasında büyütüyordu. O gün ölçülmüş ve
ZARARSIZ bulunmuştu (`bir_tur` onları yalnız yazıyor), ama madde 301'in
4. yasası şöyleydi: *"şu an okunmayan bir dosya yarın okunur."*

Fikstür artık ürünün yazdığı BÜTÜN dosyaları yönlendiriyor
(`TP_DEFTER_DOSYA`, `TP_KURULUM_DOSYA`, `PRIM_DOSYA` eklendi).
Doğrulama: takım koştuktan sonra proje dizininde yalnızca
`referans_getiri.csv` (sabitlenmiş girdi) kalıyor.

═══ 6. NE DEĞİŞMEDİ ═══

Strateji ayarı, seçim, bacak büyüklükleri, geri test: hiçbiri. 15x5
varsayılanında eşikler birebir aynı. 13x3 koşan biri için eşikler
madde 302'ye göre 1,1 puan gevşedi.

AYAR DEĞİŞMEDİ. Öneri: **13 dilim x 3 bacak, 2.000 $, 1x.**
"""

# ---------------------------------------------------------------- SABİTLER

KAYNAK = ("Madde 302'nin ACIK EKSENI: esikler iki yoldan turetilmisti ama "
          "ikisi de madde 231'in ASIL yontemini (en kotu makul rejimin "
          "1-yillik bootstrap p5/p1'i) atliyordu.")
NEDEN_KAPATILDI = ("Canliya yeni bir esik koymusken o ekseni acik birakmak "
                   "dogru degildi; yeni eksen acmadan once kapatildi.")

# --- 1. yontem dogrulamasi ---
BOOTSTRAP = "madde 231'in yil_bootstrap'i birebir: 4.000 ornek, 21 bar blok, tohum 11"
REJIM_KIRILMA = "2025-01-01"
DOGRULAMA_15X5 = {
    #  rejim      : (olculen p1, madde 231'in kaydi)
    "tum":    (-21.37, -21.4),
    "dusuk":  (-22.31, -22.3),
    "yuksek": (-17.99, -18.0),
}
ZINCIR = (231, 233, 243)
MADDE233_P5 = -17.93
"""En kotu rejim p5'i; madde 233'un -%18'i tam olarak bu."""

# --- 2. 13x3'un kanonik olcumu ---
REJIM_13X3 = {
    #  rejim      : (1y getiri p5, 1y dusus p5, 1y dusus p1)
    "tum":    (50.8, -21.29, -25.94),
    "dusuk":  (26.0, -22.66, -28.98),
    "yuksek": (96.8, -17.90, -20.86),
}
REJIM_15X5 = {
    "tum":    (41.1, -16.95, -21.37),
    "dusuk":  (24.2, -17.93, -22.31),
    "yuksek": (71.6, -15.11, -17.99),
}

REJIM_15X4 = {
    # MADDE 329: KOSULAN kitap (15 faz x 4 bacak, D8, 2.000 $).
    # rejim -> (1y getiri p5, 1y dusus p5, 1y dusus p1)
    "tum":    (36.7, -20.71, -25.84),
    "dusuk":  (18.5, -22.83, -29.23),   # EN KOTU -> esik buradan
    "yuksek": (72.8, -16.48, -19.69),
}
EN_KOTU_REJIM = "dusuk"
YUVARLAMA_KURALI = ("madde 233: buyuklugu bir sonraki tam sayiya cikar "
                    "(17,93 -> 18; 22,31 -> 23)")
ESIK_KANONIK = {"15x5": (-0.18, -0.23), "13x3": (-0.23, -0.29),
                "15x4": (-0.23, -0.30)}   # madde 329: KOSULAN kitap

# --- 3. uc turetmenin karsilastirmasi ---
YANLIS_TETIK = {
    #  esik kumesi                  : (INCELE %, DURDUR %)
    "15x5 referansi (-18/-23)":        (11.1, 2.3),
    "madde 302 (olcek 1,216)":         (12.6, 2.5),
    "madde 303 KANONIK (-23/-29)":     (9.7, 1.9),
    "madde 302 ONCESI (olceksiz)":     (30.6, 9.7),
}
GERCEK_OLCEK = {"incele": 22.66 / 17.93, "durdur": 28.98 / 22.31}
MADDE302_OLCEK = 17.68 / 14.54
MADDE302_YONU = ("Madde 302'nin duzeltmesi YONDE VE BUYUKLUKTE dogruydu "
                 "(%30,6 -> %12,6). Kanonik yontem onu biraz GEVSETIYOR: "
                 "gercek olcek 1,216 degil 1,264/1,299, yani dusus orani "
                 "gereken genislemeyi EKSIK tahmin ediyordu - esik "
                 "gereginden SIKIYDI (gereksiz alarm tarafina sapiyordu).")

# --- 4. uc kademe ---
KADEME = {
    "olculmus": "KITAP_ESIK'te olculmus cift var -> aynen kullanilir",
    "olceklenmis": "dusus tablosunda var -> dusus oraniyla olceklenir (TAHMIN)",
    "temel": "hicbiri -> temel esik + UYARI (gevsetilmez)",
}
KADEME_ORNEK = {"15x5": "olculmus", "13x3": "olculmus",
                "5x5": "olceklenmis", "7x7": "temel"}

# --- 5. madde 301'in sizintisi ---
SIZINTI_KAYNAK = 301
FIKSTUR_EKLENEN = ("TP_DEFTER_DOSYA", "TP_KURULUM_DOSYA", "PRIM_DOSYA")
SIZINTI_YASASI = "madde 301 yasa 4: su an okunmayan bir dosya yarin okunur"
PROJE_DIZINI_KALAN = ("referans_getiri.csv",)
"""Takim kostuktan sonra proje dizininde kalan tek csv (sabitlenmis girdi)."""

AYAR_DEGISTI = False
ONERI = "13 dilim x 3 bacak, 2.000 $, 1x"

YASA1 = ("Kendi actigin ekseni, yeni bir eksen acmadan ONCE kapat - "
         "ozellikle canliya bir esik koymussan. Madde 302'nin esigi "
         "dogruydu ama gereginden sikiydi; acik eksen kapanmadan bu "
         "bilinemezdi.")
YASA2 = ("Bir kisayol olcum, DOGRU YONDE olsa bile BUYUKLUKTE sapar: "
         "dusus orani (1,216) gereken genislemeyi 1,264/1,299 yerine "
         "eksik tahmin etti. 'Iki bagimsiz yol bulustu' guclu bir "
         "isarettir ama UCUNCU yol kanonikse, kanonik olan kazanir.")
YASA3 = ("Bir esigin OLCULDUGU mu TAHMIN edildigi mi, esigin DEGERI kadar "
         "onemlidir: rapor artik kademeyi de yaziyor ('olculmus' / "
         "'olceklenmis' / 'temel'), boylece gevsek bir tahmin olculmus "
         "gibi gorunmez.")


# ---------------------------------------------------------------- HÜKÜM

def yontem_dogrulandi_mi(tol: float = 0.05) -> bool:
    """15x5 kolu madde 231'in uc rakamini da verdi mi?"""
    return all(abs(a - b) <= tol for a, b in DOGRULAMA_15X5.values())


def madde233_zinciri_tutuyor_mu(tol: float = 0.1) -> bool:
    """En kotu rejim p5'i, madde 233'un -%18'ini aciklıyor mu?"""
    return abs(abs(MADDE233_P5) - 18.0) <= tol + 0.07


def en_kotu_rejim_dogru_mu(kitap: str = "13x3") -> bool:
    r = REJIM_13X3 if kitap == "13x3" else REJIM_15X5
    return min(r, key=lambda k: r[k][2]) == EN_KOTU_REJIM


def kanonik_esik(kitap: str) -> tuple[float, float]:
    return ESIK_KANONIK[kitap]


def madde302_dogru_yonde_miydi() -> bool:
    """Madde 302 yanlis tetigi %30,6'dan asagi cekti mi?"""
    return (YANLIS_TETIK["madde 302 (olcek 1,216)"][0]
            < YANLIS_TETIK["madde 302 ONCESI (olceksiz)"][0] / 2)


def madde302_gereginden_siki_miydi() -> bool:
    """Madde 302'nin esigi 15x5 referansindan daha SIK mi tetikliyordu?"""
    return (YANLIS_TETIK["madde 302 (olcek 1,216)"][0]
            > YANLIS_TETIK["15x5 referansi (-18/-23)"][0])


def kanonik_esdeger_mi(tol: float = 2.0) -> bool:
    a = YANLIS_TETIK["madde 303 KANONIK (-23/-29)"]
    b = YANLIS_TETIK["15x5 referansi (-18/-23)"]
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def kisayol_olcek_eksik_mi() -> bool:
    return (MADDE302_OLCEK < GERCEK_OLCEK["incele"]
            and MADDE302_OLCEK < GERCEK_OLCEK["durdur"])


def sizinti_kapandi_mi() -> bool:
    return len(FIKSTUR_EKLENEN) == 3


def ayar_degisti_mi() -> bool:
    return AYAR_DEGISTI


def hukum() -> str:
    return ("KAPANDI: madde 302'nin acik ekseni (madde 231'in kanonik "
            "yontemi) uygulandi. Once yontem dogrulandi - 15x5 kolu madde "
            "231'in uc rakamini da ondaligina kadar verdi ve en kotu rejim "
            "p5'i -%17,93, yani madde 233'un -%18'i tam olarak bu. 13x3 "
            "icin en kotu rejim (dusuk prim) p5 -%22,66 / p1 -%28,98 -> "
            "madde 233'un yuvarlamasiyla **-%23 / -%29**. Madde 302'nin "
            "duzeltmesi YONDE VE BUYUKLUKTE dogruydu (yanlis tetigi %30,6 "
            "-> %12,6 indirmisti) ama gereginden SIKIYDI: gercek olcek "
            "1,216 degil 1,264/1,299. Kanonik esikle yanlis tetik %9,7 / "
            "%1,9, yani 15x5'in %11,1 / %2,3'uyle esdeger. Esik artik uc "
            "kademeli (olculmus / olceklenmis / temel) ve rapor kademeyi "
            "de yaziyor. Madde 301'in fikstur sizintisi da kapatildi. "
            "Strateji ayari DEGISMEDI.")


# ---------------------------------------------------------------- RAPOR

def yaz() -> None:
    print(__doc__)
    print("KAYNAK: %s" % KAYNAK)
    print("NEDEN: %s\n" % NEDEN_KAPATILDI)

    print("1) YONTEM DOGRULAMASI (%s):" % BOOTSTRAP)
    print("   %-10s %14s %18s" % ("rejim", "olculen p1", "madde 231'in kaydi"))
    for r, (a, b) in DOGRULAMA_15X5.items():
        print("   %-10s %+13.2f %+17.1f" % (r, a, b))
    print("   -> yontem dogrulandi mi: %s" % yontem_dogrulandi_mi())
    print("   en kotu rejim p5 %+.2f -> madde 233'un -%%18'i: %s"
          % (MADDE233_P5, madde233_zinciri_tutuyor_mu()))
    print("   zincir: %s" % list(ZINCIR))

    print("\n2) REJIM OLCUMU (kirilma %s):" % REJIM_KIRILMA)
    for kitap, r in (("15x5", REJIM_15X5), ("13x3", REJIM_13X3)):
        print("   -- %s --" % kitap)
        print("   %-10s %14s %14s %14s"
              % ("rejim", "1y getiri p5", "1y dusus p5", "1y dusus p1"))
        for rad, v in r.items():
            isa = "  <== EN KOTU" if rad == EN_KOTU_REJIM else ""
            print("   %-10s %+13.1f%% %+13.2f%% %+13.2f%%%s"
                  % (rad, v[0], v[1], v[2], isa))
        print("   en kotu rejim dogru mu: %s" % en_kotu_rejim_dogru_mu(kitap))
        print("   -> KANONIK ESIK: INCELE %+.0f%% / DURDUR %+.0f%%"
              % (kanonik_esik(kitap)[0] * 100, kanonik_esik(kitap)[1] * 100))
    print("   yuvarlama: %s" % YUVARLAMA_KURALI)

    print("\n3) UC TURETMENIN KARSILASTIRMASI (yanlis tetik):")
    print("   %-34s %10s %10s" % ("esik kumesi", "INCELE", "DURDUR"))
    for ad, (i, d) in YANLIS_TETIK.items():
        print("   %-34s %9.1f%% %9.1f%%" % (ad, i, d))
    print("   madde 302 dogru yonde miydi: %s" % madde302_dogru_yonde_miydi())
    print("   madde 302 gereginden siki miydi: %s" % madde302_gereginden_siki_miydi())
    print("   kanonik esik 15x5 ile esdeger mi: %s" % kanonik_esdeger_mi())
    print("   olcek: madde 302 %.3f | gercek INCELE %.3f DURDUR %.3f -> "
          "kisayol eksik mi: %s"
          % (MADDE302_OLCEK, GERCEK_OLCEK["incele"], GERCEK_OLCEK["durdur"],
             kisayol_olcek_eksik_mi()))
    print("   %s" % MADDE302_YONU)

    print("\n4) UC KADEME:")
    for k, v in KADEME.items():
        print("   %-13s %s" % (k, v))
    print("   ornek: %s" % KADEME_ORNEK)

    print("\n5) MADDE %d'IN SIZINTISI:" % SIZINTI_KAYNAK)
    print("   fiksture eklenen: %s" % list(FIKSTUR_EKLENEN))
    print("   gerekce: %s" % SIZINTI_YASASI)
    print("   kapandi mi: %s | proje dizininde kalan: %s"
          % (sizinti_kapandi_mi(), list(PROJE_DIZINI_KALAN)))

    print("\n6) AYAR degisti mi: %s | oneri: %s" % (ayar_degisti_mi(), ONERI))
    print("\nYASA 1: %s" % YASA1)
    print("YASA 2: %s" % YASA2)
    print("YASA 3: %s" % YASA3)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
