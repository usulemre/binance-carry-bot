"""GÜNLÜK TEK SAYFA RAPOR — canlı çeyrek için tek komut.

NEDEN: `CANLIYA_CIKIS.md` dört ayrı araç çalıştırmayı ve çıktılarını
yorumlamayı gerektiriyor (sapma, izleme, defter, sağlık). Sabah 8'de
dört çıktıyı yorumlamak, yorumlamamaya dönüşür. Bu araç hepsini
çalıştırır ve TEK BİR KARAR verir:

    DEVAM   - her şey normal aralıkta
    İNCELE  - bir eşik aşıldı, sebebi bulunmalı
    DURDUR  - ölçülmüş "bu olmamalı" sınırı aşıldı

Eşikler `CANLIYA_CIKIS.md`'den gelir ve BURADA SABİTTİR - çünkü
eşiği anlık duyguyla gevşetmek, eşiğin varlık sebebini ortadan
kaldırır.

KULLANIM:
    python carry_rapor.py             # sadece yerel dosyalar (API yok)
    python carry_rapor.py --api       # funding tahsilatını da ölçer
    python carry_rapor.py --gun 30    # izleme penceresi
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carry_sapma as cs

# --- EŞİKLER (CANLIYA_CIKIS.md bölüm 6) -----------------------------
DUSUS_INCELE = -0.18
"""Normal bir yılın p5 düşüşü - bunun altı "incele".

MADDE 233'te GÜNCELLENDİ (−%20 -> −%18) ve ÖNEMLİSİ: bu sabit madde
175'ten beri BAYATTI. 175'in ölçümü (p5 −%20,0 / p1 −%26,1) o günün
kitabından geliyordu; aradan 177, 179, 184, 189, 196, 209 ve 222 geçti,
referans serisi madde 222'de yeniden üretildi ve p5 −%16,8 / p1 −%20,7
oldu. Madde 231 ayrıca EN KÖTÜ makul rejimi ölçtü: düşük prim rejiminde
p5 −%17,9 / p1 −%22,3.

Eşik en kötü rejime göre konur (madde 231'in felsefesi), o yüzden −%18.
Önceki −%20, ölçümün ARKASINDA kalıyordu: alarm, 100 yılda 1 olan bir
düşüşe yaklaşıldığında bile sessiz kalacaktı. Yanlış alarm değil,
KAÇIRILMIŞ TESPİT riski.

MADDE 243 — EŞİK BAĞIMSIZ BİR YÖNTEMLE DOĞRULANDI, VE YANLIŞ TETİKLEME
OLASILIĞI İLK KEZ SAYILDI. Yöntem: kitabın GÜNLÜK getirileri aynı kalıp
SIRASI rastgele karıştırılıyor (20.000 örnek, 1 yıllık pencere). Bu,
"aynı dağılım, farklı şans" demektir:

  1 yıllık düşüş       ort      p50      p5       p1
  gerçek pencereler  −%10,89  −%10,73  −%14,54  −%14,54
  karıştırılmış      −%12,94  −%12,25  −%20,55  −%25,30

  eşik            gerçek pencerelerde   karıştırılmışta
  İNCELE −%18            %0,0               %11,1
  DURDUR −%23            %0,0                %2,2

SAĞLIKLI bir bot, yalnızca sıralama şansından ötürü yılda **%11,1**
olasılıkla İNCELE ve **%2,2** olasılıkla DURDUR eşiğine değer. İkisi de
kabul edilebilir (incelemek durdurmak değildir; DURDUR ~45 yılda bir
boşa tetikler) - ama bu sayılar artık BİLİNİYOR ve eşik değişirse
yeniden hesaplanmalıdır. Araç: `arastirma_risk_atfi.py`.

DİKKAT (madde 243): gerçekleşen pencereler İYİMSER. Aynı getiri
dağılımının dürüst 1 yıl p5'i **−%20,55**, p1'i **−%25,30** - yani
yayınlanan −%14,5 bir ŞANSLI SIRALAMA. Canlı beklenti −%20 civarıdır
(madde 148.2'nin uyarısı, kitabın kendi dağılımından çıkarılmış hâli).

BELGE-KOD AYRIŞMASI (madde 233'te bulundu): `CANLIYA_CIKIS.md` bu
eşikleri −%17/−%21 diye yazıyordu, kod ise −%20/−%25 kullanıyordu -
yani belge ile kodun söylediği eşikler BİRKAÇ MADDE BOYUNCA farklıydı
ve bunu hiçbir test denetlemiyordu. Madde 217 belgeyi koda bağlamıştı
ama bu iki sabiti kapsamıyordu. Artık `test_carry_preflight.py`
belgedeki alarm satırlarını DOĞRUDAN bu sabitlerden türetiyor."""

DUSUS_DURDUR = -0.23
"""1 yıllık pencere bootstrap'ında p1 düşüşü: tüm örnekte −%20,7, EN
KÖTÜ (düşük prim) rejimde −%22,3 (madde 222/231). Yani 100 yılda 1 yıl.
Görülürse ya beklenti yanlış ya icra bozuk. Madde 233'te −%25'ten
çekildi - eski değer madde 175'in çürütülmüş serisinden geliyordu."""

# --- MADDE 302: ESIKLER YAPILANDIRMAYA DUYARLI --------------------
#
# Yukaridaki iki esik (−%18 / −%23) 15x5 kitabi uzerinde turetildi:
# kalibrasyon zinciri 175 -> 233 -> 243'un hepsi o kitabin istatistigini
# kullaniyor (madde 243'un tablosunda "gercek pencereler −%14,54" = 15x5'in
# tam donem dususu). AMA madde 295 kucuk sermayede 13x3 ONERIYOR ve o
# kitabin dususu −%17,68 - yani INCELE esigine payi 3,46 puan DEGIL
# 0,32 puan.
#
# Madde 243'un yontemi 13x3'te birebir tekrarlandi (gercek 1-yillik
# pencereler + sirasi karistirilmis 20.000 orneklem):
#
#   kitap   tam donem   karis. p5   karis. p1   INCELE tetik   DURDUR tetik
#   15x5     −%14,54     −%20,56     −%25,65       %11,1          %2,3
#   13x3     −%17,68     −%25,51     −%31,59       **%30,6**     **%9,7**
#
# Yani 13x3 kosan biri, HICBIR SEY BOZULMADIGI bir yilda ucte bir
# olasilikla INCELE, onda bir olasilikla DURDUR gorur - bot sirf
# sanssizliktan kapanir. Bu bir kaybedilmis kar riskidir.
#
# Esikler IKI BAGIMSIZ YOLDAN yeniden turetildi ve ayni yuvarlak degerde
# bulustu (fark 0,54 ve 0,33 puan): (1) 15x5'in yanlis-tetik olasiligini
# (%11,1 / %2,3) 13x3'te veren esik -> −%22,43 / −%28,31; (2) dusus
# oraniyla olcekleme (17,68/14,54 = 1,216) -> −%21,89 / −%27,97.
# Ikisi de **−%22 / −%28**. O esiklerle 13x3'un yanlis tetigi %12,3 / %2,5,
# yani 15x5'in kalibrasyonuyla ESDEGER.
#
# COZUM: sabitler 15x5'in TEMELI olarak kalir, karar noktalari ise
# kosulan kitabin dususuyle OLCEKLENMIS esigi kullanir. 15x5'te olcek
# 1,000 oldugu icin varsayilan davranis BIREBIR AYNI kalir.
#
# CEKINCE: olcek madde 295'in olctugu dusus tablosundan geliyor. Madde
# 231'in asil yontemi (EN KOTU MAKUL REJIMIN p5'i) bu turda 13x3 icin
# TEKRARLANMADI - rejim ayrimi yeniden uretilmedi. Iki turetmenin
# bulustugu nokta saglam ama rejim-temelli turetme ACIK bir eksen.
KITAP_DUSUS = {
    # madde 295'te olculdu (arastirma_evren_esigi.DUSUS); madde 300'de
    # 13x3 bagimsiz olarak dogrulandi (17,68 birebir).
    "15x5": 14.54, "15x2": 24.75, "13x3": 17.68, "5x5": 16.12,
    "8x5": 14.89, "4x5": 15.32, "3x5": 16.96, "3x3": 22.10,
    "2x5": 19.10, "2x4": 22.60, "1x5": 28.08,
}
KITAP_DUSUS_KOSULAN = {
    # MADDE 329: KITAP_DUSUS madde 295'in tablosudur ve YAPILANDIRMAYA
    # gore, TAM EVRENDE olculmustur. Asagidaki ise GERCEKTEN KOSULAN
    # kitabin dususu: bakiye bacagi, bacak evreni belirledigi icin bu
    # sayi SERMAYEYE BAGLIDIR ve o yuzden AYRI tutulur.
    #   anahtar: (bakiye, evren, tam donem dusus)
    # MADDE 330: bu dusus TEK BIR BASLANGIC HIZASININ (FAZ_KAY) degeri.
    # Uc ofset olculdu: 20,07 / 21,70 / 20,10 (yayilim 1,63 puan) ve
    # madde 320'nin 19,91'i en sig olcumden 0,16 puan daha sig. Pay EN
    # KOTU ofsetle 23,00 - 21,70 = +1,30 puan (tek ofsetle +3,09) -
    # hala pozitif, cift ayakta, ama pay sanildigindan INCE.
    "15x4": (2000.0, "D8", 19.91),
}
KITAP_DUSUS_OFSET = {
    # MADDE 330: anahtar -> (en sig, en derin, olculen ofset sayisi)
    "15x4": (20.07, 21.70, 3),
}
TEMEL_KITAP = "15x5"
"""Esiklerin turetildigi kitap. Olcek bunun dususune gore."""


def kitap_anahtari(n_dilim: int = None, n_legs: int = None,
                   bakiye: float = None) -> str:
    """Kosulan yapilandirmanin anahtari (or. '13x3').

    *** MADDE 329: `N_LEGS` YAPILANDIRILAN, KOSULAN DEGILDIR. ***
    `carry_bot.uygun_bacak_sayisi(bakiye)` kucuk bakiyede bacak sayisini
    OTOMATIK dusurur (2.000 $'da 5 -> 4). Eski hali `cb.N_LEGS`'i
    okudugu icin anahtar "15x5" donuyordu; o anahtarin esik cifti
    (-%18/-%23) ise dususu %14,54 olan bir kitap icin turetilmisti.
    GERCEKTEN kosulan kitabin (15x4, D8, 2.000 $) tam donem dususu
    **%19,91** - yani INCELE esigi kitabin kendi tarihsel dususunun
    ALTINDA kaliyordu (pay -1,91 puan) ve `esik_kademesi()` buna
    "olculmus" diyordu. Bakiye verilirse artik KOSULAN bacak sayisi
    kullanilir.
    """
    if n_dilim is None or n_legs is None:
        try:
            import carry_bot as _cb
            n_dilim = _cb.N_DILIM if n_dilim is None else n_dilim
            if n_legs is None:
                if bakiye is not None:
                    n_legs = _cb.uygun_bacak_sayisi(float(bakiye))
                else:
                    n_legs = _cb.N_LEGS
        except Exception:
            return TEMEL_KITAP
    return f"{int(n_dilim)}x{int(n_legs)}"


# MADDE 303: MADDE 231'IN KANONIK YONTEMIYLE OLCULMUS ESIKLER.
#
# Madde 302 esikleri IKI yoldan turetmisti (yanlis-tetik esdegerligi ve
# dusus oraniyla olcekleme) ve ikisi bulusmustu, AMA ikisi de madde
# 231'in ASIL yontemini atliyordu: "esik EN KOTU MAKUL REJIMIN 1-yillik
# bootstrap p5/p1'ine konur". O eksen madde 302'de ACIK birakilmisti.
#
# Madde 303'te kapatildi. Once YONTEM dogrulandi: 15x5 kolu madde 231'in
# uc rakamini da ondaligina kadar verdi (tum p1 -21,37 vs kayitli -21,4;
# dusuk -22,31 vs -22,3; yuksek -17,99 vs -18,0) ve en kotu rejim p5'i
# -17,93 -> madde 233'un -%18'i. Zincir tuttugu icin 13x3'e uygulandi:
#
#   kitap  rejim        1y dusus p5    1y dusus p1
#   15x5   dusuk prim     -%17,93        -%22,31   <- EN KOTU
#   15x5   yuksek prim    -%15,11        -%17,99
#   13x3   dusuk prim     **-%22,66**    **-%28,98**  <- EN KOTU
#   13x3   yuksek prim    -%17,90        -%20,86
#
# Madde 233'un yuvarlama kurali (buyuklugu bir sonraki tam sayiya cikar:
# 17,93->18 ve 22,31->23) uygulanirsa 13x3 icin **-%23 / -%29**.
#
# Yanlis tetik olasiliklari (madde 302'nin karistirilmis orneklemi):
#   15x5 referansi            INCELE %11,1   DURDUR %2,3
#   madde 302 (olcek 1,216)   INCELE %12,6   DURDUR %2,5
#   madde 303 KANONIK         INCELE  %9,7   DURDUR %1,9
#
# Yani madde 302'nin duzeltmesi YONDE VE BUYUKLUKTE dogruydu; kanonik
# yontem onu biraz GEVSETIYOR. Gercek olcek 1,216 degil 1,264 (INCELE) ve
# 1,299 (DURDUR) - dusus orani esigi hafifce SIKI tutuyordu.
#
# Artik esik UC KADEMELI belirlenir:
#   1) KITAP_ESIK'te OLCULMUS cift varsa -> aynen o (en guvenilir)
#   2) yoksa KITAP_DUSUS'te dusus varsa  -> dusus oraniyla olceklenir
#      (madde 302'nin yolu; "olcum degil TAHMIN" diye isaretlenir)
#   3) o da yoksa                        -> temel + UYARI
KITAP_ESIK = {
    # (INCELE, DURDUR) - madde 231'in yontemiyle OLCULDU (madde 303)
    "15x5": (-0.18, -0.23),
    "13x3": (-0.23, -0.29),
    "15x4": (-0.23, -0.30),     # madde 329: KOSULAN kitap (2.000 $ / D8)
}
KITAP_REJIM_OLCUMU = {
    # kitap: (en kotu rejim, 1y dusus p5, 1y dusus p1)
    "15x5": ("dusuk prim", -17.93, -22.31),
    "13x3": ("dusuk prim", -22.66, -28.98),
    "15x4": ("dusuk prim", -22.83, -29.23),     # madde 329, 2.000 $ / D8
}


def esik_kademesi(anahtar: str = None) -> str:
    """'olculmus' | 'olceklenmis' | 'temel' (madde 303)."""
    anahtar = anahtar or kitap_anahtari()
    if anahtar in KITAP_ESIK:
        return "olculmus"
    if anahtar in KITAP_DUSUS:
        return "olceklenmis"
    return "temel"


def dusus_olcegi(anahtar: str = None) -> tuple[float, str]:
    """(olcek, aciklama). Bilinmeyen yapilandirmada 1.0 ve UYARI doner.

    Bilinmeyeni 1.0'a dusurmek bilincli: esigi TAHMINLE gevsetmek,
    esigin varlik sebebini ortadan kaldirir (bu modulun docstring'i).
    """
    anahtar = anahtar or kitap_anahtari()
    temel = KITAP_DUSUS[TEMEL_KITAP]
    if anahtar not in KITAP_DUSUS:
        return 1.0, (f"UYARI: '{anahtar}' yapilandirmasinin dususu "
                     f"OLCULMEDI - esikler {TEMEL_KITAP} temelinde "
                     f"birakildi, gercek riskin ALTINDA olabilir")
    o = KITAP_DUSUS[anahtar] / temel
    if anahtar == TEMEL_KITAP:
        return 1.0, f"{anahtar} = kalibrasyonun kitabi (olcek 1,000)"
    return o, (f"{anahtar} dususu %{KITAP_DUSUS[anahtar]:.2f} vs "
               f"{TEMEL_KITAP} %{temel:.2f} -> olcek {o:.3f}")


def dusus_incele(anahtar: str = None) -> float:
    """Kosulan kitabin INCELE esigi (negatif oran).

    MADDE 303: olculmus cift varsa AYNEN kullanilir; yoksa madde 302'nin
    dusus-orani olceklemesine dusulur.
    """
    anahtar = anahtar or kitap_anahtari()
    if anahtar in KITAP_ESIK:
        return KITAP_ESIK[anahtar][0]
    return DUSUS_INCELE * dusus_olcegi(anahtar)[0]


def dusus_durdur(anahtar: str = None) -> float:
    """Kosulan kitabin DURDUR esigi (negatif oran). Madde 303: bkz. yukari."""
    anahtar = anahtar or kitap_anahtari()
    if anahtar in KITAP_ESIK:
        return KITAP_ESIK[anahtar][1]
    return DUSUS_DURDUR * dusus_olcegi(anahtar)[0]


def backtest_maksimumu(anahtar: str = None) -> float:
    """Kosulan kitabin geri testteki maksimum dususu (POZITIF yuzde).

    MADDE 302: INCELE mesaji eskiden SABIT KODLU '-14.7' yaziyordu - o
    15x5'in sayisi. 13x3 kosan biri icin yanlis bir referanstir.
    """
    anahtar = anahtar or kitap_anahtari()
    if anahtar in KITAP_DUSUS_KOSULAN:      # madde 329: sermayeye bagli
        return KITAP_DUSUS_KOSULAN[anahtar][2]
    return KITAP_DUSUS.get(anahtar, KITAP_DUSUS[TEMEL_KITAP])


BEKLENEN_FUNDING_GUNLUK = 0.001055
"""Tahsil edilen funding, sermaye oranı olarak, GÜNLÜK (madde 232).

**BU SAYI ÖLÇÜLDÜ, TÜRETİLMEDİ** - ve türetilmiş hâli YANLIŞTI. Rapor
madde 232'ye kadar beklenen funding'i `BEKLENEN_GUNLUK * 0.94` diye
hesaplıyordu, yani GÜNLÜK TOPLAM GETİRİ x 0,94. O 0,94, madde 136'nın
**"funding gelirinin %94'ü LONG bacaktan gelir"** cümlesinden alınmıştı
ve rapora **"gelirin %94'ü funding'den gelir"** olarak geçmişti. İki
ayrı büyüklük: biri funding'in TARAF dağılımı, öteki getirinin KAYNAK
dağılımı. Üstelik madde 214 ikincisini zaten çürütmüştü (funding +109,8
ve ham fiyat -108,0 birbirini götürüyor; kârın tamamı TP hasadı).

**EN PAHALI HATA TÜRÜ YİNE ETİKET** (madde 203, 209 ile aynı sınıf).

Motorla ölçüldü (`FON_OLC=1`, dilim ortalaması, 1.504 gün):

  dönem                        %/gün    14 günde
  tüm örnek (BU SAYI)        0,1055%     1,48%
  düşük prim (2022H2-24Q4)   0,0653%     0,91%
  yüksek prim (2025Q1+)      0,1648%     2,31%

Eski formül 0,2033%/gün bekliyordu, yani **1,93 KAT YÜKSEK**. Sonuç:
SAĞLIKLI bir bot raporda şöyle görünecekti:

  rejim          oran    raporun kararı
  yüksek prim    0,81    temiz          <- bu yuzden hic fark edilmedi
  tüm örnek      0,52    İNCELE
  düşük prim     0,32    **DURDUR**

Yani hata ŞU AN yüksek prim rejimi tarafından MASKELENİYOR (madde 231);
prim eski seviyesine dönseydi rapor sağlıklı bir botu durduracaktı. Ve
madde 216'ya göre bu, gün 14'te %100 güce sahip BİRİNCİL karar ölçütü -
yani sürekli öten bir alarma dönüşüp (madde 177) tek güçlü canlı
kontrolü işe yaramaz hâle getirirdi."""

BEKLENEN_FUNDING_TABAN = 0.000653
"""Alarm, EN KÖTÜ makul rejimin beklentisine göre verilir (madde 231/232).

Düşük prim rejiminin günlük funding tahsilatı. Oran bu tabana göre
hesaplanırsa sağlıklı bir bot HER rejimde >= 1,0 okur ve eşikler
anlamını korur: "en kötü rejimin bile altında" = gerçek arıza.
Rapor ayrıca harmana göre oranı BİLGİ olarak yazar."""

BEKLENEN_FUNDING_YUKSEK = 0.001648
"""Yüksek prim rejiminin (2025Q1+) günlük funding tahsilatı."""

REJIM_YILLIK = {"DÜŞÜK PRİM": 95.0, "HARMAN/ARADA": 112.5, "YÜKSEK PRİM": 141.0}
"""Madde 231'de rejim bazında ölçülen yıllık beklentiler."""


def rejim_tahmini(gunluk_funding: float) -> tuple:
    """Tahsil edilen funding'den rejimi ve geçerli beklentiyi kestirir.

    MADDE 231/232: prim 2025Q1'de SEVİYE atladı (3,8 kat) ve beklenti
    rejime göre +%95 ile +%141 arasında değişiyor. Yayınlanan +%112,5 bir
    HARMANDIR; botun hangi rejimde çalıştığını bilmeden gerçekleşen
    getiriyi ona kıyaslamak yanıltır. Tahsil edilen funding, primin
    seviyesinin en doğrudan canlı ölçüsüdür.

    Sınırlar iki rejim ortalamasının geometrik ortasında: bu, iki yönlü
    yanlış sınıflandırmayı dengeler.
    """
    import math
    alt = math.sqrt(BEKLENEN_FUNDING_TABAN * BEKLENEN_FUNDING_GUNLUK)
    ust = math.sqrt(BEKLENEN_FUNDING_GUNLUK * BEKLENEN_FUNDING_YUKSEK)
    if gunluk_funding < alt:
        return "DÜŞÜK PRİM", REJIM_YILLIK["DÜŞÜK PRİM"]
    if gunluk_funding > ust:
        return "YÜKSEK PRİM", REJIM_YILLIK["YÜKSEK PRİM"]
    return "HARMAN/ARADA", REJIM_YILLIK["HARMAN/ARADA"]


FUNDING_ORAN_INCELE = 0.80
FUNDING_ORAN_DURDUR = 0.50
"""Tahsil edilen funding / EN KÖTÜ REJİMİN beklentisi (madde 232).

Funding tahsilatı, getiriden çok daha hızlı haber verir: madde 216'da
ölçülen istatistiksel güç 14 günde **%100** (toplam getiri aynı ufukta
%15). Bu yüzden canlının birincil karar ölçütü bu - ve tam bu yüzden
beklentisinin doğru olması kritik."""

BEKLENEN_GUNLUK = 0.002163
"""Referans serinin günlük ortalaması (%0.2163) - beklenti kıyası.
MADDE 177-179: 6+6 bacak, kâr al %40, kalabalık havuzu 3.0.
MADDE 209: funding penceresi 8sa -> 48sa (%0.1887 -> %0.1940).
MADDE 222: bacak 6 -> 5; beklenti %0.1940 -> %0.2163
(yıllık +%96.8 -> +%112.5).

MADDE 231 — BU SAYI BİR REJİM HARMANIDIR, DEĞİŞTİRİLMEDİ. Funding
primi 2025Q1'de seviye atladı (bir trend DEĞİL bir rejim; Mann-Whitney
p=0,0005, seviye modeli doğrusal trendden iyi uyuyor). En uç long
adayının günlük funding medyanı -%0,49 -> -%1,86, yani **3,8 kat**.
Strateji iki rejimde de çalışıyor, sadece ölçek değişiyor:

  rejim                          yıllık   Sharpe   1y get. p5   1y düşüş p1
  tüm örnek (BU SAYI)           +112.5%   2.942      +41.1%       -21.4%
  düşük prim (%60, 2022H2-24Q4)  +95.0%   2.794      +24.2%       -22.3%
  yüksek prim (%40, 2025Q1+)    +141.0%   3.147      +71.6%       -18.0%

Bu sayı %60 düşük + %40 yüksek prim harmanı, yani ŞU ANKİ rejimden
kasten düşük. 2026'nın +%202'si veya son rejimin +%141'i beklenti
YAPILMADI, çünkü o rakam rejimin süreceğini varsaymayı gerektirir.
Prim gerilerse beklenti +%95'e iner - kenar kaybolmaz, ölçek küçülür.

Alarm eşikleri madde 231'de düşük prim rejimine göre gevşetildi
(-%17/-%21 -> -%18/-%23), çünkü o rejimin p1'i -%22,3 ve eski eşik
prim gerilediğinde YANLIŞ ALARM verirdi."""

BAYAT_INCELE_SAAT = 36.0
BAYAT_DURDUR_SAAT = 72.0
"""ÖLÜ BOT DEDEKTÖRÜ. Bot günde bir tur atar ve her turda bakiye yazar.
Yazmıyorsa süreç ölmüştür (çökme, yeniden başlatma, ağ).

NEDEN AYRI BİR ALARM: ölü bot SESSİZDİR ve en tehlikeli hâldir.
Pozisyonlar açık kalır ama (a) dilimler yenilenmez, (b) kâr al emirleri
tazelenmez, (c) madde 163'teki bayat emir temizliği çalışmaz - yani
dolmamış GTX emirleri kitapta asılı kalır. Bu araç bunu söylemezse,
bakiye dosyası dünkü hâliyle donduğu için rapor "DEVAM" derdi."""


def _renk(durum: str) -> str:
    return {"DEVAM": "✓", "İNCELE": "!", "DURDUR": "✗"}.get(durum, "?")


def bakiye_ozet(dosya: str = None) -> dict:
    """Bakiye geçmişinden gün sayısı, getiri ve düşüş."""
    d = cs.bakiye_oku(dosya)
    if d.empty or len(d) < 2:
        return {"gun": 0}
    g = cs.gunluk_getiri(d)
    e = (1 + g).cumprod()
    dusus = float((e / e.cummax() - 1).min())
    yas = (time.time() - float(d["zaman"].iloc[-1])) / 3600.0
    return {"gun": len(g), "getiri": float(e.iloc[-1] - 1), "dusus": dusus,
            "gunluk_ort": float(g.mean()), "seri": g,
            "bakiye": float(d["bakiye"].iloc[-1]),
            "ilk_bakiye": float(d["bakiye"].iloc[0]),
            "son_kayit_saat": float(yas)}


def saglik_ozet(dosya: str = None) -> dict:
    """Sağlık kapısının son durumu (bot yazar, biz sadece okuruz)."""
    yol = dosya or os.getenv("CARRY_SAGLIK_LOG", "carry_saglik.json")
    try:
        with open(yol, encoding="utf-8") as fh:
            k = json.load(fh)
        return {"var": True, "acik": bool(k.get("acik", True)),
                "kapanis_ms": k.get("kapanis_ms")}
    except (OSError, ValueError):
        return {"var": False, "acik": True}


def funding_ozet(gun: int) -> dict:
    """Borsanın gelir kayıtlarından GERÇEK funding tahsilatı (--api)."""
    try:
        from exchange_client import ExchangeClient
        import config
        import carry_izleme
    except Exception as e:
        return {"var": False, "hata": f"modül yüklenemedi: {e}"}
    try:
        c = ExchangeClient(config.API_KEY, config.API_SECRET,
                           getattr(config, "MODE", "demo"))
        r = carry_izleme.rapor(c, gun)
        return {"var": True, **r}
    except Exception as e:
        return {"var": False, "hata": str(e)}


def karar(b: dict, sap: dict, sag: dict, fnd: dict) -> tuple:
    """Tek karar + gerekçe listesi. En kötü sinyal kazanır."""
    sebep = []
    durum = "DEVAM"

    def yukselt(yeni, not_):
        nonlocal durum
        sira = {"DEVAM": 0, "İNCELE": 1, "DURDUR": 2}
        if sira[yeni] > sira[durum]:
            durum = yeni
        sebep.append(f"[{yeni}] {not_}")

    # ÖLÜ BOT: her şeyden önce. Bakiye dosyası donduysa aşağıdaki
    # ölçümlerin hepsi DÜNÜN verisidir ve yanıltıcıdır.
    yas = b.get("son_kayit_saat")
    if yas is not None:
        if yas >= BAYAT_DURDUR_SAAT:
            yukselt("DURDUR", f"bot {yas/24:.1f} GÜNDÜR tur atmamış - pozisyonlar "
                              "yönetilmiyor (dilim yenilenmiyor, kâr al "
                              "tazelenmiyor, bayat emir temizlenmiyor)")
        elif yas >= BAYAT_INCELE_SAAT:
            yukselt("İNCELE", f"son tur {yas:.0f} saat önce - bot günde bir tur "
                              "atmalı, süreç ayakta mı?")

    # SİNYAL TANIMI PARİTESİ (madde 210): ilk 5 gün kuralından ÖNCE,
    # çünkü bu bir AYAR hatasıdır ve ilk turdan itibaren geçerlidir.
    # Madde 209'da canlı bot backtest'ten farklı bir funding penceresi
    # kullanıyordu; beklenti (%0.194/gün) o ayarla ölçülmemişti ve
    # aşağıdaki bütün karşılaştırmalar yanlış ölçüte bakıyordu.
    # Veri gerektirmeyen iki şart kontrol edilir (pencere sabiti +
    # pencereye giren ödeme sayısı); kesitsel ölçüm `carry_parite.py`de.
    try:
        import carry_parite as cp
        _p = cp.karar()
        if _p["durum"] != "TAMAM":
            yukselt("DURDUR",
                    "SİNYAL TANIMI PARİTESİ BOZUK - " + "; ".join(_p["sorunlar"])
                    + ". Beklenti bu ayarla ölçülmedi, aşağıdaki kıyaslar "
                      "GEÇERSİZ (madde 209/210)")
    except Exception as _e:      # araç yoksa rapor çalışmaya devam eder
        sebep.append(f"[DEVAM] parite kontrolü yapılamadı ({_e}) - "
                     "`carry_parite.py` eksik olabilir")

    if b.get("gun", 0) < 5:
        sebep.append("[DEVAM] ilk 5 gün kitap kurulumu - getiri okuması "
                     "anlamsız, sadece emirlerin açıldığını doğrula")
        return durum, sebep

    d = b.get("dusus", 0.0)
    # MADDE 302: esikler KOSULAN kitaba olceklenir (15x5'te birebir ayni)
    # MADDE 329: anahtar BAKIYEDEN turetilir - `uygun_bacak_sayisi` kucuk
    # bakiyede bacagi otomatik dusurur ve kitap "15x5" DEGIL "15x4"tur.
    _ank = kitap_anahtari(bakiye=b.get("ilk_bakiye") or None)
    _ki, _kd = dusus_incele(_ank), dusus_durdur(_ank)
    _kmax = backtest_maksimumu(_ank)
    if d <= _kd:
        yukselt("DURDUR", f"düşüş %{d*100:.1f} - 1x'te 100 yılda 1 olay "
                          f"(sınır %{_kd*100:.0f}, {_ank})")
    elif d <= _ki:
        yukselt("İNCELE", f"düşüş %{d*100:.1f} - {_ank} "
                          f"kitabının backtest maksimumunu (%-{_kmax:.2f}) "
                          f"aştı, sebebi bulunmalı")

    if sap.get("durum") == "CİDDİ SAPMA":
        yukselt("DURDUR", f"sapma CİDDİ (yüzdelik %{sap.get('yuzdelik',0):.0f}) "
                          "- KALDIRAÇ ARTIRMA")
    elif sap.get("durum") == "BEKLENENİN ALTINDA":
        yukselt("İNCELE", f"sapma beklenenin altında "
                          f"(yüzdelik %{sap.get('yuzdelik',0):.0f})")

    if sag.get("var") and not sag.get("acik", True):
        yukselt("İNCELE", "sağlık kapısı KAPALI - bot pozisyonları kapattı, "
                          "kapanma sebebini logdan oku")

    if fnd.get("var"):
        # MADDE 232: alarm EN KÖTÜ rejimin beklentisine göre (taban),
        # rapor metni harmana göre oranı da yazar.
        bekl = BEKLENEN_FUNDING_TABAN * b.get("gun", 0) * b.get("ilk_bakiye", 0)
        ger = float(fnd.get("funding", 0) or 0)
        if bekl > 0:
            oran = ger / bekl
            if oran < FUNDING_ORAN_DURDUR:
                yukselt("DURDUR", f"funding tahsilatı beklentinin %{oran*100:.0f}'i "
                                  "- hesap/API tarafında sorun ara")
            elif oran < FUNDING_ORAN_INCELE:
                yukselt("İNCELE", f"funding tahsilatı beklentinin %{oran*100:.0f}'i")
            else:
                sebep.append(f"[DEVAM] funding tahsilatı beklentinin "
                             f"%{oran*100:.0f}'i")

    if durum == "DEVAM" and not sebep:
        sebep.append("[DEVAM] ölçülen her şey normal aralıkta")
    return durum, sebep


def yaz(gun: int = 7, api: bool = False, dosya: str = None) -> str:
    b = bakiye_ozet(dosya)
    if b.get("gun", 0) == 0:
        return ("Bakiye geçmişi yok (carry_equity.csv). Bot hiç çalışmamış "
                "ya da yanlış dizindesin.")
    ref = cs.referans_oku()
    sap = (cs.degerlendir(b["seri"], ref) if b["gun"] >= 7
           else {"durum": "YETERSİZ", "gun": b["gun"]})
    sag = saglik_ozet()
    fnd = funding_ozet(gun) if api else {"var": False}
    dur, sebep = karar(b, sap, sag, fnd)

    s = []
    s.append("=" * 64)
    s.append(f"  CARRY BOT — GÜNLÜK RAPOR        KARAR: {_renk(dur)} {dur}")
    s.append("=" * 64)
    s.append("")
    _y = b.get("son_kayit_saat", 0.0)
    s.append(f"  çalışma süresi   : {b['gun']} gün")
    s.append(f"  son tur          : {_y:.1f} saat önce"
             f"{'' if _y < BAYAT_INCELE_SAAT else '   <-- BOT DURMUŞ OLABİLİR'}")
    s.append(f"  bakiye           : {b['bakiye']:.2f} USD "
             f"(başlangıç {b['ilk_bakiye']:.2f})")
    s.append(f"  toplam getiri    : %{b['getiri']*100:+.2f}")
    s.append(f"  günlük ortalama  : %{b['gunluk_ort']*100:+.3f} "
             f"(harman beklenti %{BEKLENEN_GUNLUK*100:+.3f})")
    # MADDE 232: hangi REJIMDE oldugumuz, hangi beklentinin gecerli
    # oldugunu soyleyen tek sey (madde 231). Tahsil edilen funding,
    # primin seviyesinin en dogrudan canli olcusu.
    if fnd.get("var") and b.get("gun", 0) >= 3:
        _fg = (float(fnd.get("funding", 0) or 0)
               / max(1e-9, b.get("gun", 0) * b.get("ilk_bakiye", 0)))
        _rj, _bek = rejim_tahmini(_fg)
        s.append(f"  funding tahsilatı: %{_fg*100:.4f}/gün  "
                 f"(düşük prim %{BEKLENEN_FUNDING_TABAN*100:.4f} / "
                 f"harman %{BEKLENEN_FUNDING_GUNLUK*100:.4f} / "
                 f"yüksek %{BEKLENEN_FUNDING_YUKSEK*100:.4f})")
        s.append(f"  → REJİM          : {_rj}  "
                 f"geçerli beklenti ~+%{_bek:.0f}/yıl (madde 231)")
    _pank = kitap_anahtari(bakiye=b.get("ilk_bakiye") or None)   # madde 329
    s.append(f"  maksimum düşüş   : %{b['dusus']*100:.1f} "
             f"(incele %{dusus_incele(_pank)*100:.0f} / "
             f"durdur %{dusus_durdur(_pank)*100:.0f}; {_pank}, "
             f"{esik_kademesi(_pank)})")
    s.append("")
    if sap.get("durum") != "YETERSİZ":
        s.append(f"  sapma durumu     : {sap['durum']} "
                 f"(dağılımın %{sap.get('yuzdelik', 0):.0f}. yüzdeliği)")
        s.append(f"  testin gücü      : %{sap.get('guc', 0):.0f} "
                 f"({b['gun']} günde ölü stratejiyi yakalama olasılığı)")
    else:
        s.append(f"  sapma durumu     : YETERSİZ ({b['gun']} gün, 7 gün gerekli)")
    s.append(f"  sağlık kapısı    : "
             f"{'AÇIK' if sag.get('acik', True) else 'KAPALI'}"
             f"{'' if sag.get('var') else ' (dosya yok - bot henüz yazmadı)'}")
    if fnd.get("var"):
        s.append(f"  funding (son {gun}g): {fnd.get('funding', 0):+.2f} USD | "
                 f"komisyon {fnd.get('komisyon', 0):+.2f} | "
                 f"net {fnd.get('net', 0):+.2f}")
    elif api:
        s.append(f"  funding ölçümü   : ALINAMADI ({fnd.get('hata', '?')})")
    s.append("")
    s.append("  GEREKÇE:")
    for x in sebep:
        s.append(f"    {x}")
    s.append("")
    if b["gun"] < 30:
        s.append("  NOT: 30 günden kısa veride getiri neredeyse hiçbir şey")
        s.append("  söylemez (ölü stratejiyi yakalama gücü ~%15). Bu dönemde")
        s.append("  asıl kanıt `carry_rapor.py --api` ile funding tahsilatıdır.")
        s.append("")
    s.append("  Normal olan: zararlı gün %46, zararlı hafta %39, zararlı ay")
    s.append("  %14. Üst üste 3 zararlı ay ve 118 gün düşüşte kalma tarihte")
    s.append("  GÖRÜLDÜ. Tek başına zarar, bilgi değildir.")
    s.append("=" * 64)
    return "\n".join(s)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gun", type=int, default=7,
                    help="funding/işlem penceresi (gün)")
    ap.add_argument("--api", action="store_true",
                    help="borsadan gerçek funding tahsilatını da ölç")
    a = ap.parse_args()
    print(yaz(a.gun, a.api))


if __name__ == "__main__":
    main()
