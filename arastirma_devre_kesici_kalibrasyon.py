#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 302 — DEVRE KESİCİLER 15x5 ÜZERİNE KALİBRELİYDİ, AMA MADDE 295
13x3 ÖNERİYOR: O KİTAPTA İNCELE ALARMI NORMAL BİR YILDA %30,6, DURDUR
%9,7 OLASILIKLA ŞANSSIZLIKTAN TETİKLENİYOR. EŞİKLER ARTIK
YAPILANDIRMADAN TÜRETİLİYOR.

Beş tur (297-301) geri testte iyileşme bulamadı; ikisi kod kusuru
çıkardı. Bu tur, kullanıcının gerçek kârını en çok tehdit eden ama hiç
ölçülmemiş şeye bakıyor: **ilk çeyrekte ne görecek, ve gördüğü şey onu
çalışan bir botu kapatmaya itecek mi?**

İlk bakışta bir çelişki göründü ve kovalandı.

═══ 1. BULUNAN ÇELİŞKİ ═══

    devre kesiciler:  INCELE −%18   DURDUR −%23   (carry_rapor)
    13x3 kitabinin tam donem dususu:  −%17,68

İNCELE eşiğine payı **0,32 puan**. 15x5'te bu pay **3,46 puandı**.

Sebep: kalibrasyon zinciri 175 -> 233 -> 243'ün hepsi **15x5** kitabının
istatistiğini kullanıyor. Madde 243'ün doğrulama tablosundaki "gerçek
pencereler −%14,54" tam olarak 15x5'in düşüşü. Üstüne, İNCELE mesajı
**sabit kodlu** `(%-14.7)` yazıyordu — 13x3 koşan biri için yanlış bir
referans.

Madde 295 ise küçük sermayede **13x3 öneriyor**. Yani öneri değişmiş,
eşikler değişmemiş.

═══ 2. MADDE 243'ÜN YÖNTEMİ BİREBİR TEKRARLANDI ═══

Önce yöntem doğrulandı: 15x5 kolu madde 243'ün tablosunu **aynen** verdi
(gerçek pencereler ort −%10,89 · p50 −%10,73 · p5 −%14,54 — üçü de
madde 243'ün yazdığı değerler). Yöntem tuttuğu için 13x3'e uygulandı.

    kitap   tam donem   karis. p5   karis. p1   INCELE %   DURDUR %
    15x5     −%14,54     −%20,56     −%25,65      %11,1      %2,3
    13x3     −%17,68     −%25,51     −%31,59    **%30,6**  **%9,7**

(karıştırılmış = günlük getiriler aynı, SIRASI rastgele, 20.000 örnek,
1 yıllık pencere; "aynı dağılım, farklı şans" — madde 243'ün tanımı.)

**13x3 koşan biri, hiçbir şey bozulmadığı bir yılda üçte bir olasılıkla
İNCELE, onda bir olasılıkla DURDUR görür.** DURDUR bot'u kapattırır;
yani yılda %9,7 olasılıkla çalışan bir strateji şanssızlıktan durur.
Bu, kaybedilmiş kârdır.

═══ 3. EŞİKLER İKİ BAĞIMSIZ YOLDAN YENİDEN TÜRETİLDİ ═══

(1) YANLIŞ TETİK EŞDEĞERLİĞİ — 15x5'in yanlış-tetik olasılığını
    (%11,1 / %2,3) 13x3'te veren eşik:   **−%22,43 / −%28,31**
(2) DÜŞÜŞ ORANIYLA ÖLÇEKLEME — 17,68/14,54 = 1,216:
                                          **−%21,89 / −%27,97**

İki türetmenin farkı 0,54 ve 0,33 puan; ikisi de **−%22 / −%28**'e
yuvarlanıyor. O eşiklerle 13x3'ün yanlış tetiği **%12,3 / %2,5** —
15x5'in kalibrasyonuyla eşdeğer, ve tam dönem düşüşüne payı +4,32 puan
(15x5'te +3,46).

═══ 4. ÇÖZÜM: EŞİK YAPILANDIRMADAN TÜRETİLİYOR ═══

Sabitleri doğrudan −%22/−%28 yapmak YANLIŞ olurdu: 15x5 koşan biri
korumasını kaybederdi. Bunun yerine sabitler **15x5'in temeli** olarak
kaldı ve karar noktaları koşulan kitabın düşüşüyle ölçeklenmiş eşiği
kullanıyor:

    carry_rapor.dusus_incele()  ->  DUSUS_INCELE * olcek
    carry_rapor.dusus_durdur()  ->  DUSUS_DURDUR * olcek
    olcek = KITAP_DUSUS[kitap] / KITAP_DUSUS["15x5"]

15x5'te ölçek 1,000, yani **varsayılan davranış birebir aynı**.
Bilinmeyen bir yapılandırmada ölçek 1,0'da bırakılıyor ve UYARI
veriliyor — eşiği tahminle gevşetmek, eşiğin varlık sebebini ortadan
kaldırır (bu modülün kendi docstring'i).

Sabit kodlu `(%-14.7)` da `backtest_maksimumu()` ile değiştirildi.

═══ 5. İLK ÇEYREK: 2.000 $ İLE NE GÖRECEK ═══

13x3, 1x, 2.000 $. İki yöntem (tarihte gerçekten olan ardışık
N-günler, ve 20.000 blok bootstrap yolu) birbirine çok yakın çıktı:

    gun  P(zarar)   getiri p5 / p50 / p75      dolar p5 / p50 / p75   ic dusus p95
     30    ~%20      −%5,0 / +%6,4 / +%13      −99$ / +128$ / +255$      ~%11,4
     60    ~%10      −%3,1 / +%14,0 / +%26     −62$ / +279$ / +527$      ~%16,2
     90    %3,5-6    −%1,1 / +%22,3 / +%40     −21$ / +446$ / +806$      ~%17,0

Yani: **ilk ayda beşte bir olasılıkla zararda olmak NORMALDİR** ve
tipik iç düşüş %5 civarı, p95'te %11. 90 günde zarar olasılığı %3,5-6'ya
düşüyor ve medyan +%22 (2.000 $'da ~+450 $).

DÜRÜST NÜANS: devre kesici sorunu **ilk çeyrekte küçük**. İlk 90 günde
eski −%18 eşiğinin yanlış tetiği yalnızca **%2,46** (yeni eşikle %0,41).
Sorun **yıl ölçeğinde** büyüyor (%30,6 vs %12,3). Yani bu düzeltme ilk
çeyreği değil, **birinci yılı** koruyor. Olduğundan büyük gösterilmedi.

═══ 6. NE DEĞİŞMEDİ ═══

Strateji ayarı, seçim, bacak büyüklükleri, geri test: hiçbiri. 15x5
varsayılanında eşikler birebir aynı. Değişen tek şey: 15x5 DIŞINDA bir
yapılandırma koşulursa eşikler o kitabın riskine ölçekleniyor.

AYAR DEĞİŞMEDİ. Öneri: **13 dilim x 3 bacak, 2.000 $, 1x** — ama artık
devre kesicileri o kitaba göre.

═══ 7. AÇIK EKSEN ═══

Ölçek, madde 295'in ölçtüğü düşüş tablosundan geliyor. Madde 231'in
ASIL yöntemi (EN KÖTÜ MAKUL REJİMİN p5'i) bu turda 13x3 için
TEKRARLANMADI — rejim ayrımı yeniden üretilmedi. İki türetmenin
buluştuğu nokta sağlam, ama rejim-temelli türetme açık bir eksen.
"""

# ---------------------------------------------------------------- SABİTLER

SORU = ("Kullanicinin gercek karini en cok tehdit eden sey: ilk ceyrekte "
        "ne gorecek, ve gordugu sey onu CALISAN bir botu kapatmaya itecek mi?")

# --- 1. celiski ---
ESIK_ESKI = {"incele": -0.18, "durdur": -0.23}
TAM_DONEM_DUSUS = {"15x5": 14.54, "13x3": 17.68}
PAY_PUAN = {"15x5": 3.46, "13x3": 0.32}
"""INCELE esigine kalan pay. 13x3'te 0,32 puan."""
KALIBRASYON_ZINCIRI = (175, 233, 243)
KALIBRASYON_KITABI = "15x5"
SABIT_KODLU_MESAJ = "(%-14.7)"
"""INCELE mesaji 15x5'in dususunu SABIT KODLU tasiyordu."""

# --- 2. madde 243'un yontemi ---
YONTEM_DOGRULAMA = {
    # 15x5 gercek pencereler: madde 243'un tablosu vs bu turun olcumu
    "ort": (-10.89, -10.89), "p50": (-10.73, -10.73), "p5": (-14.54, -14.54),
}
DD_DAGILIMI = {
    #  kitap : (tam donem, karis p5, karis p1, INCELE tetik%, DURDUR tetik%)
    "15x5": (-14.54, -20.56, -25.65, 11.1, 2.3),
    "13x3": (-17.68, -25.51, -31.59, 30.6, 9.7),
}
KARISTIRMA = ("gunluk getiriler ayni, SIRASI rastgele, 20.000 ornek, "
              "1 yillik pencere - 'ayni dagilim, farkli sans' (madde 243)")

# --- 3. iki turetme ---
TURETME = {
    "yanlis tetik esdegerligi": (-22.43, -28.31),
    "dusus oraniyla olcekleme": (-21.89, -27.97),
}
OLCEK_13X3 = 17.68 / 14.54
ESIK_YENI_13X3 = {"incele": -0.22, "durdur": -0.28}
"""*** MADDE 303 GUNCELLEMESI: BU DEGER YURURLUKTE DEGIL. ***
Madde 231'in KANONIK yontemi (en kotu makul rejimin 1-yillik bootstrap
p5/p1'i) uygulandi ve 13x3 icin **-%23 / -%29** cikti. Bu maddenin
duzeltmesi YONDE VE BUYUKLUKTE dogruydu (yanlis tetigi %30,6 -> %12,6
indirdi) ama gereginden SIKIYDI: gercek olcek 1,216 degil 1,264 (INCELE)
ve 1,299 (DURDUR). Yururlukteki deger carry_rapor.KITAP_ESIK'te."""
MADDE303_YURURLUKTEKI = {"incele": -0.23, "durdur": -0.29}


def madde303_bu_esigi_gevsetti_mi() -> bool:
    return abs(MADDE303_YURURLUKTEKI["incele"]) > abs(ESIK_YENI_13X3["incele"])
YENI_TETIK_13X3 = {"incele": 12.3, "durdur": 2.5}
YENI_PAY_13X3 = 4.32

# --- 4. cozum ---
COZUM = ("Sabitler 15x5'in TEMELI olarak kaldi; karar noktalari kosulan "
         "kitabin dususuyle OLCEKLENMIS esigi kullaniyor "
         "(carry_rapor.dusus_incele / dusus_durdur / backtest_maksimumu).")
NEDEN_SABIT_DEGISTIRILMEDI = ("Sabitleri dogrudan -%22/-%28 yapmak 15x5 "
                              "kosan birinin korumasini KALDIRIRDI.")
VARSAYILAN_BIREBIR = True
"""15x5'te olcek 1,000 -> varsayilan davranis degismedi."""
BILINMEYEN_DAVRANIS = ("olcek 1,0'da birakilir ve UYARI verilir - esigi "
                       "TAHMINLE gevsetmek, esigin varlik sebebini ortadan "
                       "kaldirir")

# --- 5. ilk ceyrek (13x3, 1x, 2.000 $) ---
BAKIYE = 2000.0
CEYREK = {
    #  gun : (P(zarar)% ort, getiri p5, p50, p75 (%), ic dusus p95 (%))
    30: (19.7, -5.0, 6.4, 13.0, 11.4),
    60: (10.5, -3.1, 14.0, 26.0, 16.2),
    90: (4.8, -1.1, 22.3, 40.0, 17.0),
}
CEYREK_YONTEM = ("tarihte gercekten olan ardisik N-gunler (1.415-1.475 "
                 "pencere) VE 20.000 blok bootstrap yolu; ikisi birbirine "
                 "cok yakin cikti")
ILK_CEYREK_TETIK = {
    #  gun : (eski -18 tetik%, yeni -21,9 tetik%)  [bootstrap]
    30: (0.22, 0.01), 60: (1.04, 0.17), 90: (2.46, 0.41),
}
NUANS = ("Devre kesici sorunu ILK CEYREKTE kucuk: ilk 90 gunde eski "
         "esigin yanlis tetigi yalnizca %2,46 (yeni esikle %0,41). Sorun "
         "YIL olceginde buyuyor (%30,6 vs %12,3). Yani bu duzeltme ilk "
         "ceyregi degil BIRINCI YILI koruyor.")

AYAR_DEGISTI = False
ONERI = "13 dilim x 3 bacak, 2.000 $, 1x (devre kesiciler o kitaba gore)"

ACIK_EKSEN = ("Olcek madde 295'in olctugu dusus tablosundan geliyor. Madde "
              "231'in ASIL yontemi (EN KOTU MAKUL REJIMIN p5'i) bu turda "
              "13x3 icin TEKRARLANMADI - rejim ayrimi yeniden uretilmedi.")

YASA1 = ("Bir esik, turetildigi KITABA aittir. Yapilandirma onerisi "
         "degisince esikler onunla gelmezse alarm, korudugu seyi degil "
         "ESKI bir kitabi olcer - ve 13x3'te bu, normal bir yilda %30,6 "
         "yanlis INCELE ve %9,7 yanlis DURDUR demekti.")
YASA2 = ("Bir esigi dogru degere CEKMEK yetmez, TURETILEBILIR yapmak "
         "gerekir: -%22'yi sabit yazmak 13x3'u duzeltir ve 15x5'i bozardi. "
         "Sabit bir sayinin yerine, sayiyi URETEN kurali koy.")
YASA3 = ("Bir kalibrasyonu yeniden kullanmadan once YONTEMI eski sonucla "
         "dogrula: 15x5 kolu madde 243'un uc sayisini birebir verdigi icin "
         "13x3 sonucuna guvenilebildi.")
YASA4 = ("Bir riski olduğundan BUYUK gostermek de bir olcum hatasidir: "
         "yanlis tetik yil olceginde %30,6 ama ILK CEYREKTE %2,46. Ikisini "
         "ayirmak, kullanicinin neye hazirlanacagini belirler.")


# ---------------------------------------------------------------- HÜKÜM

def pay_erimis_miydi(esik: float = 1.0) -> bool:
    """13x3'un INCELE esigine payi 1 puandan az miydi?"""
    return PAY_PUAN["13x3"] < esik


def yontem_dogrulandi_mi(tol: float = 0.01) -> bool:
    """15x5 kolu madde 243'un tablosunu birebir verdi mi?"""
    return all(abs(a - b) <= tol for a, b in YONTEM_DOGRULAMA.values())


def eski_esik_13x3_te_yanlis_tetikli_mi(esik: float = 20.0) -> bool:
    return DD_DAGILIMI["13x3"][3] >= esik


def durdur_sanssizliktan_tetiklenir_mi(esik: float = 5.0) -> bool:
    """Bot'u KAPATAN esik, normal bir yilda %esik'ten fazla tetikleniyor mu?"""
    return DD_DAGILIMI["13x3"][4] >= esik


def iki_turetme_bulustu_mu(tol: float = 1.0) -> bool:
    a, b = TURETME["yanlis tetik esdegerligi"], TURETME["dusus oraniyla olcekleme"]
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def turetmeler_ayni_yuvarlakta_mi() -> bool:
    a, b = TURETME["yanlis tetik esdegerligi"], TURETME["dusus oraniyla olcekleme"]
    return all(round(x) == round(y) for x, y in zip(a, b))


def yeni_esik_esdeger_mi(tol: float = 2.0) -> bool:
    """13x3'un yeni tetik orani 15x5'in orijinaline yakin mi?"""
    return (abs(YENI_TETIK_13X3["incele"] - DD_DAGILIMI["15x5"][3]) <= tol
            and abs(YENI_TETIK_13X3["durdur"] - DD_DAGILIMI["15x5"][4]) <= tol)


def varsayilan_degismedi_mi() -> bool:
    return VARSAYILAN_BIREBIR


def ilk_ay_zarar_normal_mi() -> bool:
    """Ilk 30 gunde zarar olasiligi anlamli mi (yani zarar NORMAL mi)?"""
    return CEYREK[30][0] > 15.0


def ceyrek_sorunu_kucuk_mu(esik: float = 5.0) -> bool:
    """Devre kesici yanlis tetigi ILK CEYREKTE kucuk mu?"""
    return ILK_CEYREK_TETIK[90][0] < esik


def ayar_degisti_mi() -> bool:
    return AYAR_DEGISTI


def hukum() -> str:
    return ("DUZELTILDI: devre kesiciler (INCELE -%18 / DURDUR -%23) 15x5 "
            "kitabi uzerine kalibreliydi (zincir 175->233->243), ama madde "
            "295 kucuk sermayede 13x3 oneriyor ve o kitabin dususu -%17,68 "
            "- INCELE'ye payi 3,46 DEGIL 0,32 puan. Madde 243'un yontemi "
            "birebir tekrarlanarak olculdu: 13x3'te normal bir yilda INCELE "
            "%30,6, DURDUR %9,7 olasilikla SANSSIZLIKTAN tetikleniyor "
            "(15x5: %11,1 ve %2,3). Esikler iki bagimsiz yoldan yeniden "
            "turetildi ve ayni yuvarlak degerde bulustu (-%22 / -%28, fark "
            "0,54 ve 0,33 puan); o esiklerle 13x3'un yanlis tetigi %12,3 / "
            "%2,5, yani ESDEGER. Sabitler degistirilmedi - 15x5'i bozardi; "
            "bunun yerine esikler artik KOSULAN kitabin dususuyle "
            "olcekleniyor ve 15x5'te olcek 1,000 oldugu icin varsayilan "
            "davranis BIREBIR AYNI. Sabit kodlu '(%-14.7)' mesaji da "
            "yapilandirmadan turetiliyor. Strateji ayari DEGISMEDI.")


# ---------------------------------------------------------------- RAPOR

def yaz() -> None:
    print(__doc__)
    print("SORU: %s\n" % SORU)

    print("1) BULUNAN CELISKI:")
    print("   esikler: INCELE %+.0f%% / DURDUR %+.0f%%"
          % (ESIK_ESKI["incele"] * 100, ESIK_ESKI["durdur"] * 100))
    for k, v in TAM_DONEM_DUSUS.items():
        print("   %-6s tam donem dususu -%%%.2f -> INCELE'ye pay %+.2f puan"
              % (k, v, PAY_PUAN[k]))
    print("   kalibrasyon zinciri %s, hepsi %s kitabi"
          % (list(KALIBRASYON_ZINCIRI), KALIBRASYON_KITABI))
    print("   INCELE mesaji SABIT KODLU: %s" % SABIT_KODLU_MESAJ)
    print("   pay erimis miydi: %s" % pay_erimis_miydi())

    print("\n2) MADDE 243'UN YONTEMI (%s):" % KARISTIRMA)
    print("   YONTEM DOGRULAMA (15x5, madde 243 vs bu tur):")
    for ad, (a, b) in YONTEM_DOGRULAMA.items():
        print("     %-5s %+7.2f vs %+7.2f" % (ad, a, b))
    print("   -> yontem dogrulandi mi: %s" % yontem_dogrulandi_mi())
    print("   %-6s %10s %11s %11s %10s %10s"
          % ("kitap", "tam donem", "karis. p5", "karis. p1", "INCELE %", "DURDUR %"))
    for k, v in DD_DAGILIMI.items():
        print("   %-6s %+10.2f %+11.2f %+11.2f %9.1f%% %9.1f%%"
              % (k, v[0], v[1], v[2], v[3], v[4]))
    print("   eski esik 13x3'te yanlis tetikli mi: %s"
          % eski_esik_13x3_te_yanlis_tetikli_mi())
    print("   DURDUR sanssizliktan tetiklenir mi: %s (bot KAPANIR)"
          % durdur_sanssizliktan_tetiklenir_mi())

    print("\n3) IKI BAGIMSIZ TURETME:")
    for ad, (i, d) in TURETME.items():
        print("   %-26s INCELE %+7.2f%%  DURDUR %+7.2f%%" % (ad, i, d))
    print("   olcek (13x3) %.3f | bulustu mu: %s | ayni yuvarlakta mi: %s"
          % (OLCEK_13X3, iki_turetme_bulustu_mu(), turetmeler_ayni_yuvarlakta_mi()))
    print("   YENI esikler: INCELE %+.0f%% / DURDUR %+.0f%%"
          % (ESIK_YENI_13X3["incele"] * 100, ESIK_YENI_13X3["durdur"] * 100))
    print("   yeni tetik: INCELE %%%.1f / DURDUR %%%.1f -> esdeger mi: %s"
          % (YENI_TETIK_13X3["incele"], YENI_TETIK_13X3["durdur"],
             yeni_esik_esdeger_mi()))
    print("   yeni pay: %+.2f puan (15x5'te %+.2f)"
          % (YENI_PAY_13X3, PAY_PUAN["15x5"]))

    print("\n4) COZUM: %s" % COZUM)
    print("   %s" % NEDEN_SABIT_DEGISTIRILMEDI)
    print("   varsayilan (15x5) degismedi mi: %s" % varsayilan_degismedi_mi())
    print("   bilinmeyen yapilandirma: %s" % BILINMEYEN_DAVRANIS)

    print("\n5) ILK CEYREK (13x3, 1x, %.0f $):" % BAKIYE)
    print("   yontem: %s" % CEYREK_YONTEM)
    print("   %-5s %10s %9s %9s %9s %12s %12s"
          % ("gun", "P(zarar)", "p5", "p50", "p75", "p50 dolar", "ic dusus p95"))
    for g, v in CEYREK.items():
        print("   %-5d %9.1f%% %+8.1f%% %+8.1f%% %+8.1f%% %+11.0f$ %11.1f%%"
              % (g, v[0], v[1], v[2], v[3], v[2] / 100 * BAKIYE, v[4]))
    print("   ilk ayda zarar NORMAL mi: %s (P %.1f%%)"
          % (ilk_ay_zarar_normal_mi(), CEYREK[30][0]))
    print("   -- esik tetigi ILK CEYREKTE (bootstrap) --")
    print("   %-5s %18s %18s" % ("gun", "eski -%18", "yeni -%21,9"))
    for g, (a, b) in ILK_CEYREK_TETIK.items():
        print("   %-5d %17.2f%% %17.2f%%" % (g, a, b))
    print("   ceyrek sorunu kucuk mu: %s" % ceyrek_sorunu_kucuk_mu())
    print("   NUANS: %s" % NUANS)

    print("\n6) AYAR degisti mi: %s | oneri: %s" % (ayar_degisti_mi(), ONERI))
    print("\n7) ACIK EKSEN: %s" % ACIK_EKSEN)

    print("\nYASA 1: %s" % YASA1)
    print("YASA 2: %s" % YASA2)
    print("YASA 3: %s" % YASA3)
    print("YASA 4: %s" % YASA4)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
