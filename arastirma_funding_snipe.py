#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 275 — FUNDING KESKİN NİŞANCISI: kitabın bir ayarı değil, BAŞKA BİR
İŞLEM. Reddedildi — ama neden reddedildiği kitabın 5 günlük tutmasını
açıklıyor.

Kullanıcı "farklı yaklaşımlar düşün" dedi. 274 maddenin tamamı aynı
işlemin varyasyonlarıydı: kesitsel funding taşıma, 5 gün tutma, TP hasadı.
Bu madde aynı sinyal üzerine **yapısal olarak farklı** bir işlem kuruyor:

    funding ödemesini FİYAT RİSKİ OLMADAN topla.
    Ödemeden 1 dakika önce gir, 1 dakika sonra çık -> ~2 dakika maruziyet.
    Yön: funding pozitifse SHORT, negatifse LONG (hep ödemeyi ALAN taraf).

Kitap 5 gün tutar ve parasını TP hasadından kazanır (madde 214); bu işlem
TP istemiyor, yalnız ödemeyi istiyor. Projede hiç ölçülmedi; madde 265'in
dakika verisi mümkün kıldı.

ÖLÇÜM (18 sembol, 2026-07/08, 4.399 ödeme olayı)
------------------------------------------------
    gelir (|funding|)        **+0,97 bp/ödeme**
    fiyat hareketi           +1,01 bp   <- ALEYHTE DEĞİL
    maliyet                 −30,76 bp   (kayma ort 10,38 bp/taraf)
    **NET                   −28,78 bp**  medyan −18,46 · net>0 %9,3

**Kalabalık korkusu gerçekleşmedi:** ödeme anındaki fiyat hareketi
ortalama +1,01 bp, medyan 0,00 — yani ters seçilim yok. İşlemi öldüren
şey saf İŞLEM MALİYETİ.

KAYMA DUYARLILIĞI — SIFIR KAYMAYLA BİLE ÖLÜ
-------------------------------------------
    varsayım                          maliyet    NET      net>0
    ölçülen (yarım aralık) + 5bp      −30,76    −28,78    %9,3
    çeyrek aralık + 5bp               −20,38    −18,40    %15,6
    **kayma YOK + 5bp taker**         −10,00    **−8,02**  %25,1
    kayma YOK + 2bp maker (imkânsız)   −4,00    −2,02     %40,3

2 dakikalık pencerede maker olmak imkânsız (madde 265: 1. deneme 3 dakika
bekliyor ve %72,3 doluyor), ama o satır bile negatif. **Gelir yapısal
olarak maliyetin altında.**

ARZ YOK: ÖDEMELERİN %97,9'U MALİYETİ KARŞILAMIYOR
-------------------------------------------------
Tüm evren (841 sembol, **2.461.016 ödeme**):
    |funding| >= 1 bp   -> %39,357
    |funding| >= 3 bp   -> %9,351
    |funding| >= 5 bp   -> %5,171
    **|funding| >= 10 bp -> %2,129**   (asgari maliyet eşiği)
    |funding| >= 20 bp  -> %0,961
    |funding| >= 50 bp  -> %0,322
Asgari maliyet (kayma yok, 5bp taker, gidiş-dönüş) 10 bp ve ödemelerin
yalnız **%2,13'ü** bunu geçiyor. Filtreli bir sürüm de besleyemez.

UÇ KUYRUKTA DURUM DAHA KÖTÜ — AMA ÖRNEKLEM KÜÇÜK
------------------------------------------------
Gelir dilimlerine göre (n, gelir, fiyat, net):
    0-1 bp    n=3396  gelir 0,45  fiyat **+1,68**  net −26,67
    1-3 bp    n= 908  gelir 1,23  fiyat +0,22      net −29,03
    3-7 bp    n=  62  gelir 4,16  fiyat **−4,17**  net −79,96
    7-15 bp   n=  12  gelir 10,08 fiyat +23,84     net −215,46
    40+ bp    n=  12  gelir 83,31 fiyat **−121,92** net −141,38
Uç kuyrukta fiyat hareketi ALEYHE dönüyor (−121,92 bp) ama n=12; bu
kuyruk hakkında hüküm vermek için örneklem yetersiz. Yine de o kuyruk
ödemelerin %0,3'ü, yani işlese bile arz yok.

ASIL KAZANÇ: KİTABIN 5 GÜNLÜK TUTMASI NEDEN VAR
-----------------------------------------------
Bu red, kitabın bir tasarım kararını AÇIKLIYOR. Gidiş-dönüş maliyeti
madde 265'in ölçtüğü maker harmanıyla ~5,14 bp (2,57 bp/taraf). Evren
ortalamasında funding 0,97 bp/ödeme × 3 ödeme/gün = 2,9 bp/gün. Yani
**yalnız icrayı funding'den karşılamak için asgari ~1,8 gün tutmak
gerekir.** Kitap 5 gün tutuyor.

Madde 264 tutma süresini "kaldıraç kolu" diye ölçmüştü (kısaldıkça getiri
ve düşüş birlikte büyür, Sharpe sabit). Madde 275 o kola bir **TABAN**
koyuyor: tutma süresi, biriken funding'in gidiş-dönüş maliyetini
karşıladığı noktanın altına indirilemez. Tutma süresi serbest bir
parametre değil, maliyet/gelir oranının dayattığı bir eşik.

HÜKÜM: RED — yapısal. Gelir (1 bp) asgari maliyetin (4-10 bp) altında ve
ödemelerin %97,9'u eşiği geçmiyor. Mühendislikle kapanacak bir açık
değil. Ayar DEĞİŞMEDİ.
"""
from __future__ import annotations

OLCUM = {
    "sembol": 18, "olay": 4399,
    "gelir_bp": 0.97, "fiyat_bp": 1.01, "maliyet_bp": -30.76,
    "net_bp": -28.78, "net_medyan_bp": -18.46, "net_pozitif_pct": 9.3,
    "kayma_ort_bp": 10.38,
}

DUYARLILIK = {   # ad -> (maliyet_bp, net_bp, net_pozitif_pct)
    "olculen_yarim_aralik_5bp": (-30.76, -28.78, 9.3),
    "ceyrek_aralik_5bp": (-20.38, -18.40, 15.6),
    "kayma_yok_5bp_taker": (-10.00, -8.02, 25.1),
    "kayma_yok_2bp_maker": (-4.00, -2.02, 40.3),
}

ARZ = {   # esik bp -> odeme orani %
    1: 39.357, 3: 9.351, 5: 5.171, 10: 2.129, 20: 0.961, 50: 0.322,
}
ARZ_SEMBOL = 841
ARZ_ODEME = 2461016
ASGARI_MALIYET_BP = 10.0       # kayma yok + 5bp taker, gidis-donus

DILIM = {   # (alt, ust) -> (n, gelir, fiyat, net)
    (0, 1): (3396, 0.45, 1.68, -26.67),
    (1, 3): (908, 1.23, 0.22, -29.03),
    (3, 7): (62, 4.16, -4.17, -79.96),
    (7, 15): (12, 10.08, 23.84, -215.46),
    (40, None): (12, 83.31, -121.92, -141.38),
}

# Kitabin 5 gunluk tutmasinin tabani
MAKER_GIDIS_DONUS_BP = 5.14    # madde 265: 2,57 bp/taraf
FUNDING_GUNLUK_BP = 2.9        # 0,97 bp x 3 odeme
TABAN_GUN = MAKER_GIDIS_DONUS_BP / FUNDING_GUNLUK_BP   # ~1,8
KITAP_TUTMA_GUN = 5


def kalabalik_etkisi_var_mi() -> bool:
    """Odeme anindaki fiyat hareketi ALEYHTE mi? (genel ortalamada)"""
    return OLCUM["fiyat_bp"] < 0


def maliyet_mi_olduruyor() -> bool:
    """Isi bitiren sey maliyet mi, ters secilim mi?"""
    return abs(OLCUM["maliyet_bp"]) > abs(OLCUM["gelir_bp"] + OLCUM["fiyat_bp"])


def sifir_kaymayla_bile_olu_mu() -> bool:
    return DUYARLILIK["kayma_yok_5bp_taker"][1] < 0


def imkansiz_maker_ile_bile_olu_mu() -> bool:
    return DUYARLILIK["kayma_yok_2bp_maker"][1] < 0


def arz_var_mi(esik_bp: float = ASGARI_MALIYET_BP, yeter_pct: float = 10.0) -> bool:
    return ARZ.get(int(esik_bp), 0.0) >= yeter_pct


def uc_kuyruk_hukum_verilebilir_mi(asgari_n: int = 30) -> bool:
    return DILIM[(40, None)][0] >= asgari_n


def tutma_tabani_gun() -> float:
    """Tutma suresinin ALT siniri: biriken funding gidis-donusu karsilar mi?"""
    return TABAN_GUN


def tutma_taban_ustunde_mi() -> bool:
    return KITAP_TUTMA_GUN > TABAN_GUN


def hukum() -> str:
    return ("RED - yapisal. Gelir %.2f bp/odeme, asgari maliyet %.0f bp "
            "(kayma YOK + taker) ve odemelerin yalniz %%%.2f'si o esigi "
            "geciyor. Sifir kaymayla bile net %+.2f bp. Isi bitiren sey "
            "ters secilim DEGIL (fiyat %+.2f bp), saf maliyet. "
            "Ayar DEGISMEDI."
            % (OLCUM["gelir_bp"], ASGARI_MALIYET_BP, ARZ[10],
               DUYARLILIK["kayma_yok_5bp_taker"][1], OLCUM["fiyat_bp"]))


def yaz() -> None:
    print("MADDE 275 — FUNDING KESKİN NİŞANCISI\n")
    print("kurgu: ödemeden 1 dk önce gir, 1 dk sonra çık; hep ödemeyi ALAN taraf")
    print("%d sembol, %d ödeme olayı\n" % (OLCUM["sembol"], OLCUM["olay"]))
    print("  gelir (|funding|)   %+8.2f bp" % OLCUM["gelir_bp"])
    print("  fiyat hareketi      %+8.2f bp  -> aleyhte mi: %s"
          % (OLCUM["fiyat_bp"], kalabalik_etkisi_var_mi()))
    print("  maliyet             %+8.2f bp  (kayma %.2f bp/taraf)"
          % (OLCUM["maliyet_bp"], OLCUM["kayma_ort_bp"]))
    print("  NET                 %+8.2f bp  medyan %+.2f · net>0 %%%.1f"
          % (OLCUM["net_bp"], OLCUM["net_medyan_bp"], OLCUM["net_pozitif_pct"]))
    print("  -> işi bitiren MALİYET mi: %s" % maliyet_mi_olduruyor())
    print("\nKAYMA DUYARLILIĞI:")
    for ad, (m, n, p) in DUYARLILIK.items():
        print("  %-28s maliyet %+7.2f  NET %+7.2f  net>0 %%%.1f" % (ad, m, n, p))
    print("  -> sıfır kaymayla bile ölü: %s | imkânsız maker ile bile ölü: %s"
          % (sifir_kaymayla_bile_olu_mu(), imkansiz_maker_ile_bile_olu_mu()))
    print("\nARZ (%d sembol, %d ödeme):" % (ARZ_SEMBOL, ARZ_ODEME))
    for e in sorted(ARZ):
        print("  |funding| >= %2d bp -> %%%7.3f" % (e, ARZ[e]))
    print("  -> asgari maliyet eşiğinde (%.0f bp) yeterli arz var mı: %s"
          % (ASGARI_MALIYET_BP, arz_var_mi()))
    print("\nGELİR DİLİMLERİ (n, gelir, fiyat, net):")
    for (alt, ust), (n, g, f, nt) in DILIM.items():
        print("  %3s-%-4s bp | n=%4d | gelir %6.2f | fiyat %+7.2f | net %+8.2f"
              % (alt, ust if ust else "+", n, g, f, nt))
    print("  -> uç kuyruk hakkında hüküm verilebilir mi: %s (n=%d)"
          % (uc_kuyruk_hukum_verilebilir_mi(), DILIM[(40, None)][0]))
    print("\nKİTABIN 5 GÜNLÜK TUTMASININ TABANI:")
    print("  maker gidiş-dönüş %.2f bp ÷ funding %.1f bp/gün = **%.1f gün** taban"
          % (MAKER_GIDIS_DONUS_BP, FUNDING_GUNLUK_BP, tutma_tabani_gun()))
    print("  kitap %d gün tutuyor -> tabanın üstünde: %s"
          % (KITAP_TUTMA_GUN, tutma_taban_ustunde_mi()))
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
