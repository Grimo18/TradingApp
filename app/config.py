"""
Centralized configuration management for the QUANT AI TERMINAL v3 (Institutional Grade).

This module defines all UI styling constants, color palettes, and application-level
parameters in a single source of truth for consistency across the application.
"""

# Application UI Configuration
APP_TITLE = "QUANT AI TERMINAL"
APP_SIZE = "1150x850"
APP_MIN_SIZE = (1000, 700)

APPEARANCE_MODE = "dark"
COLOR_THEME = "dark-blue"

# Professional Color Palette (Ultra-Modern, Flat Design - No Borders)
# Chosen for institutional trading environments with minimal visual distraction
COLOR_BG = "#09090b"          # Ultra-dark background (almost black)
COLOR_PANEL = "#18181b"       # Base panel layer
COLOR_HEADER = "#09090b"      # Header background
COLOR_CARD = "#27272a"        # Card container (slight elevated contrast)
COLOR_ACCENT = "#0ea5e9"      # Sky blue accent (primary action color)
COLOR_ACCENT_HOVER = "#0284c7"  # Darker sky blue (hover state)
COLOR_SUCCESS = "#10b981"     # Emerald green (positive P&L, buy signals)
COLOR_ERROR = "#f43f5e"       # Rose red (negative P&L, sell signals)
COLOR_WARNING = "#f59e0b"     # Amber (alerts, warnings)
COLOR_TEXT_SUBTLE = "#a1a1aa" # Light gray (primary text)
COLOR_TEXT_MUTED = "#71717a"  # Muted gray (secondary text)
COLOR_CHART_LINE = "#2dd4bf"  # Teal (chart lines, data visualization)

# Terminal/Console Styling (Hacker aesthetic for live trading logs)
COLOR_TERM_BG = "#000000"     # Pure black terminal background
COLOR_TERM_TEXT = "#10b981"   # Emerald green text (classic CRT look)