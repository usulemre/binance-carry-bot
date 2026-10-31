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


PAKET_DIR = os.getenv("CARRY_PAKET_DIR", "/opt/carry-rapor/paket")
_PAKET_AD = re.compile(r"^paket_\d{4}-\d{2}\.zip$")


def paketler(dizin: str | None = None) -> list[dict]:
    """MADDE 674: sunucunun aylık indirdiği veri paketleri (araştırma için; panelden indirilip sohbete yüklenir)."""
    dizin = dizin or PAKET_DIR
    try:
        adlar = sorted((f for f in os.listdir(dizin) if _PAKET_AD.match(f)), reverse=True)
    except OSError:
        return []
    return [{"ad": f, "mb": round(os.path.getsize(os.path.join(dizin, f)) / 1e6, 1)} for f in adlar]


def veri(klasorler: list[str], servis: bool = True) -> dict:
    out = []
    for kl in klasorler:
        e = _env(kl); b = os.path.basename(kl.rstrip("/"))
        ad = e.get("CARRY_BILDIRIM_AD") or (b[len("carry-"):] if b.startswith("carry-") else "ana")
        o = ozet(defter_oku(kl))
        o.update({"ad": ad, "mod": e.get("BINANCE_MODE", "demo"), "servis": servis_durumu(kl) if servis else "—",
                  "olaylar": olaylar(kl)})
        out.append(o)
    return {"kurulumlar": out, "paketler": paketler(), "uretim": dt.datetime.now().strftime("%Y-%m-%d %H:%M")}


SAYFA = r"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Carry Panel</title>
<link rel="manifest" href="manifest.webmanifest"><meta name="theme-color" content="#0f1115">
<link rel="icon" href="ikon-192.png"><link rel="apple-touch-icon" href="ikon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-title" content="Carry">
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
  </div>
  ${(VERI.paketler||[]).length && !VERI_GOMULU ? `<div class="kart"><h2>Aylık veri paketleri (araştırma: indirip sohbete yükleyin)</h2>${VERI.paketler.map(p=>`<div class="olay"><a href="paket/${p.ad}" style="color:var(--vurgu)">${p.ad}</a><span class="z">${p.mb} MB</span></div>`).join("")}</div>` : ""}`;
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
if(!VERI_GOMULU && "serviceWorker" in navigator){ try{ navigator.serviceWorker.register("sw.js"); }catch(e){} }
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", ()=>VERI && ciz());
</script></body></html>"""


SW_JS = """const K="carry-kabuk-v1";
self.addEventListener("install",e=>{e.waitUntil(caches.open(K).then(c=>c.addAll(["./","ikon-192.png","ikon-512.png"])));self.skipWaiting();});
self.addEventListener("activate",e=>{e.waitUntil(caches.keys().then(a=>Promise.all(a.filter(x=>x!==K).map(x=>caches.delete(x)))));self.clients.claim();});
self.addEventListener("fetch",e=>{const u=new URL(e.request.url);
  if(e.request.method!=="GET"||u.pathname.includes("/api/")||u.pathname.includes("/paket/"))return;   // veri ve paket önbelleğe ALINMAZ
  e.respondWith(fetch(e.request).then(r=>{const k=r.clone();caches.open(K).then(c=>c.put(e.request,k));return r;}).catch(()=>caches.match(e.request)));});
"""
IKON_192 = "iVBORw0KGgoAAAANSUhEUgAAAMAAAADACAIAAADdvvtQAAADUElEQVR42u3dsW0UQRTHYYwuRwTIogCaoAoaQBc7pwzyiy0aoAqaoAB0XRBYcnLIXnZmZ9689/0ihJCxuE//2ZWP27t37z+8kfb21j+BABJAAkgASQAJIAEkgCSABJAAEkASQAJIAAkgCSABJIAEkACSABJAAkgASQAJIAEkgCSABJAAEkASQAJIATr5J8jap59fb3/z95cfff+WO5/SWoTOQYwcYeX0bPwzANEzwhBAFfV0NARQUT29DAFUV08XQwDJAgkgzTqDGr8CQLJAAkgAaULny3XuN+Cn8ehYoNp6Pv/53vjVWn44D5DtcYSh4whTi56WU6zxzWUAJdmefYba35roLa2pjq1fH7+N1GOBsl30bN+hXm+LBijbJfMWQx3fVO8uLNvd1uPD/dMv/LceevbrGZYFSkJnih6ADI+LaHrm6bFAji2ADM/UHGH0WCB0LBA9K+qxQK6XATI8jjB6FtVjgRxbABkeRxg9i+oBiB5HWKLWomOBYs3PinosUAg9i9KxQI4tgBafn9X1OMKm6UlAxwI5tgBacH4y6QGIHoAEkPkBiJ6KegASQOYHIHoAkiNM5gcgegASQOanxvwARA9AAsj8AERPRT0ACSDzAxA9AMkRJvMDED2DO+V4dSu/hHNb73FPLwxDR0bmJyegja9r44tKT85roO2v6/lyDfiIdQu0hp7GnTA/CQF1mZMtrzc9Ce/Ceh1Gz1/Ha19lgQ69jrllZH5SARp2FfykgZ5UR9jIeyj3a9lu4yO/ouYnOiB6AHKauAZaRM/zJAyQZ35C34V1+YTl4xjRE3qBen0+98hBUpQFOu7T3XsxMj9BAQ17Lkmdp3cVugsb+VSbx4d7DlIt0NxnIvmpxdqAgjxR69Vvg56IgAI+j+2f3xI9EQFFfprf+XKFJjSgas+CLNIpph503MbTAxA9mniEueixQPRoBiB6AKJHMwDRA1BT/6uBHoD2m6AnQUf9KOPlswwdC7R/XegBaNxFkuoCurVCD0D7DdED0H5D9LgLkwJcRAsgCSABJIAEkACSABJAAkgASQAJIAEkgCSABJAAEkASQAJIAAkgCSABJIAEkACSABJAAkgASQAJIAEkgCSABJAAEkASQAJIAAkg1e0vEmVbz2lwGEEAAAAASUVORK5CYII="
IKON_512 = "iVBORw0KGgoAAAANSUhEUgAAAgAAAAIACAIAAAB7GkOtAAAKQElEQVR42u3dwW1TaxSFUTvy3PLAiiggTVBFGogYM6cM5oxRGkgVNJECEF0wQEIBjENMfH3O2WsNnx685PK0v/+/IbDe7vYrAPJceQQAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACACAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACACAAAAgAAAIAAACAIAAADDFxiMAAt083B3/Fx5v78c/hPV2t/e/AmD0A2MgAIDpD82AAAB2P7QEvggMWP8qP7MbAECPge5+FXADAKx/6FVAAADrH9oAAQCsf2gDBACw/qENEADA+oc2QAAA6x/aAAEArH9oAwQAsP6hDRAAgFACADj+h14CBACw/qENEACAUAIAIAAAHXR5w17/4xQAADcAAMfqpI9WAADcAAAQAAAEAKCKjn/kcuWPWQAA3AAAEAAABAAAAQBAAAAQAIAlvPv0zUMQAMD6IwCA9edUG48AMP1uAACl1//t14/tPovH23sBAHD2r8UrIMD0h3IDAKx/qPV2t/cUgEbT/+XNhy6fVOUvALgBAA7+uQQAaLb+XX4vUPHj/8oXgQEHfzcAAOsvAAC117/+W6D6739WfhcQ0PfgX/a3A7VYfzcAoOv64wYARE9/wUtAl+O/GwDQ++Bf7YsBjdZfAIDG61+tAb3Wf+UVENB3+p+6+LugduvvBgBMWP+L3wM6rr8AABPW/7INaLr+K6+AgAHT/9TC74L6rr8bADBq/Re+B7RefzcAYM70L3kV6D79bgDA2PU/61Vgxvq7AQAz1/8ct4Exu/+Tvw8AmDz9T7f75uHO9LsBAEHr//n99Z//8NkYTB19AQCi158fvAICTH8ovwsIsP5uAACm3w0AwPoLAGD9rf9MXgEBpt8NAMD6CwBg/a3/eF4BAabfDQCw/tbfDQAw/abfDQCw/tZfAADrb/0H8QoITL/pdwMArL/1FwDA+lv/8bwCAtNv+t0AAOtv/d0AANNv+t0AAOtv/QUAsP7WfxCvgMD0m343AMD6W38BAKy/9R/PKyAw/abfDQCw/tbfDQAw/abfDQCw/tZfAADrb/0H8QoITL/pdwMArL/1FwDA+lv/8bwCAtNv+t0AAOtv/d0AANNv+t0AAOtv/QUAsP7WfxCvgMD6m343AADr7wYAOPtbfwEArL/pn8krIMD6uwEAjv+m3w0AsP7WXwAArP9MXgGB47/pdwMArL/1FwAA6z+eV0Dg+G/63QAA62/93QCAQKbfDQBIPP5bfwEArD8pvAKCaKbfDQBIPP5bfwEArD+JvAKCOKYfNwBIPP5bf9wAIG79TT9uAJDI+iMAkHj8t/4c5BUQTF5/048bAAACAI7/IABg/REAAAQAcPxHAADrjwAAIACA4z8CAFh/BAAAAQDHf8d/BACsv/VHAAAQAHD8d/xHAMD6W38EAAABAMd/x38EAKy/9UcAABAAcPx3/EcAwPqDAAAgAOD4DwIA1h8EAAABAMd/BMAjAOuPAAAgAIDjPwIAWH8EAAABAMd/x38EAKy/9UcAABAAcPx3/EcAwPpbfwQAAAEAx3/HfwQArL/1RwAAEABw/AcBAOsPAgCAAIDjPwgAWH8QAAAEABz/QQDA+oMAACAA4PiPAID1t/4IAAACAI7/jv8IAFh/648AACAA4Pjv+I8AgPW3/ggAAAIAjv+O/wgAWH8oZeMRGEELBZnW293eU3D4DYmB4z8IgOlPnC3rD7/xCsj6P/8DTRi4ARB95m2dAcd/EADrn7ho1h8O8grI+p/4M1s3cAMg+sBbPwOO/yAA1j9x7Kw/HOEVkOl/zf+04QM3AILWv+z51/EfBMD6J2bA+sOzvAKy/mf/wGwiuAEQtP6XPRo7/oMAWP/EDFh/+EdeAVn/y3zY5hLcAAha/wVOzY7/IACmPzED1h9exCsg61/o87Kk4AZA0Pq/1oHa8R8EwPonZsD6wwm8ArL+1T9rIwtuANY/2pEMOP6DAFj/xAxYfziZV0DWv+Uzsb/gBmD6cfyHE115BNYf648AYP0BAcD64/iPAGD9sf4IANYfEACsv+M/CADW3/pDR74RzPQDbgBYfxz/EQCsP9YfAcD6AzP5GoD1/+Wcq0+O/+Twh8FZ/0J/xrL1hyV5BWT9rw/+Q/MHbgDErX+jj9/xHwTA9C8xcDkZsP6E8ArI+r/gR1lGcAMgbv1zLgQihwBg/RMzYP2J4hWQ9f/fn9NoghsAces/7EKgZAgA1j8xA9afQF4BWf+z/BftKbgBmH6n2gYXArlCALD+HhQE8QrIqC33IZlacAOw/o60VZ6eJiEAWP/Ex2j9CecVkPW/8AdshcENwPo7zy76bIUHBMD6Jz5k6w8rfyew6S/7GflrKcENwPqnn2Rf/eE7/oMAWP+4XwXTDwJg/RN/Oaw/CID1j/ul8bhAAKz/wF+jI18x9qBAAKw/wAG+E9j6A6F8H4DpB9wArL/1BwTA+lt/QACsv/UHBMD6W39AAKy/9QcEwPpbf0AArL/1B/pI/D4A0w+QeAOw/gCJAbD+AIkBsP4AiQGw/gCJAbD+AIkBsP4AiQGw/gB/M/b7AEw/QOINwPoDJAbA+gMkBsD6A4QGoObOWn9AABLX1voDApC4udYfEIDE5bX+QGUbj8D0A24AVtj6AwKgAdYfEAANsP6AAGiA9QcEQAOsPyAAGmD9AQFIbID1B5ryfQCmH3ADsNrWHxAADbD+gABogPUHBEADrD8gAJkNsP6AACQ2wPoDApDYAOsPzOP7AEw/4AZg5a0/IAAaYP0BAQhtgPUHBCCxAdYfSLDe7vaeAoAbAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAIAAACAIAAACAAAAgAAAIAgAAAIAAACAAAAgCAAAAgAAAC4BEAZPoO2bqU5a7sCg8AAAAASUVORK5CYII="


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
                                                "style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; manifest-src 'self'; worker-src 'self'")
        return r

    # MADDE 680: PWA — telefonda "Ana ekrana ekle" ile uygulama gibi açılır (Tailscale HTTPS adresinde). Önbellek YALNIZ kabuk
    # (sayfa + simgeler); veri (/api/veri) hiçbir zaman önbelleğe alınmaz -> çevrimdışıyken eski rakam gösterilmez.
    @app.get("/manifest.webmanifest")
    def manifest():
        m = {"name": "Carry Panel", "short_name": "Carry", "start_url": "./", "scope": "./", "display": "standalone",
             "background_color": "#0f1115", "theme_color": "#0f1115",
             "icons": [{"src": "ikon-192.png", "sizes": "192x192", "type": "image/png"},
                       {"src": "ikon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}
        return Response(json.dumps(m), mimetype="application/manifest+json")

    @app.get("/ikon-<int:n>.png")
    def ikon(n):
        import base64
        from flask import abort
        if n not in (192, 512):
            abort(404)
        return Response(base64.b64decode(IKON_192 if n == 192 else IKON_512), mimetype="image/png")

    @app.get("/sw.js")
    def sw():
        return Response(SW_JS, mimetype="application/javascript", headers={"Service-Worker-Allowed": "./"})

    @app.get("/")
    def ana():
        return Response(SAYFA, mimetype="text/html")

    @app.get("/api/veri")
    def api():
        return jsonify(veri(klasorler))

    @app.get("/paket/<ad>")
    def paket(ad):
        from flask import abort, send_from_directory
        if not _PAKET_AD.match(ad):          # yalnız paket_YYYY-MM.zip; yol gezintisi yok
            abort(404)
        return send_from_directory(PAKET_DIR, ad, as_attachment=True)

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
