#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MADDE 656 testleri: önerilen ayarın otomatik çözümlenmesi (bakiye eşikleri, açık değerlerin korunması, kapatma, preflight)."""
import os, subprocess, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_hata = 0
def kontrol(ad, ok, ek=""):
    global _hata
    print(("  OK  " if ok else "  XX  ") + ad + (f"  [{ek}]" if ek and not ok else ""))
    _hata += 0 if ok else 1

import onerilen as O
print("1) eşikler (madde 596 / 629)")
kontrol("2.000 $ -> T7K 1,15", O.sec(2000) == ("T7K", "1.15"))
kontrol("3.499 $ -> T7K 1,15", O.sec(3499) == ("T7K", "1.15"))
kontrol("3.500 $ -> T7K 1,10", O.sec(3500) == ("T7K", "1.10"))
kontrol("12.499 $ -> T7K 1,10", O.sec(12499) == ("T7K", "1.10"))
kontrol("12.500 $ -> T6 1,10", O.sec(12500) == ("T6", "1.10"))
kontrol("bakiye yok -> T7K 1,0 (kaldıraçsız)", O.sec(None) == ("T7K", "1.0"))

def temiz(**ek):
    for k in [k for k in os.environ if k.startswith("CARRY_") or k == O._ISARET]: os.environ.pop(k)
    os.environ.update(ek)

print("2) gerekli()")
temiz(); kontrol("profil boş -> çözülür", O.gerekli())
temiz(CARRY_PROFIL="ONERILEN"); kontrol("ONERILEN -> çözülür", O.gerekli())
temiz(CARRY_PROFIL="T4"); kontrol("açık T4 -> dokunulmaz", not O.gerekli())
temiz(CARRY_ONERILEN="0"); kontrol("CARRY_ONERILEN=0 -> kapalı", not O.gerekli())
temiz(**{O._ISARET: "1"}); kontrol("yeniden başlatmadan sonra tekrar çözülmez (döngü yok)", not O.gerekli())

print("3) cozumle()")
k = tempfile.mkdtemp(); open(os.path.join(k, "carry_prim_tohum.csv"), "w").write("x\n")
temiz(); o = O.cozumle(lambda: 2000.0, kok=k)
kontrol("2.000 $: T7K / 1.15 / onay / KS 0.03", (os.environ["CARRY_PROFIL"], os.environ["CARRY_GROSS"], os.environ["CARRY_DOZ_ONAY"],
        os.environ["CARRY_LONG_24S_PIYASA"]) == ("T7K", "1.15", "1.15", "0.03"))
kontrol("T7K: prim tohumu kopyalandı", os.path.exists(os.path.join(k, "carry_prim.csv")))
temiz(); O.cozumle(lambda: 50000.0, kok=k)
kontrol("50.000 $: T6 1.10 + onay", (os.environ["CARRY_PROFIL"], os.environ["CARRY_GROSS"], os.environ["CARRY_DOZ_ONAY"]) == ("T6", "1.10", "1.10"))
temiz(CARRY_GROSS="1.0"); O.cozumle(lambda: 2000.0, kok=k)
kontrol("açık CARRY_GROSS=1.0 korunur", os.environ["CARRY_GROSS"] == "1.0" and "CARRY_DOZ_ONAY" not in os.environ)
temiz(CARRY_LONG_24S_PIYASA="0.05"); O.cozumle(lambda: 2000.0, kok=k)
kontrol("açık koşullu stop 0.05 korunur", os.environ["CARRY_LONG_24S_PIYASA"] == "0.05")
temiz(); O.cozumle(lambda: (_ for _ in ()).throw(RuntimeError("ağ yok")), kok=k)
kontrol("bakiye okuma hatası -> T7K 1.0, onay yok", os.environ["CARRY_PROFIL"] == "T7K" and os.environ["CARRY_GROSS"] == "1.0"
        and "CARRY_DOZ_ONAY" not in os.environ)
shutil.rmtree(k)

print("4) preflight uçtan uca (alt süreç, --yerel: bakiye yok -> T7K 1,0 + KS)")
e = {kk: v for kk, v in os.environ.items() if not kk.startswith("CARRY_") and kk != O._ISARET}
r = subprocess.run([sys.executable, "carry_preflight.py", "--yerel"], capture_output=True, text=True, env=e,
                   cwd=os.path.dirname(os.path.abspath(__file__)))
kontrol("ÖNERİLEN satırı basıldı", "ÖNERİLEN AYAR (madde 656)" in r.stdout, r.stdout[-300:])
kontrol("profil T7K ve 0 HATA", "T7K (kullanıcı kararı" in r.stdout and "0 HATA" in r.stdout, r.stdout[-400:])
e2 = dict(e, CARRY_PROFIL="T4")
r = subprocess.run([sys.executable, "carry_preflight.py", "--yerel"], capture_output=True, text=True, env=e2,
                   cwd=os.path.dirname(os.path.abspath(__file__)))
kontrol("açık T4: çözümleme yok, T4 kalır", "ÖNERİLEN AYAR" not in r.stdout and "0 HATA" in r.stdout, r.stdout[-300:])

print("5) carry_bot.main(): bakiye 2.000 $ -> T7K 1,15 ile yeniden başlatma isteği")
kod = ("import sys, os, carry_bot as cb, onerilen as O\n"
       "class F:\n    mode='demo'\n    def __init__(s,*a,**k): pass\n"
       "cb.ExchangeClient = F; cb.sermaye_oku = lambda c: 2000.0\n"
       "def yb():\n    print('YB', os.environ['CARRY_PROFIL'], os.environ['CARRY_GROSS'], os.environ['CARRY_DOZ_ONAY'], os.environ['CARRY_LONG_24S_PIYASA']); sys.exit(0)\n"
       "O.yeniden_baslat = yb\nsys.argv=['carry_bot.py','--dry-run','--once']\ncb.main()\n")
r = subprocess.run([sys.executable, "-c", kod], capture_output=True, text=True, env=e, cwd=os.path.dirname(os.path.abspath(__file__)))
subprocess.run(["git", "checkout", "-q", "carry_bot.log"], cwd=os.path.dirname(os.path.abspath(__file__)))   # main() log dosyasına yazar
kontrol("main: YB T7K 1.15 1.15 0.03", "YB T7K 1.15 1.15 0.03" in r.stdout, (r.stdout + r.stderr)[-400:])
p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "carry_prim.csv")
if os.path.exists(p) and not os.path.exists(p + ".koru"): os.remove(p)   # alt süreç tohumdan kopyalamış olabilir (test artığı)
print(f"\nSONUÇ: {_hata} hata"); sys.exit(1 if _hata else 0)
