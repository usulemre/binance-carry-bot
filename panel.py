# -*- coding: utf-8 -*-
"""MADDE 671 — PANEL: tarayıcıdan izleme (SALT OKUNUR). Bot'a / Binance'e hiçbir emir göndermez, API anahtarı YÜKLEMEZ.

Okuduğu dosyalar (her kurulum: /opt/carry, /opt/carry-*/): defter/gunluk.jsonl (günlük defter: kitap, getiri, funding,
pozisyonlar), carry_bot.log (önemli olaylar: stop, delist, sağlık, hata, başlama), servis durumu (systemctl).
GÜVENLİK: varsayılan 127.0.0.1'e bağlanır = İNTERNETTEN ERİŞİLEMEZ. Telefondan / bilgisayardan Tailscale ile açılır:
    sudo tailscale serve --bg 8050          -> https://<sunucu-adı>.<tailnet>.ts.net  (yalnız sizin cihazlarınız)
İsteğe bağlı ek şifre: .env'de CARRY_PANEL_SIFRE=... (kullanıcı adı: carry). Kurulum KURULUM_SUNUCU.md "Panel".
Elle:      .venv/bin/python panel.py                     (http://127.0.0.1:8050)
Anlık görüntü (tek HTML dosyası, sunucusuz):  .venv/bin/python panel.py --disa-aktar panel.html [--klasor DİZİN ...]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import hmac
import json
import os
import re
import subprocess
import sys

OLAY_DESENLERI = [
    ("stop", re.compile(r"(24 SA DÜŞÜŞ STOP'U|KOŞULLU 24 SA STOP: \S+ .*kapatılıyor)")),
    ("delist", re.compile(r"DELİST: \S+ (listeden çıkıyor|kapanmalı)")),
    ("saglik", re.compile(r"SAĞLIK KAPISI KAPALI")),
    ("hata", re.compile(r"tur başarısız|KAPATILAMADI")),
    ("ayar", re.compile(r"önerilen ayar etkin|ÖNERİLEN AYAR: kitap")),
    ("basla", re.compile(r"carry_bot başladı")),
]
_ZAMAN = re.compile(r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}):\d{2}(?:[,.]\d+)?\s*(?:\[?(?:INFO|WARNING|ERROR|CRITICAL|DEBUG)\]?)?")
_GIZLI = re.compile(r"(api[_-]?key|secret|signature|token)\S*", re.I)


def kurulumlar(kok: str = "/opt") -> list[str]:
    out = [os.path.join(kok, "carry")] if os.path.exists(os.path.join(kok, "carry", "carry_bot.py")) else []
    out += [d for d in sorted(glob.glob(os.path.join(kok, "carry-*"))) if os.path.exists(os.path.join(d, "carry_bot.py"))]
    return out


def _env(klasor: str) -> dict:
    d = {}
    try:
        for l in open(os.path.join(klasor, ".env"), encoding="utf-8"):
            l = l.strip()
            if l and not l.startswith("#") and "=" in l:
                k, v = l.split("=", 1)
                if k.strip() in ("BINANCE_MODE", "CARRY_PROFIL", "CARRY_BILDIRIM_AD", "CARRY_SERMAYE_OLCEK"):   # anahtarlar OKUNMAZ
                    d[k.strip()] = v.split("#")[0].strip()
    except OSError:
        pass
    return d


def defter_oku(klasor: str) -> list[dict]:
    yol = os.path.join(klasor, "defter", "gunluk.jsonl")
    out = []
    try:
        for l in open(yol, encoding="utf-8"):
            l = l.strip()
            if l:
                try:
                    out.append(json.loads(l))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def olaylar(klasor: str, en_cok: int = 40, son_bayt: int = 2_000_000) -> list[dict]:
    yol = os.path.join(klasor, "carry_bot.log")
    try:
        with open(yol, "rb") as f:
            f.seek(0, 2); n = f.tell(); f.seek(max(0, n - son_bayt))
            satirlar = f.read().decode("utf-8", "replace").splitlines()
    except OSError:
        return []
    out = []
    for s in satirlar:
        for tur, d in OLAY_DESENLERI:
            if d.search(s):
                m = _ZAMAN.match(s)
                metin = s[m.end():].strip(" -|") if m else s
                out.append({"zaman": m.group(1) if m else "", "tur": tur, "metin": _GIZLI.sub("***", metin)[:300]})
                break
    return out[-en_cok:][::-1]


def servis_durumu(klasor: str) -> str:
    b = os.path.basename(klasor.rstrip("/"))
    sv = "carry" if b == "carry" else "carry@" + b[len("carry-"):]
    try:
        return subprocess.run(["systemctl", "is-active", sv], capture_output=True, text=True, timeout=5).stdout.strip() or "?"
    except Exception:
        return "?"


def ozet(defter: list[dict]) -> dict:
    """Seri + göstergeler. Getiri zinciri günlük getiriden (transferler zaten ayıklanmış)."""
    seri, deg = [], 1.0
    for k in defter:
        g = k.get("gun_getiri")
        if g is not None:
            deg *= 1 + g
        seri.append({"tarih": k.get("tarih"), "kitap": k.get("kitap", k.get("ozkaynak")), "gun": g, "deger": deg,
                     "funding": (k.get("gelir_24s") or {}).get("FUNDING_FEE", 0),
                     "komisyon": (k.get("gelir_24s") or {}).get("COMMISSION", 0)})
    zirve, dd = 1.0, 0.0
    for s in seri:
        zirve = max(zirve, s["deger"]); dd = min(dd, s["deger"] / zirve - 1)

    def _pencere(n):
        if len(seri) < 2:
            return None
        b = seri[max(0, len(seri) - 1 - n)]["deger"]
        return seri[-1]["deger"] / b - 1
    aylik = {}
    for s in seri:
        if s["gun"] is not None:
            a = s["tarih"][:7]; aylik[a] = (1 + aylik.get(a, 0.0)) * (1 + s["gun"]) - 1
    son = defter[-1] if defter else {}
    return {"seri": seri, "toplam": seri[-1]["deger"] - 1 if seri else None, "dd": dd, "g7": _pencere(7), "g30": _pencere(30),
            "bugun": seri[-1]["gun"] if seri else None, "kitap": seri[-1]["kitap"] if seri else None,
            "aylik": aylik, "pozisyonlar": son.get("pozisyonlar", {}), "son_tarih": son.get("tarih"),
            "profil": son.get("profil"), "doz": son.get("doz"),
            "funding_top": sum(s["funding"] or 0 for s in seri), "komisyon_top": sum(s["komisyon"] or 0 for s in seri)}


def veri(klasorler: list[str], servis: bool = True) -> dict:
    out = []
    for kl in klasorler:
        e = _env(kl); b = os.path.basename(kl.rstrip("/"))
        ad = e.get("CARRY_BILDIRIM_AD") or (b[len("carry-"):] if b.startswith("carry-") else "ana")
        o = ozet(defter_oku(kl))
        o.update({"ad": ad, "mod": e.get("BINANCE_MODE", "demo"), "servis": servis_durumu(kl) if servis else "—",
                  "olaylar": olaylar(kl)})
        out.append(o)
    return {"kurulumlar": out, "uretim": dt.datetime.now().strftime("%Y-%m-%d %H:%M")}


SAYFA = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Carry Panel</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
:root{--bg:#f6f7f9;--kart:#fff;--yazi:#16181d;--soluk:#6b7280;--cizgi:#e5e7eb;--art:#0f9d58;--eks:#d93025;--vurgu:#2563eb;--uyari:#b45309}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f1115;--kart:#171a21;--yazi:#e8eaed;--soluk:#9aa0a6;--cizgi:#2a2f3a;--art:#34c172;--eks:#f2685c;--vurgu:#6ea8fe;--uyari:#f0a44b}}
:root[data-theme="dark"]{--bg:#0f1115;--kart:#171a21;--yazi:#e8eaed;--soluk:#9aa0a6;--cizgi:#2a2f3a;--art:#34c172;--eks:#f2685c;--vurgu:#6ea8fe;--uyari:#f0a44b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--yazi);font:14px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
.kap{max-width:1180px;margin:0 auto;padding:16px}
header{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;justify-content:space-between;margin-bottom:12px}
h1{font-size:18px;margin:0}.k{color:var(--soluk);font-size:12px}
.sekme{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px}.sekme button{border:1px solid var(--cizgi);background:var(--kart);color:var(--yazi);
padding:6px 12px;border-radius:999px;cursor:pointer;font:inherit}.sekme button.on{border-color:var(--vurgu);color:var(--vurgu);font-weight:600}
.izgara{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}
.kart{background:var(--kart);border:1px solid var(--cizgi);border-radius:12px;padding:12px 14px}
.kart .e{color:var(--soluk);font-size:12px}.kart .d{font-size:22px;font-weight:650;font-variant-numeric:tabular-nums;margin-top:2px}
.art{color:var(--art)}.eks{color:var(--eks)}
.iki{display:grid;grid-template-columns:2fr 1fr;gap:12px;margin-bottom:12px}@media(max-width:820px){.iki{grid-template-columns:1fr}}
.kart h2{font-size:13px;margin:0 0 8px;color:var(--soluk);font-weight:600}
.grafik{position:relative;height:260px}
table{width:100%;border-collapse:collapse;font-variant-numeric:tabular-nums}td,th{padding:4px 6px;border-bottom:1px solid var(--cizgi);text-align:right;font-size:13px}
th{color:var(--soluk);font-weight:500}td.l,th.l{text-align:left}.tablo{overflow-x:auto}
.olay{display:flex;gap:8px;align-items:flex-start;padding:6px 0;border-bottom:1px solid var(--cizgi);font-size:13px}.olay .z{color:var(--soluk);white-space:nowrap;font-size:12px}
.rozet{flex:none;margin-top:1px;display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;font-weight:600;border:1px solid currentColor;white-space:nowrap}
.r-stop,.r-hata{color:var(--eks)}.r-delist,.r-saglik{color:var(--uyari)}.r-ayar,.r-basla{color:var(--vurgu)}
.durum{font-size:12px;padding:2px 8px;border-radius:999px;border:1px solid var(--cizgi)}.durum.ok{color:var(--art);border-color:var(--art)}.durum.yok{color:var(--eks);border-color:var(--eks)}
.bos{color:var(--soluk);padding:20px 0;text-align:center}
</style></head><body><div class="kap">
<header><div><h1>Carry Panel</h1><div class="k" id="alt"></div></div><div class="k">salt okunur · emir göndermez</div></header>
<div class="sekme" id="sekme"></div><div id="icerik"></div></div>
<script>
const VERI_GOMULU = /*VERI*/null;
const $ = s => document.querySelector(s);
const yz = (v, d=2) => v==null ? "—" : (v>=0?"+":"") + (v*100).toFixed(d) + "%";
const para = v => v==null ? "—" : v.toLocaleString("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2}) + " $";
const sinif = v => v==null ? "" : (v>=0 ? "art" : "eks");
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
let VERI, secili = 0, grafikler = [];
function ciz(){
  const K = VERI.kurulumlar; $("#alt").textContent = "güncellendi " + VERI.uretim;
  $("#sekme").innerHTML = K.map((k,i)=>`<button class="${i==secili?'on':''}" onclick="secili=${i};ciz()">${k.ad} · ${k.mod}</button>`).join("");
  const k = K[secili]; if(!k){ $("#icerik").innerHTML = "<div class='kart bos'>Henüz kurulum / defter yok.</div>"; return; }
  const sv = k.servis; const svc = sv=="active" ? "ok" : (sv=="—"||sv=="?" ? "" : "yok");
  const P = Object.entries(k.pozisyonlar||{}); const L = P.filter(p=>p[1].yon=="L").sort((a,b)=>b[1].usd-a[1].usd), S = P.filter(p=>p[1].yon=="S").sort((a,b)=>b[1].usd-a[1].usd);
  const sat = (p) => p ? `<td class="l">${p[0].replace("USDT","")}</td><td>${para(p[1].usd)}</td><td class="${p[1].kar_yuzde==null?'':sinif(p[1].kar_yuzde)}">${p[1].kar_yuzde==null?"—":(p[1].kar_yuzde>=0?"+":"")+p[1].kar_yuzde.toFixed(1)+"%"}</td>` : "<td></td><td></td><td></td>";
  let poz = ""; for(let i=0;i<Math.max(L.length,S.length);i++) poz += `<tr>${sat(L[i])}${sat(S[i])}</tr>`;
  const ay = Object.entries(k.aylik||{}).sort((a,b)=>b[0].localeCompare(a[0]));
  $("#icerik").innerHTML = `
  <div class="izgara">
    <div class="kart"><div class="e">Kitap ${svc?`<span class="durum ${svc}">${sv=="active"?"çalışıyor":sv}</span>`:""}</div><div class="d">${para(k.kitap)}</div></div>
    <div class="kart"><div class="e">Son gün (${k.son_tarih||"—"})</div><div class="d ${sinif(k.bugun)}">${yz(k.bugun)}</div></div>
    <div class="kart"><div class="e">Son 7 gün</div><div class="d ${sinif(k.g7)}">${yz(k.g7,1)}</div></div>
    <div class="kart"><div class="e">Son 30 gün</div><div class="d ${sinif(k.g30)}">${yz(k.g30,1)}</div></div>
    <div class="kart"><div class="e">Başlangıçtan</div><div class="d ${sinif(k.toplam)}">${yz(k.toplam,1)}</div></div>
    <div class="kart"><div class="e">En büyük düşüş</div><div class="d eks">${yz(k.dd,1)}</div></div>
  </div>
  <div class="iki">
    <div class="kart"><h2>Kitap ($) · ayar ${k.profil||"—"} ${k.doz||""}x</h2><div class="grafik"><canvas id="g1"></canvas></div></div>
    <div class="kart"><h2>Aylık getiri</h2><div class="tablo"><table><tr><th class="l">Ay</th><th>Getiri</th></tr>
      ${ay.map(a=>`<tr><td class="l">${a[0]}</td><td class="${sinif(a[1])}">${yz(a[1],1)}</td></tr>`).join("") || "<tr><td class='l bos' colspan=2>—</td></tr>"}</table></div>
      ${(k.funding_top||k.komisyon_top)?`<div class="k" style="margin-top:8px">Toplam funding ${para(k.funding_top)} · komisyon ${para(k.komisyon_top)}</div>`:""}</div>
  </div>
  <div class="kart" style="margin-bottom:12px"><h2>Günlük getiri</h2><div class="grafik" style="height:180px"><canvas id="g2"></canvas></div></div>
  <div class="iki">
    <div class="kart"><h2>Pozisyonlar (${L.length} long / ${S.length} short)</h2><div class="tablo"><table>
      <tr><th class="l">Long</th><th>$</th><th>kâr</th><th class="l">Short</th><th>$</th><th>kâr</th></tr>${poz || "<tr><td colspan=6 class='bos'>açık pozisyon yok</td></tr>"}</table></div></div>
    <div class="kart"><h2>Olaylar</h2>${(k.olaylar||[]).map(o=>`<div class="olay"><span class="rozet r-${o.tur}">${o.tur}</span><div><div>${o.metin.replace(/</g,"&lt;")}</div><div class="z">${o.zaman}</div></div></div>`).join("") || "<div class='bos'>olay yok</div>"}</div>
  </div>`;
  grafikler.forEach(g=>g.destroy()); grafikler = [];
  if (!window.Chart) return;
  const x = k.seri.map(s=>s.tarih), izg = css("--cizgi"), sol = css("--soluk");
  const ortak = {responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{display:false}},
    scales:{x:{ticks:{color:sol,maxTicksLimit:innerWidth<600?4:8,maxRotation:0,autoSkip:true},grid:{display:false}},y:{ticks:{color:sol},grid:{color:izg}}}};
  grafikler.push(new Chart($("#g1"),{type:"line",data:{labels:x,datasets:[{data:k.seri.map(s=>s.kitap),borderColor:css("--vurgu"),borderWidth:2,pointRadius:0,fill:false,tension:.15}]},
    options:{...ortak,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>para(c.parsed.y)}}}}}));
  grafikler.push(new Chart($("#g2"),{type:"bar",data:{labels:x,datasets:[{data:k.seri.map(s=>s.gun==null?null:s.gun*100),
    backgroundColor:k.seri.map(s=>(s.gun||0)>=0?css("--art"):css("--eks"))}]},
    options:{...ortak,plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>(c.parsed.y>=0?"+":"")+c.parsed.y.toFixed(2)+"%"}}},
      scales:{...ortak.scales,y:{ticks:{color:sol,callback:v=>v+"%"},grid:{color:izg}}}}}));
}
async function yukle(){
  if (VERI_GOMULU){ VERI = VERI_GOMULU; ciz(); return; }
  try { const r = await fetch("api/veri", {cache:"no-store"}); VERI = await r.json(); ciz(); } catch(e){ $("#alt").textContent = "veri alınamadı"; }
}
yukle(); if(!VERI_GOMULU) setInterval(yukle, 60000);
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", ()=>VERI && ciz());
</script></body></html>"""


def statik_html(v: dict) -> str:
    return SAYFA.replace("/*VERI*/null", json.dumps(v, ensure_ascii=False).replace("</", "<\\/"))


def uygulama(klasorler: list[str]):
    from flask import Flask, Response, jsonify, request
    app = Flask(__name__)
    sifre = os.getenv("CARRY_PANEL_SIFRE", "")

    @app.before_request
    def _kimlik():
        if sifre:
            a = request.authorization
            if not a or a.username != "carry" or not hmac.compare_digest(a.password or "", sifre):
                return Response("şifre gerekli", 401, {"WWW-Authenticate": 'Basic realm="carry"'})

    @app.after_request
    def _basliklar(r):
        r.headers["X-Frame-Options"] = "DENY"
        r.headers["X-Content-Type-Options"] = "nosniff"
        r.headers["Referrer-Policy"] = "no-referrer"
        r.headers["Cache-Control"] = "no-store"
        r.headers["Content-Security-Policy"] = ("default-src 'none'; script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
                                                "style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:")
        return r

    @app.get("/")
    def ana():
        return Response(SAYFA, mimetype="text/html")

    @app.get("/api/veri")
    def api():
        return jsonify(veri(klasorler))

    return app


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--klasor", action="append", help="kurulum klasörü (varsayılan: /opt/carry ve /opt/carry-*)")
    ap.add_argument("--host", default=os.getenv("CARRY_PANEL_HOST", "127.0.0.1"))
    ap.add_argument("--port", type=int, default=int(os.getenv("CARRY_PANEL_PORT", "8050")))
    ap.add_argument("--disa-aktar", metavar="HTML", help="tek dosyalık anlık görüntü yaz ve çık")
    a = ap.parse_args(argv)
    klasorler = a.klasor or kurulumlar() or [os.path.dirname(os.path.abspath(__file__))]
    if a.disa_aktar:
        open(a.disa_aktar, "w", encoding="utf-8").write(statik_html(veri(klasorler)))
        print(f"panel: {a.disa_aktar}")
        return 0
    if a.host not in ("127.0.0.1", "localhost", "::1") and not os.getenv("CARRY_PANEL_SIFRE"):
        print("!! panel dış arayüze açılıyor ama CARRY_PANEL_SIFRE yok — reddedildi (127.0.0.1 + tailscale serve kullanın)")
        return 2
    from waitress import serve
    print(f"panel: http://{a.host}:{a.port}  (salt okunur)")
    serve(uygulama(klasorler), host=a.host, port=a.port, threads=4)
    return 0


if __name__ == "__main__":
    sys.exit(main())
