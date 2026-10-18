#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 283 — "ATIL TEMİNAT" DİYE BİR ŞEY YOK: KENDİ İDDİAMI DÜZELTİYORUM.
VE GETİRİ TAŞIYAN TEMİNAT, KİTABIN GETİRİSİ YÜKSELDİKÇE DAHA KÖTÜ OLUYOR.

İki tur önce kullanıcıya "ölçülmeye değer tek kalem atıl teminat getirisi
(+0,8–1,0 puan, risksiz)" demiştim. **Yanlıştı ve sebebi mekanik.**

HATAM
-----
"Fırsat rezervi sermayenin %20'si ve yılda ~58 kez devreye giriyor, yani
çoğu zaman atıl" demiştim. Rezerv **atıl NAKİT değil, kullanılmamış
MARUZİYET KAPASİTESİ.** Para çapraz teminatta tüm kitabın marjini olarak
duruyor. Üstelik bot boyutunu **toplam teminat değerinden** okuyor
(`sermaye_oku()` → `totalMarginBalance`, madde 162), yani:

**Teminattan para çekmek kitabı BİREBİR küçültür.** 100 dolardan 50'sini
çekmek kitabı yarıya indirir; "boşta duran para" diye kullanılabilecek
bir şey yok. Serbest marj bir YASTIK, bir fırsat değil.

Doğru kullanımı: dozda ne kadar yastık kaldığı. Madde 266'nın ölçülen gün
içi kuyruğu 1x'te −%41,41; doz 1,25x'te tüketilen pay
0,4141×1,25 + mmr×1,25 = **%53,0**, yani **%47,0 yastık**. Bu bir güvenlik
ifadesidir, getiri ifadesi değil.

GERÇEK ROTA: GETİRİ TAŞIYAN TEMİNAT — VE DENKLEMİ
-------------------------------------------------
Bu projede o kol ZATEN var: `CARRY_TEMINAT_MODU=coklu` (madde 141, BFUSD
/ LDUSDT). Madde 141 onu **+0,2 puan** ölçüp `KAPALI_EKSEN`e koymuş.
Sebebi şimdi tam olarak yazılabilir. Teminat kesintisi (haircut) h ise
bot sermayeyi (1−h) kadar küçük görür ve kitap o oranda küçülür:

    **NET = y − h × R_kitap**        (y = teminat getirisi, R = kitap getirisi)

    kesinti h   y=%2     y=%4     y=%5     y=%8
    %0,0       +2,00    +4,00    +5,00    +8,00
    %0,5       +1,44    +3,44    +4,44    +7,44
    %1,0       +0,88    +2,88    +3,88    +6,88
    %2,0       −0,23    +1,77    +2,77    +5,77
    %5,0       −3,59    −1,59    −0,59    +2,41
    %10,0      −9,17    −7,17    −6,17    −3,17

**BAŞABAŞ KESİNTİ: h* = y / R_kitap.** y=%5 için h* = **%4,48**, yani
teminat en az **%95,52** değer görmeli. Kesinti bunun üstündeyse getiri
ne olursa olsun kaybediyorsun.

YENİ YASA — BU RED BAYATLAMADI, GÜÇLENDİ
----------------------------------------
Madde 141 ölçüm yaptığında kitap **+%52** idi. Bugün **+%111,7**. Aynı
y=%5 getirisi için başabaş kesinti o zaman %9,62 iken bugün **%4,48** —
**eşik yarıya indi.** Yani:

**Getiri taşıyan teminat, kitabın getirisi yükseldikçe DAHA KÖTÜ bir
fikirdir.** Kesintinin maliyeti kitabın getirisiyle ölçeklenir, teminatın
getirisi ölçeklenmez. Projedeki alışılmış desenin TERSİ: bu red
bayatlamadı, daha da doğru hâle geldi.

ÜSTÜNE: GETİRİ AYNI PRİMDEN GELİYOR
-----------------------------------
`TEMINAT_MODU` belgesinin kendi uyarısı (madde 141): *"BFUSD'nin getirisi
de funding ücretlerinden gelir (Binance'in kendi delta-nötr stratejisi).
Yani bu botun edge'iyle AYNI primden beslenir: funding çökerse ikisi
birlikte düşer. Çeşitlendirme değildir."* Madde 220'nin yasası
(*"bu piyasadaki her carry primi aynı primin bir yüzü"*) ve madde
279'un dersi (*karar veren sayı korelasyondur*) burada da geçerli:
h=0 olsa bile bu +y puan **çeşitlendirme değil, aynı prime daha fazla
maruziyet**.

TEK GÜVENLE SÖYLENEBİLİR POZİTİF: BNB KOMİSYON İNDİRİMİ
-------------------------------------------------------
Madde 213'ün denetlenmiş sabiti: **1 bp = 1,65 puan/yıl** (yıllık devir
sermayenin 312,6 katı; harmanlanmış komisyon 2,072 bp).

    indirim %10 -> 0,207 bp -> **+0,34 puan/yıl**
    indirim %25 -> 0,518 bp -> +0,85 puan/yıl

Kavramsal maliyeti var: komisyonu BNB ile ödemek **BNB tutmayı** gerektirir
ve kitap tasarım gereği piyasa nötr — yani bu, bilinçli ve küçük bir
nötrlük ihlali. Tutulması gereken miktar küçük (yıllık komisyon
sermayenin ~%6,5'i mertebesinde) ama sıfır değil.

Ayrıca indirim oranı bir **ürün şartı** ve bu kutudan doğrulanamıyor
(`fapi.binance.com` 451; arşiv ürün şartı taşımıyor). Sayı, indirim %10
varsayımıyla verilmiştir.

HÜKÜM
-----
* **"Atıl teminat getirisi" ekseni YOK.** Kendi iddiamı geri alıyorum;
  bot sermayeyi teminat değerinden okuduğu için çekilen para kitabı
  birebir küçültür.
* **Getiri taşıyan teminat:** madde 141'in reddi AYAKTA ve güçlendi.
  Yeniden açma koşulu artık sayısal: **teminat kesintisi < y/R_kitap**
  (bugün y=%5 için **%4,48**). Kesinti doğrulanabilirse hesap tek satır.
* **BNB indirimi: +0,34 puan/yıl**, güvenle söylenebilir tek pozitif;
  uygulanması bir ürün tercihi, kod değişikliği gerektirmiyor.
* **Ayar DEĞİŞMEDİ.**

DERS
----
**Bir kalemi "risksiz kazanç" diye sunmadan önce o paranın kitapta ne iş
yaptığını sor.** Rezerv atıl değil, kullanılmamış kapasiteydi; serbest
marj bir yastıktı. İkisini de getiri kalemi sandım. Ve ikinci ders:
**bir redin bayat olup olmadığını varsaymak yerine o reddin DENKLEMİNİ
yaz** — burada denklem (y − h·R) reddin zamanla GÜÇLENDİĞİNİ gösterdi.
"""
from __future__ import annotations

# --- benim hatam ------------------------------------------------------
HATAM = {
    "iddia": "atil teminat getirisi +0,8-1,0 puan, risksiz",
    "neden_yanlis": "rezerv atil NAKIT degil kullanilmamis MARUZIYET KAPASITESI; "
                    "bot boyutu totalMarginBalance'dan okuyor (sermaye_oku, "
                    "madde 162) -> teminattan cekilen para kitabi BIREBIR kucultur",
    "dogru_kullanim": "serbest marj bir YASTIK, getiri kalemi degil",
}

R_KITAP_NET = 111.7          # madde 265 duzeltmeli
R_KITAP_MADDE141 = 52.0      # madde 141 zamaninda
MADDE_141_OLCUM = 0.2        # puan

# --- yastik hesabi (dogru kullanim) -----------------------------------
GUN_ICI_KUYRUK_1X = 41.41    # madde 266
MMR = 0.01
DOZ_BRUT = 1.254             # madde 276


def tuketilen_pay(brut: float = DOZ_BRUT, mmr: float = MMR) -> float:
    return (GUN_ICI_KUYRUK_1X / 100.0 + mmr) * brut * 100.0


def yastik(brut: float = DOZ_BRUT, mmr: float = MMR) -> float:
    return 100.0 - tuketilen_pay(brut, mmr)


# --- getiri tasiyan teminat denklemi ----------------------------------
def net_puan(y: float, h: float, r: float = R_KITAP_NET) -> float:
    """Getiri y, teminat kesintisi h (oran) -> net puan/yil."""
    return y - h * r


def basabas_kesinti(y: float, r: float = R_KITAP_NET) -> float:
    """h* = y / R_kitap (ORAN olarak)."""
    return y / r


def asgari_teminat_degeri(y: float, r: float = R_KITAP_NET) -> float:
    """Teminat EN AZ bu kadar deger gormeli (yuzde)."""
    return 100.0 * (1.0 - basabas_kesinti(y, r))


def esik_sertlesti_mi(y: float = 5.0) -> bool:
    """Kitabin getirisi yukseldikce basabas kesinti DUSUYOR mu?"""
    return basabas_kesinti(y, R_KITAP_NET) < basabas_kesinti(y, R_KITAP_MADDE141)


def red_guclendi_mi(y: float = 5.0) -> bool:
    """Madde 141'in reddi bayatladi mi, yoksa guclendi mi?"""
    return esik_sertlesti_mi(y)


def getiri_ayni_primden_mi() -> bool:
    """TEMINAT_MODU belgesinin kendi uyarisi."""
    return True


# --- BNB komisyon indirimi --------------------------------------------
PUAN_BASINA_BP = 1.65        # madde 213 (denetlendi)
HARMAN_BP = 2.072            # madde 213
BNB_INDIRIM = 0.10           # urun sarti - bu kutudan DOGRULANAMIYOR


def bnb_kazanci(indirim: float = BNB_INDIRIM) -> float:
    return HARMAN_BP * indirim * PUAN_BASINA_BP


BNB_MALIYETI = ("komisyonu BNB ile odemek BNB TUTMAYI gerektirir; kitap "
                "tasarim geregi piyasa notr -> bilincli ve kucuk bir "
                "notrluk ihlali")
DOGRULANAMAYAN = ("indirim orani bir URUN SARTI; fapi.binance.com bu "
                  "kutudan 451 ve arsiv urun sarti tasimiyor")


def tek_guvenli_pozitif() -> tuple:
    return ("BNB komisyon indirimi", bnb_kazanci())


def atil_teminat_ekseni_var_mi() -> bool:
    return False


def hukum() -> str:
    return ("'Atil teminat getirisi' ekseni YOK - kendi iddiami geri "
            "aliyorum (bot sermayeyi teminat degerinden okuyor, cekilen "
            "para kitabi birebir kucultur; serbest marj bir YASTIK: doz "
            "1,25x'te %%%.1f). Getiri tasiyan teminat: madde 141'in reddi "
            "AYAKTA ve GUCLENDI - basabas kesinti h*=y/R_kitap, y=%%5 icin "
            "bugun %%%.2f (madde 141'de %%%.2f), yani esik YARIYA indi. "
            "Tek guvenli pozitif: BNB indirimi **+%.2f puan/yil**. "
            "Ayar DEGISMEDI."
            % (yastik(), basabas_kesinti(5.0) * 100,
               basabas_kesinti(5.0, R_KITAP_MADDE141) * 100, bnb_kazanci()))


def yaz() -> None:
    print("MADDE 283 — TEMİNAT GETİRİSİ VE BNB İNDİRİMİ\n")
    print("BENİM HATAM: %s" % HATAM["iddia"])
    print("  neden yanlış: %s" % HATAM["neden_yanlis"])
    print("  doğru kullanım: %s" % HATAM["dogru_kullanim"])
    print("\nYASTIK (doğru kullanım): madde 266'nın gün içi kuyruğu 1x'te −%%%.2f"
          % GUN_ICI_KUYRUK_1X)
    for b in (1.0, DOZ_BRUT, 1.5):
        print("  brüt %.3fx -> tüketilen %%%.1f | YASTIK %%%.1f"
              % (b, tuketilen_pay(b), yastik(b)))
    print("\nGETİRİ TAŞIYAN TEMİNAT — NET = y − h × R_kitap  (R = %%%.1f)"
          % R_KITAP_NET)
    print("  kesinti |   y=%2 |   y=%4 |   y=%5 |   y=%8")
    for h in (0.0, 0.005, 0.01, 0.02, 0.05, 0.10):
        print("  %%%5.1f  | " % (h * 100)
              + " | ".join("%+6.2f" % net_puan(y, h) for y in (2.0, 4.0, 5.0, 8.0)))
    print("\nBAŞABAŞ KESİNTİ h* = y / R_kitap:")
    for y in (2.0, 4.0, 5.0, 8.0):
        print("  y=%%%.0f -> h* = %%%.2f  (teminat en az %%%.2f değer görmeli)"
              % (y, basabas_kesinti(y) * 100, asgari_teminat_degeri(y)))
    print("\nBU RED BAYATLAMADI, GÜÇLENDİ:")
    for y in (4.0, 5.0):
        print("  y=%%%.0f -> madde 141'de (kitap +%%%.0f) h*=%%%.2f, BUGÜN "
              "(kitap +%%%.1f) h*=%%%.2f"
              % (y, R_KITAP_MADDE141, basabas_kesinti(y, R_KITAP_MADDE141) * 100,
                 R_KITAP_NET, basabas_kesinti(y) * 100))
    print("  -> eşik sertleşti mi: %s | red güçlendi mi: %s"
          % (esik_sertlesti_mi(), red_guclendi_mi()))
    print("  -> ve getiri AYNI primden geliyor (madde 141'in kendi uyarısı,"
          " madde 220'nin yasası): %s" % getiri_ayni_primden_mi())
    print("\nBNB KOMİSYON İNDİRİMİ (madde 213'ün sabiti: 1 bp = %.2f puan):"
          % PUAN_BASINA_BP)
    for ind in (0.10, 0.25):
        print("  indirim %%%.0f -> %.3f bp -> **%+.2f puan/yıl**"
              % (ind * 100, HARMAN_BP * ind, bnb_kazanci(ind)))
    print("  maliyeti: %s" % BNB_MALIYETI)
    print("  doğrulanamayan: %s" % DOGRULANAMAYAN)
    print("\n'Atıl teminat' ekseni var mı: %s" % atil_teminat_ekseni_var_mi())
    print("Tek güvenli pozitif: %s -> +%.2f puan/yıl" % tek_guvenli_pozitif())
    print("\nHÜKÜM: %s" % hukum())


if __name__ == "__main__":
    yaz()
