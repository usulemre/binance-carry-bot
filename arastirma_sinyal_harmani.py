#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 299 — ÇEŞİTLENDİRMEYİ SERMAYEDE YAPMAK İLE SİNYALDE YAPMAK AYNI
ŞEY DEĞİLDİR: SİNYALİ EĞMENİN BEDELİ (−34,02) EKLENEN SİNYALİN
KATKISINDAN (+12,13) BÜYÜK. VE BİR MOTORUN SİNYAL KANALI YALNIZ
SIRALAMA TAŞIMIYOR OLABİLİR.

Madde 298 her eksende iyileşen bir aday bulmuştu (trend sleeve'i, w=0,2:
Sharpe 2,984 · düşüş 12,93 · doz 1,582x · net +208,46 · P(Sh) %81,0) ama
tek blokeri **sermaye** idi: harman İKİ kitap demek, en küçük sleeve
asgari bacağı taşımalı ⇒ 13x3 ile **4.875 $**. Kullanıcı 1.000-2.000 $
ile başlıyor.

Doğal soru: aynı faydayı **tek kitap içinde**, sinyalleri birleştirerek
alabilir miyiz? O zaman sermaye eşiği 4.875 $ değil **975 $** olur.

CEVAP: HAYIR. Ve yol üstünde motorla ilgili bir gerçek bulundu.

═══ 1. BULUNAN MOTOR GERÇEĞİ: SK_DOSYA PANELİ BİR SIRALAMA DEĞİL ═══

İlk kurgu: funding ve momentum sıralamalarını yüzdelik (0..1) olarak
harmanlayıp `SK_DOSYA` ile vermek. g33 içeride `sc=rk(S[i][ix])`
uyguladığı için bu monoton dönüşüm seçimi korumalıydı.

**PARİTE KIRILDI:** w=0 kolu +%94,4 / Sh 2,98 verdi, kontrol
+%112,3 / Sh 3,10.

"Seçim değişti" sanmak doğal olurdu. Ölçüldü: 301 rebalance barının
**HEPSİNDE** long ve short kümeleri **birebir aynı**. Kırılan şey seçim
değil, **rezerv kuralı**:

    g33 satir 363: [k for k in lo if S[i,k] <= -REZ_ESIK]
    g33 satir 490: (eski[k]>0 and S[i+1,k] <= -REZ_ESIK) or ...

`REZ_ESIK=0.015` sinyalin **BÜYÜKLÜĞÜYLE** doğrudan kıyaslanıyor.
Panel 0..1 sıralarına çevrilince `S <= -0,015` hiç sağlanmıyor ⇒ fırsat
rezervi **hiç devreye girmiyor**. Uyarı g33'e yazıldı (madde 299 bloğu),
ve değişiklik yorum olduğu için parite yeniden koşuldu: iki fazda da
max fark **0,000e+00**.

═══ 2. BU, MADDE 298'İ GERİYE DÖNÜK ETKİLİYOR ═══

Madde 298'in momentum panelleri ham geçmiş getiriydi (~0,1 ölçeği), yani
eşiği sürekli aşıyordu. Çıktıdaki rezerv kullanımı:

    kontrol (funding)   58 /yil
    mom1               214 /yil
    mom7               218 /yil
    mom30              218 /yil
    ters7              192 /yil
    mom1 PLASEBO       176 /yil

Yani madde 298'in **momentum-vs-kontrol** karşılaştırması rezerv
davranışını da içeriyordu. (**momentum-vs-plasebo** karşılaştırması
etkilenmedi: ikisi de aynı birim ölçeğinde, 214 ve 176.)

Üç kol REZERV=0 ile yeniden koşuldu (kapanma çıktıdan doğrulandı:
`rez_kullanim/yil 0`):

    kol        CAGR      Sh     dusus    doz       net
    carry   +127,56   2,879    16,91  1,305x   +186,09
    mom1    + 89,45   2,543    18,13  1,372x   +134,92
    plasebo + 55,91   2,016    15,35  1,364x   + 79,73
    mom1 vs plasebo: P(Sharpe) **%98,9**
    mom1 vs carry  : P(Sharpe) %18,9

**MADDE 298'İN HÜKMÜ AYAKTA:** mom1 Sharpe 2,543 (madde 298: 2,535),
plasebo 2,016 (1,999), plaseboyu geçme olasılığı %98,9 (%98,9).
Karışımın YÖNÜ momentumun **lehine değil ALEYHİNE** idi — rezervden
carry yararlanıyordu (Sh 3,10 -> 2,88 kapatınca), momentum değil
(2,62 -> 2,64). Yani madde 298 momentumu olduğundan İYİ değil, hafifçe
KÖTÜ göstermiş.

Not: rezerv kapatılınca mom1'in **dozu carry'den YÜKSEK** (1,372x vs
1,305x) ama neti düşük — doz kazancı yine sinyale ait değil, plasebonun
dozu da 1,364x (madde 298 yasa 2 bir kez daha).

═══ 3. DOĞRU KURGU: HARMAN FUNDING BİRİMİNDE ═══

    S_harman = F + w * sigma_F(satir) * z(momentum)

`F` = kontrolün kendi panelidir (`/tmp/sk_bar48.pkl`), `sigma_F` o barın
uygun kümesindeki funding yayılımı (medyan **0,00166**), `z` momentumun
uygun kümedeki standart puanı. Eğim yalnız uygun kümede eklenir,
dışarıda `S = F` kalır (satır 490 **tutulan** pozisyonun `S[i+1]`'ini
okuyor ve o sembol o an uygun olmayabilir).

w=0 paneli ham funding paneliyle **bit düzeyinde aynı**, ve koşu
kontrolü birebir verdi: +%112,3 / Sh 3,10 / dd −14,5.

═══ 4. SONUÇ: HER AĞIRLIKTA RED ═══

    kol              CAGR      Sh    dusus    Sh22    Sh25     doz      net   P(Sh)
    w=0 (PARITE)  +112,27   2,939   14,54   2,789   3,147  1,505x  +200,85     -
    w=0,1         +105,51   2,809   14,27   2,557   3,145  1,465x  +179,19  %12,8
    w=0,2         +105,50   2,807   13,98   2,503   3,210  1,464x  +178,96  %19,8
    w=0,3         +103,96   2,799   15,13   2,507   3,185  1,476x  +178,15  %21,7
    w=0,5         +103,62   2,790   15,59   2,512   3,159  1,466x  +175,68  %22,2
    PLASEBO w=0,2 + 98,11   2,736   14,03   2,630   2,886  1,477x  +166,83   %1,2

Dört şart hepsini reddetti; hepsi şart 1'den düştü (22-24 Sharpe
−0,23 ile −0,29 arası).

**AYRIŞMA (w=0,2):** sinyali eğmenin **mekanik bedeli** −34,02 puan
(plasebo harmanı: 166,83 − 200,85), momentumun **içeriği** bunun
**+12,13**'ünü geri alıyor (178,96 − 166,83), kalan **−21,89**.

Yani momentum içeriği GERÇEK (plasebo harmanını geçiyor) ama ana sinyali
sulandırmanın bedeli ondan büyük.

**PLATO:** 22-24 kaybı w=0,1'de −0,232, w=0,5'te −0,277 — yani
neredeyse DOZA DUYARSIZ. Kademeli bir sulanma olsa doz-tepkisi olurdu.
Plato, bedelin birkaç yüksek-değerli seçimin BOZULMASINDAN geldiğini
söylüyor, genel bir gürültü eklenmesinden değil.

**FAZ DESENİ:** gerçek eğim 22-24'te plasebodan **daha kötü**
(2,503 vs 2,630) ama 25-26'da belirgin **daha iyi** (3,210 vs 2,886).
Momentumun kenarı bu kitapta tamamen **son rejimde**. Madde 297'nin
hacim ekseni bunun tersiydi (22-24 iyi, 25-26 kötü): kontrol iki
rejime-özgü eğimin ARASINDA duruyor.

═══ 5. PARAMETRELEME ÇEKİNCESİ (dürüstlük notu) ═══

Bu harman **değer uzayında**; motorun kendi `AKW` harmanı
(`sc=(1-AKW)*sc+AKW*rank`) **sıra uzayında**. Aynı w aynı şey değildir.
Sıra uzayında bir harman ise `REZ_ESIK`'i bozar (bölüm 1).

Değer ve sırayı birlikte koruyan bir kurgu YOK: sıralamayı harmanlayıp
büyüklükleri yeniden atamak, bir sembole BAŞKASININ funding'ini
yakıştırır ve rezerv onun üzerinden tetiklenir. Yani bu motorda
**sinyal harmanı rezerv kuralından bağımsız tanımlanamaz**. Bu bir
ölçüm eksikliği değil, motorun sinyal kanalının sıralamayı ve
büyüklüğü birbirine bağlamasıdır.

═══ 6. KULLANICI İÇİN NE DEĞİŞTİ ═══

Hiçbir şey. 1.000-2.000 $ aralığında momentumun faydasını almanın ucuz
bir yolu YOK: çalışan tek sürüm madde 298'in sermaye harmanı ve o
**4.875 $** istiyor. Öneri aynen duruyor: **13 dilim x 3 bacak,
2.000 $, 1x**.

AYAR DEĞİŞMEDİ.
"""

# ---------------------------------------------------------------- SABİTLER

SORU = ("Madde 298'in trend faydasi SERMAYE bolmeden, tek kitap icinde "
        "sinyalleri birlestirerek alinabilir mi? (sermaye esigi 4.875 $ "
        "yerine 975 $ olurdu)")

# --- 1. motor gercegi ---
MOTOR_GERCEGI = (
    "SK_DOSYA paneli bir SIRALAMA degil: motor S'nin BUYUKLUGUNU de "
    "okuyor. REZ_ESIK karsilastirmalari (g33 satir 363 ve ~490) sinyali "
    "dogrudan bir funding esigiyle kiyaslar.")
REZ_ESIK = 0.015
G33_SATIRLAR = (363, 490)
PARITE_KIRILDI = {"sira panelli w=0": (94.4, 2.98), "kontrol": (112.3, 3.10)}
TANI_BAR_SAYISI = 301
TANI_FARKLI_BAR = 0
"""301 rebalance barinin HEPSINDE secim kumeleri birebir ayni. Kirilan
sey secim DEGIL, rezerv kuralidir."""
G33_UYARISI_YAZILDI = True
PARITE_YENIDEN = 0.0
"""Yorum eklendikten sonra parite yeniden kosuldu: iki fazda max fark 0,000e+00."""

# --- 2. madde 298'in karisimi ---
REZERV_KULLANIMI = {
    "kontrol (funding)": 58, "mom1": 214, "mom7": 218, "mom30": 218,
    "ters7": 192, "mom1 PLASEBO": 176,
}
KARISIM_ETKILEMEDI = "momentum-vs-plasebo (ikisi de ayni birim olceginde)"
KARISIM_ETKILEDI = "momentum-vs-kontrol (ve dolayisiyla sermaye harmani)"
REZERV_SIFIR = {
    #  kol      : (cagr,   sh,    dusus,  doz,   net)
    "carry":     (127.56, 2.879, 16.91, 1.305, 186.09),
    "mom1":      ( 89.45, 2.543, 18.13, 1.372, 134.92),
    "plasebo":   ( 55.91, 2.016, 15.35, 1.364,  79.73),
}
REZERV_SIFIR_P = {"mom1 vs plasebo": 98.9, "mom1 vs carry": 18.9}
MADDE298_KARSILASTIRMA = {
    #  nicelik           : (madde 298 degeri, madde 299 REZERV=0 degeri)
    "mom1 Sharpe":        (2.535, 2.543),
    "plasebo Sharpe":     (1.999, 2.016),
    "mom1 vs plasebo P":  (98.9, 98.9),
}
KARISIM_YONU = (
    "Karisim momentumun LEHINE degil ALEYHINE idi: rezervden carry "
    "yararlaniyordu (Sh 3,10 -> 2,88 kapatinca), momentum degil "
    "(2,62 -> 2,64). Madde 298 momentumu olmasi gerekenden IYI degil "
    "hafifce KOTU gostermis.")

# --- 3. dogru kurgu ---
HARMAN_FORMULU = "S = F + w * sigma_F(satir) * z(momentum)"
SIGMA_F_MEDYAN = 0.00166109
PARITE_BIT_AYNI = True
PARITE_KOSU = {"cagr": 112.3, "sh": 3.10, "dd": -14.5}
TAM_DESTEK_NOTU = (
    "Egim yalniz UYGUN kumede eklenir, disarida S = F kalir - cunku satir "
    "490 TUTULAN pozisyonun S[i+1]'ini okuyor ve o sembol o an uygun "
    "olmayabilir. Maskelemek orada kontrolden ayrisirdi.")

# --- 4. sonuc ---
KONTROL = {"cagr": 112.27, "sh": 2.939, "dd": 14.54, "sh22": 2.789,
           "sh25": 3.147, "doz": 1.505, "net": 200.85}
HARMAN = {
    #  w   : (cagr,   sh,    dusus,  sh22,  sh25,  doz,   net,    P(Sh)%)
    0.0: (112.27, 2.939, 14.54, 2.789, 3.147, 1.505, 200.85, None),
    0.1: (105.51, 2.809, 14.27, 2.557, 3.145, 1.465, 179.19, 12.8),
    0.2: (105.50, 2.807, 13.98, 2.503, 3.210, 1.464, 178.96, 19.8),
    0.3: (103.96, 2.799, 15.13, 2.507, 3.185, 1.476, 178.15, 21.7),
    0.5: (103.62, 2.790, 15.59, 2.512, 3.159, 1.466, 175.68, 22.2),
}
PLASEBO_HARMAN = {"w": 0.2, "cagr": 98.11, "sh": 2.736, "dd": 14.03,
                  "sh22": 2.630, "sh25": 2.886, "doz": 1.477,
                  "net": 166.83, "P": 1.2}
BAR_P = 80.0
AYRISMA = {
    # elle yazilmasin: yayinlanan netlerden TURETILIR (madde 298'in dersi)
    "egmenin mekanik bedeli": round(166.83 - 200.85, 2),
    "momentumun icerigi": round(178.96 - 166.83, 2),
    "kalan (kontrole karsi)": round(178.96 - 200.85, 2),
}
PLATO = ("22-24 kaybi w=0,1'de -0,232, w=0,5'te -0,277: neredeyse DOZA "
         "DUYARSIZ. Kademeli bir sulanma olsa doz-tepkisi olurdu; plato "
         "bedelin birkac YUKSEK-DEGERLI SECIMIN bozulmasindan geldigini "
         "soyluyor.")
FAZ_DESENI = ("Gercek egim 22-24'te plasebodan DAHA KOTU (2,503 vs 2,630) "
              "ama 25-26'da belirgin DAHA IYI (3,210 vs 2,886): momentumun "
              "kenari tamamen SON REJIMDE. Madde 297'nin hacim ekseni "
              "bunun TERSIYDI - kontrol iki rejime-ozgu egimin ARASINDA.")

# --- 5. parametreleme cekincesi ---
PARAMETRELEME = (
    "Bu harman DEGER uzayinda; motorun kendi AKW harmani "
    "(sc=(1-AKW)*sc+AKW*rank) SIRA uzayinda. Ayni w ayni sey degildir.")
KURGU_YOK = (
    "Degeri ve sirayi birlikte koruyan bir kurgu YOK: siralamayi "
    "harmanlayip buyuklukleri yeniden atamak bir sembole BASKASININ "
    "funding'ini yakistirir ve rezerv onun uzerinden tetiklenir. Bu "
    "motorda sinyal harmani REZERV KURALINDAN BAGIMSIZ TANIMLANAMAZ.")

# --- 6. kullanici ---
SERMAYE_SINYAL_HARMANI = 975.0
"""13x3 ile tek kitap asgarisi - sinyal harmani sermaye bolmediği icin
esik bu olurdu. Ama harman REDDEDILDI."""
SERMAYE_SERMAYE_HARMANI = 4875.0
"""Madde 298: calisan tek surum, w=0,2 sleeve icin."""
ONERI = "13 dilim x 3 bacak, 2.000 $, 1x (DEGISMEDI)"
AYAR_DEGISTI = False

YASA1 = ("Cesitlendirmeyi SERMAYEDE yapmak ile SINYALDE yapmak ayni sey "
         "degildir: sermaye harmani ana sinyalin secimine DOKUNMAZ, sinyal "
         "harmani onu SULANDIRIR - ve sulandirmanin bedeli (-34,02 puan) "
         "eklenen sinyalin katkisindan (+12,13) buyuktur.")
YASA2 = ("Bir motorun sinyal kanali yalniz SIRALAMA tasimiyor olabilir: bu "
         "motor REZ_ESIK'te sinyalin BUYUKLUGUNU okur, o yuzden skor paneli "
         "siraya cevrilemez - ve bu, sira uzayinda bir harmani imkansiz "
         "kilar.")
YASA3_MADDE300_EKI = (
    "MADDE 300: bu yasanin TERS yonu de olculdu. Yanlis nicelik yalniz "
    "haksiz REDDETMEZ, haksiz KABUL de eder: 13x3 kitabinda TPL 0,55'i "
    "ham getiri bootstrap'i %95,9 ile KABUL ederdi, doz olcusu reddetti "
    "(net -5,26) cunku aday getiriyi VE riski birlikte yukseltiyor. "
    "Ikisi ayni hatanin iki yuzu.")

YASA3 = ("Bir parite kosusu kirildiginda 'secim degisti' VARSAYILMAZ: bu "
         "turda secim 301 barin HEPSINDE ayniydi, kirilan rezerv kuraliydi. "
         "Pariteyi kiran seyi BULMADAN sonuc yorumlanamaz.")
YASA4 = ("Bir karisimin YONU olculmeden hukme varilmaz: madde 298'in rezerv "
         "karisimi gercekti ama momentumun ALEYHINE isliyordu, yani "
         "duzeltme hukmu degistirmedi - sadece guclendirdi.")
YASA5 = ("Doza duyarsiz bir kayip (PLATO) kademeli sulanma DEGIL, birkac "
         "yuksek-degerli secimin bozulmasidir. Doz-tepkisinin YOKLUGU da "
         "bir bulgudur.")


# ---------------------------------------------------------------- HÜKÜM

def parite_kirilmasi_secimden_miydi() -> bool:
    return TANI_FARKLI_BAR > 0


def parite_geri_geldi_mi() -> bool:
    return PARITE_YENIDEN == 0.0 and PARITE_BIT_AYNI


def rezerv_karisimi_var_miydi(kat: float = 2.0) -> bool:
    """Momentum kollarinin rezerv kullanimi kontrolun kac katiydi?"""
    k = REZERV_KULLANIMI["kontrol (funding)"]
    return all(v >= kat * k for a, v in REZERV_KULLANIMI.items()
               if a != "kontrol (funding)")


def madde298_hukmu_ayakta_mi(tol: float = 0.05) -> bool:
    """REZERV=0 ile yeniden olculunce madde 298'in sayilari tutuyor mu?"""
    return all(abs(a - b) <= tol for a, b in MADDE298_KARSILASTIRMA.values()
               if a < 10.0) and MADDE298_KARSILASTIRMA["mom1 vs plasebo P"][1] >= 95.0


def karisim_adayin_lehine_miydi() -> bool:
    """Karisim momentumu OLDUGUNDAN IYI mi gosterdi?"""
    return REZERV_SIFIR["mom1"][1] < 2.535


def doz_kazanci_sinyale_mi_ait() -> bool:
    """REZERV=0'da plasebonun dozu mom1'in dozundan dusuk mu?"""
    return REZERV_SIFIR["plasebo"][3] < REZERV_SIFIR["mom1"][3] - 0.05


def gecen_agirlik_var_mi() -> bool:
    return any(v[7] is not None and v[7] >= BAR_P for v in HARMAN.values())


def hepsi_sart1den_mi_dustu() -> bool:
    return all(HARMAN[w][3] < KONTROL["sh22"] for w in HARMAN if w > 0)


def momentum_icerigi_gercek_mi() -> bool:
    """Gercek harman, PLASEBO harmanini geciyor mu?"""
    return HARMAN[0.2][6] > PLASEBO_HARMAN["net"]


def bedel_katkidan_buyuk_mu() -> bool:
    return abs(AYRISMA["egmenin mekanik bedeli"]) > AYRISMA["momentumun icerigi"]


def plato_var_mi(tol: float = 0.1) -> bool:
    """22-24 kaybi doza duyarsiz mi?"""
    k = [KONTROL["sh22"] - HARMAN[w][3] for w in HARMAN if w > 0]
    return max(k) - min(k) < tol


def son_rejime_mi_ait() -> bool:
    """Gercek egim 22-24'te plasebodan kotu, 25-26'da iyi mi?"""
    return (HARMAN[0.2][3] < PLASEBO_HARMAN["sh22"]
            and HARMAN[0.2][4] > PLASEBO_HARMAN["sh25"])


def sinyal_harmani_sermaye_bolmuyor_mu() -> bool:
    return SERMAYE_SINYAL_HARMANI < SERMAYE_SERMAYE_HARMANI


def kullanici_icin_degisen_var_mi() -> bool:
    return gecen_agirlik_var_mi()


def ayar_degisti_mi() -> bool:
    return AYAR_DEGISTI


def hukum() -> str:
    if gecen_agirlik_var_mi():
        return "ACIK: kanit esigini gecen bir agirlik var."
    return ("RED: sinyal harmani HER agirlikta dustu (en iyi w=0,2, net "
            "+178,96 vs +200,85, P(Sh) %19,8) ve hepsi sart 1'den "
            "(22-24 Sharpe -0,23..-0,29). Momentum icerigi GERCEK - "
            "plasebo harmanini +12,13 puan geciyor - ama ana sinyali "
            "sulandirmanin bedeli -34,02 puan, yani icerikten buyuk. "
            "1.000-2.000 $'da momentumun faydasini almanin ucuz bir yolu "
            "YOK: calisan tek surum madde 298'in sermaye harmani ve "
            "4.875 $ istiyor. Oneri ve ayar DEGISMEDI.")


# ---------------------------------------------------------------- RAPOR

def yaz() -> None:
    print(__doc__)
    print("SORU: %s\n" % SORU)

    print("1) BULUNAN MOTOR GERCEGI:")
    print("   %s" % MOTOR_GERCEGI)
    print("   REZ_ESIK=%.3f, g33 satirlari %s" % (REZ_ESIK, list(G33_SATIRLAR)))
    print("   parite kirildi: sira panelli w=0 %s vs kontrol %s"
          % (PARITE_KIRILDI["sira panelli w=0"], PARITE_KIRILDI["kontrol"]))
    print("   TANI: %d rebalance bari karsilastirildi, secimi FARKLI olan %d"
          % (TANI_BAR_SAYISI, TANI_FARKLI_BAR))
    print("   -> kirilma secimden miydi: %s" % parite_kirilmasi_secimden_miydi())
    print("   g33'e uyari yazildi: %s | parite yeniden kosuldu, max fark %.3e"
          % (G33_UYARISI_YAZILDI, PARITE_YENIDEN))

    print("\n2) MADDE 298'IN REZERV KARISIMI:")
    for ad, v in REZERV_KULLANIMI.items():
        print("   %-20s %4d /yil" % (ad, v))
    print("   karisim VAR mi (>=2 kat): %s" % rezerv_karisimi_var_miydi())
    print("   ETKILENMEDI: %s" % KARISIM_ETKILEMEDI)
    print("   ETKILENDI  : %s" % KARISIM_ETKILEDI)
    print("   -- REZERV=0 ile yeniden --")
    print("   %-10s %8s %7s %7s %8s %9s" % ("kol", "CAGR", "Sh", "dusus", "doz", "net"))
    for ad, v in REZERV_SIFIR.items():
        print("   %-10s %+8.2f %7.3f %7.2f %7.3fx %+9.2f"
              % (ad, v[0], v[1], v[2], v[3], v[4]))
    for ad, p in REZERV_SIFIR_P.items():
        print("   %-18s P(Sharpe) %%%.1f" % (ad, p))
    print("   %-20s %10s %10s" % ("nicelik", "madde 298", "madde 299"))
    for ad, (a, b) in MADDE298_KARSILASTIRMA.items():
        print("   %-20s %10.3f %10.3f" % (ad, a, b))
    print("   madde 298'in hukmu ayakta mi: %s" % madde298_hukmu_ayakta_mi())
    print("   karisim adayin LEHINE miydi: %s" % karisim_adayin_lehine_miydi())
    print("   %s" % KARISIM_YONU)
    print("   doz kazanci sinyale mi ait: %s (plasebo %.3fx vs mom1 %.3fx)"
          % (doz_kazanci_sinyale_mi_ait(), REZERV_SIFIR["plasebo"][3],
             REZERV_SIFIR["mom1"][3]))

    print("\n3) DOGRU KURGU: %s" % HARMAN_FORMULU)
    print("   sigma_F medyani %.6g | w=0 paneli bit duzeyinde ayni: %s"
          % (SIGMA_F_MEDYAN, PARITE_BIT_AYNI))
    print("   w=0 kosusu: %s | parite geri geldi mi: %s"
          % (PARITE_KOSU, parite_geri_geldi_mi()))
    print("   %s" % TAM_DESTEK_NOTU)

    print("\n4) SONUC:")
    print("   %-14s %8s %7s %7s %7s %7s %8s %9s %7s"
          % ("kol", "CAGR", "Sh", "dusus", "Sh22", "Sh25", "doz", "net", "P(Sh)"))
    for w in sorted(HARMAN):
        c, s, d, a, b, k, n, p = HARMAN[w]
        print("   %-14s %+8.2f %7.3f %7.2f %7.3f %7.3f %7.3fx %+9.2f %6s%s"
              % ("w=%.1f" % w, c, s, d, a, b, k, n,
                 "-" if p is None else "%.1f%%" % p,
                 "  <== PARITE" if w == 0 else ""))
    P = PLASEBO_HARMAN
    print("   %-14s %+8.2f %7.3f %7.2f %7.3f %7.3f %7.3fx %+9.2f %6.1f%%"
          % ("PLASEBO w=0,2", P["cagr"], P["sh"], P["dd"], P["sh22"],
             P["sh25"], P["doz"], P["net"], P["P"]))
    print("   kanit esigini (>=%%%.0f) gecen agirlik: %s"
          % (BAR_P, gecen_agirlik_var_mi()))
    print("   hepsi sart 1'den mi dustu: %s" % hepsi_sart1den_mi_dustu())
    print("   AYRISMA: %s" % AYRISMA)
    print("   momentum icerigi gercek mi: %s | bedel katkidan buyuk mu: %s"
          % (momentum_icerigi_gercek_mi(), bedel_katkidan_buyuk_mu()))
    print("   PLATO: %s" % PLATO)
    print("   plato var mi: %s" % plato_var_mi())
    print("   FAZ DESENI: %s" % FAZ_DESENI)
    print("   son rejime mi ait: %s" % son_rejime_mi_ait())

    print("\n5) PARAMETRELEME CEKINCESI:")
    print("   %s" % PARAMETRELEME)
    print("   %s" % KURGU_YOK)

    print("\n6) KULLANICI ICIN:")
    print("   sinyal harmani sermaye bolmez (esik %.0f $ olurdu) ama REDDEDILDI"
          % SERMAYE_SINYAL_HARMANI)
    print("   calisan tek surum sermaye harmani: %.0f $ (madde 298)"
          % SERMAYE_SERMAYE_HARMANI)
    print("   degisen var mi: %s | oneri: %s"
          % (kullanici_icin_degisen_var_mi(), ONERI))
    print("   ayar degisti mi: %s" % ayar_degisti_mi())

    print("\nYASA 1: %s" % YASA1)
    print("YASA 2: %s" % YASA2)
    print("YASA 3: %s" % YASA3)
    print("YASA 4: %s" % YASA4)
    print("YASA 5: %s" % YASA5)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
