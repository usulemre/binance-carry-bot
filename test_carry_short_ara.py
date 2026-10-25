"""Short ara dengelemesi ve short coin tavanı (madde 500-502) birim testleri.

T60 profilinde (eski varsayılan T1) ikisi de KAPALI; testler düğmeleri modül düzeyinde açar.
Madde 534'ten beri kod varsayılanı T4; bu yüzden modül T60 profiliyle yüklenir.
"""
import os
import sys
os.environ["CARRY_PROFIL"] = "T60"
sys.path.insert(0, '.')
import carry_bot as cb

basarisiz = []


def kontrol(ad, kosul, detay=""):
    if kosul:
        print(f"  [OK]   {ad}")
    else:
        print(f"  [HATA] {ad}  {detay}")
        basarisiz.append(ad)


print("1) T60 profilinde kapalı")
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

print("6a) evren tabanı (madde 508)")
class _C:
    class client:
        @staticmethod
        def futures_ticker():
            return [{"symbol": f"C{i}USDT", "quoteVolume": str(v), "priceChangePercent": "0"}
                    for i, v in enumerate([9e7, 8e7, 5e7, 4e7, 3e7, 1e7])]
cb.sembol_bilgisi = lambda c: {}; cb.listeleme_yaslari = lambda c, b=None: {}
_mv, _ms = cb.MIN_DAILY_VOLUME_USD, cb.MIN_LEGS
cb.MIN_DAILY_VOLUME_USD = 7e7
kontrol("kapalıyken yalnız eşik üstü (2)", cb.evren_sec(_C) == ["C0USDT", "C1USDT"], cb.evren_sec(_C))
cb.EVREN_MIN = 4
kontrol("N=4: hacim sırasıyla 4'e tamamlandı", cb.evren_sec(_C) == ["C0USDT", "C1USDT", "C2USDT", "C3USDT"], cb.evren_sec(_C))
cb.EVREN_MIN = 10
kontrol("N=10: 20M tabanın altı (1e7) girmez", "C5USDT" not in cb.evren_sec(_C) and len(cb.evren_sec(_C)) == 5)
cb.EVREN_MIN = 2
kontrol("eşik yeterliyse evren değişmez", cb.evren_sec(_C) == ["C0USDT", "C1USDT"])
cb.EVREN_MIN = 0; cb.MIN_DAILY_VOLUME_USD = _mv

print("6) preflight profilleri (alt süreç, temiz ortam)")
import os, subprocess
def _pf(env):
    kod = ("import carry_preflight as p; p.kontrol_ayarlar(); "
           "print('HATA_SAYISI', sum(1 for a,d,m in p._satirlar if d=='HATA'))")
    e = {k: v for k, v in os.environ.items() if not k.startswith("CARRY_")}; e.update(env)
    o = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True, env=e).stdout
    return int(o.split("HATA_SAYISI")[-1].strip() or -1)
kontrol("profilsiz = T4 (madde 534): HATA yok", _pf({}) == 0)
kontrol("T60 açıkça: HATA yok", _pf({"CARRY_PROFIL": "T60"}) == 0)
kontrol("T3 tam ayarla: HATA yok", _pf({"CARRY_PROFIL": "T3", "CARRY_SHORT_ARA_SAAT": "48", "CARRY_SHORT_TAVAN": "0.08",
                                        "CARRY_MERDIVEN_PAY": "0.80"}) == 0)
kontrol("T3 ayarsız: HATA", _pf({"CARRY_PROFIL": "T3"}) > 0)
kontrol("T60 + T3 düğmesi açık: HATA", _pf({"CARRY_PROFIL": "T60", "CARRY_SHORT_ARA_SAAT": "48"}) > 0)
kontrol("T4: yalnız CARRY_PROFIL=T4 yeterli (varsayılanlar profilden)", _pf({"CARRY_PROFIL": "T4"}) == 0)
kontrol("T4 ama evren tabanı elle 0: HATA", _pf({"CARRY_PROFIL": "T4", "CARRY_EVREN_MIN": "0"}) > 0)
_k = ("import carry_bot as cb; print('V', cb.SHORT_ARA_SAAT, cb.SHORT_TAVAN, cb.MERDIVEN_PAY, cb.EVREN_MIN)")
_e = {k: v for k, v in os.environ.items() if not k.startswith("CARRY_")}; _e["CARRY_PROFIL"] = "T4"
_o = subprocess.run([sys.executable, "-c", _k], capture_output=True, text=True, env=_e).stdout.split("V")[-1].split()
kontrol("T4 profil değerleri 48 / 0,08 / 0,80 / 30", _o == ["48.0", "0.08", "0.8", "30"], _o)
_e.pop("CARRY_PROFIL")
_o = subprocess.run([sys.executable, "-c", _k], capture_output=True, text=True, env=_e).stdout.split("V")[-1].split()
kontrol("profilsiz varsayılan = T4 değerleri (madde 534)", _o == ["48.0", "0.08", "0.8", "30"], _o)
_e["CARRY_PROFIL"] = "T60"
_o = subprocess.run([sys.executable, "-c", _k], capture_output=True, text=True, env=_e).stdout.split("V")[-1].split()
kontrol("CARRY_PROFIL=T60 = eski T1 değerleri 0 / 0 / 0,667 / 0", _o == ["0.0", "0.0", "0.667", "0"], _o)
print()
if basarisiz:
    print(f"BAŞARISIZ: {len(basarisiz)} -> {basarisiz}"); sys.exit(1)
print("TÜM TESTLER GEÇTİ")
