import pandas as pd, numpy as np, math, html
D = pd.read_pickle("../gunluk.pkl")
BAS = 2000.0; KAL = 1.25
D["t60k"] = D.t60 * KAL
for c in ("bot", "t60", "t60k"):
    D[c + "_b"] = BAS * (1 + D[c]).cumprod()
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
AYK = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

def yuzde(x, d=2):
    s = f"{x*100:+.{d}f}".replace(".", ",").replace("-", "−")
    return s + "%"
def para(x):
    return f"{x:,.0f}".replace(",", ".") + " $"
def sinif(x):
    return "pos" if x > 0.0005 else "neg" if x < -0.0005 else "flat"

def egri_svg(w=680, h=230):
    pad_l, pad_r, pad_t, pad_b = 54, 14, 12, 26
    ys = np.log10(np.r_[D.bot_b.values, D.t60_b.values])
    lo, hi = math.floor(ys.min() * 2) / 2, math.ceil(ys.max() * 2) / 2
    n = len(D)
    X = lambda i: pad_l + (w - pad_l - pad_r) * i / (n - 1)
    Y = lambda v: pad_t + (h - pad_t - pad_b) * (1 - (math.log10(v) - lo) / (hi - lo))
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart">']
    for t in [2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000]:
        if lo <= math.log10(t) <= hi:
            y = Y(t)
            out.append(f'<line x1="{pad_l}" x2="{w-pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
            out.append(f'<text x="{pad_l-6}" y="{y+3:.1f}" class="ax" text-anchor="end">{para(t)}</text>')
    for yr in range(2023, 2027):
        i = D.index.searchsorted(pd.Timestamp(f"{yr}-01-01"))
        x = X(i)
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{pad_t}" y2="{h-pad_b}" class="grid"/>')
        out.append(f'<text x="{x:.1f}" y="{h-8}" class="ax" text-anchor="middle">{yr}</text>')
    for col, cls in (("bot_b", "l-eski"), ("t60_b", "l-t60")):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(D[col].values) if i % 2 == 0 or i == n - 1)
        out.append(f'<polyline points="{pts}" class="{cls}"/>')
    out.append(f'<circle cx="{X(n-1):.1f}" cy="{Y(D.t60_b.iloc[-1]):.1f}" r="3.2" class="d-t60"/>')
    out.append(f'<circle cx="{X(n-1):.1f}" cy="{Y(D.bot_b.iloc[-1]):.1f}" r="3.2" class="d-eski"/>')
    out.append("</svg>")
    return "".join(out)

def bar_svg(M, w=680, h=120):
    pad_l, pad_r, pad_t, pad_b = 40, 8, 10, 18
    v = M.t60.values * 100; e = M.bot.values * 100
    m = max(2.0, math.ceil(max(abs(v).max(), abs(e).max())))
    n = len(v); bw = (w - pad_l - pad_r) / n
    Y = lambda x: pad_t + (h - pad_t - pad_b) * (m - x) / (2 * m)
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart">']
    for t in (-m, -m / 2, 0, m / 2, m):
        out.append(f'<line x1="{pad_l}" x2="{w-pad_r}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="{"zero" if t == 0 else "grid"}"/>')
        out.append(f'<text x="{pad_l-5}" y="{Y(t)+3:.1f}" class="ax" text-anchor="end">{t:+.0f}%</text>'.replace("+0%", "0%").replace("-", "−"))
    for i, x in enumerate(v):
        x0 = pad_l + i * bw + bw * 0.18
        y0, y1 = sorted((Y(0), Y(x)))
        out.append(f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{bw*0.64:.1f}" height="{max(0.6, y1-y0):.1f}" class="{"b-pos" if x >= 0 else "b-neg"}"/>')
    pts = " ".join(f"{pad_l + i*bw + bw/2:.1f},{Y(x):.1f}" for i, x in enumerate(e))
    out.append(f'<polyline points="{pts}" class="l-eski-ince"/>')
    for i, d in enumerate(M.index):
        if d.day in (1, 5, 10, 15, 20, 25) or i == n - 1:
            out.append(f'<text x="{pad_l + i*bw + bw/2:.1f}" y="{h-5}" class="ax" text-anchor="middle">{d.day}</text>')
    out.append("</svg>")
    return "".join(out)

def ay_tablo(M, onceki):
    rows = []
    for d, r in M.iterrows():
        rows.append(f'<tr class="{"hs" if d.weekday() >= 5 else ""}"><td class="dt">{d.day:02d}.{d.month:02d}.{d.year}</td><td class="gn">{GUNLER[d.weekday()]}</td>'
                    f'<td class="{sinif(r.t60)} num strong">{yuzde(r.t60)}</td><td class="num">{para(r.t60_b)}</td>'
                    f'<td class="{sinif(r.t60k)} num">{yuzde(r.t60k)}</td><td class="num muted">{para(r.t60k_b)}</td>'
                    f'<td class="{sinif(r.bot)} num">{yuzde(r.bot)}</td><td class="num muted">{para(r.bot_b)}</td></tr>')
    return ('<table class="gunluk"><thead><tr><th>Tarih</th><th>Gün</th><th>T60</th><th>T60 bakiye</th>'
            f'<th>T60 {str(KAL).replace(".", ",")}x</th><th>{str(KAL).replace(".", ",")}x bakiye</th><th>Eski bot</th><th>Eski bakiye</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")

ay_say = []
sayfalar = []
for p in sorted(set(D.index.to_period("M"))):
    M = D[D.index.to_period("M") == p]
    ilk = D.index.get_loc(M.index[0])
    onc = D.iloc[ilk - 1] if ilk > 0 else None
    def ayg(c):
        b0 = onc[c + "_b"] if onc is not None else BAS
        return M[c + "_b"].iloc[-1] / b0 - 1
    g = {c: ayg(c) for c in ("t60", "t60k", "bot")}
    ay_say.append((p, g))
    eniyi, enkotu = M.t60.idxmax(), M.t60.idxmin()
    kayip = int((M.t60 < 0).sum())
    sayfalar.append(f'''
<section class="sayfa ay">
  <header class="ay-bas">
    <div><div class="ust">Günlük defter</div><h2>{AYLAR[p.month-1]} {p.year}</h2></div>
    <div class="kpi-sira">
      <div class="kpi"><span>T60</span><b class="{sinif(g["t60"])}">{yuzde(g["t60"],1)}</b></div>
      <div class="kpi"><span>T60 {str(KAL).replace(".", ",")}x</span><b class="{sinif(g["t60k"])}">{yuzde(g["t60k"],1)}</b></div>
      <div class="kpi"><span>Eski bot</span><b class="{sinif(g["bot"])}">{yuzde(g["bot"],1)}</b></div>
      <div class="kpi"><span>Ay sonu T60</span><b>{para(M.t60_b.iloc[-1])}</b></div>
    </div>
  </header>
  <div class="notlar">En iyi gün <b>{eniyi.day} {AYK[eniyi.month-1]}</b> {yuzde(M.t60.max())} · en kötü gün <b>{enkotu.day} {AYK[enkotu.month-1]}</b> {yuzde(M.t60.min())} · kayıp gün <b>{kayip}/{len(M)}</b>
  <span class="lej"><i class="sw sw-t60"></i>T60 günlük % <i class="sw sw-eski"></i>Eski bot</span></div>
  {bar_svg(M)}
  {ay_tablo(M, onc)}
</section>''')

# yıllık
yil_rows = []
for y in sorted(set(D.index.year)):
    Y_ = D[D.index.year == y]
    ilk = D.index.get_loc(Y_.index[0]); onc = D.iloc[ilk - 1] if ilk > 0 else None
    def yg(c):
        b0 = onc[c + "_b"] if onc is not None else BAS
        return Y_[c + "_b"].iloc[-1] / b0 - 1
    et = f"{y}" + (" <small>20 Tem–Ara</small>" if y == 2022 else " <small>Oca–Eyl</small>" if y == 2026 else "")
    yil_rows.append(f'<tr><td class="yl">{et}</td><td class="num {sinif(yg("t60"))} strong">{yuzde(yg("t60"),0)}</td><td class="num">{para(Y_.t60_b.iloc[-1])}</td>'
                    f'<td class="num {sinif(yg("t60k"))}">{yuzde(yg("t60k"),0)}</td><td class="num {sinif(yg("bot"))}">{yuzde(yg("bot"),0)}</td>'
                    f'<td class="num muted">{para(Y_.bot_b.iloc[-1])}</td><td class="num neg">{yuzde(Y_.t60.min())}</td><td class="num">{int((Y_.t60<0).sum())}/{len(Y_)}</td></tr>')
def dd(s): e = (1 + s).cumprod(); return ((e / e.cummax()) - 1).min()
cagr = lambda s: (1 + s).prod() ** (365.25 / len(s)) - 1

# aylık ısı haritası
def isi(col, baslik):
    yillar = sorted(set(D.index.year))
    h = [f'<table class="isi"><caption>{baslik}</caption><thead><tr><th></th>' + "".join(f"<th>{a}</th>" for a in AYK) + "<th>Yıl</th></tr></thead><tbody>"]
    for y in yillar:
        h.append(f"<tr><th>{y}</th>")
        for m in range(1, 13):
            g = next((g for p, g in ay_say if p.year == y and p.month == m), None)
            if g is None:
                h.append('<td class="bos"></td>'); continue
            v = g[col]; a = min(1, abs(v) / 0.30)
            h.append(f'<td class="{"hp" if v >= 0 else "hn"}" style="--a:{0.12 + 0.78*a:.2f}">{yuzde(v,1).replace("%","")}</td>')
        Y_ = D[D.index.year == y]; ilk = D.index.get_loc(Y_.index[0]); onc = D.iloc[ilk-1] if ilk > 0 else None
        b0 = onc[col + "_b"] if onc is not None else BAS
        h.append(f'<td class="yt">{yuzde(Y_[col+"_b"].iloc[-1]/b0-1,0).replace("%","")}</td></tr>')
    h.append("</tbody></table>")
    return "".join(h)

kapak = f'''
<section class="sayfa kapak">
  <div class="ust">binance-carry-bot · backtest defteri</div>
  <h1>Kazanç Defteri</h1>
  <p class="alt">20 Temmuz 2022 – 30 Eylül 2026 · {len(D)} gün · 2.000 $ başlangıç, kâr her gün yeniden yatırılır</p>
  <div class="kpi-buyuk">
    <div><span>T60 · 30 Eylül 2026</span><b>{para(D.t60_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.t60),0)} · en kötü düşüş {yuzde(dd(D.t60),1)}</em></div>
    <div><span>T60 {str(KAL).replace(".", ",")}x</span><b>{para(D.t60k_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.t60k),0)} · en kötü düşüş {yuzde(dd(D.t60k),1)}</em></div>
    <div><span>Eski bot</span><b>{para(D.bot_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.bot),0)} · en kötü düşüş {yuzde(dd(D.bot),1)}</em></div>
  </div>
  <h3>Bakiye (logaritmik ölçek)</h3>
  <div class="lej"><i class="sw sw-t60"></i>T60 <i class="sw sw-eski"></i>Eski bot</div>
  {egri_svg()}
  <h3>Yıl yıl</h3>
  <table class="yillik"><thead><tr><th>Yıl</th><th>T60</th><th>T60 yıl sonu</th><th>T60 {str(KAL).replace(".", ",")}x</th><th>Eski bot</th><th>Eski yıl sonu</th><th>T60 en kötü gün</th><th>T60 kayıp gün</th></tr></thead>
  <tbody>{"".join(yil_rows)}</tbody></table>
  <p class="dipnot">Kaynak: binance-carry-bot backtest motoru (g33.py), gerçekçi ağırlık kayması modeli, 2.000 $ seviyesi (D8 evreni), iki dilim hizasının ortalaması.
  T60 = botun yeni varsayılan ayarı (madde 442); Eski bot = T60 öncesi ayarlar (hacim 100M, yaş 90, kâr al 0,40). {str(KAL).replace(".", ",")}x sütunu günlük getiri × kaldıraçtır; teminat maliyeti ve likidasyon dahil değildir.
  Bunlar geçmiş verinin simülasyonudur, canlı hesabın gerçek sonucu değildir ve gelecek için garanti vermez. Büyük bakiyelerde likidite nedeniyle bileşik büyüme gerçekte bu kadar sürmez.</p>
</section>
<section class="sayfa">
  <div class="ust">Ay ay getiri</div>
  <h2>Aylık tablo</h2>
  <p class="alt">Her hücre o ayın getirisi (%). Yeşil kazanç, kırmızı kayıp; renk ne kadar koyuysa ay o kadar güçlü.</p>
  {isi("t60", "T60")}
  {isi("t60k", f"T60 {str(KAL).replace('.', ',')}x")}
  {isi("bot", "Eski bot")}
</section>'''

css = open("stil.css").read()
html_ = f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Kazanç Defteri</title><style>{css}</style></head><body>{kapak}{"".join(sayfalar)}</body></html>'
open("defter.html", "w").write(html_)
print("sayfa", 2 + len(sayfalar))
