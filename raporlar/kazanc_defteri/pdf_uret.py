import pandas as pd, numpy as np, math
# Seriler: t1 = şu anki bot (ZSR15P67), t2 = 2. aday (BRP80_CAP_A43), bot = eski bot (T60 öncesi, referans)
import os
UZUN = os.environ.get("PDF_PROFIL", "") == "uzun"     # 6 yıllık defter: t1=T1, t2=T4, sr=T3, bot=merdivensiz T60
D = pd.read_pickle("../gunluk_uzun.pkl" if UZUN else "../gunluk.pkl")
ILK_YIL = int(D.index[0].year)
BAS = 2000.0
S = [("t1", "Şu anki bot", "l-t1", "sw-t1"), ("t2", "2. aday (T2)", "l-t2", "sw-t2"), ("sr", "Short ara dengeli", "l-sr", "sw-sr"), ("bot", "Eski bot", "l-eski", "sw-eski")]
for c, *_ in S:
    D[c + "_b"] = BAS * (1 + D[c]).cumprod()
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
AYK = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
GUNLER = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]

def yuzde(x, d=2):
    return f"{x*100:+.{d}f}".replace(".", ",").replace("-", "−") + "%"
def para(x):
    return f"{x:,.0f}".replace(",", ".") + " $"
def sinif(x):
    return "pos" if x > 0.0005 else "neg" if x < -0.0005 else "flat"
def dd(s): e = (1 + s).cumprod(); return ((e / e.cummax()) - 1).min()
cagr = lambda s: (1 + s).prod() ** (365.25 / len(s)) - 1
sharpe = lambda s: s.mean() / s.std() * math.sqrt(365.25)
def lej(): return "".join(f'<i class="sw {sw}"></i>{ad} ' for _, ad, _, sw in S)

def egri_svg(w=680, h=240):
    pad_l, pad_r, pad_t, pad_b = 54, 14, 12, 26
    ys = np.log10(np.r_[tuple(D[c + "_b"].values for c, *_ in S)])
    lo, hi = math.floor(ys.min() * 2) / 2, math.ceil(ys.max() * 2) / 2
    n = len(D)
    X = lambda i: pad_l + (w - pad_l - pad_r) * i / (n - 1)
    Y = lambda v: pad_t + (h - pad_t - pad_b) * (1 - (math.log10(v) - lo) / (hi - lo))
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart">']
    for t in [2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000, 1000000]:
        if lo <= math.log10(t) <= hi:
            y = Y(t)
            out.append(f'<line x1="{pad_l}" x2="{w-pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
            out.append(f'<text x="{pad_l-6}" y="{y+3:.1f}" class="ax" text-anchor="end">{para(t)}</text>')
    for yr in range(2023, 2027):
        x = X(D.index.searchsorted(pd.Timestamp(f"{yr}-01-01")))
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{pad_t}" y2="{h-pad_b}" class="grid"/>')
        out.append(f'<text x="{x:.1f}" y="{h-8}" class="ax" text-anchor="middle">{yr}</text>')
    for c, _, cls, _ in reversed(S):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(D[c + "_b"].values) if i % 2 == 0 or i == n - 1)
        out.append(f'<polyline points="{pts}" class="{cls}"/>')
        out.append(f'<circle cx="{X(n-1):.1f}" cy="{Y(D[c+"_b"].iloc[-1]):.1f}" r="3" class="d-{cls[2:]}"/>')
    out.append("</svg>")
    return "".join(out)

def bar_svg(M, w=680, h=120):
    pad_l, pad_r, pad_t, pad_b = 40, 8, 10, 18
    v = M.t1.values * 100; e = M.t2.values * 100
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
    out.append(f'<polyline points="{pts}" class="l-t2-ince"/>')
    for i, d in enumerate(M.index):
        if d.day in (1, 5, 10, 15, 20, 25) or i == n - 1:
            out.append(f'<text x="{pad_l + i*bw + bw/2:.1f}" y="{h-5}" class="ax" text-anchor="middle">{d.day}</text>')
    out.append("</svg>")
    return "".join(out)

def ay_tablo(M):
    rows = []
    for d, r in M.iterrows():
        rows.append(f'<tr class="{"hs" if d.weekday() >= 5 else ""}"><td class="dt">{d.day:02d}.{d.month:02d}.{d.year}</td><td class="gn">{GUNLER[d.weekday()]}</td>'
                    f'<td class="{sinif(r.t1)} num strong">{yuzde(r.t1)}</td><td class="num">{para(r.t1_b)}</td>'
                    f'<td class="{sinif(r.t2)} num strong">{yuzde(r.t2)}</td><td class="num">{para(r.t2_b)}</td>'
                    f'<td class="{sinif(r.sr)} num">{yuzde(r.sr)}</td><td class="num muted">{para(r.sr_b)}</td></tr>')
    return ('<table class="gunluk"><thead><tr><th>Tarih</th><th>Gün</th><th>Şu anki bot</th><th>Bakiye</th>'
            '<th>2. aday T2</th><th>T2 bakiye</th><th>Short ara dengeli</th><th>SAD bakiye</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")

def donem_getiri(Y_, c):
    ilk = D.index.get_loc(Y_.index[0]); onc = D.iloc[ilk - 1] if ilk > 0 else None
    b0 = onc[c + "_b"] if onc is not None else BAS
    return Y_[c + "_b"].iloc[-1] / b0 - 1

ay_say, sayfalar = [], []
for p in sorted(set(D.index.to_period("M"))):
    M = D[D.index.to_period("M") == p]
    g = {c: donem_getiri(M, c) for c, *_ in S}
    ay_say.append((p, g))
    eniyi, enkotu = M.t1.idxmax(), M.t1.idxmin()
    sayfalar.append(f'''
<section class="sayfa ay">
  <header class="ay-bas">
    <div><div class="ust">Günlük defter</div><h2>{AYLAR[p.month-1]} {p.year}</h2></div>
    <div class="kpi-sira">
      <div class="kpi"><span>Şu anki bot</span><b class="{sinif(g["t1"])}">{yuzde(g["t1"],1)}</b></div>
      <div class="kpi"><span>2. aday T2</span><b class="{sinif(g["t2"])}">{yuzde(g["t2"],1)}</b></div>
      <div class="kpi"><span>Short ara dengeli</span><b class="{sinif(g["sr"])}">{yuzde(g["sr"],1)}</b></div>
      <div class="kpi"><span>Ay sonu (şu anki)</span><b>{para(M.t1_b.iloc[-1])}</b></div>
    </div>
  </header>
  <div class="notlar"><span>Şu anki bot · en iyi <b>{eniyi.day} {AYK[eniyi.month-1]}</b> {yuzde(M.t1.max())} · en kötü <b>{enkotu.day} {AYK[enkotu.month-1]}</b> {yuzde(M.t1.min())} · kayıp gün <b>{int((M.t1<0).sum())}/{len(M)}</b> · T2 en kötü {yuzde(M.t2.min())}</span>
  <span class="lej"><i class="sw sw-t1"></i>Şu anki bot <i class="sw sw-t2"></i>T2</span></div>
  {bar_svg(M)}
  {ay_tablo(M)}
</section>''')

yil_rows = []
for y in sorted(set(D.index.year)):
    Y_ = D[D.index.year == y]
    et = f"{y}" + (f" <small>{D.index[0].day} {AYK[D.index[0].month-1]}–Ara</small>" if y == ILK_YIL else " <small>Oca–Eyl</small>" if y == 2026 else "")
    g = {c: donem_getiri(Y_, c) for c, *_ in S}
    yil_rows.append(f'<tr><td class="yl">{et}</td><td class="num {sinif(g["t1"])} strong">{yuzde(g["t1"],0)}</td><td class="num">{para(Y_.t1_b.iloc[-1])}</td>'
                    f'<td class="num {sinif(g["t2"])} strong">{yuzde(g["t2"],0)}</td><td class="num">{para(Y_.t2_b.iloc[-1])}</td>'
                    f'<td class="num {sinif(g["sr"])} strong">{yuzde(g["sr"],0)}</td><td class="num {sinif(g["bot"])}">{yuzde(g["bot"],0)}</td>'
                    f'<td class="num neg">{yuzde(Y_.t1.min())}</td><td class="num neg">{yuzde(Y_.t2.min())}</td></tr>')

def isi(col, baslik):
    h = [f'<table class="isi"><caption>{baslik}</caption><thead><tr><th></th>' + "".join(f"<th>{a}</th>" for a in AYK) + "<th>Yıl</th></tr></thead><tbody>"]
    for y in sorted(set(D.index.year)):
        h.append(f"<tr><th>{y}</th>")
        for m in range(1, 13):
            g = next((g for p, g in ay_say if p.year == y and p.month == m), None)
            if g is None:
                h.append('<td class="bos"></td>'); continue
            v = g[col]; a = min(1, abs(v) / 0.30)
            h.append(f'<td class="{"hp" if v >= 0 else "hn"}" style="--a:{0.12 + 0.78*a:.2f}">{yuzde(v,1).replace("%","")}</td>')
        h.append(f'<td class="yt">{yuzde(donem_getiri(D[D.index.year == y], col),0).replace("%","")}</td></tr>')
    h.append("</tbody></table>")
    return "".join(h)

def ozet_satir(c, ad):
    s = D[c]
    return (f'<tr><td class="yl">{ad}</td><td class="num">{yuzde(cagr(s),0)}</td><td class="num">{sharpe(s):.2f}'.replace(".", ",")
            + f'</td><td class="num neg">{yuzde(dd(s),1)}</td><td class="num neg">{yuzde(s.min())}</td>'
            f'<td class="num">{int((s < -0.05).sum())}</td><td class="num">{int((s < -0.03).sum())}</td><td class="num">{para(D[c+"_b"].iloc[-1])}</td></tr>')

kapak = f'''
<section class="sayfa kapak">
  <div class="ust">binance-carry-bot · backtest defteri</div>
  <h1>Kazanç Defteri</h1>
  <p class="alt">20 Temmuz 2022 – 30 Eylül 2026 · {len(D)} gün · 2.000 $ başlangıç, kâr her gün yeniden yatırılır</p>
  <div class="kpi-buyuk">
    <div class="k-t1"><span>Şu anki bot · 30 Eylül 2026</span><b>{para(D.t1_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.t1),0)} · en kötü düşüş {yuzde(dd(D.t1),1)}</em></div>
    <div class="k-t2"><span>2. aday T2</span><b>{para(D.t2_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.t2),0)} · en kötü düşüş {yuzde(dd(D.t2),1)}</em></div>
    <div class="k-sr"><span>Short ara dengeli</span><b>{para(D.sr_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.sr),0)} · en kötü düşüş {yuzde(dd(D.sr),1)}</em></div>
    <div class="k-eski"><span>Eski bot (referans)</span><b>{para(D.bot_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.bot),0)} · en kötü düşüş {yuzde(dd(D.bot),1)}</em></div>
  </div>
  <h3>Bakiye (logaritmik ölçek)</h3>
  <div class="lej">{lej()}</div>
  {egri_svg()}
  <h3>Yıl yıl</h3>
  <table class="yillik"><thead><tr><th>Yıl</th><th>Şu anki bot</th><th>Yıl sonu</th><th>2. aday T2</th><th>T2 yıl sonu</th><th>Short ara dengeli</th><th>Eski bot</th><th>En kötü gün</th><th>T2 en kötü gün</th></tr></thead>
  <tbody>{"".join(yil_rows)}</tbody></table>
  <p class="dipnot">Kaynak: binance-carry-bot backtest motoru (g33.py), gerçekçi ağırlık kayması modeli, 2.000 $ seviyesi (D8 evreni), iki dilim hizasının ortalaması.
  Şu anki bot = canlı varsayılan (T60 + 24 saatlik düşüş stop'u + iki taraflı merdiven; madde 469). 2. aday T2 = şu anki bot + merdiven payı 0,80 + short coin tavanı %8 + 4 long / 3 short
  (madde 485–487; komşulukta plato, protokolde kanıt sınırda — canlıda değil). Short ara dengeli = şu anki bot + short tarafı her gün yeniden seçilir,
  long'lar 5 günde bir (madde 493–495; 2025–26 rejimine bağlı: 2022–24'te etkisi ~0, protokol RED — canlıda değil; canlı gibi giriş ve 5 bp maliyetle yıllık fark +83'e iner). Eski bot = T60 öncesi ayarlar.
  Bunlar geçmiş verinin simülasyonudur, canlı hesabın gerçek sonucu değildir ve gelecek için garanti vermez. Büyük bakiyelerde likidite nedeniyle bileşik büyüme gerçekte bu kadar sürmez.</p>
</section>
<section class="sayfa">
  <div class="ust">Karşılaştırma</div>
  <h2>Şu anki bot ve adaylar</h2>
  <p class="alt">Aynı dönem, aynı başlangıç. T2'nin farkı getiriden çok kötü günlerde.</p>
  <table class="yillik"><thead><tr><th>Ayar</th><th>Yıllık ort.</th><th>Sharpe</th><th>En kötü düşüş</th><th>En kötü gün</th><th>−%5'ten kötü gün</th><th>−%3'ten kötü gün</th><th>30.09.2026 bakiye</th></tr></thead>
  <tbody>{ozet_satir("t1", "Şu anki bot")}{ozet_satir("t2", "2. aday T2")}{ozet_satir("sr", "Short ara dengeli")}{ozet_satir("bot", "Eski bot")}</tbody></table>
  <h3>Ay ay getiri</h3>
  <p class="alt">Her hücre o ayın getirisi (%). Yeşil kazanç, kırmızı kayıp; renk ne kadar koyuysa ay o kadar güçlü.</p>
  {isi("t1", "Şu anki bot")}
  {isi("t2", "2. aday T2")}
</section>
<section class="sayfa">
  <div class="ust">Ay ay getiri</div>
  <h2>Short ara dengeli · eski bot</h2>
  {isi("sr", "Short ara dengeli (şu anki bot + short her gün yeniden seçilir)")}
  {isi("bot", "Eski bot (referans)")}
</section>'''

css = open("stil.css").read()
html_ = f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Kazanç Defteri</title><style>{css}</style></head><body>{kapak}{"".join(sayfalar)}</body></html>'
if True:   # madde 528: iki defter de düzeltilmiş seriyle (t1=şu anki bot, t2=T4, sr=T4 merdivensiz, bot=merdivensiz T60)
    for a, b in [("2. aday (T2)", "T4 (aday)"), ("2. aday T2", "T4 (aday)"), ("2, aday T2", "T4 (aday)"), ("T2 yıl sonu", "T4 yıl sonu"), ("T2 en kötü gün", "T4 en kötü gün"),
                 ("T2 bakiye", "T4 bakiye"), ("T2 en kötü", "T4 en kötü"), ("Short ara dengeli · eski bot", "T4 merdivensiz · merdivensiz T60"),
                 ("Short ara dengeli (şu anki bot + short her gün yeniden seçilir)", "T4 merdivensiz (T4 − iki taraflı merdiven)"),
                 ("Short ara dengeli", "T4 merdivensiz"), ("SAD bakiye", "T4M bakiye"), ("Eski bot (referans)", "Merdivensiz T60 (referans)"),
                 ("Eski bot", "Merdivensiz T60"), ("20 Temmuz 2022", "19 Temmuz 2020" if UZUN else "20 Temmuz 2022"), ("T2'nin farkı getiriden çok kötü günlerde.", "Kaldıraçsız (1,0x)."),
                 ("<i class=\"sw sw-t2\"></i>T2", "<i class=\"sw sw-t2\"></i>T4")]:
        html_ = html_.replace(a, b)
    i = html_.index('<p class="dipnot">'); j = html_.index("</p>", i)
    html_ = html_[:i] + ('<p class="dipnot">Kaynak: binance-carry-bot backtest motoru (g33.py), UZUN ZEMİN (2020-01 verisi), ölçüm ' + ('19.07.2020' if UZUN else '20.07.2022') + ' – 30.09.2026, DÜZELTİLMİŞ DOLUM KURALI '
        '(madde 527: aynı barda kademe + son TP vurursa kademe payı kademe fiyatından dolar; önceki defterdeki merdivenli rakamlar iyimserdi), '
        'gerçekçi ağırlık kayması, 2.000 $ seviyesi (D8 evreni), iki dilim hizasının ortalaması, KALDIRAÇSIZ (1,0x). Kalabalık (long/short) oranı 2021-12 '
        'öncesi yok → o dönemde seçim funding sırasıyla (tüm serilerde aynı). Şu anki bot = canlı varsayılan (T60 + 24 sa stop + iki taraflı merdiven). '
         'T4 = şu anki bot + short 2 g\'de bir + short coin tavanı %8 + merdiven payı 0,80 + evren tabanı 30 (demo hesapta, madde 523). '
        'T4 merdivensiz = T4 − iki taraflı merdiven (merdiven düzeltilmiş modelde kâr değil kötü-gün savunması, madde 528). Merdivensiz T60 = merdivenden önceki canlı ayar. Bunlar geçmiş verinin simülasyonudur, canlı hesabın gerçek '
        'sonucu değildir ve gelecek için garanti vermez. Büyük bakiyelerde likidite nedeniyle bileşik büyüme gerçekte bu kadar sürmez.') + html_[j:]
open("defter.html", "w").write(html_)
print("sayfa", 3 + len(sayfalar))
