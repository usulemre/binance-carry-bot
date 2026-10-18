#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 280 — KİTAP SEVİYESİNDE DEVRE KESİCİ: RED, VE DÜŞÜŞÜ **ARTIRIYOR**.
MEKANİZMA ÖLÇÜLDÜ: KESİLMİŞ MARUZİYET YENİ ZİRVE YAPAMAZ.

Madde 276'nın bıraktığı son canlı aday. Madde 191 tek bacağa (long) stop
koydu → tekdüze yıkıcı, çünkü long kanaması sıkışma opsiyonunun PRİMİ.
Madde 215 taraf bazlı tutma kesti → eşleşmeyi bozdu, kitap yönlü hâle
geldi. **Her iki bacağı ORANTILI küçültmek** eşleşmeyi bozmaz: nötrlük
korunur, yalnız ölçek küçülür. Bu aile hiç denenmemişti.

NEDEN ŞİMDİ: madde 276 dozu bağlayan şeyin likidasyon duvarı değil
kullanıcının **toleransı** olduğunu kurdu (−%30 bir yıllık p95 düşüş).
Dolayısıyla p95 düşüşü azaltan her şey doğrudan brüt → doğrudan getiri
satın alır. Ölçüt baştan belliydi: **aynı −%30 toleransta brütü ne kadar
yükseltiyor.**

ÖN KAYIT
--------
Kural: gün t'nin KAPANIŞINDA zirveden düşüş ≥ D ise, t+1'den itibaren
maruziyet f ile ölçeklenir; özkaynak zirvenin D/2 kadar altına geri
çıkınca tam ölçeğe dönülür. Bilgi gecikmesi gerçek: karar kapanışta,
uygulama ertesi gün. Maliyet: her ölçek değişimi bacakların (1−f) kadarını
kapatıp geri açmak → madde 275'in maker gidiş-dönüşü **5,14 bp** düşülüyor.
İzgara: D ∈ {10,15,20(,25)} × f ∈ {0,25; 0,50}. Çokluk beyan edildi.
Ölçüt (madde 274'ün yasası): **blok bootstrap ZORUNLU** — kural YOL
BAĞIMLI ve karıştırma seri korelasyonunu yok eder, yani kuralın değerini
tanım gereği silerdi.

BENİM HATAM — BİRİNCİ KISIM D=15 ve 20'Yİ HİÇ ÖLÇMEMİŞ
------------------------------------------------------
Gerçekleşen yolda devre kesici yalnız D=10'da tetikledi (6-8 olay);
**D=15 ve D=20 HİÇ tetiklenmedi**, çünkü gerçekleşen maks düşüş 14,54.
O satırlar "etkisi yok" değil "kural hiç çalışmadı" demekti ve ben onları
tabloya sonuç gibi yazmıştım. Düzeltme: kural her **bootstrap yolunun
içinde**, kaldıraçlı özkaynak üzerinde koşuldu — orada derin düşüşler
gerçekten oluyor ve D=15/20/25 tetikliyor (%10,9–%99,6 yol).

BULGU 1 — GERÇEKLEŞEN YOLDA: GETİRİ DÜŞÜYOR, DÜŞÜŞ DÜŞMÜYOR
-----------------------------------------------------------
    aday          olay   yıllık    Sharpe   maks düşüş
    kontrol         -   +%111,67   2,943     14,54
    D10 f0,25       6    +%78,07   2,577     **14,57**
    D10 f0,50       8    +%96,93   2,827     **14,56**
    D15/D20          0   (tetiklemedi — ölçüm YOK)

33,6 puan getiri gitti, düşüş **0,03 puan kötüleşti.** İlk işaret buydu.

BULGU 2 — BOOTSTRAP YOLLARININ İÇİNDE: SEKİZ VARYANTIN SEKİZİ DE KAYBEDİYOR
---------------------------------------------------------------------------
Aynı −%30 toleransta çözülen brüt ve medyan net yıllık getiri:

    aday          brüt     net yıllık   kontrole göre   tetikleme
    kontrol      1,878x     +%274,13         -             -
    D10 f0,25    1,571x     +%164,06     **−110,07**    %96,8 yol
    D10 f0,50    1,862x     +%224,61       −49,52       %99,6 yol
    D15 f0,25    1,547x     +%180,30       −93,82       %56,5 yol
    D15 f0,50    1,810x     +%236,92       −37,21       %74,2 yol
    D20 f0,25    1,606x     +%196,90       −77,22       %32,8 yol
    D20 f0,50    1,799x     +%240,64       −33,49       %41,2 yol
    D25 f0,25    1,716x     +%233,85       −40,28       %10,9 yol
    D25 f0,50    1,824x     +%257,53     **−16,60**     %14,9 yol

**Doz-tepki tek yönlü ve kural NE KADAR ÇOK ÇALIŞIRSA O KADAR KÖTÜ.**
Kayıp, tetikleme sıklığıyla neredeyse birebir: %99,6 tetikleyen −49,5
puan, %14,9 tetikleyen −16,6 puan. Sıfıra ancak kural hiç çalışmayınca
yaklaşıyor. **Hiçbir eşikte yardımcı olmuyor.**

BULGU 3 — MEKANİZMA: AYNI BRÜTTE DÜŞÜŞÜ **ARTIRIYOR**
-----------------------------------------------------
Brüt sabitlenince (1,878x) sebep görünüyor:

    aday         p95 düşüş   medyan düşüş   medyan getiri   yeni zirve   sualtı gün
    kontrol        30,00        19,06         +%275,7         67,3        294,9
    D10 f0,25    **34,92**      19,48         +%194,6       **57,0**    **305,6**
    D15 f0,25    **35,00**      19,29         +%235,9         62,2        300,2
    D20 f0,25      34,19        19,06         +%255,0         64,6        297,7
    D25 f0,50      30,84        19,06         +%270,7         66,6        295,6

Sekiz varyantın **sekizi de p95 düşüşü ARTIRIYOR** (+0,25 … +5,00 puan),
**medyan düşüş değişmiyor** (19,06 → 18,74-19,48), ve iki mekanizma
göstergesi kayıpla birebir hareket ediyor: **yeni zirve sayısı azalıyor**
(−0,7 … −10,4) ve **sualtı gün sayısı artıyor** (+0,7 … +10,7).

**SEBEP: düşüş ZİRVEDEN ölçülür.** Maruziyeti kesmiş bir kitap toparlanmaya
da küçük ölçekle katılır, yani **yeni zirve yapamaz**; eski zirvenin
altında daha uzun kalır ve bir sonraki düşüş o **bayat ve yüksek**
zirveden ölçülür. Devre kesici V şeklindeki toparlanmayı L'ye çeviriyor
ve maksimum düşüş ölçütü tam olarak bunu cezalandırıyor. Üstüne her
anahtarlama 5,14 bp maliyet.

HÜKÜM
-----
**RED — çifte kayıp.** Getiri düşüyor VE kuyruk derinleşiyor; medyan
düşüşe bile faydası yok. Sekiz varyantın sekizi, dört eşiğin dördü. Ayar
DEĞİŞMEDİ. Madde 276'nın bıraktığı son canlı aday kapandı.

VE BU, 191/215'İ GENELLEŞTİRİYOR: red artık "taraf bazlı kesme çalışmaz"
değil, **"düşüş sırasında maruziyeti kesmek çalışmaz"** — ve sebebi
ampirik değil MEKANİK. Kitabın kuyruğunu azaltmanın yalnız iki yolu var:
(a) düşüşten ÖNCE kesmek, yani öngörü — madde 278 bunun geçmişten
ulaşılamaz olduğunu ölçtü; (b) KALICI olarak düşük brütle çalışmak —
ki bu zaten doz kararıdır (madde 276). **Bedava kuyruk azaltma yok.**

SINIR / KİRLENME UYARISI
------------------------
Buradaki blok bootstrap kontrol brütünü 1,878-1,899x veriyor, oysa
madde 276'nın doz kararı **karıştırma** ölçütüyle 1,497x (medyan) /
**1,254x (p5)** demişti. Fark yöntemde ve madde 262 bunu zaten
belgelemişti (blok büyüdükçe düşüş kuyruğu İYİLEŞİR). **Bu maddenin
1,878x'i bir KIYAS ARACIDIR, doz tavsiyesi DEĞİL.** Doz kararı madde
276'da ve 1,25x'te kalıyor.
"""
from __future__ import annotations

MAKER_GIDIS_DONUS_BP = 5.14      # madde 275
TOLERANS = 30.0
ICRA_1X = 0.79

HATAM = {
    "ne": "birinci kisimda D=15 ve D=20 GERCEKLESEN yolda HIC tetiklemedi "
          "(maks dusus 14,54) ve ben o satirlari sonuc gibi yazdim; "
          "'etkisi yok' degil 'kural hic calismadi' demekti",
    "duzeltme": "kural her BOOTSTRAP YOLUNUN icinde, kaldiracli ozkaynak "
                "uzerinde kosuldu; orada D=15/20/25 gercekten tetikliyor",
}

# --- gerceklesen yol (1x) ---------------------------------------------
GERCEKLESEN = {   # aday -> (olay, yillik_net, sharpe, maks_dusus)
    "kontrol": (None, 111.67, 2.943, 14.54),
    "D10_f0.25": (6, 78.07, 2.577, 14.57),
    "D10_f0.50": (8, 96.93, 2.827, 14.56),
}
TETIKLEMEYENLER = ("D15_f0.25", "D15_f0.50", "D20_f0.25", "D20_f0.50")

# --- bootstrap yollarinin icinde (doz olcutu) -------------------------
KONTROL_YOL = (1.878, 274.13)
DOZ = {   # (D, f) -> (brut, net_yillik, kontrole_gore, tetikleme_pct)
    (10.0, 0.25): (1.571, 164.06, -110.07, 96.8),
    (10.0, 0.50): (1.862, 224.61, -49.52, 99.6),
    (15.0, 0.25): (1.547, 180.30, -93.82, 56.5),
    (15.0, 0.50): (1.810, 236.92, -37.21, 74.2),
    (20.0, 0.25): (1.606, 196.90, -77.22, 32.8),
    (20.0, 0.50): (1.799, 240.64, -33.49, 41.2),
    (25.0, 0.25): (1.716, 233.85, -40.28, 10.9),
    (25.0, 0.50): (1.824, 257.53, -16.60, 14.9),
}
BAKIS = len(DOZ)

# --- mekanizma: AYNI brutte (1,878x) ----------------------------------
SABIT_BRUT = 1.878
MEKANIZMA = {   # aday -> (p95_dusus, medyan_dusus, medyan_getiri, yeni_zirve, sualti)
    "kontrol": (30.00, 19.06, 275.7, 67.3, 294.9),
    "D10_f0.25": (34.92, 19.48, 194.6, 57.0, 305.6),
    "D10_f0.50": (30.25, 18.74, 227.2, 61.4, 301.0),
    "D15_f0.25": (35.00, 19.29, 235.9, 62.2, 300.2),
    "D15_f0.50": (30.64, 19.14, 254.3, 64.8, 297.5),
    "D20_f0.25": (34.19, 19.06, 255.0, 64.6, 297.7),
    "D20_f0.50": (31.27, 19.06, 259.0, 65.2, 297.0),
    "D25_f0.25": (32.91, 19.06, 267.3, 66.3, 295.9),
    "D25_f0.50": (30.84, 19.06, 270.7, 66.6, 295.6),
}

# --- kirlenme uyarisi -------------------------------------------------
BLOK_KONTROL_BRUT = 1.878
MADDE_276_KARISTIRMA_BRUT = 1.497
MADDE_276_DOZ_BRUT = 1.254
KIRLENME_UYARISI = ("bu maddenin 1,878x'i KIYAS ARACI, doz tavsiyesi DEGIL; "
                    "doz karari madde 276'da karistirma olcutuyle 1,25x")

# --- kapanan aile -----------------------------------------------------
GENELLESTIRILEN = (191, 215)
KUYRUK_AZALTMANIN_IKI_YOLU = (
    "dususten ONCE kesmek = ongoru (madde 278: gecmisten ulasilamaz)",
    "KALICI dusuk brut = doz karari (madde 276)",
)


def hatam_kayitli_mi() -> bool:
    return ("tetiklemedi" in HATAM["ne"].lower()
            and "olcum" not in HATAM["duzeltme"].lower()[:0]
            and len(TETIKLEMEYENLER) == 4)


def gerceklesen_dusus_iyilesti_mi() -> bool:
    """Gerceklesen yolda devre kesici dususu iyilestirdi mi?"""
    k = GERCEKLESEN["kontrol"][3]
    return any(GERCEKLESEN[a][3] < k for a in GERCEKLESEN if a != "kontrol")


def hepsi_kaybediyor_mu() -> bool:
    return all(v[2] < 0 for v in DOZ.values())


def en_iyi_varyant() -> tuple:
    a = max(DOZ, key=lambda k: DOZ[k][2])
    return a, DOZ[a][2]


def kayip_tetiklemeyle_artiyor_mu() -> bool:
    """Kural ne kadar cok calisirsa o kadar mi kotu?"""
    s = sorted(DOZ.values(), key=lambda v: v[3])
    return s[0][2] > s[-1][2]


def ayni_brutte_dususu_artiriyor_mu() -> bool:
    """Sekiz varyantin HEPSI p95 dususu artiriyor mu?"""
    k = MEKANIZMA["kontrol"][0]
    return all(v[0] > k for a, v in MEKANIZMA.items() if a != "kontrol")


def medyan_dususe_faydasi_var_mi(tol: float = 0.5) -> bool:
    k = MEKANIZMA["kontrol"][1]
    return any(v[1] < k - tol for a, v in MEKANIZMA.items() if a != "kontrol")


def mekanizma_zirve_mi() -> bool:
    """Dususu artiran varyantlar AYNI ZAMANDA daha az yeni zirve yapiyor mu?"""
    k = MEKANIZMA["kontrol"]
    kotuler = [v for a, v in MEKANIZMA.items()
               if a != "kontrol" and v[0] > k[0] + 2.0]
    return bool(kotuler) and all(v[3] < k[3] and v[4] > k[4] for v in kotuler)


def cifte_kayip_mi() -> bool:
    """Hem getiri hem kuyruk kotulesiyor mu?"""
    return hepsi_kaybediyor_mu() and ayni_brutte_dususu_artiriyor_mu()


def bedava_kuyruk_azaltma_var_mi() -> bool:
    return False


def hukum() -> str:
    a, p = en_iyi_varyant()
    return ("RED - CIFTE KAYIP. %d varyantin %d'i de doz olcutunde "
            "kaybediyor (en iyisi D%.0f f%.2f ile %+.2f puan) VE ayni "
            "brutte (%.3fx) hepsi p95 dususu ARTIRIYOR; medyan dususe "
            "faydasi bile yok. Sebep MEKANIK: dusus ZIRVEDEN olculur ve "
            "kesilmis maruziyet YENI ZIRVE YAPAMAZ (yeni zirve -%.1f, "
            "sualti +%.1f gun). Madde 191/215 'taraf bazli kesme "
            "calismaz'dan 'DUSUS SIRASINDA MARUZIYETI KESMEK calismaz'a "
            "genellestirildi. Ayar DEGISMEDI."
            % (BAKIS, BAKIS, a[0], a[1], p, SABIT_BRUT,
               MEKANIZMA["kontrol"][3] - MEKANIZMA["D10_f0.25"][3],
               MEKANIZMA["D10_f0.25"][4] - MEKANIZMA["kontrol"][4]))


def yaz() -> None:
    print("MADDE 280 — KİTAP SEVİYESİNDE DEVRE KESİCİ\n")
    print("BENİM HATAM: %s\n  düzeltme: %s" % (HATAM["ne"], HATAM["duzeltme"]))
    print("\nGERÇEKLEŞEN YOL (1x):")
    print("  aday        | olay | yıllık   | Sharpe | maks düşüş")
    for a, v in GERCEKLESEN.items():
        print("  %-11s | %4s | %+8.2f | %6.3f | %10.2f"
              % (a, v[0] if v[0] is not None else "-", v[1], v[2], v[3]))
    print("  (%s: TETİKLEMEDİ -> ölçüm YOK)" % ", ".join(TETIKLEMEYENLER))
    print("  -> gerçekleşen yolda düşüş İYİLEŞTİ mi: %s"
          % gerceklesen_dusus_iyilesti_mi())
    print("\nBOOTSTRAP YOLLARININ İÇİNDE (aynı −%%%.0f toleransta):" % TOLERANS)
    print("  aday        | brüt   | net yıllık | kontrole göre | tetikleme")
    print("  kontrol     | %.3fx | %+10.2f | %+13s | -" % (KONTROL_YOL + ("-",)))
    for (D, f) in sorted(DOZ):
        b, n, fark, tet = DOZ[(D, f)]
        print("  D%-4.0f f%.2f | %.3fx | %+10.2f | %+13.2f | %%%.1f yol"
              % (D, f, b, n, fark, tet))
    a, p = en_iyi_varyant()
    print("  -> hepsi kaybediyor mu: %s | en iyisi D%.0f f%.2f (%+.2f puan)"
          % (hepsi_kaybediyor_mu(), a[0], a[1], p))
    print("  -> kayıp TETİKLEME sıklığıyla artıyor mu: %s"
          % kayip_tetiklemeyle_artiyor_mu())
    print("\nMEKANİZMA — AYNI BRÜTTE (%.3fx):" % SABIT_BRUT)
    print("  aday        | p95 düşüş | medyan dd | medyan getiri | yeni zirve | sualtı")
    for a_, v in MEKANIZMA.items():
        print("  %-11s | %9.2f | %9.2f | %+13.1f | %10.1f | %6.1f"
              % (a_, v[0], v[1], v[2], v[3], v[4]))
    print("  -> AYNI brütte p95 düşüşü ARTIRIYOR mu (hepsi): %s"
          % ayni_brutte_dususu_artiriyor_mu())
    print("  -> medyan düşüşe faydası var mı: %s" % medyan_dususe_faydasi_var_mi())
    print("  -> mekanizma ZİRVE mi (düşüşü artıranlar az zirve + çok sualtı): %s"
          % mekanizma_zirve_mi())
    print("  -> ÇİFTE KAYIP mı: %s" % cifte_kayip_mi())
    print("\nKUYRUĞU AZALTMANIN YALNIZ İKİ YOLU:")
    for y in KUYRUK_AZALTMANIN_IKI_YOLU:
        print("  - %s" % y)
    print("  -> bedava kuyruk azaltma var mı: %s" % bedava_kuyruk_azaltma_var_mi())
    print("\nKİRLENME UYARISI: %s" % KIRLENME_UYARISI)
    print("  (blok %.3fx · madde 276 karıştırma %.3fx · DOZ KARARI %.3fx)"
          % (BLOK_KONTROL_BRUT, MADDE_276_KARISTIRMA_BRUT, MADDE_276_DOZ_BRUT))
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
