"""Paralel indirici: 8 is parcacigi, sadece ana kitabin filtresini gecen
239 sembol. Rate limit icin is parcacigi basina 0.15s bekleme."""
import json, urllib.request, time, os, threading, queue
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
DIZ = "/tmp/gate"
BAS = int(time.mktime(time.strptime("2022-01-01", "%Y-%m-%d")))
ortak = json.load(open(f"{DIZ}/ortak.json"))
hedef = [s for s in json.load(open(f"{DIZ}/hedef.json"))
         if not os.path.exists(f"{DIZ}/{s}.csv")]
print(f"{len(hedef)} sembol indirilecek", flush=True)
q = queue.Queue()
for s in hedef: q.put(s)
kilit = threading.Lock(); sayac = [0]

def al(u, deneme=4):
    for i in range(deneme):
        try:
            r = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(r, timeout=30) as resp:
                return json.loads(resp.read())
        except Exception:
            if i == deneme - 1: raise
            time.sleep(1.0 + i)

def isci():
    while True:
        try: s = q.get_nowait()
        except queue.Empty: return
        satir = []; t = None
        try:
            for _ in range(130):
                u = ("https://api.gateio.ws/api/v4/futures/usdt/funding_rate"
                     f"?contract={ortak[s]}&limit=1000")
                if t: u += f"&to={t}"
                d = al(u)
                if not d: break
                satir.extend((x["t"], x["r"]) for x in d)
                t = d[-1]["t"]
                if t < BAS: break
                time.sleep(0.15)
        except Exception as e:
            with kilit: print(f"  {s}: {type(e).__name__} ({len(satir)})", flush=True)
        if len(satir) >= 50:
            satir = sorted(set(satir))
            with open(f"{DIZ}/{s}.csv", "w") as f:
                f.write("t,r\n")
                for a, b in satir: f.write(f"{a},{b}\n")
        with kilit:
            sayac[0] += 1
            if sayac[0] % 20 == 0:
                print(f"  {sayac[0]}/{len(hedef)} bitti", flush=True)
        q.task_done()

ip = [threading.Thread(target=isci, daemon=True) for _ in range(8)]
for x in ip: x.start()
for x in ip: x.join()
print("BITTI", flush=True)
