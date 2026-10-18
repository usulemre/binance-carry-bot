#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 273 — NAKİT KADRANI + KALDIRAÇ: cephe 0,40'ta bitmiyordu, ve
bağlayıcı kısıt artık LİKİDASYON DUVARI.

Madde 272 rezerv 0,40'ı açtı (madde 266 likidasyonu ölçtüğü için 4. şartın
gerekçesi karşılanmıştı) ve +2,04 net puan buldu. Ama madde 225'in cephesi
0,40'ta KESİLMİŞTİ ve eşit-risk getirisi hâlâ MONOTON yükseliyordu:
+%103,3 (0) · +%107,8 (0,10) · +%112,6 (0,20) · +%113,5 (0,30) ·
+%114,6 (0,40). Tepe ölçülmemişti. Bu madde 0,50/0,60/0,70'i ölçtü.

MOTOR (faz ortalaması, bugünün yüzeyi)
--------------------------------------
    rezerv  yıllık   Sharpe(motor)  düşüş
    0,20   +112,35      3,115       −14,7   (kontrol)
    0,30    +96,35      3,125       −13,0
    0,40    +81,20      3,135       −11,3
    0,50    +67,05      3,155        −9,65
    0,60    +53,85      3,165        −7,95
    0,70    +41,65      3,175        −6,2
Motor Sharpe'ı 0,70'e kadar yükselmeye devam ediyor; düşüş yarıdan aza
iniyor. Madde 225'in "nakit kadranı" imzası cephenin sonuna kadar sürüyor.

EŞİT RİSK CEPHESİ (günlük seri, düşüş 14,54 puana eşitlenerek)
--------------------------------------------------------------
    rezerv  kaldıraç  eşit-risk  icra   NET    25-26 Sh  likid.eşiği  266 kuyruğu
    0,20     1,000x    +112,46   0,79   +0,00    3,384     −%99,0      hayır
    0,40     1,298x    +114,45   1,03   +2,04    3,379     −%76,0      hayır
    0,50     1,529x    +116,18   1,21   +3,31    3,370     −%64,4      hayır
    0,60     1,861x    +118,93   1,47   **+5,80**  3,351   −%52,7      hayır
    0,70     2,383x    +123,58   1,88   +10,03   3,311     −%41,0      **EVET**

Önemli: eşit-risk hesabı kaldıraçlı düşüşü her satırda **14,54'e
eşitliyor**, yani günlük risk gerçekten eşit; madde 266'nın büyütmesiyle
gün içi karşılığı da her satırda aynı (%21,63). *İlk tablomda gün içi
düşüşü bir kez daha kaldıraçla çarpmıştım — kendi hatam, düzeltildi.*

BAĞLAYICI KISIT: LİKİDASYON DUVARI
----------------------------------
Madde 266'nın ölçtüğü EN KÖTÜ iki aylık yol −%41,41 (kaldıraçsız).
Likidasyon eşiği `r <= (mmr·g − 1)/g` olduğu için o kuyruk şu
kaldıraçların ÜSTÜNDE öldürücü olur:
    mmr %0,5 -> 2,386x · **mmr %1,0 -> 2,358x** · mmr %2,5 -> 2,277x
Rezerv 0,70'in istediği **2,383x bu duvarın ÖTESİNDE.** Rezerv 0,60'ın
istediği 1,861x duvarın epey içinde. **Cephenin tepesi getiri eğrisinin
değil, kuyruk duvarının belirlediği yerde: rezerv ~0,60.**

BOOTSTRAP (günlük seri, 20 günlük blok, B=3.000) — icra NET'e dahil
-------------------------------------------------------------------
    rezerv  Δeşit-risk  P(>0)   ΔNET    P(net>0)
    0,50     +3,92      %80,9   +3,50    %78,0
    0,60     +6,23      %80,6   +5,56    %77,6
    0,70     +9,36      %79,0   +8,30    %76,1

**Δeşit-risk kıl payı çıtanın üstünde (%80,6-80,9) AMA icra bedeli
düşülünce NET'in gücü %78'e iniyor — projenin %80 çıtasının ALTINDA.**
Yani kaldıracın kendi maliyeti, kazancı yalnız küçültmüyor, KANITINI da
zayıflatıyor.

ŞART 1 HÂLÂ DÜŞÜYOR VE KÖTÜLEŞİYOR
----------------------------------
Günlük 25-26 Sharpe monoton geriliyor: 3,384 → 3,370 → 3,351 → 3,311.
Yani kural, rezerv büyüdükçe 1. şarttan daha SERT düşüyor.

HÜKÜM
-----
Nakit kadranı + kaldıraç yolu **gerçek ve ölçülmüş bir kazanç veriyor:
rezerv 0,60 @1,861x -> net +5,80 puan** (+%111,7 -> +%117,5). Üç fren:
  1. 1. şart düşüyor (25-26 Sharpe −0,033) ve rezervle kötüleşiyor,
  2. NET kazancın bootstrap gücü **%77,6** — %80 çıtasının altında,
  3. 0,70'in ötesi likidasyon duvarına çarpıyor (2,358x).
Ve operasyonel gerçek: rezerv 0,60 demek sermayenin %60'ı nakitte ve
kitap kalan kısımda 1,86x brütle çalışıyor — madde 204'ün kapasitesi,
madde 265'in icrası, hepsi bu brütle ölçeklenir.

**Bu bir PARAMETRE değil KALDIRAÇ kararıdır; AYAR DEĞİŞTİRİLMEDİ.**
Ölçülmüş en iyi seçenek olarak kayda geçti.
"""
from __future__ import annotations

MOTOR = {   # rezerv -> (yillik, sharpe_motor, dusus)
    0.20: (112.35, 3.115, -14.7),
    0.30: (96.35, 3.125, -13.0),
    0.40: (81.20, 3.135, -11.3),
    0.50: (67.05, 3.155, -9.65),
    0.60: (53.85, 3.165, -7.95),
    0.70: (41.65, 3.175, -6.2),
}

# rezerv -> (kaldirac, esit_risk, icra_puan, net_puan, gec_sharpe, likid_esik)
CEPHE = {
    0.20: (1.000, 112.46, 0.79, 0.00, 3.384, -99.0),
    0.40: (1.298, 114.45, 1.03, 2.04, 3.379, -76.0),
    0.50: (1.529, 116.18, 1.21, 3.31, 3.370, -64.4),
    0.60: (1.861, 118.93, 1.47, 5.80, 3.351, -52.7),
    0.70: (2.383, 123.58, 1.88, 10.03, 3.311, -41.0),
}

BOOTSTRAP = {   # rezerv -> (d_esitrisk, P_esitrisk, d_net, P_net)
    0.50: (3.92, 80.9, 3.50, 78.0),
    0.60: (6.23, 80.6, 5.56, 77.6),
    0.70: (9.36, 79.0, 8.30, 76.1),
}

MADDE_266_KUYRUK = -41.41
DUVAR = {0.005: 2.386, 0.010: 2.358, 0.025: 2.277}
GUC_CITASI = 80.0
HEDEF_DUSUS = 14.54
GUN_ICI = 21.63           # madde 266'nin 1,488 buyutmesiyle, her satirda AYNI
DURUST_KONTROL = 111.7    # madde 265'in icra duzeltmesiyle

BENIM_HATAM = ("ilk tabloda gun ici dususu bir kez daha kaldiracla carptim; "
               "oysa esit-risk hesabi KALDIRACLI dususu zaten 14,54'e "
               "esitliyor, yani gun ici karsiligi her satirda AYNI (%21,63). "
               "Duzeltildi.")


def duvar(mmr: float = 0.010) -> float:
    """madde 266'nin kuyrugu hangi kaldiracin uzerinde oldurucu olur?"""
    return 1.0 / (abs(MADDE_266_KUYRUK) / 100.0 + mmr)


def duvari_asiyor_mu(rezerv: float, mmr: float = 0.010) -> bool:
    return CEPHE[rezerv][0] > duvar(mmr)


def en_iyi_guvenli(mmr: float = 0.010) -> float:
    """Duvarin icinde kalan en yuksek rezerv."""
    uygun = [r for r in CEPHE if not duvari_asiyor_mu(r, mmr)]
    return max(uygun, key=lambda r: CEPHE[r][3])


def net_citayi_geciyor_mu(rezerv: float) -> bool:
    return rezerv in BOOTSTRAP and BOOTSTRAP[rezerv][3] >= GUC_CITASI


def esitrisk_citayi_geciyor_mu(rezerv: float) -> bool:
    return rezerv in BOOTSTRAP and BOOTSTRAP[rezerv][1] >= GUC_CITASI


def sart1_kotulesyor_mu() -> bool:
    """Rezerv buyudukce 25-26 Sharpe monoton geriliyor mu?"""
    rs = sorted(CEPHE)
    g = [CEPHE[r][4] for r in rs]
    return all(g[i] > g[i + 1] for i in range(len(g) - 1))


def kaldirac_kaniti_zayiflatiyor_mu(rezerv: float = 0.60) -> bool:
    """Icra bedeli yalnizca kazanci degil KANITI da dusuruyor mu?"""
    d, pe, dn, pn = BOOTSTRAP[rezerv]
    return pe >= GUC_CITASI > pn


def hukum() -> str:
    r = en_iyi_guvenli()
    k = CEPHE[r]
    return ("En iyi GUVENLI nokta rezerv %.2f @%.3fx -> net +%.2f puan "
            "(+%%%.1f -> +%%%.1f). UC FREN: sart 1 dusuyor (25-26 %.3f vs "
            "%.3f), NET bootstrap gucu %%%.1f (cita %%%.0f), ve 0,70'in "
            "otesi likidasyon duvarina (%.3fx) carpiyor. KALDIRAC kararidir; "
            "AYAR DEGISTIRILMEDI."
            % (r, k[0], k[3], DURUST_KONTROL, DURUST_KONTROL + k[3],
               k[4], CEPHE[0.20][4], BOOTSTRAP[r][3], GUC_CITASI, duvar()))


def yaz() -> None:
    print("MADDE 273 — NAKİT KADRANI + KALDIRAÇ\n")
    print("MOTOR (faz ort.): Sharpe cephenin SONUNA kadar yükseliyor")
    for r in sorted(MOTOR):
        v = MOTOR[r]
        print("  rezerv %.2f  yıllık %+7.2f  Sh %.3f  düşüş %+6.2f" % (r, *v))
    print("\nEŞİT RİSK CEPHESİ (düşüş %.2f puana eşitlenerek):" % HEDEF_DUSUS)
    print("  rezerv | kaldıraç | eşit-risk |  icra | NET    | 25-26 | likid.eşiği | duvarı aşıyor?")
    for r in sorted(CEPHE):
        kal, esit, icra, net, gec, lik = CEPHE[r]
        print("   %.2f  | %7.3fx | %+9.2f | %5.2f | %+6.2f | %5.3f | %10.1f%% | %s"
              % (r, kal, esit, icra, net, gec, lik,
                 "EVET" if duvari_asiyor_mu(r) else "hayır"))
    print("  (kaldıraçlı düşüş her satırda %.2f, gün içi %.2f — eşit risk bunu "
          "zaten eşitliyor)" % (HEDEF_DUSUS, GUN_ICI))
    print("\nLİKİDASYON DUVARI (madde 266'nın kuyruğu %.2f):" % MADDE_266_KUYRUK)
    for mmr, g in DUVAR.items():
        print("  mmr %%%.1f -> %.3fx üzerinde öldürücü" % (mmr * 100, g))
    print("\nBOOTSTRAP (icra NET'e dahil):")
    print("  rezerv | Δeşit-risk | P(>0) | ΔNET  | P(net>0) | eşit-risk çıta | NET çıta")
    for r in sorted(BOOTSTRAP):
        d, pe, dn, pn = BOOTSTRAP[r]
        print("   %.2f  | %+10.2f | %%%4.1f | %+5.2f | %%%7.1f  | %-14s | %s"
              % (r, d, pe, dn, pn,
                 "GEÇER" if esitrisk_citayi_geciyor_mu(r) else "altinda",
                 "GEÇER" if net_citayi_geciyor_mu(r) else "ALTINDA"))
    print("\n  kaldıraç KANITI da zayıflatıyor mu: %s"
          % kaldirac_kaniti_zayiflatiyor_mu())
    print("  şart 1 rezervle KÖTÜLEŞİYOR mu: %s" % sart1_kotulesyor_mu())
    print("\nBENİM HATAM: %s" % BENIM_HATAM)
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
