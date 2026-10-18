"""ÖN KAYITLI KARAR KURALI (madde 212).

Bu proje boyunca her parametre/sinyal kararı aynı kurala bağlıydı ama
kural sadece PROSE olarak yazılıydı. Madde 212'de kuralın bir DELİĞİ
bulundu: bir varyant (`wins` - uçları kırpılmış funding ortalaması) iki
dönemde de Sharpe'ı yükseltip düşüşü tolerans içinde tutarak kuralı
GEÇTİ, ama getiriyi 7,5 puan düşürüp düşüşü 1,75 puan derinleştirdiği
için **eşit riskte** +94,7 → +78,3'e geriletiyordu. Yani kural "daha
kötü"ye EVET diyordu.

Kural artık burada, çalıştırılabilir halde. Yeni bir aday ölçüldüğünde
`gecer_mi()` çağrılır; prose'a bakıp yorumlamak yok.

DÖRT ŞART (hepsi gerekli):
  1. İKİ DÖNEMDE de Sharpe iyileşsin (2022-24 ve 2025-26). Tek dönemde
     iyileşme, dönem seçmekten (period picking) ayırt edilemez.
  2. Maksimum düşüş TOLERANS puanından fazla kötüleşmesin (varsayılan 3).
  4. EŞİT RİSK İÇİN KALDIRAÇ GEREKMESİN (madde 225). Şart 3 adayı
     kontrolün düşüşüne getirirken kaldıraç kullanır; 1'in üstünde bir
     kaldıraç, üstünlüğün ancak borsada gerçekten borçlanarak
     toplanabileceği anlamına gelir. Motor likidasyonu modellemez, yani
     kıyas modellenen getiriyi modellenmeyen bir tehlikeye karşı
     fiyatlar. Böyle bir aday parametre kararı değil KALDIRAÇ kararıdır.
  3. EŞİT RİSKTE getiri düşmesin (madde 212). Getiri düşüşle
     ölçeklenir: kaldıraç Sharpe'ı değiştirmez, ölçeği değiştirir -
     bu yüzden iki kitabı ancak aynı düşüşe getirerek karşılaştırmak
     adil olur.

ŞART 3 TEK BAŞINA KABUL ETTİRMEZ (MADDE 223). Şart 3'ün ÖRNEKLEME
HATASI, şart 1'inkinden kat kat büyüktür. Madde 223'te 5 aday tutma
süresi ölçüldü; eşli blok bootstrap (1.504 gün, 21 günlük blok, 2.000
örnek) iki şartın belirsizliğini yan yana koydu:

  aday      ΔSharpe [p5, p95]      Δeşit-risk getiri [p5, p95]
  3 gün   −0.087 [−0.31, +0.12]     −5,7 puan [−43,6, +37,8]
  4 gün   −0.066 [−0.19, +0.04]     −5,0 puan [−28,8, +16,9]

Şart 1'in aralığı ±0,2 Sharpe; şart 3'ün aralığı **±40 PUAN getiri**.
3 ve 4 gün tam örneklemde eşit riskte +3,9 / +3,7 puan DAHA getiriyordu
(şart 3'ü geçtiler) ama bootstrap ortalaması işareti ÇEVİRDİ (−5,7 /
−5,0) - o kazanç gürültüydü. Onları reddeden şart 1 oldu.

Kural olarak: şart 3 bir VETO'dur (madde 212'de `wins`'i reddetmek için
kondu), bir kabul gerekçesi DEĞİLDİR. Bir aday yalnızca şart 3'ten
geçiyor ve şart 1'de kaybediyorsa, cevap "eşit riskte daha iyi" değil
"ayırt edilemez"dir; kabul için şart 1 ŞARTTIR.

MADDE 242 — DÖRT ŞARTIN EN NET GEREKÇESİ, DÖRT BOYUTTA BİRDEN. Madde
223 şart 3'ün tek bir parametre için nasıl yanlış yöne çektiğini
göstermişti. Madde 242 bir 2^4 faktöriyel koştu (TPL × HAVUZ × UCELE ×
REZERV; dördünün de komşusu tek tek ölçüldüğünde eşit-riski YUKARI
gösteriyordu) ve 16 hücrenin hepsinde aynı deseni buldu:

  15 alternatif hücrenin TAMAMI: eşit-risk merkezin ÜSTÜNDE
  (+%113,5..+%134,3), Sharpe merkezin ALTINDA (2,830..2,941), 22-24
  Sharpe merkezin ALTINDA, kaldıraç >= 1,02x.
  Kaldıraçsız kalan tek hücre MERKEZİN KENDİSİ (1/16).

Merkez Sharpe'ta **1/16**, eşit-riskte **16/16**. Yani şart 3 bir kabul
gerekçesi olsaydı ve şart 4 olmasaydı, kural küpün **en uzak köşesine**
yürürdü (eşit-risk +%134,3) — ve o köşe küpteki **en düşük Sharpe'a**
(2,830) sahip, 1,24x kaldıraç istiyor, ve eşli blok bootstrap kazancını
**−2,7 puana** çeviriyor (P %46,0).

Yan bulgu (yöntem için önemli): en büyük ikili etkileşim Sharpe'ta
+0,004, en büyük ana etki −0,065 — etkileşim ana etkinin %6'sı. Yerel
parametre adımları TOPLAMSALDIR, yani projenin tek-parametre tarama
disiplini optimumun yakınında yeterlidir. (Katman aç/kapa sıçramaları
ise etkileşir: madde 238.) Araç: `arastirma_faktoriyel.py`.

MADDE 248 — KURALIN KENDİ SİCİLİ ÖLÇÜLDÜ. Dört şarttan hangisi fiilen
bağlayıcı? Makineyle çıkarıldı: madde 239 (prim brütü), 242 (en uzak
köşe), 244 (üst trader kolu) — **hepsi ŞART 1'den** düşüyor; 240'ın
rezerv eşikleri şart 3'ten. **Şart 4 hiçbir adayda belirleyici oy
olmadı** (onu kıran her aday şart 1'i de kırıyordu), ve yalnız şart
3/4'ten düşen grubun kazancı +0,3 puan. Yani şart 4'ü gevşetmenin
ölçülmüş ödülü sıfıra yakın.

ŞART 1'İN YANLIŞ RED ORANI: gerçek farkı SIFIR olan bir aday şart 1'i
yalnızca **%22,2** olasılıkla geçer (eşli blok bootstrap, 4.000 örnek;
iki alt dönemin farkları birbirinden bağımsız, korelasyon −0,003;
analitik beklenti 0,5² = %25). Ampirik teyit: %5 rastgele sembol
düşürmeyle kurulmuş sekiz EŞDEĞER kitabın **8'i de** şart 1'den düştü.

BU KURALI GEVŞETMEZ: reddedilen adayları BOOTSTRAP da bağımsız olarak
ayırt edilemez buldu (239: +22,2 puan P %79,0 · 244: +8,5 P %64,5 ·
235: +3,3 P %58,5 · 242: −2,7 P %46,0). Şart 1'in sertliği ölçülebilir
bir şey maliyet etmedi; asıl kapı bootstrap.

AMA RAPOR DİLİNİ DEĞİŞTİRİR: **"RED" demek "daha kötü" demek DEĞİL,
"iki dönemde birden GÖSTERİLEMEDİ" demek.** Beş eşdeğer adaydan dördü
bu şarttan düşer. Araç: `arastirma_kural_sicili.py`.

ŞART 3 NEDEN GEREKLİ: Sharpe günlük getirinin ortalama/std'si, maksimum
düşüş ise YOLA bağlı. Bir varyant oynaklığı düşürüp Sharpe'ı yükseltirken
düşüşü derinleştirebilir (uzun ve yavaş bir düşüş, kısa ve keskin bir
düşüşten daha derin olabilir). O zaman kaldıraçla eşit riske getirildiğinde
daha AZ para verir. `wins` tam olarak buydu.
"""
from __future__ import annotations

from dataclasses import dataclass

KALDIRAC_TOLERANS = 1.005
"""Şart 4 (madde 225) kaç kata kadar "kaldıraç yok" saysın.

Madde 226: `esit_risk_gercek` ikili arama yapar ve 1,0'i tam tutturamaz;
150M adayı 1,0005x çıkıp şart 4'ten YANLIŞ yere RED aldı. Kararı
değiştirmedi (zaten 1. ve 3. şarttan düşüyordu) ama bir sonraki iyi
adayı eleyebilirdi. İki haneye yuvarlanınca 1,00 olan bir kaldıraç,
kaldıraç değildir."""

DUSUS_TOLERANS = 3.0
"""Maksimum düşüş kaç PUAN kötüleşebilir. Madde 188: doz kararları
bootstrap p5/p1 ile verilir; buradaki tolerans sadece ELEME eşiği."""


@dataclass(frozen=True)
class Olcum:
    """Bir kitabın ölçümü. Sharpe'lar faz ORTALAMASI olmalı (madde 133.6).

    getiri : yıllık yüzde (ör. 96.8)
    sharpe : tam dönem Sharpe
    erken  : 2022-24 Sharpe
    gec    : 2025-26 Sharpe
    dusus  : maksimum düşüş, POZİTİF puan olarak (ör. 13.7)
    """
    ad: str
    getiri: float
    sharpe: float
    erken: float
    gec: float
    dusus: float

    def esit_risk_getiri(self, hedef_dusus: float) -> float:
        """Düşüşü `hedef_dusus`a ölçeklenince getiri ne olur (YAKLAŞIK).

        MADDE 218 - BU DOĞRUSAL YAKLAŞIM YANLIŞ TARAFA SAPAR. Bileşik bir
        seride kaldıraç k, yıllık getiriyi k ile ÇARPMAZ: günlük getiriler
        k katına çıkınca bileşik yıllık getiri **konveks** büyür (%0,1/gün
        → +%44/yıl, %0,2/gün → +%107/yıl - iki katı değil 2,4 katı).
        Doğrusal ölçekleme bu konveksliği kaçırır ve DÜŞÜK oynaklıklı bir
        adayı olduğundan kötü gösterir.

        Madde 218'de bu bir kararı TERSİNE çevirdi: çapraz kitap harmanı
        doğrusal hesapla +%91,1 (RED) görünürken gerçek kaldıraçla
        +%103,4 (KABUL) çıktı.

        Bu yüzden asıl karar `gecer_mi(..., gunluk_a=, gunluk_b=)` ile
        GÜNLÜK SERİLER verilerek alınır; o zaman kaldıraç gerçekten
        uygulanır. Seri yoksa bu yaklaşım kullanılır ve `gecer_mi`
        sonucunda `yaklasik=True` işaretlenir.
        """
        if self.dusus <= 0:
            return float("nan")
        return self.getiri * hedef_dusus / self.dusus


def _stat(r) -> tuple[float, float]:
    """Günlük getiri serisinden (yıllık getiri, POZİTİF maks düşüş)."""
    import numpy as np
    r = np.asarray([x for x in r if x == x], dtype=float)
    if r.size < 30:
        return float("nan"), float("nan")
    e = np.cumprod(1.0 + r)
    yil = e[-1] ** (365.25 / r.size) - 1.0
    dd = -float((e / np.maximum.accumulate(e) - 1.0).min())
    return float(yil), dd


def esit_risk_gercek(gunluk, hedef_dusus_puan: float,
                     alt: float = 0.05, ust: float = 8.0) -> tuple:
    """Günlük seriyi GERÇEKTEN kaldıraçlayıp düşüşü hedefe eşitler.

    `hedef_dusus_puan` PUAN cinsindendir (ör. 13.70), `_stat` ise KESİR
    döner (0.1370). Madde 218'de ilk sürüm bu ikisini karıştırdı: kesir
    her zaman puandan küçük olduğu için ikili arama kaldıracı üst sınıra
    (10x) dayadı ve +%4.045 gibi saçma sonuçlar verdi. Birim hatası
    sonucu SAÇMA yaptığı için yakalandı - sessiz kalabilirdi.

    Döner: (kaldıraç, eşit riskteki yıllık getiri PUAN, ulaşılan düşüş PUAN).
    """
    import numpy as np
    r = np.asarray([x for x in gunluk if x == x], dtype=float)
    hedef = hedef_dusus_puan / 100.0            # PUAN -> KESİR
    if r.size < 30 or hedef <= 0:
        return float("nan"), float("nan"), float("nan")
    # tam kaldıraçsız hâli hedeften zaten derinse kaldıraç 1'in altına iner
    for _ in range(80):
        k = (alt + ust) / 2.0
        _, dd = _stat(k * r)
        if not (dd == dd):
            return float("nan"), float("nan"), float("nan")
        if dd < hedef:
            alt = k
        else:
            ust = k
    k = (alt + ust) / 2.0
    y, dd = _stat(k * r)
    return k, y * 100.0, dd * 100.0


# ======================================================================
# MADDE 255: COK BAKIS DUZELTMESI - sart 1'in AYNASI
# ======================================================================
# Madde 248 sart 1'in YANLIS RED oranini olctu: gercek farki sifir olan bir
# aday sart 1'i yalnizca %22,2 olasilikla gecer, yani %77,8 yanlis red.
# AMA bunun aynasi hic hesaplanmamisti: bir TURDA k varyant denenirse,
# hepsi TAMAMEN ETKISIZ olsa bile en az birinin sart 1'i gecme olasiligi
#
#     P(en az bir gecis) = 1 - (1 - 0,222)^k
#
# k=1  %22,2   k=3  %53,0   k=5  %71,4   k=8  **%86,6**   k=12 %95,1
#
# Madde 255'te 8 varyant denendi ve ikisi sart 1'i gecti - yukaridaki
# hesaba gore BEKLENEN sonuc. Yani COK VARYANTLI bir turda sart 1'i
# gecmek NEREDEYSE HIC DELIL TASIMAZ.
#
# SONUC (madde 248'in "asil kapi bootstrap" tespitinin nicel hali):
#   * sart 1 bir ON SURUDUR, delil degildir;
#   * delil, esli blok bootstrap'in esit-risk farkidir;
#   * ve bir MODEL/TAHMIN adayinda bootstrap IKI kez kosulur:
#     KONTROLE karsi (para getiriyor mu?) VE kendi PLASEBOSUNA karsi
#     (bilgi mi, mekanik mi?). Ikisi ayri sorudur ve ayri cevaplanir.
SART1_NULL_GECME = 0.222          # madde 248'de olculdu

# ======================================================================
# MADDE 258: SART 1'IN UCUNCU YUZU - REJIM ARACLARI
# ======================================================================
# Sart 1 iki alt donemde birden iyilesme ister. Ama madde 231'e gore o iki
# alt donem IKI AYRI REJIMDIR (kirilma 2025-01-01, prim 3,8 kat). Yalnizca
# bir rejimde calisan bir aday - ki bir REJIM ARACI tanim geregi oyledir -
# sart 1'i gecemez. Bu kalibrasyon hatasi degil, tasarimin dogal sonucu.
#
# Madde 258'de olculen ornek: madde 239'un prim-olcekli brutu. Tam ornekte
# bootstrap P %69-79 (esigin alti), AMA rejim ayriminda:
#   dusuk prim (896 gun): +34..+69 puan, P %92,3 / %94,4 / %93,8
#   yuksek prim (608 gun): -3..-13 puan, P %20..%44
#   PLASEBO ayni pencerede P %68,1 -> boru hatti temiz
# Mekanizma aciklanabiliyor: prim-olcekli brut, prim ZATEN yuksekken
# surekli kaldiracli olmak demektir.
#
# SINIFLANDIRMA: bir aday sart 1'i YALNIZCA TEK alt donemde kaybediyor VE
# o donemdeki isareti mekanizmayla aciklanabiliyorsa, "RED" degil
# "REJIM ARACI - KOSULLU" olur. KABUL EDILMEZ (ayar degismez) ama COPE DE
# ATILMAZ: tetigi yazilir ve rejim dondugunde YENIDEN OLCULUR.
# Rejim TAHMINIYLE acilmaz - once olcum, sonra karar.


def rejim_araci_mi(kontrol: "Olcum", aday: "Olcum",
                   boot_p_dusuk: float | None = None,
                   boot_p_yuksek: float | None = None) -> dict:
    """Aday bir REJIM ARACI mi, yoksa duz bir RED mi?

    boot_p_* : o rejimdeki bootstrap P(>0), YUZDE (varsa).
    """
    e = aday.erken > kontrol.erken
    g = aday.gec > kontrol.gec
    tek_donemde = (e != g)                      # biri iyi, oteki kotu
    d = {"sart1_gecti": e and g, "tek_donemde_kaybetti": tek_donemde,
         "iyi_olan_donem": "22-24" if e else ("25-26" if g else None)}
    if boot_p_dusuk is not None:
        d["dusuk_primde_guclu"] = boot_p_dusuk > 80.0
    if boot_p_yuksek is not None:
        d["yuksek_primde_guclu"] = boot_p_yuksek > 80.0
    d["sinif"] = ("GECER" if d["sart1_gecti"] else
                  "REJIM ARACI - KOSULLU" if (tek_donemde and
                                              (boot_p_dusuk or 0) > 80.0)
                  else "RED")
    return d



def cok_bakis_riski(k: int) -> float:
    """k varyant denenirse, HEPSI etkisizken en az birinin sart 1'i gecme
    olasiligi (yuzde). Bir turda kac bakis yapildigi RAPOR EDILMELIDIR."""
    return 100.0 * (1.0 - (1.0 - SART1_NULL_GECME) ** max(0, int(k)))


def delil_mi(k_bakis: int, boot_p_kontrol: float,
             boot_p_plasebo: float | None = None) -> dict:
    """Bir adayin gecisi DELIL mi, cok bakisin gurultusu mu?

    boot_p_* : bootstrap'in P(>0) degerleri, YUZDE.
    Esik: kontrole karsi P>%80 (madde 239'un +22,2/%79,0 reddi bu esigin
    altinda kaldi), plaseboya karsi P>%80.
    """
    return {
        "cok_bakis_riski": cok_bakis_riski(k_bakis),
        "sart1_delil_mi": cok_bakis_riski(k_bakis) < 30.0,
        "kontrole_karsi_guclu": boot_p_kontrol > 80.0,
        "plaseboya_karsi_guclu": (None if boot_p_plasebo is None
                                  else boot_p_plasebo > 80.0),
    }


def gecer_mi(kontrol: Olcum, aday: Olcum,
             tolerans: float = DUSUS_TOLERANS,
             gunluk_kontrol=None, gunluk_aday=None) -> dict:
    """Aday kabul edilir mi? Üç şartın hepsi ayrı ayrı döner.

    Döner: {'gecer': bool, 'sartlar': {ad: (bool, açıklama)},
            'esit_risk': float, 'gerekce': str}
    """
    s = {}
    s["iki dönemde Sharpe"] = (
        aday.erken > kontrol.erken and aday.gec > kontrol.gec,
        f"22-24 {aday.erken:.3f} vs {kontrol.erken:.3f} "
        f"({aday.erken - kontrol.erken:+.3f}), "
        f"25-26 {aday.gec:.3f} vs {kontrol.gec:.3f} "
        f"({aday.gec - kontrol.gec:+.3f})")
    s["düşüş toleransı"] = (
        aday.dusus <= kontrol.dusus + tolerans,
        f"−{aday.dusus:.2f} vs −{kontrol.dusus:.2f} "
        f"({aday.dusus - kontrol.dusus:+.2f} puan, tolerans {tolerans:.1f})")
    # MADDE 218: günlük seri verilirse GERÇEK kaldıraçla, yoksa yaklaşık.
    yaklasik = True
    kaldirac = float("nan")
    if gunluk_aday is not None:
        hedef = kontrol.dusus                    # PUAN
        if gunluk_kontrol is not None:
            _, _dd = _stat(gunluk_kontrol)       # KESİR
            if _dd == _dd:
                hedef = _dd * 100.0              # PUAN'a çevir
        kaldirac, er, _ = esit_risk_gercek(gunluk_aday, hedef)
        if er == er:
            yaklasik = False
        else:
            er = aday.esit_risk_getiri(kontrol.dusus)
    else:
        er = aday.esit_risk_getiri(kontrol.dusus)
    s["eşit riskte getiri"] = (
        er >= kontrol.getiri,
        f"%{er:+.1f} vs %{kontrol.getiri:+.1f} ({er - kontrol.getiri:+.1f} puan)"
        + ("  [YAKLAŞIK - günlük seri verilmedi]" if yaklasik
           else f"  [kaldıraç {kaldirac:.2f}x]"))
    # MADDE 225 - DÖRDÜNCÜ ŞART: eşit riskteki üstünlük KALDIRAÇ
    # GEREKTİRMEMELİ. Şart 3 adayı kontrolün düşüşüne getirmek için
    # kaldıraç kullanır. Kaldıraç 1'in ALTINDAysa (aday daha riskli,
    # kısılıyor) sorun yok. 1'in ÜSTÜNDEyse aday yalnızca NAKİT
    # tuttuğu için daha sığ düşüyordur ve üstünlüğü ancak borsada
    # gerçekten kaldıraç kullanılarak toplanır - yani kıyas, modellenen
    # bir büyüklüğü (getiri) MODELLENMEYEN bir tehlikeye (marj,
    # likidasyon) karşı sessizce fiyatlar. Motor likidasyonu hiç
    # modellemez. Böyle bir aday bir "parametre iyileştirmesi" değil,
    # AYRI bir KALDIRAÇ KARARIdır ve madde 149'un kaldıraç tablosuna
    # karşı verilir.
    # KALDIRAC_TOLERANS: ikili arama 1.0'i tam tutturamaz (madde 226'da
    # 150M adayi 1.0005x cikip YANLIS yere RED aldi - karar degismedi ama
    # bir sonraki iyi aday elenebilirdi). "Iki haneye yuvarlaninca 1.00"
    # olan bir kaldirac, kaldirac degildir.
    # MADDE 227 - IKINCI DUZELTME: aday KALDIRACSIZ hâliyle kontrolü hem
    # getiride hem düşüşte geçiyorsa ortada bir kaldıraç kararı YOKTUR.
    # Şart 4 madde 225'te TEK bir örnekten (nakit kadranı) yazıldı ve
    # fazla genellendi: TPL 0,60 kontrolden hem daha çok kazanıyor hem
    # daha sığ düşüyordu, gereken 1,031x sadece düşüşü kontrolün
    # SEVİYESİNE ÇIKARMAK için — kozmetik. Şart onu YANLIŞ yere eledi.
    _ustun = (aday.getiri >= kontrol.getiri and aday.dusus <= kontrol.dusus)
    _kald_ok = ((not (kaldirac == kaldirac))
                or kaldirac <= KALDIRAC_TOLERANS or _ustun)
    s["kaldıraç gerektirmiyor"] = (
        _kald_ok,
        f"eşit risk için gereken kaldıraç {kaldirac:.3f}x"
        + ("  [aday kaldıraçsız zaten ÜSTÜN - kaldıraç kozmetik]"
           if (_ustun and kaldirac > KALDIRAC_TOLERANS) else "")
        + ("" if _kald_ok
           else " — bu bir PARAMETRE kararı değil KALDIRAÇ kararıdır "
                "(madde 225); madde 149 tablosuna karşı ayrıca verilmeli"))
    gecer = all(v[0] for v in s.values())
    dusen = [k for k, v in s.items() if not v[0]]
    return {"gecer": gecer, "sartlar": s, "esit_risk": er,
            "yaklasik": yaklasik, "kaldirac": kaldirac,
            "gerekce": ("dört şartın hepsi geçti" if gecer
                        else "geçmeyen şart: " + ", ".join(dusen))}


def yaz(kontrol: Olcum, adaylar: list[Olcum],
        tolerans: float = DUSUS_TOLERANS) -> str:
    """Karar tablosu - bir turun sonucunu olduğu gibi yazdırmak için."""
    s = ["=" * 78, f"ÖN KAYITLI KARAR KURALI — kontrol: {kontrol.ad}", "=" * 78,
         f"{'aday':14s} {'getiri':>7s} {'Sharpe':>7s} {'22-24':>6s} "
         f"{'25-26':>6s} {'düşüş':>7s} {'eşit-risk':>10s}  karar",
         f"{kontrol.ad:14s} {kontrol.getiri:+7.1f} {kontrol.sharpe:7.3f} "
         f"{kontrol.erken:6.3f} {kontrol.gec:6.3f} {-kontrol.dusus:7.2f} "
         f"{kontrol.getiri:+10.1f}  KONTROL"]
    for a in adaylar:
        r = gecer_mi(kontrol, a, tolerans)
        s.append(f"{a.ad:14s} {a.getiri:+7.1f} {a.sharpe:7.3f} {a.erken:6.3f} "
                 f"{a.gec:6.3f} {-a.dusus:7.2f} {r['esit_risk']:+10.1f}  "
                 f"{'KABUL' if r['gecer'] else 'RED'}")
    s.append("")
    for a in adaylar:
        r = gecer_mi(kontrol, a, tolerans)
        if not r["gecer"]:
            s.append(f"  {a.ad}: {r['gerekce']}")
            for k, (ok, aciklama) in r["sartlar"].items():
                if not ok:
                    s.append(f"      {k}: {aciklama}")
    s.append("=" * 78)
    return "\n".join(s)


# Madde 212'nin kendi tablosu - kuralın DELİĞİNİ bulan ölçüm. Regresyon
# kaydı olarak burada duruyor; `wins` satırı şart 1 ve 2'yi geçip şart
# 3'te düşen TEK örnek.
MADDE_212 = {
    "kontrol": Olcum("ort (48sa)", 94.7, 2.970, 2.870, 3.130, 15.45),
    "adaylar": [
        Olcum("med", 83.6, 2.860, 2.675, 3.130, 14.10),
        Olcum("tstat", 70.3, 2.150, 2.040, 2.310, 19.70),
        Olcum("ewma", 92.2, 2.885, 2.705, 3.140, 15.00),
        Olcum("wins", 87.2, 3.005, 2.925, 3.145, 17.20),
        Olcum("blend30", 76.3, 2.810, 2.755, 2.905, 16.25),
        Olcum("blend50", 72.7, 2.715, 2.635, 2.840, 16.60),
    ],
}


if __name__ == "__main__":
    print(yaz(MADDE_212["kontrol"], MADDE_212["adaylar"]))

# ---------------------------------------------------------------- MADDE 286
# ASGARI SAPTANABILIR ETKI (ASE) — madde 285'te olculdu, burada ON FILTRE.
#
# NEDEN BURADA: madde 285, kitabin oynakligi + 4,1 yillik veri + %80 kanit
# bari birlikte bir MINIMUM ETKI BUYUKLUGU tanimladigini olctu (~+13 puan
# doz olcutunde). Bunun altindaki bir aday YANLIS degil, KARARLASTIRILAMAZ.
# Madde 285'e kadar bu, her turun SONUNDA ogreniliyordu; 13 motor kosumu
# yapip "P(>0) %67,5, bar %80" demek pahali. Artik BASTA sorulabilir.
ASE_PUAN = 13.0
"""Doz olcutunde, bu veri tabaninda %80 barini gecebilecek asgari etki.

Madde 285'in turetmesi: olculen +7,22 puan P(>0) %67,5 verdi; %80 icin
z 0,454 -> 0,842, yani etki 1,9 kat veya veri 3,44 kat buyumeli.
+7,22 x 1,9 ~ +13,4 puan.

*** MADDE 288 - BU SABIT YANLIS. TEK BASINA KULLANMA. ***

Madde 285 bu sayiyi TEK bir adaydan olcup PROJE SABITI ilan etti. Madde
288 dort ayri (etki, P) cifti olcunce iliski MONOTON CIKMADI:

    etki +7,22  -> P %67,5   (285: %10 kontrarian dilim, AYRI bir kitap)
    etki +1,32  -> P %71,0   (288: karistirilmis PLASEBO)
    etki +11,89 -> P %95,0   (288: prim-brut e0,10 r120)
    etki +38,14 -> P %90,7   (287: prim-brut e0,50 r180)

+1,32'lik bir etki %71'e, +7,22'lik bir etki %67,5'e ulasiyor: SIRA
TERS. Cunku esli blok bootstrap'in gurultusu etkinin BUYUKLUGUNE degil,
adayin kontrole gore IZLEME HATASINA baglidir. Prim-brut adayi kontrolun
kendisinin %0,5 yeniden olceklenmisidir -> fark serisinin oynakligi
kucuk -> kucuk etki bile yuksek P verir. Madde 285'in adayi ise ayri bir
kitapti -> fark serisi oynak -> buyuk etki bile dusuk P verir.

ASE **ADAYA AITTIR**: ASE = z(0,80) * sigma(esli fark). `ase_puan_adaydan()`
bunu hesaplar. Sabit surumu yalnizca madde 285'in GOZLEMI olarak
saklaniyor; onunla hukum verilmez.

MALIYETI SOMUT: bu sabit yazili haliyle madde 288'in adayini turun
BASINDA elerdi ("etki +11,9 < 13, gereken ufuk 4,9 yil") - oysa olculen
P %95,0'ti ve aday 275-288 araliginda dort sarti gecen TEK aday oldu.
Guc filtresi, kotu turu elemek icin kuruldu; sabitlestirilince IYI
adayi eliyor."""

BAR_Z = 0.8416
"""Phi^-1(0,80): %80 kanit barinin z degeri."""

ASE_GOZLEMLERI = {
    # ad -> (doz olcutunde etki puani, olculen P(>0) yuzdesi)
    "285 kontrarian dilim": (7.22, 67.5),
    "288 plasebo karistirilmis": (1.32, 71.0),
    "288 prim-brut e0.10 r120": (11.89, 95.0),
    "287 prim-brut e0.50 r180": (38.14, 90.7),
}
"""Madde 288'in kanit kumesi: etki ile P arasinda monoton iliski YOK."""


def ase_monoton_mu(g: dict = None) -> bool:
    """Etki buyudukce P buyuyor mu? (Madde 288: HAYIR.)"""
    g = g or ASE_GOZLEMLERI
    s = sorted(g.values())
    return all(s[i][1] <= s[i + 1][1] for i in range(len(s) - 1))


def ase_puan_adaydan(sigma_boot: float, z: float = BAR_Z) -> float:
    """ADAYA AIT ASE: esli bootstrap dagiliminin sigmasindan.

    P(>0) ~ Phi(etki/sigma) oldugu icin %80 bari etki >= z*sigma ister.
    sigma_boot: adayin doz olcutu farkinin esli blok bootstrap sigmasi.
    """
    return abs(z) * abs(sigma_boot)

UFUK_GUN = 1504
"""Kanonik veri ufku (referans_getiri.csv)."""


def saptanabilir_mi(etki_puan: float, ase: float = ASE_PUAN) -> bool:
    """Bu etki buyuklugu BU veri tabaninda %80 barini gecebilir mi?"""
    return abs(etki_puan) >= ase


def gereken_ufuk_gun(etki_puan: float, ase: float = ASE_PUAN,
                     ufuk: float = UFUK_GUN) -> float:
    """Bu etkiyi %80 barina tasimak icin gereken veri ufku (gun).

    Standart hata ~ 1/sqrt(T) oldugu icin gereken kat (ase/etki)^2.
    """
    e = abs(etki_puan)
    if e <= 0:
        return float("inf")
    return ufuk * (ase / e) ** 2


def gereken_ufuk_yil(etki_puan: float, **kw) -> float:
    return gereken_ufuk_gun(etki_puan, **kw) / 365.25


def tur_degerli_mi(beklenen_etki_puan: float,
                   sigma_boot: float = None) -> dict:
    """Bir arastirma turuna BASLAMADAN once: bu tur hukum verebilir mi?

    Madde 285'in dersi: "P(>0) %67,5, bar %80" bir red gerekcesidir ama
    "%80'e ulasmak 14,2 yil ister" bambaska bir sey soyler. Ikincisi
    TURUN BASINDA bilinebilir ve bilinmesi gerekir.

    MADDE 288'IN DUZELTMESI: `sigma_boot` VERILMEDIKCE bu fonksiyon
    HUKUM VERMEZ, yalnizca madde 285'in gozlemini hatirlatir. ASE adaya
    aittir (bkz. ASE_PUAN'in docstring'i); sabitle elenen aday, madde
    288'de P %95,0 olcen adayin ta kendisiydi.

    sigma_boot verilirse: ase = z(0,80)*sigma, karar ADAYA ozel.
    """
    if sigma_boot is not None:
        ase = ase_puan_adaydan(sigma_boot)
        sapt = abs(beklenen_etki_puan) >= ase
        return {
            "beklenen_etki": beklenen_etki_puan,
            "ase": ase,
            "ase_kaynagi": "ADAYA AIT (sigma_boot %.3f)" % sigma_boot,
            "saptanabilir": sapt,
            "gereken_yil": gereken_ufuk_yil(beklenen_etki_puan, ase=ase),
            "mevcut_yil": UFUK_GUN / 365.25,
            "oneri": ("tur HUKUM verebilir" if sapt else
                      "tur hukum VEREMEZ: etki adayin KENDI gurultu "
                      "olceginin altinda"),
        }
    sapt = saptanabilir_mi(beklenen_etki_puan)
    return {
        "beklenen_etki": beklenen_etki_puan,
        "ase": ASE_PUAN,
        "ase_kaynagi": "SABIT - madde 288'de YANLISLANDI, hukum icin "
                       "sigma_boot ver",
        "saptanabilir": sapt,
        "gereken_yil": gereken_ufuk_yil(beklenen_etki_puan),
        "mevcut_yil": UFUK_GUN / 365.25,
        "uyari": "MADDE 288: sabit ASE ile hukum verilmez; bu sayi madde "
                 "285'in TEK gozlemidir ve etki-P iliskisi monoton degil.",
        "oneri": ("madde 285'in sabitine gore tur hukum verebilir"
                  if sapt else
                  "madde 285'in sabitine gore tur hukum VEREMEZ - AMA bu "
                  "sabit yanlislandi: turu bu gerekceyle IPTAL ETME, "
                  "adayin esli fark sigmasini olcup tekrar sor"),
    }
