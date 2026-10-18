"""MADDE 257: "YOGUN OYNAKLIKLI COINLERI YAKALA" - olculdu; cevap DOZ kararinda.

Kullanicinin onerisi: "yukselticek yaklasim gerekiyo, gunluk volatilitesi
cok yogun olan coinleri yakalamak gerekiyo".

Bu eksende projenin sicili var ama kullanicinin cercevesi iki yerde FARKLI
ve ikisi de bugunun yuzeyinde olculmemisti:
  * madde 251 oynakliga TERS agirligi olctu (risk paritesi) - bu onun AYNASI;
  * madde 142.2 oynaklikla orantili agirligi olctu AMA madde 182'nin 41
    puanlik sizintisi ve madde 209'un sinyal hatasi DUZELTILMEDEN ONCE
    (o turun tabani Sharpe 1,04-1,47 bandindaydi);
  * havuz olcutunu OYNAKLIK yapmak HIC denenmedi.

PARITE: iki yeni mod (AGIRLIK=volduz, ad=volsec) eklendikten sonra kontrol
birebir tekrar etti (+%112,3 / Sharpe 3,10 / dusus -14,5).
BAKIS SAYISI: 4 (madde 255'in kurali geregi raporlanir; cok-bakis riski %63,3).

================================================================
0) ONCE OLGU: KITAP ZATEN OYNAK COINLERI SECIYOR
================================================================
Bugunun panelinde, 301 rebalance aninda yillik oynaklik MEDYANI:

  secilen 10 bacak          **%128,2**
  secilmeyen UYGUN coinler    %91,7
  tum panel                   %91,4
  -> secici oynakliga **1,40 KAT** tilt yapiyor

Madde 142 bunu %101 vs %60 olarak olcmustu; bugunun yuzeyinde tilt DAHA
BUYUK. Sebebi mekanik: funding'in UC degerleri en oynak coinlerde olusur,
sinyal zaten oraya gidiyor. Yani bu bos bir eksen degil, kitabin MEVCUT
davranisi; soru "yakalamak" degil, "DAHA FAZLA yakalamak".

================================================================
1) DORT VARYANT, DORDU DE RED
================================================================
Kontrol: +%112,3 · Sharpe 2,939 · 22-24 2,789 · 25-26 3,147 · -%14,5

  aday                        yillik  Sharpe   22-24   25-26  dusus  esit-risk  kald.
  havuz olcutu = EN OYNAK      +62,3   1,670   1,959   1,439  -21,7      +38,4  0,647
  havuz olcutu = EN SAKIN      +22,7   1,681   1,463   2,142  -15,2      +21,6  0,955
  agirlik ~ oynaklik          +145,2   2,701   2,538   2,950  -19,0      +99,1  0,755
  agirlik ~ (oynaklik+0,02)   +132,9   2,761   2,611   2,990  -15,8     +117,4  0,914

DORDU DE SART 1'DEN DUSTU. Bootstrap (4.000 ornek, esli blok, esit riskte):
  agirlik ~ oynaklik          d **-13,1 puan**  std 22,8  P(>0) %24,6
  agirlik ~ (oynaklik+0,02)   d  **-8,5 puan**  std 18,2  P(>0) %29,5

(Dikkat: taban 0,02'nin NOKTA tahmini esit riskte +%117,4, yani kontrolun
+%112,3'unun USTUNDE - ama bootstrap -8,5 puan P %29,5 diyor. Madde 255'in
kurali tam bu durum icin yazildi: nokta tahmini DELIL DEGILDIR.)

SECIM TARAFININ OGRETTIGI: havuz olcutunu oynaklik yapmak kitabi yariya
indiriyor (+%62,3), ama EN SAKIN'i secmek daha da kotu (+%22,7). Yani
oynaklik YON olarak dogru bilgi tasiyor (yuksek, dusukten 40 puan iyi) -
ama o bilgiyi kullanmanin maliyeti, yerini aldigi KALABALIK OLCUTUDUR;
madde 256 o olcutu P %99,7 ile projenin en degerli katmani olarak olctu.
Oynaklik tiltini artirmak icin onu feda etmek, zaten sahip oldugunuz bir
seyi en degerli seyinizle degistirmektir.

================================================================
2) ASIL CEVAP: AYNI RISKTE KALDIRAC DAHA IYI
================================================================
Oynaklik agirligi getiriyi +%112,3'ten +%145,2'ye cikariyor (+33 puan) ama
dususu -%14,5'ten -%19,0'a goturuyor. Dogru kiyas, kontrolu AYNI dususe
kaldiraclamaktir:

  kontrol x1,319 (dusus -%19,0'a olceklenmis)   ->  **+%165,8**
  oynaklikla agirlikli kitap (dusus -%19,0)      ->   +%145,2
  FARK                                            ->  **kaldirac 20,6 puan ONDE**

Yani oynaklik agirliginin getirdigi ekstra getiri bir KENAR degil, RISK -
ve ustelik duz kaldiractan DAHA KOTU bir risk. Kaldirac ekstra risk alirken
kitabin sechiminin sekline dokunmuyor; oynaklik agirligi ise maruziyeti en
oynak bacaklara yigiyor ve esli blok bootstrap bunu 13 puan geride buluyor.

**KULLANICININ ISTEGININ DOGRU ADRESI MADDE 245'IN DOZ CEPHESIDIR.**
Daha yuksek getiri isteniyorsa yol bellidir ve ZATEN OLCULMUSTUR: kitabin
kendisine kaldirac. Madde 245 o cepheyi dogrusal buldu ve likidasyonun
3x'e kadar baglayici olmadigini olctu. Bu bir strateji degisikligi degil,
bir DOZ kararidir - ve madde 227'nin kaydina gore o karar CANLI OLCUM
ONCESINDE verilmemelidir.

================================================================
3) YENI YASA
================================================================
  **BIR TILT, DUZ KALDIRACI YENEMIYORSA, TILT DEGIL KALDIRACTIR.**
  Getiriyi artiran her aday icin su kiyas zorunludur: kontrolu adayin
  KENDI dususune kaldiraclayip getirileri karsilastir. Aday bu kiyasi
  kaybediyorsa, getirisi mekanizmadan degil maruziyetten geliyor ve
  "daha yuksek getiri" istegi doz ekseninde daha ucuza karsilanir.

Madde 250 (ortalama dusurme) ayni testi kaybetmisti; 257 onu bir KURALA
cevirdi. Madde 251 (risk paritesi) bu aynanin oteki yuzuydu: oynakliga
ters agirlik Sharpe'i artirip parayi artirmiyor, oynaklikla orantili
agirlik parayi artirip riski daha fazla artiriyor. **Esit agirlik ikisinin
ARASINDA ve ikisini de yeniyor** - ve bu, 142/251/257'nin uc bagimsiz
olcumunun ortak sonucu.

Kosum: python3 arastirma_oynaklik_tilt.py
"""

# --- olgu: kitap zaten oynak coinleri seciyor (bugunun paneli, 301 an) ---
OYNAKLIK_OLCUMU = {"secilen 10 bacak": 128.2, "secilmeyen uygun": 91.7,
                   "tum panel": 91.4}
TILT_KATI = 128.2 / 91.7
MADDE_142_OLCUMU = {"secilen": 101.0, "secilmeyen": 60.0}   # eski yuzey

KONTROL = dict(yillik=112.3, sharpe=2.939, erken=2.789, gec=3.147, dusus=-14.5)

# aday: (yillik, Sharpe, 22-24, 25-26, dusus, esit-risk, kaldirac)
VARYANT = {
    "havuz olcutu = EN OYNAK": (62.3, 1.670, 1.959, 1.439, -21.7, 38.4, 0.647),
    "havuz olcutu = EN SAKIN": (22.7, 1.681, 1.463, 2.142, -15.2, 21.6, 0.955),
    "agirlik ~ oynaklik": (145.2, 2.701, 2.538, 2.950, -19.0, 99.1, 0.755),
    "agirlik ~ (oynaklik+0,02)": (132.9, 2.761, 2.611, 2.990, -15.8, 117.4, 0.914),
}
KIRILAN_SART = "iki donemde Sharpe"       # DORDU DE
BOOTSTRAP = {   # aday: (d esit-risk, std, P(>0))
    "agirlik ~ oynaklik": (-13.1, 22.8, 24.6),
    "agirlik ~ (oynaklik+0,02)": (-8.5, 18.2, 29.5),
}
BAKIS_SAYISI = 4                           # madde 255 geregi raporlanir

# --- asil kiyas: ayni dususe kaldiraclanmis kontrol ---
KALDIRAC_KIYASI = dict(hedef_dusus=-19.0, kaldirac=1.319, kontrol_getiri=165.8,
                       aday_getiri=145.2)

YASA = ("BIR TILT, DUZ KALDIRACI YENEMIYORSA TILT DEGIL KALDIRACTIR. Getiriyi "
        "artiran her aday icin kontrolu adayin KENDI dususune kaldiraclayip "
        "getiriler karsilastirilir; aday kaybediyorsa getirisi mekanizmadan "
        "degil maruziyetten gelir.")
DOGRU_ADRES = ("madde 245'in doz cephesi - kitabin kendisine kaldirac. Dogrusal "
               "olculdu, likidasyon 3x'e kadar baglayici degil; ama madde "
               "227: doz karari CANLI OLCUM ONCESINDE verilmez.")


def kitap_zaten_oynak_seciyor():
    """Secilen bacaklarin oynakligi, secilmeyenlerden belirgin yuksek mi?"""
    return TILT_KATI > 1.25


def dordu_de_red():
    """Sart 1'i gecen varyant var mi?"""
    return [a for a, v in VARYANT.items()
            if v[2] > KONTROL["erken"] and v[3] > KONTROL["gec"]]


def kaldirac_onde_mi():
    """Ayni dususte duz kaldirac, oynaklik agirligini geciyor mu?"""
    k = KALDIRAC_KIYASI
    return k["kontrol_getiri"] > k["aday_getiri"]


def nokta_tahmini_yaniltiyor():
    """Taban 0,02'nin nokta tahmini kontrolu geciyor ama bootstrap gecmiyor?"""
    a = "agirlik ~ (oynaklik+0,02)"
    return (VARYANT[a][5] > KONTROL["yillik"] and BOOTSTRAP[a][0] < 0
            and BOOTSTRAP[a][2] < 80.0)


if __name__ == "__main__":
    print("MADDE 257 - OYNAKLIK TILTI\n")
    print("0) OLGU: KITAP ZATEN OYNAK COINLERI SECIYOR")
    print("  yillik oynaklik medyani (bugunun paneli, 301 an):")
    for a, v in OYNAKLIK_OLCUMU.items():
        print("    %-26s%%%.1f" % (a, v))
    print("    -> secici oynakliga **%.2f KAT** tilt yapiyor" % TILT_KATI)
    print("    (madde 142 eski yuzeyde %%%.0f vs %%%.0f olcmustu)"
          % (MADDE_142_OLCUMU["secilen"], MADDE_142_OLCUMU["secilmeyen"]))
    print("    bos eksen degil, MEVCUT davranis: %s"
          % ("DOGRULANDI" if kitap_zaten_oynak_seciyor() else "HAYIR"))

    print("\n1) DORT VARYANT  (bakis sayisi: %d)" % BAKIS_SAYISI)
    print("  %-28s%8s%8s%8s%8s%8s%11s%7s"
          % ("aday", "yillik", "Sharpe", "22-24", "25-26", "dusus", "esit-risk",
             "kald."))
    print("  %-28s%+8.1f%8.3f%8.3f%8.3f%8.1f%+11.1f%7.3f"
          % ("KONTROL", KONTROL["yillik"], KONTROL["sharpe"], KONTROL["erken"],
             KONTROL["gec"], KONTROL["dusus"], KONTROL["yillik"], 1.0))
    for a, v in VARYANT.items():
        print("  %-28s%+8.1f%8.3f%8.3f%8.3f%8.1f%+11.1f%7.3f"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5], v[6]))
    print("\n  sart 1'i gecen: %s  (kirilan: %s)"
          % (dordu_de_red() or "YOK (4/4 RED)", KIRILAN_SART))
    print("  bootstrap:")
    for a, (d, s, p) in BOOTSTRAP.items():
        print("    %-28s d%+7.1f puan  std %5.1f  P(>0) %%%.1f" % (a, d, s, p))
    print("  nokta tahmini yaniltiyor mu (madde 255'in durumu)? %s"
          % ("EVET" if nokta_tahmini_yaniltiyor() else "HAYIR"))

    print("\n2) ASIL KIYAS: AYNI RISKTE KALDIRAC")
    k = KALDIRAC_KIYASI
    print("  hedef dusus %.1f%%" % k["hedef_dusus"])
    print("    kontrol x%.3f               -> %+.1f%%" % (k["kaldirac"],
                                                          k["kontrol_getiri"]))
    print("    oynaklikla agirlikli kitap  -> %+.1f%%" % k["aday_getiri"])
    print("    FARK: kaldirac **%.1f puan ONDE**"
          % (k["kontrol_getiri"] - k["aday_getiri"]))
    print("  kaldirac onde mi? %s" % ("EVET" if kaldirac_onde_mi() else "HAYIR"))
    print("\n  DOGRU ADRES: %s" % DOGRU_ADRES)

    print("\n3) YENI YASA\n  %s" % YASA)
    print("\nAYAR DEGISMEDI.")
