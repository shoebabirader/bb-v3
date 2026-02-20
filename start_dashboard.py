#!/usr/bin/env python3
"""
Trading Bot Dashboard Launcher

Cross-platform script to launch both the trading bot and Streamlit dashboard.
Supports command-line options for flexible deployment.
"""

import argparse
import os
import sys
import subprocess
import time
import webbrowser
from pathlib import Path


def check_python_version():
    """Check if Python version is 3.8 or higher."""
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    return True


def check_files_exist():
    """Check if required files exist."""
    required_files = ["main.py", "streamlit_app.py"]
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("ERROR: Required files not found:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nPlease run this script from the project root directory")
        return False
    
    return True


def check_config_exists():
    """Check if config file exists."""
    config_path = Path("config/config.json")
    if not config_path.exists():
        print("WARNING: config/config.json not found")
        print("Please ensure you have configured the bot before starting")
        response = input("Continue anyway? (y/n): ").strip().lower()
        return response == 'y'
    return True


def check_dependencies(install=False):
    """Check if required dependencies are installed."""
    try:
        import streamlit
        return True
    except ImportError:
        print("ERROR: Streamlit is not installed")
        
        if install:
            print("Installing UI dependencies...")
            try:
                subprocess.check_call([
                    sys.executable, "-m", "pip", "install", 
                    "-r", "requirements_ui.txt"
                ])
                print("Dependencies installed successfully")
                return True
            except subprocess.CalledProcessError:
                print("ERROR: Failed to install dependencies")
                return False
        else:
            print("Run with --install-deps to install automatically")
            print("Or manually run: pip install -r requirements_ui.txt")
            return False


def start_bot(bot_script="main.py"):
    """Start the trading bot process."""
    print(f"Starting Trading Bot ({bot_script})...")
    
    try:
        if sys.platform == "win32":
            # Windows: Start in new console window
            process = subprocess.Popen(
                [sys.executable, bot_script],
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # Unix-like: Start in background
            process = subprocess.Popen(
                [sys.executable, bot_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
        
        print(f"✓ Trading Bot started (PID: {process.pid})")
        return process
    
    except Exception as e:
        print(f"ERROR: Failed to start bot: {e}")
        return None


def start_dashboard(port=8501, open_browser=True):
    """Start the Streamlit dashboard."""
    print(f"Starting Streamlit Dashboard on port {port}...")
    
    try:
        cmd = [sys.executable, "-m", "streamlit", "run", "streamlit_app.py"]
        cmd.extend(["--server.port", str(port)])
        cmd.extend(["--server.headless", "true"])
        
        if sys.platform == "win32":
            # Windows: Start in new console window
            process = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE
            )
        else:
            # Unix-like: Start in background
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )
        
        print(f"✓ Streamlit Dashboard started (PID: {process.pid})")
        
        # Wait for Streamlit to start
        time.sleep(5)
        
        # Open browser
        if open_browser:
            url = f"http://localhost:{port}"
            print(f"Opening browser at {url}...")
            webbrowser.open(url)
        
        return process
    
    except Exception as e:
        print(f"ERROR: Failed to start dashboard: {e}")
        return None


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Launch Trading Bot and Streamlit Dashboard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python start_dashboard.py                    # Start both bot and dashboard
  python start_dashboard.py --dashboard-only   # Start only dashboard
  python start_dashboard.py --bot-only         # Start only bot
  python start_dashboard.py --port 8502        # Use custom port
  python start_dashboard.py --install-deps     # Install dependencies first
        """
    )
    
    parser.add_argument(
        "--bot-only",
        action="store_true",
        help="Start only the trading bot"
    )
    
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Start only the Streamlit dashboard"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port for Streamlit dashboard (default: 8501)"
    )
    
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser automatically"
    )
    
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install dependencies before starting"
    )
    
    parser.add_argument(
        "--bot-script",
        default="main.py",
        help="Path to bot script (default: main.py)"
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Trading Bot Dashboard Launcher")
    print("=" * 50)
    print()
    
    # Pre-flight checks
    if not check_python_version():
        return 1
    
    if not check_files_exist():
        return 1
    
    if not args.dashboard_only and not check_config_exists():
        return 1
    
    if not args.bot_only and not check_dependencies(install=args.install_deps):
        return 1
    
    print()
    
    # Start services
    bot_process = None
    dashboard_process = None
    
    try:
        if not args.dashboard_only:
            bot_process = start_bot(args.bot_script)
            if bot_process is None:
                return 1
            time.sleep(3)  # Wait for bot to initialize
        
        if not args.bot_only:
            dashboard_process = start_dashboard(
                port=args.port,
                open_browser=not args.no_browser
            )
            if dashboard_process is None:
                return 1
        
        print()
        print("=" * 50)
        print("Services started successfully!")
        print()
        
        if bot_process:
            print(f"Trading Bot: Running (PID: {bot_process.pid})")
        
        if dashboard_process:
            print(f"Dashboard: http://localhost:{args.port}")
        
        print()
        print("Press Ctrl+C to stop (or close the windows)")
        print("=" * 50)
        print()
        
        # Keep script running
        if not sys.platform == "win32":
            # On Unix-like systems, wait for processes
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nShutting down...")
                if bot_process:
                    bot_process.terminate()
                if dashboard_process:
                    dashboard_process.terminate()
        
        return 0
    
    except KeyboardInterrupt:
        print("\nShutting down...")
        return 0
    
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
