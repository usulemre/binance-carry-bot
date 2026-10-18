"""MADDE 252: ACIK POZISYON (open interest) - listenin SON kalemi kapandi.

!!! MADDE 253 BU TURUN KAPSAM GEREKCESINI DUZELTTI. Asagidaki "%51 kapsam"
ve "olcum kitabin en zayif ucte biri uzerinde" ifadeleri YANLIS KAYNAKTAN
geliyordu: `data_oi/` eski ve kismi bir indirmeydi; uretim panelinin
kendisi (`/tmp/metrik_panel.pkl`) OI'yi **%97,7** kapsamla zaten
tasiyordu. Madde 253 olcumu TAM EVRENDE ve havuz acik tekrarladi:
3/3 yine RED (bootstrap -9,5 puan, P(>0) %19,7). SONUC AYAKTA, GEREKCE
DEGISTI. Yeniden acma kosulu EMEKLI (zaten karsilanmisti).
Ayrintisi: `arastirma_veri_kaynagi.py`.

Madde 251'in kavram kapsama haritasi iki bosluk bırakmisti: (a) acik
pozisyon (madde 117'de indirme YARIM KALDI), (b) opsiyon turetilmisleri
(yapisal olarak uygunsuz - kriptoda yalniz BTC/ETH likit). Bu tur (a)'yi
olctu. Yani olculebilir kavram listesi artik BITTI.

YONTEM: motora yeni bayrak EKLENMEDI. Motor `SK_DOSYA` ile distan sinyal
kabul ettigi icin varyantlar panel olarak disarida kuruldu ve beslendi -
parite riski sifir, motor dosyasi hic degismedi.

NEDENSELLIK: OI verisi GUNLUK. Gun D'nin degeri D+1 00:00'dan itibaren
bilinir sayildi (bir gun gecikme), sonra 4 saatlik bara ileri dolduruldu.

================================================================
1) ILK ENGEL: OI VERISI PRIMIN YASADIGI YERDE YOK
================================================================
`data_oi/` 60 sembol x gunluk (2022-06 -> 2026-08). Uygun evrenin
gunluk ortalama 39,0 sembolunden yalnizca **19,7'si** kapsaniyor (%51).

Daha onemlisi: o 60 sembole DARALTILMIS kitap, uretim sinyaliyle bile
yalnizca **+%34,4 / Sharpe 1,953** veriyor - tam kitap +%112,3 / 2,939.
Yani OI verisi olan buyuk sembollerde kitap kendi kenarının ucte birini
buluyor. **Prim, OI verisi OLMAYAN kucuk/uc coinlerde yasiyor.**
Bu, olcumun KAPSAMINI bastan sinirlar: "OI funding'e ekliyor mu"
sorusuna yalnizca kitabin en zayif ucte biri uzerinde cevap verilebilir.

Kalabalik havuzu (taraf basina 15 aday) 19,7 sembolluk evrende
kurulamaz; DORT kosumun hepsinde havuz kapatildi (eslesmis).

================================================================
2) UC VARYANT, UCU DE RED
================================================================
Eslesmis kontrol (uretim funding sinyali, ayni 60 sembol, havuz kapali):
  +%34,4 · Sharpe 1,953 · 22-24 2,262 · 25-26 1,420 · -%13,1

  aday                                 yillik  Sharpe   22-24   25-26  dusus  esit-risk
  funding x OI (odenen DOLAR kirasi)    +12,0   0,703   1,169  -0,171  -17,6      +9,1
  funding x OI/OI_30gun (yukseklik)     +27,7   1,533   1,681   1,283  -11,5     +31,9
  yalniz OI yuksekligi (funding YOK)    +34,1   1,406   1,587   1,105  -17,6     +24,8

UCU DE SART 1'DEN DUSTU. En iyi varyant (OI yuksekligiyle olcekleme)
icin esli blok bootstrap (4.000 ornek, 20 gunluk blok, esit riskte):
  ort **-11,3 puan**  std 9,0  **P(>0) %9,8**
Yani madde 250 gibi: "gosterilemedi" degil, POZITIF OLARAK KOTU.

"Funding x OI" neden bu kadar kotu: OI dolar cinsinden ve buyuk
coinlerde buyuk, yani odenen dolar kirasina gore siralamak kitabi
BUYUK KAPLARA tiklyor - orada funding orani (yani birim sermaye basina
kira) en dusuk. Bu, madde 116'nin "funding-orantili agirlik
konsantrasyon yaratir" bulgusunun sinyal tarafindaki esi.

================================================================
3) ASIL DERS: OI YENI BIR PRIM DEGIL, AYNI PRIMIN DAHA GURULTULU YUZU
================================================================
Dorduncu kosum bir PLASEBO olarak eklenmisti: funding HIC kullanilmadan,
yalnizca OI'nin kendi 30 gunluk ortalamasina gore yuksekligine gore
siralama. Sonuc ogretici:

  yalniz OI yuksekligi : +%34,1  Sharpe 1,406  dusus -%17,6
  uretim funding       : +%34,4  Sharpe 1,953  dusus -%13,1

**GETIRILER NEREDEYSE AYNI** (+34,1 vs +34,4) ama Sharpe 1,41 vs 1,95 ve
dusus -17,6 vs -13,1. Yani OI yuksekligi, funding'in olctugu seyin
BUYUK KISMINI olcuyor - ikisi ayni kaldirac talebini goruyor - ama OI
onu daha GURULTULU goruyor. Funding o talebin FIYATI, OI ise MIKTARI;
fiyat daha temiz bir sinyal.

Bu madde 220'nin duvarinin son dogrulamasidir: "bu piyasadaki her carry
primi AYNI primin bir yuzu". Duvar simdiye kadar baska URUNLERDE
(takvim bazi, ceyreklik baz, borsalar arasi fark, ikinci borsa) test
edilmisti; 252 onu ayni urunun baska BIR OLCUSUNDE dogruladi. Funding
zaten o primin en dogrudan ve en az gurultulu olcusu.

================================================================
4) KAPSAM SINIRI - DURUST HALI
================================================================
Bu olcum sunu GOSTERMEZ: "OI tam evrende de ise yaramaz". Gosterdigi:
OI verisinin VAR OLDUGU yerde OI, funding'e bir sey EKLEMIYOR ve tek
basina ondan daha kotu. Kalan %49 olculemez cunku madde 117'nin indirmesi
hic bitmedi ve bu kutudan Binance API'si erisilemiyor (451).

YENIDEN ACMA KOSULU: `data_oi/` uygun evrenin en az %85'ini kapsadiginda
(bugun %51) - yani ~35 sembol daha indirildiginde. Indirme betigi
(`indir_oi.py`) kaldigi yerden devam eder; API erisimi olan bir ortamda
~6 saat surer.

Kosum: python3 arastirma_acik_pozisyon.py
"""

KAPSAM = dict(sembol=60, bas="2022-06-01", son="2026-08-31",
              gunluk_ort_uygun=39.0, oi_kapsanan=19.7, oran=51)

# daraltilmis evrenin kendi zayifligi: ayni sinyal, iki evren
EVREN_BEDELI = {"tam kitap (847 panel)": (112.3, 2.939),
                "60 sembol + havuz kapali": (34.4, 1.953)}

KONTROL = dict(yillik=34.4, sharpe=1.953, erken=2.262, gec=1.420, dusus=-13.1)

# aday: (yillik, Sharpe, 22-24, 25-26, dusus, esit-risk getiri)
VARYANT = {
    "funding x OI (dolar kirasi)": (12.0, 0.703, 1.169, -0.171, -17.6, 9.1),
    "funding x OI/OI_30g": (27.7, 1.533, 1.681, 1.283, -11.5, 31.9),
    "yalniz OI yuksekligi (funding YOK)": (34.1, 1.406, 1.587, 1.105, -17.6, 24.8),
}
KIRILAN_SART = "iki donemde Sharpe"      # UCU DE
BOOTSTRAP = dict(aday="funding x OI/OI_30g", ort=-11.3, std=9.0, p_pozitif=9.8,
                 ornek=4000)

DERS = ("Funding, kaldirac talebinin FIYATI; OI ise MIKTARI. Ikisi ayni seyi "
        "goruyor (getiriler +%34,1 vs +%34,4) ama fiyat daha az gurultulu "
        "(Sharpe 1,406 vs 1,953). Madde 220'nin duvari, ayni urunun baska bir "
        "OLCUSUNDE de gecerli.")
YENIDEN_ACMA_KOSULU = ("EMEKLI (madde 253): kosul zaten karsilanmisti - uretim "
                       "paneli OI'yi %97,7 kapsamla tasiyor, tam evrende de 3/3 RED")


def ucu_de_red():
    """Sart 1'i gecen varyant var mi? (iki alt donemde de Sharpe artmali)"""
    return [a for a, v in VARYANT.items()
            if v[2] > KONTROL["erken"] and v[3] > KONTROL["gec"]]


def oi_fundingin_gurultulu_esi():
    """OI tek basina funding kadar KAZANIYOR ama daha RISKLI mi?"""
    oi = VARYANT["yalniz OI yuksekligi (funding YOK)"]
    return (abs(oi[0] - KONTROL["yillik"]) < 2.0          # getiri neredeyse ayni
            and oi[1] < KONTROL["sharpe"] - 0.3           # ama Sharpe belirgin dusuk
            and oi[4] < KONTROL["dusus"])                 # ve dusus daha derin


def evren_sinirli_mi():
    """Olcum kitabin en zayif kismi uzerinde mi yapildi?"""
    return (EVREN_BEDELI["60 sembol + havuz kapali"][0]
            < EVREN_BEDELI["tam kitap (847 panel)"][0] / 2)


if __name__ == "__main__":
    print("MADDE 252 - ACIK POZISYON (open interest)\n")
    print("1) KAPSAM: %d sembol, %s -> %s"
          % (KAPSAM["sembol"], KAPSAM["bas"], KAPSAM["son"]))
    print("   uygun evren gunluk ort %.1f sembol, OI kapsanan %.1f  (%%%d)"
          % (KAPSAM["gunluk_ort_uygun"], KAPSAM["oi_kapsanan"], KAPSAM["oran"]))
    print("\n   AYNI SINYAL, IKI EVREN - daraltmanin bedeli:")
    for a, (y, s) in EVREN_BEDELI.items():
        print("     %-28s%+8.1f%%  Sharpe %.3f" % (a, y, s))
    print("   -> prim, OI verisi OLMAYAN kucuk/uc coinlerde yasiyor")
    print("   -> olcum kitabin en zayif kismi uzerinde: %s"
          % ("EVET" if evren_sinirli_mi() else "HAYIR"))

    print("\n2) UC VARYANT")
    print("  %-36s%8s%8s%8s%8s%8s%10s"
          % ("aday", "yillik", "Sharpe", "22-24", "25-26", "dusus", "esit-risk"))
    print("  %-36s%+8.1f%8.3f%8.3f%8.3f%8.1f%+10.1f"
          % ("ESLESMIS KONTROL", KONTROL["yillik"], KONTROL["sharpe"],
             KONTROL["erken"], KONTROL["gec"], KONTROL["dusus"], KONTROL["yillik"]))
    for a, v in VARYANT.items():
        print("  %-36s%+8.1f%8.3f%8.3f%8.3f%8.1f%+10.1f"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5]))
    print("\n  sart 1'i gecen: %s  (kirilan sart: %s)"
          % (ucu_de_red() or "YOK (3/3 RED)", KIRILAN_SART))
    print("  bootstrap (%s): ort %+.1f puan  std %.1f  P(>0) %%%.1f"
          % (BOOTSTRAP["aday"], BOOTSTRAP["ort"], BOOTSTRAP["std"],
             BOOTSTRAP["p_pozitif"]))

    print("\n3) ASIL DERS")
    print("  OI funding'in gurultulu esi mi? %s"
          % ("EVET" if oi_fundingin_gurultulu_esi() else "HAYIR"))
    print("  %s" % DERS)

    print("\n4) KAPSAM SINIRI")
    print("  Bu olcum 'OI tam evrende de ise yaramaz' DEMEZ.")
    print("  YENIDEN ACMA KOSULU: %s" % YENIDEN_ACMA_KOSULU)
