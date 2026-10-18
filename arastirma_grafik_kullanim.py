"""MADDE 255: GRAFIK MODELINI NASIL KULLANMALI - dort yol, dordu de RED,
ve kurala kalici bir ekleme (COK BAKIS DUZELTMESI).

Madde 254 grafik modelinin TP dolumunu gercekten ongordugunu (AUC 0,79)
ama havuz olcutu olarak kitabi yariya indirdigini gosterdi. O turun
ondalik tablosu TARAF ASIMETRIKTI: long tarafta tahmin ile para TERS
(en ust ondalik -%1,53), short tarafta DUZ (+1,72 puan). Bu tur o
asimetriyi kullanmanin dort yolunu denedi.

DURUSTLUK NOTU (bastan): bu, AYNI VERIYE IKINCI BAKIS. Yon, madde 254'un
kendi ondalik tablosundan secildi ve bu turda 8 varyant kosuldu. O yuzden
sart 1'i gecmek burada DELIL SAYILMAZ - asagidaki cokluk hesabi bunu
sayiyla gosteriyor - ve karar bootstrap'a, hem KONTROLE hem PLASEBOYA
karsi, birakildi.

================================================================
1) DORT KULLANIM (GUNLUK baz, tam evren, havuz acik)
================================================================
Kontrol: +%112,3 · Sharpe 2,939 · 22-24 2,789 · 25-26 3,147 · -%14,5

  aday                        yillik  Sharpe   22-24   25-26  dusus  esit-risk  sart1
  taraf asimetrik secim        +28,3   1,205   1,332   1,067  -23,2      +17,3    -
  long eleme %20              +101,7   2,814   2,683   3,011  -14,3     +103,7    -
  long eleme %40               +89,9   2,735   2,756   2,745  -14,7      +88,9    -
  long eleme %20 PLASEBO      +103,2   2,769   2,736   2,839  -14,2     +106,2    -
  harman w=0,25               +112,6   3,037   2,817   3,335  -14,6     +112,2   OK
  harman w=0,50               +109,4   3,183   2,987   3,451  -14,5     +110,0   OK
  harman w=0,50 PLASEBO        +98,8   2,760   2,706   2,844  -15,8      +88,3    -

OKUNUSU:
(a) TARAF ASIMETRIK SECIM COKTU (+%28,3). Long tarafta DUSUK olasilik
    secmek de ise yaramiyor: pahali opsiyondan kacinirken HIC ODEMEYEN
    opsiyonu aliyorsunuz. Madde 254'un ondalik tablosundaki ters iliski
    SECICI olarak kullanilamiyor - iki uc da kaybediyor.
(b) ELEME MEKANIK CIKTI: gercek eleme +%101,7, PLASEBO elemesi +%103,2 -
    plasebo DAHA IYI. Yani long adaylarin %20'sini atmanin etkisi
    bilgiden degil, aday sayisini azaltmaktan geliyor.
(c) HARMAN SART 1'I GECTI (iki agirlikta da) ve PLASEBO HARMANI GECMEDI
    (+%98,8 / 2,760, iki donemde de kontrolun altinda). Bu onemli: harmanin
    sart-1 gecisi harmanlama MEKANIGININ eseri DEGIL, modelin bilgisinin.

================================================================
2) AMA BOOTSTRAP: BILGI GERCEK, PARA AYIRT EDILEMEZ
================================================================
Esli blok bootstrap, 4.000 ornek, 20 gunluk blok, ESIT RISKTE:

  aday            karsi        d esit-risk      std    P(>0)
  harman w=0,25   KONTROL         +5,7 puan     13,7    %68,0
  harman w=0,25   PLASEBO        +25,3 puan     24,4    %88,2
  harman w=0,50   KONTROL        +11,4 puan     30,3    %63,5
  harman w=0,50   PLASEBO        +30,3 puan     36,3    %80,0

IKI SORU, IKI CEVAP:
  * "Model bilgi tasiyor mu?"  -> PLASEBOYA karsi P %88,2 / %80,0: EVET.
    Madde 254'un AUC 0,79'u ile tutarli; grafik gercekten bir sey biliyor.
  * "O bilgi PARA getiriyor mu?" -> KONTROLE karsi P %68,0 / %63,5:
    AYIRT EDILEMEZ. Madde 239 (+22,2 puan, P %79,0) ve madde 244
    (+8,5 puan, P %64,5) ayni bantta reddedilmisti.

Ve sart 3 ikisini de veto etti: esit riskte +112,2 ve +110,0 vs kontrol
+112,3. w=0,25'in farki **0,1 PUAN** - yani kilpayi degil, BERABERE.

KARAR: RED. Gerekce madde 251'in dersinin aynisi: Sharpe iyilesmesi
gercek (2,939 -> 3,037) ama esit riske cevrildiginde elde bir sey
kalmiyor. Model kitaba BILGI ekliyor, PARA eklemiyor - cunku ekledigi
bilgi, kalabalik olcutunun zaten gordugu seyin bir parcasi.

================================================================
3) KURALA KALICI EKLEME: COK BAKIS DUZELTMESI
================================================================
Madde 248 sart 1'in YANLIS RED oranini olctu (%77,8). Bu turda aynasina
ihtiyac duyuldu: bir turda k varyant denenirse, hepsi TAMAMEN ETKISIZ
olsa bile en az birinin sart 1'i gecme olasiligi

    P = 1 - (1 - 0,222)^k
    k=1 %22,2 · k=3 %53,0 · k=5 %71,4 · **k=8 %86,6** · k=12 %95,1

Bu turda 8 varyant kosuldu ve 2'si sart 1'i gecti - hesabin BEKLEDIGI
sonuc. Yani cok varyantli bir turda sart 1'i gecmek neredeyse hic delil
tasimaz. `karar_kurali.py`'ye eklendi: `cok_bakis_riski(k)` ve
`delil_mi(k, P_kontrol, P_plasebo)`.

YENI KURAL (madde 248'in "asil kapi bootstrap" tespitinin nicel hali):
  * sart 1 bir ON SURUDUR, delil degildir; tur basina BAKIS SAYISI
    raporlanir;
  * delil, bootstrap'in esit-risk farkidir (esik P>%80);
  * bir MODEL/TAHMIN adayinda bootstrap IKI KEZ kosulur - kontrole karsi
    (para) VE kendi plasebosuna karsi (bilgi). Ikisi ayri sorudur.

Madde 255 bu kurali kendi uzerinde uyguladi ve kendi adayini reddetti.

Kosum: python3 arastirma_grafik_kullanim.py
"""

KONTROL = dict(yillik=112.3, sharpe=2.939, erken=2.789, gec=3.147, dusus=-14.5)

# aday: (yillik, Sharpe, 22-24, 25-26, dusus, esit-risk, sart1_gecti)
KULLANIM = {
    "taraf asimetrik secim": (28.3, 1.205, 1.332, 1.067, -23.2, 17.3, False),
    "long eleme %20": (101.7, 2.814, 2.683, 3.011, -14.3, 103.7, False),
    "long eleme %40": (89.9, 2.735, 2.756, 2.745, -14.7, 88.9, False),
    "long eleme %20 PLASEBO": (103.2, 2.769, 2.736, 2.839, -14.2, 106.2, False),
    "harman w=0,25": (112.6, 3.037, 2.817, 3.335, -14.6, 112.2, True),
    "harman w=0,50": (109.4, 3.183, 2.987, 3.451, -14.5, 110.0, True),
    "harman w=0,50 PLASEBO": (98.8, 2.760, 2.706, 2.844, -15.8, 88.3, False),
}
KIRILAN_SART = {"harman w=0,25": "esit riskte getiri",
                "harman w=0,50": "esit riskte getiri"}

# (aday, karsi): (d esit-risk, std, P(>0))
BOOTSTRAP = {
    ("harman w=0,25", "KONTROL"): (+5.7, 13.7, 68.0),
    ("harman w=0,25", "PLASEBO"): (+25.3, 24.4, 88.2),
    ("harman w=0,50", "KONTROL"): (+11.4, 30.3, 63.5),
    ("harman w=0,50", "PLASEBO"): (+30.3, 36.3, 80.0),
}
# ayni bantta reddedilmis gecmis adaylar (madde 248'in sicilinden)
BENZER_REDLER = {"239 prim brutu e0,5": 79.0, "244 ust trader kolu %20": 64.5}

BAKIS_SAYISI = 8
COK_BAKIS_RISKI = 86.6          # karar_kurali.cok_bakis_riski(8)
SART1_GECEN = 2

MOTOR_VS_GUNLUK = {"harman w=0,50 motor": 3.39, "harman w=0,50 gunluk": 3.183}

DERS = ("Model kitaba BILGI ekliyor (plaseboya karsi P %88,2), PARA "
        "eklemiyor (kontrole karsi P %68,0). Cunku ekledigi bilgi, kalabalik "
        "olcutunun zaten gordugu seyin bir parcasi.")


def eleme_mekanik_mi():
    """Plasebo elemesi gercek elemeden KOTU DEGIL mi? (bilgi katmiyor)"""
    return (KULLANIM["long eleme %20 PLASEBO"][0]
            >= KULLANIM["long eleme %20"][0])


def harman_plasebodan_iyi_mi():
    """Gercek harman, plasebo harmanini sart 1'de geciyor mu?"""
    g = KULLANIM["harman w=0,50"]
    p = KULLANIM["harman w=0,50 PLASEBO"]
    return (g[6] and not p[6]
            and g[2] > KONTROL["erken"] and p[2] < KONTROL["erken"])


def para_ayirt_edilemez():
    """Kontrole karsi bootstrap zayif (P<%80), plaseboya karsi guclu (>%80)?"""
    return (all(BOOTSTRAP[(a, "KONTROL")][2] < 80.0
                for a in ("harman w=0,25", "harman w=0,50"))
            and all(BOOTSTRAP[(a, "PLASEBO")][2] >= 80.0
                    for a in ("harman w=0,25", "harman w=0,50")))


def sart1_delil_tasimiyor():
    """8 bakista sart 1 gecisi beklenen mi? (yani delil degil mi)"""
    return COK_BAKIS_RISKI > 80.0 and SART1_GECEN <= BAKIS_SAYISI


if __name__ == "__main__":
    print("MADDE 255 - GRAFIK MODELINI NASIL KULLANMALI\n")
    print("KONTROL: %+.1f%%  Sh %.3f  (22-24 %.3f / 25-26 %.3f)  dusus %.1f%%\n"
          % (KONTROL["yillik"], KONTROL["sharpe"], KONTROL["erken"],
             KONTROL["gec"], KONTROL["dusus"]))
    print("1) DORT KULLANIM (GUNLUK baz)")
    print("  %-26s%8s%8s%8s%8s%8s%11s %s"
          % ("aday", "yillik", "Sharpe", "22-24", "25-26", "dusus", "esit-risk",
             "sart1"))
    for a, v in KULLANIM.items():
        print("  %-26s%+8.1f%8.3f%8.3f%8.3f%8.1f%+11.1f  %s"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5], "OK" if v[6] else "-"))
    print("\n  eleme MEKANIK mi (plasebo daha iyi)? %s"
          % ("EVET" if eleme_mekanik_mi() else "HAYIR"))
    print("  harman plasebodan IYI mi (bilgi var)? %s"
          % ("EVET" if harman_plasebodan_iyi_mi() else "HAYIR"))

    print("\n2) BOOTSTRAP - IKI SORU, IKI CEVAP")
    print("  %-16s%-10s%14s%8s%9s" % ("aday", "karsi", "d esit-risk", "std", "P(>0)"))
    for (a, k), (d, s, p) in BOOTSTRAP.items():
        print("  %-16s%-10s%+14.1f%8.1f%8.1f%%" % (a, k, d, s, p))
    print("\n  para AYIRT EDILEMEZ mi? %s"
          % ("EVET" if para_ayirt_edilemez() else "HAYIR"))
    print("  ayni bantta reddedilmis gecmis adaylar: %s"
          % ", ".join("%s P%%%.1f" % (a, p) for a, p in BENZER_REDLER.items()))
    print("  kirilan sart: %s" % set(KIRILAN_SART.values()))
    print("  (w=0,25'in esit-risk farki yalnizca %.1f puan - BERABERE)"
          % (KULLANIM["harman w=0,25"][5] - KONTROL["yillik"]))

    print("\n3) COK BAKIS DUZELTMESI (kurala eklendi)")
    print("  bu turda %d varyant, %d tanesi sart 1'i gecti"
          % (BAKIS_SAYISI, SART1_GECEN))
    print("  HEPSI etkisiz olsa bile en az bir gecis olasiligi: %%%.1f"
          % COK_BAKIS_RISKI)
    print("  -> sart 1 bu turda DELIL TASIMIYOR mu? %s"
          % ("EVET" if sart1_delil_tasimiyor() else "HAYIR"))
    print("  motor vs GUNLUK Sharpe tuzagi: %.2f vs %.3f (gunluk kullanildi)"
          % (MOTOR_VS_GUNLUK["harman w=0,50 motor"],
             MOTOR_VS_GUNLUK["harman w=0,50 gunluk"]))
    print("\nKARAR: RED\n  %s" % DERS)
