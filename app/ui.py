"""Interfaccia grafica CustomTkinter."""

import os
import threading
import tkinter as tk
import webbrowser

import customtkinter as ctk

from app import config
from app.backtest import esegui_backtest


class TradingApp:
    """GUI principale con gestione del backtest in thread separato."""

    def __init__(self):
        ctk.set_appearance_mode(config.APPEARANCE_MODE)
        ctk.set_default_color_theme(config.COLOR_THEME)

        self.app = ctk.CTk()
        self.app.title(config.APP_TITLE)
        self.app.geometry(config.APP_SIZE)
        self.app.minsize(*config.APP_MIN_SIZE)
        self.app.configure(fg_color=config.COLOR_BG)

        self._setup_fonts()
        self._build_layout()

    def _setup_fonts(self):
        # Tipografia coerente per un look professionale
        self.title_font = ctk.CTkFont(family="Segoe UI", size=24, weight="bold")
        self.subtitle_font = ctk.CTkFont(family="Segoe UI", size=13)
        self.section_font = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.body_font = ctk.CTkFont(family="Segoe UI", size=12)

    def _build_layout(self):
        self.app.grid_rowconfigure(0, weight=1)
        self.app.grid_columnconfigure(0, weight=1)

        root = ctk.CTkFrame(self.app, fg_color=config.COLOR_PANEL, corner_radius=20)
        root.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(root, fg_color=config.COLOR_HEADER, corner_radius=18)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 12))
        header.grid_columnconfigure(0, weight=1)

        label_titolo = ctk.CTkLabel(header, text=config.APP_TITLE, font=self.title_font)
        label_titolo.grid(row=0, column=0, sticky="w", padx=18, pady=(14, 2))

        label_sottotitolo = ctk.CTkLabel(
            header,
            text="Backtest automatico con strategia ATH dip",
            font=self.subtitle_font,
            text_color=config.COLOR_TEXT_SUBTLE,
        )
        label_sottotitolo.grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

        body = ctk.CTkFrame(root, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 16))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=3)
        body.grid_rowconfigure(1, weight=1)

        card_left = ctk.CTkFrame(
            body,
            fg_color=config.COLOR_CARD,
            corner_radius=16,
            border_width=1,
            border_color=config.COLOR_BORDER,
        )
        card_left.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=6)
        card_left.grid_columnconfigure(0, weight=1)

        card_right = ctk.CTkFrame(
            body,
            fg_color=config.COLOR_CARD,
            corner_radius=16,
            border_width=1,
            border_color=config.COLOR_BORDER,
        )
        card_right.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=6)
        card_right.grid_columnconfigure(0, weight=1)

        label_impostazioni = ctk.CTkLabel(
            card_left, text="Impostazioni", font=self.section_font
        )
        label_impostazioni.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 8))

        label_capitale = ctk.CTkLabel(
            card_left, text="Capitale iniziale", font=self.body_font
        )
        label_capitale.grid(row=1, column=0, sticky="w", padx=16, pady=(4, 2))

        self.entry_capitale = ctk.CTkEntry(
            card_left, placeholder_text="10000", height=36, corner_radius=10
        )
        self.entry_capitale.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))

        label_asset = ctk.CTkLabel(card_left, text="Asset", font=self.body_font)
        label_asset.grid(row=3, column=0, sticky="w", padx=16, pady=(4, 2))

        self.option_asset = ctk.CTkOptionMenu(
            card_left,
            values=["GLD", "SPY", "AAPL", "SLV"],
            height=36,
            corner_radius=10,
            fg_color=config.COLOR_HEADER,
            button_color=config.COLOR_ACCENT,
            button_hover_color=config.COLOR_ACCENT_HOVER,
        )
        self.option_asset.set("SPY")
        self.option_asset.grid(row=4, column=0, sticky="ew", padx=16, pady=(0, 12))

        label_regole = ctk.CTkLabel(
            card_left,
            text=(
                "Regole:\n"
                "BUY se prezzo <= -20% ATH\n"
                "SELL se prezzo >= -2% ATH"
            ),
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
            justify="left",
        )
        label_regole.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 12))

        self.bottone_avvio = ctk.CTkButton(
            card_left,
            text="Avvia Simulazione",
            height=40,
            corner_radius=12,
            fg_color=config.COLOR_ACCENT,
            hover_color=config.COLOR_ACCENT_HOVER,
            command=self._on_start,
        )
        self.bottone_avvio.grid(row=6, column=0, sticky="ew", padx=16, pady=(4, 16))

        label_stato_titolo = ctk.CTkLabel(
            card_right, text="Stato", font=self.section_font
        )
        label_stato_titolo.grid(row=0, column=0, sticky="w", padx=16, pady=(16, 6))

        self.label_stato = ctk.CTkLabel(
            card_right,
            text="In attesa...",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#e2e8f0",
            justify="left",
            wraplength=220,
        )
        self.label_stato.grid(row=1, column=0, sticky="w", padx=16, pady=(2, 6))

        self.progress_bar = ctk.CTkProgressBar(card_right, height=10, corner_radius=6)
        self.progress_bar.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        self.progress_bar.set(0)

        label_info = ctk.CTkLabel(
            card_right,
            text=(
                "Backtest dal 01/01/2020 a oggi\n"
                "Tearsheet aperto in browser"
            ),
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
            justify="left",
        )
        label_info.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 10))

        label_market_title = ctk.CTkLabel(
            card_right, text="Snapshot Mercato", font=self.section_font
        )
        label_market_title.grid(row=4, column=0, sticky="w", padx=16, pady=(6, 6))

        self.label_market_price = ctk.CTkLabel(
            card_right,
            text="Prezzo: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
        )
        self.label_market_price.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 2))

        self.label_market_return = ctk.CTkLabel(
            card_right,
            text="Rendimento 1Y: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
        )
        self.label_market_return.grid(row=6, column=0, sticky="w", padx=16, pady=(0, 2))

        self.label_market_vol = ctk.CTkLabel(
            card_right,
            text="Volatilita 1Y: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
        )
        self.label_market_vol.grid(row=7, column=0, sticky="w", padx=16, pady=(0, 2))

        self.label_market_update = ctk.CTkLabel(
            card_right,
            text="Aggiornato: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
        )
        self.label_market_update.grid(row=8, column=0, sticky="w", padx=16, pady=(0, 16))

        card_bottom = ctk.CTkFrame(
            body,
            fg_color=config.COLOR_CARD,
            corner_radius=16,
            border_width=1,
            border_color=config.COLOR_BORDER,
        )
        card_bottom.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=0, pady=(6, 0))
        card_bottom.grid_columnconfigure(0, weight=1)
        card_bottom.grid_columnconfigure(1, weight=1)

        label_details_title = ctk.CTkLabel(
            card_bottom, text="Dettagli Simulazione", font=self.section_font
        )
        label_details_title.grid(row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(14, 6))

        self.label_details_left = ctk.CTkLabel(
            card_bottom,
            text="Ticker: -\nCapitale: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
            justify="left",
        )
        self.label_details_left.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 14))

        self.label_details_right = ctk.CTkLabel(
            card_bottom,
            text="Periodo: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
            justify="left",
        )
        self.label_details_right.grid(row=1, column=1, sticky="w", padx=16, pady=(0, 14))

        label_results_title = ctk.CTkLabel(
            card_bottom, text="Risultati benchmark", font=self.section_font
        )
        label_results_title.grid(row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 6))

        self.label_metrics_left = ctk.CTkLabel(
            card_bottom,
            text="Rendimento totale: -\nCAGR: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
            justify="left",
        )
        self.label_metrics_left.grid(row=3, column=0, sticky="w", padx=16, pady=(0, 10))

        self.label_metrics_right = ctk.CTkLabel(
            card_bottom,
            text="Max Drawdown: -\nVolatilita: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
            justify="left",
        )
        self.label_metrics_right.grid(row=3, column=1, sticky="w", padx=16, pady=(0, 10))

        label_strategy_title = ctk.CTkLabel(
            card_bottom, text="Risultati strategia", font=self.section_font
        )
        label_strategy_title.grid(row=4, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 6))

        self.label_strategy_left = ctk.CTkLabel(
            card_bottom,
            text="Rendimento totale: -\nCAGR: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
            justify="left",
        )
        self.label_strategy_left.grid(row=5, column=0, sticky="w", padx=16, pady=(0, 10))

        self.label_strategy_right = ctk.CTkLabel(
            card_bottom,
            text="Max Drawdown: -\nSharpe: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
            justify="left",
        )
        self.label_strategy_right.grid(row=5, column=1, sticky="w", padx=16, pady=(0, 10))

        label_chart_title = ctk.CTkLabel(
            card_bottom, text="Equity curve (benchmark)", font=self.section_font
        )
        label_chart_title.grid(row=6, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 6))

        self.chart_canvas = tk.Canvas(
            card_bottom,
            height=110,
            bg=config.COLOR_HEADER,
            highlightthickness=0,
        )
        self.chart_canvas.grid(row=7, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 12))
        self.chart_canvas.bind("<Configure>", lambda event: self._redraw_chart())

        self.label_report = ctk.CTkLabel(
            card_bottom,
            text="Report: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
            justify="left",
        )
        self.label_report.grid(row=8, column=0, sticky="w", padx=16, pady=(0, 14))

        self.button_report = ctk.CTkButton(
            card_bottom,
            text="Apri report",
            height=34,
            corner_radius=10,
            fg_color=config.COLOR_ACCENT,
            hover_color=config.COLOR_ACCENT_HOVER,
            command=self._open_report,
            state="disabled",
        )
        self.button_report.grid(row=8, column=1, sticky="e", padx=16, pady=(0, 14))

        self.label_metrics_files = ctk.CTkLabel(
            card_bottom,
            text="Metriche salvate: -",
            font=self.body_font,
            text_color=config.COLOR_TEXT_SUBTLE,
            justify="left",
            wraplength=480,
        )
        self.label_metrics_files.grid(row=9, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 14))

        footer = ctk.CTkLabel(
            root,
            text="Lumibot + Yahoo Finance",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=config.COLOR_TEXT_MUTED,
        )
        footer.grid(row=2, column=0, pady=(0, 12))

    def _set_status(self, text):
        # Aggiornamento thread-safe della label di stato
        def _update():
            color = config.COLOR_TEXT_MUTED
            if text.lower().startswith("errore"):
                color = config.COLOR_ERROR
            elif text.lower().startswith("completato"):
                color = config.COLOR_SUCCESS
            self.label_stato.configure(text=text, text_color=color)

        self.app.after(0, _update)

    @staticmethod
    def _format_currency(value):
        if isinstance(value, (int, float)):
            return f"{value:,.2f}"
        return "-"

    @staticmethod
    def _format_number(value):
        if isinstance(value, (int, float)):
            return f"{value:,.2f}"
        return "-"

    @staticmethod
    def _format_percent(value):
        if isinstance(value, (int, float)):
            return f"{value:.2%}"
        return "-"

    @staticmethod
    def _format_date(value):
        if value is None:
            return "-"
        return str(value)

    def _set_market_snapshot(self, snapshot):
        def _update():
            price = snapshot.get("last_close")
            one_year = snapshot.get("one_year_return")
            vol = snapshot.get("volatility")
            update = snapshot.get("last_update")

            self.label_market_price.configure(
                text=f"Prezzo: {self._format_currency(price)}"
            )
            self.label_market_return.configure(
                text=f"Rendimento 1Y: {self._format_percent(one_year)}"
            )
            self.label_market_vol.configure(
                text=f"Volatilita 1Y: {self._format_percent(vol)}"
            )
            self.label_market_update.configure(
                text=f"Aggiornato: {self._format_date(update)}"
            )

        self.app.after(0, _update)

    def _set_details(self, details):
        def _update():
            ticker = details.get("ticker", "-")
            capital = details.get("capital", "-")
            start = details.get("start", "-")
            end = details.get("end", "-")
            self.label_details_left.configure(
                text=f"Ticker: {ticker}\nCapitale: {self._format_currency(capital)}"
            )
            self.label_details_right.configure(
                text=f"Periodo: {self._format_date(start)} -> {self._format_date(end)}"
            )

        self.app.after(0, _update)

    def _set_metrics(self, metrics):
        def _update():
            total_return = self._format_percent(metrics.get("total_return"))
            cagr = self._format_percent(metrics.get("cagr"))
            max_dd = self._format_percent(metrics.get("max_drawdown"))
            vol = self._format_percent(metrics.get("volatility"))
            self.label_metrics_left.configure(
                text=f"Rendimento totale: {total_return}\nCAGR: {cagr}"
            )
            self.label_metrics_right.configure(
                text=f"Max Drawdown: {max_dd}\nVolatilita: {vol}"
            )

        self.app.after(0, _update)

    def _set_strategy_metrics(self, metrics):
        def _update():
            total_return = self._format_percent(metrics.get("total_return"))
            cagr = self._format_percent(metrics.get("cagr"))
            max_dd = self._format_percent(metrics.get("max_drawdown"))
            sharpe = self._format_number(metrics.get("sharpe"))
            self.label_strategy_left.configure(
                text=f"Rendimento totale: {total_return}\nCAGR: {cagr}"
            )
            self.label_strategy_right.configure(
                text=f"Max Drawdown: {max_dd}\nSharpe: {sharpe}"
            )

        self.app.after(0, _update)

    def _set_chart_data(self, values):
        def _update():
            self.chart_data = values
            self._redraw_chart()

        self.app.after(0, _update)

    def _redraw_chart(self):
        if not hasattr(self, "chart_canvas"):
            return
        canvas = self.chart_canvas
        canvas.delete("all")
        if not getattr(self, "chart_data", None):
            return

        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width <= 2 or height <= 2:
            return

        values = self.chart_data
        min_val = min(values)
        max_val = max(values)
        if max_val == min_val:
            return

        padding = 6
        x_step = (width - padding * 2) / max(len(values) - 1, 1)
        points = []
        for idx, value in enumerate(values):
            x = padding + idx * x_step
            y = height - padding - ((value - min_val) / (max_val - min_val)) * (height - padding * 2)
            points.extend([x, y])

        canvas.create_line(points, fill=config.COLOR_CHART_LINE, width=2, smooth=True)

    def _set_report_path(self, path):
        def _update():
            self.report_path = path
            self.label_report.configure(text=f"Report: {path}")
            self.button_report.configure(state="normal")

        self.app.after(0, _update)

    def _set_metrics_files(self, files):
        def _update():
            json_path = files.get("json", "-")
            csv_path = files.get("csv", "-")
            self.label_metrics_files.configure(
                text=f"Metriche salvate: JSON {json_path} | CSV {csv_path}"
            )

        self.app.after(0, _update)

    def _open_report(self):
        if not getattr(self, "report_path", None):
            return
        abs_path = os.path.abspath(self.report_path)
        webbrowser.open(f"file:///{abs_path}")

    def _reset_results(self):
        self.report_path = None
        self.label_metrics_left.configure(text="Rendimento totale: -\nCAGR: -")
        self.label_metrics_right.configure(text="Max Drawdown: -\nVolatilita: -")
        self.label_strategy_left.configure(text="Rendimento totale: -\nCAGR: -")
        self.label_strategy_right.configure(text="Max Drawdown: -\nSharpe: -")
        self.label_report.configure(text="Report: -")
        self.label_metrics_files.configure(text="Metriche salvate: -")
        self.button_report.configure(state="disabled")
        self.chart_data = None
        self._redraw_chart()

    def _set_running(self, running):
        def _update():
            if running:
                self.bottone_avvio.configure(
                    text="Simulazione in corso...", state="disabled"
                )
            else:
                self.bottone_avvio.configure(text="Avvia Simulazione", state="normal")

        self.app.after(0, _update)

    def _progress_start(self):
        self.app.after(0, self.progress_bar.start)

    def _progress_stop(self):
        self.app.after(0, self.progress_bar.stop)

    def _on_start(self):
        # Validazione input capitale
        try:
            capitale = float(self.entry_capitale.get().strip())
            if capitale <= 0:
                raise ValueError
        except ValueError:
            self.label_stato.configure(text="Capitale non valido.")
            return

        self._reset_results()
        ticker = self.option_asset.get()

        callbacks = {
            "status": self._set_status,
            "progress_start": self._progress_start,
            "progress_stop": self._progress_stop,
            "market": self._set_market_snapshot,
            "details": self._set_details,
            "running": self._set_running,
            "metrics": self._set_metrics,
            "strategy_metrics": self._set_strategy_metrics,
            "chart": self._set_chart_data,
            "report": self._set_report_path,
            "metrics_files": self._set_metrics_files,
        }

        # Avvio del backtest in un thread separato
        thread = threading.Thread(
            target=esegui_backtest, args=(ticker, capitale, callbacks), daemon=True
        )
        thread.start()

    def run(self):
        self.app.mainloop()
