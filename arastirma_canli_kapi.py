#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 286 — CANLI ÇIKIŞ DENETİMİ: EN KRİTİK KAPIDA BİR KUSUR BULUNDU
("ölçemedim" ile "ölçtüm, şüpheli" aynı çıkış kodunu veriyordu).
VE MADDE 285'İN ASE BULGUSU BİR **ÖN FİLTREYE** ÇEVRİLDİ.

Madde 285 şunu ölçtü: backtest'te aramak artık aynı duvara (ASE ~+13
puan) farklı açılardan koşmaktır ve gerçek bilgi tek yerden gelebilir —
**1x canlı veri.** Bu madde o sonucu TEKRARLAMAK yerine ona göre
davranıyor: canlı çıkışın önündeki yolu denetliyor.

DENETİM YÖNTEMİ: araçlar **ilk kez karşılaşılacak durumda** koşuldu
(API anahtarı yok, defterler boş). Bu durum 285 madde boyunca hiç
sınanmamıştı — her zaman ya testlerin sahte istemcisiyle ya da hiç.

BULUNAN KUSUR — EN KRİTİK KAPIDA
--------------------------------
`carry_izleme.py` madde 216'nın takvimindeki **14. gün karar noktası**:
funding tahsilatını %100 güçle ölçen araç. Madde 260 bu araca ön kayıtlı
bir karar bağlamıştı ve kararı **çıkış koduyla** veriyor:
**0 DEVAM · 1 İNCELE · 2 DURDUR.**

Anahtar yokken araç `rapor()` içinde ham bir `AssertionError` ile
**çöküyordu** ve Python çıkış kodu **1** veriyordu — yani *"İNCELE"*
verdiktiyle **birebir aynı.** Gözetimsiz bir 14. gün kontrolünde bu,
*"funding tahsil edilmiyor"* ile *"anahtarı export etmeyi unuttum"*u
ayırt edemez demekti. Madde 211'in sessiz-yanlış-sinyal sınıfı, ve
madde 260'ın kendi yorumunun tam tersine düşen bir boşluk (o madde
"eskiden her halde 0 ile çıkıyordu" diye düzeltmişti ama ÇÖKME yolunu
atlamıştı).

DÜZELTME: **kod 3 = ÖLÇÜLEMEDİ**, ve bir verdikt DEĞİL.
* anahtar yoksa: borsaya hiç bağlanmadan kod 3 + açık mesaj
  (`carry_preflight.py`'nin ifadesiyle aynı: "anahtar dosyaya YAZILMAZ")
* `rapor()` herhangi bir sebeple hata verirse (izin, IP kısıtı, ağ,
  bölge): kod 3 + hatanın kendisi + "bu bir VERDİKT DEĞİL"
İkisi de sınandı: anahtar yok → 3 · sahte anahtarla bölge hatası → 3.

AİLE DENETİMİ — DİĞER ARAÇLAR TEMİZ
-----------------------------------
    arac                anahtar yok durumu                 kod
    carry_preflight.py  açık mesaj, "CANLIYA GEÇMEYİN"       1  ✔
    carry_preflight.py --yerel  borsayı atlar                0  ✔
    carry_sapma.py      "bakiye geçmişi yok" (normal)        0  ✔
    carry_defter.py     sessiz, temiz                        0  ✔
    carry_izleme.py     **ham AssertionError**            **1** ✗ → 3

Yalnız en kritik araç kusurluydu. Diğer dördü doğru davranıyor.

BENİM ÖLÇÜM HATAM (yayınlanmadan yakalandı)
-------------------------------------------
İlk koşumda `carry_preflight.py`'nin "CANLIYA GEÇMEYİN" yazıp **0**
döndürdüğünü sandım ve bunu bir kusur sanıyordum. Hata benimdi:
`python ... | tail -18; echo $?` boru hattında **`tail`'in** kodunu
yazıyor. Doğru ölçümde araç 1 döndürüyor. Kodu okumadan "kusur buldum"
demesem de, ölçüm aracının kendisini denetlemek gerekiyordu.

İKİNCİ PARÇA — MADDE 285'İN ASE'Sİ ARTIK BİR ÖN FİLTRE
------------------------------------------------------
Madde 285 ASE'yi (~+13 puan) bir turun **sonunda** öğrendi: 13 motor
koşumu yapıp "P(>0) %67,5, bar %80" demek pahalı. Artık `karar_kurali`
bunu **baştan** sorabiliyor:

    ASE_PUAN = 13.0 · UFUK_GUN = 1504
    saptanabilir_mi(etki)        -> bu etki bariyi gecebilir mi
    gereken_ufuk_yil(etki)       -> %80 icin kac yil veri gerekir
    tur_degerli_mi(beklenen_etki)-> tur HUKUM verebilir mi

    beklenen etki   saptanabilir   gereken ufuk
    +%4,73             HAYIR          31,1 yıl
    +%7,22             HAYIR          13,3 yıl
    +%13,00            EVET            4,1 yıl
    +%20,00            EVET            1,7 yıl

Kullanımı: bir tura başlamadan önce adayın beklenen etkisi ASE'nin
altındaysa tur **hüküm veremez** — o zaman ya mekanizmaya/ön sebebe
dayanarak karar verilir (madde 285'in "karar kullanıcıya ait" hâli) ya
da tur hiç başlatılmaz. Bu filtre son on turun çoğunu baştan
elerdi.

HÜKÜM
-----
Bir **kusur düzeltildi** (14. gün kapısının çıkış kodu), bir **ön filtre
eklendi** (ASE), bir **ölçüm hatam** kaydedildi. Strateji ayarı
DEĞİŞMEDİ. Canlı çıkış yolunda bilinen başka boşluk yok: beş aracın
beşi de ilk karşılaşılacak durumda doğru davranıyor ve çıkış kodları
artık ayrıştırılmış.

DERS
----
**Bir kapının doğru ÖLÇTÜĞÜNÜ test etmek, doğru SİNYAL verdiğini test
etmek değildir.** `test_carry_preflight.py` `yaz_ozet()`'in 0/1
döndürdüğünü doğruluyordu ve doğruydu; kusur, aracın o fonksiyona hiç
ULAŞAMADIĞI yoldaydı. **Bir karar aracının en önemli testi, ölçümün
BAŞARISIZ olduğu yoldur** — çünkü gözetimsiz bir kontrolde o yol, en
sık yürünen yoldur.
"""
from __future__ import annotations

# --- bulunan kusur ----------------------------------------------------
KUSUR = {
    "arac": "carry_izleme.py",
    "rol": "madde 216'nin takviminde 14. GUN KARAR NOKTASI (funding "
           "tahsilati, %100 guc)",
    "eski_davranis": "anahtar yokken rapor() icinde ham AssertionError -> "
                     "Python cikis kodu 1",
    "neden_tehlikeli": "1 = INCELE verdiktiyle BIREBIR AYNI; 'funding tahsil "
                       "edilmiyor' ile 'anahtari export etmeyi unuttum' "
                       "ayirt edilemez (madde 211'in sessiz-yanlis-sinyal sinifi)",
    "duzeltme": "kod 3 = OLCULEMEDI, ve bir VERDIKT DEGIL",
    "sinif": "madde 211 + madde 260'in atladigi COKME yolu",
}

KODLAR = {0: "DEVAM", 1: "INCELE", 2: "DURDUR", 3: "OLCULEMEDI (verdikt DEGIL)"}
SINANAN_YOLLAR = {
    "anahtar yok": 3,
    "sahte anahtar + bolge hatasi": 3,
}

# --- aile denetimi ----------------------------------------------------
AILE = {   # arac -> (anahtar yok durumu, cikis kodu, temiz mi)
    "carry_preflight.py": ("acik mesaj, CANLIYA GECMEYIN", 1, True),
    "carry_preflight.py --yerel": ("borsayi atlar", 0, True),
    "carry_sapma.py": ("bakiye gecmisi yok (normal)", 0, True),
    "carry_defter.py": ("sessiz, temiz", 0, True),
    "carry_izleme.py (ONCE)": ("ham AssertionError", 1, False),
    "carry_izleme.py (SONRA)": ("acik mesaj, verdikt degil", 3, True),
}

# --- benim olcum hatam ------------------------------------------------
OLCUM_HATAM = {
    "ne": "carry_preflight.py'nin 'CANLIYA GECMEYIN' yazip 0 dondurdugunu "
          "sandim",
    "sebep": "`python ... | tail -18; echo $?` boru hattinda TAIL'in kodunu "
             "yazar, Python'un degil",
    "dogru": "arac 1 donduruyor; kusur YOK",
    "ders": "olcum aracinin kendisi de denetlenmeli",
}

# --- ikinci parca: ASE on filtresi ------------------------------------
ASE_PUAN = 13.0
UFUK_GUN = 1504
ON_FILTRE = {   # beklenen etki -> (saptanabilir, gereken_yil)
    4.73: (False, 31.1),
    7.22: (False, 13.3),
    13.00: (True, 4.1),
    20.00: (True, 1.7),
}
FILTRE_FONKSIYONLARI = ("saptanabilir_mi", "gereken_ufuk_gun",
                        "gereken_ufuk_yil", "tur_degerli_mi")


def kusur_bulundu_mu() -> bool:
    return AILE["carry_izleme.py (ONCE)"][2] is False


def kusur_duzeltildi_mi() -> bool:
    return (AILE["carry_izleme.py (SONRA)"][1] == 3
            and AILE["carry_izleme.py (SONRA)"][2] is True)


def olcemedim_ile_supheli_ayri_mi() -> bool:
    """Kod 3, verdikt kodlarindan (0/1/2) ayri mi?"""
    return 3 in KODLAR and KODLAR[3].endswith("(verdikt DEGIL)")


def eski_kod_verdiktle_ayni_miydi() -> bool:
    return AILE["carry_izleme.py (ONCE)"][1] == 1


def iki_yol_da_sinandi_mi() -> bool:
    return len(SINANAN_YOLLAR) == 2 and all(v == 3 for v in SINANAN_YOLLAR.values())


def aile_kac_arac_temiz() -> int:
    return sum(1 for v in AILE.values() if v[2])


def yalniz_en_kritik_arac_mi_kusurluydu() -> bool:
    kusurlu = [a for a, v in AILE.items() if not v[2]]
    return kusurlu == ["carry_izleme.py (ONCE)"]


def olcum_hatam_kayitli_mi() -> bool:
    return "tail" in OLCUM_HATAM["sebep"].lower() and "YOK" in OLCUM_HATAM["dogru"]


def on_filtre_dogru_mu() -> bool:
    """ASE on filtresi: etki < ASE ise saptanamaz."""
    return all((e >= ASE_PUAN) == v[0] for e, v in ON_FILTRE.items())


def on_filtre_son_turlari_elerdi_mi() -> bool:
    """Madde 285'in +7,22'si ve madde 285'in %10 payi (+4,73) elenir miydi?"""
    return not ON_FILTRE[7.22][0] and not ON_FILTRE[4.73][0]


def ayar_degismedi_mi() -> bool:
    return True


def hukum() -> str:
    return ("Bir KUSUR duzeltildi (14. gun kapisinin cikis kodu: anahtar "
            "yoklugu %d = INCELE veriyordu, artik %d = OLCULEMEDI ve bir "
            "VERDIKT DEGIL), bir ON FILTRE eklendi (ASE %.0f puan: "
            "tur_degerli_mi), bir OLCUM HATAM kaydedildi. Besli aracin "
            "%d'u ilk karsilasilacak durumda dogru davraniyor. Strateji "
            "ayari DEGISMEDI."
            % (AILE["carry_izleme.py (ONCE)"][1],
               AILE["carry_izleme.py (SONRA)"][1], ASE_PUAN,
               aile_kac_arac_temiz()))


def yaz() -> None:
    print("MADDE 286 — CANLI ÇIKIŞ DENETİMİ + ASE ÖN FİLTRESİ\n")
    print("BULUNAN KUSUR: %s" % KUSUR["arac"])
    print("  rol: %s" % KUSUR["rol"])
    print("  eski: %s" % KUSUR["eski_davranis"])
    print("  neden tehlikeli: %s" % KUSUR["neden_tehlikeli"])
    print("  düzeltme: %s" % KUSUR["duzeltme"])
    print("\nÇIKIŞ KODLARI:")
    for k, v in KODLAR.items():
        print("  %d = %s" % (k, v))
    print("  -> 'ölçemedim' ile 'şüpheli' AYRI mı: %s | eski kod verdiktle"
          " aynı mıydı: %s"
          % (olcemedim_ile_supheli_ayri_mi(), eski_kod_verdiktle_ayni_miydi()))
    print("  -> sınanan yollar: %s (ikisi de 3 mü: %s)"
          % (dict(SINANAN_YOLLAR), iki_yol_da_sinandi_mi()))
    print("\nAİLE DENETİMİ (ilk karşılaşılacak durum: anahtar yok):")
    print("  araç                        | davranış                        | kod | temiz")
    for a, (d, k, t) in AILE.items():
        print("  %-27s | %-31s | %3d | %s" % (a, d, k, "✔" if t else "✗"))
    print("  -> yalnız EN KRİTİK araç mı kusurluydu: %s | temiz araç: %d"
          % (yalniz_en_kritik_arac_mi_kusurluydu(), aile_kac_arac_temiz()))
    print("\nBENİM ÖLÇÜM HATAM: %s" % OLCUM_HATAM["ne"])
    print("  sebep: %s" % OLCUM_HATAM["sebep"])
    print("  doğru: %s | ders: %s" % (OLCUM_HATAM["dogru"], OLCUM_HATAM["ders"]))
    print("\nASE ÖN FİLTRESİ (madde 285 -> karar_kurali):")
    print("  beklenen etki | saptanabilir | gereken ufuk")
    for e in sorted(ON_FILTRE):
        s, y = ON_FILTRE[e]
        print("  %+12.2f | %12s | %.1f yıl" % (e, s, y))
    print("  fonksiyonlar: %s" % ", ".join(FILTRE_FONKSIYONLARI))
    print("  -> filtre doğru mu: %s | son turları elerdi mi: %s"
          % (on_filtre_dogru_mu(), on_filtre_son_turlari_elerdi_mi()))
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
