#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 329 — **CANLI DEVRE KESİCİ, KOŞULMAYAN BİR KİTAP İÇİN
AYARLIYDI.** `kitap_anahtari()` yapılandırılan `N_LEGS=5`'i okuyup
**"15x5"** döndürüyordu; ama 2.000 $'da `uygun_bacak_sayisi` bacağı
**otomatik 4'e** indiriyor ve koşulan kitap **15 faz × 4 bacak (bacak
13,33 $, evren D8)**. O kitabın tam dönem düşüşü **%19,91** iken
yürürlükteki **İNCELE eşiği −%18** — yani **eşik, kitabın kendi tarihsel
düşüşünün ALTINDA** (pay **−1,91 puan**) ve `esik_kademesi()` buna
**"olculmus"** diyordu, yani hiçbir uyarı da basmıyordu.

*** BU DOSYA 2026-10-19'DA TRANSKRİPTTEN YENİDEN YAZILDI (madde 335).
Özgün hâli konteyner kaybında gitti; sayılar, hükümler ve yasalar o
turun ölçümlerinden birebir aktarıldı, ama dosya ORİJİNAL DEĞİL. ***

Kanonik yöntemle (madde 231/303 birebir) koşulan kitabın eşiği
ölçüldü: **İNCELE −%23, DURDUR −%30**. Yürürlükteki çift 5 ve 7 puan
**fazla sıkıydı** — ve dahası **DURDUR (−%23), koşulan kitabın kanonik
İNCELE seviyesine** oturuyordu: sağlıklı bir kitap en kötü rejiminin
normal p5'inde **DURDURULACAKTI** (madde 234'ün dersi).

═══ 1. NASIL BULUNDU ═══

Madde 322 ve 328 aynı sınıftan iki sorun bulmuştu: arkasında üretim
olmayan kayıtlı sayı. Canlıya çıkışta kullanılacak sayılar aynı gözle
tarandı:

    cr.kitap_anahtari()         -> "15x5"
    cr.esik_kademesi()          -> "olculmus"   (en guvenilir kademe!)
    cr.KITAP_ESIK["15x5"]       -> (-0.18, -0.23)
    cr.KITAP_DUSUS["15x5"]      -> 14.54

    cb.uygun_bacak_sayisi(2000) -> **4**
    GERCEK anahtar              -> **"15x4"**  (iki tabloda da YOK)
    kosulan kitabin dususu      -> **19.91**
    PAY = 18.00 - 19.91         -> **-1.91 puan**

═══ 2. KANONİK ÖLÇÜM (yöntem madde 231/303 ile birebir) ═══

Rejim kırılması **2025-01-01**, `yil_bootstrap(n=4000, blok=21,
tohum=11)`, en kötü rejim p5/p1, yuvarlama "büyüklüğü bir sonraki tam
sayıya":

    KOSULAN 15x4 D8 (tam donem dusus %19,91)
      rejim             n     1y getiri p5   1y dusus p5   1y dusus p1
      tum            1504        +36,7         -20,71        -25,84
      **dusuk (<2025) 896        +18,5         -22,83        -29,23**  <- EN KOTU
      yuksek (>=2025) 608        +72,8         -16,48        -19,69

    ⇒ INCELE **-23**  ·  DURDUR **-30**
    yururlukteki ("15x5" anahtari): INCELE -18 · DURDUR -23

Karşılaştırma (aynı yöntem, üç kitap):

    kitap   en kotu rejim p5    p1        esik cifti
    15x5         -17,93      -22,31     -18 / -23
    13x3         -22,66      -28,98     -23 / -29
    **15x4       -22,83      -29,23     -23 / -30**  <- KOSULAN

Koşulan kitap, eşik açısından 13×3'e **çok yakın** — ikisi de 2.000 $'da
dar bacaklı ve daralmış evrenli.

═══ 3. DÜZELTME ═══

  carry_rapor.kitap_anahtari(..., bakiye=None)
      bakiye verilirse artik `uygun_bacak_sayisi(bakiye)` kullanilir
  carry_rapor.KITAP_ESIK["15x4"]          = (-0.23, -0.30)
  carry_rapor.KITAP_REJIM_OLCUMU["15x4"]  = ("dusuk prim", -22.83, -29.23)
  carry_rapor.KITAP_DUSUS_KOSULAN["15x4"] = (2000.0, "D8", 19.91)
  carry_rapor.backtest_maksimumu()        kosulan tablodan okur
  carry_rapor.karar() + panel satiri      anahtari BAKIYEDEN turetir
  canli_karar.canli_gecer_mi(..., bakiye=) + `--bakiye`
  arastirma_rejim_esik.ESIK_KANONIK["15x4"] + REJIM_15X4

**Tablo başına yazmak hiçbir şeyi düzeltmezdi:** eşiği okuyan dört
çağrı yeri de bakiyeyi geçirecek şekilde değiştirildi.

**`KITAP_DUSUS`'e KARIŞTIRILMADI.** O tablo madde 295'in tablosudur:
yapılandırmaya göre, **tam evrende** ölçülmüş. Koşulan kitabın düşüşü
**sermayeye bağlıdır** (bacak → evren) ve bu yüzden **ayrı tabloda**
tutuldu.

Yeni pay: **23,00 − 19,91 = +3,09 puan** (eskisi −1,91).

═══ 4. AÇIK EKSEN (dürüst) ═══

`"15x4"` çifti **2.000 $ ve D8 evreni** için ölçüldü. Anahtar yalnız
yapılandırmayı taşıyor; evren sermayeye bağlı olduğu için **başka bir
bakiyede aynı anahtar başka bir kitaba karşılık gelir** ve çift yeniden
ölçülmelidir. Doğru çözüm anahtara evreni de katmaktır — yapılmadı,
işaretlendi.

AYAR DEĞİŞTİ: canlı devre kesici eşikleri koşulan kitap için
düzeltildi (İNCELE −%18 → **−%23**, DURDUR −%23 → **−%30**). Bu bir
getiri iyileştirmesi değil, **yanlış alarmın** ve madde 234'ün
"sağlıklı kitabı kapatma" riskinin giderilmesidir.
"""

from __future__ import annotations

YENIDEN_YAZILDI = True
YENIDEN_YAZMA_NOTU = ("ozgun dosya 2026-10-19 konteyner kaybinda gitti; "
                      "bu metin oturum transkriptinden yeniden yazildi "
                      "(madde 335). Sayilar o turun olcumlerinden "
                      "birebir, dosya ORIJINAL DEGIL.")

# ───────────────────────────────────────────── 1. BULGU
NASIL_BULUNDU = ("madde 322 ve 328 'arkasinda uretim olmayan kayitli "
                 "sayi' sinifindan iki sorun bulmustu; canliya cikista "
                 "kullanilacak sayilar ayni gozle tarandi")
ESKI = {"anahtar": "15x5", "kademe": "olculmus",
        "esik": (-0.18, -0.23), "dusus_tablosu": 14.54}
KOSULAN = {"bacak_sayisi": 4, "anahtar": "15x4", "bacak_usd": 13.33,
           "evren": "D8", "dusus": 19.91, "bakiye": 2000.0}
PAY_ESKI = 18.00 - 19.91          # -1.91
PAY_YENI = 23.00 - 19.91          # +3.09
KADEME_YANLIS_GUVEN_MI = True

# ───────────────────────────────────────────── 2. KANONİK ÖLÇÜM
YONTEM = ("rejim kirilmasi 2025-01-01, yil_bootstrap(n=4000, blok=21, "
          "tohum=11), en kotu rejim p5/p1, yuvarlama 'buyuklugu bir "
          "sonraki tam sayiya' (madde 231/303 ile BIREBIR)")
REJIM_15X4 = {   # rejim -> (1y getiri p5, 1y dusus p5, 1y dusus p1)
    "tum":    (36.7, -20.71, -25.84),
    "dusuk":  (18.5, -22.83, -29.23),
    "yuksek": (72.8, -16.48, -19.69),
}
EN_KOTU_REJIM = "dusuk"
ESIK_YENI = (-0.23, -0.30)
ESIK_ESKI = (-0.18, -0.23)
UC_KITAP = {   # kitap -> (en kotu p5, p1, esik cifti)
    "15x5": (-17.93, -22.31, (-0.18, -0.23)),
    "13x3": (-22.66, -28.98, (-0.23, -0.29)),
    "15x4": (-22.83, -29.23, (-0.23, -0.30)),
}
DURDUR_INCELE_SEVIYESINDE_MIYDI = True

# ───────────────────────────────────────────── 3. DÜZELTME
DUZELTME = {
    "carry_rapor.kitap_anahtari": "bakiye verilirse uygun_bacak_sayisi",
    "carry_rapor.KITAP_ESIK['15x4']": (-0.23, -0.30),
    "carry_rapor.KITAP_REJIM_OLCUMU['15x4']": ("dusuk prim", -22.83, -29.23),
    "carry_rapor.KITAP_DUSUS_KOSULAN['15x4']": (2000.0, "D8", 19.91),
    "carry_rapor.backtest_maksimumu": "kosulan tablodan okur",
    "carry_rapor.karar + panel": "anahtari BAKIYEDEN turetir",
    "canli_karar.canli_gecer_mi": "bakiye= parametresi + --bakiye",
    "arastirma_rejim_esik": "ESIK_KANONIK['15x4'] + REJIM_15X4",
}
KITAP_DUSUSE_KARISTIRILDI_MI = False
AYRIM_NEDENI = ("KITAP_DUSUS madde 295'in tablosudur: YAPILANDIRMAYA "
                "gore, TAM EVRENDE. Kosulan kitabin dususu SERMAYEYE "
                "baglidir (bacak -> evren), o yuzden AYRI tabloda.")
KABLOLAMA_SART_MI = True

# ───────────────────────────────────────────── 4. AÇIK EKSEN
ACIK_EKSEN = ("'15x4' cifti 2.000 $ ve D8 evreni icin olculdu. Anahtar "
              "yalniz yapilandirmayi tasiyor; evren SERMAYEYE bagli "
              "oldugu icin BASKA bir bakiyede ayni anahtar BASKA bir "
              "kitaba karsilik gelir. Dogru cozum anahtara evreni de "
              "katmaktir - YAPILMADI, isaretlendi.")
AYAR_DEGISTI = True
DEGISIKLIGIN_TURU = ("getiri iyilestirmesi DEGIL: yanlis alarmin ve "
                     "madde 234'un 'saglikli kitabi kapatma' riskinin "
                     "giderilmesi")

YASA1 = ("Bir esik, YAPILANDIRILAN kitaba degil KOSULAN kitaba gore "
         "secilir: `N_LEGS` yapilandirilandir, `uygun_bacak_sayisi` "
         "kosulani verir ve ikisi 2.000 $'da FARKLIDIR (5 vs 4).")
YASA2 = ("Bir esik, kitabin KENDI tarihsel dususunun ALTINDA olamaz: "
         "-%18 esik ile %19,91 dusus, payi -1,91 puan yapar ve saglikli "
         "bir kitap alarmi KESINLIKLE tetikler.")
YASA3 = ("Bir kademe fonksiyonu ('olculmus' / 'olceklenmis' / 'temel') "
         "ANAHTARIN DOGRULUGUNU denetlemiyorsa, yanlis anahtarla en "
         "guvenilir kademeyi dondurur ve UYARI basmaz - guven "
         "kademesinin kendisi bir korluk kaynagi olur.")
YASA4 = ("Sermayeye bagli bir olcum, yapilandirmaya gore tutulan bir "
         "tabloya KARISTIRILMAZ: ayri tabloda tutulur ve bagimlilik "
         "(bakiye, evren) anahtarin yaninda yazilir.")
YASA5 = ("Bir tabloya satir yazmak DUZELTME DEGILDIR; esigi okuyan "
         "butun cagri yerlerinin kablolanmasi duzeltmedir.")

ILK_KEZ = ("Projede ilk kez CANLI RISK ayarinda (devre kesici) bir "
           "hata bulundu - oncekiler olcum ya da raporlama "
           "hatalariydi.")


# ───────────────────────────────────────────── DOĞRULAMA
def anahtar_yanlis_kitabi_mi_gosteriyordu():
    return ESKI["anahtar"] != KOSULAN["anahtar"]


def pay_negatif_miydi():
    return PAY_ESKI < 0


def pay_duzeldi_mi():
    return PAY_YENI > 3.0


def kademe_yanlis_guven_veriyor_muydu():
    return KADEME_YANLIS_GUVEN_MI and ESKI["kademe"] == "olculmus"


def durdur_incele_seviyesinde_miydi():
    return abs(ESKI["esik"][1]) <= abs(ESIK_YENI[0]) + 1e-9


def kanonik_yontem_birebir_mi():
    return "BIREBIR" in YONTEM and "tohum=11" in YONTEM


def en_kotu_rejim_dusuk_mu():
    v = {k: x[1] for k, x in REJIM_15X4.items()}
    return min(v, key=v.get) == EN_KOTU_REJIM


def kosulan_13x3e_yakin_mi():
    a, b = UC_KITAP["15x4"], UC_KITAP["13x3"]
    return abs(a[0] - b[0]) < 0.5 and abs(a[1] - b[1]) < 0.5


def karistirilmadi_mi():
    return KITAP_DUSUSE_KARISTIRILDI_MI is False


def hukum():
    return {
        "eski_anahtar": ESKI["anahtar"],
        "kosulan_anahtar": KOSULAN["anahtar"],
        "eski_esik": ESIK_ESKI,
        "yeni_esik": ESIK_YENI,
        "pay_eski": round(PAY_ESKI, 2),
        "pay_yeni": round(PAY_YENI, 2),
        "degisikligin_turu": "yanlis alarm giderildi",
        "ayar_degisti_mi": True,
    }


def yaz():
    print(__doc__)
    print("UC KITAP (ayni kanonik yontem)")
    for k, (p5, p1, e) in UC_KITAP.items():
        print("  %-6s en kotu p5 %7.2f  p1 %7.2f  -> esik %s" % (k, p5, p1, e))
    print("\nHUKUM")
    for k, v in hukum().items():
        print("  %-22s %s" % (k, v))


if __name__ == "__main__":
    yaz()
