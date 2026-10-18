#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 288 — PRİM-ÖLÇEKLİ BRÜTÜN DOZU TARANDI: KURALI GEÇEN BİR NOKTA
VAR, AMA TURUN EN ÖNEMLİ BULGUSU KURALIN KENDİSİ HAKKINDA.

Madde 287 bir kapı aralık bırakmıştı: prim-ölçekli brütün kayıtlı
noktası (e0,5 ref180) ne getirinin ne doz ölçütünün tepesiydi, ve madde
239 bu adayı TEK sebeple reddetmişti - şart 1, 25-26'da −0,032. Soru:
ızgarada, kuralı GEVŞETMEDEN dört şartı da geçen bir hücre var mı?

Madde 286'nın ön-filtresi "etki +38 puan = 2,9x ASE -> tur hüküm
verebilir" dedi ve tur başlatıldı. (Aşağıdaki İKİNCİ YASA, ön-filtrenin
bu turda neredeyse ters yönde çalıştığını gösteriyor.)

═══ BİRİNCİ YASA — KALİBRASYON KONTROLDE DEĞİL ADAYDA SINANIR ═══

Doz ölçütünü hızlandırmak için "−%30 tolerans"ı tam örnek maksimum
düşüşe kalibre ettim (hedef %20,70). Kontrolü BİREBİR yeniden üretti:
1,469x / net +%193,94 (madde 287: 1,469x / +%193,17). Kalibrasyon
doğrulanmış göründü. Sonra aynı kodu adaya uyguladım: **+87,27 puan**.
Madde 287'nin kayıtlı değeri **+38,14**. 2,3 kat şişmiş.

Sebep: aday tam örnek maksimum düşüşü iyileştiriyor (−14,27 -> −13,40)
ama 1 YIL p95 düşüşünü aynı oranda iyileştirmiyor. Kısayol kontrolde
tuttu, adayda kaydı - ve kaydığı yön LEHTE. Bu kaçınılmaz: kısayol
"kontrolü yeniden üretene kadar" ayarlanıyor, yani kontrol bir TEST
değil bir KALİBRASYON NOKTASI. Test adayda yapılmalı.

Kısayol geri alındı; madde 287'nin kodu (`m287_olc.py` / `m287_boot.py`)
birebir yeniden kullanıldı: karıştırma p95, B=16.000, net = CAGR −
0,79·brüt.

═══ İKİNCİ YASA — ASE BİR PROJE SABİTİ DEĞİL, ADAYA AİT BİR SAYIDIR ═══

Madde 285 ASE'yi (asgari saptanabilir etki) TEK bir adaydan ölçüp
(+7,22 -> P %67,5) proje sabiti ilan etti: ASE_PUAN = 13,0. Madde 288
dört ayrı (etki, P) çifti ölçtü ve ilişki MONOTON ÇIKMADI:

    etki  +1,32 -> P %71,0   (288: KARIŞTIRILMIŞ PLASEBO)
    etki  +7,22 -> P %67,5   (285: %10 kontrarian dilim)
    etki +11,89 -> P %95,0   (288: prim-brüt e0,10 r120)
    etki +38,14 -> P %90,7   (287: prim-brüt e0,50 r180)

+1,32 bir plasebonun etkisi ve P'si +7,22'den YÜKSEK. Sebep: eşli blok
bootstrap'in gürültüsü etkinin büyüklüğüne değil, adayın kontrole göre
İZLEME HATASINA bağlı. Prim-brüt adayı kontrolün kendisinin %0,5
yeniden ölçeklenmişidir -> fark serisi durgun -> küçük etki bile yüksek
P. Madde 285'in adayı AYRI bir kitaptı -> fark serisi oynak -> büyük
etki bile düşük P.

MALİYETİ SOMUT: sabit ASE bu turu BAŞLATMAMAMI söylerdi ("etki +11,9 <
13, gereken ufuk 4,9 yıl, mevcut 4,12") - oysa ölçülen P %95,0'ti ve
aday 275-288 aralığında `gecer_mi()`'yi geçen TEK aday oldu. Güç
filtresi kötü turu elemek için kuruldu; sabitleştirilince iyi adayı
eliyor. `karar_kurali.py` düzeltildi: `ase_puan_adaydan(sigma_boot)` =
z(0,80)·σ, ve `tur_degerli_mi()` σ verilmedikçe artık hüküm vermiyor.

═══ ÜÇÜNCÜ YASA — DÖRT ŞART KURALI HİÇBİR ŞEY YAPMAYAN ADAYI GEÇİRİR ═══

`BRUT_PLASEBO=2` (aynı çarpan DAĞILIMI, zamanda KARIŞTIRILMIŞ - saf
gürültü) `gecer_mi()`'den **GEÇTİ**: 22-24 +0,004 · 25-26 +0,005 ·
düşüş −14,39 vs −14,54 · eşit-risk +2,3 puan · kaldıraç kozmetik.

Mekanik: ±%0,5'lik rastgele bir brüt modülasyonu kitabı neredeyse hiç
değiştirmez, dolayısıyla iki alt dönem Sharpe farkı iki BAĞIMSIZ
yazı-turaya döner (şart 1'i geçme şansı ~%25) ve kalan üç şart zaten
otomatik geçer. **"Dört şartı da geçti" bir KANIT cümlesi değil, bir
ELEME cümlesidir** - gerek şart, yeter şart değil.

Madde 286 "bir karar aracının en önemli testi, ölçümün BAŞARISIZ olduğu
yoldur" demişti; burada aynısı kuralın kendisi için: kuralın en önemli
testi GEÇMEMESİ GEREKEN bir adaydır. Sicilde plasebolar her zaman
getiriyle kıyaslanmış, hiç `gecer_mi()`'ye verilmemişti.

AYIRAN ÖLÇÜT VAR: doz ölçütü + eşli blok bootstrap. Aday %95,3,
karıştırılmış plasebo **%71,0** (barın altında), zamanda ters plasebo
şart 1 VE şart 3'ten düşüyor (eşit-risk −2,7, düşüş kötüleşiyor).
Yani bar ayakta - ama onu taşıyan şey kural değil, bootstrap.

═══ ÖLÇÜM NOTU — FAZ BAZI ═══

`Olcum`'un docstring'i "Sharpe'lar faz ORTALAMASI olmalı (madde 133.6)"
diyor. Madde 287 kontrolün 25-26 Sharpe'ını 3,076 yazmış: bu FAZ_KAY=0
tek fazıdır. Madde 239 ise 3,147 yazmış: iki faz ortalaması. İkisi de
doğru hesaplanmış ama aynı sayı değil - motor-Sharpe/günlük-Sharpe
tuzağının kuzeni. Reddin İŞARETİ her iki bazda aynı çıktığı için
239'un ve 287'nin hükümleri ayakta; madde 288 kuralın kendi bazını
(faz ortalaması) kullanıyor ve tek fazı yanında raporluyor.

═══ IZGARA ═══

25 motor ayarı x 2 faz = 50 koşu, artı 3 plasebo ayarı x 2 faz.
25-26 ΔSharpe / doz farkı puan (faz ortalaması):

    e\\ref      90        120         150        180        270       365
    0,10    −0,021   +0,003     **+0,012**   +0,005    −0,006       -
    0,15    −0,034   −0,001        -         −0,000       -         -
    0,25      -      −0,018        -         −0,020    −0,048    −0,034
    0,50      -      −0,072        -         −0,033    −0,060       -
    0,75      -      −0,039        -         −0,033    −0,066    −0,093
    1,00      -      −0,034        -         −0,028    −0,077    −0,117

Şart 1 açığı e ile MONOTON büyüyor; e0,10'da artıya geçiyor. Geçen
band ref 120-180 (ref 90 ve 270 düşüyor) - üç komşu hücre, ortası ve
aynı zamanda en iyisi **ref150**. Hücre bandın ORTASINDAN alındı,
en iyisinden değil (madde 276'nın yöntemi); ikisi aynı noktaya denk
geldi.

═══ ÇOKLU BAKIŞ (madde 279) ═══

25 hücreye bakıldı, 3'ü şart 1'i geçti. Bir arama artefaktı olmadığının
dört gerekçesi: (1) doz-yanıt MONOTON - artefakt monoton olmaz; (2)
geçen hücreler izole değil, bitişik bir band; (3) plasebo ailesi adayı
bracket'liyor (ters: kontrolün ALTINDA; karıştırılmış: ayırt edilemez;
aday: açıkça üstünde); (4) yapı madde 239'da ÖN KAYITLI, 288 yalnız
dozunu taradı - ve madde 276 doz taramasını yöntem olarak kurmuştu.

DÜRÜST KALAN: 25-26'daki +0,012 bir GÜRÜLTÜDÜR (P %66,6). Yani şart
1'in geçmesi şansın doğru tarafa düşmesidir. Kararı taşıyan şey o
değil: 22-24 +0,082 (P %98,0), doz +12,15 (P %95,3), düşüş iyileşiyor,
iki rejimde de kazanıyor, kaldıraç gerektirmiyor, plasebodan ayrışıyor.
Yapı gerçek; şart-1 geçişi tesadüf. İkisi aynı yönü gösteriyor, ama
ikincisini birincisi gibi sunmak yanlış olurdu.

═══ KOD ═══

Yapı motorda vardı (`g33.py`: BRUT_PRIM/REF/ALT/UST), CANLI BOTTA YOKTU.
Madde 288 `carry_bot.py`'a yazdı: `prim_olc` (kesitsel p90−p10, zaten
toplanan funding serisinden - EK API İSTEĞİ YOK), `prim_kaydet` /
`_prim_gecmis_oku` (tur başına bir satır), `prim_carpani` (30g ort /
PRIM_REF_GUN kayan medyan, üs, [0,5;1,5] kırpma, 1 tur gecikme).
Kanca TEK yerde: `olcek *= prim_carpani()`. `gerekli_kaldirac()` payı
ihtiyatlı tavanla (1,5) büyütüyor.

**VARSAYILAN KAPALI** (`CARRY_PRIM_E=0`): bot hiç canlı çalışmadı,
üçüncü yasa gereği kuralın geçmesi tek başına kabul gerekçesi değil, ve
çarpan ilk ~75 günde zaten 1,0 döner. Madde 216'nın takvimi bittikten
sonra tek satır: `CARRY_PRIM_E=0.10`.
"""

# --- turun ON FILTRESI (madde 286, madde 288'de duzeltildi) -----------
ON_FILTRE_SOYLEDI = "tur hukum verebilir (+38,14 = 2,9x sabit ASE)"
ON_FILTRE_YANILGISI = ("ayni filtre, ADAYIN kendi etkisi (+11,89) ile "
                       "sorulsa turu IPTAL ettirirdi - olculen P %95,0")

# --- birinci yasa: kalibrasyon hatam ---------------------------------
KISAYOL = {
    "ne": "-%30 toleransi TAM ORNEK maks dususe kalibre et (hedef %20,70)",
    "kontrol_uretildi": (1.469, 193.94),      # madde 287: 1.469 / 193.17
    "aday_sisti": 87.27,                      # dogrusu 38.14
    "sisme_kati": 87.27 / 38.14,
    "sebep": "aday tam ornek maks dususu iyilestiriyor ama 1 YIL p95 "
             "dususunu ayni oranda iyilestirmiyor",
}
BIRINCI_YASA = ("bir olcum kisayolunun KONTROLDE tutmasi, ADAYDA "
                "tuttugunun kaniti degildir; kontrol bir test degil bir "
                "kalibrasyon noktasidir ve kisayol hep LEHTE siser")

# --- ikinci yasa: ASE adaya aittir -----------------------------------
ASE_GOZLEMLERI = {            # ad -> (etki puan, olculen P(>0) %)
    "288 plasebo karistirilmis": (1.32, 71.0),
    "285 kontrarian dilim": (7.22, 67.5),
    "288 prim-brut e0.10 r120": (11.89, 95.0),
    "287 prim-brut e0.50 r180": (38.14, 90.7),
}
ASE_SABIT = 13.0
IKINCI_YASA = ("ASE bir proje sabiti degil ADAYA ait bir sayidir: esli "
               "bootstrap gurultusu etkinin BUYUKLUGUNE degil adayin "
               "kontrole gore IZLEME HATASINA baglidir - tek bir adaydan "
               "genellenen guc esigi, iyi adayi turun BASINDA oldurur")

# --- ucuncu yasa: kural plaseboyu geciriyor --------------------------
PLASEBO = {   # ad -> (22-24 fark, 25-26 fark, esit_risk fark, doz fark,
              #        gecer_mi, doz bootstrap P veya None)
    "aday_e010_r150": (+0.082, +0.012, +8.6, 12.15, True, 95.3),
    "aday_e010_r120": (+0.084, +0.003, +7.0, 11.89, True, 95.0),
    "plasebo_karistirilmis": (+0.004, +0.005, +2.3, 1.65, True, 71.0),
    "plasebo_zamanda_ters": (+0.053, -0.036, -2.7, 3.51, False, None),
}
KANIT_BARI = 80.0
UCUNCU_YASA = ("dort sart kurali HICBIR SEY YAPMAYAN bir adayi gecirir: "
               "+-%0,5 rastgele modulasyon iki alt donem Sharpe farkini "
               "iki bagimsiz yazi-turaya cevirir (~%25) ve kalan uc sart "
               "otomatik gecer - 'dort sarti da gecti' bir KANIT cumlesi "
               "degil bir ELEME cumlesidir")
SICIL_NOTU = ("sicilde plasebolar her zaman GETIRIYLE kiyaslanmis, hic "
              "gecer_mi()'ye verilmemisti")

# --- faz bazi ---------------------------------------------------------
FAZ_BAZI = {   # kontrolun 25-26 Sharpe'i, iki ayri bazda
    "faz0 (madde 287 bunu kullandi)": 3.076,
    "iki faz ortalamasi (madde 239, ve madde 133.6'nin istedigi)": 3.147,
}

# --- izgara: ayar -> 25-26 DeltaSharpe, doz farki (faz ortalamasi) ----
IZGARA = {
    ("0.10",  "90"): (-0.021,  8.91),
    ("0.10", "120"): (+0.003, 11.89),
    ("0.10", "150"): (+0.012, 12.15),
    ("0.10", "180"): (+0.005, 11.12),
    ("0.10", "270"): (-0.006,  9.61),
    ("0.15",  "90"): (-0.034, 12.88),
    ("0.15", "120"): (-0.001, 16.42),
    ("0.15", "180"): (-0.000, 15.71),
    ("0.25", "120"): (-0.018, 25.67),
    ("0.25", "180"): (-0.020, 23.85),
    ("0.25", "270"): (-0.048, 18.22),
    ("0.25", "365"): (-0.034, 19.71),
    ("0.50", "120"): (-0.072, 31.92),
    ("0.50", "180"): (-0.033, 35.78),
    ("0.50", "270"): (-0.060, 27.55),
    ("0.75", "180"): (-0.033, 42.01),   # faz0: +42,01 - doz tepesi burada degil
    ("1.00", "180"): (-0.028, 45.19),   # faz0 olcumu; doz tepesi
}
BAKIS_SAYISI = 25
GECEN_HUCRE = (("0.10", "120"), ("0.10", "150"), ("0.10", "180"))
BAND_KENARI = (("0.10", "90"), ("0.10", "270"))
SECILEN = ("0.10", "150")

# --- secilen noktanin tam cercevesi (faz ortalamasi) -----------------
SECILEN_SARTLAR = {
    "22-24 Sharpe": (2.871, 2.789, +0.082),
    "25-26 Sharpe": (3.159, 3.147, +0.012),
    "dusus": (-14.27, -14.54, -0.27),
    "esit risk getiri": (120.9, 112.3, +8.6),
    "kaldirac": 1.019,
}
SECILEN_BOOTSTRAP = {
    "22-24 DeltaSharpe": (0.0821, 98.0),
    "25-26 DeltaSharpe": (0.0165, 66.6),
    "doz farki": (11.66, 95.3),          # ort, P(>0)
}
SECILEN_DOZ = (1.508, 213.01, 12.15)     # brut, net CAGR, kontrole gore
SECILEN_BAHIS = {"22-24": 16.79, "25-26": 3.17}
ORTALAMA_CARPAN = 1.005

# --- kod ---------------------------------------------------------------
BOT_FONKSIYONLARI = ("prim_olc", "prim_kaydet", "_prim_gecmis_oku",
                     "prim_carpani")
BOT_KANCASI = "olcek *= prim_carpani()  (TEK yer, vol_olcek'in ustune)"
VARSAYILAN_KAPALI = True
ACILIS_KOMUTU = "CARRY_PRIM_E=0.10"
ISINMA_GUN = 75
EK_API_ISTEGI = 0

RISKLER = (
    "25-26'daki +0,012 GURULTU (P %66,6) - sart 1'in gecmesi sansin dogru "
    "tarafa dusmesidir; kararı tasiyan sey 22-24 (P %98,0) ve doz (P %95,3)",
    "dort sart kurali karistirilmis plaseboyu da geciriyor - yani 'kurali "
    "gecti' cumlesi bu adayi dogrulamiyor",
    "doz olcutu, icra varsayimlari yalniz 2 aylik dakika verisinde "
    "dogrulanmis bir geri testte olculuyor",
    "carpan canli botta bir DOSYA GECMISINE dayaniyor; dosya silinirse "
    "carpan 1,0'a doner (zararsiz yon) ama kazanc da gider",
    "25 hucreye bakildi; monotonluk ve plasebo ayrismasi savunma, ama "
    "tek basina bir hucrenin gectigi iddia edilemez",
)


# --- sinamalar --------------------------------------------------------
def kisayol_kontrolde_tuttu_mu(tol: float = 1.0) -> bool:
    """Kisayol kontrolu yeniden uretti mi? (Evet - ve bu yetmedi.)"""
    return abs(KISAYOL["kontrol_uretildi"][1] - 193.17) < tol


def kisayol_adayda_sisti_mi(kat: float = 2.0) -> bool:
    return KISAYOL["sisme_kati"] >= kat


def ase_monoton_mu() -> bool:
    """Etki buyudukce P buyuyor mu? (Madde 288: HAYIR.)"""
    s = sorted(ASE_GOZLEMLERI.values())
    return all(s[i][1] <= s[i + 1][1] for i in range(len(s) - 1))


def sabit_ase_turu_oldururdu_mu() -> bool:
    """Sabit ASE, secilen adayin etkisiyle sorulsa turu iptal ettirir mi?"""
    return SECILEN_DOZ[2] < ASE_SABIT


def kural_plaseboyu_geciriyor_mu() -> bool:
    return PLASEBO["plasebo_karistirilmis"][4] is True


def bootstrap_plaseboyu_geciriyor_mu() -> bool:
    """Doz olcutu + bootstrap plaseboyu AYIRIYOR mu? (Ayiriyorsa False.)"""
    return PLASEBO["plasebo_karistirilmis"][5] >= KANIT_BARI


def ters_plasebo_kontrolun_altinda_mi() -> bool:
    return PLASEBO["plasebo_zamanda_ters"][2] < 0


def doz_yaniti_monoton_mu() -> bool:
    """e buyudukce 25-26 acigi buyuyor mu? (ref 120 ve 180 kolonlari)"""
    for ref in ("120", "180"):
        d = [(float(e), IZGARA[(e, ref)][0]) for e in
             ("0.10", "0.15", "0.25", "0.50") if (e, ref) in IZGARA]
        d.sort()
        if not all(d[i][1] >= d[i + 1][1] - 1e-9 for i in range(len(d) - 1)):
            return False
    return True


def band_kapali_mi() -> bool:
    """Gecen band'in iki kenari da duruyor mu?"""
    return all(IZGARA[k][0] < 0 for k in BAND_KENARI) and \
        all(IZGARA[k][0] > 0 for k in GECEN_HUCRE)


def secilen_bandin_ortasi_mi() -> bool:
    refs = sorted(int(r) for _, r in GECEN_HUCRE)
    return int(SECILEN[1]) == refs[len(refs) // 2]


def dort_sart_gecti_mi() -> bool:
    return (SECILEN_SARTLAR["22-24 Sharpe"][2] > 0
            and SECILEN_SARTLAR["25-26 Sharpe"][2] > 0
            and SECILEN_SARTLAR["dusus"][2] <= 3.0
            and SECILEN_SARTLAR["esit risk getiri"][2] >= 0
            and SECILEN_SARTLAR["kaldirac"] < 1.05)


def kanit_bari_gecti_mi() -> bool:
    return SECILEN_BOOTSTRAP["doz farki"][1] >= KANIT_BARI


def bahis_mi() -> bool:
    """Bir rejim bahsi mi? (Iki bacak da artiysa DEGIL.)"""
    return not all(v > 0 for v in SECILEN_BAHIS.values())


def sart1_gurultu_mu(esik: float = 80.0) -> bool:
    """25-26 iyilesmesi kanit bariyla desteklenmiyor mu? (Evet - gurultu.)"""
    return SECILEN_BOOTSTRAP["25-26 DeltaSharpe"][1] < esik


def kaldirac_karari_mi() -> bool:
    """Madde 239'un (1) uyarisi bu dozda hala gecerli mi? (Hayir.)"""
    return ORTALAMA_CARPAN > 1.05


def varsayilan_kapali_mi() -> bool:
    return VARSAYILAN_KAPALI is True


def hukum() -> str:
    return (
        "KURAL GECTI, AMA KURALIN GECMESI KANIT DEGIL. e0,10/ref150 "
        "gecer_mi()'den gecen ilk aday (275-288); doz olcutu +12,15 puan, "
        "esli blok bootstrap P %95,3, iki rejimde de pozitif, dusus "
        "iyilesiyor, kaldirac gerektirmiyor, plasebolardan ayrisiyor "
        "(%71,0 ve sart-1/sart-3 reddi). YAPI BOTA KURULDU, VARSAYILAN "
        "KAPALI (CARRY_PRIM_E=0): madde 216'nin takvimi bitince tek "
        "satirla acilir. Turun en degerli bulgusu aday degil: karistirilmis "
        "PLASEBO da dort sarti gecti - kural gerek sart, yeter sart degil. "
        "Ve ASE sabiti yanlislandi: yazili haliyle bu adayi turun basinda "
        "elerdi."
    )


def yaz() -> None:
    print(__doc__)
    print("ON FILTRE:", ON_FILTRE_SOYLEDI)
    print("  YANILGISI:", ON_FILTRE_YANILGISI)
    print("\nBIRINCI YASA:", BIRINCI_YASA)
    print("  kisayol kontrolu uretti: %.3fx / %+.2f  (madde 287: 1.469 / +193.17)"
          % KISAYOL["kontrol_uretildi"])
    print("  aday: %+.2f yerine %+.2f -> %.2f kat sisme"
          % (38.14, KISAYOL["aday_sisti"], KISAYOL["sisme_kati"]))
    print("\nIKINCI YASA:", IKINCI_YASA)
    for ad, (e, p) in sorted(ASE_GOZLEMLERI.items(), key=lambda kv: kv[1]):
        print("  etki %+7.2f -> P %%%.1f   %s" % (e, p, ad))
    print("  monoton mu: %s | sabit ASE (%.1f) bu adayi elerdi mi: %s"
          % (ase_monoton_mu(), ASE_SABIT, sabit_ase_turu_oldururdu_mu()))
    print("\nUCUNCU YASA:", UCUNCU_YASA)
    print("  %s" % SICIL_NOTU)
    print("  %-24s %8s %8s %10s %9s %7s %7s"
          % ("ad", "22-24", "25-26", "esit-risk", "doz fark", "kural", "boot P"))
    for ad, v in PLASEBO.items():
        print("  %-24s %+8.3f %+8.3f %+10.1f %+9.2f %7s %7s"
              % (ad, v[0], v[1], v[2], v[3], "GECER" if v[4] else "DUSER",
                 "-" if v[5] is None else "%.1f" % v[5]))
    print("\nFAZ BAZI (kontrolun 25-26 Sharpe'i):")
    for k, v in FAZ_BAZI.items():
        print("  %-52s %.3f" % (k, v))
    print("\nIZGARA (25-26 DeltaSharpe / doz farki, %d bakis):" % BAKIS_SAYISI)
    for (e, r), (d, f) in sorted(IZGARA.items()):
        mark = "  <= GECTI" if (e, r) in GECEN_HUCRE else ""
        print("  e%-5s ref%-4s %+0.3f  %+6.2f%s" % (e, r, d, f, mark))
    print("  doz-yaniti monoton mu: %s | band kapali mi: %s | secilen bandin "
          "ortasi mi: %s" % (doz_yaniti_monoton_mu(), band_kapali_mi(),
                             secilen_bandin_ortasi_mi()))
    print("\nSECILEN: e%s / ref%s" % SECILEN)
    for ad, v in SECILEN_SARTLAR.items():
        if ad == "kaldirac":
            print("  %-18s %.3fx" % (ad, v))
        else:
            print("  %-18s %8.3f vs %8.3f  (%+0.3f)" % (ad, v[0], v[1], v[2]))
    print("  doz olcutu %.3fx / net %+.2f -> **%+.2f puan**" % SECILEN_DOZ)
    for ad, (o, p) in SECILEN_BOOTSTRAP.items():
        print("  bootstrap %-18s ort %+0.4f  P(>0) %%%.1f" % (ad, o, p))
    print("  bahis: 22-24 %+.2f | 25-26 %+.2f -> bahis mi: %s"
          % (SECILEN_BAHIS["22-24"], SECILEN_BAHIS["25-26"], bahis_mi()))
    print("  ortalama carpan %.3fx -> kaldirac karari mi: %s"
          % (ORTALAMA_CARPAN, kaldirac_karari_mi()))
    print("\nKOD: %s | kanca: %s" % (", ".join(BOT_FONKSIYONLARI), BOT_KANCASI))
    print("  varsayilan KAPALI: %s | acilis: %s | isinma %d gun | ek API %d"
          % (varsayilan_kapali_mi(), ACILIS_KOMUTU, ISINMA_GUN, EK_API_ISTEGI))
    print("\nRISKLER:")
    for r in RISKLER:
        print("  - %s" % r)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
