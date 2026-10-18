#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 282 — SİNYALİN BÜYÜKLÜĞÜ: RED, VE BU GİZLENMİŞ BİR BACAK AZALTMADIR.
MADDE 274/281'İN YASASI ÜÇÜNCÜ KEZ DOĞRULANDI (en büyük işaret dönüşü).

Kitabın çekirdeğinde kalan son sorgulanmamış varsayım: motor
`sc=rk(S[i][ix])` ile sinyalin yalnız **SIRALAMASINI** kullanıyor,
**BÜYÜKLÜĞÜNÜ atıyor.** Günlük −%0,3 funding ile −%3,0 funding aynı
muamele görüyor; büyüklük yalnız fırsat rezervi eşiğinde (`REZ_ESIK`)
devreye giriyor. Taraf içi ağırlığı `|S|^γ` yapmak hiç denenmedi.

MOTORA YENİ KOL + İKİ PARİTE (ikisi de BİREBİR geçti)
-----------------------------------------------------
`g33.py`'ye `AGIRLIK="buyukluk"` dalı ve `SK_GAMMA` eklendi; taraf
başına normalize edildiği için **dolar nötrlüğü ve brüt aynen korunuyor**
(madde 251'in yöntemi).
  * PARİTE 1 — kol kapalı yol: +%112,3 / Sh 3,10 / dd −14,5 ✔
  * PARİTE 2 — `AGIRLIK=buyukluk SK_GAMMA=0` (YENİ kod yolu, |S|^0=1 →
    eşit ağırlık): +%112,3 / Sh 3,10 / dd −14,5 ✔
İkinci parite kritik: yeni kod yolunun kendisinin doğru olduğunu
kanıtlıyor, yalnız "dokunmadığımız yol bozulmamış"ı değil.

ÖN KAYIT: γ ∈ {0,25; 0,5; 1,0; 2,0} × kırpma AG_KIRP ∈ {yok; 2,0}
= 8 aday (çokluk beyan edildi). Hüküm: dört şart + **madde 281'in yeni
yasası — oynaklığı değiştiren aday için SON KAPI doz ölçütüdür.**

BULGU 1 — GETİRİ FIRLIYOR, ŞART 1 SEKİZİNDE DE DÜŞÜYOR
------------------------------------------------------
    aday        getiri    Sharpe   22-24    25-26   düşüş   eşit-risk
    g0 (kontrol) +%112,2   2,900   2,776    3,076   14,27    +%112,2
    γ0,25       +%133,5   2,772   2,543    3,084   14,33    +%132,9
    γ0,5        +%151,4   2,604   2,293    3,009   16,50    +%131,0
    γ0,5 kırp2  +%148,6   2,681   2,400    3,054   15,24  **+%139,1**
    γ1,0        +%170,8   2,426   2,019    2,927   21,78    +%111,9
    γ1,0 kırp2  +%167,4   2,501   2,126    2,972   19,95    +%119,7
    γ2,0        +%187,0   2,365   1,879    2,946   24,79    +%107,6
    γ2,0 kırp2  +%181,7   2,386   1,931    2,935   24,13    +%107,5

Getiri +%112 → +%187'ye çıkıyor. Ama **22-24 Sharpe'ı γ ile MONOTON
yıkılıyor: 2,776 → 2,543 → 2,293 → 2,019 → 1,879.** Şart 1'i sekizinin
hiçbiri geçmiyor. Erken dönem yok ediliyor.

BULGU 2 — EŞİT RİSK YİNE KAYIRIYOR, DOZ ÖLÇÜTÜ HEPSİNİ REDDEDİYOR
-----------------------------------------------------------------
Maksimum düşüşle eşitlenince γ0,5-kırp2 **+%139,1 (+26,9 puan!)**
görünüyor. Doz kararının kendi ölçütüyle (madde 243 karıştırma p95,
B=20.000, −%30 toleransta):

    aday        brüt      net yıllık   kontrole göre
    **g0**      1,493x    **+%197,94**   **+0,00**
    γ0,25       1,272x      +%187,90      −10,05
    γ0,5 kırp2  1,133x      +%176,94    **−21,00**
    γ0,5        1,069x      +%165,78      −32,17
    γ1,0 kırp2  0,935x      +%151,39      −46,55
    γ1,0        0,874x      +%140,75      −57,19
    γ2,0 kırp2  0,809x      +%134,45      −63,50
    γ2,0        0,781x      +%131,92      −66,02

**Sekizinin sekizi de negatif, ve monoton.** γ0,5-kırp2'nin "+26,9
puanı" **−21,00**'e dönüyor: **48 puanlık işaret dönüşü** — projenin
gördüğü en büyük ölçüt bağımlılığı. Çözülen brüt de çöküyor (1,493x →
0,781x), yani yoğunlaşmış kitapların p95 düşüşü birim maruziyet başına
çok daha kötü.

BULGU 3 — MEKANİZMA: BU GİZLENMİŞ VE **DEĞİŞKEN** BİR BACAK AZALTMADIR
----------------------------------------------------------------------
Etkin isim sayısı (1/Σw², long tarafta 5 bacak, 1.500 bar örneği):

    γ      etkin N (medyan)   p10    en büyük bacağın TARAF payı
    0,00         5,00         5,00           %20,0
    0,25         4,69         4,00           %27,5
    0,50         4,01         2,75           %35,4
    1,00       **2,81**     **1,51**       **%50,0**
    2,00       **1,78**     **1,04**       **%71,8**

γ=1'de kitap etkin olarak **2,81 isme** iniyor — madde 281'de
reddettiğim L3_S3'ün 3,00'ına denk. Ama iki fark var ve ikisi de
aleyhte:
1. **Azaltma SABİT DEĞİL, DEĞİŞKEN:** p10'da etkin N **1,51** (γ=1) ve
   **1,04** (γ=2) — yani bazı barlarda kitap neredeyse TEK COİN.
2. **Yoğunlaşma tam olarak EN UÇ isme oluyor** ve madde 257 seçicinin
   zaten oynak coinlere 1,40 kat tilt yaptığını ölçmüştü → büyüklük
   ağırlığı o tilti çarpıyor.
Tek coin payı: γ=1'de taraf %50 = **brütün %25'i**; γ=2'de %71,8 =
**brütün %35,9'u**. Madde 192 bu eşiği **%16,7**'de reddetmişti (delist
riski) ve madde 266 nötr kitabın gün içi riskinin TEK İSİM riski
olduğunu ölçmüştü.

HÜKÜM
-----
**RED, üç bağımsız sebeple:** (1) şart 1'i sekizinin hiçbiri geçmiyor,
erken dönem Sharpe'ı monoton yıkılıyor; (2) doz ölçütünde sekizi de
negatif (−10 … −66 puan); (3) mekanizma, madde 192'nin reddettiği
yoğunlaşmanın iki katından fazlası. **Ayar DEĞİŞMEDİ** (`AGIRLIK`
varsayılanı `esit`, `SK_GAMMA` varsayılanı 0 → kitap birebir aynı).

KALICI KAZANÇ
-------------
Motor artık bu kolu TAŞIYOR ve iki pariteyle doğrulandı; soru kapandı
ama ölçüm aracı kaldı. Ve kitabın "sıralama kullan, büyüklüğü at"
tercihi artık bir ihmal değil **ölçülmüş bir karar**: büyüklük
bilgisini ağırlığa çevirmek, kitabı çeşitlendirmeden koparıyor.

DERS — ÖLÇÜT BAĞIMLILIĞI YASASININ ÜÇÜNCÜ DOĞRULANMASI
------------------------------------------------------
    madde   aday            maks-düşüş eşit-risk   doz ölçütü   dönüş
    274     rezerv 0,60         +5,80               +1,10       −4,7
    281     L3_S3              +13,90               −3,58      −17,5
    **282   γ0,5 kırp2        +26,90             −21,00      −47,9**

Üç turda üç kez, ve sapma adayın oynaklık artışıyla BÜYÜYOR. Yasa artık
kesin: **maksimum düşüşle eşitlenmiş "eşit risk" bir KABUL gerekçesi
değildir; oynaklığı değiştiren her aday son olarak doz ölçütünden
geçmek zorundadır.** Bu filtre bundan sonraki turları hem ucuzlatıyor
hem dürüstleştiriyor.
"""
from __future__ import annotations

# --- motora eklenen kol -----------------------------------------------
YENI_KOL = {"ad": "AGIRLIK=buyukluk", "parametre": "SK_GAMMA",
            "varsayilan": 0.0, "dosya": "g33.py",
            "notrluk": "taraf basina normalize -> dolar notrlugu ve brut AYNEN korunur"}
PARITE = {   # ad -> (getiri, sharpe, dusus)
    "kol_kapali": (112.3, 3.10, -14.5),
    "yeni_yol_gamma0": (112.3, 3.10, -14.5),
}
KONTROL_MOTOR = (112.3, 3.10, -14.5)

# --- izgara: aday -> (getiri, sharpe, 22-24, 25-26, dusus, esit_risk) --
IZGARA = {
    "g0_k0": (112.2, 2.900, 2.776, 3.076, 14.27, 112.2),
    "g0.25_k0": (133.5, 2.772, 2.543, 3.084, 14.33, 132.9),
    "g0.5_k0": (151.4, 2.604, 2.293, 3.009, 16.50, 131.0),
    "g0.5_k2.0": (148.6, 2.681, 2.400, 3.054, 15.24, 139.1),
    "g1.0_k0": (170.8, 2.426, 2.019, 2.927, 21.78, 111.9),
    "g1.0_k2.0": (167.4, 2.501, 2.126, 2.972, 19.95, 119.7),
    "g2.0_k0": (187.0, 2.365, 1.879, 2.946, 24.79, 107.6),
    "g2.0_k2.0": (181.7, 2.386, 1.931, 2.935, 24.13, 107.5),
}
KONTROL = "g0_k0"
BAKIS = 8

# --- doz olcutu (madde 243 karistirma p95, B=20.000, -%30) ------------
DOZ = {   # aday -> (brut, net_yillik, kontrole_gore)
    "g0_k0": (1.493, 197.94, 0.00),
    "g0.25_k0": (1.272, 187.90, -10.05),
    "g0.5_k2.0": (1.133, 176.94, -21.00),
    "g0.5_k0": (1.069, 165.78, -32.17),
    "g1.0_k2.0": (0.935, 151.39, -46.55),
    "g1.0_k0": (0.874, 140.75, -57.19),
    "g2.0_k2.0": (0.809, 134.45, -63.50),
    "g2.0_k0": (0.781, 131.92, -66.02),
}

# --- mekanizma: etkin isim sayisi -------------------------------------
ETKIN = {   # gamma -> (etkin_N_medyan, etkin_N_p10, en_buyuk_taraf_pay_pct)
    0.00: (5.00, 5.00, 20.0),
    0.25: (4.69, 4.00, 27.5),
    0.50: (4.01, 2.75, 35.4),
    1.00: (2.81, 1.51, 50.0),
    2.00: (1.78, 1.04, 71.8),
}
MADDE_281_L3S3_ETKIN = 3.00
MADDE_192_RED_ESIGI_BRUT = 16.7     # tek coin brutun yuzde kaci
MADDE_257_OYNAKLIK_TILT = 1.40

# --- olcut bagimliligi yasasinin uc dogrulanmasi ----------------------
YASA = {   # madde -> (aday, maks_dusus_esit_risk_puan, doz_olcutu_puan)
    274: ("rezerv 0,60", 5.80, 1.10),
    281: ("L3_S3", 13.90, -3.58),
    282: ("gamma 0,5 kirp 2", 26.90, -21.00),
}


def parite_gecti_mi(tol: float = 0.05) -> bool:
    """Iki parite de kontrolu BIREBIR verdi mi?"""
    return all(abs(v[0] - KONTROL_MOTOR[0]) < tol
               and abs(v[1] - KONTROL_MOTOR[1]) < tol
               and abs(v[2] - KONTROL_MOTOR[2]) < tol for v in PARITE.values())


def yeni_kod_yolu_dogrulandi_mi() -> bool:
    """Kritik olan: YENI kod yolu gamma=0'da kontrolu veriyor mu?"""
    v = PARITE["yeni_yol_gamma0"]
    return abs(v[0] - KONTROL_MOTOR[0]) < 0.05


def getiri_firliyor_mu() -> bool:
    return max(v[0] for v in IZGARA.values()) > 1.5 * IZGARA[KONTROL][0]


def sart1_gecen() -> list:
    k = IZGARA[KONTROL]
    return [a for a, v in IZGARA.items()
            if a != KONTROL and v[2] > k[2] and v[3] > k[3]]


def erken_donem_monoton_yikiliyor_mu() -> bool:
    """22-24 Sharpe'i gamma ile monoton dusuyor mu?"""
    sira = ["g0_k0", "g0.25_k0", "g0.5_k0", "g1.0_k0", "g2.0_k0"]
    v = [IZGARA[a][2] for a in sira]
    return all(v[i] > v[i + 1] for i in range(len(v) - 1))


def esit_riskte_ustun_gorunen() -> list:
    k = IZGARA[KONTROL][5]
    return [a for a, v in IZGARA.items() if v[5] > k + 5.0]


def doz_olcutunde_pozitif_var_mi() -> bool:
    return any(v[2] > 0 for a, v in DOZ.items() if a != KONTROL)


def doz_monoton_mu() -> bool:
    """Doz olcutundeki kayip gamma ile buyuyor mu?"""
    sira = ["g0.25_k0", "g0.5_k0", "g1.0_k0", "g2.0_k0"]
    v = [DOZ[a][2] for a in sira]
    return all(v[i] > v[i + 1] for i in range(len(v) - 1))


def gizlenmis_bacak_azaltma_mi() -> bool:
    """gamma buyudukce etkin isim sayisi dusuyor mu?"""
    g = sorted(ETKIN)
    return all(ETKIN[g[i]][0] > ETKIN[g[i + 1]][0] for i in range(len(g) - 1))


def azaltma_degisken_mi(esik: float = 2.0) -> bool:
    """Etkin N bazi barlarda tek coine mi iniyor? (p10)"""
    return any(v[1] < esik for v in ETKIN.values())


def tek_coin_brut_payi(gamma: float) -> float:
    """Taraf payi -> brut payi (taraf brutun yarisi)."""
    return ETKIN[gamma][2] / 2.0


def yogunlasma_madde192yi_asiyor_mu(gamma: float = 1.0) -> bool:
    return tek_coin_brut_payi(gamma) > MADDE_192_RED_ESIGI_BRUT


def yasa_kac_kez_dogrulandi() -> int:
    return len(YASA)


def sapma_oynaklikla_buyuyor_mu() -> bool:
    """Esit-risk ile doz olcutu arasindaki fark turlar boyunca buyuyor mu?"""
    d = [abs(v[1] - v[2]) for v in YASA.values()]
    return all(d[i] < d[i + 1] for i in range(len(d) - 1))


def ayar_degismedi_mi() -> bool:
    return YENI_KOL["varsayilan"] == 0.0


def hukum() -> str:
    return ("RED, uc bagimsiz sebeple: (1) sart 1'i %d adayin HICBIRI "
            "gecmiyor ve 22-24 Sharpe'i monoton yikiliyor (%.3f -> %.3f); "
            "(2) doz olcutunde sekizi de NEGATIF (%+.2f ... %+.2f puan); "
            "(3) mekanizma gizlenmis ve DEGISKEN bacak azaltma - gamma=1'de "
            "etkin isim %.2f, p10'da %.2f, tek coin brutun %%%.1f'i "
            "(madde 192'nin red esigi %%%.1f). Ayar DEGISMEDI."
            % (BAKIS, IZGARA["g0_k0"][2], IZGARA["g2.0_k0"][2],
               max(v[2] for a, v in DOZ.items() if a != KONTROL),
               min(v[2] for v in DOZ.values()),
               ETKIN[1.0][0], ETKIN[1.0][1], tek_coin_brut_payi(1.0),
               MADDE_192_RED_ESIGI_BRUT))


def yaz() -> None:
    print("MADDE 282 — SİNYALİN BÜYÜKLÜĞÜ (|S|^γ ağırlık)\n")
    print("MOTORA EKLENEN KOL: %s / %s (varsayılan %.1f)"
          % (YENI_KOL["ad"], YENI_KOL["parametre"], YENI_KOL["varsayilan"]))
    print("  %s" % YENI_KOL["notrluk"])
    print("\nİKİ PARİTE:")
    for a, v in PARITE.items():
        print("  %-18s +%%%.1f / Sh %.2f / dd %.1f" % (a, v[0], v[1], v[2]))
    print("  -> ikisi de BİREBİR mi: %s | YENİ kod yolu doğrulandı mı: %s"
          % (parite_gecti_mi(), yeni_kod_yolu_dogrulandi_mi()))
    print("\nİZGARA (%d aday, çokluk beyan edildi):" % BAKIS)
    print("  aday        | getiri  | Sharpe | 22-24 | 25-26 | düşüş | eşit-risk")
    for a in sorted(IZGARA, key=lambda x: IZGARA[x][0]):
        v = IZGARA[a]
        print("  %-11s | %+7.1f | %6.3f | %5.3f | %5.3f | %5.2f | %+9.1f"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5]))
    print("  -> getiri fırlıyor mu: %s | şart 1'i geçen: %s"
          % (getiri_firliyor_mu(), sart1_gecen() or "YOK"))
    print("  -> erken dönem (22-24) MONOTON yıkılıyor mu: %s"
          % erken_donem_monoton_yikiliyor_mu())
    print("  -> eşit riskte üstün GÖRÜNEN: %s" % esit_riskte_ustun_gorunen())
    print("\nDOZ ÖLÇÜTÜ — MADDE 281'İN YASASI GEREĞİ SON KAPI:")
    print("  aday        | brüt   | net yıllık | kontrole göre")
    for a in sorted(DOZ, key=lambda x: -DOZ[x][1]):
        b, n, f = DOZ[a]
        print("  %-11s | %.3fx | %+10.2f | %+13.2f" % (a, b, n, f))
    print("  -> pozitif var mı: %s | kayıp γ ile MONOTON büyüyor mu: %s"
          % (doz_olcutunde_pozitif_var_mi(), doz_monoton_mu()))
    print("\nMEKANİZMA — ETKİN İSİM SAYISI (1/Σw², long tarafta 5 bacak):")
    print("  γ     | etkin N medyan | p10  | en büyük bacağın TARAF payı | BRÜT payı")
    for g in sorted(ETKIN):
        m, p10, pay = ETKIN[g]
        print("  %5.2f | %14.2f | %4.2f | %%%24.1f | %%%.1f"
              % (g, m, p10, pay, tek_coin_brut_payi(g)))
    print("  -> gizlenmiş bacak azaltma mı: %s | azaltma DEĞİŞKEN mi (p10<2): %s"
          % (gizlenmis_bacak_azaltma_mi(), azaltma_degisken_mi()))
    print("  -> γ=1 yoğunlaşması madde 192'nin %%%.1f red eşiğini aşıyor mu: %s"
          % (MADDE_192_RED_ESIGI_BRUT, yogunlasma_madde192yi_asiyor_mu()))
    print("  (madde 281'de L3_S3 etkin N = %.2f; madde 257: seçici zaten oynak"
          " coinlere %.2f kat tilt yapıyor)"
          % (MADDE_281_L3S3_ETKIN, MADDE_257_OYNAKLIK_TILT))
    print("\nÖLÇÜT BAĞIMLILIĞI YASASI — ÜÇ DOĞRULANMA:")
    print("  madde | aday              | maks-düşüş eşit-risk | doz ölçütü | dönüş")
    for m, (ad, e, d) in YASA.items():
        print("  %5d | %-17s | %+20.2f | %+10.2f | %+6.2f" % (m, ad, e, d, d - e))
    print("  -> kaç kez doğrulandı: %d | sapma oynaklıkla BÜYÜYOR mu: %s"
          % (yasa_kac_kez_dogrulandi(), sapma_oynaklikla_buyuyor_mu()))
    print("\nAYAR DEĞİŞMEDİ Mİ: %s" % ayar_degismedi_mi())
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
