"""
Multiple trading strategy implementations using Lumibot framework.

Contains three distinct algorithmic approaches:
1. ATH Dip Strategy: Counter-trend reversion (buy dips from all-time highs)
2. SMA Cross Strategy: Trend-following (golden/death cross signals)
3. RSI Mean Reversion: Momentum oscillator (overbought/oversold levels)

Each strategy is self-contained and can be selected independently for backtesting.
"""

from lumibot.strategies import Strategy


class ATHDipStrategy(Strategy):
    """
    Counter-trend mean reversion strategy based on all-time high distance.
    
    Algorithm:
    - BUY: When price declines to -20% below recent all-time high
    - SELL: When price recovers to -2% below the same ATH (profit target)
    
    Rationale: Exploits panic selling and mean reversion after sharp drawdowns.
    Risk: Performs poorly in strong downtrends; works best in range-bound markets.
    """
    
    def initialize(self):
        """Strategy initialization: set update frequency and parameters."""
        self.sleeptime = "1D"  # Update once per day
        self.symbol = self.parameters.get("symbol", "SPY")
        self.ath = 0  # Track all-time high price

    def on_trading_iteration(self):
        """Execute strategy logic once per sleeptime interval."""
        price = self.get_last_price(self.symbol)
        if price is None or price <= 0:
            return

        # Update all-time high
        if price > self.ath:
            self.ath = price

        # Exit if ATH not yet established
        if self.ath == 0:
            return

        position = self.get_position(self.symbol)
        
        # ENTRY SIGNAL: Buy at -20% dip from ATH
        if position is None and price <= self.ath * 0.80:
            qty = self.cash // price
            if qty > 0:
                order = self.create_order(self.symbol, qty, "buy")
                self.submit_order(order)

        # EXIT SIGNAL: Sell at -2% (profit target hit)
        elif position is not None and price >= self.ath * 0.98:
            self.sell_all()


class SMACrossStrategy(Strategy):
    """
    Trend-following strategy based on moving average crossovers.
    
    Algorithm:
    - BUY (Golden Cross): SMA20 crosses above SMA50 (bullish trend initiation)
    - SELL (Death Cross): SMA20 falls below SMA50 (bearish trend initiation)
    
    Rationale: Simple Moving Averages are institutional-grade trend filters.
    Lag: Significant lag in fast-moving markets; best for daily/weekly timeframes.
    """
    
    def initialize(self):
        """Strategy initialization."""
        self.sleeptime = "1D"
        self.symbol = self.parameters.get("symbol", "SPY")

    def on_trading_iteration(self):
        """Execute crossover logic."""
        # Get 60 days of historical data (sufficient for 50-day SMA)
        bars = self.get_historical_prices(self.symbol, 60, "day")
        if bars is None or len(bars.df) < 50:
            return

        closes = bars.df["close"]
        sma_20 = closes.tail(20).mean()  # 20-day simple moving average
        sma_50 = closes.tail(50).mean()  # 50-day simple moving average

        position = self.get_position(self.symbol)
        price = self.get_last_price(self.symbol)

        # ENTRY SIGNAL: Golden Cross (bullish crossover)
        if position is None and sma_20 > sma_50:
            qty = self.cash // price
            if qty > 0:
                order = self.create_order(self.symbol, qty, "buy")
                self.submit_order(order)

        # EXIT SIGNAL: Death Cross (bearish crossover)
        elif position is not None and sma_20 < sma_50:
            self.sell_all()


class RSIMeanReversion(Strategy):
    """
    Mean-reversion strategy based on Relative Strength Index (RSI) extremes.
    
    Algorithm:
    - BUY: RSI < 30 (oversold condition, expect bounce)
    - SELL: RSI > 70 (overbought condition, expect pullback)
    
    Rationale: Momentum oscillator identifies exhaustion in trend moves.
    Best for: Range-bound markets; underperforms with strong directional trends.
    """
    
    def initialize(self):
        """Strategy initialization."""
        self.sleeptime = "1D"
        self.symbol = self.parameters.get("symbol", "SPY")

    def _calculate_rsi(self, prices, period=14):
        """
        Calculate Relative Strength Index (RSI) from price series.
        
        RSI = 100 - (100 / (1 + RS))
        where RS = Average Gain / Average Loss over period
        
        Args:
            prices (pd.Series): Price series (typically close prices).
            period (int): Lookback period (standard: 14).
        
        Returns:
            float or None: RSI value (0-100), or None if insufficient data.
        """
        if len(prices) < period + 1:
            return None
        
        # Calculate price deltas
        deltas = prices.diff()
        gains = deltas.where(deltas > 0, 0.0)  # Positive deltas only
        losses = -deltas.where(deltas < 0, 0.0)  # Negative deltas (absolute)
        
        # Calculate average gains and losses over period
        avg_gain = gains.tail(period).mean()
        avg_loss = losses.tail(period).mean()
        
        if avg_loss == 0:
            return 100  # Perfect uptrend
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def on_trading_iteration(self):
        """Execute RSI-based trading logic."""
        # Get 30 days of data (sufficient for RSI calculation on 14-period)
        bars = self.get_historical_prices(self.symbol, 30, "day")
        if bars is None or len(bars.df) < 15:
            return

        closes = bars.df["close"]
        rsi = self._calculate_rsi(closes)
        if rsi is None:
            return

        position = self.get_position(self.symbol)
        price = self.get_last_price(self.symbol)

        # ENTRY SIGNAL: Oversold condition (RSI < 30)
        if position is None and rsi < 30:
            qty = self.cash // price
            if qty > 0:
                order = self.create_order(self.symbol, qty, "buy")
                self.submit_order(order)

        # EXIT SIGNAL: Overbought condition (RSI > 70)
        elif position is not None and rsi > 70:
            self.sell_all()


# Strategy registry: Maps human-readable names to strategy classes
STRATEGIES = {
    "ATH Dip": ATHDipStrategy,
    "SMA Cross": SMACrossStrategy,
    "RSI Mean Reversion": RSIMeanReversion,
}