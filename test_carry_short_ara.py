"""Short ara dengelemesi ve short coin tavanı (madde 500-502) birim testleri.

İkisi de varsayılan KAPALI; testler düğmeleri modül düzeyinde açar.
"""
import sys
sys.path.insert(0, '.')
import carry_bot as cb

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad}  {detay}")
        basarisiz.append(ad)


print("1) varsayılanlar kapalı")
kontrol("CARRY_SHORT_ARA_SAAT varsayılan 0", cb.SHORT_ARA_SAAT == 0)
kontrol("CARRY_SHORT_TAVAN varsayılan 0", cb.SHORT_TAVAN == 0)
d = {"dilimler": {"0": {"A": 10, "B": -10}}, "dilim_bakiye": {"0": 1000}}
kontrol("kapalıyken ara dengeleme dokunmaz", cb.short_ara_dengele(d, 6, {"X": -5}, 1000, 1000) == []
        and d["dilimler"]["0"] == {"A": 10, "B": -10})
kontrol("kapalıyken tavan dokunmaz", cb.short_tavan_kirp(d, "0", {"B": -999}, 1000, 1000) == {"B": -999})

print("2) ara dengeleme: 48 sa / (120 sa / 15 dilim) = 6 tur → 6 ve 12 tur önceki dilimler")
cb.SHORT_ARA_SAAT, cb.REBALANCE_HOURS, cb.N_DILIM = 48.0, 120.0, 15
d = {"dilimler": {str(k): {f"L{k}": 10.0, f"S{k}": -10.0} for k in range(15)},
     "dilim_bakiye": {str(k): 1000.0 for k in range(15)}}
yeni = {"LN": 10.0, "SN1": -6.0, "SN2": -4.0}
g = cb.short_ara_dengele(d, 14, yeni, 1000.0, 1000.0)
kontrol("güncellenen dilimler 8 ve 2", sorted(g) == ["2", "8"], g)
kontrol("dilim 8 long korundu, short yenilendi", d["dilimler"]["8"] == {"L8": 10.0, "SN1": -6.0, "SN2": -4.0}, d["dilimler"]["8"])
kontrol("dilim 5 (9 tur önce) dokunulmadı", d["dilimler"]["5"] == {"L5": 10.0, "S5": -10.0})
kontrol("yeni dilimin long'u ara dilime TAŞINMADI", "LN" not in d["dilimler"]["2"])

print("3) ölçek: dilim 2.000 $ ile kurulmuş, bakiye 1.000 $ → saklanan birim = güncel / dilim ölçeği (madde 205, tavanlı)")
d = {"dilimler": {"2": {"L": 20.0, "S": -20.0}}, "dilim_bakiye": {"2": 2000.0}}
cb.short_ara_dengele(d, 8, {"SN": -5.0}, 1000.0, 1000.0)
_o = cb._dilim_olcek(d, "2", 1000.0)
kontrol("SN saklanan = −5 / ölçek", abs(d["dilimler"]["2"]["SN"] + 5.0 / _o) < 1e-9, (d["dilimler"]["2"], _o))
_th = {}
for _k, _h in d["dilimler"].items():
    for _s, _v in _h.items():
        _th[_s] = _th.get(_s, 0) + _v * cb._dilim_olcek(d, _k, 1000.0)
kontrol("güncel USD'de −5 (toplam_hedef ölçeğiyle)", abs(_th["SN"] + 5.0) < 1e-9, _th)

print("4) eski dilimde LONG olan coin short'a çevrilmez")
d = {"dilimler": {"8": {"X": 10.0, "S": -10.0}}, "dilim_bakiye": {"8": 1000.0}}
cb.short_ara_dengele(d, 14, {"X": -5.0, "Y": -5.0}, 1000.0, 1000.0)
kontrol("X long kaldı, Y short girdi", d["dilimler"]["8"] == {"X": 10.0, "Y": -5.0}, d["dilimler"]["8"])

print("5) short tavanı: sermaye 1.000 $, tavan %8 → coin başına toplam short ≤ 80 $")
cb.SHORT_TAVAN = 0.08
d = {"dilimler": {"0": {"A": -50.0}, "1": {"A": -20.0, "B": -10.0}}, "dilim_bakiye": {"0": 1000.0, "1": 1000.0}}
k = cb.short_tavan_kirp(d, "2", {"A": -30.0, "B": -30.0, "L": 40.0}, 1000.0, 1000.0)
kontrol("A: diğerleri 70 → yeni en fazla 10", abs(k["A"] + 10.0) < 1e-9, k)
kontrol("B: diğerleri 10 → yeni 30 serbest", abs(k["B"] + 30.0) < 1e-9, k)
kontrol("long'a dokunulmaz", k["L"] == 40.0)
d["dilimler"]["0"]["A"] = -80.0
k = cb.short_tavan_kirp(d, "2", {"A": -30.0}, 1000.0, 1000.0)
kontrol("tavan dolmuşsa coin dilimden çıkar", "A" not in k, k)

cb.SHORT_ARA_SAAT = 0.0; cb.SHORT_TAVAN = 0.0
print()
if basarisiz:
    print(f"BAŞARISIZ: {len(basarisiz)} -> {basarisiz}"); sys.exit(1)
print("TÜM TESTLER GEÇTİ")
