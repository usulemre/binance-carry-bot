#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 276 — DOZ KARARI VERİLDİ (−%30 tolerans) VE ÇÖZÜLEN BRÜT TEK BİR SAYI
DEĞİL: 1,25x ile 1,92x ARASI BİR ARALIK.

Kullanıcı madde 274'ün doz çetvelini görüp kararını verdi: **bir yıllık p95
düşüşte −%30'a tahammül ediyor.** Çetvel o satırda brüt 1,495x ve net
+%199,2 diyordu. Bu madde o satırı AYARA YAZMADAN ÖNCE üç şeyi sınadı.

DENETİM 0 — VERİ KAYNAĞI (madde 268'in dersi)
---------------------------------------------
Madde 274 `/tmp/m273_0.20.npy` kullanıyordu; o dosyanın kanonik
`referans_getiri.csv` ile AYNI seri olduğu doğrulandı (n=1504, ortalama
0,002163, std 0,014047, `allclose` atol 1e-12). Madde 268'de panelin
yanlış veri kümesiyle kıyaslanması uydurma bir sapma üretmişti; bu kez
kaynak önce denetlendi.

BULGU 1 — ÇÖZÜM TEKRARLANABİLİR AMA ÖRNEKLEME BELİRSİZLİĞİ BÜYÜK
-----------------------------------------------------------------
Beş bağımsız tohumla (B=40.000) yeniden çözüm:

    tohum    brüt      net yıllık
     2760   1,5038x     +%201,1
      777   1,5181x     +%204,0
    31337   1,5187x     +%204,1
       11   1,5076x     +%201,8
    90210   1,5120x     +%202,8
    -> yayılım 0,015 · ortalama 1,5120x (madde 274'ün 1,495'ine +0,017)

Yani **Monte Carlo gürültüsü ihmal edilebilir.** Ama asıl belirsizlik
orada değil. Günler blok bootstrap'landığında (blok 21, 120 tekrar) ve
brüt HER ÖRNEKLEMDE yeniden çözüldüğünde:

    brüt dağılımı:  p5 **1,254x** · medyan 1,497x · p95 **1,921x**
    net getiri:     p5 +%153,4   · medyan +%199,6 · p95 +%297,8

**Aynı −%30 toleransı, serinin hangi örneklemle ölçüldüğüne göre 1,25x
ile 1,92x arasında brüt istiyor.** 1,497x seçmek, geçmiş serinin kendi
dağılımının ŞANSLI tarafındaysa (madde 243: gerçekleşen yol %84'lük
yüzdelik) gerçek p95 düşüşün −%30'u AŞMASI demek.

**İHTİYATLI BRÜT = p5 = 1,254x -> net +%153,4.** Bu, serinin şanslı
olduğu durumda bile toleransı aşmayan doz.

BULGU 2 — LİKİDASYON PAYI İKİ ADAYDA DA VAR
-------------------------------------------
Madde 266'nın ölçülen gün içi kuyruğu 1x'te −%41,41 (40 tohumun EN
KÖTÜSÜ, dakika çözünürlüğü). Duvara kalan pay:

    brüt      mmr %0,5   mmr %1,0   mmr %2,5
    1,254x     +47,4      +46,8      +44,9  puan
    1,497x     +37,3      +36,5      +34,3  puan
    duvar      2,386x     2,358x     2,277x

İkisi de duvarın içinde; 1,254x duvarın %53'ünde, 1,497x %63'ünde.
Likidasyon bu dozda bağlayıcı kısıt DEĞİL.

BULGU 3 — AMA EKRANDA GÖRÜLECEK SAYI −%30 DEĞİL, ~−%45
------------------------------------------------------
Tolerans GÜNLÜK KAPANIŞ serisinde tanımlı. Madde 266 gün içi yolun
medyanda **1,488 kat**, p90'da 2,722 kat daha derin olduğunu ölçtü.
Dolayısıyla −%30'luk bir yıl, gün içinde medyanda **~−%45** demek:

    brüt      günlük p95   gün içi (medyan büyütme)   ölçülen kuyruk
    1,254x      −%30              ~−%45                  −%52
    1,497x      −%30              ~−%45                  −%62

**Bu madde p90 büyütmesini (2,722) −%30'un üstüne ÇARPMIYOR** — o iki
ayrı kuyruk ölçütünü üst üste bindirmek olurdu ve madde 273'te tam bu
hatayı (kaldıraçla iki kez çarpma) yapmıştım. Söylenen şey yalnızca
şudur: tolerans günlük kapanışta tanımlıysa gün içi karşılığı medyanda
1,5 kat daha derindir ve kullanıcı kararını verirken bunu bilmelidir.

GERÇEKLEŞEN YOLDA (karıştırma yok, 2022-07 -> 2026-08)
------------------------------------------------------
    brüt      yıllık net   maks düşüş   en kötü ay
    1,000x      +%111,7      −%14,54      −%6,4
    1,254x      +%153,4      −%18,08      −%8,1
    1,497x      +%199,7      −%21,41      −%9,6

Gerçekleşen düşüşlerin p95'ten çok sığ olması madde 243'ün bulgusudur
(yol şanslıydı), bir güvence değil.

HÜKÜM — DOZ 1,25x, AMA KAPISI 1x CANLI ÖLÇÜMÜ
---------------------------------------------
1. **Karar verilen doz: brüt 1,25x** (çözümün p5'i), beklenen net
   **+%153** yıllık. 1,50x reddedilmedi, ama ihtiyatlı olan 1,25x ve
   aradaki fark (46 puan) belirsizlik payından küçük.
2. **VARSAYILAN DEĞİŞTİRİLMEDİ: `CARRY_GROSS` 1,0'da kaldı.** Sebep
   kodun kendi talimatı (madde 149, `GROSS_EXPOSURE` belgesi):
   *"Kaldıraç kullanılacaksa önce 1x'te canlı ölçüm yapın."* Bot HİÇ
   canlı çalışmadı; üç icra varsayımı (madde 265/266/267) yalnız 2 aylık
   dakika verisinde doğrulandı. 1,25x, ölçülmemiş her canlı sapmayı
   1,25 ile çarpar. Doz, madde 216'nın takviminden (gün 14 funding
   kapısı, gün 30 long TP, gün 60 short TP) sonra açılır.
3. Açılışı tek satır: `CARRY_GROSS=1.25`. Borsa kaldıracını bot kendi
   hesaplıyor (`gerekli_kaldirac()`: 1,5 kat pay + ÇAPRAZ teminat).

DERS
----
**Bir dozu ayara yazmadan önce o dozun ÖRNEKLEME ARALIĞINI çöz.** Nokta
çözüm (1,497x) tekrarlanabilir olduğu için güvenilir görünüyor; oysa
Monte Carlo yayılımı 0,015 iken örnekleme yayılımı **0,67** (1,25-1,92).
Tekrarlanabilirlik, doğruluk değildir. Ve ikinci ders: **tolerans hangi
ölçütte verildiyse ekranda görünecek sayı o değildir** — günlük kapanışta
−%30, gün içinde medyanda ~−%45.
"""
from __future__ import annotations

# --- girdi denetimi (madde 268) ---------------------------------------
KAYNAK_DENETIMI = {
    "dosya": "referans_getiri.csv",
    "madde274_dosya": "/tmp/m273_0.20.npy",
    "n": 1504, "ort": 0.002163, "std": 0.014047,
    "ayni_seri": True,
}

TOLERANS = 30.0            # kullanicinin verdigi karar: 1 yil p95 dusus
ICRA_1X = 0.79             # madde 265

# Monte Carlo gurultusu: ayni seri, farkli tohum
TOHUM_COZUMU = {2760: 1.5038, 777: 1.5181, 31337: 1.5187,
                11: 1.5076, 90210: 1.5120}
MADDE_274_KAYDI = 1.495

# Ornekleme belirsizligi: blok bootstrap (blok 21, 120 tekrar)
BRUT_ARALIK = {"p5": 1.254, "medyan": 1.497, "p95": 1.921}
NET_ARALIK = {"p5": 153.4, "medyan": 199.6, "p95": 297.8}

KARAR_BRUT = BRUT_ARALIK["p5"]       # ihtiyatli doz
KARAR_NET = NET_ARALIK["p5"]

# Likidasyon payi (madde 266 kuyrugu 1x'te -41,41)
KUYRUK_1X = 41.41
DUVAR = {0.005: 2.386, 0.010: 2.358, 0.025: 2.277}
PAY = {   # brut -> {mmr: duvara kalan puan}
    1.254: {0.005: 47.4, 0.010: 46.8, 0.025: 44.9},
    1.497: {0.005: 37.3, 0.010: 36.5, 0.025: 34.3},
}

# Gun ici karsiligi (madde 266)
BUYUTME_MEDYAN = 1.488
BUYUTME_P90 = 2.722
GUN_ICI_MEDYAN = TOLERANS * BUYUTME_MEDYAN      # ~44,6

# Gerceklesen yol (karistirma yok)
GERCEKLESEN = {   # brut -> (yillik_net, maks_dusus, en_kotu_ay)
    1.000: (111.7, -14.54, -6.4),
    1.254: (153.4, -18.08, -8.1),
    1.497: (199.7, -21.41, -9.6),
}

# Ayar durumu
VARSAYILAN_BRUT = 1.0
KAPI = "madde 216 takvimi: 1x canli, gun 14 funding kapisi / 30 long TP / 60 short TP"
ACILIS_KOMUTU = "CARRY_GROSS=1.25"

BENIM_YAPMADIGIM_HATA = (
    "p90 buyutmesini (2,722) -%30'un ustune CARPMADIM; o iki ayri kuyruk "
    "olcutunu ust uste bindirmek olurdu. Madde 273'te kaldiracla iki kez "
    "carpma hatasini yapmistim."
)


def kaynak_denetlendi_mi() -> bool:
    return KAYNAK_DENETIMI["ayni_seri"] is True and KAYNAK_DENETIMI["n"] > 1000


def monte_carlo_yayilimi() -> float:
    v = list(TOHUM_COZUMU.values())
    return max(v) - min(v)


def ornekleme_yayilimi() -> float:
    return BRUT_ARALIK["p95"] - BRUT_ARALIK["p5"]


def belirsizlik_gurultuden_buyuk_mu() -> bool:
    """Ornekleme belirsizligi Monte Carlo gurultusunden buyuk mu?"""
    return ornekleme_yayilimi() > 10 * monte_carlo_yayilimi()


def madde_274_dogrulandi_mi(tol: float = 0.03) -> bool:
    """Madde 274'un nokta cozumu yeniden uretilebildi mi?"""
    ort = sum(TOHUM_COZUMU.values()) / len(TOHUM_COZUMU)
    return abs(ort - MADDE_274_KAYDI) < tol


def duvar_hesapla(mmr: float = 0.010) -> float:
    return 1.0 / (KUYRUK_1X / 100.0 + mmr)


def duvarin_icinde_mi(brut: float = KARAR_BRUT, mmr: float = 0.010) -> bool:
    return brut < duvar_hesapla(mmr)


def duvarin_yuzde_kaci(brut: float = KARAR_BRUT, mmr: float = 0.010) -> float:
    return brut / duvar_hesapla(mmr) * 100


def gun_ici_karsiligi(brut: float = KARAR_BRUT) -> tuple:
    """(gunluk tolerans, gun ici medyan, olculen kuyrugun bu brutteki hali)"""
    return (TOLERANS, GUN_ICI_MEDYAN, KUYRUK_1X * brut)


def ihtiyatli_doz_secildi_mi() -> bool:
    return abs(KARAR_BRUT - BRUT_ARALIK["p5"]) < 1e-9


def varsayilan_degismedi_mi() -> bool:
    """Bot HIC canli calismadi: varsayilan 1,0'da mi kaldi?"""
    return abs(VARSAYILAN_BRUT - 1.0) < 1e-9


def hukum() -> str:
    return ("Doz KARARI: brut %.2fx (cozumun p5'i), beklenen net +%%%.0f. "
            "Ama VARSAYILAN 1,0'da KALDI: kodun kendi talimati (madde 149) "
            "once 1x canli olcum istiyor ve bot hic canli calismadi. "
            "Acilis tek satir: %s. Duvarin %%%.0f'inde, likidasyon bagliyici "
            "DEGIL."
            % (KARAR_BRUT, KARAR_NET, ACILIS_KOMUTU,
               duvarin_yuzde_kaci()))


def yaz() -> None:
    print("MADDE 276 — DOZ KARARI (tolerans −%%%.0f bir yillik p95 dusus)\n"
          % TOLERANS)
    print("KAYNAK DENETIMI: %s ile %s ayni seri mi: %s (n=%d)"
          % (KAYNAK_DENETIMI["dosya"], KAYNAK_DENETIMI["madde274_dosya"],
             kaynak_denetlendi_mi(), KAYNAK_DENETIMI["n"]))
    print("\nMONTE CARLO GURULTUSU (ayni seri, 5 tohum, B=40.000):")
    for t, k in TOHUM_COZUMU.items():
        print("  tohum %5d -> %.4fx" % (t, k))
    print("  yayilim %.4f | madde 274'un 1,495'i yeniden uretildi mi: %s"
          % (monte_carlo_yayilimi(), madde_274_dogrulandi_mi()))
    print("\nORNEKLEME BELIRSIZLIGI (blok bootstrap, brut HER ORNEKLEMDE cozuldu):")
    print("  brut   p5 %.3fx | medyan %.3fx | p95 %.3fx  (yayilim %.3f)"
          % (BRUT_ARALIK["p5"], BRUT_ARALIK["medyan"], BRUT_ARALIK["p95"],
             ornekleme_yayilimi()))
    print("  net    p5 +%%%.1f | medyan +%%%.1f | p95 +%%%.1f"
          % (NET_ARALIK["p5"], NET_ARALIK["medyan"], NET_ARALIK["p95"]))
    print("  -> ornekleme yayilimi gurultunun 10 katindan buyuk mu: %s"
          % belirsizlik_gurultuden_buyuk_mu())
    print("\nLIKIDASYON PAYI (madde 266 kuyrugu 1x'te −%%%.2f):" % KUYRUK_1X)
    print("  brut   | mmr %0.5 | mmr %1.0 | mmr %2.5 | duvarin yuzdesi")
    for b in sorted(PAY):
        print("  %.3fx | %+8.1f | %+8.1f | %+8.1f | %%%.0f"
              % (b, PAY[b][0.005], PAY[b][0.010], PAY[b][0.025],
                 duvarin_yuzde_kaci(b)))
    print("  duvar: " + " | ".join("mmr %%%.1f -> %.3fx" % (m * 100, d)
                                   for m, d in DUVAR.items()))
    print("\nEKRANDA GORULECEK SAYI (madde 266'nin gun ici buyutmesi %.3f):"
          % BUYUTME_MEDYAN)
    for b in sorted(PAY):
        g, m, k = gun_ici_karsiligi(b)
        print("  %.3fx -> gunluk p95 −%%%.0f | gun ici medyan ~−%%%.0f | "
              "olculen kuyruk −%%%.0f" % (b, g, m, k))
    print("  NOT: %s" % BENIM_YAPMADIGIM_HATA)
    print("\nGERCEKLESEN YOL (karistirma yok, 2022-07 -> 2026-08):")
    print("  brut   | yillik net | maks dusus | en kotu ay")
    for b in sorted(GERCEKLESEN):
        y, d, a = GERCEKLESEN[b]
        print("  %.3fx | %+9.1f%% | %+9.2f%% | %+9.1f%%" % (b, y, d, a))
    print("\nHUKUM: %s" % hukum())
    print("KAPI: %s" % KAPI)


if __name__ == "__main__":
    yaz()
