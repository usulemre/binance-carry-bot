#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 298 — TREND KİTABI: GERÇEK BİR SİNYAL (PLASEBOYU %99 GEÇİYOR),
AMA DÜŞÜŞ AZALTMASI MOMENTUMA DEĞİL **HERHANGİ BİR İKİNCİ KİTABA** AİT.
BİR TEK-BAŞINA SHARPE EŞİĞİ, MAKİNENİN PLASEBO SHARPE'INI BİLMEDEN
ANLAMSIZDIR.

Madde 297 bir açık eksen bırakmıştı: kullanıcının USUSDT kazancı funding
değil **fiyat hareketi** ile alınmıştı, ve kitapta trend girdisi yok.
Madde 289'un şartnamesi geçerliydi: tek başına Sharpe >= 2,5.

═══ 0. KULLANICININ İŞLEMİ HANGİ KOLA AİT? ═══

Madde 297 "trend" demiş ama YÖNÜNÜ söylememişti. Ölçüldü (Eylül-Ekim 2026
verisi `data.binance.vision`'dan indirildi): 11 Ekim itibarıyla USUSDT'nin
getirisi **her** geriye bakışta negatif — 1g −%36,5 · 3g −%23,2 ·
7g −%10,0 · 14g −%55,5 · 30g −%22,8.

Yani **kaybedeni** shortladı. Bu, momentum kolunun SHORT tarafı; kazananı
shortlamak (ters kol) değil. Kesitsel ölçümde bu ayrım belirleyici:
momentum kazanıyor, ters kol sistematik kaybediyor.

═══ 1. ÖN TARAMA: PROJENİN HAM MOTORU (bt2) ═══

İlk koşuda HER ŞEY SIFIR çıktı — referans dahil. Sebep kod: `bt2`'nin
`min_bacak=8` varsayılanı ile `n=5` çelişiyor (`nn=min(5,m//2) <= 5 < 8`),
motor hiç işlem açmıyor. Madde 293'ün yasası: inanılmaz sonuç önce kod
hatası. `min_bacak=5` ile düzeltildi.

REFERANS ZORUNLU: carry kitabı AYNI ham motorda Sharpe **0,648**. Bunu
ölçmeden "trend Sharpe 1,02" hiçbir şey ifade etmez (ham motorda ne dilim,
ne TP hasadı, ne rezerv var, ve maliyet `KOM_TEK_YON=0,0006` — g33'ün üç
katı).

    gun   momentum (kazananı long)   ters (kazananı short)
     1       **Sh 1,022**                 −1,280
     3           0,819                    −1,001
     7           0,891                    −1,038
    14           0,516                    −0,678
    30           0,715                    −0,801
    60           0,598                    −0,621
    90           0,540                    −0,557

İki kol birbirinin kontrolü; işaret tartışmasız ve geriye bakışta tek
yönlü bozulma var. En iyi: 1 gün.

═══ 2. TAM MAKİNE (g33, SK_DOSYA ile dıştan skor paneli) ═══

Skor paneli nedensel: `C[i]/C[i-6k]-1`, işlem `cv[i+1]`'de. g33'ün
konvansiyonu bt2 ile aynı (düşük skor = LONG), bu kodda doğrulandı.

    kitap                        CAGR      Sh      dd    Sh22    Sh25     doz       net     rho
    KONTROL carry             +112,27   2,939   14,54   2,789   3,147  1,505x   +200,85   1,000
    mom 1g                    + 90,17 **2,535**  18,20   2,307   2,844  1,356x   +133,86 **0,741**
    mom 7g                    + 86,64   1,938   29,73   1,926   1,971  0,876x   + 73,27   0,714
    mom 30g                   + 76,82   1,731   30,48   1,621   1,883  0,802x   + 59,00   0,733
    ters 7g (isaret kontrolu) + 27,83   1,112   25,71   1,412   0,711  0,993x   + 26,86   0,424
    mom1 HASATSIZ             + 58,89   1,629   30,38   1,619   1,707  0,915x   + 52,64   0,562
    carry HASATSIZ            + 92,67   2,197   19,78   2,355   2,208  1,115x   +105,56   0,849
    **mom1 PLASEBO**          + 51,14 **1,999**  14,09   1,830   2,228  1,451x   + 78,11   0,781
    mom1 UCELE=0              + 90,57   2,361   20,39   2,265   2,508  1,199x   +113,54   0,717

═══ 3. YASA: TEK-BAŞINA SHARPE EŞİĞİ PLASEBOSUZ ANLAMSIZDIR ═══

Plasebo = mom1 skor panelinin her satırı kesitsel KARIŞTIRILDI (dağılım
korunur, sembol eşlemesi yok olur). Yani **hiç sinyal yok**, yalnız makine:
15 dilim, TP hasadı, rezerv, kalabalık havuzu.

O makine tek başına **Sharpe 1,999** veriyor. Demek ki:

    carry'nin SİNYALİ:     2,939 − 1,999 = **+0,94 Sharpe**
    momentumun SİNYALİ:    2,535 − 1,999 = **+0,54 Sharpe**

Madde 289'un "tek başına Sharpe >= 2,5" şartnamesi, makine tek başına
2,0 verdiğinde ZAYIF bir bardır. Doğru eşik sıfır değil **plasebodur**.

Bu eşikle ölçülünce momentum yine de GEÇİYOR:

    mom1 vs PLASEBO, tek başına:  net +133,86 vs +78,11 (+55,75)
                                  **P(Sharpe mom1 > plasebo) = %98,9**

═══ 4. MADDE 290'IN TUZAĞI YİNE ÇIKTI ═══

Hasatlı mom1'in bileşen muhasebesi "ham fiyat bacakları KAYBEDİYOR"
diyordu (LONG −85,9 · SHORT −26,9 puan/yıl), bütün kâr TP hasadından
(+258,5) ve LONG funding'den (+60,8) görünüyordu. Hasat KAPATILDI
(`TP=0 TPL=0 TPS=0`; `TPKAT` varsayılanı 0 olduğu için dirilmiyor, ve
kapanma ÇIKTIDAN doğrulandı: `kar-al fiyat +0,0`):

    hasatsız mom1:  LONG fiyat **+43,2** · SHORT fiyat **+30,0** (POZİTİF)

Yani "momentumun fiyat bacakları kaybediyor" bir DEFTER YAPAYIDIR.
Kurulum madde 290 ile aynı: kontrolün hasatsız hali +%93,4 / Sh 2,33 /
dd −20,6 çıktı — madde 290'ın rakamıyla birebir, yani karşılaştırma
geçerli.

Hasadın katkısı momentumda carry'den BÜYÜK:
    carry:     2,197 -> 2,939  (+0,74 Sharpe)
    momentum:  1,629 -> 2,535  (+0,91 Sharpe)
Momentum kitabı makineye carry'den DAHA BAĞIMLI.

═══ 5. HARMAN — VE ASIL BULGU ═══

    w     CAGR      Sh      dd    Sh22    Sh25     doz      net    dnet   P(Sh)
    0,0 +112,27   2,939   14,54   2,789   3,147  1,505x  +200,85   +0,00     -
    0,1 +110,30   2,968   13,74   2,796   3,205  1,547x  +205,50   +4,64 **%87,2**
    0,2 +108,27 **2,984** 12,93   2,792   3,247  1,582x **+208,46** +7,61 **%81,0**
    0,3 +106,18   2,985   12,12   2,774   3,272  1,599x  +207,25   +6,40   %72,8
    0,4 +104,04   2,968   12,29   2,742   3,276  1,603x  +203,09   +2,24   %63,9
    0,5 +101,84   2,934   13,13   2,697   3,257  1,594x  +196,13   −4,72   %54,0

ÖLÇÜ UYUŞMAZLIĞI DÜZELTİLDİ: ham günlük getiri farkının P(>0)'ı
w'nin HEPSİNDE %15,2 — çünkü çeşitlendiricinin kazancı ORTALAMADA değil
RİSKTE. Doğru nicelik Sharpe farkı (madde 289). Tabloda P(Sh) o.

w=0,2'de dört şart: şart 1 GEÇER (Sh22 +0,003, Sh25 +0,100), şart 2
GEÇER (düşüş −1,61 puan DAHA İYİ), şart 3 GEÇER (eşit riskte +15,3
puan), **şart 4 DÜŞER** (gereken kaldıraç 1,127x > 1,005).

Madde 289 bunu önceden söylemişti: *"çeşitlendiricide bağlayıcı şart
şart 1 değil ŞART 4'tür."* Doğrulandı — ve bu **şart 4'ten tek başına
düşen ÜÇÜNCÜ aday** (madde 290'ın SEC_volyuk'u ve madde 288'in
prim-brütü diğerleri).

═══ 6. SAĞLAMLIK: ADAYI KESEN TEST ═══

w=0,2'de sleeve DEĞİŞTİRİLDİ:

    sleeve      CAGR      Sh      dd     doz      net    dnet   P(Sh)
    mom1     +108,27   2,984   12,93  1,582x  +208,46   +7,61  %81,0
    mom7     +107,90   2,847   14,19  1,471x  +184,99  −15,87  %18,9
    mom30    +105,68   2,775   14,39  1,426x  +172,27  −28,59   %4,1
    PLASEBO  + 98,78   2,869   13,27 **1,583x** +187,06 −13,80  %11,1
    ters7    + 92,99   2,859   14,94 **1,632x** +182,58 −18,27  %23,4

İKİ ŞEY BİRDEN:

(a) **Düşüş azaltması momentuma AİT DEĞİL.** Plasebo harmanının dozu
    1,583x — mom1'in 1,582x'inden YÜKSEK; ters7'nin 1,632x, hepsinden
    yüksek. Yani ikinci bir eşitlik yolu eklemek düşüşü kendiliğinden
    düşürüyor; sinyalin bununla ilgisi yok. mom1'in katkısı yalnız
    harmanın CAGR'ını ayakta tutması.

(b) **Yalnız 1 günlük geriye bakış çalışıyor.** mom7 ve mom30 harmanları
    kontrolün ALTINA düşüyor. 7 geriye bakış × 2 işaret taranmıştı;
    mom1'in kazanması SEÇİM olabilir. Tek koruma: ham motor (bt2) da
    bağımsız olarak 1 günü en iyi saymıştı (1,022 vs 0,891 / 0,819) —
    ama aynı veri üzerinde.

Buna karşılık momentumun kendi katkısı plasebo harmanına karşı ölçüldü:

    mom1 harmanı vs PLASEBO harmanı: net +208,46 vs +187,06 (+21,40)
    **P(Sharpe mom1 harmanı > plasebo harmanı) = %99,4**

Yani +7,61'lik net kazanç şöyle ayrışıyor: genel çeşitlendirme
**−13,80**, momentumun sinyali üstüne **+21,40**.

═══ 7. YANLIŞ ÇIKAN TAHMİNİM ═══

`UCELE=0.40` (madde 196) pump olmuş coini LONG adaylığından çıkarıyor.
"Momentum kitabının tam istediği şeyi eliyor, kapatınca iyileşir"
dedim. YANLIŞ: UCELE=0 momentumu **bozuyor** (2,535 -> 2,361, net
+133,86 -> +113,54). Yani momentumun kenarı UÇLARDA değil ORTA
HAREKETLERDE. Bu madde 297'ye bağlanıyor: USUSDT tam bir uç hareket
(+%721 sonra −%65) ve kitabın orada kaybettiği yer de orası.

═══ 8. SERMAYE: KULLANICININ BAKİYESİNDE KOŞAMAZ ═══

Harman İKİ kitap demek, sermaye bölünür (madde 293: dilim tabanlı
çeşitlendirmenin sermaye tabanı 1/ağırlık ile büyür).

    bacak = bakiye x 0,400 / (N_DILIM x N_LEGS),  asgari bacak 10,00 $

    kurulum                   tek kitap asgari   w=0,2 sleeve icin TOPLAM
    15 x 5 (geri test)              1.875 $            **9.375 $**
    13 x 3 (madde 295 onerisi)        975 $            **4.875 $**

Ve TERS TENSİYON: kanıtı en güçlü ağırlık w=0,1 (P %87,2) DAHA ÇOK
sermaye istiyor (13x3 ile 9.750 $), çünkü sleeve küçüldükçe onu
besleyecek toplam büyüyor.

Kullanıcı 1.000-2.000 $ ile başlıyor. **Bu bulgu şimdilik
uygulanabilir DEĞİL.** Kayda geçiyor: ilk gerçekten her eksende
iyileşen ve kanıt barını geçen aday, sermaye eşiği ekli.

═══ 9. SONUÇ ═══

Trend kitabı gerçek: plaseboyu tek başına %98,9, harmanda %99,4
olasılıkla geçiyor ve madde 289'un şartnamesini (2,535 >= 2,5) sağlıyor.
Ama (i) tek bir geriye bakışta yaşıyor, (ii) rho 0,741 ile bağımsız
değil, (iii) düşüş kazancı kendisine ait değil, (iv) şart 4'ten düşüyor,
(v) 4.875 $'ın altında koşamaz.

AYAR DEĞİŞMEDİ.
"""

# ---------------------------------------------------------------- SABİTLER

ACIK_EKSEN_KAYNAK = 297
SARTNAME_SHARPE = 2.5
"""Madde 289'un tek-başına kitap şartnamesi."""

# --- 0. kullanicinin isleminin yonu (Eylul-Ekim 2026, data.binance.vision) ---
USUSDT_GIRIS_GETIRI = {1: -36.5, 3: -23.2, 7: -10.0, 14: -55.5, 30: -22.8}
"""%; 11 Ekim 2026 itibarıyla. HEPSİ negatif => KAYBEDENİ shortladı,
yani momentum kolunun SHORT tarafı, ters kol değil."""

# --- 1. ham motor (bt2) on taramasi ---
BT2_HATA = ("bt2 varsayilani min_bacak=8, n=5 ile celisiyor "
            "(nn=min(5,m//2)<=5<8) -> motor hic islem acmiyor, HER SEY "
            "SIFIR cikiyor. min_bacak=5 ile duzeltildi (madde 293'un yasasi).")
BT2_REFERANS_SHARPE = 0.648
"""carry kitabi AYNI ham motorda. Bunu olcmeden trend sayilari anlamsiz."""
BT2_KOM = 0.0006
"""KOM_TEK_YON: taker + kayma, g33'un 0,0002'sinin UC KATI."""
BT2_TARAMA = {
    #  gun: (momentum Sharpe, ters Sharpe)
    1:  (1.022, -1.280), 3: (0.819, -1.001), 7: (0.891, -1.038),
    14: (0.516, -0.678), 30: (0.715, -0.801), 60: (0.598, -0.621),
    90: (0.540, -0.557),
}

# --- 2. tam makine (g33) ---
KONTROL = {"cagr": 112.27, "sh": 2.939, "dd": 14.54, "sh22": 2.789,
           "sh25": 3.147, "doz": 1.505, "net": 200.85, "ro": 1.000}
KITAPLAR = {
    #  ad                 : (cagr,   sh,    dd,    sh22,  sh25,  doz,   net,    ro)
    "mom 1g":              (90.17, 2.535, 18.20, 2.307, 2.844, 1.356, 133.86, 0.741),
    "mom 7g":              (86.64, 1.938, 29.73, 1.926, 1.971, 0.876,  73.27, 0.714),
    "mom 30g":             (76.82, 1.731, 30.48, 1.621, 1.883, 0.802,  59.00, 0.733),
    "ters 7g":             (27.83, 1.112, 25.71, 1.412, 0.711, 0.993,  26.86, 0.424),
    "mom1 HASATSIZ":       (58.89, 1.629, 30.38, 1.619, 1.707, 0.915,  52.64, 0.562),
    "carry HASATSIZ":      (92.67, 2.197, 19.78, 2.355, 2.208, 1.115, 105.56, 0.849),
    "mom1 PLASEBO":        (51.14, 1.999, 14.09, 1.830, 2.228, 1.451,  78.11, 0.781),
    "mom1 UCELE=0":        (90.57, 2.361, 20.39, 2.265, 2.508, 1.199, 113.54, 0.717),
}
SKOR_NEDENSEL = "C[i]/C[i-6k]-1, islem cv[i+1]'de; g33 konvansiyonu dusuk=LONG."

# *** MADDE 299 DUZELTMESI - BU TABLODA BIR KARISIM VARDI ***
MADDE299_KARISIMI = (
    "Momentum panelleri ham gecmis getiriydi (~0,1 olcegi); motor "
    "REZ_ESIK=0,015'i sinyalin BUYUKLUGUYLE kiyasladigi icin firsat "
    "rezervi momentum kollarinda 176-218 kez/yil devreye girdi, kontrolde "
    "58. Yani yukaridaki momentum-vs-KONTROL karsilastirmasi rezerv "
    "davranisini da iceriyordu. (momentum-vs-PLASEBO etkilenmedi: ikisi de "
    "ayni birim olceginde.) Madde 299'da uc kol REZERV=0 ile yeniden "
    "kosuldu: mom1 Sharpe 2,543 (burada 2,535), plasebo 2,016 (1,999), "
    "plaseboyu gecme P %98,9 (%98,9) -> BU MADDENIN HUKMU AYAKTA. Ustelik "
    "karisimin yonu momentumun ALEYHINEYDI (rezervden carry yararlaniyordu: "
    "3,10 -> 2,88; momentum 2,62 -> 2,64), yani bu tablo momentumu "
    "oldugundan IYI degil hafifce KOTU gosteriyor.")
MADDE299_REZERV_KULLANIMI = {"kontrol": 58, "mom1": 214, "mom7": 218,
                             "mom30": 218, "ters7": 192, "PLASEBO": 176}
MADDE299_TEMIZ = {"carry": 2.879, "mom1": 2.543, "plasebo": 2.016}


def madde299_karisimi_hukmu_degistirdi_mi() -> bool:
    """REZERV=0 ile yeniden olculunce bu maddenin hukmu degisti mi?"""
    return not (abs(MADDE299_TEMIZ["mom1"] - KITAPLAR["mom 1g"][1]) < 0.05
                and abs(MADDE299_TEMIZ["plasebo"] - PLASEBO_SHARPE) < 0.05)

# --- 3. PLASEBO: makinenin tek basina odedigi ---
PLASEBO_TANIMI = ("mom1 skor panelinin her satiri KESITSEL karistirildi: "
                  "dagilim korunur, sembol eslemesi yok olur. Hic sinyal yok, "
                  "yalniz makine (15 dilim + TP hasadi + rezerv + havuz).")
PLASEBO_SHARPE = 1.999
SINYAL_DEGERI = {"carry": 2.939 - 1.999, "momentum": 2.535 - 1.999}
MOM_VS_PLASEBO = {"net_aday": 133.86, "net_plasebo": 78.11, "P_sharpe": 98.9}

# --- 4. madde 290'in tuzagi ---
HASATLI_MUHASEBE = {"LONG fiyat": -85.9, "SHORT fiyat": -26.9,
                    "LONG tp": 166.4, "SHORT tp": 92.1,
                    "LONG funding": 60.8, "SHORT funding": 4.4}
HASATSIZ_MUHASEBE = {"LONG fiyat": 43.2, "SHORT fiyat": 30.0,
                     "LONG tp": 0.0, "SHORT tp": 0.0,
                     "LONG funding": 85.4, "SHORT funding": 1.4}
HASAT_KAPATMA = "TP=0 TPL=0 TPS=0 (TPKAT varsayilani 0); CIKTIDAN dogrulandi"
HASAT_KATKISI = {"carry": 2.939 - 2.197, "momentum": 2.535 - 1.629}
MADDE290_PARITE = {"carry hasatsiz cagr": 93.4, "carry hasatsiz sharpe": 2.33,
                   "carry hasatsiz dd": 20.6}
"""Madde 290'in rakamiyla birebir -> hasat-kapali kurulum AYNI, karsilastirma gecerli."""

# --- 5. harman ---
HARMAN = {
    #  w  : (cagr,   sh,    dd,    sh22,  sh25,  doz,   net,    P(Sh)%)
    0.0: (112.27, 2.939, 14.54, 2.789, 3.147, 1.505, 200.85, None),
    0.1: (110.30, 2.968, 13.74, 2.796, 3.205, 1.547, 205.50, 87.2),
    0.2: (108.27, 2.984, 12.93, 2.792, 3.247, 1.582, 208.46, 81.0),
    0.3: (106.18, 2.985, 12.12, 2.774, 3.272, 1.599, 207.25, 72.8),
    0.4: (104.04, 2.968, 12.29, 2.742, 3.276, 1.603, 203.09, 63.9),
    0.5: (101.84, 2.934, 13.13, 2.697, 3.257, 1.594, 196.13, 54.0),
}
BAR_P = 80.0
HAM_GETIRI_P = 15.2
OLCU_UYUSMAZLIGI = (
    "Ham gunluk getiri farkinin P(>0)'i w'nin HEPSINDE %15,2 - cunku "
    "cesitlendiricinin kazanci ORTALAMADA degil RISKTE. Dogru nicelik "
    "Sharpe farki (madde 289). Yanlis nicelikle olculurse aday REDDEDILIR. "
    "(MADDE 300: ters yonu de olculdu - yanlis nicelik haksiz KABUL de "
    "eder; 13x3'te TPL 0,55'i ham getiri olcusu %95,9 ile kabul ederdi.)")
SART4_DUSEN_ADAY_SAYISI = 3
"""Madde 288 prim-brut, madde 290 SEC_volyuk, madde 298 trend harmani."""
HARMAN_KALDIRAC = {0.2: 1.127, 0.3: 1.203}

# --- 6. saglamlik: adayi kesen test ---
SLEEVE_DEGISTI = {
    #  sleeve  : (cagr,   sh,    dd,    doz,   net,    dnet,   P(Sh)%)
    "mom1":    (108.27, 2.984, 12.93, 1.582, 208.46,   7.61, 81.0),
    "mom7":    (107.90, 2.847, 14.19, 1.471, 184.99, -15.87, 18.9),
    "mom30":   (105.68, 2.775, 14.39, 1.426, 172.27, -28.59,  4.1),
    "PLASEBO": ( 98.78, 2.869, 13.27, 1.583, 187.06, -13.80, 11.1),
    "ters7":   ( 92.99, 2.859, 14.94, 1.632, 182.58, -18.27, 23.4),
}
HARMAN_VS_PLASEBO = {"net_aday": 208.46, "net_plasebo": 187.06,
                     "fark": 21.40, "P_sharpe": 99.4}
AYRISMA = {
    # MADDE 298: elle yazilmasin - yayinlanan netlerden TURETILIR, yoksa
    # yuvarlama yuzunden toplami tutmaz (ilk yazimda -13,80 yazmistim,
    # dogrusu 187,06 - 200,85 = -13,79).
    "genel cesitlendirme": round(SLEEVE_DEGISTI["PLASEBO"][4] - 200.85, 2),
    "momentumun sinyali": round(
        SLEEVE_DEGISTI["mom1"][4] - SLEEVE_DEGISTI["PLASEBO"][4], 2),
    "toplam (kontrole karsi)": round(SLEEVE_DEGISTI["mom1"][4] - 200.85, 2),
}
TARANAN_KOMBINASYON = 7 * 2
"""bt2'de 7 geriye bakis x 2 isaret; mom1'in kazanmasi SECIM olabilir."""

# --- 7. yanlis cikan tahminim ---
TAHMIN_YANLIS = (
    "UCELE=0.40 (madde 196) pump olmus coini LONG adayligindan cikarir. "
    "'Momentumun istedigini eliyor, kapatinca iyilesir' dedim. YANLIS: "
    "UCELE=0 momentumu BOZUYOR (2,535 -> 2,361; net +133,86 -> +113,54). "
    "Momentumun kenari UCLARDA degil ORTA HAREKETLERDE - ve madde 297'de "
    "kitabin USUSDT'de kaybettigi yer de tam o uc hareketti.")

# --- 8. sermaye esigi ---
TABAN_PAYI = 0.400
ASGARI_BACAK = 10.00
SERMAYE_ESIGI = {
    #  kurulum : (tek kitap asgari $, w=0,2 sleeve icin TOPLAM $)
    "15x5": (1875.0, 9375.0),
    "13x3": (975.0, 4875.0),
}
TERS_TENSIYON = ("Kaniti en guclu agirlik w=0,1 (P %87,2) DAHA COK sermaye "
                 "istiyor (13x3 ile 9.750 $): sleeve kuculdukce onu "
                 "besleyecek TOPLAM buyur.")
KULLANICI_BAKIYE = (1000.0, 2000.0)

AYAR_DEGISTI = False

YASA1 = ("Bir kitabin TEK-BASINA Sharpe esigi, MAKINENIN plasebo "
         "Sharpe'ini bilmeden anlamsizdir: bu makine hic sinyal yokken "
         "1,999 veriyor, yani 'Sharpe >= 2,5' sarti sifira karsi degil "
         "2,0'a karsi okunmalidir.")
YASA2 = ("Harmanin dusus azaltmasi SLEEVE'E ait olmayabilir: plasebo "
         "sleeve'i 1,583x doz, ters-sinyal sleeve'i 1,632x verdi - ikisi "
         "de gercek sinyalden YUKSEK. Cesitlendirmenin degeri, sleeve'i "
         "PLASEBO SLEEVE'E karsi olcmeden bilinemez.")
YASA3 = ("Cesitlendiriciyi ham getiri ortalamasiyla bootstrapllamak onu "
         "REDDEDER (P %15,2) cunku kazanci riskte. Nicelik secimi, "
         "kararin kendisi kadar onemlidir.")
YASA4 = ("Bir harman IKI kitaptir ve sermaye bolunur: en kucuk sleeve "
         "asgari bacagi tasiyabilmeli. Iyilestirmenin GECERLI oldugu "
         "sermaye araligi, iyilestirmenin kendisi kadar bir bulgudur.")


# ---------------------------------------------------------------- HÜKÜM

def kullanici_momentum_kolunda_mi() -> bool:
    """Kullanıcı kaybedeni mi shortladı (momentum) yoksa kazananı mı (ters)?"""
    return all(v < 0 for v in USUSDT_GIRIS_GETIRI.values())


def bt2_en_iyi_gun() -> int:
    return max(BT2_TARAMA, key=lambda g: BT2_TARAMA[g][0])


def bt2_isaret_tek_yonlu_mu() -> bool:
    """Her geriye bakışta momentum pozitif, ters negatif mi?"""
    return all(m > 0 > t for m, t in BT2_TARAMA.values())


def sartname_gecti_mi() -> bool:
    return KITAPLAR["mom 1g"][1] >= SARTNAME_SHARPE


def sartname_yeterince_yukarida_mi() -> bool:
    """Şartname eşiği (2,5), makinenin plasebo Sharpe'ının (2,0) BİR TAM
    PUAN üstünde mi? Değilse eşik zayıftır: makine onu neredeyse kendi
    başına karşılıyor. Bu fonksiyonun FALSE dönmesi madde 298'in bulgusu."""
    return SARTNAME_SHARPE - PLASEBO_SHARPE > 1.0


def sartname_payi() -> float:
    """2,5 eşiğinin ne kadarı makinenin kendisi? (yüzde)"""
    return 100.0 * PLASEBO_SHARPE / SARTNAME_SHARPE


def plaseboyu_gecti_mi() -> bool:
    return MOM_VS_PLASEBO["P_sharpe"] >= 95.0


def muhasebe_yapay_mi() -> bool:
    """Hasatlı muhasebe fiyat bacaklarını NEGATİF, hasatsız POZİTİF mi gösteriyor?"""
    return (HASATLI_MUHASEBE["LONG fiyat"] < 0
            and HASATSIZ_MUHASEBE["LONG fiyat"] > 0)


def momentum_makineye_daha_mi_bagimli() -> bool:
    return HASAT_KATKISI["momentum"] > HASAT_KATKISI["carry"]


def en_iyi_agirlik() -> float:
    return max((w for w in HARMAN if w > 0), key=lambda w: HARMAN[w][6])


def en_guclu_kanit_agirligi() -> float:
    return max((w for w in HARMAN if w > 0), key=lambda w: HARMAN[w][7])


def harman_kanit_barini_gecti_mi(w: float = 0.2) -> bool:
    return HARMAN[w][7] is not None and HARMAN[w][7] >= BAR_P


def yalniz_sart4ten_mi_dustu() -> bool:
    """w=0,2: şart 1-2-3 geçti, yalnız şart 4 (kaldıraç) düştü."""
    return HARMAN_KALDIRAC[0.2] > 1.005


def dusus_azaltmasi_sleeve_e_mi_ait() -> bool:
    """Plasebo/ters sleeve'in dozu gerçek sinyalden DÜŞÜK mü?"""
    return (SLEEVE_DEGISTI["PLASEBO"][3] < SLEEVE_DEGISTI["mom1"][3]
            and SLEEVE_DEGISTI["ters7"][3] < SLEEVE_DEGISTI["mom1"][3])


def yalniz_bir_geriye_bakis_mi_calisiyor() -> bool:
    return all(SLEEVE_DEGISTI[s][6] < BAR_P for s in ("mom7", "mom30"))


def momentum_plasebo_sleeve_i_gecti_mi() -> bool:
    return HARMAN_VS_PLASEBO["P_sharpe"] >= 95.0


def ucele_tahmini_dogru_muydu() -> bool:
    """UCELE=0 momentumu iyileştirdi mi? (tahminim buydu)"""
    return KITAPLAR["mom1 UCELE=0"][1] > KITAPLAR["mom 1g"][1]


def kullanici_bakiyesinde_kosar_mi(kurulum: str = "13x3") -> bool:
    return max(KULLANICI_BAKIYE) >= SERMAYE_ESIGI[kurulum][1]


def gereken_sermaye(kurulum: str = "13x3") -> float:
    return SERMAYE_ESIGI[kurulum][1]


def ayar_degisti_mi() -> bool:
    return AYAR_DEGISTI


def hukum() -> str:
    if not plaseboyu_gecti_mi():
        return "RED: plaseboyu gecemedi."
    return ("ACIK AMA UYGULANAMAZ: trend kitabi GERCEK (plaseboyu tek "
            "basina %%98,9, harmanda %%99,4 geciyor; 2,535 >= 2,5). Harman "
            "w=0,2'de her eksende daha iyi (Sh 2,984 · dusus 12,93 · doz "
            "1,582x · net +208,46) ve kanit barini geciyor (P(Sh) %%81,0). "
            "AMA: (i) yalniz 1 gunluk geriye bakista yasiyor, (ii) rho "
            "0,741, (iii) dusus kazanci sleeve'e ait DEGIL (plasebo "
            "sleeve'i 1,583x), (iv) sart 4'ten dusuyor (kaldirac 1,127x), "
            "(v) 4.875 $'in altinda KOSAMAZ - kullanici 1.000-2.000 $ ile "
            "basliyor. Ayar DEGISMEDI.").replace("%%", "%")


# ---------------------------------------------------------------- RAPOR

def yaz() -> None:
    print(__doc__)

    print("0) KULLANICININ ISLEMI HANGI KOLDA:")
    for g, v in sorted(USUSDT_GIRIS_GETIRI.items()):
        print("   %2d gunluk getiri %+7.1f%%" % (g, v))
    print("   hepsi negatif -> KAYBEDENI shortladi (momentum kolu): %s"
          % kullanici_momentum_kolunda_mi())

    print("\n1) HAM MOTOR (bt2) ON TARAMASI:")
    print("   BULUNAN KOD HATASI: %s" % BT2_HATA)
    print("   REFERANS: carry AYNI motorda Sharpe %.3f (kom %.4f = g33'un %.0f kati)"
          % (BT2_REFERANS_SHARPE, BT2_KOM, BT2_KOM / 0.0002))
    print("   %-6s %12s %12s" % ("gun", "momentum", "ters"))
    for g in sorted(BT2_TARAMA):
        m, t = BT2_TARAMA[g]
        print("   %-6d %12.3f %12.3f%s"
              % (g, m, t, "  <== en iyi" if g == bt2_en_iyi_gun() else ""))
    print("   isaret her bakista tek yonlu mu: %s" % bt2_isaret_tek_yonlu_mu())

    print("\n2) TAM MAKINE (g33): %s" % SKOR_NEDENSEL)
    print("   %-22s %8s %7s %7s %7s %7s %8s %9s %7s"
          % ("kitap", "CAGR", "Sh", "dd", "Sh22", "Sh25", "doz", "net", "rho"))
    print("   %-22s %+8.2f %7.3f %7.2f %7.3f %7.3f %7.3fx %+9.2f %7.3f"
          % ("KONTROL carry", KONTROL["cagr"], KONTROL["sh"], KONTROL["dd"],
             KONTROL["sh22"], KONTROL["sh25"], KONTROL["doz"],
             KONTROL["net"], KONTROL["ro"]))
    for ad, v in KITAPLAR.items():
        print("   %-22s %+8.2f %7.3f %7.2f %7.3f %7.3f %7.3fx %+9.2f %7.3f"
              % (ad, v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7]))

    print("\n3) PLASEBO = MAKINENIN TEK BASINA ODEDIGI:")
    print("   %s" % PLASEBO_TANIMI)
    print("   plasebo Sharpe %.3f" % PLASEBO_SHARPE)
    for k, v in SINYAL_DEGERI.items():
        print("   %-10s SINYALININ degeri: %+.2f Sharpe" % (k, v))
    print("   sartname esigi %.1f; plasebonun BIR TAM PUAN ustunde mi: %s"
          % (SARTNAME_SHARPE, sartname_yeterince_yukarida_mi()))
    print("   -> esigin %%%.0f'i MAKINENIN KENDISI; bar ZAYIF (madde 298 yasa 1)"
          % sartname_payi())
    print("   mom1 vs plasebo: net %+.2f vs %+.2f | P(Sharpe) %%%.1f -> gecti mi %s"
          % (MOM_VS_PLASEBO["net_aday"], MOM_VS_PLASEBO["net_plasebo"],
             MOM_VS_PLASEBO["P_sharpe"], plaseboyu_gecti_mi()))

    print("\n4) MADDE 290'IN TUZAGI (hasat kapatma: %s):" % HASAT_KAPATMA)
    print("   %-16s %10s %10s" % ("kalem", "HASATLI", "HASATSIZ"))
    for k in HASATLI_MUHASEBE:
        print("   %-16s %+10.1f %+10.1f"
              % (k, HASATLI_MUHASEBE[k], HASATSIZ_MUHASEBE[k]))
    print("   muhasebe yapay miydi: %s" % muhasebe_yapay_mi())
    print("   hasadin katkisi: carry %+.2f vs momentum %+.2f Sharpe "
          "(momentum makineye daha bagimli: %s)"
          % (HASAT_KATKISI["carry"], HASAT_KATKISI["momentum"],
             momentum_makineye_daha_mi_bagimli()))
    print("   madde 290 paritesi: %s" % MADDE290_PARITE)

    print("\n5) HARMAN:")
    print("   %-5s %8s %7s %7s %7s %7s %8s %9s %7s %7s"
          % ("w", "CAGR", "Sh", "dd", "Sh22", "Sh25", "doz", "net", "dnet", "P(Sh)"))
    for w in sorted(HARMAN):
        c, s, d, s2, s5, k, n, p = HARMAN[w]
        print("   %-5.1f %+8.2f %7.3f %7.2f %7.3f %7.3f %7.3fx %+9.2f %+7.2f %6s"
              % (w, c, s, d, s2, s5, k, n, n - KONTROL["net"],
                 "-" if p is None else "%.1f%%" % p))
    print("   OLCU UYUSMAZLIGI: %s" % OLCU_UYUSMAZLIGI)
    print("   en yuksek net: w=%.1f | en guclu kanit: w=%.1f"
          % (en_iyi_agirlik(), en_guclu_kanit_agirligi()))
    print("   kanit barini (>=%%%.0f) gecti mi: %s"
          % (BAR_P, harman_kanit_barini_gecti_mi()))
    print("   yalniz sart 4'ten mi dustu: %s (gereken kaldirac %.3fx)"
          % (yalniz_sart4ten_mi_dustu(), HARMAN_KALDIRAC[0.2]))
    print("   sart 4'ten TEK BASINA dusen aday sayisi: %d"
          % SART4_DUSEN_ADAY_SAYISI)

    print("\n6) SAGLAMLIK (w=0,2'de sleeve degistirildi):")
    print("   %-10s %8s %7s %7s %8s %9s %7s %7s"
          % ("sleeve", "CAGR", "Sh", "dd", "doz", "net", "dnet", "P(Sh)"))
    for ad, v in SLEEVE_DEGISTI.items():
        print("   %-10s %+8.2f %7.3f %7.2f %7.3fx %+9.2f %+7.2f %6.1f%%"
              % (ad, v[0], v[1], v[2], v[3], v[4], v[5], v[6]))
    print("   dusus azaltmasi sleeve'e mi ait: %s"
          % dusus_azaltmasi_sleeve_e_mi_ait())
    print("   yalniz bir geriye bakis mi calisiyor: %s (taranan kombinasyon %d)"
          % (yalniz_bir_geriye_bakis_mi_calisiyor(), TARANAN_KOMBINASYON))
    print("   mom1 harmani plasebo harmanini gecti mi: %s "
          "(net %+.2f vs %+.2f, P(Sharpe) %%%.1f)"
          % (momentum_plasebo_sleeve_i_gecti_mi(),
             HARMAN_VS_PLASEBO["net_aday"], HARMAN_VS_PLASEBO["net_plasebo"],
             HARMAN_VS_PLASEBO["P_sharpe"]))
    print("   +7,61 NASIL AYRISIYOR: %s" % AYRISMA)

    print("\n7) YANLIS CIKAN TAHMINIM:")
    print("   %s" % TAHMIN_YANLIS)
    print("   tahmin dogru muydu: %s" % ucele_tahmini_dogru_muydu())

    print("\n8) SERMAYE ESIGI (taban payi %.3f, asgari bacak %.2f $):"
          % (TABAN_PAYI, ASGARI_BACAK))
    print("   %-10s %18s %24s" % ("kurulum", "tek kitap asgari", "w=0,2 TOPLAM"))
    for k, (a, b) in SERMAYE_ESIGI.items():
        print("   %-10s %15.0f $ %21.0f $" % (k, a, b))
    print("   TERS TENSIYON: %s" % TERS_TENSIYON)
    print("   kullanici bakiyesi %s -> kosar mi: %s (gereken %.0f $)"
          % (list(KULLANICI_BAKIYE), kullanici_bakiyesinde_kosar_mi(),
             gereken_sermaye()))

    print("\n9) AYAR degisti mi: %s" % ayar_degisti_mi())
    print("\nYASA 1: %s" % YASA1)
    print("YASA 2: %s" % YASA2)
    print("YASA 3: %s" % YASA3)
    print("YASA 4: %s" % YASA4)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
