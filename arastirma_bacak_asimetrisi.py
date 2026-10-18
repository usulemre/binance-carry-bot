#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 281 — İKİ BACAK AYNI İŞLEM DEĞİL, AMA YOĞUNLAŞMA ASİMETRİSİ İŞE
YARAMIYOR: RED. VE MADDE 274'ÜN YASASI İKİNCİ KEZ DOĞRULANDI.

Kullanıcı "mantık değiştirmek de gerekebilir" dedi. Kitabın çekirdek
mantığında sorgulanmamış bir yer arandı ve bulundu: **kitap iki bacağı
AYNI muamele ediyor** — aynı N, aynı dolar, aynı tutma, aynı dilim.
Oysa madde 214/191 ikisinin AYNI İŞLEM OLMADIĞINI ölçmüştü. Motorun
kendi ayrışımı (kontrol koşumu):

    SHORT bacak fiyat   −12,8   |  SHORT kâr-al  +86,8   -> net **+74,0**
    LONG  bacak fiyat   −85,9   |  LONG  kâr-al +134,8   -> net **+48,9**

Long bacak kanayan bir prim ödeyip **sıkışma opsiyonu** alıyor; short
bacak az kanayıp düzenli hasat yapıyor. İki farklı enstrüman, tek
muamele. Madde 189 bir SEVİYE asimetrisinin çalıştığını göstermişti
(short TP %40→%20, +5 puan) ve madde 215'in yasası seviye asimetrisine
İZİN veriyor, zamanlama asimetrisine vermiyor. **Bacak SAYISI asimetrisi
bir yoğunlaşma/seviye asimetrisidir ve hiç denenmedi** — madde 186
yalnız SİMETRİK taramıştı (1+1, 4+4, 6+6).

TASARIM — DOLAR NÖTRLÜĞÜ KORUNUYOR
----------------------------------
`g33.py` satır 326: `y[lo]=taban/len(lo); y[sh]=-taban/len(sh)` → taraf
başına TOPLAM dolar sabit, bacak sayısı yalnız **yoğunlaşmayı**
değiştiriyor. Yani bu bir yön/beta değişimi DEĞİL.

CONFOUND VE ÇÖZÜMÜ: havuz `mm = HAVUZ*max(N_L,N_S)` ile ölçekleniyor,
yani asimetrik sayılar havuzu da değiştiriyor (madde 253: havuz önemli).
Bu yüzden asimetrinin KENDİ etkisi **eşleştirilmiş kontrastla** ölçüldü:
`(3,8)` ile `(8,3)` aynı toplam bacak, aynı havuz, aynı her şey — tek
fark hangi tarafın yoğunlaştığı. Ayrıca simetrik eğri (3+3, 5+5, 8+8)
doz/havuz zeminini veriyor. 9 koşum, çokluk beyan edildi (6 asimetrik).

BULGU 1 — ASİMETRİ ETKİSİ İŞARET DEĞİŞTİRİYOR, TANIMLANAMIYOR
-------------------------------------------------------------
Eşit riskte (kontrolün düşüşüne ölçeklenmiş) eşleştirilmiş kontrast:

    çift                LONG yoğun    SHORT yoğun    fark    ΔSharpe
    (3,5) vs (5,3)       +%113,4       +%122,2      **−8,8**  −0,037
    (3,8) vs (8,3)       +%105,0        +%97,5      **+7,5**  −0,014
    (5,8) vs (8,5)       +%100,2        +%92,1      **+8,1**  +0,025

**Üç kontrastın ikisi long yoğunlaşmayı, biri short yoğunlaşmayı
seviyor; Sharpe farkları sıfıra yakın (−0,037 … +0,025).** Hipotez
("long bacak opsiyon alır, opsiyon daha çok isim ister") desteklenmedi
— ve tersi de desteklenmedi. 6 bakışla şart 1'i tesadüfen geçme
olasılığı %77,8. **Etki yok değil: TANIMLANAMIYOR.**

BULGU 2 — TABLODAKİ TEK GÜÇLÜ DESEN SİMETRİK EĞRİ, VE O DA ÖLÇÜT TUZAĞI
-----------------------------------------------------------------------
    aday     getiri    Sharpe   düşüş   EŞİT-RİSK
    L3_S3   +%148,4    2,859    16,79   **+%126,1**  (+13,9 puan!)
    L5_S5   +%112,2    2,900    14,27    +%112,2
    L8_S8    +%76,5    2,616    13,20     +%82,7

Maksimum düşüşle eşitlenince L3_S3 **+13,9 puan** daha iyi görünüyor —
Sharpe'ı DAHA DÜŞÜK olmasına rağmen. Madde 274'ün tuzağı birebir. Doz
kararının kendi ölçütüyle (madde 243 karıştırma p95, B=20.000, −%30
toleransta) aynı kıyas:

    aday     brüt      net yıllık   kontrole göre   tek coin payı
    L3_S3   1,189x     +%190,34       **−3,58**        **%16,7**
    L5_S3   1,426x     +%192,19         −1,74            %16,7
    **L5_S5  1,473x    +%193,92         +0,00**           %10,0
    L8_S8   1,655x     +%147,84        −46,09             %6,2

**+13,9 puanlık üstünlük −3,58'e dönüyor.** Örnekleme aralığı da aynı
şeyi söylüyor (madde 276'nın yöntemi): kontrol brüt p5 1,200x →
ihtiyatlı net **+%143,5**; L3_S3 p5 0,974x → +%142,3.

**Kontrol 5+5, kararın kendi ölçütünde OPTİMUM.**

BULGU 3 — ÜSTÜNE MODELLENMEMİŞ BİR RİSK
---------------------------------------
L3_S3 bir coini brütün **%16,7**'sine çıkarıyor. Madde 192 tam bu
seviyeyi reddetmişti (*"tek coin kitabın %16,7'sine çıkıyor — delist
riski"*) ve madde 266 nötr kitabın gün içi riskinin **TEK İSİM riski**
olduğunu ölçmüştü. Yani doz ölçütü L3_S3'ü sevseydi bile backtest'in
modellemediği bir riskle bloke olurdu.

HÜKÜM
-----
**RED, iki alt soruda da.** (a) Yoğunlaşma asimetrisi: etki
tanımlanamıyor, işaret kontrasttan kontrasta değişiyor. (b) Simetrik
bacak azaltma: eşit-risk üstünlüğü doz ölçütünde **negatife** dönüyor
ve ayrıca tek-coin yoğunlaşmasıyla bloke. **Ayar DEĞİŞMEDİ (5+5).**

DERS — MADDE 274'ÜN YASASI İKİNCİ BAĞIMSIZ DOĞRULANMASI
-------------------------------------------------------
İkinci kez bir **maksimum düşüşle eşitlenmiş** üstünlük doz ölçütünde
buharlaştı: madde 274'te rezerv 0,60 (+5,80 → +1,1), burada L3_S3
(+13,9 → **−3,58**, işaret değişti). Desen artık mekanik olarak
anlaşılıyor: **maks-düşüşle eşitleme, OYNAKLIĞI artıran adayları
sistematik olarak KAYIRIR** — çünkü tek bir uç noktayı eşitler, oysa
getiri tüm dağılımdan gelir. Dolayısıyla:

**Kitabın oynaklığını değiştiren hiçbir aday, şart 3'ü (eşit-risk
getirisi) geçtiği için kabul edilmez; son kapı doz ölçütüdür.**
"""
from __future__ import annotations

# --- motorun bacak ayrisimi (kontrol kosumu) --------------------------
BACAK_AYRISIMI = {
    "short_fiyat": -12.8, "short_tp": 86.8,
    "long_fiyat": -85.9, "long_tp": 134.8,
}
SHORT_NET = BACAK_AYRISIMI["short_fiyat"] + BACAK_AYRISIMI["short_tp"]   # +74.0
LONG_NET = BACAK_AYRISIMI["long_fiyat"] + BACAK_AYRISIMI["long_tp"]      # +48.9

DOLAR_NOTR_SATIR = "g33.py:326  y[lo]=taban/len(lo); y[sh]=-taban/len(sh)"
KOSUM = 9
ASIMETRIK_BAKIS = 6
COK_BAKIS_RISKI = 77.8

# --- izgara: aday -> (getiri, sharpe, 22-24, 25-26, dusus, esit_risk) --
IZGARA = {
    "L3_S3": (148.4, 2.859, 2.684, 3.098, 16.79, 126.1),
    "L3_S5": (146.0, 2.866, 2.600, 3.224, 18.36, 113.4),
    "L3_S8": (130.3, 2.697, 2.501, 2.963, 17.71, 105.0),
    "L5_S3": (116.2, 2.903, 2.774, 3.083, 13.56, 122.2),
    "L5_S5": (112.2, 2.900, 2.776, 3.076, 14.27, 112.2),
    "L5_S8": (100.6, 2.730, 2.712, 2.772, 14.34, 100.2),
    "L8_S3": (86.8, 2.711, 2.490, 3.013, 12.70, 97.5),
    "L8_S5": (82.9, 2.705, 2.560, 2.905, 12.85, 92.1),
    "L8_S8": (76.5, 2.616, 2.595, 2.666, 13.20, 82.7),
}
KONTROL = "L5_S5"

# --- eslestirilmis kontrast: (long_yogun, short_yogun) -> fark puan ----
KONTRAST = {
    ("L3_S5", "L5_S3"): -8.8,
    ("L3_S8", "L8_S3"): +7.5,
    ("L5_S8", "L8_S5"): +8.1,
}

# --- doz olcutu (madde 243 karistirma p95, B=20.000, -%30) ------------
DOZ = {   # aday -> (brut, net_yillik, kontrole_gore, tek_coin_pay_pct)
    "L3_S3": (1.189, 190.34, -3.58, 16.7),
    "L5_S3": (1.426, 192.19, -1.74, 16.7),
    "L5_S5": (1.473, 193.92, 0.00, 10.0),
    "L8_S8": (1.655, 147.84, -46.09, 6.2),
}
ORNEKLEME = {   # aday -> (p5, medyan, p95, ihtiyatli_net)
    "L5_S5": (1.200, 1.488, 1.870, 143.5),
    "L3_S3": (0.974, 1.186, 1.493, 142.3),
}

# --- modellenmeyen risk ----------------------------------------------
MADDE_192_RED_ESIGI = 16.7      # "tek coin kitabin %16,7'sine cikiyor"
MADDE_266_TEK_ISIM = "notr kitabin gun ici riski TEK ISIM riskidir"

# --- madde 274'un yasasinin ikinci dogrulanmasi -----------------------
OLCUT_TUZAGI = {
    "madde_274_rezerv060": (5.80, 1.1),      # maks-dusus esit-risk -> doz
    "madde_281_L3_S3": (13.9, -3.58),        # isaret DEGISTI
}


def iki_bacak_ayni_mi(tol: float = 10.0) -> bool:
    """Iki bacagin net katkisi ayni mi?"""
    return abs(SHORT_NET - LONG_NET) < tol


def short_bacak_daha_karli_mi() -> bool:
    return SHORT_NET > LONG_NET


def asimetri_isaret_degistiriyor_mu() -> bool:
    v = list(KONTRAST.values())
    return max(v) > 0 > min(v)


def asimetri_tanimlanabilir_mi() -> bool:
    """Uc kontrastin hepsi AYNI yone mi isaret ediyor?"""
    v = list(KONTRAST.values())
    return all(x > 0 for x in v) or all(x < 0 for x in v)


def sharpe_farklari_sifira_yakin_mi(tol: float = 0.05) -> bool:
    """Not: Sharpe farklari izgaradan turetiliyor."""
    for (a, b) in KONTRAST:
        if abs(IZGARA[a][1] - IZGARA[b][1]) > tol:
            return False
    return True


def esit_riskte_ustun_gorunen() -> list:
    k = IZGARA[KONTROL][5]
    return [a for a, v in IZGARA.items() if v[5] > k + 5.0]


def doz_olcutunde_ustun_var_mi() -> bool:
    return any(v[2] > 0 for a, v in DOZ.items() if a != KONTROL)


def kontrol_doz_optimumu_mu() -> bool:
    return max(DOZ, key=lambda a: DOZ[a][1]) == KONTROL


def olcut_tuzagi_isaret_cevirdi_mi(ad: str = "madde_281_L3_S3") -> bool:
    esit, doz = OLCUT_TUZAGI[ad]
    return esit > 0 > doz


def ikinci_dogrulanma_mi() -> bool:
    return len(OLCUT_TUZAGI) == 2 and all(
        v[0] > v[1] for v in OLCUT_TUZAGI.values())


def yogunlasma_bloke_mi(aday: str = "L3_S3") -> bool:
    """Tek coin payi madde 192'nin reddettigi seviyede mi?"""
    return DOZ[aday][3] >= MADDE_192_RED_ESIGI


def hukum() -> str:
    return ("RED, iki alt soruda da. (a) Yogunlasma asimetrisi: etki "
            "TANIMLANAMIYOR - uc eslestirilmis kontrastta isaret degisiyor "
            "(%s) ve Sharpe farklari sifira yakin; 6 bakista tesadufi gecis "
            "olasiligi %%%.1f. (b) Simetrik bacak azaltma: maks-dususle "
            "esitlenince +%.1f puan gorunen L3_S3, doz olcutunde %+.2f'e "
            "DONUYOR (isaret degisti) ve ustune tek coin payi %%%.1f ile "
            "madde 192'nin reddettigi seviyede. Kontrol 5+5 kararın kendi "
            "olcutunde OPTIMUM. Ayar DEGISMEDI."
            % (", ".join("%+.1f" % v for v in KONTRAST.values()),
               COK_BAKIS_RISKI, OLCUT_TUZAGI["madde_281_L3_S3"][0],
               OLCUT_TUZAGI["madde_281_L3_S3"][1], DOZ["L3_S3"][3]))


def yaz() -> None:
    print("MADDE 281 — BACAK ASİMETRİSİ (yoğunlaşma)\n")
    print("MOTORUN BACAK AYRIŞIMI:")
    print("  SHORT: fiyat %+.1f + kâr-al %+.1f = **%+.1f**"
          % (BACAK_AYRISIMI["short_fiyat"], BACAK_AYRISIMI["short_tp"], SHORT_NET))
    print("  LONG : fiyat %+.1f + kâr-al %+.1f = **%+.1f**"
          % (BACAK_AYRISIMI["long_fiyat"], BACAK_AYRISIMI["long_tp"], LONG_NET))
    print("  -> iki bacak AYNI işlem mi: %s | short daha kârlı mı: %s"
          % (iki_bacak_ayni_mi(), short_bacak_daha_karli_mi()))
    print("\nDOLAR NÖTRLÜĞÜ: %s (taraf başına TOPLAM dolar sabit)" % DOLAR_NOTR_SATIR)
    print("\nİZGARA (%d koşum):" % KOSUM)
    print("  aday    | getiri  | Sharpe | 22-24 | 25-26 | düşüş | eşit-risk")
    for a in sorted(IZGARA):
        v = IZGARA[a]
        print("  %-7s | %+7.1f | %6.3f | %5.3f | %5.3f | %5.2f | %+9.1f"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5]))
    print("\nEŞLEŞTİRİLMİŞ KONTRAST (aynı toplam bacak, aynı havuz):")
    print("  çift              | LONG yoğun | SHORT yoğun | fark   | ΔSharpe")
    for (a, b), fark in KONTRAST.items():
        print("  %-7s vs %-7s | %+10.1f | %+11.1f | %+6.1f | %+7.3f"
              % (a, b, IZGARA[a][5], IZGARA[b][5], fark,
                 IZGARA[a][1] - IZGARA[b][1]))
    print("  -> işaret değiştiriyor mu: %s | tanımlanabilir mi: %s"
          % (asimetri_isaret_degistiriyor_mu(), asimetri_tanimlanabilir_mi()))
    print("  -> çok bakış riski: %%%.1f (%d asimetrik aday)"
          % (COK_BAKIS_RISKI, ASIMETRIK_BAKIS))
    print("\nEŞİT RİSKTE ÜSTÜN GÖRÜNEN: %s" % esit_riskte_ustun_gorunen())
    print("\nDOZ ÖLÇÜTÜ (madde 243 karıştırma p95, −%30):")
    print("  aday    | brüt   | net yıllık | kontrole göre | tek coin payı")
    for a in sorted(DOZ, key=lambda x: -DOZ[x][1]):
        b, n, f, p = DOZ[a]
        print("  %-7s | %.3fx | %+10.2f | %+13.2f | %%%.1f" % (a, b, n, f, p))
    print("  -> doz ölçütünde üstün var mı: %s | kontrol OPTİMUM mu: %s"
          % (doz_olcutunde_ustun_var_mi(), kontrol_doz_optimumu_mu()))
    print("\nÖRNEKLEME ARALIĞI (madde 276'nın yöntemi):")
    for a, v in ORNEKLEME.items():
        print("  %-7s p5 %.3fx | medyan %.3fx | p95 %.3fx -> ihtiyatlı net +%%%.1f"
              % (a, v[0], v[1], v[2], v[3]))
    print("\nMODELLENMEYEN RİSK: L3_S3 tek coini brütün %%%.1f'ine çıkarıyor;"
          " madde 192 bu seviyeyi REDDETMİŞTİ (delist riski) ve madde 266: %s"
          % (DOZ["L3_S3"][3], MADDE_266_TEK_ISIM))
    print("  -> yoğunlaşma bloke mi: %s" % yogunlasma_bloke_mi())
    print("\nMADDE 274'ÜN YASASI — İKİNCİ BAĞIMSIZ DOĞRULANMASI:")
    for ad, (esit, doz) in OLCUT_TUZAGI.items():
        print("  %-22s maks-düşüş eşit-risk %+5.1f -> doz ölçütü %+6.2f"
              % (ad, esit, doz))
    print("  -> işaret çevirdi mi (281): %s | ikinci doğrulanma mı: %s"
          % (olcut_tuzagi_isaret_cevirdi_mi(), ikinci_dogrulanma_mi()))
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
