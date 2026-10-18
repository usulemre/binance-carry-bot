"""carry_sapma.py testleri (madde 151).

En kritik test: aracın AYIRT ETME gücü. Backtest dağılımından üretilen
bir seri NORMAL, yarı getirili bir seri DÜŞÜK, çöken bir seri CİDDİ
SAPMA demeli. Aksi halde araç her şeye "normal" der ve işe yaramaz.
"""
import os
import sys
import tempfile
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import carry_sapma as cs

gecen = basarisiz = 0


def kontrol(ad, kosul, ek=""):
    global gecen, basarisiz
    if kosul:
        gecen += 1
        print(f"  [OK]   {ad}")
    else:
        basarisiz += 1
        print(f"  [HATA] {ad} {ek}")


REF = cs.referans_oku()


def seri(getiriler, bas=None, olcek=1.0):
    """Getiri listesinden sahte bakiye dosyası yazar, yolunu döner."""
    bas = bas or (time.time() - 86400 * (len(getiriler) + 1))
    yol = tempfile.mktemp(suffix=".csv")
    b = 1000.0
    with open(yol, "w", encoding="utf-8") as fh:
        fh.write(f"{bas:.0f},{b:.4f},{olcek:.6f}\n")
        for i, r in enumerate(getiriler):
            b *= 1 + r * olcek
            fh.write(f"{bas + 86400 * (i + 1):.0f},{b:.4f},{olcek:.6f}\n")
    return yol


print("1) REFERANS VERİSİ")
kontrol("referans dosyası var ve 1000+ gün", len(REF) > 1000, f"({len(REF)})")
kontrol("referans günlük ortalama makul (%0.05-%0.25)",
        0.0005 < REF.mean() < 0.0025, f"({REF.mean()*100:.3f}%)")
kontrol("referans günlük oynaklık makul (%0.5-%2)",
        0.005 < REF.std() < 0.02, f"({REF.std()*100:.3f}%)")

print("\n2) BAKİYE OKUMA")
y = seri([0.01, -0.005, 0.02])
d = cs.bakiye_oku(y)
kontrol("3 getirili dosyadan 4 kayıt okundu", len(d) == 4, f"({len(d)})")
g = cs.gunluk_getiri(d)
kontrol("günlük getiriler doğru hesaplandı",
        len(g) == 3 and abs(g.iloc[0] - 0.01) < 1e-6 and abs(g.iloc[2] - 0.02) < 1e-6,
        f"({list(np.round(g.values, 5))})")
y2 = seri([0.01, -0.005, 0.02], olcek=2.0)
g2 = cs.gunluk_getiri(cs.bakiye_oku(y2))
kontrol("KALDIRAÇLI kayıtlar kaldıraçsıza çevriliyor (ölçeğe bölünüyor)",
        abs(g2.iloc[1] - g.iloc[1]) < 1e-6,
        f"({g2.iloc[1]:.5f} vs {g.iloc[1]:.5f})")
with open(y, "a", encoding="utf-8") as fh:
    fh.write("bozuk,satir\nx\n,,\n")
kontrol("bozuk satırlar çökertmiyor, atlanıyor", len(cs.bakiye_oku(y)) == 4)
kontrol("dosya yoksa boş dönüyor, çökmüyor",
        cs.bakiye_oku("/tmp/olmayan_dosya_xyz.csv").empty)

print("\n3) AYIRT ETME GÜCÜ (30 gün)")
rng = np.random.default_rng(7)


def durum_dagilimi(carpan, n=40, gun=30, tohum0=100):
    """Referanstan blok örneklenmiş, `carpan` ile ölçeklenmiş serilerin durumları."""
    v = REF.values
    say = {}
    for t in range(n):
        r = np.random.default_rng(tohum0 + t)
        bas = r.integers(0, len(v) - 5, size=int(np.ceil(gun / 5)))
        ix = (bas[:, None] + np.arange(5)[None, :]).reshape(-1)[:gun]
        s = cs.degerlendir(pd.Series(v[ix] * carpan), REF, tohum=t)
        say[s["durum"]] = say.get(s["durum"], 0) + 1
    return say


d_normal = durum_dagilimi(1.0)
kontrol("backtest gibi giden seri çoğunlukla NORMAL",
        d_normal.get("NORMAL", 0) >= 32, f"({d_normal})")
d_olu = durum_dagilimi(0.0)
kontrol("ÖLÜ strateji 30 günde ÇOĞUNLUKLA yakalanmıyor (testin gerçek sınırı)",
        d_olu.get("NORMAL", 0) >= 30, f"({d_olu})")
d_ters = durum_dagilimi(-1.0)
kontrol("getirisi TERS dönmüş seri daha sık yakalanıyor",
        d_ters.get("NORMAL", 0) < d_normal.get("NORMAL", 0), f"({d_ters})")

print("\n3b) GÜÇ HESABI VE UYARI")
g30 = cs.guc(REF, 30, 1.0, n=60, tohum=3)
g365 = cs.guc(REF, 365, 1.0, n=60, tohum=3)
# MADDE 179: yeni yapılandırmada sinyal/gürültü yükseldi, güç de arttı
# (%15 -> ~%27-30). Yine de YARIDAN AZ: 30 günlük getiri hâlâ zayıf
# kanıt, asıl kanıt carry_izleme.py'nin funding tahsilatıdır.
kontrol("30 günde ölü stratejiyi yakalama gücü hâlâ YARIDAN AZ",
        g30 < 50, f"(%{g30:.0f})")
kontrol("365 günde güç belirgin artıyor (>30 puan fark)",
        g365 > g30 + 30, f"(%{g30:.0f} -> %{g365:.0f})")
kontrol("365 günde güç YÜKSEK (>%70)", g365 > 70, f"(%{g365:.0f})")
# MADDE 184: tek tohumda n=200 Monte Carlo gurultusu +-5 puan oynuyor
# (tohum 3/5/7 -> %5.5 / %12.0 / %2.5). Esigi gevsetmek yerine UC
# TOHUMUN ORTALAMASI alinir - ayni testin daha az gurultulu hali.
_ya = [cs.guc(REF, 90, 0.0, n=200, tohum=t) for t in (3, 5, 7)]
_yao = sum(_ya) / len(_ya)
kontrol("yanlış alarm oranı eşiğe yakın (%5 civarı)",
        _yao < 10, f"(ortalama %{_yao:.1f}, tohumlar {[round(x,1) for x in _ya]})")
_r30 = cs.rapor(cs.degerlendir(pd.Series(REF.values[:30]), REF))
kontrol("NORMAL raporu düşük güç uyarısı ve carry_izleme yönlendirmesi içeriyor",
        "gücü sadece" in _r30 and "carry_izleme" in _r30)
s_cok = cs.degerlendir(pd.Series([-0.02] * 30), REF)
kontrol("her gün -%2 kaybeden seri CİDDİ SAPMA",
        s_cok["durum"] == "CİDDİ SAPMA", f"({s_cok['durum']})")
s_iyi = cs.degerlendir(pd.Series([0.02] * 30), REF)
kontrol("her gün +%2 kazanan seri 'çok üstünde'",
        s_iyi["durum"] == "BEKLENENİN ÇOK ÜSTÜNDE", f"({s_iyi['durum']})")

print("\n4) KISA VERİ VE SINIRLAR")
kontrol("7 günden az veri YETERSİZ diyor",
        cs.degerlendir(pd.Series([0.01] * 5), REF)["durum"] == "YETERSİZ")
s7 = cs.degerlendir(pd.Series(REF.values[:7]), REF)
kontrol("7 günde çalışıyor ama rapor kısalık notu veriyor",
        s7["durum"] != "YETERSİZ" and "30 gün" in cs.rapor(s7))
s_tek = cs.degerlendir(pd.Series([-0.03] + [0.002] * 29), REF)
kontrol("TEK kötü gün tek başına alarm ÜRETMİYOR",
        s_tek["durum"] == "NORMAL", f"({s_tek['durum']}, %{s_tek['yuzdelik']:.0f})")

print("\n5) BANT VE RAPOR")
b = cs.bant(REF, 30)
kontrol("30 günlük bant sıralı (p5 < orta < p95)",
        b["p5"] < b["orta"] < b["p95"], f"({b})")
kontrol("30 günlük ortanca getiri %1-%10 arası",
        0.01 < b["orta"] < 0.10, f"({b['orta']*100:.1f}%)")
kontrol("uzun dönem bandı daha yüksek ortanca veriyor",
        cs.bant(REF, 180)["orta"] > b["orta"])
# MADDE 178: yeni referans seride (6+6, kâr al %40) günlük otokorelasyon
# ~0 (-0.026). Bu yüzden blok örnekleme ile tekil karıştırma ARTIK
# neredeyse aynı bandı veriyor (25.8 vs 26.4 puan). Eski seride blok
# bandı belirgin GENİŞTİ. Blok örnekleme yine de KORUNUYOR: otokorelasyon
# geri gelirse tek doğru yöntem odur, ve maliyeti yok.
_b1 = cs.bant(REF, 30, blok=1)
_gb, _g1 = b["p95"] - b["p5"], _b1["p95"] - _b1["p5"]
kontrol("blok ve tekil bant genişliği birbirine YAKIN (otokorelasyon ~0)",
        abs(_gb - _g1) / max(_g1, 1e-9) < 0.15,
        f"(blok {_gb*100:.1f} vs tekil {_g1*100:.1f} puan)")
r = cs.rapor(cs.degerlendir(pd.Series([-0.02] * 30), REF))
kontrol("ciddi sapma raporu kaldıraç UYARISI içeriyor", "kaldıraç ARTIRMAYIN" in r)
kontrol("rapor sebep listesi veriyor", "kayma" in r and "funding" in r)

print("\n" + "=" * 50)
print(f"GEÇEN: {gecen}   BAŞARISIZ: {basarisiz}")
if basarisiz:
    sys.exit(1)
print("Tum sapma testleri gecti.")
