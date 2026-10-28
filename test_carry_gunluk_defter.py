import os, sys, json, time, shutil
sys.path.insert(0, "/home/claude/binance-carry-bot")
import carry_gunluk_defter as G
class Ic:
    def __init__(s, gel): s.gel = gel
    def futures_income_history(s, startTime, endTime, limit): return [g for g in s.gel if startTime <= g["time"] <= endTime]
class Sahte:
    def __init__(s, oz, poz, gel): s.oz, s.poz, s.client = oz, poz, Ic(gel)
    def get_account_equity_usd(s): return s.oz
    def get_open_positions(s): return s.poz
os.chdir(__import__("tempfile").mkdtemp())
T0 = 1793836800  # 2026-11-01 00:00 UTC
hata = []
for ad, olcek, ozler in (("A", "1.0", [2000, 2040, 2020]), ("B", "0.2", [10000, 10080, 10040])):
    k = os.path.abspath(ad); shutil.rmtree(k, ignore_errors=True); os.makedirs(k)
    open(os.path.join(k, ".env"), "w").write(f"CARRY_PROFIL={'T7K' if ad=='B' else 'T4'}\nCARRY_GROSS={'1.15' if ad=='B' else '1.0'}\nCARRY_LONG_24S_PIYASA={'0.03' if ad=='B' else '0'}\n")
    os.environ["CARRY_SERMAYE_OLCEK"] = olcek
    for gun, oz in enumerate(ozler):
        t = T0 + gun * 86400 + 300
        poz = [{"symbol": "AAAUSDT", "positionAmt": "10", "entryPrice": "1.0", "markPrice": str(1 + 0.05 * gun), "unRealizedProfit": "0.5"}]
        if gun < 2: poz.append({"symbol": "BBBUSDT", "positionAmt": "-5", "entryPrice": "2.0", "markPrice": "1.9", "unRealizedProfit": "0.5"})
        else: poz.append({"symbol": "CCCUSDT", "positionAmt": "-3", "entryPrice": "3.0", "markPrice": "3.1", "unRealizedProfit": "-0.3"})
        gel = [{"incomeType": "FUNDING_FEE", "income": "1.5", "symbol": "BBBUSDT", "time": (t - 3600) * 1000},
               {"incomeType": "COMMISSION", "income": "-0.2", "symbol": "AAAUSDT", "time": (t - 7200) * 1000}]
        cwd = os.getcwd(); os.chdir(k)
        r = G.topla(Sahte(oz, poz, gel), simdi=t); G.topla(Sahte(oz, poz, gel), simdi=t + 60)   # aynı gün iki kez
        os.chdir(cwd)
    sat = [json.loads(l) for l in open(os.path.join(k, "defter", "gunluk.jsonl"))]
    if len(sat) != 3: hata.append(f"{ad}: satır {len(sat)} != 3")
    beklenen = (ozler[1] - ozler[0]) / (ozler[0] * float(olcek))
    if abs(sat[1]["gun_getiri"] - beklenen) > 1e-9: hata.append(f"{ad}: getiri {sat[1]['gun_getiri']} != {beklenen}")
    if sat[2]["degisim"]["acilan"] != ["CCCUSDT S"] or sat[2]["degisim"]["kapanan"] != ["BBBUSDT S"]: hata.append(f"{ad}: değişim {sat[2]['degisim']}")
    if abs(sat[1]["gelir_24s"]["FUNDING_FEE"] - 1.5) > 1e-9: hata.append(f"{ad}: funding")
G.rapor([os.path.abspath("A"), os.path.abspath("B")], "rapor.html", pdf=True)
h = open("rapor.html").read()
for x in ("T4", "T7K 1,15x + koşullu stop", "CCCUSDT", "+2,00%", "+4,00%"):
    if x not in h: hata.append(f"raporda yok: {x}")
print("HATA:", hata if hata else "yok")
