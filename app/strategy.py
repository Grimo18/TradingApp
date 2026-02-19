"""Strategie di trading multiple."""

from lumibot.strategies import Strategy


class ATHDipStrategy(Strategy):
    """Compra a -20% dall'ATH e vende a -2% dall'ATH."""

    def initialize(self):
        # Parametri passati dal backtest
        self.symbol = self.parameters["symbol"]
        self.ath = None

    def on_trading_iteration(self):
        # Prezzo corrente e aggiornamento ATH
        price = self.get_last_price(self.symbol)
        if price is None:
            return

        if self.ath is None or price > self.ath:
            self.ath = price

        position = self.get_position(self.symbol)
        has_position = position is not None and position.quantity > 0

        # BUY: -20% o peggio rispetto all'ATH
        if (not has_position) and price <= self.ath * 0.80:
            cash = self.get_cash()
            qty = int(cash / price)
            if qty > 0:
                self.buy(self.symbol, qty)

        # SELL: ritorno a -2% o meglio rispetto all'ATH
        if has_position and price >= self.ath * 0.98:
            self.sell_all()


class SMACrossStrategy(Strategy):
    """Strategia basata su incrocio medie mobili: SMA20 e SMA50."""

    def initialize(self):
        self.symbol = self.parameters["symbol"]
        self.sleeptime = "1D"  # Esegue una volta al giorno

    def on_trading_iteration(self):
        # Ottieni storico prezzi (ultimi 60 giorni per calcolare SMA50)
        bars = self.get_historical_prices(self.symbol, 60, "day")
        if bars is None or bars.df.empty:
            return

        closes = bars.df["close"]
        if len(closes) < 50:
            return

        # Calcolo medie mobili
        sma_20 = closes.tail(20).mean()
        sma_50 = closes.tail(50).mean()

        position = self.get_position(self.symbol)
        has_position = position is not None and position.quantity > 0

        # BUY: SMA20 supera SMA50 (golden cross)
        if not has_position and sma_20 > sma_50:
            cash = self.get_cash()
            price = self.get_last_price(self.symbol)
            if price and price > 0:
                qty = int(cash / price)
                if qty > 0:
                    self.buy(self.symbol, qty)

        # SELL: SMA20 scende sotto SMA50 (death cross)
        if has_position and sma_20 < sma_50:
            self.sell_all()


class RSIMeanReversion(Strategy):
    """Strategia mean reversion basata su RSI."""

    def initialize(self):
        self.symbol = self.parameters["symbol"]
        self.sleeptime = "1D"

    def _calculate_rsi(self, prices, period=14):
        """Calcola RSI su una serie di prezzi."""
        if len(prices) < period + 1:
            return None

        deltas = prices.diff()
        gains = deltas.where(deltas > 0, 0)
        losses = -deltas.where(deltas < 0, 0)

        avg_gain = gains.tail(period).mean()
        avg_loss = losses.tail(period).mean()

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def on_trading_iteration(self):
        # Ottieni storico prezzi per calcolare RSI
        bars = self.get_historical_prices(self.symbol, 30, "day")
        if bars is None or bars.df.empty:
            return

        closes = bars.df["close"]
        rsi = self._calculate_rsi(closes, period=14)
        if rsi is None:
            return

        position = self.get_position(self.symbol)
        has_position = position is not None and position.quantity > 0

        # BUY: RSI sotto 30 (ipervenduto)
        if not has_position and rsi < 30:
            cash = self.get_cash()
            price = self.get_last_price(self.symbol)
            if price and price > 0:
                qty = int(cash / price)
                if qty > 0:
                    self.buy(self.symbol, qty)

        # SELL: RSI sopra 70 (ipercomprato)
        if has_position and rsi > 70:
            self.sell_all()


# Dizionario per mappare nomi strategie a classi
STRATEGIES = {
    "ATH Dip": ATHDipStrategy,
    "SMA Cross": SMACrossStrategy,
    "RSI Mean Reversion": RSIMeanReversion,
}
