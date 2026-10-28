import pandas as pd, numpy as np, math
i = pd.read_pickle('/tmp/m644_kullanici.pkl'); g = pd.read_pickle('/tmp/m644_kullanici_gun.pkl')
g = g[g.index >= '2026-07-10']; g.iloc[0] = 2000.0
d = g.pct_change()
def y(x, k=2): return "—" if pd.isna(x) else (f"{x*100:+.{k}f}".replace('.', ',').replace('-', '−') + '%')
def p(x): return f"{x:,.0f}".replace(',', '.') + ' $'
def c(x): return '' if pd.isna(x) else ('pos' if x > 0.0005 else 'neg' if x < -0.0005 else '')
W, H = 680, 220; n = len(g); lo, hi = math.log10(g.min() * 0.9), math.log10(g.max() * 1.1)
X = lambda k: 50 + (W - 60) * k / (n - 1); Yf = lambda v: 10 + (H - 35) * (1 - (math.log10(v) - lo) / (hi - lo))
svg = [f'<svg viewBox="0 0 {W} {H}" style="width:100%">']
for t in (1000, 1500, 2000, 3000, 4000, 5000):
    if lo <= math.log10(t) <= hi: svg.append(f'<line x1="50" x2="{W-10}" y1="{Yf(t):.1f}" y2="{Yf(t):.1f}" stroke="#e2e6ee"/><text x="46" y="{Yf(t)+3:.1f}" font-size="9" text-anchor="end" fill="#5a6475">{p(t)}</text>')
for k, t in enumerate(g.index):
    if t.day == 1: svg.append(f'<text x="{X(k):.1f}" y="{H-6}" font-size="9" text-anchor="middle" fill="#5a6475">{t:%d.%m}</text>')
svg.append('<polyline fill="none" stroke="#7a4fa3" stroke-width="1.8" points="' + ' '.join(f"{X(k):.1f},{Yf(v):.1f}" for k, v in enumerate(g.values)) + '"/></svg>')
sh = i[i.yon < 0]; lg = i[i.yon > 0]
h = [f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><title>Reversal Deneyi — Yeniden Üretim</title><style>
body{{font-family:Arial,Helvetica,sans-serif;color:#1d2433;margin:26px;font-size:11.5px}} h1{{font-size:22px;margin:0}} h2{{font-size:15px;border-bottom:2px solid #7a4fa3;padding-bottom:3px;margin-top:20px}}
.alt{{color:#5a6475}} table{{border-collapse:collapse;width:100%;margin:6px 0 12px}} th,td{{border-bottom:1px solid #e2e6ee;padding:3px 5px;text-align:right}} th{{background:#f3f5f9}}
.l{{text-align:left}} .pos{{color:#1d7a4c;font-weight:600}} .neg{{color:#b3392f;font-weight:600}} .k{{display:inline-block;margin-right:22px}} .k b{{font-size:20px;display:block}}
.not{{font-size:9.5px;color:#5a6475;line-height:1.45}}</style></head><body>
<h1>Reversal Deneyi — bizim veride yeniden üretim</h1>
<p class="alt">10 Temmuz 2026 19:21 TR → 30 Eylül 2026 (verimiz burada bitiyor; botun 109 gününün ilk 82 günü) · 2.000 $ başlangıç · kâr yeniden yatırılır</p>
<div><span class="k">30 Eylül bakiye<b>{p(g.iloc[-1])}</b></span><span class="k">Toplam<b class="{c(g.iloc[-1]/2000-1)}">{y(g.iloc[-1]/2000-1,0)}</b></span>
<span class="k">En düşük<b class="neg">{p(g.min())}</b></span><span class="k">En kötü gün<b class="neg">{y(d.min(),1)}</b></span>
<span class="k">İşlem<b>{len(i)}</b></span><span class="k">Kazanan<b>{(i.getiri>0).mean()*100:.0f}%</b></span></div>
{''.join(svg)}
<p class="not">Kural: her gün 03:00 TR'de (00:00 UTC) son 24 saatte ±%30'dan fazla hareket etmiş, 24 sa hacmi ≥ 5 M$ olan coinlerden en büyük hareketli
ikisi: yükseleni SHORT, düşeni LONG; her biri o anki bakiyenin %25'i; 1 gün tut (ertesi 03:00'te kapat) ya da %25 sert stop; giriş/çıkış 5 bp kayma,
funding dahil. Veri: Binance 4 saatlik mumlar (853 sembol). Short {len(sh)} işlem ort {y(sh.getiri.mean())} · Long {len(lg)} işlem ort {y(lg.getiri.mean())} ·
stop'la kapanan {(i.neden=='stop').mean()*100:.0f}%. Botun gerçek dolumları / saatleri farklı olabilir; karar saati değişince sonuç çok değişiyor
(aynı dönem 07:00 TR'de 1.657 $, 15:00'te 327 $) — bkz. KAR_HARITASI madde 644.</p>
<h2>Gün gün</h2><table><tr><th class="l">Tarih</th><th>Bakiye</th><th>Gün</th><th class="l">O gün açılan pozisyonlar (03:00) → sonuç</th><th>Kâr $</th></tr>"""]
i['gun'] = i.giris_tr.dt.normalize()
for t in g.index[1:]:
    x = i[i.gun == t]
    poz = '<br>'.join(f"{r.sembol.replace('USDT','')} {'SHORT' if r.yon<0 else 'LONG'} {r.giris:.4g} → {r.cikis:.4g} "
                      f"<span class='{c(r.getiri)}'>{y(r.getiri,1)}</span>{' (stop)' if r.neden=='stop' else ''}" for r in x.itertuples()) or '—'
    h.append(f"<tr><td class='l'>{t:%d.%m.%Y}</td><td>{p(g[t])}</td><td class='{c(d[t])}'>{y(d[t])}</td><td class='l'>{poz}</td>"
             f"<td class='{c(x.kar_usd.sum()/1e4) if len(x) else ''}'>{x.kar_usd.sum():+,.0f} $</td></tr>")
h.append("</table></body></html>")
open('reversal_yeniden.html', 'w').write(''.join(h))
