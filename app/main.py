"""
Main application entry point for the QUANT AI TERMINAL.

Initializes logging, launches the CustomTkinter user interface, 
and automatically spins up the Streamlit Web Dashboard in the background.
"""

from app.logging_setup import configure_logging
from app.ui import TradingApp
import subprocess
import atexit
import sys

def main():
    """
    Application bootstrap function.
    
    Sequence:
    1. Configure logging
    2. Start Streamlit Web Dashboard as a background process
    3. Initialize UI (CustomTkinter app)
    4. Start event loop
    """
    configure_logging()
    
    # 🌐 AUTOMATIC BACKGROUND START OF THE WEB DASHBOARD
    print("🔄 Spinning up remote Web Dashboard on port 8501...")
    
    # Execute the Streamlit command. "--server.headless true" prevents it from
    # opening a new browser tab on the server every single time the bot starts.
    dashboard_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "web_dashboard.py", "--server.headless", "true"],
        stdout=subprocess.DEVNULL, # Hides verbose Streamlit logs from the main terminal
        stderr=subprocess.DEVNULL
    )
    
    # Security: Ensure the web process is gracefully terminated when the UI (Tkinter) is closed
    atexit.register(lambda: dashboard_process.terminate())
    
    # 🖥️ INITIALIZE THE MAIN GRAPHICAL USER INTERFACE
    app = TradingApp()
    app.run()


if __name__ == "__main__":
    main()