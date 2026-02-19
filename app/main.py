"""Entry point dell'applicazione."""

from app.logging_setup import configure_logging
from app.ui import TradingApp


def main():
    configure_logging()
    app = TradingApp()
    app.run()


if __name__ == "__main__":
    main()
