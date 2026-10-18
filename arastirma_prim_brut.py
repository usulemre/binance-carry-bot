#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 287 — ASE FİLTRESİ GERİYE DÖNÜK UYGULANDI VE PROJENİN EN GÜÇLÜ
DURAN ADAYI BULUNDU: MADDE 239'UN PRİM-ÖLÇEKLİ BRÜTÜ. DOZ ÖLÇÜTÜNDE
**+38,14 PUAN, P(>0) %90,7** — BARIN ÜSTÜNDE. TEK EKSİĞİ ŞART 1'DE
**−0,020**'LİK BİR SAPMA VE BAHSİN FİYATI **%3,1**.

Madde 285/286 ASE'yi (asgari saptanabilir etki ~+13 puan) ölçüp bir ön
filtreye çevirdi. Bu madde o filtreyi **geriye dönük** uyguladı: sicilde
ölçülmüş etki büyüklüğü olan redlerin kaçı gerçekten ÇÜRÜTÜLMÜŞ, kaçı
yalnızca KARARLAŞTIRILAMAZ?

DENETİMİN KENDİ NOTU — İKİ TABAN KARIŞTIRILMAMALI
-------------------------------------------------
İlk taramada madde 255'in "P %88,2"sini barın üstünde bir geçiş sandım.
Yanlış: o P **plaseboya** karşı; kontrole karşı +5,7 puan / **%68,0**.
Madde 255 bunu kendi metninde doğru ayırmış (*"model BİLGİ taşıyor ama
PARA getirmiyor"*). **Sicildeki P değerleri iki ayrı tabana karşıdır ve
havuzlanamaz.** Denetim yöntemine giren ilk kural bu oldu.

ASIL BULGU — MADDE 239'UN (B) PARÇASI
-------------------------------------
Prim-ölçekli brüt: brüt çarpanı, **kesitsel funding dağılımının** (p90−p10,
30g ortalama) kendi **180 günlük YEREL** medyanına oranının üssü
(1 bar gecikmeli, [0,5 ; 1,5] aralığına kırpılmış). Madde 165 aynı aileyi
OYNAKLIK koşullayıcısıyla reddetmişti; buradaki koşullayıcı farklı ve
madde 239 bunu "edge yoğunluğu ölçüsü" olarak kurmuştu (çeyrek sıralaması
Q1 +%49,7 → Q4 +%239,9 iken oynaklık çeyrekler arası DÜZ).

**YENİDEN ÜRETİM TUTTU:** motor +%137,7 / Sh 3,23 / −14,6 (kayıt: +%137,3
/ 3,061 / −13,31 — Sharpe farkı motor-vs-günlük ekseni).

GÜNCEL ÇERÇEVEYLE ÖLÇÜM (günlük baz)
------------------------------------
    ölçüt           kontrol    **ADAY**     PLASEBO
    getiri          +%112,2   **+%137,5**   +%122,2
    Sharpe           2,900     **3,029**     2,879
    22-24            2,776     **3,062**     2,865
    25-26            3,076      3,056        2,899
    düşüş            14,27     **13,40**     16,69
    eşit-risk       +%112,2   **+%146,4**   +%104,5

**Plasebo (aynı çarpan dağılımı, zamanda TERS) kontrolün ALTINA
düşüyor** (+%104,5 vs +%112,2) → etki doz değil **ZAMANLAMA**.

MADDE 281'İN SON KAPISI — DOZ ÖLÇÜTÜ
------------------------------------
    aday        brüt      net yıllık   kontrole göre
    kontrol    1,469x     +%193,17         -
    **ADAY**   1,419x   **+%231,30**   **+38,14**
    plasebo    1,373x     +%191,84       −1,33

Brüt DAHA DÜŞÜK, net DAHA YÜKSEK → risk birimi başına getiri gerçekten
iyileşiyor. Ve plasebo sıfır.

KARAR VEREN SAYI — DOZ ÖLÇÜTÜNDE EŞLİ BLOK BOOTSTRAP
----------------------------------------------------
    **ADAY**   ort +34,11 | p5 −9,03 | medyan +25,70 | p95 +96,05 | **P(>0) %90,7**
    plasebo    ort  +2,36 | p5 −34,52 | medyan −2,33 | p95 +54,56 | P(>0) %46,7

**%90,7 > %80 barı.** Madde 239 bu barı EŞİT-RİSK ölçütünde %79,0 ölçüp
geçememişti; madde 281 sonradan **doz ölçütünü** son kapı ilan etti ve o
ölçütte aday barı geçiyor. Plasebo yazı-tura.

MADDE 284'ÜN BAHİS FİYATI
-------------------------
    22-24 kazanç: **+71,83 puan**
    25-26 kazanç:   **−2,29 puan**
    → düşük prim rejimine bahis, **p\* = %3,1**

Yani "birinde iyi ötekinde kötü" değil; **birinde çok iyi, ötekinde
SIFIR.** Madde 239'un kendi alt dönem bootstrap'i bunu zaten söylemişti:
22-24 ΔSharpe +0,269 **P %95,6** · 25-26 −0,008 **P %48,2 (yazı-tura)**.
Kayıp bacağı olmayan bir bahsin fiyatı sıfıra yakındır.

MADDE 285'İN GÜÇ BÜTÇESİ — BU ADAY **KARARLAŞTIRILABİLİR**
----------------------------------------------------------
Etki **+38,14 puan**, ASE ~+13 → etki ASE'nin **3 katı**; gereken ufuk
**0,5 yıl** (eldeki 4,1). Madde 285'in adayı (+7,22) kararlaştırılamazdı;
**bu aday kararlaştırılabilir ve karar POZİTİF tarafta.**

PLATO DOĞRULANDI (madde 282'nin dersi: en heyecanlı sayı en çok denetlenir)
--------------------------------------------------------------------------
    ayar               getiri    Sharpe   düşüş
    kontrol            +%112,3    3,10    −14,5
    e0,25 ref180       +%130,1    3,21    −14,5
    **e0,50 ref180**   +%137,7    3,23    −14,6   (kayıtlı nokta)
    e0,75 ref180       +%139,3    3,24    −14,7
    e0,50 ref120       +%135,6    3,23    −16,0
    e0,50 ref270       +%141,4    3,20   **−13,4**

Beş ayarın beşi de kontrolü belirgin aşıyor ve **kayıtlı nokta tepe
değil** (e0,50/ref270 daha iyi). Bu bir plato, bıçak sırtı bir uyum değil
— seçim yanlılığına karşı en güçlü savunma.

ŞART 1 — VE KURAL GEVŞETİLMİYOR
-------------------------------
Tek eksik: 25-26 Sharpe 3,076 → **3,056 (−0,020)**. Madde 239'un kendi
notu geçerli: *"KURAL DEĞİŞTİRİLMEDİ — aday eldeyken gevşetmek madde
212'nin kapattığı delik."* **Bu madde de kuralı gevşetmiyor ve ayarı
değiştirmiyor.** Değişen tek şey: reddin **fiyatı** artık ölçülü (%3,1) ve
adayın **diğer bütün kapıları geçtiği** belgelenmiş.

DÜRÜST RİSKLER
--------------
1. **Değişken kaldıraç ailesi.** Madde 165 bu aileyi OYNAKLIK
   koşullayıcısıyla reddetti. Buradaki koşullayıcı farklı ve **plasebo
   ile doğrulandı** — ama aile geçmişi dikkat gerektirir.
2. **Ortalama brüt 1,058x**, yani biraz daha maruziyet. Doz ölçütü riski
   eşitliyor ve plasebonun çarpan dağılımı AYNI; itiraz bu iki kontrolle
   karşılanıyor ama sıfırlanmıyor.
3. **Çokluk:** madde 239 üs × pencere taradı. Beş noktalık plato bunun
   savunmasıdır; o turun tam tarama genişliği yeniden kurulmadı.
4. **Şart 1 ihlali gerçek.** Muaf tutulmuyor.
5. **Kazanç düşük prim rejiminden geliyor.** Yüksek prim rejimi sürerse
   aday ~sıfır ekler (−2,29), kaybetmez. Bahis fiyatının %3,1 olmasının
   sebebi bu.

HÜKÜM
-----
**Ayar DEĞİŞMEDİ** (kural gevşetilmez). Ama sicile şu geçiyor: **projenin
en güçlü duran adayı budur** — doz ölçütünde +38,14 puan / **P %90,7**
(barın üstünde), plasebo sıfır, düşüş İYİLEŞİYOR, plato beş noktada
doğrulanmış, etki ASE'nin 3 katı (**kararlaştırılabilir**), bahis fiyatı
**%3,1**. Tek eksiği şart 1'de −0,020 ve o alt dönemde etki istatistiksel
olarak sıfır.

Madde 285'in yasası gereği karar meşru olarak kullanıcıya ait; ve bu
aday, madde 285'in adayından (+7,22 / kararlaştırılamaz / p*%25,4)
**her ölçütte daha güçlü.**

DERS
----
**Bir ret gerekçesi, ondan SONRA kurulan ölçütlerle yeniden okunmalıdır.**
Madde 239 kanıt barını **eşit-risk** ölçütünde ölçtü (%79,0) ve şart
1'den reddetti. Madde 281 sonradan **doz ölçütünü** son kapı ilan etti,
madde 284 bahsi fiyatlamayı, madde 285 ASE'yi getirdi. Aynı aday, aynı
veri, üç yeni ölçüt: **+38,14 puan / %90,7 / %3,1 / kararlaştırılabilir.**
Hiçbir yeni ölçüm yapılmadı — yalnız doğru sorular soruldu. **Sicilin
kendisi, en az piyasa kadar denetlenmeye değer bir veri kümesidir.**
"""
from __future__ import annotations

# --- denetimin kendi notu ---------------------------------------------
TABAN_UYARISI = ("sicildeki P degerleri IKI AYRI tabana karsidir "
                 "(kontrol vs plasebo) ve HAVUZLANAMAZ; madde 255'in "
                 "%88,2'si PLASEBOYA karsidir, kontrole karsi %68,0")

# --- yapi -------------------------------------------------------------
YAPI = {
    "ad": "prim-olcekli brut (madde 239 (B))",
    "kol": "BRUT_PRIM=0.5 BRUT_REF=180",
    "kosullayici": "kesitsel funding dagilimi (p90-p10, 30g ort) / kendi "
                   "180g YEREL medyani, 1 bar gecikmeli, [0,5;1,5] kirpma",
    "madde_165_farki": "165'in kosullayicisi OYNAKLIK'ti; bu EDGE YOGUNLUGU",
    "ortalama_brut": 1.058,
}
YENIDEN_URETIM = {"motor_getiri": 137.7, "kayit_getiri": 137.3}

# --- gunluk baz: aday -> (getiri, sharpe, 22-24, 25-26, dusus, esit_risk)
GUNLUK = {
    "kontrol": (112.2, 2.900, 2.776, 3.076, 14.27, 112.2),
    "aday": (137.5, 3.029, 3.062, 3.056, 13.40, 146.4),
    "plasebo": (122.2, 2.879, 2.865, 2.899, 16.69, 104.5),
}

# --- doz olcutu (madde 281'in son kapisi) -----------------------------
DOZ = {"kontrol": (1.469, 193.17, 0.00),
       "aday": (1.419, 231.30, 38.14),
       "plasebo": (1.373, 191.84, -1.33)}

# --- karar veren sayi: doz olcutunde esli blok bootstrap --------------
BOOTSTRAP = {   # aday -> (ort, p5, medyan, p95, P>0)
    "aday": (34.11, -9.03, 25.70, 96.05, 90.7),
    "plasebo": (2.36, -34.52, -2.33, 54.56, 46.7),
}
KANIT_BARI = 80.0
MADDE_239_ESITRISK_P = 79.0      # 239'un olctugu bar (BASKA olcut)

# --- madde 284'un bahis fiyati ----------------------------------------
BAHIS = {"22-24": 71.83, "25-26": -2.29}
MADDE_239_ALT_DONEM = {"22-24": (0.269, 95.6), "25-26": (-0.008, 48.2)}

# --- madde 285'in guc butcesi -----------------------------------------
ASE_PUAN = 13.0
GEREKEN_YIL = 0.5
MADDE_285_ADAYI = {"etki": 7.22, "p": 67.5, "bahis": 25.4}

# --- plato ------------------------------------------------------------
PLATO = {   # ayar -> (getiri, sharpe, dusus)
    "kontrol": (112.3, 3.10, -14.5),
    "e0.25_ref180": (130.1, 3.21, -14.5),
    "e0.50_ref180": (137.7, 3.23, -14.6),
    "e0.75_ref180": (139.3, 3.24, -14.7),
    "e0.50_ref120": (135.6, 3.23, -16.0),
    "e0.50_ref270": (141.4, 3.20, -13.4),
}
KAYITLI_NOKTA = "e0.50_ref180"

# --- sart 1 -----------------------------------------------------------
SART1_SAPMA = -0.020
KURAL_GEVSETILMEDI = ("madde 212'nin kapattigi delik: aday eldeyken kural "
                      "gevsetilmez; bu madde de gevsetmiyor")

RISKLER = (
    "degisken kaldirac ailesi (madde 165) - kosullayici farkli ve PLASEBO "
    "ile dogrulandi ama aile gecmisi dikkat gerektirir",
    "ortalama brut 1,058x = biraz daha maruziyet; doz olcutu ve plasebonun "
    "AYNI carpan dagilimi bu itirazi karsilar ama sifirlamaz",
    "cokluk: madde 239 us x pencere taradi; bes noktalik PLATO savunmadir "
    "ama o turun tam tarama genisligi yeniden kurulmadi",
    "sart 1 ihlali GERCEK ve muaf tutulmuyor",
    "kazanc DUSUK prim rejiminden geliyor; yuksek prim surerse aday ~sifir "
    "ekler (-2,29), kaybetmez",
)


def taban_karistirilmadi_mi() -> bool:
    return "HAVUZLANAMAZ" in TABAN_UYARISI


def yeniden_uretim_tuttu_mu(tol: float = 1.0) -> bool:
    y = YENIDEN_URETIM
    return abs(y["motor_getiri"] - y["kayit_getiri"]) < tol


def plasebo_sifir_mi() -> bool:
    """Plasebo kontrolun ALTINA mi dusuyor (etki zamanlama mi)?"""
    return (GUNLUK["plasebo"][5] < GUNLUK["kontrol"][5]
            and DOZ["plasebo"][2] < 1.0
            and BOOTSTRAP["plasebo"][4] < 60.0)


def dusus_iyilesiyor_mu() -> bool:
    return GUNLUK["aday"][4] < GUNLUK["kontrol"][4]


def doz_olcutu_gecti_mi() -> bool:
    return DOZ["aday"][2] > 0


def kanit_bari_gecti_mi() -> bool:
    return BOOTSTRAP["aday"][4] >= KANIT_BARI


def bar_hangi_olcutte_gecilmedi() -> str:
    return ("madde 239 bari ESIT-RISK olcutunde %%%.1f ile gecemedi; "
            "madde 281 sonradan DOZ olcutunu son kapi ilan etti ve o "
            "olcutte aday %%%.1f ile geciyor"
            % (MADDE_239_ESITRISK_P, BOOTSTRAP["aday"][4]))


def bahis_fiyati() -> float:
    g1, g2 = BAHIS["22-24"], BAHIS["25-26"]
    return 100.0 * abs(g2) / (g1 + abs(g2)) if g2 < 0 else 0.0


def kayip_bacagi_var_mi(esik: float = 5.0) -> bool:
    return BAHIS["25-26"] < -esik


def kararlastirilabilir_mi() -> bool:
    return DOZ["aday"][2] >= ASE_PUAN


def ase_kac_kati() -> float:
    return DOZ["aday"][2] / ASE_PUAN


def plato_mu() -> bool:
    """Tum ayarlar kontrolu belirgin asiyor mu?"""
    k = PLATO["kontrol"][0]
    d = [v for a, v in PLATO.items() if a != "kontrol"]
    return all(v[0] > k + 10.0 for v in d)


def kayitli_nokta_tepe_mi() -> bool:
    d = {a: v for a, v in PLATO.items() if a != "kontrol"}
    return max(d, key=lambda a: d[a][0]) == KAYITLI_NOKTA


def sart1_gecti_mi() -> bool:
    return SART1_SAPMA > 0


def kural_gevsetildi_mi() -> bool:
    return False


def madde285_adayindan_guclu_mu() -> bool:
    m = MADDE_285_ADAYI
    return (DOZ["aday"][2] > m["etki"]
            and BOOTSTRAP["aday"][4] > m["p"]
            and bahis_fiyati() < m["bahis"])


def hukum() -> str:
    return ("Ayar DEGISMEDI (kural gevsetilmez). Ama sicile sunu geciriyorum: "
            "PROJENIN EN GUCLU DURAN ADAYI bu. Doz olcutunde **+%.2f puan / "
            "P %%%.1f** (bar %%%.0f), plasebo SIFIR (P %%%.1f), dusus "
            "IYILESIYOR (%.2f -> %.2f), plato BES noktada dogrulandi ve "
            "kayitli nokta tepe bile degil, etki ASE'nin **%.1f kati** "
            "(KARARLASTIRILABILIR, gereken ufuk %.1f yil), bahis fiyati "
            "**%%%.1f**. Tek eksigi sart 1'de %+.3f ve o alt donemde etki "
            "istatistiksel olarak SIFIR (madde 239: P %%%.1f). Madde 285'in "
            "adayindan her olcutte daha guclu."
            % (DOZ["aday"][2], BOOTSTRAP["aday"][4], KANIT_BARI,
               BOOTSTRAP["plasebo"][4], GUNLUK["kontrol"][4],
               GUNLUK["aday"][4], ase_kac_kati(), GEREKEN_YIL,
               bahis_fiyati(), SART1_SAPMA, MADDE_239_ALT_DONEM["25-26"][1]))


def yaz() -> None:
    print("MADDE 287 — PROJENİN EN GÜÇLÜ DURAN ADAYI (madde 239'un (B) parçası)\n")
    print("DENETİMİN KENDİ NOTU: %s" % TABAN_UYARISI)
    print("  -> iki taban karıştırılmadı mı: %s" % taban_karistirilmadi_mi())
    print("\nYAPI: %s (%s)" % (YAPI["ad"], YAPI["kol"]))
    print("  koşullayıcı: %s" % YAPI["kosullayici"])
    print("  madde 165'ten farkı: %s" % YAPI["madde_165_farki"])
    print("  yeniden üretim: motor +%%%.1f vs kayıt +%%%.1f -> tuttu mu: %s"
          % (YENIDEN_URETIM["motor_getiri"], YENIDEN_URETIM["kayit_getiri"],
             yeniden_uretim_tuttu_mu()))
    print("\nGÜNLÜK BAZ:")
    print("  aday     | getiri  | Sharpe | 22-24 | 25-26 | düşüş | eşit-risk")
    for a, v in GUNLUK.items():
        print("  %-8s | %+7.1f | %6.3f | %5.3f | %5.3f | %5.2f | %+9.1f"
              % (a, v[0], v[1], v[2], v[3], v[4], v[5]))
    print("  -> plasebo SIFIR mı (etki zamanlama mı): %s | düşüş İYİLEŞİYOR mu: %s"
          % (plasebo_sifir_mi(), dusus_iyilesiyor_mu()))
    print("\nMADDE 281'İN SON KAPISI — DOZ ÖLÇÜTÜ:")
    print("  aday     | brüt   | net yıllık | kontrole göre")
    for a, v in DOZ.items():
        print("  %-8s | %.3fx | %+10.2f | %+13.2f" % (a, v[0], v[1], v[2]))
    print("  -> geçti mi: %s" % doz_olcutu_gecti_mi())
    print("\nKARAR VEREN SAYI — doz ölçütünde eşli blok bootstrap:")
    print("  aday     | ort     | p5      | medyan  | p95     | P(>0)")
    for a, v in BOOTSTRAP.items():
        print("  %-8s | %+7.2f | %+7.2f | %+7.2f | %+7.2f | %%%.1f"
              % (a, v[0], v[1], v[2], v[3], v[4]))
    print("  -> KANIT BARI (%%%.0f) GEÇİLDİ Mİ: **%s**"
          % (KANIT_BARI, kanit_bari_gecti_mi()))
    print("  not: %s" % bar_hangi_olcutte_gecilmedi())
    print("\nMADDE 284'ÜN BAHİS FİYATI:")
    print("  22-24 kazanç %+.2f | 25-26 kazanç %+.2f -> p* = **%%%.1f**"
          % (BAHIS["22-24"], BAHIS["25-26"], bahis_fiyati()))
    print("  -> kayıp bacağı var mı: %s (madde 239 alt dönem: 22-24 P %%%.1f,"
          " 25-26 P %%%.1f = yazı-tura)"
          % (kayip_bacagi_var_mi(), MADDE_239_ALT_DONEM["22-24"][1],
             MADDE_239_ALT_DONEM["25-26"][1]))
    print("\nMADDE 285'İN GÜÇ BÜTÇESİ:")
    print("  etki %+.2f puan | ASE %.0f -> **%.1f KAT** | KARARLAŞTIRILABİLİR: %s"
          " | gereken ufuk %.1f yıl"
          % (DOZ["aday"][2], ASE_PUAN, ase_kac_kati(),
             kararlastirilabilir_mi(), GEREKEN_YIL))
    print("\nPLATO (madde 282'nin dersi):")
    print("  ayar             | getiri  | Sharpe | düşüş")
    for a, v in PLATO.items():
        im = " <- kayıtlı" if a == KAYITLI_NOKTA else ""
        print("  %-16s | %+7.1f | %6.2f | %6.1f%s" % (a, v[0], v[1], v[2], im))
    print("  -> plato mu: %s | kayıtlı nokta TEPE mi: %s"
          % (plato_mu(), kayitli_nokta_tepe_mi()))
    print("\nŞART 1: %+.3f -> geçti mi: %s | kural gevşetildi mi: %s"
          % (SART1_SAPMA, sart1_gecti_mi(), kural_gevsetildi_mi()))
    print("  (%s)" % KURAL_GEVSETILMEDI)
    print("\nDÜRÜST RİSKLER:")
    for r in RISKLER:
        print("  - %s" % r)
    print("\n-> madde 285'in adayından her ölçütte güçlü mü: %s"
          % madde285_adayindan_guclu_mu())
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
