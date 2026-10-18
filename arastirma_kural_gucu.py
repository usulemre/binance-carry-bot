#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 289 — KURALIN GÜÇ EĞRİSİ ÖLÇÜLDÜ: YANLIŞ GEÇME %20, VE
ÇEŞİTLENDİRİCİLERİ BLOKLAYAN ŞART, ŞART 1 DEĞİL ŞART 4.

Madde 288 tek bir karıştırılmış plasebonun `gecer_mi()`'den geçtiğini
göstermişti. Bu madde onu bir ÖLÇÜME çevirdi: kural, etkisi BİLİNEN
adaylar karşısında ne yapıyor?

YÖNTEM. Gürültünün ŞEKLİ gerçekten alınıyor: d = aday − kontrol (madde
288'in e0,10/ref150 adayı, günlük, faz ortalaması; izleme/kitap oranı
**0,079**). d'nin ortalaması sıfırlanıp blok bootstrap (21 gün) ile
yeniden örnekleniyor, üzerine bilinen bir δ ekleniyor, kontrol SABİT
tutuluyor — yani kıyas eşli, tam kuralın yaptığı gibi. Her sahte aday
`gecer_mi()`'ye veriliyor.

DOĞRULAMA. Simülasyon yanlış geçmeyi %18,3 dedi; motorla üretilen 10
bağımsız karıştırılmış plasebo (`BRUT_PLASEBO=2`, tohum 11-20)
**%20,0** verdi (2/10). Şart 1'de simülasyon %22,0, motor %20,0. Yani
simülasyon motorda doğrulanmış durumda.

═══ BULGU 1 — KURAL HER İKİ YÖNDE DE ZAYIF ═══

Sıkı eşleşen bir aday için (izleme oranı 0,079):

    gerçek etki    şart 1   şart 3   DÖRDÜ DE
    0 (null)        %22,0    %47,0    **%18,3**   <- yanlış geçme
    +1,33 puan      %48,3    %73,0      %43,0     <- gerçek kazancın
    +2,65 puan      %85,3    %92,0      %80,3        %57'si ELENİYOR
    +5,31 puan     %100,0    %98,7      %98,7

Şart 2 (düşüş toleransı 3 puan) bu kolda HER ZAMAN geçiyor — yani
eleyen şey şart 1 ve şart 3. Şart 1'in null'da %22'si, "iki alt dönemde
de iyileşme" isteyen bir testin iki BAĞIMSIZ yazı-turaya dönüşmesinin
ölçülmüş hâli (%25 beklenirdi).

İzleme hatası 3 katına çıkınca güç çöküyor: +2,65 puanda **%23,7**.
Yani küçük ağırlıklı bir harman için gerçek bir kazanç dörtte üçü
oranında reddediliyor.

═══ BENİM HATAM VE DÜZELTMESİ ═══

İlk kurguda bir "izleme ×10" kolu vardı ve her şeyi reddediyordu (güç
%1,7). O kolu `kontrol + BÜYÜK bağımsız gürültü` diye üretmiştim — o
bir BAŞKA KİTAP değil, kontrolün BOZULMUŞ hâli: oynaklığı artıyor,
Sharpe'ı düşüyor, düşüşü derinleşiyor. Kuralın onu reddetmesi bir güç
eksikliği DEĞİL, doğru karardır. ×1 ve ×3 kolları geçerli, ×10 kolu
geçersiz ve yayımlanmadı.

DOĞRU KURGU: aday = (1−w)·kontrol + w·öteki_kitap; ötekinin kendi
Sharpe'ı var ve harman ÇEŞİTLENDİRME ile oynaklığı DÜŞÜRÜYOR. Sicildeki
"%10 dilim" adaylarının (madde 285) gerçek şekli budur. Ve bu kurguyla
tablo tamamen değişti.

═══ BULGU 2 — ÇEŞİTLENDİRİCİDE BAĞLAYICI ŞART, ŞART 4'TÜR ═══

%10 dilim, korelasyonsuz, kontrolün Sharpe'ı 2,940:

    öteki Sh   harman etkisi   şart 1   şart 3   ŞART 4   DÖRDÜ DE
      1,0        −5,34 pt       %75,3    %80,3    **%1,0**   %0,0
      2,0        −2,56 pt       %99,0    %97,0    **%5,3**   %5,0
      3,0        +0,16 pt      %100,0    %99,7     %73,0    %72,7
      4,0        +2,80 pt      %100,0   %100,0     %99,0    %99,0

Düşük Sharpe'lı bir dilim oynaklığı düşürdüğü için şart 1 ve 3'ten
RAHATÇA geçiyor; üstünlüğü ancak KALDIRAÇLA toplanabildiği için şart 4
kapatıyor. Bu, madde 225/227'nin tam olarak amaçladığı davranıştır.

EŞİK, KİTABIN KENDİ SHARPE'I: 2,20 → %20,0 · 2,60 → %46,4 · 2,80 →
%53,6 · **2,94 → %71,6** · 3,10 → %78,8 · 3,40 → %90,8. Yazı-tura
noktası ~2,8, yani kontrolün Sharpe'ının hemen altı.

VE KORELASYON YARDIM ETMİYOR (öteki Sharpe 2,0, eşiğin altında):
ρ=−0,50 → %7,2 · ρ=−0,25 → %8,4 · ρ=0 → %7,6 · ρ=+0,25 → %3,6 ·
ρ=+0,50 → %1,6. Negatif korelasyon, sıfır korelasyona göre HİÇBİR ŞEY
kazandırmıyor. Pozitif korelasyon zarar veriyor.

**KURAL ÇEŞİTLENDİRMEYİ SIFIR FİYATLIYOR.** Sebebi mekanik: harmanın
getirisi ρ ne olursa olsun düşüyor, ve şart 4 o getiriyi geri almak
için kaldıraç kullanılmasını reddediyor. Düşüşün azalması tam olarak
şart 4'ün kaldıraçla ödemeyi reddettiği şeydir.

═══ BULGU 3 — ŞART 4 İLE DOZ ÖLÇÜTÜ TERS YÖNÜ GÖSTERİYOR ═══

%10 dilim, aynı sahte adaylar, iki kapı:

    öteki Sh  ρ      harman pt   düşüş   ŞART 4    DOZ FARKI
      2,00  −0,50      −4,09     12,07    %5,0     **+83,64**
      2,00   0,00      −1,20     12,99    %7,5     **+41,24**
      2,50  −0,50      −2,24     11,86   %27,5     **+96,28**
      1,50  −0,50      −4,51     12,02    %2,5     **+72,73**

(kontrol: düşüş 14,54 · doz 1,505x · net +%200,85)

İki kapı farklı şeyler söylemiyor — **ZIT** şeyler söylüyor, hem de
devasa bir marjla. Çünkü iki ayrı KARARI ölçüyorlar: şart 4 "getiriyi
kaldıraçla satın alma" diyor; doz ölçütü "kullanıcının verdiği −%30
toleransına kadar al" diyor. Ve o toleransı kullanıcı **madde 276'da
verdi** — şart 4 ise **madde 225/227'de**, yani o cevaptan ÖNCE
yazıldı. İkisi birlikte duramaz. **KURAL DEĞİŞTİRİLMEDİ** (madde
212'nin kapattığı delik); çelişki kullanıcıya bırakıldı.

═══ BULGU 4 — KARARI SABİT BRÜTTE SOR (asıl kullanılabilir sayı) ═══

Doz ölçütünün +84 puanı brütü ~1,7x'e çıkarmaya dayanıyor; madde 276
ihtiyatlı dozu **1,25x**'te kesti. Aynı adaylar, SABİT 1,25x'te
(kontrol @1,25x: CAGR +%153,37 · Sharpe 2,939 · maks düşüş −18,02):

    öteki Sh  ρ      CAGR fark  harman Sh  düşüş fark   kur
      2,00  −0,50     −3,39       3,341      −3,11     1,09 pt/pt
      2,00   0,00     −4,40       3,154      −1,96     2,24 pt/pt
      2,50  −0,50     **−0,13**   **3,385**  **−3,24** **0,04 pt/pt**
      1,50  −0,50     −9,40       3,254      −3,04     3,09 pt/pt
      2,94   0,00     **+2,83**     3,250      −2,29     BEDAVA

Madde 280 "düşüşü azaltmak bedava değildir" demişti. Bu madde onu
FİYATLIYOR: sabit brütte kur, dilimin KENDİ Sharpe'ına göre **1 puan
düşüş başına 0,04 ile 3,09 puan getiri** arasında değişiyor. Sharpe
2,5 ve ρ=−0,5 olan bir dilim neredeyse BEDAVA (−0,13 puan) 3,24 puan
düşüş kesiyor ve Sharpe'ı 2,939 → 3,385'e çıkarıyor — ve şart 4 onu
%72,5 oranında reddediyor.

═══ ARAMA ŞARTNAMESİ (madde 237/239'un reçetesinin düzeltmesi) ═══

Madde 237 "farklı SİNYAL değil farklı YAPI/PİYASA ara" demişti; madde
239 bunu sistematik uyguladı. Eksik olan şey şuydu: **farklı yapı tek
başına MÜKEMMEL olmadıkça işe yaramıyor; yalnızca korelasyonsuz olması
HİÇBİR ŞEY kazandırmıyor.** Ölçülmüş şartname:

    - tek başına Sharpe **>= 2,5** (ideal >= 2,94 = kitabın kendisi)
    - korelasyon <= 0 (negatif olması şart 4 için fark yaratmıyor ama
      sabit brütte takas kurunu iyileştiriyor)
    - ağırlık ~%10 (izleme oranını 0,14'te tutar, kuralın güç
      aralığında kalır)

Sicildeki bütün dilim/harman redleri (285 kontrarian dilim, 239(A)
vade merdiveni, 282, 279) bu şartnamenin ALTINDAYDI; redleri doğruydu
ama GEREKÇELERİ eksik yazılmıştı: "bootstrap çökertiyor" değil, "tek
başına Sharpe'ı yetmiyor".

DİKKAT: yukarıdaki çeşitlendiriciler SİMÜLASYON (sentetik Gauss
kitapları). Projede böyle bir kitap BULUNMADI. Bu tablo, aramanın
TUTMASI GEREKEN ŞARTNAMEyi söylüyor; böyle bir kitabın var olduğunu
söylemiyor.
"""

# --- dogrulama: simulasyon vs motor --------------------------------
SIMULASYON_NULL = {"sart1": 22.0, "sart2": 100.0, "sart3": 47.0,
                   "sart4": 86.0, "dordu": 18.3}
MOTOR_NULL = {"n": 10, "sart1": 2, "sart2": 10, "sart3": 7, "sart4": 10,
              "dordu": 2}
MOTOR_NULL_TOHUM = tuple(range(11, 21))
IZLEME_ORANI = 0.079

# --- guc egrisi: (izleme olcegi, delta kati) -> (yillik pt, sart1, dordu)
GUC = {
    (1.0, 0.00): (0.00, 22.0, 18.3),
    (1.0, 0.50): (1.33, 48.3, 43.0),
    (1.0, 1.00): (2.65, 85.3, 80.3),
    (1.0, 2.00): (5.31, 100.0, 98.7),
    (1.0, 4.00): (10.61, 100.0, 100.0),
    (3.0, 0.00): (0.00, 10.0, 7.7),
    (3.0, 0.50): (1.33, 17.7, 13.0),
    (3.0, 1.00): (2.65, 29.7, 23.7),
    (3.0, 2.00): (5.31, 53.3, 43.7),
    (3.0, 4.00): (10.61, 93.0, 84.3),
}
GERCEK_ADAY_ETKI_PT = 2.65          # madde 288'in adayi, aritmetik yillik

# --- benim hatam ----------------------------------------------------
HATAM = {
    "ne": "'izleme x10' kolunu kontrol + BUYUK bagimsiz gurultu diye urettim",
    "neden_gecersiz": "o bir BASKA KITAP degil kontrolun BOZULMUS hali: "
                      "oynaklik artiyor, Sharpe dusuyor, dusus derinlesiyor",
    "yanlis_sonuc": "guc %1,7 -> 'kural hicbir cesitlendiriciyi gecirmez'",
    "dogru_kurgu": "aday = (1-w)*kontrol + w*oteki_kitap (cesitlendirme "
                   "oynakligi DUSURUR)",
    "yayimlandi_mi": False,
}

# --- harman kolu: (w, oteki Sharpe) -> (harman pt, s1, s3, s4, dordu)
HARMAN = {
    (0.10, 1.0): (-5.34, 75.3, 80.3, 1.0, 0.0),
    (0.10, 2.0): (-2.56, 99.0, 97.0, 5.3, 5.0),
    (0.10, 3.0): (+0.16, 100.0, 99.7, 73.0, 72.7),
    (0.10, 4.0): (+2.80, 100.0, 100.0, 99.0, 99.0),
    (0.25, 1.0): (-12.89, 58.3, 64.0, 6.7, 0.0),
    (0.25, 2.0): (-6.41, 96.3, 94.3, 8.7, 7.3),
    (0.25, 3.0): (+0.58, 100.0, 99.7, 73.0, 73.0),
    (0.25, 4.0): (+7.26, 100.0, 100.0, 99.7, 99.7),
}
KONTROL_SHARPE = 2.940

# --- esik taramasi: oteki Sharpe -> dordu de gecme % ----------------
ESIK = {2.20: 20.0, 2.60: 46.4, 2.80: 53.6, 2.94: 71.6, 3.10: 78.8,
        3.40: 90.8}

# --- korelasyon: rho -> dordu de gecme % (oteki Sharpe 2.0) ---------
KORELASYON = {-0.50: 7.2, -0.25: 8.4, 0.00: 7.6, 0.25: 3.6, 0.50: 1.6}

# --- sart 4 vs doz olcutu: (oteki Sh, rho) -> (pt, dusus, s4%, doz) -
IKI_KAPI = {
    (2.00, -0.50): (-4.09, 12.07, 5.0, 83.64),
    (2.00, 0.00): (-1.20, 12.99, 7.5, 41.24),
    (2.50, -0.50): (-2.24, 11.86, 27.5, 96.28),
    (1.50, -0.50): (-4.51, 12.02, 2.5, 72.73),
}
KONTROL_DUSUS = 14.54
KONTROL_DOZ = (1.505, 200.85)

# --- sabit 1,25x: (oteki Sh, rho) -> (CAGR fark, harman Sh, dusus fark)
SABIT_BRUT = 1.25
SABIT = {
    (2.00, -0.50): (-3.39, 3.341, -3.11),
    (2.00, 0.00): (-4.40, 3.154, -1.96),
    (2.50, -0.50): (-0.13, 3.385, -3.24),
    (1.50, -0.50): (-9.40, 3.254, -3.04),
    (2.94, 0.00): (+2.83, 3.250, -2.29),
}
KONTROL_SABIT = (153.37, 2.939, -18.02)

# --- arama sartnamesi ----------------------------------------------
SARTNAME = {"tek_basina_sharpe_min": 2.5, "ideal_sharpe": KONTROL_SHARPE,
            "korelasyon_max": 0.0, "agirlik": 0.10,
            # MADDE 298 EKLEMESI - asagidaki nota bak:
            "plasebo_sharpe": 1.999, "plaseboyu_gecme_P_min": 95.0}
SARTNAME_MADDE298_NOTU = (
    "MADDE 298: 'tek basina Sharpe >= 2,5' esigi SIFIRA karsi okunamaz. "
    "Bu makine (15 dilim + TP hasadi + rezerv + kalabalik havuzu) HIC "
    "SINYAL YOKKEN Sharpe 1,999 veriyor (skor paneli kesitsel "
    "karistirilmis plasebo). Yani 2,5 esiginin %80'i MAKINENIN KENDISI; "
    "bar zayiftir. Dogru sart: adayin PLASEBOYU gecmesi - esli blok "
    "bootstrap ile P(Sharpe_aday > Sharpe_plasebo) >= %95. Madde 298'in "
    "trend kitabi bunu gecti (%98,9), ham esigi ise kil payi gecmisti "
    "(2,535 >= 2,5).")
SIMULASYON_UYARISI = ("yukaridaki cesitlendiriciler SENTETIK Gauss "
                      "kitaplari; bu tablo aramanin tutmasi gereken "
                      "SARTNAMEyi soyler. *** MADDE 298 DUZELTMESI: bu not "
                      "eskiden 'projede boyle bir kitap BULUNMADI' diyordu; "
                      "ARTIK BULUNDU - madde 298'in 1 gunluk momentum "
                      "kitabi, tek basina Sharpe 2,535. AMA sartnamenin "
                      "korelasyon kalemini TUTMUYOR: rho 0,741 (sart <= 0) "
                      "ve harmandaki dusus kazanci kendisine ait degil "
                      "(plasebo sleeve'i ayni dozu veriyor). ***")

# --- kullaniciya ait celiski ---------------------------------------
CELISKI = {
    "sart4": "madde 225/227 - 'esit riskteki ustunluk kaldirac gerektirmemeli'",
    "tolerans": "madde 276 - kullanici: '-30 tahammul ederim'",
    "sira": "sart 4, kullanicinin cevabindan ONCE yazildi",
    "kural_degistirildi_mi": False,
}


# --- sinamalar ------------------------------------------------------
def simulasyon_motorda_dogrulandi_mi(tol: float = 10.0) -> bool:
    """Simulasyonun yanlis-gecme orani motorun olctuguyle uyusuyor mu?"""
    motor = 100.0 * MOTOR_NULL["dordu"] / MOTOR_NULL["n"]
    return abs(SIMULASYON_NULL["dordu"] - motor) <= tol


def yanlis_gecme_orani_motorda() -> float:
    return 100.0 * MOTOR_NULL["dordu"] / MOTOR_NULL["n"]


def sart1_iki_yazi_tura_mi(tol: float = 6.0) -> bool:
    """Null'da sart 1, iki bagimsiz yazi-turaya (%25) yakin mi?"""
    return abs(SIMULASYON_NULL["sart1"] - 25.0) <= tol


def guc_gercek_adayda(olcek: float = 1.0) -> float:
    return GUC[(olcek, 1.00)][2]


def gercek_kazanc_eleniyor_mu(esik: float = 50.0) -> bool:
    """+1,33 puanlik GERCEK bir kazanc, yarisindan cok eleniyor mu?"""
    return GUC[(1.0, 0.50)][2] < esik


def izleme_buyurken_guc_dusuyor_mu() -> bool:
    return all(GUC[(3.0, k)][2] < GUC[(1.0, k)][2]
               for k in (0.0, 0.5, 1.0, 2.0, 4.0))


def hatam_yayimlanmadi_mi() -> bool:
    return HATAM["yayimlandi_mi"] is False


def cesitlendiricide_baglayici_sart_dort_mu() -> bool:
    """%10 dilim, oteki Sharpe 2,0: en kucuk gecme orani sart 4'te mi?"""
    pt, s1, s3, s4, hep = HARMAN[(0.10, 2.0)]
    return s4 < min(s1, s3)


def esik_kitabin_sharpe_i_mi(tol: float = 0.25) -> bool:
    """%50 gecme noktasi, kontrolun kendi Sharpe'inin yakininda mi?"""
    alt = max(s for s, g in ESIK.items() if g < 50.0)
    ust = min(s for s, g in ESIK.items() if g >= 50.0)
    return abs((alt + ust) / 2 - KONTROL_SHARPE) <= tol + 0.25


def korelasyon_yardim_ediyor_mu(tol: float = 3.0) -> bool:
    """Negatif korelasyon, sifir korelasyona gore kazandiriyor mu?"""
    return KORELASYON[-0.50] > KORELASYON[0.00] + tol


def iki_kapi_ters_mi() -> bool:
    """Sart 4 reddederken doz olcutu KABUL mu diyor? (Hepsinde.)"""
    return all(s4 < 50.0 and doz > 0 for _, (_, _, s4, doz) in IKI_KAPI.items())


def sabit_brutte_bedavaya_yakin_var_mi(esik: float = 0.5) -> bool:
    """Sabit 1,25x'te getiriden neredeyse hic vermeden dusus kesen var mi?"""
    return any(abs(dy) < esik and dd < -1.0 for dy, _, dd in SABIT.values())


def takas_kuru(oteki_sh: float, rho: float) -> float:
    """Sabit brutte: 1 puan dusus basina kac puan getiri."""
    dy, _, dd = SABIT[(oteki_sh, rho)]
    return abs(dy / dd)


def kural_degistirilmedi_mi() -> bool:
    return CELISKI["kural_degistirildi_mi"] is False


def hukum() -> str:
    return (
        "KURAL OLCULDU. Yanlis gecme %20,0 (motor, 2/10; simulasyon %18,3) "
        "ve gercek bir +1,33 puanlik kazanc %57 oraninda ELENIYOR; izleme "
        "hatasi 3 katina cikinca +2,65 puanda guc %23,7'ye dusuyor. AMA "
        "ASIL BULGU: cesitlendirici adaylarda baglayici sart SART 1 DEGIL "
        "SART 4'tur ve esik tam olarak KITABIN KENDI SHARPE'IDIR (~2,8-2,94); "
        "negatif korelasyon HICBIR SEY kazandirmiyor, yani kural "
        "cesitlendirmeyi SIFIR fiyatliyor. Sart 4 ile doz olcutu ayni "
        "adaylarda ZIT yon gosteriyor (sart 4 %5, doz +83,64 puan) cunku iki "
        "AYRI karari olcuyorlar ve sart 4, kullanicinin madde 276'daki "
        "'-30 tahammul ederim' cevabindan ONCE yazildi. KURAL "
        "DEGISTIRILMEDI; celiski kullaniciya ait. Sabit 1,25x'te takas "
        "kuru olculdu: 1 puan dusus basina 0,04-3,09 puan getiri, dilimin "
        "KENDI Sharpe'ina gore. Arama sartnamesi: tek basina Sharpe >= 2,5, "
        "korelasyon <= 0, agirlik ~%10 - yalnizca korelasyonsuz olmak "
        "HICBIR SEY kazandirmiyor."
    )


def yaz() -> None:
    print(__doc__)
    print("DOGRULAMA — simulasyon vs motor (null, karistirilmis plasebo):")
    print("  simulasyon: sart1 %%%.1f | dordu de %%%.1f"
          % (SIMULASYON_NULL["sart1"], SIMULASYON_NULL["dordu"]))
    print("  motor (n=%d, tohum %d-%d): sart1 %d/%d | dordu de **%d/%d = %%%.1f**"
          % (MOTOR_NULL["n"], MOTOR_NULL_TOHUM[0], MOTOR_NULL_TOHUM[-1],
             MOTOR_NULL["sart1"], MOTOR_NULL["n"], MOTOR_NULL["dordu"],
             MOTOR_NULL["n"], yanlis_gecme_orani_motorda()))
    print("  uyusuyor mu: %s | sart 1 iki yazi-tura mi: %s"
          % (simulasyon_motorda_dogrulandi_mi(), sart1_iki_yazi_tura_mi()))
    print("\nGUC EGRISI (izleme olcegi x delta):")
    print("  %7s %7s %10s | %7s %9s" % ("izleme", "delta", "yillik pt",
                                        "sart1", "DORDU DE"))
    for (o, kat), (pt, s1, hep) in sorted(GUC.items()):
        print("  x%-6.0f %7.2f %+10.2f | %6.1f%% %8.1f%%" % (o, kat, pt, s1, hep))
    print("  gercek kazanc eleniyor mu (+1,33'te): %s | izleme buyurken guc "
          "dusuyor mu: %s" % (gercek_kazanc_eleniyor_mu(),
                              izleme_buyurken_guc_dusuyor_mu()))
    print("\nBENIM HATAM: %s" % HATAM["ne"])
    print("  gecersiz cunku: %s" % HATAM["neden_gecersiz"])
    print("  yanlis sonuc: %s | yayimlandi mi: %s"
          % (HATAM["yanlis_sonuc"], HATAM["yayimlandi_mi"]))
    print("\nHARMAN KOLU (kontrol Sharpe %.3f):" % KONTROL_SHARPE)
    print("  %4s %9s %10s | %7s %7s %8s | %s"
          % ("w%", "oteki Sh", "harman pt", "sart1", "sart3", "SART4", "DORDU"))
    for (w, sh), (pt, s1, s3, s4, hep) in sorted(HARMAN.items()):
        print("  %4.0f %9.1f %+10.2f | %6.1f%% %6.1f%% %7.1f%% | %6.1f%%"
              % (w * 100, sh, pt, s1, s3, s4, hep))
    print("  baglayici sart 4 mu: %s" % cesitlendiricide_baglayici_sart_dort_mu())
    print("\nESIK (w=%10, rho=0):")
    for sh, g in sorted(ESIK.items()):
        print("  oteki Sharpe %.2f -> %%%.1f%s"
              % (sh, g, "   <- kitabin kendi Sharpe'i" if sh == 2.94 else ""))
    print("  esik kitabin Sharpe'i mi: %s" % esik_kitabin_sharpe_i_mi())
    print("\nKORELASYON YARDIM EDIYOR MU (oteki Sharpe 2,0):")
    for r, g in sorted(KORELASYON.items()):
        print("  rho %+.2f -> %%%.1f" % (r, g))
    print("  yardim ediyor mu: %s  -> KURAL CESITLENDIRMEYI SIFIR FIYATLIYOR"
          % korelasyon_yardim_ediyor_mu())
    print("\nIKI KAPI (kontrol: dusus %.2f, doz %.3fx/+%.2f):"
          % (KONTROL_DUSUS, KONTROL_DOZ[0], KONTROL_DOZ[1]))
    print("  %8s %6s %10s %8s %8s %11s"
          % ("oteki Sh", "rho", "harman pt", "dusus", "SART4", "DOZ FARKI"))
    for (sh, r), (pt, du, s4, doz) in sorted(IKI_KAPI.items()):
        print("  %8.2f %+6.2f %+10.2f %8.2f %7.1f%% %+11.2f"
              % (sh, r, pt, du, s4, doz))
    print("  iki kapi TERS mi: %s" % iki_kapi_ters_mi())
    print("\nSABIT %.2fx (kontrol: CAGR %+.2f Sharpe %.3f dusus %.2f):"
          % (SABIT_BRUT, *KONTROL_SABIT))
    print("  %8s %6s %10s %9s %11s %s"
          % ("oteki Sh", "rho", "CAGR fark", "harman Sh", "dusus fark", "kur"))
    for (sh, r), (dy, s, du) in sorted(SABIT.items()):
        print("  %8.2f %+6.2f %+10.2f %9.3f %+11.2f %.2f pt/pt"
              % (sh, r, dy, s, du, takas_kuru(sh, r)))
    print("  sabit brutte bedavaya yakin var mi: %s"
          % sabit_brutte_bedavaya_yakin_var_mi())
    print("\nARAMA SARTNAMESI: tek basina Sharpe >= %.1f (ideal %.2f), "
          "korelasyon <= %.1f, agirlik %%%.0f"
          % (SARTNAME["tek_basina_sharpe_min"], SARTNAME["ideal_sharpe"],
             SARTNAME["korelasyon_max"], SARTNAME["agirlik"] * 100))
    print("  UYARI: %s" % SIMULASYON_UYARISI)
    print("\nKULLANICIYA AIT CELISKI:")
    for k2, v in CELISKI.items():
        print("  %-22s %s" % (k2, v))
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
