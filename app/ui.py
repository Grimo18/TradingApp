"""Interfaccia grafica CustomTkinter V8.7 (Telegram Env & Multi-User)."""

import threading
import datetime
import customtkinter as ctk

from app import config
from app.mt5_engine import gestisci_connessione, aggiorna_parametri_e_avvia, ferma_trading, spegni_tutto

C_BG = "#1e1e24"
C_CARD = "#2a2a35"
C_TEXT = "#ffffff"
C_SUB = "#9ca3af"
C_GREEN = "#4ade80"
C_GREEN_DARK = "#22c55e"
C_RED = "#f87171"
C_RED_DARK = "#ef4444"
C_TERM_BG = "#09090b"
C_BORDER = "#3f3f46"

class TradingApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        self.app = ctk.CTk()
        self.app.title("QUANT AI TERMINAL")
        self.app.geometry("1300x850")
        self.app.minsize(1100, 700)
        self.app.configure(fg_color=C_BG)
        
        self.watchlist_map = {
            "🌍 Mega-Mix Istituzionale (30 Asset)": "EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, BTCUSD, ETHUSD, AAPL.OQ, MSFT.OQ, NVDA.OQ, TSLA.OQ, AMZN.OQ, META.OQ, GOOGL.OQ, NFLX.OQ, AMD.OQ, INTC.OQ, QCOM.OQ, CSCO.OQ, PEP.OQ, COST.OQ, SBUX.OQ, PYPL.OQ, MU.OQ, TXN.OQ, INTU.OQ, AMAT.OQ, CMCSA.OQ, GILD.OQ, MDLZ.OQ",
            "🦅 Top 5 Big Tech USA": "NVDA.OQ, TSLA.OQ, AAPL.OQ, MSFT.OQ, META.OQ, AMZN.OQ",
            "💱 Top 5 Forex Majors": "EURUSD, GBPUSD, USDJPY, USDCAD, AUDUSD",
            "🪙 Top Crypto Asset": "BTCUSD, ETHUSD"
        }

        self._setup_fonts()
        self._build_layout()
        self._log_to_terminal("System status: Normal. Connection stable. Ready.")
        
        # 💡 FIX SALDO ALL'AVVIO: Forza la connessione a MT5 appena si apre la finestra!
        self._change_mode("[ Demo ]")

    def _setup_fonts(self):
        self.title_font = ctk.CTkFont(family="Inter", size=20, weight="bold")
        self.card_title_font = ctk.CTkFont(family="Inter", size=14, weight="bold")
        self.label_font = ctk.CTkFont(family="Inter", size=12)
        self.metric_font = ctk.CTkFont(family="Inter", size=28, weight="bold")
        self.sub_metric_font = ctk.CTkFont(family="Inter", size=12)
        self.term_font = ctk.CTkFont(family="Consolas", size=13)

    def _build_layout(self):
        self.app.grid_rowconfigure(1, weight=1)
        self.app.grid_columnconfigure(1, weight=1)

        header = ctk.CTkFrame(self.app, fg_color=C_BG, corner_radius=0)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=30, pady=(20, 10))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(header, text="QUANT AI TERMINAL", font=self.title_font, text_color=C_TEXT).grid(row=0, column=0, sticky="w")

        self.seg_mode = ctk.CTkSegmentedButton(header, values=["[ Backtest ]", "[ Demo ]", "[ Live ]"], 
                                               command=self._change_mode, 
                                               fg_color=C_CARD, selected_color="#4f46e5", selected_hover_color="#4338ca")
        self.seg_mode.set("[ Demo ]")
        self.seg_mode.grid(row=0, column=1, sticky="e")

        left_panel = ctk.CTkFrame(self.app, fg_color="transparent")
        left_panel.grid(row=1, column=0, sticky="nsew", padx=(30, 15), pady=(0, 20))
        left_panel.grid_columnconfigure(0, weight=1)

        # 1. Capital & Risk
        card_risk = ctk.CTkFrame(left_panel, fg_color=C_CARD, corner_radius=8, border_width=1, border_color=C_BORDER)
        card_risk.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        card_risk.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(card_risk, text="Capital & Risk", font=self.card_title_font, text_color=C_TEXT).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(card_risk, text="Maximum Capital ($)", font=self.label_font, text_color=C_SUB).grid(row=1, column=0, sticky="w", padx=15)
        self.entry_capitale = ctk.CTkEntry(card_risk, fg_color=C_BG, border_color=C_BORDER, text_color=C_TEXT, height=35)
        self.entry_capitale.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.entry_capitale.insert(0, "100.00")

        ctk.CTkLabel(card_risk, text="Max Daily Drawdown ($)", font=self.label_font, text_color=C_SUB).grid(row=5, column=0, sticky="w", padx=15)
        self.entry_loss = ctk.CTkEntry(card_risk, fg_color=C_BG, border_color=C_BORDER, text_color=C_TEXT, height=35)
        self.entry_loss.grid(row=6, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.entry_loss.insert(0, "30.00")

        # 2. Asset Selection
        card_asset = ctk.CTkFrame(left_panel, fg_color=C_CARD, corner_radius=8, border_width=1, border_color=C_BORDER)
        card_asset.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        card_asset.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card_asset, text="Asset Selection", font=self.card_title_font, text_color=C_TEXT).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        ctk.CTkLabel(card_asset, text="Select Asset List", font=self.label_font, text_color=C_SUB).grid(row=1, column=0, sticky="w", padx=15)
        
        opzioni_menu = list(self.watchlist_map.keys())
        self.combo_ticker = ctk.CTkComboBox(card_asset, values=opzioni_menu, fg_color=C_BG, border_color=C_BORDER, button_color=C_BORDER, text_color=C_TEXT, height=35)
        self.combo_ticker.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        self.combo_ticker.set(opzioni_menu[0])

        # 3. Telegram (SOLO CHAT ID ORA)
        card_tg = ctk.CTkFrame(left_panel, fg_color=C_CARD, corner_radius=8, border_width=1, border_color=C_BORDER)
        card_tg.grid(row=2, column=0, sticky="ew", pady=(0, 15))
        card_tg.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(card_tg, text="Telegram Notifications", font=self.card_title_font, text_color=C_TEXT).grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(card_tg, text="Chat ID (separati da virgola per multi-user)", font=self.label_font, text_color=C_SUB).grid(row=1, column=0, sticky="w", padx=15)
        self.entry_tg_chat = ctk.CTkEntry(card_tg, fg_color=C_BG, border_color=C_BORDER, text_color=C_TEXT, height=35, placeholder_text="es. 1234567, 9876543")
        self.entry_tg_chat.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))

        # 4. Bottoni Start / Stop
        frame_btns = ctk.CTkFrame(left_panel, fg_color="transparent")
        frame_btns.grid(row=3, column=0, sticky="ew")
        frame_btns.grid_columnconfigure((0,1), weight=1)

        self.btn_start = ctk.CTkButton(frame_btns, text="START BOT", font=self.card_title_font, fg_color=C_GREEN_DARK, hover_color=C_GREEN, text_color="#000000", height=45, command=self._on_start)
        self.btn_start.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        self.btn_stop = ctk.CTkButton(frame_btns, text="STOP BOT", font=self.card_title_font, fg_color=C_RED_DARK, hover_color=C_RED, text_color="#ffffff", height=45, command=self._on_stop, state="disabled")
        self.btn_stop.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        right_panel = ctk.CTkFrame(self.app, fg_color="transparent")
        right_panel.grid(row=1, column=1, sticky="nsew", padx=(15, 30), pady=(0, 20))
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        dash_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        dash_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))
        dash_frame.grid_columnconfigure((0,1,2), weight=1)

        self.lbl_cash = self._create_stat_card(dash_frame, 0, "Available Liquidity", "$ 0.00", "Total Available")
        self.lbl_pos = self._create_stat_card(dash_frame, 1, "Capital in Open Positions", "$ 0.00", "Active Capital")
        self.lbl_tot = self._create_stat_card(dash_frame, 2, "Total Equity", "$ 0.00", "Liquidity + Open Positions")

        term_card = ctk.CTkFrame(right_panel, fg_color=C_CARD, corner_radius=8, border_width=1, border_color=C_BORDER)
        term_card.grid(row=1, column=0, sticky="nsew")
        term_card.grid_rowconfigure(1, weight=1)
        term_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(term_card, text="Bot Activity Terminal", font=self.card_title_font, text_color=C_TEXT).grid(row=0, column=0, sticky="w", padx=20, pady=(15, 5))
        
        self.terminal = ctk.CTkTextbox(term_card, fg_color=C_TERM_BG, text_color=C_GREEN, font=self.term_font, corner_radius=6)
        self.terminal.grid(row=1, column=0, sticky="nsew", padx=20, pady=(5, 20))
        self.terminal.configure(state="disabled")

    def _create_stat_card(self, parent, col, title, value, sub):
        card = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=8, border_width=1, border_color=C_BORDER)
        card.grid(row=0, column=col, sticky="nsew", padx=(0 if col==0 else 10, 0 if col==2 else 10))
        ctk.CTkLabel(card, text=title, font=self.card_title_font, text_color=C_TEXT).pack(anchor="w", padx=20, pady=(15, 5))
        lbl_val = ctk.CTkLabel(card, text=value, font=self.metric_font, text_color=C_TEXT)
        lbl_val.pack(anchor="w", padx=20)
        ctk.CTkLabel(card, text=sub, font=self.sub_metric_font, text_color=C_SUB).pack(anchor="w", padx=20, pady=(0, 15))
        return lbl_val

    def _log_to_terminal(self, text, replace_last=False):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        def _update():
            self.terminal.configure(state="normal")
            if replace_last:
                try: self.terminal.delete("end-2l", "end-1l")
                except: pass
            self.terminal.insert("end", f"[{timestamp}] {text}\n")
            self.terminal.see("end")
            self.terminal.configure(state="disabled")
        self.app.after(0, _update)

    def _update_portfolio(self, cash, val_posizioni):
        def _update():
            self.lbl_cash.configure(text=f"$ {cash:,.2f}")
            self.lbl_pos.configure(text=f"$ {val_posizioni:,.2f}")
            self.lbl_tot.configure(text=f"$ {(cash + val_posizioni):,.2f}")
        self.app.after(0, _update)

    def _get_callbacks(self):
        return {"log": self._log_to_terminal, "portfolio": self._update_portfolio, "running": self._set_running_ui}

    def _get_params(self):
        nome_menu = self.combo_ticker.get().strip()
        tickers_reali = self.watchlist_map.get(nome_menu, nome_menu)
        
        return {
            "ticker": tickers_reali or "EURUSD", 
            "budget": self.entry_capitale.get().strip() or "100",
            "target": self.entry_target.get().strip() or "50",
            "loss": self.entry_loss.get().strip() or "30",
            "tg_chat": self.entry_tg_chat.get().strip() # Ora prende SOLO la chat ID
        }

    def _change_mode(self, value):
        self._log_to_terminal(f"Modalità cambiata in: {value}")
        if value != "[ Backtest ]":
            gestisci_connessione("LIVE", self._get_callbacks(), self._get_params())
        else:
            spegni_tutto()

    def _set_running_ui(self, is_trading):
        def _update():
            if is_trading:
                self.btn_start.configure(state="disabled", fg_color="#064e3b")
                self.btn_stop.configure(state="normal", fg_color=C_RED_DARK)
            else:
                self.btn_start.configure(state="normal", fg_color=C_GREEN_DARK)
                self.btn_stop.configure(state="disabled", fg_color="#7f1d1d")
        self.app.after(0, _update)

    def _on_start(self):
        if self.seg_mode.get() == "[ Backtest ]": return
        self._log_to_terminal("Market scan started... Scanning for signals.")
        aggiorna_parametri_e_avvia(self._get_params())

    def _on_stop(self):
        self._log_to_terminal("System commanded to halt. Returning to standby.")
        ferma_trading()

    def run(self):
        self.app.mainloop()