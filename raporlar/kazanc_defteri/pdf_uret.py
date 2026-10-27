import pandas as pd, numpy as np, math
# Seriler: t1 = şu anki bot (ZSR15P67), t2 = 2. aday (BRP80_CAP_A43), bot = eski bot (T60 öncesi, referans)
import os
UZUN = os.environ.get("PDF_PROFIL", "") == "uzun"     # 6 yıllık defter: t1=T1, t2=T4, sr=T3, bot=merdivensiz T60
SEV = int(os.environ.get("SEVIYE", "2000"))      # madde 630: 2000 (D8) | 1000 (D9)
_ek = "" if SEV == 2000 else f"_{SEV}"
D = pd.read_pickle(f"../gunluk_uzun{_ek}.pkl" if UZUN else f"../gunluk{_ek}.pkl")
# MADDE 534: T4 kod varsayılanı (asıl bot) -> başlık sütunu T4. Pickle'da t1=T1, t2=T4; burada yer değiştirir.
D[["t1", "t2"]] = D[["t2", "t1"]].values
ILK_YIL = int(D.index[0].year)
BAS = float(SEV)
S = [("t1", "Şu anki bot", "l-t1", "sw-t1"), ("t2", "2. aday (T2)", "l-t2", "sw-t2"), ("sr", "Short ara dengeli", "l-sr", "sw-sr"), ("bot", "Eski bot", "l-eski", "sw-eski")]
T6V = "t6" in D.columns      # madde 631: bilgi amaçlı T6 1x + koşullu stop sütunu (küçük bakiyede ölçülmüş doz DEĞİL)
if T6V: S.append(("t6", "§T6§", "l-t6", "sw-t6"))
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

def egri_svg(w=680, h=(200 if "t6" in D.columns else 240)):
    pad_l, pad_r, pad_t, pad_b = 54, 14, 12, 26
    ys = np.log10(np.r_[tuple(D[c + "_b"].values for c, *_ in S)])
    lo, hi = math.floor(ys.min() * 2) / 2, math.ceil(ys.max() * 2) / 2
    n = len(D)
    X = lambda i: pad_l + (w - pad_l - pad_r) * i / (n - 1)
    Y = lambda v: pad_t + (h - pad_t - pad_b) * (1 - (math.log10(v) - lo) / (hi - lo))
    out = [f'<svg viewBox="0 0 {w} {h}" class="chart">']
    for t in [1000, 2000, 5000, 10000, 20000, 50000, 100000, 200000, 500000, 1000000, 2000000, 5000000, 10000000, 20000000]:
        if lo <= math.log10(t) <= hi:
            y = Y(t)
            out.append(f'<line x1="{pad_l}" x2="{w-pad_r}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
            out.append(f'<text x="{pad_l-6}" y="{y+3:.1f}" class="ax" text-anchor="end">{para(t)}</text>')
    for yr in range(ILK_YIL + 1, 2027):
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
                    f'<td class="{sinif(r.sr)} num">{yuzde(r.sr)}</td><td class="num muted">{para(r.sr_b)}</td>'
                    + (f'<td class="{sinif(r.t6)} num">{yuzde(r.t6)}</td>' if T6V else '') + '</tr>')
    return ('<table class="gunluk"><thead><tr><th>Tarih</th><th>Gün</th><th>Şu anki bot</th><th>Bakiye</th>'
            '<th>2. aday T2</th><th>T2 bakiye</th><th>Short ara dengeli</th><th>SAD bakiye</th>' + ('<th>§T6K§</th>' if T6V else '') + '</tr></thead><tbody>'
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
                    + (f'<td class="num {sinif(g["t6"])}">{yuzde(g["t6"],0)}</td>' if T6V else '') +
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
  <p class="alt">20 Temmuz 2022 – 30 Eylül 2026 · {len(D)} gün · §BAS§ başlangıç, kâr her gün yeniden yatırılır</p>
  <div class="kpi-buyuk">
    <div class="k-t1"><span>Şu anki bot · 30 Eylül 2026</span><b>{para(D.t1_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.t1),0)} · en kötü düşüş {yuzde(dd(D.t1),1)}</em></div>
    <div class="k-t2"><span>2. aday T2</span><b>{para(D.t2_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.t2),0)} · en kötü düşüş {yuzde(dd(D.t2),1)}</em></div>
    <div class="k-sr"><span>Short ara dengeli</span><b>{para(D.sr_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.sr),0)} · en kötü düşüş {yuzde(dd(D.sr),1)}</em></div>
    <div class="k-eski"><span>Eski bot (referans)</span><b>{para(D.bot_b.iloc[-1])}</b><em>yıllık ort. {yuzde(cagr(D.bot),0)} · en kötü düşüş {yuzde(dd(D.bot),1)}</em></div>{('<div class="k-t6"><span>§T6§</span><b>' + para(D.t6_b.iloc[-1]) + '</b><em>yıllık ort. ' + yuzde(cagr(D.t6),0) + ' · en kötü düşüş ' + yuzde(dd(D.t6),1) + '</em></div>') if T6V else ''}
  </div>
  <h3>Bakiye (logaritmik ölçek)</h3>
  <div class="lej">{lej()}</div>
  {egri_svg()}
  <h3>Yıl yıl</h3>
  <table class="yillik"><thead><tr><th>Yıl</th><th>Şu anki bot</th><th>Yıl sonu</th><th>2. aday T2</th><th>T2 yıl sonu</th><th>Short ara dengeli</th><th>Eski bot</th>{"<th>§T6K§</th>" if T6V else ""}<th>En kötü gün</th><th>T2 en kötü gün</th></tr></thead>
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
  <tbody>{ozet_satir("t1", "Şu anki bot")}{ozet_satir("t2", "2. aday T2")}{ozet_satir("sr", "Short ara dengeli")}{ozet_satir("bot", "Eski bot")}{ozet_satir("t6", "§T6§") if T6V else ""}</tbody></table>
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
  {isi("t6", "§T6§ — bilgi amaçlı (küçük bakiyede önerilen kitap değil)") if T6V else ""}
</section>'''

css = open("stil.css").read()
html_ = f'<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Kazanç Defteri</title><style>{css}</style></head><body>{kapak}{"".join(sayfalar)}</body></html>'
if True:   # madde 612/624: görünen t1 = T4 (asıl bot), t2 = T7K 1,15x + koşullu stop, sr = T7K 1,15x eski stop, bot = eski bot T1 — hepsi GERÇEKÇİ model
    for a, b in [("Şu anki bot ve adaylar", "Asıl bot T4 ve adaylar"), ("2. aday (T2)", "§T7§"), ("2. aday T2", "§T7§"), ("2, aday T2", "§T7§"),
                 ("T2 yıl sonu", "T7K+KS yıl sonu"), ("T2 en kötü gün", "T7K+KS en kötü gün"),
                 ("T2 bakiye", "T7K+KS bakiye"), ("T2 en kötü", "T7K+KS en kötü"), ("Short ara dengeli · eski bot", "T7K 1,15x (eski stop) · eski bot T1"),
                 ("Short ara dengeli (şu anki bot + short her gün yeniden seçilir)", "T7K 1,15x, eski 24 sa stop (borsada, koşulsuz)"),
                 ("Short ara dengeli", "T7K eski stop"), ("SAD bakiye", "Eski stop bakiye"), ("Eski bot (referans)", "§ES§ (referans)"),
                 ("Eski bot", "§ES§"), ("20 Temmuz 2022", "19 Temmuz 2020" if UZUN else "20 Temmuz 2022"),
                 ("T2'nin farkı getiriden çok kötü günlerde.", "T4 ve eski bot kaldıraçsız (1,0x); T7K 1,15x kaldıraçla — T4 ile AYNI RİSKTE (madde 596). Koşullu stop (KS, madde 621-623): 24 sa stop yalnız piyasa medyanı ≤ −%3 iken, 8 sa'lik bot turunda kapanışla."),
                 ("<i class=\"sw sw-t2\"></i>T2", "<i class=\"sw sw-t2\"></i>T7K+KS")]:
        html_ = html_.replace(a, b)
    html_ = html_.replace("Şu anki bot", "Asıl bot T4").replace("şu anki bot", "asıl bot T4").replace("§T7§", "T7K 1,15x + koşullu stop").replace("§ES§", "Eski bot T1")
    i = html_.index('<p class="dipnot">'); j = html_.index("</p>", i)
    html_ = html_[:i] + ('<p class="dipnot">Kaynak: binance-carry-bot backtest motoru (g33.py), uzun zemin, ölçüm ' + ('19.07.2020' if UZUN else '20.07.2022') + ' – 30.09.2026. '
        'GERÇEKÇİ MODEL (madde 587, 27.10.2026 güncellemesi): canlı gibi tek hesap girişi (Binance entryPrice), işlem başı 5 bp maliyet, düzeltilmiş kademe dolumu '
        '(MERD_SIRA); ' + ('2.000 $ seviyesi (D8 evreni)' if SEV == 2000 else '1.000 $ seviyesi (D9 evreni: D8 + AVAX, madde 349)') + ', iki dilim hizasının ortalaması. '
        'Asıl bot T4 = kod varsayılanı (madde 534). T7K 1,15x + koşullu stop = CARRY_PROFIL=T7K, CARRY_GROSS=1,15, CARRY_LONG_24S_PIYASA=0,03 (madde 596, 621-623); eski stop = aynı kitap, borsada koşulsuz 24 sa stop. '
        'Canlıya geçiş Ekim OOS sonucunu bekliyor (madde 617). '
        'Eski bot T1 = CARRY_PROFIL=T60. '
        'Kalabalık oranı 2021-12 öncesi yok → o dönemde seçim funding sırasıyla. Bunlar geçmiş verinin simülasyonudur, canlı hesabın gerçek '
        'sonucu değildir ve gelecek için garanti vermez. Büyük bakiyelerde likidite nedeniyle bileşik büyüme gerçekte bu kadar sürmez.') + html_[j:]
    oto = """<h3>En kötü gün otopsisi (madde 609–611)</h3>
  <p class="alt">19 Mayıs 2021 (T4 −13,3%): seçilen coinler değil piyasa çöküşü — tutulan 15 long'un hepsi −25..−40% (DOGE, YFI, IOTA, MKR …).
  Zararı büyüten iki mekanizma: short'lar çöküşün ortasında kâr alıp kapandı (kitap net long kaldı) ve 24 saatlik stop gün içi iğnede, dipte doldu.
  Stop'u 4 saatlik kapanışla tetiklemek o günü −7,8%'e indiriyor ama getiriyi ve kaldıraç tavanını değiştirmiyor; kaldıracı bağlayan 6 yıllık en büyük
  düşüş (2022 yazı, UNFI short sıkışması, −15,3%) — onu kesmeye yönelik iki kural (zarardaki pozisyona ekleme yok, coin başına kayıp hafızası) RED.
  Çıkış otopsisi (madde 621, ~12 bin çıkış): kâr al ve kademe doğru zamanda; erken satış YALNIZ 24 sa stop'ta ve yalnız piyasa sakinken
  (tek coin çöküşü 3 günde dönüyor). Koşullu stop (madde 622-623: stop yalnız piyasa medyanı ≤ −%3 iken) aynı riskte yılda +12..+19 puan,
  dört bakiye/kitap hücresinin dördünde de; Sharpe iki dönemde de ↑.</p>"""
    if T6V:
        oto = """<h3>En kötü gün otopsisi (madde 609–611, 621–623)</h3>
  <p class="alt">19 Mayıs 2021 (T4 −13,3%): piyasa çöküşü; short'lar çöküş ortasında kâr aldı, 24 sa stop iğnede dipte doldu. Çıkış otopsisi:
  erken satış yalnız 24 sa stop'ta ve yalnız piyasa sakinken → koşullu stop (piyasa ≤ −%3 iken) aynı riskte yılda +12..+19 puan.</p>"""
    k = html_.index("</section>", html_.index("T7K 1,15x (eski stop) · eski bot T1</h2>"))
    html_ = html_[:k] + oto + html_[k:]
html_ = html_.replace("§BAS§", para(BAS))
html_ = html_.replace("§T6K§", "T6 1x+KS").replace("§T6§", "T6 1x + koşullu stop")
open("defter.html", "w").write(html_)
print("sayfa", 3 + len(sayfalar))
