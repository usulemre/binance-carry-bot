#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 290 — 289'UN ŞARTNAMESİ ARAMA OLARAK UYGULANDI; VE MADDE 214'ÜN
EN ÇOK ATIF ALAN YASASI BİR MUHASEBE ARTEFAKTI ÇIKTI.

Madde 289 ölçmüştü: bu kural, kendi Sharpe'ı kitabın Sharpe'ından düşük
hiçbir çeşitlendiriciyi kabul edemez; eşik ~2,8-2,94 ve negatif
korelasyon hiçbir şey kazandırmıyor. Ama o tablo SENTETİK Gauss
kitaplarıyla çıkarılmıştı. Madde 290 şartnameyi gerçek motora uyguladı:
her kitabı TEK BAŞINA ölç, kontrolle korelasyonunu çıkar, sonra %10
ağırlıkla harmanla ve dört şarta + doz ölçütüne ver.

Sicilde kitaplar hep HARMAN olarak ölçülmüş; tek başına Sharpe'ı ve ρ'su
hiç bir arada raporlanmamıştı.

═══ BULGU 1 — HİÇBİR KİTAP ŞARTNAMEYİ TUTMUYOR ═══

Kârlı her kitabın kontrolle korelasyonu **+0,635'in üstünde**. Şartname
ρ <= 0 istiyordu; proje o eksende BOŞ. Ve madde 288'in kabul edilen
adayının ρ'su **+0,997** — yani o bir çeşitlendirme değil, kitabın
kendisinin %0,5 yeniden ölçeklenmişi. Bunu artık ölçülmüş olarak
biliyoruz.

═══ BULGU 2 — MADDE 289'UN YASASININ GERÇEK KARŞILIĞI BULUNDU ═══

En düşük korelasyonlu kârlı kitap (yüksek oynaklıklı SHORT seçimi,
tek başına Sharpe 2,448, ρ **+0,635**), %10 ağırlıkla:

    22-24 +0,066 ✓ · 25-26 +0,039 ✓ · düşüş −0,28 ✓ · eşit-risk +1,9 ✓
    doz ölçütü **+11,19 puan**, eşli blok bootstrap **P(>0) %91,5**
    bahis DEĞİL: 22-24 +11,18 **ve** 25-26 +14,29
    düşüş iyileşmesi bootstrap'ta da duruyor: P %76,1
    -> ve **ŞART 4'TEN DÜŞÜYOR** (kaldıraç 1,02x)

Madde 289 bunu sentetik kitaplarla göstermişti; madde 290 onu projenin
kendi motorunda buldu. Kullanıcının bekleyen çelişkisinin (şart 4 vs
madde 276'nın −%30 toleransı) artık gerçek bir adayı ve fiyatı var:
**+11,19 puan, P %91,5.**

═══ BULGU 3 — KURALIN HÜKMÜ, KANITLA TERS KORELASYONLU ═══

İki gerçek aday, %10 ağırlıkla:

    aday                 doz farkı   bootstrap P   KURAL
    yüksek-oynaklık SHORT   +11,19       %91,5     DÜŞER (şart 4)
    saf akış seçici          +6,56          -      düşer
    2 günlük ufuk            +3,36       **%68,0** **GEÇER**

Kuralı geçen aday, EN KÜÇÜK etkiye ve EN ZAYIF kanıta sahip olan.
(2 günlük ufuk = madde 239(A)'nın vade merdiveni; 239 %33 ağırlıkta
P %59,7 ölçmüştü, %10'da %68,0 — tutarlı.) Madde 288'in üçüncü yasası
("dört şartı da geçti bir ELEME cümlesidir") burada gerçek adaylarla
gösterilmiş oluyor.

═══ BULGU 4 — SABİT BRÜTTE BAKMAK SIRALAMAYI TERSİNE ÇEVİRİYOR ═══

İki aday birbirinin aynası:

    aday                 kitap vol   harman vol   (kontrol %26,85)
    2 günlük ufuk          %34,53      %27,25     -> oynaklık SATIN ALIR
    yüksek-oynaklık SHORT  %29,27      %26,12     -> oynaklık SATAR

Sabit 1,25x'te (kullanıcının kabul ettiği doz), 3.000 örnekli eşli blok
bootstrap:

    aday                  CAGR farkı   P(>0)    düşüş farkı   P(iyileşir)
    2 günlük ufuk           +5,25      %99,2       +0,19         %32,9
    yüksek-oynaklık SHORT   −2,08      %28,5       −0,55         %76,1

Sabit brüt, oynaklık satın alan adayı **ödüllendiriyor** (+5,25 puan,
P %99,2) ve oynaklık satan adayı **cezalandırıyor** (−2,08). Oysa doz
ölçütü tam tersini söylüyor (+3,36 / P %68,0 vs +11,19 / P %91,5).
Çünkü sabit brütte getiri farkı RİSKLE satın alınabilir; doz ölçütü
riski eşitleyip o satın almayı iptal ediyor. Madde 281 doz ölçütünü son
kapı ilan etmişti; madde 290 bunun NEDENİNİ iki gerçek ayna adayla
gösteriyor. (İlk yazımımda sabit-brüt çerçevesini kullanacaktım; harman
oynaklığını kontrol edince yakaladım.)

═══ BULGU 5 — MADDE 214 DÜZELTİLDİ: "KÂRIN TAMAMI HASATTAN" BİR
MUHASEBE ARTEFAKTI ═══

Madde 214 projenin en çok atıf alan yasalarından biri: "funding
SEÇİCİdir, gelir değil; funding ve ham fiyat birbirini götürür; kârın
tamamı kâr-al hasadından gelir." Kontrolün bileşen muhasebesi bunu
destekliyor: funding +116,8 · ham fiyat **−98,7** · hasat **+221,6**
(toplam +239,7 puan/yıl).

Hasadı GERÇEKTEN kapattım (`TP=0 TPL=0 TPS=0`; logda "SHORT kar-al
fiyat +0.0 · LONG kar-al fiyat +0.0" ile doğrulandı):

    kitap            CAGR     Sharpe   düşüş   funding   ham fiyat   hasat
    kontrol        +%112,3     3,10    −14,5    +116,8     **−98,7**  +221,6
    HASATSIZ        +%93,4     2,33    −20,6    +150,8     **+64,9**     0,0

**Hasat kapalıyken aynı fiyat maruziyeti +64,9 puan KAZANDIRIYOR.**
Mekanizma: kâr-al, lehte hareket eden pozisyonları erken çıkarıp
"kar-al fiyat" kovasına yazıyor; 5 günlük normal çıkışa SADECE aleyhte
olanlar kalıyor. Yani "bacak fiyat" kovasının −98,7'si bir SEÇİLİM
sonucu, ekonomik bir maliyet değil.

DOĞRU OKUMA: kitap funding'DEN **ve** fiyattan kazanıyor; kâr-al hasadı
çıkışları yeniden zamanlıyor ve bunun üstüne **+18,9 CAGR puanı, +0,77
Sharpe, −6,1 puan düşüş** ekliyor. "Kârın tamamı hasattan" cümlesi
yanlış; hasat kârın %17'sini ve Sharpe'ın dörtte birini ekliyor.

Madde 214'ün SEÇİCİ kısmı ayakta: funding bir seçicidir. Götürme
(cancellation) kısmı bir muhasebe konvansiyonunun sonucudur.

═══ BULGU 6 — SHORT SEÇİCİSİNİN DEĞERİ ═══

SHORT tarafı funding yerine RASTGELE seçilince (LONG hâlâ funding
sıralı): +%83,2 / Sharpe 2,612 / düşüş −13,50. Yani SHORT tarafındaki
funding sıralaması **+29,1 CAGR puanı ve +0,33 Sharpe** değerinde.
(Düşüşü ise rastgele seçim İYİLEŞTİRİYOR: −13,50 vs −14,54.)

═══ BENİM ÜÇ ETİKETLEME HATAM ═══

Bu turda üç knobu yanlış etiketledim; üçü de yayımlanmadan yakalandı:

1. `SSEC` kitabın seçicisini değiştirmiyor, **yalnız SHORT tarafını**
   değiştiriyor (kod satır 295-307; LONG hâlâ funding sıralı). Kodu
   okumadan yazsam manşet "rastgele seçim Sharpe 2,61 veriyor" olurdu —
   kitabın tamamı hakkında YANLIŞ bir iddia.
2. `TERS=1` ters/işareti çevrilmiş kitap DEĞİL; kâr-al dolduktan sonra
   **ters yönde yeniden giriş** kuralı. ρ≈−1 çapası elde edilmedi.
3. İlk "hasatsız" koşumda `TP=0` verdim ama taban ortamda `TPL=0.40
   TPS=0.20` duruyordu, yani bacak kâr-alları AÇIK kaldı. Gerçek
   hasatsız kitap `TPL=0 TPS=0` ile alındı ve bileşen muhasebesiyle
   doğrulandı.

**YASA: bir knobu 0'a çekmek kapandığını KANITLAMAZ (0 çoğu zaman ayrı
bir rejimdir), ve bir knobun ADINDAN ne yaptığını çıkarma — kodu oku ve
kapanmayı ÇIKTIDAN doğrula.** Madde 286'nın ailesi: ölçüm aracının
kendisi denetlenmeli.
"""

SART_SHARPE, SART_RHO = 2.5, 0.0

# --- tarama: kitap -> (CAGR, Sharpe, dusus, vol, rho) ---------------
TARAMA = {
    "kontrol (carry)": (112.27, 2.939, 14.54, 26.85, 1.000),
    "prim-brut e0,10 (madde 288)": (117.71, 2.988, 14.27, 27.30, 0.997),
    "prim-brut e1,0": (138.69, 3.078, 13.55, 29.72, 0.936),
    "rastgele SHORT": (83.16, 2.612, 13.50, 24.30, 0.943),
    "oynakliga ters agirlik": (87.27, 2.965, 15.65, 21.99, 0.937),
    "2 gunluk ufuk": (148.35, 2.809, 16.94, 34.53, 0.877),
    "dusuk oynaklikli SHORT": (56.64, 1.819, 20.10, 26.61, 0.863),
    "saf akis secici": (93.47, 2.536, 15.07, 27.53, 0.763),
    "BTC SHORT": (40.74, 1.378, 17.72, 27.52, 0.730),
    "yuksek oynaklikli SHORT": (96.08, 2.448, 15.35, 29.27, 0.635),
}
EN_DUSUK_RHO = 0.635

# --- %10 harman: kitap -> (22-24, 25-26, dusus, es-risk, kald, doz, kural)
HARMAN = {
    "yuksek oynaklikli SHORT": (+0.066, +0.039, -0.28, +1.9, 1.02, 11.19, False),
    "saf akis secici": (-0.005, +0.061, -0.48, +3.7, 1.04, 6.56, False),
    "2 gunluk ufuk": (+0.019, +0.031, -0.75, +12.6, 1.06, 3.36, True),
    "oynakliga ters agirlik": (+0.012, +0.021, +0.11, -3.7, 0.99, 2.50, False),
    "rastgele SHORT": (-0.001, -0.035, -0.12, -1.8, 1.01, -2.54, False),
    "dusuk oynaklikli SHORT": (-0.053, -0.106, +0.16, -7.8, 0.99, -12.21, False),
    "BTC SHORT": (-0.068, -0.114, -0.49, -3.2, 1.04, -13.81, False),
}
AGIRLIK = 0.10

# --- doz olcutu bootstrap: kitap -> (ort, P>0) ----------------------
DOZ_BOOTSTRAP = {
    "yuksek oynaklikli SHORT": (12.07, 91.5),
    "2 gunluk ufuk": (2.65, 68.0),
}
KANIT_BARI = 80.0
MADDE_239A_P = 59.7          # ayni yapi %33 agirlikta

# --- bahis fiyati ---------------------------------------------------
BAHIS = {"yuksek oynaklikli SHORT": (11.18, 14.29),
         "2 gunluk ufuk": (3.08, 2.07)}

# --- ayna teshisi: oynaklik satin alan vs satan --------------------
VOL = {   # kitap -> (kitap vol, harman vol)
    "2 gunluk ufuk": (34.53, 27.25),
    "yuksek oynaklikli SHORT": (29.27, 26.12),
    "saf akis secici": (27.53, 26.33),
}
KONTROL_VOL = 26.85
SABIT_BRUT = 1.25
SABIT_BOOTSTRAP = {   # kitap -> (CAGR farki, P>0, dusus farki, P iyilesir)
    "2 gunluk ufuk": (5.25, 99.2, +0.19, 32.9),
    "yuksek oynaklikli SHORT": (-2.08, 28.5, -0.55, 76.1),
}

# --- madde 214'un duzeltmesi ---------------------------------------
BILESEN = {   # kitap -> (funding, ham fiyat, hasat, toplam puan/yil)
    "kontrol": (116.8, -98.7, 221.6, 239.7),
    "HASATSIZ": (150.8, 64.9, 0.0, 215.7),
}
HASAT_ETKISI = {"cagr": 18.9, "sharpe": 0.77, "dusus": -6.1}
HASATSIZ = (93.4, 2.33, 20.6)
KONTROL = (112.3, 3.10, 14.5)
MADDE_214_IDDIASI = ("funding ve ham fiyat birbirini goturur; karin "
                     "TAMAMI kar-al hasadindan gelir")
MADDE_214_DUZELTME = ("gotrume bir MUHASEBE ARTEFAKTI: kar-al lehte "
                      "hareketleri erken cikarip kendi kovasina yaziyor, "
                      "5 gunluk cikisa SADECE aleyhte olanlar kaliyor; "
                      "hasat kapaliyken ayni fiyat maruziyeti +64,9 puan "
                      "KAZANDIRIYOR. Hasat karin %17'sini ve Sharpe'in "
                      "dortte birini ekliyor, tamamini degil")
MADDE_214_AYAKTA = "funding bir SECICIdir (iddianin ilk yarisi dogru)"

# --- short secicisinin degeri --------------------------------------
SHORT_SECICI = {"cagr": 29.1, "sharpe": 0.33, "dusus_rastgele_daha_iyi": True}

# --- benim etiketleme hatalarim ------------------------------------
ETIKET_HATALARIM = {
    "SSEC": "kitabin secicisini degil YALNIZ SHORT tarafini degistiriyor "
            "(LONG hala funding sirali) - kodu okumadan yazsam mansetim "
            "'rastgele secim Sharpe 2,61 veriyor' olurdu, kitabin tamami "
            "hakkinda YANLIS bir iddia",
    "TERS=1": "isareti cevrilmis kitap DEGIL; kar-al dolduktan sonra ters "
              "yonde YENIDEN GIRIS kurali - rho~-1 capasi elde edilmedi",
    "TP=0": "ilk kosumda taban ortamda TPL=0.40 TPS=0.20 duruyordu, yani "
            "bacak kar-allari ACIK kaldi; gercek hasatsiz kitap TPL=0 "
            "TPS=0 ile alindi ve BILESEN MUHASEBESIYLE dogrulandi",
}
ETIKET_YASASI = ("bir knobu 0'a cekmek kapandigini KANITLAMAZ (0 cogu "
                 "zaman ayri bir rejimdir), ve bir knobun ADINDAN ne "
                 "yaptigini cikarma - kodu oku, kapanmayi CIKTIDAN dogrula")
UCU_DE_YAYIMLANMADAN_YAKALANDI = True


# --- sinamalar ------------------------------------------------------
def sartnameyi_tutan_var_mi() -> bool:
    return any(sh >= SART_SHARPE and rho <= SART_RHO
               for _, sh, _, _, rho in TARAMA.values())


def en_dusuk_rho_karli_kitap() -> float:
    return min(rho for _, sh, _, _, rho in TARAMA.values() if sh >= 2.0)


def madde288_adayi_cesitlendirme_mi(esik: float = 0.9) -> bool:
    """rho 0,997 ise o bir cesitlendirme DEGIL, yeniden olceklemedir."""
    return TARAMA["prim-brut e0,10 (madde 288)"][4] < esik


def en_guclu_aday_sart4ten_mi_dusuyor() -> bool:
    """En yuksek doz farkli aday kurali geciyor mu? (Hayir - sart 4.)"""
    ad = max(HARMAN, key=lambda a: HARMAN[a][5])
    v = HARMAN[ad]
    return (v[6] is False and v[0] > 0 and v[1] > 0 and v[2] < 0
            and v[3] > 0 and v[4] > 1.005)


def kural_hukmu_kanitla_ters_mi() -> bool:
    """Kurali GECEN adayin dozu, DUSEN en iyi adaydan kucuk mu?"""
    gecen = [a for a in HARMAN if HARMAN[a][6]]
    dusen = [a for a in HARMAN if not HARMAN[a][6]]
    return (max(HARMAN[a][5] for a in gecen)
            < max(HARMAN[a][5] for a in dusen))


def gecen_aday_bari_gecemiyor_mu() -> bool:
    return DOZ_BOOTSTRAP["2 gunluk ufuk"][1] < KANIT_BARI


def dusen_aday_bari_geciyor_mu() -> bool:
    return DOZ_BOOTSTRAP["yuksek oynaklikli SHORT"][1] >= KANIT_BARI


def bahis_mi(ad: str) -> bool:
    return not all(v > 0 for v in BAHIS[ad])


def oynaklik_satin_alan_hangisi() -> str:
    return max(VOL, key=lambda a: VOL[a][1])


def sabit_brut_siralamayi_ters_mi_ceviriyor() -> bool:
    """Sabit brut ve doz olcutu iki adayi TERS siraliyor mu?"""
    a, b = "2 gunluk ufuk", "yuksek oynaklikli SHORT"
    return ((SABIT_BOOTSTRAP[a][0] > SABIT_BOOTSTRAP[b][0])
            and (HARMAN[a][5] < HARMAN[b][5]))


def hasat_karin_tamami_mi() -> bool:
    """Madde 214'un iddiasi: hasat kapaliyken kar sifira mi iniyor?"""
    return HASATSIZ[0] < 0.25 * KONTROL[0]


def hasatsizda_fiyat_kazandiriyor_mu() -> bool:
    return BILESEN["HASATSIZ"][1] > 0 and BILESEN["kontrol"][1] < 0


def hasadin_payi() -> float:
    """Hasat, kontrolun CAGR'inin yuzde kacini ekliyor?"""
    return 100.0 * HASAT_ETKISI["cagr"] / KONTROL[0]


def etiket_hatalari_yayimlanmadi_mi() -> bool:
    return UCU_DE_YAYIMLANMADAN_YAKALANDI is True


def hukum() -> str:
    return (
        "SARTNAME BOS CIKTI: karli her kitabin kontrolle korelasyonu "
        "+0,635'in ustunde, madde 288'in kabul edilen adayinin rho'su "
        "+0,997 (cesitlendirme degil, yeniden olcekleme). AMA madde "
        "289'un yasasinin GERCEK karsiligi bulundu: yuksek oynaklikli "
        "SHORT secimi %10 agirlikta doz olcutunde +11,19 puan / P %91,5 "
        "veriyor, iki rejimde de kazaniyor, dususu iyilestiriyor ve "
        "YALNIZ SART 4'TEN dusuyor (1,02x) - kullanicinin bekleyen "
        "celiskisinin artik gercek bir adayi ve fiyati var. Kuralin "
        "hukmu KANITLA TERS korelasyonlu: kurali GECEN aday (2 gunluk "
        "ufuk) en kucuk etkiye (+3,36) ve en zayif kanita (P %68,0) "
        "sahip. Ve madde 214 DUZELTILDI: hasat gercekten kapatilinca "
        "kitap +%93,4 / Sharpe 2,33 kazaniyor ve ayni fiyat maruziyeti "
        "+64,9 puan VERIYOR - 'funding ve fiyat goturur, karin tamami "
        "hasattan' bir MUHASEBE ARTEFAKTIdir; hasat karin %17'sini ve "
        "Sharpe'in dortte birini ekler. Ayar DEGISMEDI."
    )


def yaz() -> None:
    print(__doc__)
    print("TARAMA (sartname: tek basina Sharpe >= %.1f VE rho <= %.1f):"
          % (SART_SHARPE, SART_RHO))
    print("  %-30s %8s %8s %8s %7s %8s"
          % ("kitap", "CAGR%", "Sharpe", "dusus", "vol%", "rho"))
    for ad, (y, sh, du, vol, rho) in sorted(TARAMA.items(),
                                            key=lambda kv: -kv[1][4]):
        print("  %-30s %8.2f %8.3f %8.2f %7.2f %+8.3f" % (ad, y, sh, du, vol, rho))
    print("  sartnameyi tutan var mi: %s | en dusuk rho (karli): %+.3f"
          % (sartnameyi_tutan_var_mi(), en_dusuk_rho_karli_kitap()))
    print("  madde 288'in adayi CESITLENDIRME mi: %s (rho %+.3f)"
          % (madde288_adayi_cesitlendirme_mi(),
             TARAMA["prim-brut e0,10 (madde 288)"][4]))
    print("\n%%%.0f HARMAN:" % (AGIRLIK * 100))
    print("  %-26s %8s %8s %7s %8s %6s %9s %s"
          % ("kitap", "22-24", "25-26", "dusus", "es-risk", "kald", "doz", "KURAL"))
    for ad, v in sorted(HARMAN.items(), key=lambda kv: -kv[1][5]):
        print("  %-26s %+8.3f %+8.3f %+7.2f %+8.1f %6.2f %+9.2f %s"
              % (ad, v[0], v[1], v[2], v[3], v[4], v[5],
                 "**GECER**" if v[6] else "duser"))
    print("  en guclu aday SART 4'ten mi dusuyor: %s"
          % en_guclu_aday_sart4ten_mi_dusuyor())
    print("  kuralin hukmu KANITLA TERS mi: %s" % kural_hukmu_kanitla_ters_mi())
    print("\nDOZ OLCUTU BOOTSTRAP (bar %%%.0f):" % KANIT_BARI)
    for ad, (o, p) in DOZ_BOOTSTRAP.items():
        print("  %-26s ort %+6.2f  P(>0) %%%.1f  %s"
              % (ad, o, p, "GECER" if p >= KANIT_BARI else "BARIN ALTINDA"))
    print("  madde 239(A) ayni yapiyi %%33'te P %%%.1f olcmustu" % MADDE_239A_P)
    print("\nBAHIS FIYATI:")
    for ad, (a, b) in BAHIS.items():
        print("  %-26s 22-24 %+6.2f | 25-26 %+6.2f -> bahis mi: %s"
              % (ad, a, b, bahis_mi(ad)))
    print("\nAYNA TESHISI (kontrol vol %%%.2f):" % KONTROL_VOL)
    for ad, (kv, hv) in VOL.items():
        print("  %-26s kitap %%%.2f -> harman %%%.2f  (%s)"
              % (ad, kv, hv, "oynaklik SATIN ALIR" if hv > KONTROL_VOL
                 else "oynaklik SATAR"))
    print("  SABIT %.2fx bootstrap (3.000 ornek):" % SABIT_BRUT)
    print("    %-26s %10s %8s %11s %9s"
          % ("kitap", "CAGR fark", "P(>0)", "dusus fark", "P(iyilesir)"))
    for ad, (dy, p1, du, p2) in SABIT_BOOTSTRAP.items():
        print("    %-26s %+10.2f %7.1f%% %+11.2f %8.1f%%" % (ad, dy, p1, du, p2))
    print("  sabit brut siralamayi TERS mi ceviriyor: %s"
          % sabit_brut_siralamayi_ters_mi_ceviriyor())
    print("\nMADDE 214'UN DUZELTMESI:")
    print("  iddia: %s" % MADDE_214_IDDIASI)
    print("  %-10s %8s %8s %8s | %9s %11s %8s"
          % ("kitap", "CAGR%", "Sharpe", "dusus", "funding", "ham fiyat", "hasat"))
    for ad, (f, p, h, t) in BILESEN.items():
        g = KONTROL if ad == "kontrol" else HASATSIZ
        print("  %-10s %8.1f %8.2f %8.1f | %+9.1f %+11.1f %+8.1f"
              % (ad, g[0], g[1], -abs(g[2]), f, p, h))
    print("  hasat karin TAMAMI mi: %s | hasatsizda fiyat KAZANDIRIYOR mu: %s"
          % (hasat_karin_tamami_mi(), hasatsizda_fiyat_kazandiriyor_mu()))
    print("  hasadin payi: %%%.1f (CAGR +%.1f puan, Sharpe +%.2f, dusus %+.1f)"
          % (hasadin_payi(), HASAT_ETKISI["cagr"], HASAT_ETKISI["sharpe"],
             HASAT_ETKISI["dusus"]))
    print("  DUZELTME: %s" % MADDE_214_DUZELTME)
    print("  AYAKTA KALAN: %s" % MADDE_214_AYAKTA)
    print("\nSHORT SECICISININ DEGERI: +%.1f CAGR puani, +%.2f Sharpe "
          "(rastgele SHORT'a gore); dususu rastgele IYILESTIRIYOR: %s"
          % (SHORT_SECICI["cagr"], SHORT_SECICI["sharpe"],
             SHORT_SECICI["dusus_rastgele_daha_iyi"]))
    print("\nBENIM UC ETIKETLEME HATAM (ucu de yayimlanmadan yakalandi: %s):"
          % etiket_hatalari_yayimlanmadi_mi())
    for k, v in ETIKET_HATALARIM.items():
        print("  %-8s %s" % (k, v))
    print("  YASA: %s" % ETIKET_YASASI)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
