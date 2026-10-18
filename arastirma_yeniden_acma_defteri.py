"""MADDE 240: YENIDEN ACMA DEFTERI - hangi parametre en son hangi maddede olculdu.

NEDEN VAR: madde 222 bir kural koydu - "bir parametre taranmis ve
optimumda ise, o taramadan BERI kabul edilen her degisiklik onu yeniden
acar". Madde 227 o kuralin uygulanmasinda bir delik buldu: **listenin
kendisi eksikti** ve eksik olan, kârin TAMAMINI tasiyan mekanizmaydi
(kâr al). O yuzden liste artik elle tutulmuyor: bu arac `carry_bot.py`
docstring'lerinden OKUYOR.

NASIL: modul duzeyindeki BUYUK HARF atamalarin hemen ardindaki
docstring'de anilan en buyuk madde numarasi = o parametrenin son
olculdugu tur. Docstring'i ya da madde atfi olmayan parametreler
AYRICA listelenir - cunku denetim disi kalan parametre, bayat
parametreden daha tehlikelidir (madde 217'nin dersi, belgeden koda
tasinmis hali).

MADDE 240'TA BU DEFTERIN BULDUGU: canli STRATEJI parametreleri icinde
madde atfi HIC OLMAYAN iki tane vardi - `REZERV_ESIK_YILLIK` ve
`REZERV_COIN_KAP`. Ikisi de sermaye dagitimini belirliyor ve ikisi de
projenin 240 turu boyunca bir kez taranip hic yeniden acilmamisti.
Madde 240 ikisini de taradi (ve `DONUK_ESIK`'i, son olcum madde 183).

DEFTERIN YAPISAL SINIRI (madde 240'ta bulundu): birlikte taranan
parametrelerde olcum genellikle TEK bir docstring'de durur, oteki
parametre BAYAT gorunur. Ornek: `KAR_AL_SHORT` madde 189 gorunuyordu,
oysa madde 227 onu `KAR_AL_ORAN` docstring'inde yeniden olcmustu.
Cozum: capraz atif - olculen parametrenin docstring'ine "madde N'de
yeniden acildi, tarama su docstring'de" satiri yazilir. Defter bayat
gosterdiginde ilk bakilacak yer budur; ikinci bakilacak yer gercekten
olculmemis olmasidir.

Kosum: python3 arastirma_yeniden_acma_defteri.py
"""
import ast
import re

DOSYA = "carry_bot.py"
MADDE = re.compile(r"(?:madde|MADDE|Madde)\s+(\d{2,3})")

# operasyonel/altyapi: strateji yuzeyini degistirmeyen parametreler
ALTYAPI = {
    "MAX_SYMBOLS", "MIN_NOTIONAL_USD", "MIN_BACAK_USD", "DOLUM_DENEME",
    "AKIS_KISA_BAR", "AKIS_UZUN_BAR", "_PROFILLER", "DILIM_DURUM_DOSYA",
    "VOL_GECMIS_DOSYA", "VOL_MIN_KAYIT", "SAGLIK_DOSYA", "SAGLIK_GOLGE_BACAK",
    "_TRADFI_TIPLERI", "_TRADFI_YEDEK", "BEKLENEN_TP_LONG", "TP_DEFTER_DOSYA",
    # raporlama/muhasebe sabitleri: secimi, boyutu, cikisi degistirmezler
    "BEKLENEN_TP_SHORT", "DEVIR_YILLIK", "PUAN_BASINA_BP",
    # operasyonel guvenlik: pozisyon modu, kurtarma, izole/cross denetimi
    "DURUM_KURTAR", "IZOLE_KAPAT", "IZOLE_OLCUM", "POZ_MODU_KONTROL",
}


# Madde 222'nin kuralindan ONCE olculmus olmasi SORUN OLMAYAN
# parametreler ve sebebi. Buradaki her giris bir OLCUMU isaret eder;
# "sanirim onemsiz" gerekcesi kabul edilmez.
KAPALI_EKSEN = {
    "LIMIT_EMIR": "icra ekseni - madde 213: TOPLAM butce 3,3 puan, tabandan 0,12 puan uzakta",
    "LIMIT_OFSET": "icra ekseni - madde 213",
    "GTX_DENEME_CARPANLARI": "icra ekseni - madde 213",
    "DOLUM_BEKLEME_SN": "icra ekseni - madde 213",
    "ISLEM_TOLERANSI": "madde 124 + 183.2 + MADDE 247 (guncel yuzeyde yeniden): canli %50 notr - getiri +112,6 vs +112,5, Sharpe 2,944 vs 2,942",
    "OTOMATIK_BACAK": "bacak sayisi madde 230'da (N_LEGS) olculdu",
    "MIN_LEGS": "bacak sayisi madde 230'da (N_LEGS) olculdu",
    "SAGLIK_MODU": "izleme katmani - madde 234'te kapi yeniden kuruldu",
    "RISK_PROFILI": "degisken kaldirac ailesi - madde 165: ayni ortalamada sabitten 14-24 puan kotu",
    "VOL_HEDEF": "degisken kaldirac ailesi - madde 165",
    "VOL_PENCERE": "yalnizca TPKAT'i besler; TPKAT madde 221'de reddedildi (kapali)",
    "TEMINAT_MODU": "BFUSD ekseni - madde 141: +0,2 puan",
    "TRADFI_HARIC": "evren kurali - madde 142; funding mekanizmasi yapisal olarak farkli",
    "SOLMA_ORAN": "funding-solma cikisi - madde 167/191: aile KAPANDI",
    "LEVERAGE": "madde 227'nin BEKLEYEN kaldirac karari (canli olcum oncesi verilmemeli)",
    "DELIST_UFUK_GUN": "madde 183.2 + MADDE 247 (guncel yuzeyde yeniden): canli 30 gunluk ufuk MALIYET DEGIL, hafif fayda (+113,0 vs +112,5; Sh 2,949 vs 2,942)",
    "PIYASA_YEDEK": "icra ekseni (emir tipi yedegi) - madde 160/213",
    "ASGARI_BACAK_CARPANI": "madde 204: asgari bakiye kurali - maruziyeti degil UYGULANABILIRLIGI belirler",
    "DILIM_OLCEK_TAVAN": "madde 205: dilim olcek guvenlik rayi; ust sinir -9,9 puan olarak OLCULDU",
}


# MADDE 251'DE BULUNAN DELIK: bu defter yalnizca `carry_bot.py`'deki BUYUK
# HARF atamalarini okuyor - yani ADI OLAN parametreleri. Ama kitabin bazi
# kararlari KODA GOMULU yapisal secimlerdir; adi olmadigi icin defter
# onlari hic gormez. Madde 251 boyle bir tanesini buldu: bacak AGIRLIGI
# (esit para) `g33.py`'de `y[lo]=taban/len(lo)` olarak gomuluydu, madde
# 116'da (madde 182'nin 41 puanlik sizintisi duzeltilmeden ONCE) olculmus
# ve bir daha hic acilmamisti.
#
# Kural: bir yapisal secim buraya girer ve GEREKCESI bir OLCUME isaret
# eder. "Varsayilan boyle" gerekce DEGILDIR.
YAPISAL_SECIM = {
    "bacak agirligi (esit para)":
        "MADDE 251: risk paritesi cephesi - 7/7 sart 1'i GECTI ama 7/7 sart "
        "3'ten dustu; esit riskte +79,0...+110,2, kontrol +112,3. Bootstrap: "
        "Sharpe +0,071 P%75,2 ama esit-risk -2,8 puan P%39,3",
    "taraf notrlugu (yarim/yarim)":
        "madde 158: beta ~0 olculdu; madde 230: asimetrik bacak sayisi 37 "
        "yapilandirmada reddedildi",
    "kesitsel secim (siralama)":
        "madde 118: zaman serisi momentum ve bes alternatif yapi elendi; "
        "madde 244: alti alternatif secici",
    "esit dilim buyuklugu (15 dilim)":
        "madde 199: dilimleme ekseninin sonu - 15'te doygunluk, tutma "
        "karisimi ise yaramiyor",
}


def yapisal_denetim():
    """Gerekcesi bir OLCUME isaret etmeyen yapisal secim var mi?"""
    import re
    return sorted(a for a, g in YAPISAL_SECIM.items()
                  if not re.search(r"madde\s*\d{2,3}", g, re.I))


def denetim(yol=DOSYA, sinir=222):
    """Madde `sinir`'dan once olculmus ve gerekcesi OLMAYAN parametreler.

    Bos liste donerse: canli strateji yuzeyinde, madde 222'nin
    kuralindan once olculmus ve hesabi verilmemis parametre KALMADI.
    """
    son, atifsiz = defter(yol)
    acik = [a for a, m in son.items()
            if m < sinir and a not in ALTYAPI and a not in KAPALI_EKSEN]
    acik += [a for a in atifsiz if a not in ALTYAPI and a not in KAPALI_EKSEN]
    return sorted(acik)


def defter(yol=DOSYA):
    """{parametre: son madde numarasi} ve atfi olmayanlarin listesi."""
    govde = ast.parse(open(yol, encoding="utf-8").read()).body
    son, atifsiz = {}, []
    for i, n in enumerate(govde):
        if not (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id.isupper()):
            continue
        ad = n.targets[0].id
        doc = None
        if (i + 1 < len(govde) and isinstance(govde[i + 1], ast.Expr)
                and isinstance(govde[i + 1].value, ast.Constant)
                and isinstance(govde[i + 1].value.value, str)):
            doc = govde[i + 1].value.value
        m = sorted({int(x) for x in MADDE.findall(doc)}) if doc else []
        if m:
            son[ad] = m[-1]
        else:
            atifsiz.append(ad)
    return son, atifsiz


if __name__ == "__main__":
    son, atifsiz = defter()
    print("YENIDEN ACMA DEFTERI (%d parametre okundu)\n" % (len(son) + len(atifsiz)))
    print("son olcum maddesine gore:")
    for ad, m in sorted(son.items(), key=lambda t: t[1]):
        isaret = "  <- ESKI" if m <= 200 and ad not in ALTYAPI else ""
        print("  %-26s%6d%s" % (ad, m, isaret))
    kritik = [a for a in atifsiz if a not in ALTYAPI]
    print("\nMADDE ATFI OLMAYAN (denetim disi):")
    for ad in atifsiz:
        print("  %-26s%s" % (ad, "" if ad in ALTYAPI else "  <- STRATEJI, ATIFSIZ"))
    print("\nstrateji yuzeyinde atifsiz kalan: %d" % len(kritik))
    print("\nYAPISAL SECIMLER (madde 251: defterin gormedigi kategori):")
    for ad, g in YAPISAL_SECIM.items():
        print("  %-32s%s" % (ad, g[:70]))
    eksik = yapisal_denetim()
    print("  gerekcesi OLCUME dayanmayan yapisal secim: %s" % (eksik or "YOK"))
    acik = denetim()
    print("\nDENETIM - madde 222'nin kuralindan once olculmus ve "
          "GEREKCESI OLMAYAN parametre:")
    if acik:
        for ad in acik:
            print("  %-26s  <- YENIDEN ACILMALI" % ad)
    else:
        print("  YOK. Canli strateji yuzeyinin tamami madde 222'nin "
              "kuralindan sonra olculdu")
        print("  ya da kapali bir eksende (gerekceler KAPALI_EKSEN'de, "
              "her biri bir OLCUME isaret eder).")
