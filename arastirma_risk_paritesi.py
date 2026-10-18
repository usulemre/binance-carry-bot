"""MADDE 251: RISK PARITESI - sart 1'i GECEN ilk aday ailesi, ve yine kâr etmiyor.

Kullanicinin sorusu: "acaba finansal baska kavramlar, terimler mi test
etsek, eksik o mu ki". Dogru soru. Tahminle cevap vermek yerine projenin
sicilini (261 README bolumu) bir KAVRAM LISTESINE karsi taradim; iki
gercek bosluk cikti (asagi, bolum 4). Birincisi burada olculdu.

BOSLUK: **bacak AGIRLIGI**. Kitap her bacaga esit PARA veriyor
(`y[lo]=taban/len(lo)`). Esit RISK vermek - oynakliga ters agirlik -
madde 116'da olculmus ve "panele bagli gurultu" denip varsayilan
YAPILMAMISTI. Ama o olcum madde 182'nin 41 puanlik sizintisi ve madde
209'un sinyal hatasi DUZELTILMEDEN once, Sharpe 0,86-1,50 bandindaki bir
taban uzerinde yapildi. **Bugunun yuzeyinde (Sharpe 2,94) hic
olculmedi** - ve madde 222'nin kurali tam olarak bunu yeniden acmayi
emrediyor.

DEFTERIN GORMEDIGI DELIK (bu turun arac bulgusu): madde 240'in yeniden
acma defteri bunu YAKALAYAMAZDI, cunku agirlik bir PARAMETRE degil -
`carry_bot.py`'de adi olan bir sabit yok, esit agirlik KODA GOMULU. Defter
yalnizca BUYUK HARF atamalarini okuyor. Yani defter "parametre bayatligini"
deneteliyor ama "YAPISAL SECIM bayatligini" denetlemiyordu. Duzeltildi:
`arastirma_yeniden_acma_defteri.py`'ye `YAPISAL_SECIM` eklendi.

Motor bayragi: `AGIRLIK=vol` + `AG_TABAN` (buzme) + `AG_KIRP` (kirpma).
Agirlik TARAF BASINA normalize edilir, yani taraf notrlugu ve toplam brut
AYNEN korunur - olculen sey saf agirlik dagilimi.
PARITE: AGIRLIK=esit ile kontrol birebir (+%112,3 / 3,10 / -14,5).

================================================================
1) CEPHE: SHARPE ARTIYOR, PARA ARTMIYOR
================================================================
Kontrol: +%112,3 · Sharpe 2,939 · 22-24 2,789 · 25-26 3,147 · -%14,5

  aday              yillik  Sharpe   22-24   25-26   dusus  esit-risk  kald.  sart1
  saf 1/vol          +87,3   2,965   2,833   3,154   -15,6     +79,0  0,926   OK
  1/(vol+0,02)       +96,0   3,001   2,873   3,182   -15,0     +92,3  0,970   OK
  1/(vol+0,05)      +101,1   3,000   2,865   3,187   -14,7     +99,4  0,987   OK
  1/(vol+0,10)      +104,8   2,989   2,849   3,183   -14,6    +104,2  0,996   OK
  1/(vol+0,15)      +106,6   2,981   2,838   3,179   -14,6    +106,4  0,999   OK
  1/(vol+0,25)      +108,4   2,970   2,824   3,171   -14,5    +108,4  1,000   OK
  1/(vol+0,50)      +110,1   2,957   2,810   3,162   -14,5    +110,2  1,001   OK

**YEDISININ HEPSI SART 1'I GECTI - IKI ALT DONEMDE BIRDEN.** Bu projede
gorulmemis bir sey: madde 248 sart 1'in yanlis red oranini %77,8 olarak
olcmus ve 223-250 arasi her adayi oradan dusurmustu. Risk paritesi o
kapidan gecen ILK aile.

**AMA YEDISI DE SART 3'TEN DUSTU** (esit riskte getiri). Ve cephe
MONOTON: buzme (AG_TABAN) buyudukce esit-risk getirisi +79,0'dan
+110,2'ye tirmaniyor ama kontrolun +112,3'unu **HIC GECMIYOR** -
limitte (taban -> sonsuz) agirlik esite donuyor, yani KONTROLUN
KENDISINE yakinsiyor. Iceride baskin bir optimum YOK.

================================================================
2) BOOTSTRAP: SHARPE KAZANCI GERCEK, PARAYA DONMUYOR
================================================================
Esli blok bootstrap, 4.000 ornek, 20 gunluk bloklar:

  aday             esit-risk fark      P(>0)      Sharpe farki      P(>0)
  1/(vol+0,02)     -2,8 puan (sd 17,3)  %39,3    +0,071 (sd 0,103)  %75,2
  1/(vol+0,50)     +0,6 puan (sd  3,1)  %56,2    +0,019 (sd 0,019)  %85,6

Iki satir birlikte okunmali: **Sharpe iyilesmesi SAGLAM** (P %75 ve
%86 - projenin olctugu en tutarli etkilerden biri), ama **esit riskte
para farki SIFIR** (P %39 ve %56 - yazi tura). Yani risk paritesinin
verdigi sey getiri degil OYNAKLIK AZALTIMI, ve o azaltim kaldiracla
geri kazanildiginda elde bir sey kalmiyor.

**SART 3'UN VAROLMA SEBEBI TAM OLARAK BUDUR.** Madde 248 sart 3'un
sicilini "yalnizca madde 240'in rezerv esiklerini engelledi, kazanc
+0,3 puan - yani hic" diye yazmisti. Bu tur o sicili DEGISTIRIYOR: sart
3 burada butun bir aileyi, 33 puana kadar maliyetle engelledi ve
bootstrap onu bagimsiz olarak dogruladi. Sart 3 artik "gurultulu bir
veto" degil, Sharpe ile PARA'yi ayiran kapi.

================================================================
3) NEDEN: EN OYNAK COINLER EN YUKSEK FUNDING'I ODUYOR
================================================================
Secici en uc funding'i arar; en uc funding en oynak coinlerde olur
(madde 116'nin "funding-orantili agirlik konsantrasyon yaratiyor"
bulgusunun aynadaki hali). Oynakliga TERS agirlik vermek, tam olarak
PRIMIN EN YUKSEK oldugu bacaklari KUCULTUR. Sharpe artiyor cunku
oynaklik dusuyor; getiri dusuyor cunku prim de dusuyor. Ikisi birbirini
goturuyor - madde 214'un "funding ve fiyat birbirini goturur, kâr TP
hasadindan gelir" bulgusunun agirlik eksenindeki karsiligi.

================================================================
4) KAVRAM KAPSAMA HARITASI (kullanicinin sorusunun asil cevabi)
================================================================
261 README bolumu bir kavram listesine karsi tarandi. KAPSAM dict'i
koddadir; ozet:

  TASIMA/BAZ ailesi        : KAPALI (145 takvim, 170 nakit-tasima,
                             174/219 borsalar arasi, 220 ceyreklik baz,
                             173.2 COIN-M, 249 ikinci borsa) - madde
                             220'nin duvari: hepsi AYNI primin bir yuzu
  SINYAL/FAKTOR ailesi     : KAPALI (152 ML, 148/179 kalabalik,
                             178/228 emir akisi, 244 ust trader, 212/246
                             sinyal sekli, 118 zaman serisi momentum)
  RISK/BOYUT ailesi        : 165 kaldirac+vol hedefi, 245 doz siniri,
                             191 stop, 250 ortalama dusurme,
                             **251 risk paritesi (BU TUR)**
  ICRA ailesi              : KAPALI (213 butun eksen 3,3 puan)
  CIKIS ailesi             : KAPALI (227 seviye, 235 sekil, 154 takip,
                             167 solma, 229 bos koltuk)

  GERIYE KALAN GERCEK BOSLUK - IKI TANE:
  (a) ACIK POZISYON (open interest): madde 117'de indirme YARIM KALDI.
      `data_oi/` 60 sembol x gunluk (2022-06 -> 2026-08) duruyor. AMA
      uygun evrenin yalnizca **%51'ini** kapsiyor (gunluk ort 39,0
      uygun sembolden 19,7'si) -> kitabin yarisi sinyalsiz kalir ya da
      funding'e doner. Olculebilir ama KISITLI; sirada.
  (b) OPSIYON TURETILMISLERI (implied vol, skew, risk reversal):
      HIC denenmedi. Ama bu kutudan opsiyon verisi indirilemiyor ve
      kriptoda yalnizca BTC/ETH opsiyonu likit - 5+5 bacakli kesitsel
      bir kitabi besleyemez. YAPISAL OLARAK KAPALI, veri eksikligi degil.

Yani "eksik bir kavram" sorusunun cevabi: liste neredeyse tukenmis.
Kalan iki kalemden biri yarim veri, oteki yapisal olarak uygunsuz.

Kosum: python3 arastirma_risk_paritesi.py
"""

KONTROL = dict(yillik=112.3, sharpe=2.939, erken=2.789, gec=3.147, dusus=-14.5)

# aday: (yillik, Sharpe, 22-24, 25-26, dusus, esit-risk getiri, kaldirac)
CEPHE = {
    "saf 1/vol":      (87.3, 2.965, 2.833, 3.154, -15.6, 79.0, 0.926),
    "1/(vol+0,02)":   (96.0, 3.001, 2.873, 3.182, -15.0, 92.3, 0.970),
    "1/(vol+0,05)":  (101.1, 3.000, 2.865, 3.187, -14.7, 99.4, 0.987),
    "1/(vol+0,10)":  (104.8, 2.989, 2.849, 3.183, -14.6, 104.2, 0.996),
    "1/(vol+0,15)":  (106.6, 2.981, 2.838, 3.179, -14.6, 106.4, 0.999),
    "1/(vol+0,25)":  (108.4, 2.970, 2.824, 3.171, -14.5, 108.4, 1.000),
    "1/(vol+0,50)":  (110.1, 2.957, 2.810, 3.162, -14.5, 110.2, 1.001),
}
KIRILAN_SART = "esit riskte getiri"      # YEDISININ HEPSI (sart 3)

# aday: (esit-risk fark, std, P(>0), Sharpe fark, std, P(>0))
BOOTSTRAP = {
    "1/(vol+0,02)": (-2.8, 17.3, 39.3, +0.071, 0.103, 75.2),
    "1/(vol+0,50)": (+0.6, 3.1, 56.2, +0.019, 0.019, 85.6),
}

KAPSAM = {   # kavram ailesi: (durum, kapatan maddeler)
    "tasima/baz": ("KAPALI", "145, 170, 174, 219, 220, 173.2, 249"),
    "sinyal/faktor": ("KAPALI", "152, 148, 179, 178, 228, 244, 212, 246, 118"),
    "risk/boyut": ("KAPALI", "165, 245, 191, 250, 251"),
    "icra": ("KAPALI", "213"),
    "cikis": ("KAPALI", "227, 235, 154, 167, 229"),
    "acik pozisyon (OI)": ("KAPALI (MADDE 253) - tam evrende olculdu, eklemiyor", "117, 252, 253"),
    "opsiyon turetilmisleri": ("YAPISAL KAPALI - yalniz BTC/ETH likit", "-"),
}
OI_KAPSAM = dict(gunluk_ort_uygun=39.0, oi_verisi_olan=19.7, oran=51,
                 sembol=60, bas="2022-06-01", son="2026-08-31")

SEBEP = ("Secici en UC funding'i arar; en uc funding en OYNAK coinlerde olur. "
         "Oynakliga ters agirlik, primin en yuksek oldugu bacaklari kuculttur: "
         "Sharpe artar cunku oynaklik duser, getiri duser cunku prim de duser.")


def hepsi_sart1_gecti():
    """Cephedeki her aday iki alt donemde de Sharpe'i artirdi mi?"""
    return all(v[2] > KONTROL["erken"] and v[3] > KONTROL["gec"]
               for v in CEPHE.values())


def esit_risk_kontrolu_gecen():
    """Esit riskte kontrolu GECEN aday var mi? (sart 3)"""
    return [a for a, v in CEPHE.items() if v[5] > KONTROL["yillik"]]


def cephe_monoton():
    """Buzme buyudukce esit-risk getirisi monoton artiyor mu?"""
    sira = ["saf 1/vol", "1/(vol+0,02)", "1/(vol+0,05)", "1/(vol+0,10)",
            "1/(vol+0,15)", "1/(vol+0,25)", "1/(vol+0,50)"]
    e = [CEPHE[a][5] for a in sira]
    return all(e[i] < e[i + 1] for i in range(len(e) - 1))


def sharpe_saglam_para_degil():
    """Sharpe farki guvenilir (P>70), esit-risk farki yazi-tura (P<60)?"""
    return all(b[5] > 70.0 and b[2] < 60.0 for b in BOOTSTRAP.values())


if __name__ == "__main__":
    print("MADDE 251 - RISK PARITESI (oynakliga ters agirlik)\n")
    print("KONTROL: %+.1f%%  Sh %.3f  (22-24 %.3f / 25-26 %.3f)  dusus %.1f%%\n"
          % (KONTROL["yillik"], KONTROL["sharpe"], KONTROL["erken"],
             KONTROL["gec"], KONTROL["dusus"]))
    print("1) CEPHE")
    print("  %-16s%8s%8s%8s%8s%8s%11s%7s %s"
          % ("aday", "yillik", "Sharpe", "22-24", "25-26", "dusus", "esit-risk",
             "kald.", "sart1"))
    for a, v in CEPHE.items():
        s1 = v[2] > KONTROL["erken"] and v[3] > KONTROL["gec"]
        print("  %-16s%+8.1f%8.3f%8.3f%8.3f%8.1f%+11.1f%7.3f  %s"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5], v[6], "OK" if s1 else "-"))
    print("\n  hepsi sart 1'i gecti mi? %s  <- projede ILK"
          % ("EVET" if hepsi_sart1_gecti() else "HAYIR"))
    print("  esit riskte kontrolu gecen: %s" % (esit_risk_kontrolu_gecen() or "YOK"))
    print("  cephe monoton mu (limit = kontrol)? %s"
          % ("EVET" if cephe_monoton() else "HAYIR"))
    print("  -> kirilan sart: %s (7/7)" % KIRILAN_SART)

    print("\n2) BOOTSTRAP (4.000 ornek, 20 gunluk blok)")
    print("  %-16s%22s%10s%22s%10s"
          % ("aday", "esit-risk fark", "P(>0)", "Sharpe farki", "P(>0)"))
    for a, b in BOOTSTRAP.items():
        print("  %-16s%+14.1f (sd %4.1f)%9.1f%%%+14.3f (sd %5.3f)%9.1f%%"
              % (a, b[0], b[1], b[2], b[3], b[4], b[5]))
    print("\n  Sharpe saglam ama para degil mi? %s"
          % ("EVET" if sharpe_saglam_para_degil() else "HAYIR"))
    print("  -> SART 3'UN VAROLMA SEBEBI: Sharpe ile PARA'yi ayirir")

    print("\n3) NEDEN\n  %s" % SEBEP)

    print("\n4) KAVRAM KAPSAMA HARITASI")
    for k, (d, m) in KAPSAM.items():
        print("  %-24s%-34s%s" % (k, d, m))
    print("\n  acik pozisyon verisi: %d sembol, %s -> %s, uygun evrenin %%%d'i"
          % (OI_KAPSAM["sembol"], OI_KAPSAM["bas"], OI_KAPSAM["son"],
             OI_KAPSAM["oran"]))
