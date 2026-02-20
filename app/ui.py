"""Interfaccia grafica CustomTkinter V3.1 (Fix Stato Pulsanti)."""

import threading
import datetime
import customtkinter as ctk

from app import config
from app.backtest import esegui_backtest
from app.mt5_engine import gestisci_connessione, aggiorna_parametri_e_avvia, ferma_trading, spegni_tutto

class TradingApp:
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
        self._log_to_terminal("TERMINALE PRONTO. In attesa di selezione modalità...")

    def _setup_fonts(self):
        self.title_font = ctk.CTkFont(family="Inter", size=28, weight="bold")
        self.subtitle_font = ctk.CTkFont(family="Inter", size=13)
        self.section_font = ctk.CTkFont(family="Inter", size=15, weight="bold")
        self.body_font = ctk.CTkFont(family="Inter", size=13)
        self.metric_font = ctk.CTkFont(family="Inter", size=24, weight="bold")
        self.term_font = ctk.CTkFont(family="Consolas", size=13)

    def _build_layout(self):
        self.app.grid_rowconfigure(0, weight=1)
        self.app.grid_columnconfigure(0, weight=1)

        root = ctk.CTkScrollableFrame(self.app, fg_color=config.COLOR_PANEL, corner_radius=0)
        root.grid(row=0, column=0, sticky="nsew")
        root.grid_columnconfigure(0, weight=1)

        # HEADER
        header = ctk.CTkFrame(root, fg_color=config.COLOR_HEADER, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(header, text=config.APP_TITLE, font=self.title_font).grid(row=0, column=0, sticky="w", padx=30, pady=(20, 2))
        ctk.CTkLabel(header, text="Cloud AI + MT5 Execution Engine", font=self.subtitle_font, text_color=config.COLOR_TEXT_SUBTLE).grid(row=1, column=0, sticky="w", padx=30, pady=(0, 20))

        self.seg_mode = ctk.CTkSegmentedButton(header, values=["SIMULAZIONE", "LIVE DEMO", "SOLDI REALI"], command=self._change_mode)
        self.seg_mode.set("SIMULAZIONE")
        self.seg_mode.grid(row=0, column=1, rowspan=2, sticky="e", padx=30)

        # CORPO CENTRALE
        body = ctk.CTkFrame(root, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=30)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=2)

        # SINISTRA: IMPOSTAZIONI
        card_left = ctk.CTkFrame(body, fg_color=config.COLOR_CARD, corner_radius=12)
        card_left.grid(row=0, column=0, sticky="nsew", padx=(0, 15), pady=10)
        card_left.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card_left, text="PARAMETRI", font=self.section_font, text_color=config.COLOR_ACCENT).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 15))

        self.entry_capitale = ctk.CTkEntry(card_left, placeholder_text="Capitale ($)", height=40, border_width=0, fg_color=config.COLOR_PANEL)
        self.entry_capitale.grid(row=1, column=0, sticky="ew", padx=20, pady=5)

        self.option_strategy = ctk.CTkOptionMenu(card_left, values=["ATH Dip", "SMA Cross", "RSI Mean"], height=40, fg_color=config.COLOR_PANEL, button_color=config.COLOR_ACCENT)
        self.option_strategy.grid(row=2, column=0, sticky="ew", padx=20, pady=5)

        # SMART SEARCH BAR
        self.frame_ticker = ctk.CTkFrame(card_left, fg_color="transparent")
        self.frame_ticker.grid(row=3, column=0, sticky="ew", padx=20, pady=5)
        self.frame_ticker.grid_columnconfigure(0, weight=1)

        self.combo_ticker = ctk.CTkComboBox(self.frame_ticker, values=["EURUSD", "BTCUSD"], height=40, fg_color=config.COLOR_PANEL, border_width=0, button_color=config.COLOR_ACCENT)
        self.combo_ticker.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.combo_ticker.set("EURUSD")
        self.combo_ticker.bind("<Return>", lambda event: self._cerca_ticker_ui())

        self.btn_cerca = ctk.CTkButton(self.frame_ticker, text="🔍", width=40, height=40, font=self.section_font, fg_color=config.COLOR_PANEL, hover_color=config.COLOR_ACCENT, command=self._cerca_ticker_ui)
        self.btn_cerca.grid(row=0, column=1)

        # Date per la Simulazione
        self.frame_date = ctk.CTkFrame(card_left, fg_color="transparent")
        self.frame_date.grid(row=4, column=0, sticky="ew", padx=20, pady=5)
        self.frame_date.grid_columnconfigure((0,1), weight=1)
        self.entry_start = ctk.CTkEntry(self.frame_date, placeholder_text="Start (YYYY-MM-DD)", height=40, border_width=0, fg_color=config.COLOR_PANEL)
        self.entry_start.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.entry_end = ctk.CTkEntry(self.frame_date, placeholder_text="End (YYYY-MM-DD)", height=40, border_width=0, fg_color=config.COLOR_PANEL)
        self.entry_end.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        # Bottone di Avvio
        self.bottone_avvio = ctk.CTkButton(card_left, text="▶ AVVIA BACKTEST", height=50, font=self.section_font, fg_color=config.COLOR_ACCENT, hover_color=config.COLOR_ACCENT_HOVER, command=self._on_start_btn)
        self.bottone_avvio.grid(row=5, column=0, sticky="ew", padx=20, pady=(20, 20))

        # DESTRA: PORTAFOGLIO E TERMINALE
        card_right = ctk.CTkFrame(body, fg_color=config.COLOR_CARD, corner_radius=12)
        card_right.grid(row=0, column=1, sticky="nsew", padx=(15, 0), pady=10)
        card_right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card_right, text="PORTAFOGLIO LIVE", font=self.section_font, text_color=config.COLOR_TEXT_SUBTLE).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 5))
        
        stats_frame = ctk.CTkFrame(card_right, fg_color="transparent")
        stats_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        stats_frame.grid_columnconfigure((0,1,2), weight=1)

        self.lbl_cash = ctk.CTkLabel(stats_frame, text="$0.00\nLiquidità", font=self.metric_font, text_color=config.COLOR_SUCCESS)
        self.lbl_cash.grid(row=0, column=0, sticky="w")
        self.lbl_pos = ctk.CTkLabel(stats_frame, text="$0.00\nIn Posizione", font=self.metric_font, text_color=config.COLOR_WARNING)
        self.lbl_pos.grid(row=0, column=1, sticky="w")
        self.lbl_tot = ctk.CTkLabel(stats_frame, text="$0.00\nEquity Totale", font=self.metric_font, text_color=config.COLOR_CHART_LINE)
        self.lbl_tot.grid(row=0, column=2, sticky="w")

        term_frame = ctk.CTkFrame(card_right, fg_color=config.COLOR_TERM_BG, corner_radius=8)
        term_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(20, 20))
        card_right.grid_rowconfigure(2, weight=1)

        self.terminal = ctk.CTkTextbox(term_frame, fg_color="transparent", text_color=config.COLOR_TERM_TEXT, font=self.term_font)
        self.terminal.pack(fill="both", expand=True, padx=15, pady=15)
        self.terminal.configure(state="disabled")

    def _log_to_terminal(self, text):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        def _update():
            self.terminal.configure(state="normal")
            self.terminal.insert("end", f"[{timestamp}] {text}\n")
            self.terminal.see("end")
            self.terminal.configure(state="disabled")
        self.app.after(0, _update)

    def _update_portfolio(self, cash, val_posizioni):
        def _update():
            self.lbl_cash.configure(text=f"${cash:,.2f}\nLiquidità")
            self.lbl_pos.configure(text=f"${val_posizioni:,.2f}\nIn Posizione")
            self.lbl_tot.configure(text=f"${(cash + val_posizioni):,.2f}\nEquity Totale")
        self.app.after(0, _update)

    def _get_callbacks(self):
        return {"log": self._log_to_terminal, "portfolio": self._update_portfolio, "running": self._set_running_ui}

    def _get_params(self):
        return {
            "ticker": self.combo_ticker.get().strip() or "EURUSD", 
            "strategia": self.option_strategy.get(),
            "budget": self.entry_capitale.get().strip() or "100"
        }

    def _change_mode(self, value):
        self.terminal.configure(state="normal")
        self.terminal.delete("1.0", "end")
        self.terminal.configure(state="disabled")
        
        if value == "SIMULAZIONE":
            spegni_tutto()
            self._log_to_terminal("Modalità Backtest. MT5 Disconnesso.")
            self.seg_mode.configure(selected_color=config.COLOR_ACCENT)
            self.frame_date.grid()
            self.bottone_avvio.configure(text="▶ AVVIA BACKTEST", fg_color=config.COLOR_ACCENT)
        else:
            self._log_to_terminal("Connessione ai Sensori Live in corso...")
            self.frame_date.grid_remove()
            # FIX: Soldi reali ora è Viola/Blu scuro, non rosso errore!
            color = config.COLOR_WARNING if value == "LIVE DEMO" else "#6366f1" 
            self.seg_mode.configure(selected_color=color)
            self.bottone_avvio.configure(text="▶ AVVIA TRADING", fg_color=color)
            gestisci_connessione(value, self._get_callbacks(), self._get_params())

    def _set_running_ui(self, is_trading):
        def _update():
            mode = self.seg_mode.get()
            if mode == "SIMULAZIONE": return
            if is_trading:
                self.bottone_avvio.configure(text="⏸ PAUSA BOT", fg_color=config.COLOR_ERROR)
            else:
                color = config.COLOR_WARNING if mode == "LIVE DEMO" else "#6366f1"
                self.bottone_avvio.configure(text="▶ AVVIA TRADING", fg_color=color)
        self.app.after(0, _update)

    def _on_start_btn(self):
        mode = self.seg_mode.get()
        text = self.bottone_avvio.cget("text")

        if mode == "SIMULAZIONE":
            self._log_to_terminal("Avvio Backtest...")
        else:
            if "AVVIA" in text:
                self._log_to_terminal("Armamento Motore: TRADING ATTIVATO.")
                from app.mt5_engine import aggiorna_parametri_e_avvia
                aggiorna_parametri_e_avvia(self._get_params())
            else:
                self._log_to_terminal("Disarmo Motore: TRADING IN PAUSA.")
                from app.mt5_engine import ferma_trading
                ferma_trading()
    
    def _cerca_ticker_ui(self):
        query = self.combo_ticker.get().strip()
        if len(query) < 2:
            self._log_to_terminal("⚠️ Scrivi almeno 2 lettere.")
            return
        self._log_to_terminal(f"🔍 Ricerca '{query}'...")
        self.btn_cerca.configure(state="disabled")
        
        def esegui_ricerca():
            from app.mt5_engine import cerca_simboli_broker
            risultati = cerca_simboli_broker(query)
            def aggiorna_ui():
                self.btn_cerca.configure(state="normal")
                if risultati:
                    self.combo_ticker.configure(values=risultati)
                    self.combo_ticker.set(risultati[0])
                    self._log_to_terminal(f"✅ Trovati {len(risultati)} asset.")
                else:
                    self._log_to_terminal("❌ Nessun risultato.")
            self.app.after(0, aggiorna_ui)
        threading.Thread(target=esegui_ricerca, daemon=True).start()

    def run(self):
        self.app.mainloop()