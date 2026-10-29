#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 658 testleri: kâr çekimi / para yatırma raporlarda (carry_sapma / carry_rapor) zarar ya da düşüş sayılmaz."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("CARRY_PROFIL", "T4")
import carry_bot as cb, carry_sapma as cs
_h = 0
def kontrol(ad, ok, ek=""):
    global _h
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else "")); _h += 0 if ok else 1

class _C:
    def __init__(s, gelir): s.gelir = gelir
    def futures_income_history(s, incomeType=None, startTime=0, limit=1000):
        return [{"income": str(v), "time": t} for t, v in s.gelir if t >= startTime]
class F:
    def __init__(s, gelir): s.client = _C(gelir)

d = tempfile.mkdtemp(); yol = os.path.join(d, "eq.csv")
gun = 86400
# 4 gün: 2000 -> 2040 -> 2080 ; 3. gün 600 $ çekildi -> 1500 (gerçek getiri ≈ +%0,96) ; 4. gün 1530
satirlar = [(1_700_000_000 + 0 * gun, 2000.0), (1_700_000_000 + 1 * gun, 2040.0), (1_700_000_000 + 2 * gun, 2080.0)]
with open(yol, "w") as fh:
    for z, b in satirlar: fh.write(f"{z},{b},1.0,0.0\n")
cekim_zamani_ms = (1_700_000_000 + 2 * gun + 3600) * 1000
f = F([(cekim_zamani_ms, -600.0)])
t = cb.transfer_kumulatif(f, yol)
kontrol("çekim sonrası birikimli transfer −600", abs(t - (-600.0)) < 1e-9, t)
with open(yol, "a") as fh: fh.write(f"{1_700_000_000 + 3 * gun},1500.0,1.0,{t}\n")
t2 = cb.transfer_kumulatif(f, yol)
kontrol("sonraki turda aynı çekim tekrar sayılmaz", abs(t2 - (-600.0)) < 1e-9, t2)
with open(yol, "a") as fh: fh.write(f"{1_700_000_000 + 4 * gun},1530.0,1.0,{t2}\n")
g = cs.gunluk_getiri(cs.bakiye_oku(yol))
kontrol("çekim günü getirisi ≈ +%0,96 (−%28 değil)", abs(g.iloc[2] - (1500 + 600) / 2080 + 1) < 1e-9, g.round(4).tolist())
e = (1 + g).cumprod(); dd = float((e / e.cummax() - 1).min())
kontrol("düşüş yok (rapor DURDUR/İNCELE demez)", dd >= -1e-9, dd)
# eski dosya biçimi (3 sütun) hâlâ okunur
y2 = os.path.join(d, "eski.csv")
with open(y2, "w") as fh: fh.write("1700000000,2000,1.0\n1700086400,2020,1.0\n")
g2 = cs.gunluk_getiri(cs.bakiye_oku(y2))
kontrol("3 sütunlu eski dosya: getiri +%1", abs(g2.iloc[0] - 0.01) < 1e-9, g2.tolist())
kontrol("geçmiş yoksa birikimli transfer 0", cb.transfer_kumulatif(f, os.path.join(d, "yok.csv")) == 0.0)
class Bozuk:
    class client:
        @staticmethod
        def futures_income_history(**k): raise RuntimeError("ağ yok")
kontrol("API hatası: son bilinen değer korunur", cb.transfer_kumulatif(Bozuk(), yol) == -600.0)
cb._TRANSFER_KUM[0] = -600.0; y3 = os.path.join(d, "y3.csv"); cb._bakiye_yaz(y3, 1500.0, 1.0)
kontrol("_bakiye_yaz 4. sütunu yazar", open(y3).read().strip().split(",")[3] == "-600.0000")
cb._TRANSFER_KUM[0] = None
print(f"\nSONUÇ: {_h} hata"); sys.exit(1 if _h else 0)
