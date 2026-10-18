#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 333 — **CANLI PARA BOTUNUN REZERV BOYUTLANDIRMASINI DENETLEYEN
ENTEGRASYON TESTİ KARARSIZ ÇIKTI; SEBEP BLOKTA DA SAATTE DE DEĞİL, VE
BUNU TEŞHİS ETMEYİ ENGELLEYEN ŞEY TESTİN KENDİ RAPORLAMASIYDI. AYRICA
ÜÇ ÖLÇÜM HATAM VAR — ÜÇÜ DE KENDİ ARAÇLARIMDA.**

*** BU DOSYA 2026-10-19'DA TRANSKRİPTTEN YENİDEN YAZILDI (madde 335).
Özgün hâli konteyner kaybında gitti. Madde 334'ün elemeleri de
buraya işlendi. ***

═══ 0. NASIL ORTAYA ÇIKTI ═══

Madde 332'nin doğrulama adımında `test_carry_entegrasyon.py` şunu
verdi:

    BASARISIZ: 1
      - uç funding'li coine DAHA BÜYÜK pozisyon açıldı       (blok 11e)

Aynı kodla bir sonraki koşuda **hepsi geçti**. Kararsız olan şey,
**canlı para botunun fırsat rezervi boyutlandırması** (madde 156).

═══ 1. ÜÇ ÖLÇÜM HATAM (hepsi kendi araçlarımda) ═══

**HATA 1 — BORULU ÇIKIŞ KODU.** Paketi `python3 test_... | tail -3` ile
koşturuyordum; bir boru hattının çıkış kodu **son komutun** kodudur,
yani **tail'in**. Paket `sys.exit(1)` verirken ben "çıkış 0" diye okudum
ve bu oturumda **"entegrasyon geçti (çıkış 0)" diye rapor ettim.**

**HATA 2 — `pkill -f` KENDİ KABUĞUMU ÖLDÜRDÜ.** `-f` tüm komut satırını
eşler ve **benim komutumun kendi satırı o dizgeyi içeriyordu** → kabuk
kendini öldürdü (çıkış 144) ve aynı komutta yazılacak betik hiç
oluşmadı.

**HATA 3 — `| tail` ARTIMLI ÇIKTIYI SAKLADI.** tail **bitene kadar
hiçbir şey basmıyor**; 15 dakika "çıktı yok" görüp koşunun takıldığını
sandım.

═══ 2. KARARSIZLIĞIN KAYNAĞI — DÖRT ADAY ELENDİ ═══

**BLOK KENDİSİ DEĞİL.** 11e'nin hesabı izole edilip **20 kez** koşuldu:
20/20 geçer · uc 55,6 (min=max) · dig 22,2 (min=max) · n_dig 10 ·
oran **2,500** (min=max) — eşik 1,5, yani marj **%67**.

**SAAT DEĞİL.** `time.time` 8 saatlik ödeme ızgarasının **16 noktasına**
(30 dk adım) sabitlendi: 16/16 geçer, hepsi birebir aynı (n_emir 24
dahil). Madde 262'nin tarihe bağlı kararsız test ailesinden **değil**.

**(MADDE 334) `cb` MODÜL GLOBALLERİ DEĞİL.** Paket 11e'nin **tam
içinde** durdurulup `cb`nin **60 global sabiti** anlık görüntülendi ve
paket sonundakiyle karşılaştırıldı: **60'ın 60'ı aynı.** Yalnızca altı
**geçici dizin yolu** farklı — `temiz_ortam()` her çağrıda yeni
`mkdtemp` açtığı için beklenen. 638. satırdaki `SAGLIK_MODU = "durdur"`
ataması da varsayılanla **aynı değerde**, yani sızıntı değil. Madde
333'ün "ilk bakılacak yer"i (yarım izolasyon) **ÇÜRÜDÜ**.

**(MADDE 334) `PYTHONHASHSEED` DEĞİL.** Çok iyi uyuyordu: hash tohumu
**süreç başına** değişir ve yukarıdaki 20 tekrar ile 16 noktalı tarama
**tek süreçte** koşmuştu, yani tek tohumla; sembol seçiminde bir
eşitliği set yineleme sırası bozuyorsa sonuç koşudan koşuya değişirdi.
**15 ayrı süreçte 15 ayrı tohumla** ölçüldü (0..9, 11, 17, 23, 42, 99):
**hepsi birebir aynı** ve LONG alınan sembol listesi bile aynı.

**KALAN: YÜK/ZAMANLAMA.** Düşen koşu, CPU'yu doyuran motor koşularıyla
**aynı andaydı**. Kodda süre temelli kesinti (deadline/timeout/
perf_counter) **arandı, bulunmadı** — ama bu yükün etkisiz olduğunu
kanıtlamaz. Paket üç CPU yükü altında altı kez koşturulmak üzere
başlatıldı; **konteyner kaybı o koşuyu kesti**, sonuç alınamadı.

═══ 3. ASIL KUSUR — TEST KENDİ TEŞHİSİNİ ENGELLİYORDU ═══

`kontrol(ad, kosul, detay)` ayrıntıyı **yalnızca HATA'da** basıyordu.
Sonuç: düşen koşunun sayıları **elde yok**; geçen koşuların sayıları da
basılmadığı için **kıyaslanacak taban da yok.**

**DÜZELTME:**
  - `kontrol(..., her_zaman=True)` → detay GEÇSE DE basılır.
  - 11e artık her koşuda bir `[tani]` satırı basıyor:
    `uc · dig · n_dig · n_emir · oran`.

Böylece bir sonraki düşme, sebebini yanında taşır.

═══ 4. AÇIK EKSEN (dürüst) ═══

**Kararsızlığın kök nedeni BULUNMADI.** Elenenler: blok (20/20), saat
(16/16), `cb` globalleri (60/60 aynı), hash tohumu (15/15 aynı). Kalan:
**yük/zamanlama** — ve o ölçüm konteyner kaybında kesildi.

AYAR DEĞİŞMEDİ. Bu madde bir **test sağlamlaştırması** ve üç ölçüm
hatamın kaydı.
"""

from __future__ import annotations

YENIDEN_YAZILDI = True

# ───────── 0. OLAY
BLOK = "11e) FIRSAT REZERVI TAM TURDA (madde 156)"
DUSEN_KONTROL = "uç funding'li coine DAHA BÜYÜK pozisyon açıldı"
NE_DENETLIYOR = ("canli para botunun firsat rezervi boyutlandirmasi: uc "
                 "funding'li bir coine gercekten DAHA BUYUK pozisyon "
                 "aciliyor mu (madde 156)")
GOZLENEN_SIKLIK = "1/4 tam paket kosusu (o oturumda)"

# ───────── 1. ÜÇ ÖLÇÜM HATAM
OLCUM_HATALARIM = {
    "borulu cikis kodu": (
        "`python3 test_... | tail -3`; boru hattinin cikis kodu SON "
        "komutun kodudur, yani tail'in. Paket sys.exit(1) verirken "
        "'cikis 0' okudum ve 'entegrasyon gecti' diye RAPOR ETTIM.",
        "bir paketin cikis kodu BORUSUZ okunur"),
    "pkill -f kendini vurdu": (
        "`pkill -f <dizge>`; -f tum komut satirini esler ve BENIM "
        "komutumun satiri o dizgeyi iceriyordu -> kabuk kendini oldurdu "
        "(144) ve ayni komutta yazilacak betik hic olusmadi.",
        "dizge eslesmeli surec oldurme CAGIRAN komutu da esler; PID ile"),
    "tail artimli cikti sakladi": (
        "`| tail -32` ile baslattim; tail BITENE KADAR hicbir sey "
        "basmaz, 15 dakika 'cikti yok' gorup takildi sandim.",
        "artimli izlenecek kosu dogrudan DOSYAYA yazdirilir"),
}

# ───────── 2. ELENENLER
IZOLE_TEKRAR = {"n": 20, "gecen": 20, "uc": (55.6, 55.6),
                "dig": (22.2, 22.2), "n_dig": [10],
                "oran": (2.500, 2.500), "esik": 1.5}
SAAT_TARAMASI = {"nokta": 16, "adim_dk": 30, "gecen": 16,
                 "uc": (55.6, 55.6), "dig": (22.2, 22.2),
                 "n_dig": [10], "n_emir": [24]}
ELENEN_334 = {
    "cb modul globalleri (YARIM IZOLASYON)": (
        "paket 11e'nin TAM ICINDE durdurulup cb'nin BUTUN 60 global "
        "sabiti anlik goruntulendi ve paket sonundakiyle karsilastirildi: "
        "ALTMISININ ALTMISI AYNI. Yalnizca alti GECICI DIZIN yolu farkli "
        "(temiz_ortam() her cagrida yeni mkdtemp acar - BEKLENEN). "
        "SAGLIK_MODU'nun 638. satirdaki atamasi da varsayilanla AYNI.",
        "ELENDI: madde 333'un 'ilk bakilacak yer'i YANLIS"),
    "PYTHONHASHSEED (string hash rastgeleligi)": (
        "hash tohumu SUREC BASINA degisir ve 20 tekrar ile 16 noktali "
        "tarama TEK SUREC'te kosmustu. 15 ayri surecte 15 ayri tohumla "
        "olculdu: HEPSI BIREBIR AYNI (oran 2,500) ve LONG alinan sembol "
        "listesi de ayni.",
        "ELENDI: hash tohumu etkisiz"),
}
HIZLI_KOSUM_DUZENI = ("madde 334'un araci: paketin SADECE tanim oneki "
                      "(blok 1'den oncesi) exec edilip 11e hesabi "
                      "yapiliyor - tam paket ~10-15 dk iken bu ~saniyeler")
KALAN_ADAY = ("YUK/ZAMANLAMA: dusen kosu CPU'yu doyuran motor "
              "kosulariyla AYNI ANDAYDI. Kodda sure temelli kesinti "
              "ARANDI, BULUNMADI - ama bu yukun etkisiz oldugunu "
              "KANITLAMAZ. Uc CPU yuku altinda alti kosuluk deneme "
              "BASLATILDI ama KONTEYNER KAYBI onu kesti.")
OLCUM_KESILDI_MI = True

# ───────── 3. ASIL KUSUR
ASIL_KUSUR = ("kontrol(ad, kosul, detay) ayrintiyi YALNIZCA HATA'da "
              "basiyordu: dusen kosunun sayilari elde YOK, gecen "
              "kosularin sayilari da basilmadigi icin KIYASLANACAK TABAN "
              "da yok.")
DUZELTME = {
    "kontrol(..., her_zaman=True)": "detay GECSE DE basilir",
    "11e [tani] satiri": "uc · dig · n_dig · n_emir · oran, HER kosuda",
}
BEKLENEN = {"uc": 55.6, "dig": 22.2, "n_dig": 10, "n_emir": 24}

# ───────── 4. AÇIK EKSEN
ACIK_EKSEN = ("kok neden BULUNMADI. Elenenler: blok (20/20), saat "
              "(16/16), cb globalleri (60/60 ayni), hash tohumu (15/15 "
              "ayni). Kalan: yuk/zamanlama - ve o olcum konteyner "
              "kaybinda KESILDI, YAPILMADI.")
AYAR_DEGISTI = False

YASA1 = ("Bir paketin cikis kodu BORUSUZ okunur: `| tail` koyan, "
         "olctugu seyi degistirir ve 'gecti' diye yanlis rapor ettirir.")
YASA2 = ("Kararsiz bir kontrolun olcumu HER KOSUDA kayda gecer; "
         "yalnizca duserken basilan bir sayi, dustugunde zaten yoktur.")
YASA3 = ("Bir kararsizligin kok nedeni bulunamadiysa, en azindan bir "
         "dahaki dusmenin TESHIS EDILEBILIR olmasi saglanir.")
YASA4 = ("Dizge eslesmeli surec oldurme CAGIRAN komutun kendisini de "
         "esler; uzun kosular PID ile durdurulur.")
YASA5 = ("Bir hipotez 'muhtemel' diye elenmez, OLCULEREK elenir: dort "
         "aday (blok, saat, globaller, hash tohumu) dordu de olcumle "
         "elendi - ve ikisi cok ikna ediciydi.")


# ───────── DOĞRULAMA
def izole_deterministik_mi():
    t = IZOLE_TEKRAR
    return (t["gecen"] == t["n"] and t["uc"][0] == t["uc"][1]
            and t["oran"][0] == t["oran"][1])


def marj_genis_mi():
    return IZOLE_TEKRAR["oran"][0] / IZOLE_TEKRAR["esik"] > 1.6


def saat_bagimli_degil_mi():
    s = SAAT_TARAMASI
    return (s["gecen"] == s["nokta"] and s["uc"][0] == s["uc"][1]
            and s["n_emir"] == [24])


def madde262_ailesinden_mi():
    return False


def uc_olcum_hatasi_kayitli_mi():
    return len(OLCUM_HATALARIM) == 3


def yanlis_rapor_ettigimi_yazdim_mi():
    return "RAPOR ETTIM" in OLCUM_HATALARIM["borulu cikis kodu"][0]


def asil_kusur_raporlamada_miydi():
    return "YALNIZCA HATA'da" in ASIL_KUSUR


def dort_aday_elendi_mi():
    return len(ELENEN_334) == 2        # + blok ve saat = dort


def kok_neden_bulundu_mu():
    return False


def olcum_kesildi_mi():
    return OLCUM_KESILDI_MI and "KESILDI" in ACIK_EKSEN


def bir_dahaki_dusme_teshis_edilebilir_mi():
    return "[tani] satiri" in " ".join(DUZELTME)


def hukum():
    return {
        "ne_kararsiz": "11e - canli rezerv boyutlandirmasi (madde 156)",
        "izole": "20/20 birebir, oran 2,500 (esik 1,5)",
        "saat": "16/16 birebir",
        "cb_globalleri": "60/60 AYNI (madde 334)",
        "hash_tohumu": "15/15 birebir (madde 334)",
        "kalan": "yuk/zamanlama - olcum KESILDI",
        "asil_kusur": "detay yalnizca HATA'da basiliyordu",
        "kok_neden": "BULUNMADI (acik eksen)",
        "olcum_hatam": 3,
        "ayar_degisti_mi": False,
    }


def yaz():
    print(__doc__)
    print("OLCUM HATALARIM")
    for k, (ne, yasa) in OLCUM_HATALARIM.items():
        print("  %-26s %s" % (k, yasa))
    print("\nELENENLER (madde 334)")
    for k, (ne, son) in ELENEN_334.items():
        print("  %-42s %s" % (k, son))
    print("\nHUKUM")
    for k, v in hukum().items():
        print("  %-22s %s" % (k, v))


if __name__ == "__main__":
    yaz()
