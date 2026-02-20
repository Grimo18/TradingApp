"""Strategie di trading multiple."""

from lumibot.strategies import Strategy

class ATHDipStrategy(Strategy):
    """Compra a -20% dall'ATH e vende a -2% dall'ATH."""
    def initialize(self):
        self.sleeptime = "1D"
        self.symbol = self.parameters.get("symbol", "SPY")
        self.ath = 0

    def on_trading_iteration(self):
        price = self.get_last_price(self.symbol)
        if price is None or price <= 0:
            return

        if price > self.ath:
            self.ath = price

        if self.ath == 0:
            return

        position = self.get_position(self.symbol)
        
        # BUY: -20% dall'ATH
        if position is None and price <= self.ath * 0.80:
            qty = self.cash // price
            if qty > 0:
                order = self.create_order(self.symbol, qty, "buy")
                self.submit_order(order)

        # SELL: Ritorno al -2%
        elif position is not None and price >= self.ath * 0.98:
            self.sell_all()


class SMACrossStrategy(Strategy):
    """Strategia basata su incrocio medie mobili: SMA20 supera SMA50."""
    def initialize(self):
        self.sleeptime = "1D"
        self.symbol = self.parameters.get("symbol", "SPY")

    def on_trading_iteration(self):
        bars = self.get_historical_prices(self.symbol, 60, "day")
        if bars is None or len(bars.df) < 50:
            return

        closes = bars.df["close"]
        sma_20 = closes.tail(20).mean()
        sma_50 = closes.tail(50).mean()

        position = self.get_position(self.symbol)
        price = self.get_last_price(self.symbol)

        # BUY: Golden Cross
        if position is None and sma_20 > sma_50:
            qty = self.cash // price
            if qty > 0:
                order = self.create_order(self.symbol, qty, "buy")
                self.submit_order(order)

        # SELL: Death Cross
        elif position is not None and sma_20 < sma_50:
            self.sell_all()


class RSIMeanReversion(Strategy):
    """Compra se RSI < 30 (ipervenduto), vende se RSI > 70 (ipercomprato)."""
    def initialize(self):
        self.sleeptime = "1D"
        self.symbol = self.parameters.get("symbol", "SPY")

    def _calculate_rsi(self, prices, period=14):
        if len(prices) < period + 1:
            return None
        deltas = prices.diff()
        gains = deltas.where(deltas > 0, 0.0)
        losses = -deltas.where(deltas < 0, 0.0)
        avg_gain = gains.tail(period).mean()
        avg_loss = losses.tail(period).mean()
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def on_trading_iteration(self):
        bars = self.get_historical_prices(self.symbol, 30, "day")
        if bars is None or len(bars.df) < 15:
            return

        closes = bars.df["close"]
        rsi = self._calculate_rsi(closes)
        if rsi is None:
            return

        position = self.get_position(self.symbol)
        price = self.get_last_price(self.symbol)

        # BUY: Ipervenduto
        if position is None and rsi < 30:
            qty = self.cash // price
            if qty > 0:
                order = self.create_order(self.symbol, qty, "buy")
                self.submit_order(order)

        # SELL: Ipercomprato
        elif position is not None and rsi > 70:
            self.sell_all()

# Dizionario per mappare nomi strategie a classi
STRATEGIES = {
    "ATH Dip": ATHDipStrategy,
    "SMA Cross": SMACrossStrategy,
    "RSI Mean Reversion": RSIMeanReversion,
}