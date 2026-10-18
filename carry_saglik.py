"""CARRY EDGE SAĞLIK DEDEKTÖRÜ — edge ölürse fiyat kaybını beklemeden yakala.

NEDEN (madde 139): carry'nin kârı funding'den gelir ve funding
metrikleri fiyattan ~9 kat daha az gürültülüdür (tek rebalance sd:
funding 63 bp, fiyat 546 bp). Bu yüzden "edge öldü mü?" sorusunu
getiri eğrisine bakarak değil, doğrudan funding'e bakarak sormak
çok daha hızlı ve çok daha az yanlış alarmlı olur.

Üç metrik, hepsi nedensel (karar anında bilinir):

  IC   : önceki seçim anındaki funding sırası ile o dönemde GERÇEKLEŞEN
         funding arasındaki Spearman. Kalıcılık ölürse ~0'a düşer.
  F    : kitabın önceki dönemde gerçekten topladığı funding
         (brüt notional başına). Prim ölürse ~0'a düşer.
  DISP : ŞU ANKİ seçimde short ve long bacak arasındaki funding farkı.
         Toplanacak prim kalmazsa daralır. Beklemeden bilinir.

EŞİKLER 2022-07 .. 2024-12 verisinden, ÖNCEDEN sabitlendi; 2025-26
yanlış alarm testi için hiç kullanılmadı. Değiştirilirse madde 139'daki
ölçümler geçersiz olur.
"""
from __future__ import annotations

import numpy as np

# ---- ÖNCEDEN SABİTLENMİŞ EŞİKLER (2022-07..2024-12 kalibrasyonu) ----
# Eğitim döneminde kayan 6-rebalance (30 gün) ortalamaların minimumları:
#   IC  min +0.386, F min +4.62 bp, DISP min +5.71 bp  (N=156 pencere)
# Kural: IC ve DISP için eğitim minimumunun YARISI; F için "30 günde
# net funding geliri sıfır ya da eksi". Üçü de eğitimde HİÇ görülmemiş
# bir bozulma demektir - normal dalgalanma değil.
IC_ESIK = 0.193
"""MADDE 234 — IC ARTIK KAPIYI KAPATMIYOR, YALNIZCA UYARIR.

Bu eşik, kapının 4 yılda tek ötme olayının SEBEBİydi ve o olay bir
YANLIŞ ALARMdı. Ölçüldü (1.478 gözlem, kayan 6 pencere ortalaması,
ileriye dönük 30 günlük getiriye karşı):

  ölçüt   alt %10   üst %90   tüm ort   Spearman        eşiğin altında
  IC       +%7,9     +%7,1     +%6,7   0,048 (p=0,067)     **+%10,9**
  F        +%4,0    +%10,5     +%6,7   0,314 (p<0,001)      +%6,7
  DISP     +%2,1     +%9,2     +%6,7   0,336 (p<0,001)      -%1,7

**IC'nin ileriye dönük haber değeri YOK** - ve eşiğinin altındayken
getiri ortalamanın ÜSTÜNDE (+%10,9 vs +%6,7). Yani eşik, tehlike değil
neredeyse alım sinyali işaretliyor. F ve DISP ise gerçekten sıralıyor.

TARİHSEL SİMÜLASYON: kapı 295 pencerenin 6'sında (%2,0) BOZUK diyor ve
altısı tek bir olay - 2024-11-16..12-11, hepsi IC yüzünden. O dönemde
strateji 36 günde **+%25,5** yaptı, yani aynı uzunluktaki tüm
pencerelerin **95. yüzdeliği**. Kapı kitabı stratejinin en iyi
dönemlerinden birinde kapatacaktı.

MADDE 139'UN KENDİ KAYDI BUNU DESTEKLİYOR: IC'nin var olma sebebi
"kalıcılık ölümü" (senaryo A) idi; yakalama 40/40 ama getiri farkı
**-1,5 puan, t=-0,55 - ANLAMSIZ**. Yani IC, madde 139'un kendi
ölçümünde bile anlamlı bir fayda vermiyordu. Senaryo B/C (prim
sıkışması, yavaş erime) ise F ve DISP'in senaryoları ve orada fayda
GERÇEK (düşüş -%26,3 -> -%17,9).

Ayrıca madde 139.5'in "sağlıklı edge'e hiç dokunmuyor (0 yanlış alarm)"
iddiası ÇÜRÜDÜ - o ölçüm, 2024-11 öncesi veriyle ve madde 177-222
öncesi yapılandırmayla yapılmıştı.

IC hesaplanmaya ve raporlanmaya DEVAM EDİYOR (senaryo A kanaryası ve
bedava), ama artık yalnızca "UYARI" üretir; kitabı kapatmaz."""
F_ESIK = 0.0            # kayan ortalama funding geliri <= 0 ise (oran)
DISP_ESIK = 2.86e-4     # kayan ortalama short-long funding farkı (günlük eşdeğer)
PENCERE = 6             # 6 rebalance = 30 gün (5 günlük tutmada)
TOPARLANMA = 2          # tüm koşullar art arda bu kadar tur temizse devam


def saglik_durumu(ic_gecmis, f_gecmis, disp_gecmis, pencere=PENCERE):
    """Son `pencere` gözlemin ortalamasıyla durum döner.

    Argümanlar en eskiden en yeniye listeler. Yetersiz geçmişte
    ('ISINMA') karar verilmez - edge sağlıklı varsayılır. Bu bilinçli:
    veri yokken durmak, madde 123'teki sessiz duruş hatasının aynısı olur.

    Döner: (durum, gerekce)  durum in {"SAGLIKLI", "BOZUK", "ISINMA"}
    """
    ic = [x for x in ic_gecmis if x is not None and np.isfinite(x)]
    f = [x for x in f_gecmis if x is not None and np.isfinite(x)]
    d = [x for x in disp_gecmis if x is not None and np.isfinite(x)]
    if len(ic) < pencere or len(f) < pencere or len(d) < 1:
        return "ISINMA", f"yetersiz gecmis (ic {len(ic)}, f {len(f)}, disp {len(d)})"
    ic_o = float(np.mean(ic[-pencere:]))
    f_o = float(np.mean(f[-pencere:]))
    d_o = float(np.mean(d[-min(pencere, len(d)):]))
    # MADDE 234: KAPIYI KAPATAN olcutler yalnizca F ve DISP. IC'nin
    # ileriye donuk haber degeri olculdu ve YOK (Spearman 0,048,
    # p=0,067); esiginin altinda getiri ORTALAMANIN USTUNDE. Kapinin 4
    # yildaki tek otmesi IC yuzundendi ve stratejinin +%25,5 yaptigi 36
    # gune denk geliyordu. IC yine olculup RAPORLANIYOR ama kapatmiyor.
    sebep = []
    if f_o <= F_ESIK:
        sebep.append(f"funding geliri {f_o * 1e4:+.1f}bp <= 0")
    if d_o < DISP_ESIK:
        sebep.append(f"funding farki {d_o * 1e4:+.1f}bp < {DISP_ESIK * 1e4:.1f}bp")
    _ic_not = (f"  [UYARI madde 234: IC {ic_o:+.3f} < {IC_ESIK} - kapatma "
               f"ölçütü DEĞİL, haber değeri ölçüldü ve yok]"
               if ic_o < IC_ESIK else "")
    if sebep:
        return "BOZUK", "; ".join(sebep) + _ic_not
    return ("SAGLIKLI",
            f"IC {ic_o:+.3f}, F {f_o * 1e4:+.1f}bp, "
            f"DISP {d_o * 1e4:+.1f}bp" + _ic_not)


def _sira_korelasyonu(a: dict, b: dict) -> float:
    """Spearman: ortak semboller üzerinde sıra korelasyonu (scipy'siz)."""
    import pandas as pd
    ortak = [s for s in a if s in b and np.isfinite(a[s]) and np.isfinite(b[s])]
    if len(ortak) < 10:
        return float("nan")
    x = pd.Series([a[s] for s in ortak]).rank()
    y = pd.Series([b[s] for s in ortak]).rank()
    if x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(x.corr(y))


def _yillik(kayit_listesi) -> float | None:
    """(zaman_ms, oran) listesinden yıllık oran - carry_bot.yillik_funding
    ile AYNI mantık (medyan aralık, alt sınır 4 saat)."""
    if len(kayit_listesi) < 2:
        return None
    z = sorted(t for t, _ in kayit_listesi)
    fark = [(z[i + 1] - z[i]) / 3600000.0 for i in range(len(z) - 1)]
    fark = [f for f in fark if 0.5 <= f <= 24]
    if not fark:
        return None
    aralik = max(sorted(fark)[len(fark) // 2], 4.0)
    ort = sum(r for _, r in kayit_listesi) / len(kayit_listesi)
    return ort * (24.0 / aralik) * 365.0


def metrikleri_hesapla(gecmis: dict, simdi_ms: int, n_legs: int,
                       blok_saat: float = 120.0, sinyal_saat: float = 72.0,
                       pencere: int = PENCERE):
    """Funding geçmişinden IC, F ve DISP dizilerini DURUMSUZ hesaplar.

    gecmis: {sembol: [(fundingTime_ms, fundingRate), ...]}
    Son `pencere` tamamlanmış blok değerlendirilir. Blok k için:
      t_k      = simdi - k*blok               (k = pencere..1)
      sinyal   = [t_k - sinyal_saat, t_k] arası yıllık ortalama funding
      gölge    = sinyale göre en düşük n long / en yüksek n short
      gerçek   = (t_k, t_k + blok] arasında ÖDENEN ham oranların toplamı
      IC_k     = Spearman(sinyal, gerçek)
      F_k      = (-Σ gerçek[long] + Σ gerçek[short]) / (2n)
      DISP_k   = (ort sinyal[short] - ort sinyal[long]) / 365  (günlük)
    Ek olarak ŞU ANKİ DISP (blok 0) listeye eklenir.

    Gölge kitap, bot pozisyonsuzken bile hesaplanır - aksi halde kapı
    bir kez kapanınca edge'in geri geldiğini hiç göremezdi.
    """
    B = blok_saat * 3600000.0
    W = sinyal_saat * 3600000.0
    ic, f, disp = [], [], []
    for k in range(pencere, -1, -1):
        t = simdi_ms - k * B
        sinyal = {}
        for s, kay in gecmis.items():
            pen = [(z, r) for z, r in kay if t - W < z <= t]
            y = _yillik(pen)
            if y is not None:
                sinyal[s] = y
        if len(sinyal) < 2 * max(1, min(n_legs, 3)):
            if k > 0:
                ic.append(float("nan")); f.append(float("nan"))
            disp.append(float("nan"))
            continue
        sirali = sorted(sinyal, key=sinyal.get)
        n = min(n_legs, len(sirali) // 2)
        L, S = sirali[:n], sirali[-n:]
        disp.append((np.mean([sinyal[s] for s in S])
                     - np.mean([sinyal[s] for s in L])) / 365.0)
        if k == 0:
            continue                      # şimdiki blok henüz gerçekleşmedi
        gercek = {s: sum(r for z, r in gecmis[s] if t < z <= t + B)
                  for s in sinyal}
        ic.append(_sira_korelasyonu(sinyal, gercek))
        f.append((-sum(gercek[s] for s in L) + sum(gercek[s] for s in S))
                 / (2 * n))
    return ic, f, disp


def kapi_guncelle_zamanli(kapi: dict, durum: str, simdi_ms: int,
                          blok_saat: float = 120.0,
                          toparlanma: int = TOPARLANMA) -> dict:
    """Canlı bot için ZAMAN bazlı histerezis.

    Bot günde bir tur atar ama eşikler 5 günlük bloklarla kalibre edildi.
    Tur saymak kapıyı 2 günde yeniden açardı; burada gereken süre
    `toparlanma x blok` = 10 gün kesintisiz SAGLIKLI'dır.

    kapi: {"acik": bool, "temiz_bas_ms": int|None, "kapanis_ms": int|None}
    """
    k = {"acik": True, "temiz_bas_ms": None, "kapanis_ms": None}
    k.update(kapi or {})
    if durum == "BOZUK":
        if k["acik"]:
            k["kapanis_ms"] = simdi_ms
        k["acik"] = False
        k["temiz_bas_ms"] = None
    elif durum == "SAGLIKLI" and not k["acik"]:
        if k["temiz_bas_ms"] is None:
            k["temiz_bas_ms"] = simdi_ms
        if simdi_ms - k["temiz_bas_ms"] >= toparlanma * blok_saat * 3600000.0:
            k["acik"] = True
            k["temiz_bas_ms"] = None
            k["kapanis_ms"] = None
    return k


class SaglikKapisi:
    """Durdurma / devam etme kararını histerezisle verir.

    BOZUK görülür görülmez kapı kapanır (pozisyonlar sıfırlanır).
    Yeniden açılması için TOPARLANMA kadar art arda SAGLIKLI tur gerekir -
    eşik etrafında aç-kapa yapıp ücret yakmamak için.
    """

    def __init__(self, toparlanma=TOPARLANMA):
        self.acik = True
        self.temiz_seri = 0
        self.toparlanma = toparlanma

    def guncelle(self, durum: str) -> bool:
        if durum == "BOZUK":
            self.acik = False
            self.temiz_seri = 0
        elif durum == "SAGLIKLI":
            if not self.acik:
                self.temiz_seri += 1
                if self.temiz_seri >= self.toparlanma:
                    self.acik = True
                    self.temiz_seri = 0
        # ISINMA: durumu değiştirme
        return self.acik
