#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 293 — AYNA KİTAPLARIN ÇOK YÖNLÜ HARMANI: PROJENİN EN GÜÇLÜ
İSTATİSTİĞİ, VE ONU ERİŞİLEMEZ KILAN SERMAYE TABANI.

Madde 290 on kitabı TEK TEK ölçtü ve hepsi elendi. Ama ikisi birbirinin
aynasıydı: 2 günlük ufuk harman oynaklığını YUKARI itiyor (oynaklık
satın alır), yüksek-oynaklıklı SHORT ve saf akış seçici düşük
korelasyonla AŞAĞI çekiyor (oynaklık satar). **Birlikte hiç
denenmemişti.** Motor koşusu gerekmedi; günlük seriler elde.

125 ağırlık bileşimi doz ölçütünde tarandı (4 kitap × {0; %5; %10; %15},
toplam ağırlık ≤ %30). **48'i dört şartı da geçiyor.** En yüksek doz
kazançları (+25,43; +23,09; +21,69) yine **şart 4'ten** düşüyor — madde
289'un yasası ("çeşitlendiricide bağlayıcı şart şart 4'tür") üçüncü kez
doğrulandı.

═══ SEÇİM: ÖNCEDEN YAZILMIŞ KURAL, MAKSİMUM DEĞİL ═══

Kural (bakmadan önce yazıldı): geçen bileşimlerin AĞIRLIK ORTALAMASI,
%5 ızgarasına yuvarlanır, o nokta da geçmek zorundadır. Maksimumu
seçmek 125 bakışın en şanslı hücresini seçmek olurdu (madde 282/289).

Çıkan nokta **oynaklığa-ters %5 + akış %5 + 2g ufuk %10 + yüksek-oyn
SHORT %5** (kontrol %70... toplam dilim %25, kontrol %75) ve maksimumun
(+21,63) altında kalıyor — kuralın bedeli bu, ve ödendi.

═══ SONUÇ: HER HAM EKSENDE KONTROLDEN İYİ ═══

    ölçü               aday      kontrol
    CAGR            +%113,25     +%112,27
    tam Sharpe         3,016        2,939
    22-24 Sharpe       2,849        2,789   ✓
    25-26 Sharpe       3,247        3,147   ✓
    maks düşüş        −13,46       −14,54   ✓
    oynaklık          %26,26       %26,85
    doz ölçütü     **+13,69 puan**

`gecer_mi()` GEÇER. Karar veren sayı: doz ölçütünde eşli blok bootstrap
**P(>0) %96,0** · ort +15,17 · **p5 +0,66** · medyan +12,93 · p95 +36,52.
**p5'in ARTIDA olması projede ilk** — dağılımın alt %5'i bile kontrolü
geçiyor. Bahis fiyatı: 22-24 +10,85 **ve** 25-26 +19,30 → bahis DEĞİL.
İki faz bazında da aynı (faz0: +13,95, GEÇER). Plato: merkez çevresinde
8 komşunun 6'sı geçiyor, doz +8 ile +19,5 arası.

═══ VE ONU DURDURAN ŞEY: SERMAYE TABANI ═══

Bir dilim sermayenin %w'sini alıyorsa bacak büyüklüğü de %w'ye düşer.
Projenin kendi fonksiyonuyla (`bakiye_yeterli_mi`, bacak =
bakiye·w/187,5):

    ağırlık   teknik taban   tam beklenti (80$ bacak)
    %100        1.875 $            15.000 $
    %25         7.500 $            60.000 $
    %15        12.500 $           100.000 $
    %10        18.750 $           150.000 $
    %5         37.500 $           300.000 $

Seçilen adayın en küçük dilimi %5 → **teknik taban 37.500 $, tam
beklenti 300.000 $.** 15.000 $'da %5'lik dilimin bacakları 4 $ olur,
borsa minimumunun altında, madde 204 o dilimi HER TURDA ATLAR — yani
dilim **sessizce var olmaz** ve kullanıcı kontrolü sermayenin %75'iyle
çalıştırmış olur. Bu kontrolden **KÖTÜ**.

**YASA: dilim tabanlı çeşitlendirmenin sermaye tabanı 1/ağırlık ile
büyür.** %5'lik bir dilim, aynı bacak büyüklüğü için **20 kat** sermaye
ister. Proje madde 237'den beri çeşitlendirici arıyor ve bu maliyeti
hiç fiyatlamamıştı. Üstüne madde 176 küçük bacağın evreni elediğini ve
getiriyi düşürdüğünü ölçmüştü — yani dilimler mümkün olduğu sermayede
ölçülen +13,69 aynı kalmayabilir.

═══ KISITLI SEÇİM KURALI KENDİNİ ÇÜRÜTTÜ ═══

Uygulanabilirliği kurala çevirdim (en fazla 2 dilim, her ağırlık ≥%15 →
taban 12.500 $). Kısıtı sağlayan 10 bileşimin 4'ü geçiyor. Ama onların
**ağırlık ortalaması yine 4 dilimli ve %5'lik** bir nokta verdi: yani
kural, uygulanabilir noktaların ortalamasından UYGULANAMAZ bir nokta
üretiyor — **ortalama alma kısıt kümesinde kapalı değil.**

Kuralı sonuçları gördükten sonra değiştirmedim (madde 212'nin kapattığı
delik). Bunun yerine kısıtı geçen DÖRT adayın tamamını ölçüp kaydettim;
aralarındaki seçim, sonradan yazacağım bir kuralla benim değil.

═══ KISITI GEÇEN ADAYLAR (hepsi `gecer_mi()` GEÇER, hiçbiri bahis DEĞİL)

    aday                       doz      P      p5    CAGR   düşüş
    ufuk2g%15 + volyuk%15    +18,44  %88,5   −6,93  +115,96  −12,99
    akis%15 + ufuk2g%15      +12,18  %84,5  −11,05  +115,20  −13,23
    agvol%15 + ufuk2g%15      +8,04     —       —        —       —
    ufuk2g%15                 +4,08     —       —        —       —

İki dilimli sürüm daha BÜYÜK nokta tahmini (+18,44) ve daha SIĞ düşüş
(−12,99) veriyor ama **daha ZAYIF kanıt** (P %88,5 vs %96,0, p5 negatif)
— mantıklı: daha az dilim, daha az ortalama, daha çok yol bağımlılığı.
İki faz bazında da duruyor (faz0: +18,29, GEÇER).

═══ KENDİ ÜÇ HATAM ═══

**(1) HARMAN KODUNDA TİPO.** `for a, p in w.items()` yazmışım, `par`
yerine — `p` bir FLOAT oluyor ve `w[a]*p` her güne ağırlığın KARESİNİ
ekliyordu. Sonuç: Sharpe **34,7**, CAGR +%98.969. **Absürtlük hatayı
yakalattı.** YASA: inanılmayacak kadar iyi bir sonuç, piyasa bulgusu
olmadan önce bir KOD HATASIDIR.

**(2) ZAMANDA KARIŞTIRMA PLASEBOSU BU ADAY İÇİN GEÇERSİZ.** Karıştırma
dilimin kontrolle korelasyonunu yok eder; oysa adayın kazancının bir
kısmı tam olarak DÜŞÜK korelasyondan gelir. Ölçüldü: plasebo Sharpe
**3,877 > adayın 3,016** — plasebo adayı İYİLEŞTİRİYOR. **Bir plasebo,
sınadığı mekanizmayı GÜÇLENDİRİYORSA plasebo değildir.** Doğru null
eşli blok bootstrap'in kendisi: blok içi çapraz korelasyonu KORUR,
yolun kendisini rastgeleler.

**(3) DOZ ÇÖZÜCÜSÜ TAVANA DAYANABİLİYOR.** `coz` brütü [0,05; 6,0]
aralığında arar. Düşüşü SIĞ bir adayın yeniden örneklenmiş yolunda 1
yıl p95 düşüş 6,0x'te bile −%30'a ulaşmıyor; çözücü tavanı döner ve 4
yıllık bileşik getiri astronomik çıkar — **sahte bir P %100,0**. Böyle
bir yol ÖLÇÜLEMEMİŞTİR, "lehte" değil. Korumaya alındı: tavana dayanan
yollar dışlanır ve SAYILIR (madde 286'nın ayrımı). Nihai koşularda 0
yol dışlandı, yani koruma cevabı değiştirmedi — ama daha sığ bir adayda
değiştirirdi.

═══ MÜHENDİSLİK MALİYETİ ═══

Dilimler ayrı KİTAPLAR demek: farklı tutma süresi (2 gün), farklı SHORT
ölçütü (yüksek oynaklık), farklı seçici (saf akış), farklı ağırlıklama
(oynaklığa ters). Canlı bot şu an TEK kitap çalıştırıyor; iki-üç kitabı
paralel çalıştırmak bir knob değil ciddi bir inşa. Madde 292 tek bir
korumasız API çağrısının hasadın altıda birini sessizce götürebildiğini
gösterdi; üç kitap üç kat o yüzey demek.

**HÜKÜM: ayar DEĞİŞMEDİ.** Aday istatistiksel olarak projenin en
güçlüsü ama 15.000 $'da UYGULANAMAZ ve 100.000-300.000 $ ister. Karar,
hesap o büyüklüğe gelirse kullanıcının.
"""

# --- izgara -----------------------------------------------------------
BAKIS = 125
GECEN = 48
IZGARA_ADIM = (0.0, 0.05, 0.10, 0.15)
TOPLAM_AGIRLIK_UST = 0.30
EN_IYI_DOZ_SART4TEN_DUSEN = (25.43, 23.09, 21.69)
MAKSIMUM_GECEN = 21.63

# --- on kayitli secim kurali -----------------------------------------
SECIM_KURALI = ("gecen bilesimlerin AGIRLIK ORTALAMASI, %5 izgarasina "
                "yuvarlanir, o nokta da gecmek zorundadir - maksimumu "
                "secmek 125 bakisin en sansli hucresini secmek olurdu")
MERKEZ = {"agvol": 0.05, "akis": 0.05, "ufuk2g": 0.10, "volyuk": 0.05}

# --- merkezin olcumu: (aday, kontrol) --------------------------------
MERKEZ_OLCUM = {
    "CAGR": (113.25, 112.27),
    "Sharpe": (3.016, 2.939),
    "22-24": (2.849, 2.789),
    "25-26": (3.247, 3.147),
    "dusus": (-13.46, -14.54),
    "vol": (26.26, 26.85),
}
MERKEZ_DOZ = 13.69
MERKEZ_BOOTSTRAP = {"ort": 15.17, "p5": 0.66, "medyan": 12.93,
                    "p95": 36.52, "P": 96.0}
MERKEZ_BAHIS = {"22-24": 10.85, "25-26": 19.30}
MERKEZ_FAZ0_DOZ = 13.95
KANIT_BARI = 80.0
PLATO_GECEN = (6, 8)          # merkez cevresinde gecen / toplam komsu

# --- sermaye tabani ---------------------------------------------------
TEKNIK_TABAN_1X = 1875.0
TAM_BEKLENTI_1X = 15000.0
def taban(w: float) -> float:
    return TEKNIK_TABAN_1X / w
def tam_beklenti(w: float) -> float:
    return TAM_BEKLENTI_1X / w
SERMAYE_TABLOSU = {1.00: (1875, 15000), 0.25: (7500, 60000),
                   0.15: (12500, 100000), 0.10: (18750, 150000),
                   0.05: (37500, 300000)}
SERMAYE_YASASI = ("dilim tabanli cesitlendirmenin sermaye tabani "
                  "1/agirlik ile buyur: %5'lik bir dilim ayni bacak "
                  "buyuklugu icin 20 KAT sermaye ister")
MADDE_204_SONUCU = ("15.000 $'da %5'lik dilimin bacaklari 4 $ olur, borsa "
                    "minimumunun altinda, madde 204 o dilimi HER TURDA "
                    "ATLAR - dilim SESSIZCE var olmaz ve kullanici "
                    "kontrolu sermayenin %75'iyle calistirmis olur, yani "
                    "kontrolden KOTU")

# --- kisitli kural kendini curuttu -----------------------------------
KISIT = {"maks_dilim": 2, "min_agirlik": 0.15}
KISIT_SAGLAYAN = 10
KISIT_GECEN = 4
KISIT_KURALI_CIKTISI = {"agvol": 0.05, "akis": 0.05, "ufuk2g": 0.15,
                        "volyuk": 0.05}
KISIT_KURALI_CURUDU = ("uygulanabilir noktalarin ORTALAMASI 4 dilimli ve "
                       "%5'lik bir nokta verdi: ortalama alma kisit "
                       "kumesinde KAPALI DEGIL")
KURAL_SONRADAN_DEGISTIRILMEDI = True

# --- kisiti gecen adaylar: ad -> (doz, P, p5, CAGR, dusus) -----------
ADAYLAR = {
    "ufuk2g%15 + volyuk%15": (18.44, 88.5, -6.93, 115.96, -12.99),
    "akis%15 + ufuk2g%15": (12.18, 84.5, -11.05, 115.20, -13.23),
    "agvol%15 + ufuk2g%15": (8.04, None, None, None, None),
    "ufuk2g%15": (4.08, None, None, None, None),
}
IKI_DILIM_FAZ0_DOZ = 18.29

# --- uc hatam ---------------------------------------------------------
HATALARIM = {
    "harman tipo": ("for a, p in w.items() yazmisim, par yerine - p bir "
                    "FLOAT oluyor ve her gune agirligin KARESI ekleniyordu; "
                    "Sharpe 34,7 ve CAGR +%98.969 cikti",
                    "inanilmayacak kadar iyi bir sonuc, piyasa bulgusu "
                    "olmadan once bir KOD HATASIDIR"),
    "gecersiz plasebo": ("zamanda karistirma dilimin KORELASYONUNU yok "
                         "eder, oysa kazancin bir kismi tam olarak dusuk "
                         "korelasyondan gelir; olculdu: plasebo Sharpe "
                         "3,877 > adayin 3,016",
                         "bir plasebo, sinadigi mekanizmayi GUCLENDIRIYORSA "
                         "plasebo degildir"),
    "doz cozucusu tavani": ("dususu SIG bir adayin yeniden orneklenmis "
                            "yolunda 1 yil p95 dusus 6,0x'te bile -%30'a "
                            "ulasmiyor; cozucu tavani doner ve bilesik "
                            "getiri astronomik cikar - SAHTE P %100,0",
                            "tavana dayanan yol OLCULEMEMISTIR, 'lehte' "
                            "degil (madde 286'nin ayrimi)"),
}
PLASEBO_SHARPE = 3.877
TAVANDA_DISLANAN = 0

# --- muhendislik ------------------------------------------------------
MUHENDISLIK = ("dilimler ayri KITAPLAR demek (farkli tutma suresi, farkli "
               "SHORT olcutu, farkli secici, farkli agirliklama); canli bot "
               "su an TEK kitap calistiriyor ve madde 292 tek bir korumasiz "
               "API cagrisinin hasadin altida birini sessizce goturebildigini "
               "gosterdi - uc kitap uc kat o yuzey")
AYAR_DEGISTI = False


# --- sinamalar --------------------------------------------------------
def merkez_her_eksende_iyi_mi() -> bool:
    a = MERKEZ_OLCUM
    return (a["CAGR"][0] > a["CAGR"][1] and a["Sharpe"][0] > a["Sharpe"][1]
            and a["22-24"][0] > a["22-24"][1] and a["25-26"][0] > a["25-26"][1]
            and a["dusus"][0] > a["dusus"][1]        # daha SIG (negatif, buyuk)
            and a["vol"][0] < a["vol"][1])


def merkez_bari_gecti_mi() -> bool:
    return MERKEZ_BOOTSTRAP["P"] >= KANIT_BARI


def p5_artida_mi() -> bool:
    """Projede ilk: bootstrap dagiliminin alt %5'i de kontrolu geciyor."""
    return MERKEZ_BOOTSTRAP["p5"] > 0


def merkez_bahis_mi() -> bool:
    return not all(v > 0 for v in MERKEZ_BAHIS.values())


def merkez_maksimumun_altinda_mi() -> bool:
    """On kayitli kural bedelini odedi mi?"""
    return MERKEZ_DOZ < MAKSIMUM_GECEN


def en_iyiler_sart4ten_mi_dusuyor() -> bool:
    return all(d > MERKEZ_DOZ for d in EN_IYI_DOZ_SART4TEN_DUSEN)


def sermaye_tabani_dogru_mu() -> bool:
    return all(abs(taban(w) - t) < 1.0 and abs(tam_beklenti(w) - b) < 1.0
               for w, (t, b) in SERMAYE_TABLOSU.items())


def merkez_kac_kat_sermaye_istiyor() -> float:
    return 1.0 / min(MERKEZ.values())


def merkez_uygulanabilir_mi(bakiye: float = 15000.0) -> bool:
    return bakiye >= taban(min(MERKEZ.values()))


def kisit_kurali_curudu_mu() -> bool:
    """Kisitli kuralin ciktisi kisiti IHLAL ediyor mu?"""
    c = KISIT_KURALI_CIKTISI
    return (len(c) > KISIT["maks_dilim"]
            or any(v < KISIT["min_agirlik"] - 1e-9 for v in c.values()))


def kural_sonradan_degistirilmedi_mi() -> bool:
    return KURAL_SONRADAN_DEGISTIRILMEDI is True


def iki_dilim_daha_mi_uygulanabilir() -> bool:
    return taban(0.15) < taban(min(MERKEZ.values()))


def iki_dilim_kaniti_daha_mi_zayif() -> bool:
    d, p, p5, _, _ = ADAYLAR["ufuk2g%15 + volyuk%15"]
    return (d > MERKEZ_DOZ and p < MERKEZ_BOOTSTRAP["P"]
            and p5 < MERKEZ_BOOTSTRAP["p5"])


def plasebo_adayi_iyilestirdi_mi() -> bool:
    return PLASEBO_SHARPE > MERKEZ_OLCUM["Sharpe"][0]


def uc_hatam_kayitli_mi() -> bool:
    return len(HATALARIM) == 3 and all(len(v) == 2 for v in HATALARIM.values())


def ayar_degisti_mi() -> bool:
    return AYAR_DEGISTI


def hukum() -> str:
    return (
        "PROJENIN EN GUCLU ISTATISTIGI, VE ONU ERISILEMEZ KILAN SERMAYE "
        "TABANI. 125 agirlik bilesiminden 48'i dort sarti geciyor; on "
        "kayitli merkez kurali (maksimum DEGIL) %5+%5+%10+%5'lik bir "
        "harman veriyor ve bu aday HER HAM EKSENDE kontrolden iyi: CAGR "
        "+%113,25 vs +%112,27, Sharpe 3,016 vs 2,939, iki alt donemde de "
        "artis, dusus -13,46 vs -14,54, oynaklik DAHA DUSUK. Doz olcutu "
        "+13,69 puan, bootstrap **P %96,0** ve **p5 +0,66** (projede ILK "
        "kez alt %5 de kontrolu geciyor), bahis DEGIL, iki faz bazinda da "
        "ayni. AMA en kucuk dilim %5 oldugu icin teknik taban 37.500 $ ve "
        "tam beklenti 300.000 $: 15.000 $'da o dilimin bacaklari 4 $ olur, "
        "madde 204 dilimi her turda atlar ve kullanici kontrolu sermayenin "
        "%75'iyle calistirmis olur - kontrolden KOTU. YASA: dilim tabanli "
        "cesitlendirmenin sermaye tabani 1/agirlik ile buyur (%5 -> 20 kat "
        "sermaye); proje 237'den beri cesitlendirici ariyor ve bu maliyeti "
        "hic fiyatlamamisti. Uygulanabilir surum (iki dilim, %15+%15) "
        "+18,44 puan ve P %88,5 veriyor, taban 12.500 $ / tam 100.000 $. "
        "AYAR DEGISMEDI."
    )


def yaz() -> None:
    print(__doc__)
    print("IZGARA: %d bakis, %d gecen | en iyi dozlar SART 4'ten dusuyor: %s"
          % (BAKIS, GECEN, en_iyiler_sart4ten_mi_dusuyor()))
    print("SECIM KURALI: %s" % SECIM_KURALI)
    print("  merkez: %s | maksimumun (%.2f) altinda mi: %s"
          % ({a: "%.0f%%" % (v * 100) for a, v in MERKEZ.items()},
             MAKSIMUM_GECEN, merkez_maksimumun_altinda_mi()))
    print("\nMERKEZIN OLCUMU:")
    print("  %-14s %10s %10s" % ("olcu", "aday", "kontrol"))
    for ad, (x, y) in MERKEZ_OLCUM.items():
        print("  %-14s %10.3f %10.3f" % (ad, x, y))
    print("  doz olcutu **%+.2f puan** | her eksende iyi mi: %s"
          % (MERKEZ_DOZ, merkez_her_eksende_iyi_mi()))
    print("  BOOTSTRAP ort %+.2f | p5 %+.2f | medyan %+.2f | p95 %+.2f | "
          "**P %%%.1f**" % (MERKEZ_BOOTSTRAP["ort"], MERKEZ_BOOTSTRAP["p5"],
                            MERKEZ_BOOTSTRAP["medyan"], MERKEZ_BOOTSTRAP["p95"],
                            MERKEZ_BOOTSTRAP["P"]))
    print("  bar gecti mi: %s | p5 ARTIDA mi (projede ilk): %s | bahis mi: %s"
          % (merkez_bari_gecti_mi(), p5_artida_mi(), merkez_bahis_mi()))
    print("  faz0 dozu %+.2f | plato: %d/%d komsu geciyor"
          % (MERKEZ_FAZ0_DOZ, *PLATO_GECEN))
    print("\nSERMAYE TABANI (bacak = bakiye x agirlik / 187,5):")
    print("  %8s %14s %22s" % ("agirlik", "teknik taban", "tam beklenti (80$)"))
    for w in sorted(SERMAYE_TABLOSU, reverse=True):
        t, b = SERMAYE_TABLOSU[w]
        print("  %7.0f%% %14s %22s" % (w * 100, format(t, ","), format(b, ",")))
    print("  tablo dogru mu: %s" % sermaye_tabani_dogru_mu())
    print("  merkez %0.0f KAT sermaye istiyor | 15.000 $'da uygulanabilir mi: %s"
          % (merkez_kac_kat_sermaye_istiyor(), merkez_uygulanabilir_mi()))
    print("  %s" % MADDE_204_SONUCU)
    print("  YASA: %s" % SERMAYE_YASASI)
    print("\nKISITLI KURAL: en fazla %d dilim, her agirlik >= %%%.0f"
          % (KISIT["maks_dilim"], KISIT["min_agirlik"] * 100))
    print("  saglayan %d, gecen %d | kuralin ciktisi: %s"
          % (KISIT_SAGLAYAN, KISIT_GECEN,
             {a: "%.0f%%" % (v * 100) for a, v in KISIT_KURALI_CIKTISI.items()}))
    print("  KURAL CURUDU MU: %s -> %s" % (kisit_kurali_curudu_mu(),
                                           KISIT_KURALI_CURUDU))
    print("  kural sonradan DEGISTIRILMEDI mi: %s"
          % kural_sonradan_degistirilmedi_mi())
    print("\nKISITI GECEN ADAYLAR:")
    print("  %-24s %8s %7s %8s %9s %8s" % ("aday", "doz", "P", "p5", "CAGR",
                                           "dusus"))
    for ad, v in ADAYLAR.items():
        print("  %-24s %+8.2f %7s %8s %9s %8s"
              % (ad, v[0], "-" if v[1] is None else "%.1f" % v[1],
                 "-" if v[2] is None else "%+.2f" % v[2],
                 "-" if v[3] is None else "%+.2f" % v[3],
                 "-" if v[4] is None else "%.2f" % v[4]))
    print("  iki dilim daha uygulanabilir mi: %s | kaniti daha zayif mi: %s"
          % (iki_dilim_daha_mi_uygulanabilir(), iki_dilim_kaniti_daha_mi_zayif()))
    print("  iki dilim faz0 dozu: %+.2f" % IKI_DILIM_FAZ0_DOZ)
    print("\nUC HATAM (hepsi yayimlanmadan yakalandi: %s):" % uc_hatam_kayitli_mi())
    for ad, (ne, ders) in HATALARIM.items():
        print("  %s" % ad.upper())
        print("    ne  : %s" % ne)
        print("    ders: %s" % ders)
    print("  plasebo adayi IYILESTIRDI mi: %s (Sharpe %.3f)"
          % (plasebo_adayi_iyilestirdi_mi(), PLASEBO_SHARPE))
    print("  tavanda dislanan yol: %d (koruma cevabi degistirmedi, ama daha "
          "sig bir adayda degistirirdi)" % TAVANDA_DISLANAN)
    print("\nMUHENDISLIK: %s" % MUHENDISLIK)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
