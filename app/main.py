"""
Main application entry point for the QUANT AI TERMINAL.

Initializes logging and launches the CustomTkinter user interface.
The UI serves as the control layer for the trading engine and backtesting functionality.
"""

from app.logging_setup import configure_logging
from app.ui import TradingApp


def main():
    """
    Application bootstrap function.
    
    Sequence:
    1. Configure logging (file + console output)
    2. Initialize UI (CustomTkinter app)
    3. Start event loop
    """
    configure_logging()
    app = TradingApp()
    app.run()


if __name__ == "__main__":
    main()
