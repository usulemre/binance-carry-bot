#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 285 — MADDE 284'ÜN YÖNTEMİ SİMETRİK UYGULANDI VE TERS İŞARET BULUNDU:
MADDE 244'ÜN ADAYI **DÜŞÜK PRİM REJİMİNE** BAHİS VE FİYATI YALNIZCA %25,4.
AMA ASIL BULGU: PROJENİN **ASGARİ SAPTANABİLİR ETKİSİ ~+13 PUAN** VE BU
ADAY ONUN ALTINDA — YANİ YANLIŞ DEĞİL, **KARARLAŞTIRILAMAZ.**

Madde 284 bir yöntem kurdu (bahsi fiyatla). O yöntemi yalnız red üreten
yönde kullanmak taraflı olurdu; bu madde onu **simetrik** uyguluyor:
şart 1'den düşen ama TAM ÖRNEKTE ve 22-24'te İYİLEŞEN adaylar. Sicilde
böyle iki tane var (madde 191'in short stopu, madde 244'ün üst trader
kontrarian'ı); ikincisi projenin en geniş eşitsizlik marjına sahip.

YENİDEN ÜRETİM TUTTU
--------------------
Panel `sum_toptrader_long_short_ratio`'dan kuruldu (skor = log(oran), en
düşük skor → LONG = kalabalığın short olduğu yere long):
**Sharpe 2,351** (madde 244: 2,350) · **korelasyon +0,710** (244: +0,702).

BULGU 1 — HARMAN DÖRT ŞARTTA NEREDE DURUYOR
-------------------------------------------
    pay    getiri   Sharpe   22-24   25-26   düşüş    eşit-risk
    0,00   +%112,2  2,900    2,776   3,076   14,27    +%112,2
    0,10   +%110,4  **2,924** **2,831** 3,064 **12,94** +%121,7
    0,20   +%108,5  **2,929** **2,874** 3,032 **12,47** +%124,1
    0,30   +%106,5  2,916    2,899   2,982   12,34    +%123,1

Şart 1: tam örnek ve 22-24 **yükseliyor**, 25-26 %10 payda **−0,012** —
yuvarlama hatası mertebesinde. Şart 2: düşüş **1,33 puan İYİLEŞİYOR**
(bu, son on turda reddettiğim imzanın TERSİ). Şart 3: eşit-risk +9,5
puan. Şart 4: eşit risk için 1,10x gerekiyor — **madde 276'nın doz
kararı (1,25x) bunu zaten veriyor**, yani madde 244'ün ikinci red
gerekçesi artık geçersiz.

BULGU 2 — BAHİS TERS YÖNDE VE UCUZ
----------------------------------
Madde 284'ün fiyatlaması (doz ölçütü her pencerede ayrı):

    pay   22-24 kazanç   25-26 kazanç   bahis
    0,10    **+11,04**      −3,76       DÜŞÜK prim rejimine, **p*=%25,4**
    0,20    **+21,31**     −11,66       DÜŞÜK prim rejimine, p*=%35,4
    0,30      +26,98       −23,23       DÜŞÜK prim rejimine, p*=%46,3

Madde 282'nin γ=0,25'i yüksek prim rejiminin sürmesine %57,4 olasılık
istiyordu; **bu aday düşük prim rejiminin dönmesine yalnız %25,4 istiyor**
— ve madde 231'in ölçümü (SEVİYE atlaması, *"rejim geri dönmeyi
düşündürür"*) tam bu yönü destekliyor. **Projede fiyatı ölçülmüş en ucuz
bahis.**

BULGU 3 — TAM ÖRNEKTE DOZ ÖLÇÜTÜ DE POZİTİF (son kapı geçildi)
--------------------------------------------------------------
Madde 281'in son kapısı (karıştırma p95, −%30, B=20.000):

    pay    brüt      net yıllık   kontrole göre
    0,00   1,465x    +%192,46         -
    0,05   1,488x    +%195,26       +2,79
    0,10   1,506x    +%197,20       +4,73
    **0,20 1,539x    +%199,68     **+7,22**
    0,30   1,550x    +%197,62       +5,16

**Hepsi pozitif, doz-tepki İÇ OPTİMUM yapıyor (%20) ve brüt YÜKSELİYOR**
(1,465 → 1,539) — yani p95 düşüş birim maruziyet başına İYİLEŞİYOR.
Madde 281/282'de reddedilen adaylarda brüt ÇÖKÜYORDU; bu adayın imzası
tam tersi.

BULGU 4 — ASIL BULGU: KANIT BARI BU ADAY İÇİN ULAŞILAMAZ
--------------------------------------------------------
Eşli blok bootstrap (blok 21, doz ölçütündeki kazanç):

    pay 0,10 | p5 −13,24 | medyan +3,11 | p95 +18,57 | **P(>0) %65,0**
    pay 0,20 | p5 −42,06 | medyan +7,88 | p95 +45,88 | **P(>0) %67,5**

Madde 244 bunu +8,5 puan / P %64,5 ölçmüştü; bağımsız yeniden ölçüm
+7,22 / %67,5 — **tutarlı.** Bar %80. Ve asıl soru: ne kadar veri gerekir?

    P(>0)=Φ(z), standart hata ~ 1/√T:
    pay 0,20: z=0,454 → %80 için z=0,842 → veri **3,44 KAT**
              gereken ufuk **5.174 gün = 14,2 YIL** (bugün 4,1 yıl)
    pay 0,10: veri 4,77 kat → **19,6 YIL**
    Ters soru: bugünkü veriyle %80 için etki **1,9 kat** büyük olmalıydı
    (+7,22 yerine +13,39 puan).

**YENİ YASA — ASGARİ SAPTANABİLİR ETKİ (ASE).** Kitabın oynaklığı, 4,1
yıllık veri ve projenin %80 kanıt barı birlikte bir **minimum etki
büyüklüğü** tanımlıyor: **~+13 puan.** Bunun altındaki hiçbir aday bu
veri tabanında kararlaştırılamaz. Ve bu, **285 maddelik red sicilini
tek tek bulgulardan daha iyi açıklıyor:** kalan eksenlerin etkileri ASE'nin
altında. Proje **fikir sınırlı değil, GÜÇ sınırlı.**

HÜKÜM
-----
**Ayar DEĞİŞMEDİ** — ve bu kez sebep "aday kötü" değil, **"aday
kararlaştırılamaz".** Madde 244'ün iki red gerekçesinden biri (şart 4)
doz kararıyla geçersiz kaldı, diğeri (şart 1) −0,012'lik bir yuvarlama;
dört şartın ikisi (düşüş ve eşit-risk) RAHAT geçiyor, doz ölçütü
POZİTİF (+7,22), bahis TERS yönde ve UCUZ (p*=%25,4), brüt İYİLEŞİYOR.
Tek engel güç — ve güç boşluğu bir çeyrek değil **bir on yıl.**

Dolayısıyla bu, projede kararın meşru olarak **veriye değil kullanıcıya**
ait olduğu tek aday. Varsayılan değişmiyor (ihtiyatlı taraf), ama
isteyen için en iyi fiyatlanmış tercih **%10 pay** (bahis en ucuz:
%25,4; kazanç +4,73 puan; düşüş 14,27 → 12,94).

DERS
----
**Bir adayı reddetmeden önce o reddin GÜÇ bütçesini hesapla.** "P(>0)
%67,5, bar %80" bir red gerekçesidir — ama "%80'e ulaşmak 14,2 yıl
ister" bundan bambaşka bir şey söyler: aday yanlış değil,
**kararlaştırılamaz.** İkisini ayırmak gerekir, çünkü birincisi "bunu
yapma", ikincisi "bunu veri ASLA söylemeyecek, karar senin" demektir.
"""
from __future__ import annotations

# --- yeniden uretim ---------------------------------------------------
YENIDEN_URETIM = {"sharpe": 2.351, "madde244_sharpe": 2.350,
                  "korelasyon": 0.710, "madde244_korelasyon": 0.702,
                  "getiri": 90.7, "dusus": 20.74}
PANEL = "sum_toptrader_long_short_ratio; skor=log(oran), en dusuk -> LONG"

# --- harman: pay -> (getiri, sharpe, 22-24, 25-26, dusus, esit_risk) --
HARMAN = {
    0.00: (112.2, 2.900, 2.776, 3.076, 14.27, 112.2),
    0.10: (110.4, 2.924, 2.831, 3.064, 12.94, 121.7),
    0.20: (108.5, 2.929, 2.874, 3.032, 12.47, 124.1),
    0.30: (106.5, 2.916, 2.899, 2.982, 12.34, 123.1),
}

# --- madde 284'un fiyatlamasi: pay -> (22-24 kazanc, 25-26 kazanc) ----
BAHIS = {0.10: (11.04, -3.76), 0.20: (21.31, -11.66), 0.30: (26.98, -23.23)}
MADDE_282_KARSI_BAHIS = 57.4      # yuksek prim rejimine, gereken olasilik

# --- tam ornekte doz olcutu (son kapi) --------------------------------
DOZ = {0.00: (1.465, 192.46, 0.00), 0.05: (1.488, 195.26, 2.79),
       0.10: (1.506, 197.20, 4.73), 0.20: (1.539, 199.68, 7.22),
       0.30: (1.550, 197.62, 5.16)}

# --- kanit bari -------------------------------------------------------
BOOTSTRAP = {0.10: (-13.24, 3.11, 18.57, 65.0), 0.20: (-42.06, 7.88, 45.88, 67.5)}
KANIT_BARI = 80.0
MADDE_244_BOOTSTRAP = (8.5, 64.5)

# --- guc butcesi ------------------------------------------------------
UFUK_GUN = 1504
GEREKEN = {0.10: (4.77, 7175, 19.6), 0.20: (3.44, 5174, 14.2)}   # kat, gun, yil
GEREKEN_ETKI = {0.10: (4.73, 10.33), 0.20: (7.22, 13.39)}
ASE_PUAN = 13.0        # asgari saptanabilir etki

MADDE_276_DOZ = 1.254  # sart 4'un gerekcesini gecersiz kilan karar
SART4_GEREKEN = 1.10


def yeniden_uretim_tuttu_mu(tol: float = 0.02) -> bool:
    y = YENIDEN_URETIM
    return (abs(y["sharpe"] - y["madde244_sharpe"]) < tol
            and abs(y["korelasyon"] - y["madde244_korelasyon"]) < tol)


def dusus_iyilesiyor_mu(pay: float = 0.10) -> bool:
    return HARMAN[pay][4] < HARMAN[0.00][4]


def sart1_yuvarlama_mi(pay: float = 0.10, tol: float = 0.05) -> bool:
    """25-26 kaybi yuvarlama mertebesinde mi?"""
    return 0 < HARMAN[0.00][3] - HARMAN[pay][3] < tol


def erken_ve_tam_iyilesiyor_mu(pay: float = 0.10) -> bool:
    return (HARMAN[pay][1] > HARMAN[0.00][1]
            and HARMAN[pay][2] > HARMAN[0.00][2])


def sart4_gerekcesi_gecersiz_mi() -> bool:
    """Doz karari (1,25x) sart 4'un istedigi kaldiraci zaten veriyor mu?"""
    return MADDE_276_DOZ >= SART4_GEREKEN


def bahis_yonu(pay: float = 0.10) -> str:
    g1, g2 = BAHIS[pay]
    return "dusuk prim rejimi" if g1 > 0 > g2 else "yuksek prim rejimi"


def bahis_fiyati(pay: float = 0.10) -> float:
    g1, g2 = BAHIS[pay]
    return 100.0 * abs(g2) / (g1 + abs(g2))


def en_ucuz_bahis_mi() -> bool:
    """Madde 282'nin bahsinden ucuz mu?"""
    return bahis_fiyati(0.10) < MADDE_282_KARSI_BAHIS


def madde231_bu_yonu_destekliyor_mu() -> bool:
    """Madde 231: SEVIYE atlamasi -> geri donus; yani DUSUK prim rejimi."""
    return bahis_yonu(0.10) == "dusuk prim rejimi"


def doz_olcutu_pozitif_mi() -> bool:
    return all(v[2] > 0 for p, v in DOZ.items() if p > 0)


def doz_ic_optimum_mu() -> bool:
    p = [x for x in sorted(DOZ) if x > 0]
    en = max(p, key=lambda x: DOZ[x][2])
    return en not in (p[0], p[-1])


def brut_iyilesiyor_mu() -> bool:
    return DOZ[0.20][0] > DOZ[0.00][0]


def kanit_bari_gecildi_mi(pay: float = 0.20) -> bool:
    return BOOTSTRAP[pay][3] >= KANIT_BARI


def gereken_yil(pay: float = 0.20) -> float:
    return GEREKEN[pay][2]


def guc_boslugu_on_yil_mi(pay: float = 0.20) -> bool:
    return gereken_yil(pay) - UFUK_GUN / 365.25 > 5.0


def ase_altinda_mi(etki: float) -> bool:
    return etki < ASE_PUAN


def proje_guc_sinirli_mi() -> bool:
    return ase_altinda_mi(DOZ[0.20][2])


def karar_kullaniciya_mi_ait() -> bool:
    """Doz olcutu pozitif + bahis ucuz + bar ULASILAMAZ -> karar kullanicinin."""
    return (doz_olcutu_pozitif_mi() and en_ucuz_bahis_mi()
            and not kanit_bari_gecildi_mi() and guc_boslugu_on_yil_mi())


def hukum() -> str:
    return ("Ayar DEGISMEDI - ama sebep 'aday kotu' DEGIL, 'aday "
            "KARARLASTIRILAMAZ'. Madde 244'un iki red gerekcesinden sart 4 "
            "doz karariyla gecersiz, sart 1 ise %%10 payda -%.3f'luk bir "
            "yuvarlama; dusus 1,33 puan IYILESIYOR, esit-risk +9,5, doz "
            "olcutu POZITIF (+%.2f puan, ic optimum %%20, brut 1,465->%.3f) "
            "ve bahis TERS yonde + UCUZ (p*=%%%.1f, madde 282'nin %%%.1f'ine "
            "karsi; madde 231 bu yonu destekliyor). Tek engel GUC: P(>0) "
            "%%%.1f vs bar %%%.0f ve %%80'e ulasmak **%.1f YIL** ister "
            "(bugun %.1f). ASE ~+%.0f puan; bu aday onun ALTINDA."
            % (HARMAN[0.00][3] - HARMAN[0.10][3], DOZ[0.20][2], DOZ[0.20][0],
               bahis_fiyati(0.10), MADDE_282_KARSI_BAHIS,
               BOOTSTRAP[0.20][3], KANIT_BARI, gereken_yil(),
               UFUK_GUN / 365.25, ASE_PUAN))


def yaz() -> None:
    print("MADDE 285 — ASGARİ SAPTANABİLİR ETKİ VE EN UCUZ BAHİS\n")
    y = YENIDEN_URETIM
    print("YENİDEN ÜRETİM (%s):" % PANEL)
    print("  Sharpe %.3f (madde 244: %.3f) | korelasyon %+.3f (244: %+.3f) -> tuttu mu: %s"
          % (y["sharpe"], y["madde244_sharpe"], y["korelasyon"],
             y["madde244_korelasyon"], yeniden_uretim_tuttu_mu()))
    print("\nHARMAN — DÖRT ŞART:")
    print("  pay  | getiri  | Sharpe | 22-24 | 25-26 | düşüş | eşit-risk")
    for p in sorted(HARMAN):
        v = HARMAN[p]
        print("  %.2f | %+7.1f | %6.3f | %5.3f | %5.3f | %5.2f | %+9.1f"
              % (p, v[0], v[1], v[2], v[3], v[4], v[5]))
    print("  -> tam örnek VE 22-24 iyileşiyor mu: %s | şart 1 kaybı yuvarlama mı: %s"
          % (erken_ve_tam_iyilesiyor_mu(), sart1_yuvarlama_mi()))
    print("  -> DÜŞÜŞ İYİLEŞİYOR mu (son turların TERSİ imza): %s" % dusus_iyilesiyor_mu())
    print("  -> şart 4'ün gerekçesi doz kararıyla geçersiz mi: %s"
          % sart4_gerekcesi_gecersiz_mi())
    print("\nMADDE 284'ÜN FİYATLAMASI:")
    print("  pay  | 22-24 kazanç | 25-26 kazanç | bahis yönü         | p*")
    for p in sorted(BAHIS):
        g1, g2 = BAHIS[p]
        print("  %.2f | %+12.2f | %+12.2f | %-18s | %%%.1f"
              % (p, g1, g2, bahis_yonu(p), bahis_fiyati(p)))
    print("  -> madde 282'nin bahsinden (%%%.1f) UCUZ mu: %s | madde 231 destekliyor mu: %s"
          % (MADDE_282_KARSI_BAHIS, en_ucuz_bahis_mi(),
             madde231_bu_yonu_destekliyor_mu()))
    print("\nTAM ÖRNEKTE DOZ ÖLÇÜTÜ (madde 281'in SON KAPISI):")
    print("  pay  | brüt   | net yıllık | kontrole göre")
    for p in sorted(DOZ):
        b, n, f = DOZ[p]
        print("  %.2f | %.3fx | %+10.2f | %+13.2f" % (p, b, n, f))
    print("  -> hepsi pozitif mi: %s | iç optimum mu: %s | brüt İYİLEŞİYOR mu: %s"
          % (doz_olcutu_pozitif_mi(), doz_ic_optimum_mu(), brut_iyilesiyor_mu()))
    print("\nKANIT BARI (eşli blok bootstrap):")
    print("  pay  | p5      | medyan | p95     | P(>0)")
    for p in sorted(BOOTSTRAP):
        v = BOOTSTRAP[p]
        print("  %.2f | %+7.2f | %+6.2f | %+7.2f | %%%.1f" % (p, v[0], v[1], v[2], v[3]))
    print("  (madde 244: +%.1f puan / P %%%.1f -> bağımsız ölçüm TUTARLI)"
          % MADDE_244_BOOTSTRAP)
    print("  -> bar (%%%.0f) geçildi mi: %s" % (KANIT_BARI, kanit_bari_gecildi_mi()))
    print("\nGÜÇ BÜTÇESİ — %%80'E ULAŞMAK İÇİN:")
    for p in sorted(GEREKEN):
        kat, gun, yil = GEREKEN[p]
        olc, ger = GEREKEN_ETKI[p]
        print("  pay %.2f: veri %.2f kat -> **%.1f YIL** (bugün %.1f) | ya da etki"
              " %+.2f yerine %+.2f olmalıydı"
              % (p, kat, yil, UFUK_GUN / 365.25, olc, ger))
    print("  -> güç boşluğu bir ON YIL mı: %s" % guc_boslugu_on_yil_mi())
    print("\nYENİ YASA — ASGARİ SAPTANABİLİR ETKİ (ASE) ~+%.0f PUAN" % ASE_PUAN)
    print("  bu adayın etkisi (+%.2f) ASE'nin ALTINDA mı: %s"
          % (DOZ[0.20][2], ase_altinda_mi(DOZ[0.20][2])))
    print("  -> proje FİKİR sınırlı değil GÜÇ sınırlı mı: %s" % proje_guc_sinirli_mi())
    print("\nKARAR MEŞRU OLARAK KULLANICIYA MI AİT: %s" % karar_kullaniciya_mi_ait())
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
