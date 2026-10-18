#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 301 — KARARSIZ BİR TESTİ CİDDİYE ALMAK CANLI YOLDA GERÇEK BİR
KUSUR BULDU: EMİR SIRASI SÜREÇ BAŞINA RASTGELEYDİ.

Madde 300'ün test turunda entegrasyon takımı üç testten düştü
(11e/11f: "uç funding'li coine DAHA BÜYÜK pozisyon açıldı",
"reddedilen emir DAHA UZAK fiyatla yeniden deneniyor", "2. denemede
geçen bacak AÇILDI"). O turda `carry_bot.py`'ye HİÇ dokunulmamıştı ve
madde 299'un turunda aynı takım geçmişti.

Tekrar koşuldu: **üçü de geçti.** Yani takım kararsızdı.

Kolay yol, "yeşil olana kadar tekrar koş" demekti. Yapılmadı.

═══ 1. SEBEP: `set` ÜZERİNDE DÖNÜP SONRA YALNIZ BÜYÜKLÜĞE GÖRE SIRALAMAK ═══

`carry_bot.emirleri_hesapla()` şöyleydi:

    for s in set(hedef) | set(mevcut):      # <- hash sirasi
        ...
    kapanis.sort(key=lambda e: -abs(mevcut.get(e[0], 0.0)))
    al  = sorted(..., key=lambda e: -e[2])  # <- yalniz buyukluk
    sat = sorted(..., key=lambda e: -e[2])

Ama bu kitabın açılış bacakları **EŞİT BÜYÜKLÜKTE** (taraf içinde eşit
ağırlık). Yani sıralama tümüyle beraberlik ve Python'un kararlı sıralaması
`set` iterasyonundan gelen sırayı korur — o sıra da **sürecin rastgele
string hash tohumuna** bağlıdır.

ÖLÇÜLDÜ. Aynı girdi (10 eşit bacak), beş ayrı `PYTHONHASHSEED`:

    0 -> C0, C7, C2, C1, C4, C5, C6, C9, C8, C3
    1 -> C4, C3, C2, C5, C0, C1, C8, C7, C6, C9
    2 -> C8, C1, C2, C9, C0, C3, C4, C7, C6, C5
    3 -> C6, C3, C4, C1, C0, C7, C2, C5, C8, C9
    4 -> C0, C5, C2, C1, C6, C7, C4, C3, C8, C9

Beş koşu, beş ayrı sıra.

═══ 2. CANLIDAKİ ANLAMI (asıl mesele) ═══

Bu bir test kusuru DEĞİL, canlı yolda bir kusurdu:

  * Tur yarıda kesilirse — API hatası, oran limiti, zaman aşımı, bakiye
    yetmemesi — **HANGİ** bacakların açıldığı keyfi olur.
  * Kitap **NÖTR KALIR**: madde 208'in dokuması açılışları taraf taraf
    alternatifliyor, ve dokuma sıralı listeler üzerinde çalıştığı için
    her kesme noktasında |net| en fazla bir bacak. O garanti bozulmadı.
  * Bozulan şey YENİDEN ÜRETİLEBİLİRLİK: aynı bakiye, aynı piyasa, aynı
    kod — farklı sembol bileşimi. Bir arızayı aynı koşullarda tekrarlamak
    imkânsız, ve iki koşunun farkı "piyasa mı değişti, kod mu?" sorusuna
    cevap vermiyor.
  * Ve entegrasyon takımı bu yüzden ara ara düşüyordu. **Ara ara düşen
    bir preflight, insanı uyarıları görmezden gelmeye alıştırır** — canlıya
    gerçek parayla çıkmadan önce en tehlikeli alışkanlık.

═══ 3. DÜZELTME ═══

Her sıralamaya **sembol adı ikincil anahtar** olarak eklendi:

    for s in sorted(set(hedef) | set(mevcut)):
    kapanis.sort(key=lambda e: (-abs(mevcut.get(e[0], 0.0)), e[0]))
    al  = sorted(..., key=lambda e: (-e[2], e[0]))
    sat = sorted(..., key=lambda e: (-e[2], e[0]))

Büyüklük sırası DEĞİŞMEDİ (birincil anahtar aynı); yalnız beraberlikler
artık alfabetik kırılıyor.

DOĞRULANDI: altı ayrı `PYTHONHASHSEED` ile tek bir sıra
(`C0, C1, C2, ... C9`) ve dokuma korunmuş — C0 long, C1 short, C2 long…
yani her kesme noktasında nötrlük duruyor.

VE TAKIM: entegrasyon üç ayrı hash tohumuyla (0, 7, 42) koşuldu, üçünde
de geçti. Kararsızlık kapandı.

═══ 4. NE DEĞİŞMEDİ ═══

  * Hangi semboller seçiliyor: DEĞİŞMEDİ (seçim bu fonksiyonun dışında).
  * Bacak büyüklükleri: DEĞİŞMEDİ.
  * Geri test: ETKİLENMEZ — `emirleri_hesapla` yalnız canlı yolda çağrılır,
    motor (g33) onu hiç kullanmaz. Backtest paritesi takımda doğrulandı.
  * Strateji ayarı: DEĞİŞMEDİ.

Yani bu bir kâr değişikliği değil, bir **GÜVENİLİRLİK** değişikliği. Ama
canlı kârı dolaylı olarak korur: yeniden üretilemeyen bir botun arızasını
teşhis edemezsiniz.

═══ 5. BENZER SIZINTI: TEST TAKIMI DURUM BIRAKIYOR ═══

Araştırma sırasında ikinci bir şey görüldü: `temiz_ortam()` üç dosyayı
geçici dizine yönlendiriyor (`DILIM_DURUM_DOSYA`, `VOL_GECMIS_DOSYA`,
`SAGLIK_DOSYA`) ama **`TP_DEFTER_DOSYA` (madde 214) ve
`TP_KURULUM_DOSYA` (madde 292)** listede yok. Takım bu iki dosyayı proje
dizinine yazıyor ve koşular arasında büyütüyor.

Bu turda kararsızlığın sebebi BU DEĞİLDİ — ölçüldü: `bir_tur` içinde o
iki defter yalnız YAZILIYOR, hiç okunmuyor (okuyan tek yer
`carry_izleme`). Yani şu an zararsız. Ama bir gün bir okuma eklenirse
takım sessizce koşu-sırasına bağımlı hale gelir. Kayda geçti; eksen açık.

AYAR DEĞİŞMEDİ.
"""

# ---------------------------------------------------------------- SABİTLER

KAYNAK = ("Madde 300'un test turunda entegrasyon takimi uc testten dustu, "
          "ama o turda carry_bot.py'ye HIC dokunulmamisti.")
DUSEN_TESTLER = (
    "uc funding'li coine DAHA BUYUK pozisyon acildi",
    "reddedilen emir DAHA UZAK fiyatla yeniden deneniyor",
    "2. denemede gecen bacak ACILDI",
)
TEKRAR_KOSUDA_GECTI = True
"""Tekrar kosuldu, ucu de gecti -> takim KARARSIZDI."""
KOLAY_YOL = "'yesil olana kadar tekrar kos' - yapilmadi."

# --- 1. sebep ---
FONKSIYON = "carry_bot.emirleri_hesapla"
SEBEP = ("`set(hedef) | set(mevcut)` uzerinde donup sonra YALNIZ buyukluge "
         "gore siralamak. Bu kitabin acilis bacaklari ESIT BUYUKLUKTE, yani "
         "siralama tumuyle beraberlik ve Python'un kararli siralamasi `set` "
         "iterasyon sirasini korur - o sira da SUREC BASINA rastgele string "
         "hash tohumuna baglidir.")
HASH_OLCUMU = {
    0: ["C0", "C7", "C2", "C1", "C4", "C5", "C6", "C9", "C8", "C3"],
    1: ["C4", "C3", "C2", "C5", "C0", "C1", "C8", "C7", "C6", "C9"],
    2: ["C8", "C1", "C2", "C9", "C0", "C3", "C4", "C7", "C6", "C5"],
    3: ["C6", "C3", "C4", "C1", "C0", "C7", "C2", "C5", "C8", "C9"],
    4: ["C0", "C5", "C2", "C1", "C6", "C7", "C4", "C3", "C8", "C9"],
}

# --- 2. canlidaki anlami ---
CANLI_ETKI = (
    "Tur yarida kesilirse (API hatasi, oran limiti, zaman asimi, bakiye "
    "yetmemesi) HANGI bacaklarin acildigi KEYFI olur.")
NOTRLUK_BOZULMADI = (
    "Madde 208'in dokumasi acilislari taraf taraf alternatifliyor ve dokuma "
    "SIRALI listeler uzerinde calistigi icin her kesme noktasinda |net| en "
    "fazla BIR bacak. O garanti bozulmadi.")
BOZULAN = (
    "YENIDEN URETILEBILIRLIK: ayni bakiye, ayni piyasa, ayni kod - farkli "
    "sembol bilesimi. Bir arizayi ayni kosullarda tekrarlamak imkansiz, ve "
    "iki kosunun farki 'piyasa mi degisti, kod mu?' sorusuna cevap vermiyor.")
PREFLIGHT_TEHLIKESI = (
    "Ara ara dusen bir preflight, insani uyarilari gormezden gelmeye "
    "alistirir - canliya gercek parayla cikmadan once en tehlikeli aliskanlik.")

# --- 3. duzeltme ---
DUZELTME = ("Her siralamaya SEMBOL ADI ikincil anahtar eklendi: "
            "sorted(set(...)), (-buyukluk, sembol), (-e[2], e[0]).")
BUYUKLUK_SIRASI_DEGISTI = False
"""Birincil anahtar ayni; yalniz beraberlikler alfabetik kiriliyor."""
DOGRULAMA_TOHUM_SAYISI = 6
DOGRULANAN_TEKIL_SIRA = 1
"""Alti ayri PYTHONHASHSEED, TEK bir sira."""
TAKIM_TOHUMLARI = (0, 7, 42)
"""Entegrasyon bu uc hash tohumuyla kosuldu, ucunde de gecti."""

# --- 4. ne degismedi ---
DEGISMEYENLER = {
    "secilen semboller": "secim bu fonksiyonun DISINDA",
    "bacak buyuklukleri": "dokunulmadi",
    "geri test": "emirleri_hesapla yalniz CANLI yolda cagrilir; g33 onu "
                 "hic kullanmaz (backtest paritesi takimda dogrulandi)",
    "strateji ayari": "degismedi",
}
NITELIK = ("Bu bir KAR degisikligi degil, bir GUVENILIRLIK degisikligi. Ama "
           "canli kari dolayli korur: yeniden uretilemeyen bir botun "
           "arizasini teshis edemezsiniz.")

# --- 5. ikinci sizinti (acik eksen) ---
TEMIZ_ORTAM_YONLENDIRILEN = ("DILIM_DURUM_DOSYA", "VOL_GECMIS_DOSYA",
                             "SAGLIK_DOSYA")
TEMIZ_ORTAM_EKSIK = ("TP_DEFTER_DOSYA", "TP_KURULUM_DOSYA")
SIZINTI_SU_AN_ZARARSIZ = (
    "Olculdu: bir_tur icinde o iki defter yalniz YAZILIYOR, hic okunmuyor "
    "(okuyan tek yer carry_izleme). Yani su an zararsiz - bu turda "
    "kararsizligin sebebi BU DEGILDI. Ama bir gun bir okuma eklenirse takim "
    "sessizce KOSU SIRASINA bagimli hale gelir.")

AYAR_DEGISTI = False

YASA1 = ("Kararsiz bir testi 'yesil olana kadar tekrar kos' ile gecmek, bir "
         "kusuru ORTBAS etmektir: bu turda kararsizligin sebebi CANLI yolda "
         "belirlenimsiz bir emir sirasiydi.")
YASA2 = ("Bir siralama, birincil anahtarda BERABERLIK varsa siralama "
         "DEGILDIR: esit buyuklukteki bacaklar `sorted(key=-buyukluk)` "
         "altinda hash sirasinda kalir. Kararli siralama, beraberligi "
         "cozmez - SAKLAR.")
YASA3 = ("Notrluk korunurken yeniden uretilebilirlik kaybedilebilir: madde "
         "208'in garantisi bu kusurda hic bozulmadi, bozulan sey bir "
         "arizanin TEKRARLANABILIRLIGIYDI - ve o, garantinin olcmedigi bir "
         "seydir.")
YASA4 = ("Bir test fikstürü, urunun yazdigi HER dosyayi yonlendirmezse "
         "takim kosu-sirasina bagimli hale gelebilir. Su an okunmayan bir "
         "dosya, yarin okunur.")


# ---------------------------------------------------------------- HÜKÜM

def test_kararsiz_miydi() -> bool:
    return TEKRAR_KOSUDA_GECTI and len(DUSEN_TESTLER) == 3


def hash_sirasi_rastgele_miydi() -> bool:
    """Bes tohum bes AYRI sira verdi mi?"""
    return len({tuple(v) for v in HASH_OLCUMU.values()}) == len(HASH_OLCUMU)


def duzeltme_belirlenimli_mi() -> bool:
    return DOGRULANAN_TEKIL_SIRA == 1 and DOGRULAMA_TOHUM_SAYISI >= 5


def buyukluk_sirasi_korundu_mu() -> bool:
    return BUYUKLUK_SIRASI_DEGISTI is False


def notrluk_bozulmus_muydu() -> bool:
    return False


def geri_test_etkilendi_mi() -> bool:
    return False


def sizinti_su_an_zararli_mi() -> bool:
    return False


def ayar_degisti_mi() -> bool:
    return AYAR_DEGISTI


def hukum() -> str:
    return ("DUZELTILDI: `emirleri_hesapla` esit buyuklukteki bacaklari "
            "SUREC BASINA rastgele sirada donduruyordu (alti tohum, alti "
            "sira). Canlida sonucu: tur yarida kesilirse HANGI bacaklarin "
            "acildigi keyfi - kitap madde 208 sayesinde NOTR kalir ama "
            "canli davranis YENIDEN URETILEMEZ, ve entegrasyon takimi bu "
            "yuzden ara ara dusuyordu. Her siralamaya sembol adi ikincil "
            "anahtar eklendi; alti tohumda TEK sira, takim uc ayri tohumda "
            "gecti. Secim, buyuklukler, geri test ve strateji ayari "
            "DEGISMEDI. Bu bir kar degisikligi degil GUVENILIRLIK "
            "degisikligidir.")


# ---------------------------------------------------------------- RAPOR

def yaz() -> None:
    print(__doc__)
    print("KAYNAK: %s" % KAYNAK)
    print("DUSEN TESTLER:")
    for t in DUSEN_TESTLER:
        print("   - %s" % t)
    print("   tekrar kosuda gecti mi: %s -> test KARARSIZ miydi: %s"
          % (TEKRAR_KOSUDA_GECTI, test_kararsiz_miydi()))
    print("   kolay yol: %s" % KOLAY_YOL)

    print("\n1) SEBEP (%s):" % FONKSIYON)
    print("   %s" % SEBEP)
    print("   OLCUM - ayni girdi, bes PYTHONHASHSEED:")
    for s, v in sorted(HASH_OLCUMU.items()):
        print("     %d -> %s" % (s, ", ".join(v)))
    print("   sira rastgele miydi: %s (%d tohum, %d ayri sira)"
          % (hash_sirasi_rastgele_miydi(), len(HASH_OLCUMU),
             len({tuple(v) for v in HASH_OLCUMU.values()})))

    print("\n2) CANLIDAKI ANLAMI:")
    print("   %s" % CANLI_ETKI)
    print("   NOTRLUK: %s" % NOTRLUK_BOZULMADI)
    print("   -> notrluk bozulmus muydu: %s" % notrluk_bozulmus_muydu())
    print("   BOZULAN: %s" % BOZULAN)
    print("   PREFLIGHT: %s" % PREFLIGHT_TEHLIKESI)

    print("\n3) DUZELTME: %s" % DUZELTME)
    print("   %d tohum -> %d tekil sira | belirlenimli mi: %s"
          % (DOGRULAMA_TOHUM_SAYISI, DOGRULANAN_TEKIL_SIRA,
             duzeltme_belirlenimli_mi()))
    print("   buyukluk sirasi korundu mu: %s" % buyukluk_sirasi_korundu_mu())
    print("   entegrasyon tohumlari %s -> ucunde de gecti" % list(TAKIM_TOHUMLARI))

    print("\n4) NE DEGISMEDI:")
    for k, v in DEGISMEYENLER.items():
        print("   %-22s %s" % (k + ":", v))
    print("   geri test etkilendi mi: %s" % geri_test_etkilendi_mi())
    print("   NITELIK: %s" % NITELIK)

    print("\n5) IKINCI SIZINTI (acik eksen):")
    print("   temiz_ortam yonlendiriyor: %s" % list(TEMIZ_ORTAM_YONLENDIRILEN))
    print("   temiz_ortam EKSIK      : %s" % list(TEMIZ_ORTAM_EKSIK))
    print("   %s" % SIZINTI_SU_AN_ZARARSIZ)
    print("   su an zararli mi: %s" % sizinti_su_an_zararli_mi())

    print("\n6) AYAR degisti mi: %s" % ayar_degisti_mi())
    print("\nYASA 1: %s" % YASA1)
    print("YASA 2: %s" % YASA2)
    print("YASA 3: %s" % YASA3)
    print("YASA 4: %s" % YASA4)
    print("\nHUKUM: %s" % hukum())


if __name__ == "__main__":
    yaz()
