"""MADDE 249: IKINCI BORSA (OKX) - "yeni bir kitap" sezgisinin olculmesi.

Kullanicinin sorusu: "neden bulamiyorsun, belki yeni bir kitap lazim".
Dogru sezgi - ve madde 237'nin kendi recetesi de buydu ("farkli bir
PIYASA ara"). Madde 174 borsalar arasi funding FARKINI kapatmisti, ama
kitabin KENDISINI ikinci bir evrende kosmak hic denenmedi.

Bu kutudan Binance API'si erisilemiyor (451) ama **OKX erisilebiliyor**
(200). Yani ilk kez gercekten YENI bir evren indirilebildi: 140 sembol,
4 saatlik mum, 417 gun.

ONEMLI: bu dosya KENDI backtester'ini tasir, cunku motorun paneli
Binance'e ozgu (kalabalik olcutu `globalLongShortAccountRatio` OKX'te
yok). Karsilastirma adil olsun diye AYNI backtester iki evrende de
kosulur ve tek fark BORSA olur.

================================================================
0) BACKTESTER DOGRULAMASI (once bu - yoksa hicbir sayi yayinlanmaz)
================================================================
                            yillik   Sharpe   dusus     (GUNLUK baz)
  motor, ciplak secici, TP yok    +72,5    1,389   -34,8   <- madde 238 A
  benim bt(), ayni               +73,2    1,405   -33,1
  motor, ciplak + TP 40/20       +64,5    1,561   -28,7   <- yeni referans
  benim bt(), ayni               +64,5    1,551   -27,2

Ikinci satir cifti madde 249'da OZELLIKLE kosuldu, cunku ilk dogrulamayi
yalnizca TP KAPALI halde yapmistim - klasik hata; TP acikken backtester
-%54,6 / Sharpe -2,087 veriyordu.

HATA 1 - TERS DOLUM FIYATI (yayinlanmadan yakalandi): TP dolumunu
`min(sev,op) if uzun else max(sev,op)` diye yazmistim. Bu konvansiyon
g33.py'de DOGRUDUR - ama orada STOP vardir (TAKIP ve SLL/SLS blokları),
stop ters tarafa gap atar. TP ise bir LIMIT emri. Ters cevrilmis hali
normal durumda (bar TP'nin altinda acip gun icinde seviyeye yukselir)
`op ~ cv[i]` donduruyordu: pozisyon KAZANCI SIFIRLANARAK kapaniyordu.
Yani her TP dolumu kendi hasadini siliyordu - madde 214'un "kârin
TAMAMI TP hasadi" bulgusunun tam tersi. Motor etkilenmedi: g33.py'de TP
`br[k]=sev/cv[i,k]-1` ile tam seviyeden dolar.

Teshisi veren olcum: TP 1000/1000 (hic dolmaz) = TP YOK (birebir), ama
TP 100/100 (nadiren dolar) bile 33 puan kotuydu -> hata DOLUM YOLUNDA.
Duzeltmeden sonra merdiven dogru yone donuyor:
  TP yok +73,2 / 1,405 / -33,1 · TP 100/100 +79,2 / 1,579 / -31,2
  TP 300/90 +77,1 / 1,479 / -33,1 · TP 40/20 +64,5 / 1,551 / -27,2

HATA 2 - HACIM BIRIMI: OKX history-candles alan 7 `volCcyQuote`, yani
ZATEN USDT. Paneli kurarken fiyatla carpmisim; uygunluk sayilari fiyat
kati kadar sisiyordu ($100M ustu 20,0 -> dogrusu 9,9). Ticker anlik
sayisiyla (12) capraz dogrulandi.

HATA 3 - SAHTE SINYAL: `ODE.fillna(0)` funding verisi OLMAYAN barlarda
SIN'i gecerli gorunen bir SIFIR yapiyordu. Maskelenince gercek pencere
ortaya cikti (asagi). Maskesiz halde sinyalin medyani 0'di ve sinyali
TERS cevirmek sonucu degistirmiyordu (-18,8 vs -18,1) - "sinyal yok"un
imzasi.

================================================================
1) OKX EVRENI: KITABI TASIYAMAZ
================================================================
485 canli USDT swap var, ama likidite dar (gunluk ortalama UYGUN sembol,
2026-06-30 -> 2026-10-03):

  esik        OKX     Binance (ayni pencere, canli uygunluk)
  $100M       9,9     -
  $50M       16,0     -
  $20M       28,6     34,4
  kitabin ihtiyaci: taraf basina 15 ADAY (madde 226) = en az 30

Yani OKX projenin likidite standardinda ($100M) kitabin ucte birini
tasiyor. Genislik tek basina aciklama DEGIL: Binance'i her barda hacme
gore ilk 26 sembole daraltinca kitap +%61,8'den +%60,9'a iniyor -
yani darlik 1 puan. Fark BASKA yerde.

================================================================
2) ASIL FARK: FUNDING DAGILIMI 2-4 KAT DAHA DAR
================================================================
Seciciyi besleyen sey funding'in KESITSEL ACIKLIGI. Iki borsada AYNI
formulle (48sa gerceklesmis odeme -> yillik oran) kurulan sinyal:

  pencere 2026-07-01 -> 2026-08-31 (372 bar)
                    kesit std   5-5 ACIKLIK
    OKX                 1,053         1,523
    BINANCE             3,614         6,175   -> **4,05 KATI**
  Binance TAM tarih (2022-07 -> 2026-08)
    BINANCE             1,602         3,100   -> OKX'in **2,04 KATI**

(Esli pencere Binance icin olagandisi genis bir donem - kendi uzun
vadeli ortalamasinin 2 kati. Adil kiyas 2,04 katidir, 4,05 degil.)

Sinyal TANIMI kiyasi bozmuyor: Binance'i OKX'in formuluyle kosmak
+%60,2 / 1,474 veriyor (sk_bar48 ile +%64,5 / 1,551).

MEKANIZMA OKX'TE VAR - ama ince. Funding bacagi tek basina, 96 gunde:
  +%59,9 / yil, Sharpe 8,454, dusus -%0,1
Yani carry gercek ve duzgun; onu kâra ceviren DAGILIM dar.

================================================================
3) NEDEN HUKUM VERILEMEZ: 96 GUN HICBIR SEY OLCMEZ
================================================================
OKX'in public `funding-rate-history` ucu **2026-06-29'da basliyor**;
-120 gun sorgusu 0 kayit donuyor. Kullanilabilir funding: 96 GUN.

Sart 1 iki ALT DONEMDE (22-24 ve 25-26) Sharpe iyilesmesi ister. 96
gunle bu sart tanim geregi kurulamaz. Ustelik 96 gun gurultuden
ayirt edilemez - CALISAN Binance kitabinin kendi serisinden cekilen
rastgele 96 gunluk pencereler (4.000 ornek):

  ortalama Sharpe  +1,737   std 2,132
  p5 -0,867 · p25 +0,244 · p50 +1,295 · p75 +2,632 · p95 +6,380
  **NEGATIF cikma olasiligi: %21,1**

  gereken pencere:  96 gun -> Sharpe standart hatasi ~1,95
                   365 gun -> ~1,00      1.095 gun -> ~0,58

OKX'in 96 gunluk tam kitabi -%46,5 / Sharpe -1,683 cikti. Bu sayi
**BULGU OLARAK YAYINLANMAZ**: calisan bir kitap bu pencere boyunda
besde bir kez negatif gorunuyor (-1,683'ten kotu olma olasiligi %1,1,
yani zayif bir aleyhte delil - kanit degil). Ayni esli 62 gunde
Binance'in kendisi de -%5,8 verdi.

================================================================
4) SONUC
================================================================
"Yeni bir kitap lazim" sezgisi dogruydu ve ilk kez gercekten yeni bir
evren olculdu. Cevap: **OKX yeni bir kâr kaynagi degil, ayni piyasanin
DAHA DAR bir kopyasi.** Uc bagimsiz nedenle kapali:
  (a) likidite: $100M ustu 9,9 sembol, kitap 30 istiyor
  (b) dagilim: funding acikligi uzun vadede Binance'in yarisi
  (c) olculemezlik: public funding gecmisi 96 gun; sart 1 kurulamaz

(a) ve (b) YAPISALDIR - veri gelse de degismez. (c) bir gun kalkabilir:
OKX funding gecmisi birikerek uzuyor, 2027 ortasinda ~2 yil olur.
YENIDEN ACMA KOSULU: OKX funding gecmisi 2 YILI gectiginde ve $100M
ustu sembol sayisi 30'u astiginda - ikisi birden.

Kosum: python3 arastirma_ikinci_borsa.py
"""
import numpy as np
import pandas as pd

KOM = 0.0002
TPL_VAR = 0.40
TPS_VAR = 0.20
N_BACAK = 5
TUT_BAR = 30        # 5 gun x 6 bar
DILIM = 15


def bt(C, H, L, O, ODE, SIN, uy, tpl=TPL_VAR, tps=TPS_VAR, n=N_BACAK,
       tut=TUT_BAR, dilim=DILIM, kom=KOM, bas=200):
    """Basit kesitsel funding kitabi. Doner: gunluk getiri serisi.

    C/H/L/O: fiyat panelleri (bar x sembol), ODE: bar basina funding
    odemesi, SIN: siralama sinyali (dusuk -> LONG), uy: uygunluk maskesi.
    """
    cv, hv, lv, ov = C.values, H.values, L.values, O.values
    fv, S, U = ODE.values, SIN.values, uy.values
    nk = cv.shape[1]
    adim = max(1, tut // dilim)
    seriler = []
    for f in range(0, tut, adim):
        poz = np.zeros(nk); giris = np.full(nk, np.nan); eq = [1.0]; bek = None
        for i in range(bas + f, len(cv) - 1):
            if bek is not None and bek[0] == i:
                y = bek[1]
                eq[-1] *= 1 - np.abs(y - poz).sum() * kom
                poz = y; giris = np.where(y != 0, cv[i], np.nan); bek = None
            if (i - bas - f) % tut == 0:
                g = np.isfinite(S[i]) & np.isfinite(cv[i]) & U[i]
                ix = np.flatnonzero(g)
                if len(ix) >= 2 * n + 2:
                    o = np.argsort(S[i][ix])
                    lo, sh = ix[o[:n]], ix[o[-n:]]
                    y = np.zeros(nk); y[lo] = 0.5 / len(lo); y[sh] = -0.5 / len(sh)
                    bek = (i + 1, y)
            gec = np.isfinite(cv[i]) & np.isfinite(cv[i + 1])
            br = np.where(gec, (cv[i + 1] - cv[i]) / np.where(cv[i] == 0, np.nan, cv[i]), 0.0)
            br = np.nan_to_num(br)
            cik = np.zeros(nk, bool)
            for k in np.flatnonzero(poz != 0):
                e = giris[k]
                if not (np.isfinite(e) and e > 0 and np.isfinite(hv[i + 1, k])
                        and np.isfinite(lv[i + 1, k])):
                    continue
                uzun = poz[k] > 0
                t = tpl if uzun else tps
                if t <= 0:
                    continue
                sev = e * (1 + t) if uzun else e * (1 - t)
                if (uzun and hv[i + 1, k] >= sev) or ((not uzun) and lv[i + 1, k] <= sev):
                    # MADDE 249 HATA 1: ilk surum burada STOP konvansiyonunu
                    # (min(sev,op) if uzun else max(sev,op)) kullaniyordu. O
                    # konvansiyon g33.py'de DOGRUDUR cunku orada STOP var;
                    # stop ters tarafa gap atar. TP ise bir LIMIT emri. Ters
                    # hali `op ~ cv[i]` verip hasadi SILIYORDU (-%54,6).
                    # Motorun konvansiyonu: tam seviyeden dol.
                    br[k] = sev / cv[i, k] - 1
                    cik[k] = True
            fu = np.where(cik, 0.0, -poz * np.nan_to_num(fv[i + 1]))
            r = np.nansum(poz * br) + np.nansum(fu)
            eq.append(eq[-1] * (1 + r))
            if cik.any():
                eq[-1] *= 1 - np.abs(poz[cik]).sum() * kom
                poz = np.where(cik, 0.0, poz)
                giris = np.where(cik, np.nan, giris)
        seriler.append(pd.Series(eq, index=C.index[bas + f:bas + f + len(eq)]).pct_change())
    g = pd.concat(seriler, axis=1).mean(axis=1).dropna()
    return (1 + g).resample("1D").prod().dropna() - 1


def ozet(v):
    e = (1 + v).cumprod()
    return dict(yillik=(e.iloc[-1] ** (365.25 / len(v)) - 1) * 100,
                sharpe=v.mean() / v.std(ddof=1) * np.sqrt(365.25),
                dusus=-(e / e.cummax() - 1).min() * 100, gun=len(v))


# ---------------- 0) DOGRULAMA ----------------
# (yillik, gunluk Sharpe, dusus); motor = g33.py, HAVUZ=1 AKIS=0 UCELE=0
# REZERV=0, iki faz ortalamasi, 2022-07-20 -> 2026-08-31
DOGRULAMA = {
    "TP yok  motor (madde 238 A)": (72.5, 1.389, -34.8),
    "TP yok  bt()":                (73.2, 1.405, -33.1),
    "TP40/20 motor (madde 249)":   (64.5, 1.561, -28.7),
    "TP40/20 bt()":                (64.5, 1.551, -27.2),
}
TP_MERDIVENI = {   # bt(), Binance tam ornek - duzeltmeden SONRA
    "TP yok": (73.2, 1.405, -33.1), "TP 1000/1000": (73.2, 1.405, -33.1),
    "TP 300/90": (77.1, 1.479, -33.1), "TP 100/100": (79.2, 1.579, -31.2),
    "TP 40/20": (64.5, 1.551, -27.2),
}
TP_HATALI = (-54.6, -2.087, -96.3)   # ters dolum fiyatiyla, TP 40/20

# ---------------- 1) EVREN ----------------
OKX_EVREN = {"100M ustu": 9.9, "50M ustu": 16.0, "20M ustu": 28.6}
OKX_TOPLAM_SWAP = 485
BINANCE_EVREN = {"canli uygunluk (ayni pencere)": 34.4}
KITABIN_IHTIYACI = 30          # madde 226: taraf basina 15 aday
GENISLIK_TESTI = {"Binance kendi evreni": 61.8, "Binance OKX genisligine daraltilmis": 60.9}

# ---------------- 2) DAGILIM ----------------
# (kesitsel std, en yuksek 5 - en dusuk 5 yillik carry acikligi)
DAGILIM = {
    "OKX (2026-07/08)": (1.053, 1.523),
    "BINANCE (2026-07/08)": (3.614, 6.175),
    "BINANCE (2022-07 -> 2026-08)": (1.602, 3.100),
}
OKX_FUNDING_BACAGI = (59.9, 8.454, -0.1)    # 96 gun, yalniz funding
SINYAL_TANIMI_KIYASI = {"OKX formulu": (60.2, 1.474), "sk_bar48": (64.5, 1.551)}

# ---------------- 3) GUC ----------------
OKX_FUNDING_BASLANGIC = "2026-06-29"
OKX_KULLANILABILIR_GUN = 96
GUC_96GUN = {"ort": 1.737, "std": 2.132, "p5": -0.867, "p25": 0.244,
             "p50": 1.295, "p75": 2.632, "p95": 6.380, "negatif_olasilik": 21.1}
OKX_TAM_KITAP_96GUN = (-46.5, -1.683)       # YAYINLANMAZ - gurultu icinde
SHARPE_STD_HATASI = {96: 1.95, 180: 1.42, 365: 1.00, 730: 0.71, 1095: 0.58, 1500: 0.49}

YENIDEN_ACMA_KOSULU = ("OKX funding gecmisi 2 YILI gectiginde VE $100M ustu "
                       "sembol sayisi 30'u astiginda - ikisi birden")


def hukum_verilebilir_mi(gun=OKX_KULLANILABILIR_GUN, sembol=None):
    """Sart 1 bu evrende kurulabilir mi? (iki alt donem + yeterli guc)"""
    sembol = OKX_EVREN["100M ustu"] if sembol is None else sembol
    return gun >= 730 and sembol >= KITABIN_IHTIYACI


if __name__ == "__main__":
    print("MADDE 249 - IKINCI BORSA (OKX)\n")
    print("0) BACKTESTER DOGRULAMASI (gunluk baz, 2022-07-20 -> 2026-08-31)")
    print("  %-30s%9s%9s%9s" % ("", "yillik", "Sharpe", "dusus"))
    for a, (y, s, d) in DOGRULAMA.items():
        print("  %-30s%+9.1f%9.3f%9.1f" % (a, y, s, d))
    print("  ters dolum fiyatiyla TP 40/20: %+.1f / %.3f / %.1f  <- HATA 1"
          % TP_HATALI)
    print("\n  duzeltmeden sonra TP merdiveni:")
    for a, (y, s, d) in TP_MERDIVENI.items():
        print("    %-14s%+9.1f%9.3f%9.1f" % (a, y, s, d))

    print("\n1) OKX EVRENI (gunluk ort UYGUN sembol)")
    for a, v in OKX_EVREN.items():
        print("  %-12s%7.1f" % (a, v))
    for a, v in BINANCE_EVREN.items():
        print("  %-12s%7.1f  (Binance)" % (a, v))
    print("  kitabin ihtiyaci: %d sembol (madde 226)" % KITABIN_IHTIYACI)
    print("  genislik tek basina aciklama DEGIL:")
    for a, v in GENISLIK_TESTI.items():
        print("    %-38s%+7.1f%%" % (a, v))

    print("\n2) FUNDING DAGILIMI (ayni formul, ayni olcek)")
    print("  %-30s%12s%14s" % ("", "kesit std", "5-5 aciklik"))
    for a, (s, k) in DAGILIM.items():
        print("  %-30s%12.3f%14.3f" % (a, s, k))
    print("  -> OKX'in uzun vadeli adil kiyasi: Binance **%.2f KATI**"
          % (DAGILIM["BINANCE (2022-07 -> 2026-08)"][1] / DAGILIM["OKX (2026-07/08)"][1]))
    print("  mekanizma OKX'te VAR: funding bacagi %+.1f%% / Sharpe %.3f / dusus %.1f%%"
          % OKX_FUNDING_BACAGI)

    print("\n3) HUKUM VERILEBILIR MI?")
    print("  OKX public funding gecmisi %s'da basliyor -> %d GUN"
          % (OKX_FUNDING_BASLANGIC, OKX_KULLANILABILIR_GUN))
    print("  CALISAN Binance kitabinin rastgele %d gunluk pencereleri:"
          % OKX_KULLANILABILIR_GUN)
    print("    ort %+.3f  std %.3f  p5 %+.3f  p50 %+.3f  p95 %+.3f"
          % (GUC_96GUN["ort"], GUC_96GUN["std"], GUC_96GUN["p5"],
             GUC_96GUN["p50"], GUC_96GUN["p95"]))
    print("    NEGATIF gorunme olasiligi: %%%.1f" % GUC_96GUN["negatif_olasilik"])
    print("  OKX tam kitap 96 gun: %+.1f%% / Sharpe %.3f  <- YAYINLANMAZ"
          % OKX_TAM_KITAP_96GUN)
    print("  Sharpe standart hatasi:", ", ".join(
        "%dg~%.2f" % (g, s) for g, s in SHARPE_STD_HATASI.items()))
    print("\n  hukum verilebilir mi? %s" % ("EVET" if hukum_verilebilir_mi() else "HAYIR"))
    print("  YENIDEN ACMA KOSULU: %s" % YENIDEN_ACMA_KOSULU)
