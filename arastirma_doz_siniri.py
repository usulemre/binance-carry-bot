"""MADDE 245: "+%112 AZ" - dogru, ve o 1x satiri. DOZ CETVELI ve GERCEK SINIRI.

Kullanicinin itirazi hakli ama bir ARASTIRMA sorusu degil bir DOZ
sorusu: ayni strateji 2x brutte +%320, 3x'te +%675 veriyor ve Sharpe
DEGISMIYOR (vadeli islemde kaldiracin borclanma maliyeti yoktur; o
yuzden cetvel dogrusal). Madde 227'den beri bu fiyat listesi vardi ama
listenin GERCEK SINIRI hic olculmemisti: motor likidasyonu
modellemiyordu ve sart 4'un gerekcesi tam buydu.

Madde 245 o bosluğu kapatti.

================================================================
1) DOZ CETVELI (kontrolun gunluk serisi, likidasyon haric)
================================================================
  brut    yillik   maks dusus   en kotu gun   1 yil p5   1 yil p1
  1,00x  +%112,5     -%14,5        -%10,4      -%20,1     -%24,8
  1,25x  +%153,6     -%18,0        -%13,1      -%25,8     -%31,2
  1,50x  +%201,5     -%21,4        -%15,7      -%29,1     -%35,8
  2,00x  +%320,3     -%28,1        -%20,9      -%38,5     -%45,9
  2,50x  +%475,8     -%34,5        -%26,1      -%45,5     -%54,1
  3,00x  +%675,3     -%40,7        -%31,3      -%52,5     -%60,7

(1 yil p5/p1: madde 243'un SIRALAMA testiyle, 5.000 ornek - yani
gerceklesen sansli siraya DEGIL, ayni getiri dagilimina gore.)

================================================================
2) LIKIDASYON ARITMETIGI - ILK KEZ OLCULDU
================================================================
Kitabin en kotu TEK BARI (4 saat) brut 1x'te yalnizca **-%3,81**
(9.022 bar; p0,1 -%2,32; en kotu gun -%10,89). Cross marjda hayatta
kalma kosulu: 1 - brut x hareket > m x brut (m = bakim marji ~%1).

  brut   en kotu bar   ruin icin gereken   GUVENLIK   bar sonrasi
         (gerceklesen)   net hareket        CARPANI    kalan ozkaynak
  1,0x      -%3,81          %99,0           26,0x        %96,2
  1,5x      -%5,72          %65,7           17,2x        %94,3
  2,0x      -%7,62          %49,0           12,9x        %92,4
  3,0x     -%11,43          %32,3            8,5x        %88,6
  5,0x     -%19,06          %19,0            5,0x        %80,9
  8,0x     -%30,49          %11,5            3,0x        %69,5

**Likidasyon, brut <= 3x icin bağlayici kisit DEGIL** (guvenlik carpani
8,5x+). Bağlayici kisit DUSUSUN KENDISI: 2x'te 100 yilda 1 yil -%46,
3x'te -%61.

================================================================
3) TEK BACAK TEHLIKESI - yok (muhasebe ozdesligi ile dogrulandi)
================================================================
Madde 236'nin katki defteri (44.961 bacak) 15 fazin toplamini tasir.
Olcek ozdeslikle dogrulandi: defter/15 = +329,4 puan vs kitabin basit
getiri toplami +322,9 puan (**bagil fark %2,0**).

  bacak basina kitap katkisi (brut 1x)
  en kotu bacak        -1,69 puan
  en kotu 5            -1,69 · -1,29 · -1,22 · -1,19 · -1,17
  p0,01 / p0,1 / p1    -1,16 / -0,55 / -0,22
  en iyi bacak         +1,36 puan

En kotu bacak, en kotu GUNUN yalnizca %15'ini acikliyor. Brut 5x'te bile
hesabin %8,4'unu goturur. **Tek isim riski kitabi olduremez** - 10 bacak
x 15 dilim cesitlendirmesi bunu kesiyor. Risk korelasyonlu dususte.

================================================================
4) BUNUN SART 4 ICIN ANLAMI (kural DEGISTIRILMEDI)
================================================================
Sart 4'un (madde 225) yazili gerekcesi sudur: "motor likidasyonu
modellemez, yani kiyas modellenen getiriyi MODELLENMEYEN bir tehlikeye
karsi fiyatlar." Madde 245 o tehlikeyi OLCTU: brut 3x'e kadar guvenlik
carpani 8,5x+, ve tek bacak riski yok.

Bu, sart 4 icin bir KURAL GOZDEN GECIRME adayidir - ama **aday eldeyken
kural gevsetilmez** (madde 212'nin kapattigi delik). Madde 239'un prim
brutu (1,06x) ve madde 244'un ust trader kolu (1,13x) sart 4'ten
reddedilmisti; ikisi de yeniden degerlendirilmek icin kuralin KENDI
basina, aday olmadan revize edilmesini bekler.

================================================================
5) ASIL CEVAP
================================================================
"+%112 az" dogru - ama o rakam cetvelin 1x satiridir ve bir ARASTIRMA
sonucu degil bir RISK TERCIHIDIR. 245 madde su ikisini ayirdi:

  - Sharpe'i yukseltmek: ARASTIRMA isi. Burada tikaniktik (~3,1) ve
    240-244 bunu tek tek, ortak, risk tarafindan ve alternatif
    stratejilerle kapatti.
  - Getiriyi yukseltmek: DOZ isi. Cetvel hazir, dogrusal, ve sinirlari
    artik olculu.

Siralama degismedi (madde 227): once kucuk parayla canli olcum, SONRA
doz. Cunku cetvelin TAMAMI backtest'in +%112,5'ine dayaniyor; o rakam
yanlissa her satir ayni oranda yanlis.

Kosum: python3 arastirma_doz_siniri.py
"""

CETVEL = {   # brut: (yillik, maks dusus, en kotu gun, 1y p5, 1y p1)
    1.00: (112.5, -14.5, -10.4, -20.1, -24.8),
    1.25: (153.6, -18.0, -13.1, -25.8, -31.2),
    1.50: (201.5, -21.4, -15.7, -29.1, -35.8),
    2.00: (320.3, -28.1, -20.9, -38.5, -45.9),
    2.50: (475.8, -34.5, -26.1, -45.5, -54.1),
    3.00: (675.3, -40.7, -31.3, -52.5, -60.7),
}

EN_KOTU_BAR = 3.81      # % , brut 1x, 4 saatlik bar (9.022 bar)
EN_KOTU_GUN = 10.89     # %
BAKIM_MARJI = 0.01      # m

LIKIDASYON = {   # brut: (en kotu bar %, gereken net hareket %, guvenlik carpani)
    1.0: (3.81, 99.0, 26.0), 1.5: (5.72, 65.7, 17.2), 2.0: (7.62, 49.0, 12.9),
    3.0: (11.43, 32.3, 8.5), 5.0: (19.06, 19.0, 5.0), 8.0: (30.49, 11.5, 3.0),
}

BACAK = {   # brut 1x, kitap katkisi PUAN
    "en kotu": -1.69, "p0,01": -1.16, "p0,1": -0.55, "p1": -0.22,
    "en iyi": +1.36,
}
OZDESLIK = {"defter/15": 329.4, "kitap basit": 322.9, "bagil fark %": 2.0}


def guvenlik(brut, en_kotu_bar=None, m=BAKIM_MARJI):
    """Ruin icin gereken net hareket / gerceklesen en kotu bar."""
    w = (en_kotu_bar if en_kotu_bar is not None else EN_KOTU_BAR) / 100.0
    return ((1 - m * brut) / brut) / (brut * w) * brut   # = gereken/(brut*w)*brut


if __name__ == "__main__":
    print("MADDE 245 - DOZ CETVELI VE GERCEK SINIRI\n")
    print("1) DOZ CETVELI (Sharpe her satirda AYNI; vadelide kaldirac borc maliyeti YOK)")
    print("  %-8s%10s%12s%14s%11s%11s" % ("brut", "yillik", "maks dusus",
          "en kotu gun", "1y p5", "1y p1"))
    for g, t in CETVEL.items():
        print("  %-8s%+10.1f%12.1f%14.1f%11.1f%11.1f" % ("%.2fx" % g, *t))
    print("\n2) LIKIDASYON (en kotu 4 saatlik bar brut 1x'te -%.2f%%)" % EN_KOTU_BAR)
    print("  %-8s%14s%20s%12s" % ("brut", "en kotu bar", "ruin icin gereken",
                                  "guvenlik"))
    for g, (b, ger, gc) in LIKIDASYON.items():
        print("  %-8s%13.2f%%%19.1f%%%11.1fx" % ("%.1fx" % g, -b, ger, gc))
    print("  -> brut <= 3x icin likidasyon BAGLAYICI DEGIL (carpan 8,5x+)")
    print("     baglayici kisit DUSUSUN KENDISI")
    print("\n3) TEK BACAK TEHLIKESI (defter olcegi ozdeslikle dogrulandi: "
          "%%%.1f fark)" % OZDESLIK["bagil fark %"])
    for ad, v in BACAK.items():
        print("  %-10s%+8.2f puan" % (ad, v))
    print("  en kotu bacak, en kotu GUNUN %%%.0f'ini acikliyor"
          % (abs(BACAK["en kotu"]) / EN_KOTU_GUN * 100))
    for g in (2.0, 3.0, 5.0):
        print("  brut %.1fx'te en kotu bacak hesabin %%%.1f'ini goturur"
              % (g, abs(BACAK["en kotu"]) * g))
    print("\n4) SONUC: '+%112 az' dogru - ama o cetvelin 1x satiridir.")
    print("   Sharpe yukseltmek ARASTIRMA isi (tikanik, ~3,1).")
    print("   Getiri yukseltmek DOZ isi (cetvel hazir ve dogrusal).")
    print("   Sira degismedi: ONCE canli olcum, SONRA doz (madde 227).")
