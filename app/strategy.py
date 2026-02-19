"""Strategia di trading basata su ATH e drawdown."""

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
