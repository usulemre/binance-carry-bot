"""
Bot İzleme Arayüzü
====================
Botla (main.py) AYNI ANDA, ayrı bir terminalde çalıştırılır:

    python dashboard.py

Sonra tarayıcıda http://127.0.0.1:5000 açılır. Bakiye, açık pozisyonlar,
son taranan sinyaller ve log kaydını 5 saniyede bir otomatik yeniler.
"""

import json
import os

from flask import Flask, jsonify, render_template_string

import config

app = Flask(__name__)

# Anahtar varsa hesap/pozisyon bilgisi de gösterilir; yoksa sadece tarama sonuçları gösterilir.
HAS_KEYS = bool(config.API_KEY and config.API_SECRET)
if HAS_KEYS:
    from exchange_client import ExchangeClient
    from risk_manager import RiskManager
    exchange = ExchangeClient(config.API_KEY, config.API_SECRET, mode=config.BINANCE_MODE)
    risk_mgr = RiskManager(config.RISK, config.STATE_FILE)

HTML_PAGE = """
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Binance Agentic Bot - Panel</title>
<style>
  :root { --green:#16c784; --red:#ea3943; --bg:#0e1117; --card:#161b22; --border:#2a2f3a; --text:#e6edf3; --muted:#8b949e; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--text); font-family: -apple-system, Segoe UI, Roboto, sans-serif; padding: 24px; }
  h1 { font-size: 20px; margin-bottom: 4px; }
  .sub { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 24px; }
  .stat { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
  .stat .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; }
  .stat .value { font-size: 24px; font-weight: 600; margin-top: 6px; }
  .positive { color: var(--green); } .negative { color: var(--red); }
  table { width: 100%; border-collapse: collapse; background: var(--card); border: 1px solid var(--border); border-radius: 10px; overflow: hidden; }
  th, td { text-align: left; padding: 10px 14px; font-size: 13px; border-bottom: 1px solid var(--border); }
  th { color: var(--muted); font-weight: 500; text-transform: uppercase; font-size: 11px; }
  tr:last-child td { border-bottom: none; }
  .badge { padding: 3px 8px; border-radius: 6px; font-size: 11px; font-weight: 600; }
  .badge.long { background: rgba(22,199,132,0.15); color: var(--green); }
  .badge.short { background: rgba(234,57,67,0.15); color: var(--red); }
  section { margin-bottom: 28px; }
  section h2 { font-size: 14px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px; }
  #log { background: #000; color: #0f0; font-family: monospace; font-size: 12px; padding: 14px; border-radius: 10px; height: 200px; overflow-y: auto; white-space: pre-wrap; border: 1px solid var(--border); }
  .status-dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:6px; }
</style>
</head>
<body>
  <h1>🤖 Agentic Binance Futures Bot</h1>
  <div class="sub" id="lastUpdate">Yükleniyor...</div>

  <div class="grid">
    <div class="stat"><div class="label">Bakiye (USDT)</div><div class="value" id="balance">-</div></div>
    <div class="stat"><div class="label">Günlük P&L</div><div class="value" id="dailyPnl">-</div></div>
    <div class="stat"><div class="label">Açık Pozisyon</div><div class="value" id="openCount">-</div></div>
    <div class="stat"><div class="label">Günlük Limit</div><div class="value" id="dailyLimitStatus">-</div></div>
  </div>

  <section>
    <h2>Açık Pozisyonlar</h2>
    <table id="positionsTable">
      <thead><tr><th>Sembol</th><th>Yön</th><th>Miktar</th><th>Giriş</th><th>Şimdiki Fiyat</th><th>Anlık P&L</th></tr></thead>
      <tbody></tbody>
    </table>
  </section>

  <section>
    <h2>Son Tarama - En Güçlü Sinyaller</h2>
    <table id="signalsTable">
      <thead><tr><th>Sembol</th><th>Yön</th><th>Skor</th><th>Giriş</th><th>Stop-Loss</th><th>Take-Profit</th></tr></thead>
      <tbody></tbody>
    </table>
  </section>

  <section>
    <h2>Canlı Log</h2>
    <div id="csPanel" style="display:none;margin:12px 0;padding:10px;
         border:1px solid #30363d;border-radius:6px;background:#161b22">
      <b>Kesitsel bot</b> — tepe bakiye: <span id="csPeak">-</span> USDT |
      düşüş: <span id="csDd">-</span> | durum: <span id="csDurum">-</span>
    </div>
    <div id="log">Bağlanılıyor...</div>
  </section>

<script>
async function refresh() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    document.getElementById('lastUpdate').innerText = 'Son güncelleme: ' + new Date().toLocaleTimeString('tr-TR')

    // Kesitsel bot durumu (varsa)
    const csPanel = document.getElementById('csPanel');
    if (data.crosssec) {
      csPanel.style.display = 'block';
      document.getElementById('csPeak').innerText = data.crosssec.peak.toFixed(2);
      const dd = data.crosssec.dusus_pct;
      const ddEl = document.getElementById('csDd');
      ddEl.innerText = '%' + dd.toFixed(2);
      ddEl.style.color = dd > 20 ? '#f85149' : (dd > 10 ? '#d29922' : '#3fb950');
      const dEl = document.getElementById('csDurum');
      dEl.innerText = data.crosssec.durum;
      dEl.style.color = data.crosssec.durum === 'NORMAL' ? '#3fb950' : '#f85149';
    } else { csPanel.style.display = 'none'; }

    // Borsa hatasi varsa goster
    if (data.error) {
      document.getElementById('log').innerText = '!! ' + data.error + String.fromCharCode(10) + (data.log_tail || '');
    }
      + (data.has_keys ? '' : '  •  Anahtarsız mod: sadece tarama sonuçları gösteriliyor');
    document.getElementById('balance').innerText = data.balance.toFixed(2);

    const pnlEl = document.getElementById('dailyPnl');
    pnlEl.innerText = (data.daily_pnl >= 0 ? '+' : '') + data.daily_pnl.toFixed(2) + ' USDT';
    pnlEl.className = 'value ' + (data.daily_pnl >= 0 ? 'positive' : 'negative');

    document.getElementById('openCount').innerText = data.open_positions.length + ' / ' + data.max_positions;

    const limitEl = document.getElementById('dailyLimitStatus');
    limitEl.innerText = data.daily_limit_hit ? 'DURDURULDU' : 'Aktif';
    limitEl.className = 'value ' + (data.daily_limit_hit ? 'negative' : 'positive');

    const posBody = document.querySelector('#positionsTable tbody');
    posBody.innerHTML = data.open_positions.length ? '' : '<tr><td colspan="6" style="color:#8b949e">Açık pozisyon yok</td></tr>';
    data.open_positions.forEach(p => {
      const pnlClass = parseFloat(p.pnl) >= 0 ? 'positive' : 'negative';
      posBody.innerHTML += `<tr>
        <td>${p.symbol}</td>
        <td><span class="badge ${p.side.toLowerCase()}">${p.side}</span></td>
        <td>${p.amount}</td>
        <td>${p.entry}</td>
        <td>${p.mark}</td>
        <td class="${pnlClass}">${p.pnl}</td>
      </tr>`;
    });

    const sigBody = document.querySelector('#signalsTable tbody');
    sigBody.innerHTML = data.signals.length ? '' : '<tr><td colspan="6" style="color:#8b949e">Henüz tarama yapılmadı</td></tr>';
    data.signals.forEach(s => {
      sigBody.innerHTML += `<tr>
        <td>${s.symbol}</td>
        <td><span class="badge ${s.direction.toLowerCase()}">${s.direction}</span></td>
        <td>${s.score}</td>
        <td>${s.entry_price}</td>
        <td>${s.stop_loss}</td>
        <td>${s.take_profit}</td>
      </tr>`;
    });

    document.getElementById('log').innerText = data.log_tail;
    const logEl = document.getElementById('log');
    logEl.scrollTop = logEl.scrollHeight;
  } catch (e) {
    document.getElementById('lastUpdate').innerText = 'Bağlantı hatası: ' + e;
  }
}
refresh();
setInterval(refresh, 5000);
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML_PAGE)


def _crosssec_durum():
    """Kesitsel botun durum dosyasını okur (varsa). Tepe bakiye ve
    mevcut düşüş, kademeli azaltma/devre kesicinin ne durumda
    olduğunu gösterir - canlı izlemede en kritik bilgi."""
    try:
        import crosssec_bot as cb
        if not os.path.exists(cb.STATE_FILE):
            return None
        with open(cb.STATE_FILE) as f:
            st = json.load(f)
        peak = float(st.get("peak_balance", 0))
        if peak <= 0:
            return None
        return {"peak_balance": round(peak, 2)}
    except Exception:
        return None


@app.route("/api/status")
def status():
    signals = []
    if os.path.exists("last_signals.json"):
        with open("last_signals.json") as f:
            snap = json.load(f)
            signals = snap.get("signals", [])

    log_tail = ""
    if os.path.exists(config.LOG_FILE):
        with open(config.LOG_FILE) as f:
            lines = f.readlines()
            log_tail = "".join(lines[-40:])

    if not HAS_KEYS:
        return jsonify({
            "has_keys": False,
            "balance": 0,
            "daily_pnl": 0,
            "daily_limit_hit": False,
            "open_positions": [],
            "max_positions": config.RISK.max_concurrent_positions,
            "signals": signals,
            "log_tail": log_tail or "Henüz tarama çalıştırılmadı. 'python scanner_public.py' çalıştırın.",
        })

    # Borsa geçici olarak cevap vermeyebilir. Dashboard'ın ÇÖKMESİ,
    # botun çalışıp çalışmadığını göremez hale gelmek demektir - en çok
    # ihtiyaç duyulduğu anda. Hata durumunda son bilinen veriyi göster.
    try:
        balance = exchange.get_account_balance_usdt()
        daily_pnl = exchange.get_today_realized_pnl()
    except Exception as e:
        return jsonify({
            "has_keys": True,
            "error": f"Borsaya ulaşılamıyor: {e}",
            "balance": 0, "daily_pnl": 0, "daily_limit_hit": False,
            "open_positions": [],
            "max_positions": config.RISK.max_concurrent_positions,
            "signals": signals,
            "log_tail": log_tail,
        })
    open_positions = []
    for p in exchange.get_open_positions():
        amt = float(p["positionAmt"])
        open_positions.append({
            "symbol": p["symbol"],
            "side": "LONG" if amt > 0 else "SHORT",
            "amount": abs(amt),
            "entry": float(p["entryPrice"]),
            "mark": float(p["markPrice"]),
            "pnl": round(float(p["unRealizedProfit"]), 4),
        })

    # Kesitsel bot çalışıyorsa düşüş durumunu da göster
    cs = _crosssec_durum()
    dusus = None
    if cs and balance > 0:
        peak = cs["peak_balance"]
        dusus_pct = (peak - balance) / peak * 100 if peak > 0 else 0.0
        try:
            import crosssec_bot as cb
            olcek = cb.compute_exposure_scale(dusus_pct)
            durum = ("NORMAL" if olcek >= 0.99 else
                     f"KÜÇÜLTÜLDÜ (%{olcek*100:.0f})" if olcek > 0.01 else
                     "POZİSYON AÇILMIYOR")
            if dusus_pct >= cb.MAX_DRAWDOWN_PCT:
                durum = "DEVRE KESİCİ TETİKLENDİ"
        except Exception:
            durum = "-"
        dusus = {"peak": peak, "dusus_pct": round(dusus_pct, 2), "durum": durum}

    return jsonify({
        "has_keys": True,
        "balance": balance,
        "daily_pnl": daily_pnl,
        "daily_limit_hit": risk_mgr.is_daily_loss_limit_hit(balance, daily_pnl),
        "open_positions": open_positions,
        "max_positions": config.RISK.max_concurrent_positions,
        "signals": signals,
        "log_tail": log_tail,
        "crosssec": dusus,
    })


if __name__ == "__main__":
    print("Panel açılıyor: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
