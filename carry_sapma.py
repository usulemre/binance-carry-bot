"""CANLI / BACKTEST SAPMA KONTROLÜ (madde 151).

Bot her turda bakiyesini `carry_equity.csv` dosyasına yazar. Bu araç o
kayıtlardan GERÇEKLEŞEN getiriyi çıkarır ve backtest'in AYNI UZUNLUKTAKİ
dönemlerde ürettiği dağılımla karşılaştırır.

Sorduğu soru şudur: "bu sonuç, strateji backtest'teki gibi çalışıyorken
de görülebilir mi?" Cevap hayırsa strateji canlıda beklendiği gibi
çalışmıyor demektir.

NEDEN BÖYLE: strateji ayların yaklaşık üçte birini zararda kapatıyor.
"İki hafta eksideyiz" tek başına hiçbir şey ifade etmez. Ölçüt, aynı
uzunlukta backtest dönemlerinin dağılımıdır.

KULLANIM:
    python carry_sapma.py                 # carry_equity.csv'yi okur
    python carry_sapma.py --dosya x.csv --referans referans_getiri.csv

ÖNEMLİ: bu araç FİYAT ya da POZİSYON bilmez; sadece bakiye serisine
bakar. Funding tahsilatı, maker oranı ve komisyon için `carry_izleme.py`
kullanın - ikisi birbirini tamamlar.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import pandas as pd

R = os.path.dirname(os.path.abspath(__file__))
REFERANS = os.path.join(R, "referans_getiri.csv")
EQUITY = os.path.join(R, "carry_equity.csv")
MIN_GUN = 7          # altında istatistik anlamsız
BLOK = 5             # blok örnekleme uzunluğu (gün) - günlük getiriler bağımsız değil
N_ORNEK = 4000
DUSUK_YUZDELIK = 5.0     # bunun altı "beklenenin altında"
COK_DUSUK_YUZDELIK = 1.0  # bunun altı "ciddi sapma"


def bakiye_oku(dosya: str = None) -> pd.DataFrame:
    """carry_equity.csv -> zaman, bakiye, ölçek. Bozuk satırlar atlanır."""
    yol = dosya or EQUITY
    if not os.path.exists(yol):
        return pd.DataFrame(columns=["zaman", "bakiye", "olcek"])
    satirlar = []
    with open(yol, encoding="utf-8") as fh:
        for s in fh:
            p = s.strip().split(",")
            if len(p) < 2:
                continue
            try:
                z, b = float(p[0]), float(p[1])
                o = float(p[2]) if len(p) >= 3 else 1.0
            except ValueError:
                continue
            if b > 0 and o > 0:
                satirlar.append((z, b, o))
    d = pd.DataFrame(satirlar, columns=["zaman", "bakiye", "olcek"]).sort_values("zaman")
    d["tarih"] = pd.to_datetime(d.zaman, unit="s")
    return d


def gunluk_getiri(d: pd.DataFrame) -> pd.Series:
    """Bakiye kayıtlarından KALDIRAÇSIZ günlük getiri.

    Bot günde bir tur atar ama tur saati kayabilir; aynı güne düşen
    birden fazla kayıttan SONUNCUSU alınır. Getiri, o dönemde uygulanan
    ölçeğe bölünür - böylece kaldıraçlı ve kaldıraçsız dönemler
    karşılaştırılabilir olur (madde 140.1 ile aynı mantık)."""
    if len(d) < 2:
        return pd.Series(dtype=float)
    g = d.set_index("tarih").resample("1D").last().dropna(subset=["bakiye"])
    ham = g.bakiye.pct_change()
    olcek = g.olcek.shift(1).where(lambda x: x > 0, 1.0)
    return (ham / olcek).dropna()


def referans_oku(dosya: str = None) -> pd.Series:
    yol = dosya or REFERANS
    d = pd.read_csv(yol, parse_dates=["tarih"]).set_index("tarih")["getiri"]
    return d.dropna()


def bant(ref: pd.Series, gun: int, n_ornek: int = N_ORNEK,
         blok: int = BLOK, tohum: int = 0) -> dict:
    """Backtest getirilerinden `gun` günlük dönemlerin dağılımı.

    Blok örnekleme: günlük getiriler bağımsız değil (düşüşler kümeleniyor),
    tek tek karıştırmak dağılımı DAR gösterir ve her sapmayı alarma
    çevirirdi."""
    v = ref.values
    if len(v) < blok * 2 or gun < 1:
        return {}
    rng = np.random.default_rng(tohum)
    n_blok = int(np.ceil(gun / blok))
    bas = rng.integers(0, len(v) - blok, size=(n_ornek, n_blok))
    ix = (bas[:, :, None] + np.arange(blok)[None, None, :]).reshape(n_ornek, -1)[:, :gun]
    toplam = np.prod(1.0 + v[ix], axis=1) - 1.0
    return {
        "p1": float(np.percentile(toplam, 1)),
        "p5": float(np.percentile(toplam, 5)),
        "p25": float(np.percentile(toplam, 25)),
        "orta": float(np.percentile(toplam, 50)),
        "p75": float(np.percentile(toplam, 75)),
        "p95": float(np.percentile(toplam, 95)),
        "artida_olasilik": float((toplam > 0).mean()),
    }


def yuzdelik(ref_bant_ornekleri: np.ndarray, deger: float) -> float:
    return float((ref_bant_ornekleri < deger).mean() * 100)


def degerlendir(getiriler: pd.Series, ref: pd.Series, tohum: int = 0) -> dict:
    """Gerçekleşen getiriyi referans dağılımıyla karşılaştırır."""
    gun = len(getiriler)
    if gun < MIN_GUN:
        return {"durum": "YETERSİZ", "gun": gun,
                "mesaj": f"{gun} gün veri var, en az {MIN_GUN} gün gerekiyor."}
    gercek = float(np.prod(1.0 + getiriler.values) - 1.0)
    v = ref.values
    rng = np.random.default_rng(tohum)
    n_blok = int(np.ceil(gun / BLOK))
    bas = rng.integers(0, len(v) - BLOK, size=(N_ORNEK, n_blok))
    ix = (bas[:, :, None] + np.arange(BLOK)[None, None, :]).reshape(N_ORNEK, -1)[:, :gun]
    ornek = np.prod(1.0 + v[ix], axis=1) - 1.0
    yuzde = float((ornek < gercek).mean() * 100)
    if yuzde < COK_DUSUK_YUZDELIK:
        durum = "CİDDİ SAPMA"
    elif yuzde < DUSUK_YUZDELIK:
        durum = "BEKLENENİN ALTINDA"
    elif yuzde > 100 - COK_DUSUK_YUZDELIK:
        durum = "BEKLENENİN ÇOK ÜSTÜNDE"
    else:
        durum = "NORMAL"
    return {
        "durum": durum, "gun": gun, "gercek": gercek, "yuzdelik": yuzde,
        "guc": guc(ref, gun, 1.0, n=120, tohum=tohum + 11),
        "bant": {k: float(np.percentile(ornek, p))
                 for k, p in (("p1", 1), ("p5", 5), ("orta", 50), ("p95", 95))},
        "gunluk_ort": float(getiriler.mean()), "gunluk_std": float(getiriler.std()),
        "ref_gunluk_ort": float(ref.mean()), "ref_gunluk_std": float(ref.std()),
        "en_kotu_gun": float(getiriler.min()),
        "dusus": float(((1 + getiriler).cumprod() / (1 + getiriler).cumprod().cummax() - 1).min()),
    }


def guc(ref: pd.Series, gun: int, kayip: float = 1.0,
        n: int = 300, esik: float = DUSUK_YUZDELIK, tohum: int = 1) -> float:
    """Bu testin AYIRT ETME GÜCÜ: getirisi `kayip` oranında kaybolmuş bir
    strateji, `gun` günde yüzde kaç olasılıkla yakalanır?

    Gerekli, çünkü strateji zaten oynak: 30 günde ÖLÜ bir strateji bile
    çoğunlukla "normal" görünür. Bunu söylemeyen bir araç yanlış
    güven verir."""
    v = ref.values
    if len(v) < BLOK * 2 or gun < 1:
        return 0.0
    mu = float(v.mean())
    rng = np.random.default_rng(tohum)
    n_blok = int(np.ceil(gun / BLOK))
    yakalanan = 0
    for _ in range(n):
        bas = rng.integers(0, len(v) - BLOK, size=n_blok)
        ix = (bas[:, None] + np.arange(BLOK)[None, :]).reshape(-1)[:gun]
        r = float(np.prod(1.0 + (v[ix] - kayip * mu)) - 1.0)
        b = rng.integers(0, len(v) - BLOK, size=(1500, n_blok))
        jx = (b[:, :, None] + np.arange(BLOK)[None, None, :]).reshape(1500, -1)[:, :gun]
        orn = np.prod(1.0 + v[jx], axis=1) - 1.0
        if (orn < r).mean() * 100 < esik:
            yakalanan += 1
    return yakalanan / n * 100


def rapor(sonuc: dict) -> str:
    if sonuc.get("durum") == "YETERSİZ":
        return f"YETERSİZ VERİ: {sonuc['mesaj']}"
    b = sonuc["bant"]
    y = ["=" * 62, f"CANLI / BACKTEST KARŞILAŞTIRMASI - {sonuc['gun']} gün", "=" * 62,
         f"  gerçekleşen getiri : {sonuc['gercek']*100:+.2f}%",
         f"  backtest ortancası : {b['orta']*100:+.2f}%",
         f"  backtest %5-%95    : {b['p5']*100:+.2f}% ... {b['p95']*100:+.2f}%",
         f"  bulunduğu yüzdelik : %{sonuc['yuzdelik']:.0f}",
         f"  günlük oynaklık    : canlı %{sonuc['gunluk_std']*100:.2f} / "
         f"backtest %{sonuc['ref_gunluk_std']*100:.2f}",
         f"  en kötü gün        : {sonuc['en_kotu_gun']*100:+.2f}%",
         f"  düşüş              : {sonuc['dusus']*100:.2f}%",
         "", f"  DURUM: {sonuc['durum']}"]
    if sonuc["durum"] == "NORMAL":
        y.append("  Sonuç backtest dağılımının içinde. Bu, stratejinin kâr")
        y.append("  ettiğini DEĞİL, canlı sonucun beklenenden sapmadığını gösterir.")
        if sonuc.get("guc") is not None and sonuc["guc"] < 50:
            y.append(f"  DİKKAT: bu sürede testin gücü sadece %{sonuc['guc']:.0f}. Yani")
            y.append("  edge tamamen ölmüş olsa bile büyük olasılıkla 'NORMAL' görünürdü.")
            y.append("  Toplam kâr çok gürültülü; asıl kanıt BİLEŞENLERDEDİR:")
            y.append("  python carry_izleme.py --gun 7  (funding tahsilatı, maker oranı, komisyon)")
    elif sonuc["durum"] == "BEKLENENİN ALTINDA":
        y.append("  Backtest dönemlerinin %95'i bundan iyi. Bir kez daha bakın:")
        y.append("  carry_izleme.py ile funding tahsilatı, maker oranı, komisyon.")
    elif sonuc["durum"] == "CİDDİ SAPMA":
        y.append("  Backtest dönemlerinin %99'u bundan iyi. Strateji canlıda")
        y.append("  backtest gibi çalışmıyor. ÖNCE SEBEBİ BULUN, kaldıraç ARTIRMAYIN.")
        y.append("  Sık sebepler: kayma, dolmayan limit emirler, funding'in")
        y.append("  tahsil edilmemesi, evren/bacak sayısının beklenenden farkı.")
    else:
        y.append("  Backtest dönemlerinin %99'undan iyi. Şanslı bir dönem de")
        y.append("  olabilir; kaldıraç kararı için birkaç ay daha bekleyin.")
    if sonuc["gun"] < 30:
        y.append("")
        y.append(f"  NOT: {sonuc['gun']} gün kısa bir süre. Bu testin ayırt etme")
        y.append("  gücü 30 günden sonra anlamlı olmaya başlar.")
    y.append("=" * 62)
    return "\n".join(y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dosya", default=None, help="bakiye geçmişi (carry_equity.csv)")
    ap.add_argument("--referans", default=None, help="referans günlük getiriler")
    a = ap.parse_args()
    d = bakiye_oku(a.dosya)
    if d.empty:
        print("Bakiye geçmişi yok. Bot en az birkaç tur çalışmalı "
              "(carry_equity.csv her turda yazılır).")
        return
    g = gunluk_getiri(d)
    ref = referans_oku(a.referans)
    print(rapor(degerlendir(g, ref)))
    print("\nBU TESTİN GÜCÜ (edge tamamen ölseydi yakalama olasılığı):")
    for gun in (30, 90, 180, 365):
        print(f"  {gun:>3} gün: %{guc(ref, gun, 1.0, n=120, tohum=gun):.0f}")
    print("  Bu yüzden tek başına bu araca bakarak kaldıraç kararı VERMEYİN.")


if __name__ == "__main__":
    main()
