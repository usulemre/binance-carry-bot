"""Pozisyon büyüklüğü hesaplama ve günlük zarar limiti takibi."""

import json
import logging
import os
from datetime import date

logger = logging.getLogger("bot")


class RiskManager:
    def __init__(self, risk_cfg, state_file: str = "bot_state.json"):
        self.cfg = risk_cfg
        self.state_file = state_file
        self.state = self._load_state()

    def _varsayilan_durum(self) -> dict:
        return {"date": str(date.today()), "daily_pnl": 0.0, "starting_balance": None}

    def _load_state(self) -> dict:
        """Durum dosyasını okur. BOZUKSA sıfırdan başlar, ÇÖKMEZ.

        Neden önemli: bu dosya her döngüde yazılıyor. Yazma sırasında bot
        kapanırsa (elektrik, kill, disk dolu) dosya yarım kalır ve bot
        BİR DAHA HİÇ BAŞLAMAZ. Günlük zarar takibinin sıfırlanması,
        botun tamamen çalışmamasından çok daha iyidir.
        """
        if not os.path.exists(self.state_file):
            return self._varsayilan_durum()
        try:
            with open(self.state_file, "r") as f:
                st = json.load(f)
            if not isinstance(st, dict):
                raise ValueError("durum dosyası sözlük değil")
            return st
        except Exception as e:
            logger.warning(
                f"Durum dosyası okunamadı ({e}) - sıfırdan başlanıyor. "
                f"Günlük zarar takibi bu gün için sıfırlandı.")
            return self._varsayilan_durum()

    def _save_state(self):
        """Durum dosyasını ATOMİK yazar.

        Doğrudan yazmak, yazma sırasında kesinti olursa dosyayı bozar.
        Önce geçici dosyaya yazıp sonra yer değiştirmek (os.replace atomik)
        bu riski ortadan kaldırır: dosya ya eski ya yeni halidir, asla
        yarım değil.
        """
        tmp = self.state_file + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(self.state, f)
            os.replace(tmp, self.state_file)
        except Exception as e:
            logger.warning(f"Durum dosyası kaydedilemedi: {e}")
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except OSError:
                pass

    def _reset_if_new_day(self, current_balance: float):
        today = str(date.today())
        if self.state.get("date") != today:
            self.state = {"date": today, "daily_pnl": 0.0, "starting_balance": current_balance}
            self._save_state()
        if self.state.get("starting_balance") is None:
            self.state["starting_balance"] = current_balance
            self._save_state()

    def record_closed_trade_pnl(self, pnl: float, current_balance: float):
        self._reset_if_new_day(current_balance)
        self.state["daily_pnl"] += pnl
        self._save_state()

    def is_daily_loss_limit_hit(self, current_balance: float, daily_pnl: float) -> bool:
        """daily_pnl: exchange.get_today_realized_pnl() ile Binance'ten çekilen
        GERÇEK günlük gerçekleşmiş kâr/zarar. Tahmine dayalı iç takip yerine
        doğrudan borsa verisiyle karşılaştırılır."""
        self._reset_if_new_day(current_balance)
        starting = self.state["starting_balance"] or current_balance
        if starting <= 0:
            return False
        loss_pct = -daily_pnl / starting * 100
        hit = loss_pct >= self.cfg.max_daily_loss_pct
        if hit:
            logger.warning(f"Günlük zarar limiti aşıldı: %{loss_pct:.2f}")
        return hit

    def calculate_position_size(self, balance: float, entry_price: float,
                                 stop_loss: float, scale: float = 1.0) -> float:
        """
        Risk = sermaye * risk_per_trade_pct * scale.
        Miktar = Risk / |entry - stop_loss|  (kaldıraçtan bağımsız gerçek risk hesabı)
        Ayrıca max_position_notional_pct ile üst sınır uygulanır.

        scale: kademeli exposure azaltma çarpanı (0.0-1.0). Tepe bakiyeden
        düşüş arttıkça küçülür, toparlandıkça büyür. Ölçüldü: getiriyi
        artırırken max düşüşü yarıdan fazla azaltıyor (bkz. config.py
        USE_DRAWDOWN_SCALING notu).
        """
        scale = max(0.0, min(1.0, scale))
        risk_amount = balance * (self.cfg.risk_per_trade_pct / 100) * scale
        price_diff = abs(entry_price - stop_loss)
        if price_diff <= 0 or risk_amount <= 0:
            return 0.0

        quantity = risk_amount / price_diff

        # Notional üst sınırı (kaldıraçlı pozisyon büyüklüğü sermayenin belli bir %'sini aşmasın)
        max_notional = balance * self.cfg.leverage * (self.cfg.max_position_notional_pct / 100) * scale
        max_quantity_by_notional = max_notional / entry_price

        return min(quantity, max_quantity_by_notional)

    def can_open_new_position(self, current_open_count: int) -> bool:
        return current_open_count < self.cfg.max_concurrent_positions
