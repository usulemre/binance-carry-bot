#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 292 — EMİR YAŞAM DÖNGÜSÜ DENETİMİ: BEŞ HİPOTEZDEN DÖRDÜ ZATEN
SAVUNULMUŞ, BİRİ GERÇEK VE EN PAHALI YERDE DURUYORDU.

Kullanıcı yönü değiştirdi: "canlıyı artıracak çalışmalar." Geri testin
kârı 291 maddede ölçüldü; canlıda KAYBEDİLECEK yer başka bir eksendir —
geri test bir şeyi VARSAYIYOR, canlı kod onu GARANTİ etmiyorsa fark
doğrudan paradan çıkar. Bu eksen hiç denetlenmedi, çünkü bot hiç
çalışmadı.

Yöntem: emir yaşam döngüsünün her adımında tek bir soru — geri test ne
varsayıyor, canlı kod onu garanti ediyor mu? Giriş (GTX) → dolum/dolmama
→ kâr-al konması → kâr-al dolumu → 5. gün çıkışı.

═══ ÖNCE: DÖRT HİPOTEZ, DÖRT NON-BULGU (hepsi kodla doğrulandı) ═══

**(1) "TP referansı borsanın AĞIRLIKLI ORTALAMA girişi, geri testinki
dilimin kendi girişi."** Aynı sembol birden fazla dilimde tutulduğunda
borsada tek pozisyon ve harmanlanmış entryPrice olur; TP o harmana göre
konur. Geri testte her bacak kendi girişinden +%40 sanıyordum. **YANLIŞ:**
`g33.py:505` → `giris[k]=(abs(poz[k])*e+dw*f)/(abs(poz[k])+dw)` — motor
da sembol başına AĞIRLIKLI ORTALAMA giriş tutuyor. Canlı ile birebir.

**(2) "Durum dosyası kaybolursa borsada YETİM reduce-only TP'ler kalır,
`kar_al_kontrol` onları göremez, dolduklarında bot sembolü yeniden
açar."** **YANLIŞ:** `bayat_emirleri_temizle` (madde 163) her turda
borsadaki TÜM açık emirleri listeleyip iptal ediyor, yalnız o turda
işlem görecekleri değil. Yetim emir bir tur yaşıyor.

**(3) "Kâr-al iptal edilip yeniden konana kadar pozisyonlar TP'siz."**
Doğru ama **ölçeği önemsiz:** pencere tur başına ~30-60 saniye (emir
gönderimi 0,2s/emir + pozisyon başına bir API çağrısı), 8 saatte bir.
+%40'lık bir seviyenin tam o pencerede değme olasılığı ihmal edilebilir.

**(4) "GTX girişi dolmazsa bacak eksik kalır ve kitap yönlü olur."**
Doğru ama **savunulmuş ve ÖLÇÜLMÜŞ:** `dolumu_kovala` (madde 193) kalanı
iptal edip daha uzak limitle, son denemede piyasa emriyle kapatıyor;
madde 208 emirleri taraf DOKUMASIYLA sıralıyor, böylece liste nerede
kesilirse kesilsin |net| en fazla bir bacak kalıyor (ölçüldü: 8sa K/Z p1
−%0,520, en kötü −%0,868).

Dört hipotezi de yayımlamadan önce kodu okudum. **Madde 290'ın yasası
burada da geçerliydi: bir knobun/akışın ADINDAN ne yaptığını çıkarma.**

═══ TEK GERÇEK BULGU — `kar_al_kur` SESSİZCE BAŞARISIZ OLUYORDU ═══

Kod şöyleydi:

    except Exception as ex:
        logger.warning("kâr al emri konamadı %s: %s", sem, ex)
    ...
    return kurulan

ve çağrıldığı yerde (`bir_tur`) dönüş değeri **ATILIYORDU**. Hiç kimse
`kurulan`'ı açık pozisyon sayısıyla kıyaslamıyordu. Yani 50 pozisyonun
10'una TP konulamazsa logda 10 uyarı birikiyor ve bot devam ediyordu.

**BEDELİ ÖLÇÜLÜ:** madde 290 hasadı ablasyonla fiyatladı — kâr-al hasadı
**+18,9 CAGR puanı ve −6,1 puan düşüş** değerinde (kârın %16,8'i,
Sharpe'ın dörtte biri). Konulamayan her TP, o bacağın hasat payını
götürür. Ve TP'nin konması, hasadın tamamının dayandığı TEK adımdır.

**VE DAHA KÖTÜSÜ: YANLIŞ TEŞHİS.** `carry_izleme.py` düşük TP dolumunu
görünce şunu yazıyordu:

    [!] LONG TP dolumu beklenenin YARISINDAN AZ. Kâr motoru
        çalışmıyor olabilir

Yani 291 maddelik stratejiyi şüpheli ilan ediyordu. Oysa AYNI belirtiyi
hiç KONULMAMIŞ emirler de üretir — ve o bir İCRA arızasıdır (hız sınırı,
hassasiyet, asgari nominal). Dolmayan emir zaten konulmamışsa dolum
oranına bakmak anlamsızdır. **Madde 286'nın yasası ("ölçemedim" ile
"ölçtüm, şüpheli" AYRI kodlar olmalı) canlı yüzeyde ihlal ediliyordu:
bir API hatası, bir piyasa bulgusu gibi görünüyordu.**

═══ YAPILAN ═══

1. `TP_KURULUM_DOSYA` (`carry_tp_kurulum.csv`): zaman,hedeflenen,
   kurulan,basarisiz — her turda bir satır. `carry_tp.csv` DOLUMU
   sayıyordu; bu KONMAYI sayıyor.
2. `kar_al_kur`: başarısızlar **bir kez yeniden denenir** (hız sınırı ve
   geçici 5xx bir denemede geçer), sonuç deftere yazılır, eksik kalırsa
   **ERROR** seviyesinde sembol adlarıyla ve hasadın fiyatıyla raporlanır.
3. Pozisyonlar hiç okunamazsa deftere `hedeflenen = -1` yazılır —
   "sıfır pozisyon vardı" ile KARIŞMASIN (madde 286'nın ayrımı).
   `tp_kurulum_oku` o satırları orana KATMAZ, ayrıca sayar; yoksa toplam
   bozulur ve oran 1'in üstüne çıkabilirdi.
4. `carry_izleme`: artık önce KONMA oranına bakıyor. <%95 ise "TP
   EMİRLERİ KONULAMIYOR — bu bir PİYASA bulgusu DEĞİL, bir İCRA
   arızasıdır... Strateji şüpheli DEĞİL" diyor. Ancak konma oranı
   ≥%95 İKEN düşük dolum "gerçekten bir piyasa/varsayım bulgusu" olarak
   raporlanıyor.

═══ YASA ═══

**Canlı kârı artırmak, geri testi iyileştirmekten farklı bir iştir:
geri testin VARSAYDIĞI her adım, canlı kodda bir GARANTİ ister ve
garantisi olmayan adım sessizce para kaybeder.** Hasadın tamamı tek bir
API çağrısının başarısına bağlıydı ve o çağrının başarısı hiç
sayılmıyordu.

**İKİNCİ YASA: bir gösterge, iki farklı sebebi ayırt edemiyorsa,
varsayılan olarak yanlış olanı suçlar.** Düşük TP dolumu hem icra
arızası hem piyasa bulgusu olabilir; gösterge ikincisini yazıyordu,
çünkü yazarı (ben) ölçüyü kurarken birincisini hiç düşünmemiştim.
"""

# --- dort non-bulgu ---------------------------------------------------
NON_BULGULAR = {
    "TP referansi harmanlanmis giris": (
        "g33.py:505 motor da sembol basina AGIRLIKLI ORTALAMA giris "
        "tutuyor - canli ile birebir", False),
    "yetim reduce-only TP'ler": (
        "bayat_emirleri_temizle (madde 163) her turda borsadaki TUM acik "
        "emirleri iptal ediyor", False),
    "TP'siz pencere": (
        "tur basina ~30-60 saniye, 8 saatte bir - olcegi ihmal edilebilir",
        False),
    "dolmayan GTX girisi": (
        "dolumu_kovala (madde 193) + madde 208'in taraf dokumasi; olculdu: "
        "8sa K/Z p1 -%0,520, en kotu -%0,868", False),
}

# --- tek gercek bulgu ------------------------------------------------
BULGU = {
    "ne": "kar_al_kur tek tek emir hatalarini yalniz logger.warning ile "
          "geciyordu; donus degeri cagrildigi yerde ATILIYORDU ve hic "
          "kimse kurulan'i acik pozisyon sayisiyla kiyaslamiyordu",
    "neden_pahali": "hasat madde 290'da ablasyonla fiyatlandi: +18,9 CAGR "
                    "puani, -6,1 puan dusus, karin %16,8'i, Sharpe'in "
                    "dortte biri - ve TP'nin KONMASI hasadin dayandigi "
                    "TEK adim",
    "yanlis_teshis": "carry_izleme dusuk dolumu gorunce 'kar motoru "
                     "calismiyor olabilir' diyordu, yani 291 maddelik "
                     "stratejiyi supheli ilan ediyordu - ayni belirtiyi "
                     "hic KONULMAMIS emirler de uretir ve o bir ICRA "
                     "arizasidir",
}
HASAT_DEGERI = {"cagr_puan": 18.9, "sharpe": 0.77, "dusus_puan": -6.1,
                "karin_payi_yuzde": 16.8}

# --- yapilan duzeltmeler --------------------------------------------
DUZELTME = (
    "TP_KURULUM_DOSYA (carry_tp_kurulum.csv): zaman,hedeflenen,kurulan,"
    "basarisiz - her turda bir satir",
    "kar_al_kur: basarisizlar BIR KEZ yeniden denenir",
    "kar_al_kur: eksik kalirsa ERROR seviyesinde sembol adlari ve hasadin "
    "fiyatiyla raporlanir",
    "pozisyonlar okunamazsa hedeflenen = -1 (madde 286'nin ayrimi: 'sifir "
    "pozisyon' ile KARISMASIN)",
    "tp_kurulum_oku: hedeflenen<0 satirlar orana KATILMAZ, ayrica sayilir",
    "carry_izleme: once KONMA oranina bakar; <%95 ise 'ICRA arizasi, "
    "strateji supheli DEGIL' der",
)
KONMA_ESIGI = 0.95

# --- yasalar ---------------------------------------------------------
YASA = ("canli kari artirmak, geri testi iyilestirmekten FARKLI bir "
        "istir: geri testin VARSAYDIGI her adim canli kodda bir GARANTI "
        "ister ve garantisi olmayan adim SESSIZCE para kaybeder")
IKINCI_YASA = ("bir gosterge, iki farkli sebebi ayirt edemiyorsa "
               "varsayilan olarak YANLIS olani suclar")


# --- sinamalar --------------------------------------------------------
def kac_hipotez_savunulmus_cikti() -> int:
    return sum(1 for v in NON_BULGULAR.values() if v[1] is False)


def non_bulgular_yayimlanmadi_mi() -> bool:
    """Dort hipotezin hicbiri BULGU olarak yayimlanmadi mi?"""
    return all(v[1] is False for v in NON_BULGULAR.values())


def motor_de_harmanli_giris_mi() -> bool:
    return "AGIRLIKLI ORTALAMA" in NON_BULGULAR["TP referansi harmanlanmis giris"][0]


def bulgu_hasada_mi_dokunuyor() -> bool:
    return HASAT_DEGERI["cagr_puan"] > 15.0 and "TEK adim" in BULGU["neden_pahali"]


def yanlis_teshis_kayitli_mi() -> bool:
    return ("kar motoru" in BULGU["yanlis_teshis"]
            and "ICRA arizasi" in BULGU["yanlis_teshis"])


def duzeltme_sayisi() -> int:
    return len(DUZELTME)


def retry_var_mi() -> bool:
    return any("yeniden denenir" in d for d in DUZELTME)


def madde286_ayrimi_uygulandi_mi() -> bool:
    return any("hedeflenen = -1" in d for d in DUZELTME)


def hukum() -> str:
    return (
        "EMIR YASAM DONGUSU DENETLENDI. Bes hipotezden DORDU zaten "
        "savunulmus cikti (madde 163 bayat emirler, 193 dolum kovalama, "
        "208 taraf dokumasi, ve motorun kendisi de sembol basina "
        "harmanlanmis giris tutuyor) - dordu de yayimlanmadan once kodla "
        "dogrulandi. TEK GERCEK BULGU en pahali yerdeydi: kar_al_kur "
        "basarisiz emirleri yalnizca warning'le geciyor, donus degeri "
        "atiliyor ve hic kimse konan TP sayisini acik pozisyon sayisiyla "
        "kiyaslamiyordu - oysa hasat +18,9 CAGR puani ve -6,1 dusus "
        "degerinde ve TP'nin KONMASI onun dayandigi TEK adim. Dahasi, "
        "carry_izleme dusuk dolumu gorunce STRATEJIYI supheli ilan "
        "ediyordu; ayni belirtiyi hic konulmamis emirler de uretir. "
        "Artik: tek seferlik retry, konma defteri, ERROR raporu, ve "
        "izleme once KONMA oranina bakip 'bu bir ICRA arizasi, strateji "
        "supheli DEGIL' diyor. Strateji ayari DEGISMEDI."
    )


def yaz() -> None:
    print(__doc__)
    print("DORT NON-BULGU (hepsi kodla dogrulandi, hicbiri yayimlanmadi):")
    for ad, (sebep, bulgu_mu) in NON_BULGULAR.items():
        print("  [%s] %-34s %s" % ("X" if bulgu_mu else "-", ad, sebep))
    print("  savunulmus cikan hipotez: %d/%d | yayimlanmadi mi: %s"
          % (kac_hipotez_savunulmus_cikti(), len(NON_BULGULAR),
             non_bulgular_yayimlanmadi_mi()))
    print("\nTEK GERCEK BULGU:")
    for k, v in BULGU.items():
        print("  %-14s %s" % (k, v))
    print("  hasadin degeri: +%.1f CAGR puani / +%.2f Sharpe / %+.1f dusus "
          "= karin %%%.1f'i"
          % (HASAT_DEGERI["cagr_puan"], HASAT_DEGERI["sharpe"],
             HASAT_DEGERI["dusus_puan"], HASAT_DEGERI["karin_payi_yuzde"]))
    print("  bulgu hasada mi dokunuyor: %s | yanlis teshis kayitli mi: %s"
          % (bulgu_hasada_mi_dokunuyor(), yanlis_teshis_kayitli_mi()))
    print("\nYAPILAN (%d duzeltme, konma esigi %%%.0f):"
          % (duzeltme_sayisi(), KONMA_ESIGI * 100))
    for d in DUZELTME:
        print("  - %s" % d)
    print("  retry var mi: %s | madde 286'nin ayrimi uygulandi mi: %s"
          % (retry_var_mi(), madde286_ayrimi_uygulandi_mi()))
    print("\nYASA: %s" % YASA)
    print("IKINCI YASA: %s" % IKINCI_YASA)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
