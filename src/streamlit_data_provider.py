"""
Streamlit Data Provider

Provides data to the Streamlit dashboard by reading bot state from files.
Implements caching to avoid excessive file I/O operations.
"""

import json
import time
import psutil
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path


class StreamlitDataProvider:
    """Provides data to Streamlit dashboard by reading bot files."""
    
    def __init__(
        self,
        config_path: str = "config/config.json",
        results_path: str = "binance_results.json",
        logs_dir: str = "logs"
    ):
        """
        Initialize the data provider.
        
        Args:
            config_path: Path to configuration file
            results_path: Path to results file
            logs_dir: Directory containing log files
        """
        self.config_path = config_path
        self.results_path = results_path
        self.logs_dir = logs_dir
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 5  # seconds
    
    def get_config(self) -> Dict:
        """
        Load configuration from config.json.
        
        Returns:
            Dictionary containing configuration data
        """
        return self._read_cached_json(self.config_path, "config")
    
    def get_bot_status(self) -> Dict:
        """
        Get current bot status (running/stopped, last update).
        
        Returns:
            Dictionary with bot status information
        """
        is_running = self._is_bot_process_running()
        last_update = self._get_last_log_timestamp()
        
        return {
            "is_running": is_running,
            "last_update": last_update,
            "status": "Running" if is_running else "Stopped"
        }
    
    def get_balance_and_pnl(self) -> Dict:
        """
        Get current balance and total PnL from results file.
        
        Returns:
            Dictionary with balance and PnL information
        """
        results = self._read_cached_json(self.results_path, "results")
        return {
            "balance": results.get("balance", 0.0),
            "total_pnl": results.get("total_pnl", 0.0),
            "total_pnl_percent": results.get("total_pnl_percent", 0.0)
        }
    
    def get_open_positions(self) -> List[Dict]:
        """
        Get list of open positions.
        
        Returns:
            List of position dictionaries
        """
        results = self._read_cached_json(self.results_path, "results")
        return results.get("open_positions", [])
    
    def get_trade_history(self, limit: int = 20) -> List[Dict]:
        """
        Get recent completed trades from log files.
        
        Args:
            limit: Maximum number of trades to return
            
        Returns:
            List of trade dictionaries
        """
        trades = self._parse_trade_logs()
        return trades[-limit:] if trades else []
    
    def get_market_data(self) -> Dict:
        """
        Get current price and indicator values.
        
        Returns:
            Dictionary with market data and indicators
        """
        results = self._read_cached_json(self.results_path, "results")
        return {
            "current_price": results.get("current_price", 0.0),
            "adx": results.get("adx", 0.0),
            "rvol": results.get("rvol", 0.0),
            "atr": results.get("atr", 0.0),
            "signal": results.get("signal", "NONE")
        }
    
    def _read_cached_json(self, filepath: str, cache_key: str) -> Dict:
        """
        Read JSON file with caching.
        
        Args:
            filepath: Path to JSON file
            cache_key: Key for caching
            
        Returns:
            Dictionary from JSON file or empty dict on error
        """
        now = time.time()
        
        # Check cache
        if cache_key in self._cache:
            cache_age = now - self._cache_timestamps.get(cache_key, 0)
            if cache_age < self._cache_ttl:
                return self._cache[cache_key]
        
        # Read file
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            self._cache[cache_key] = data
            self._cache_timestamps[cache_key] = now
            return data
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            return {}
        except Exception:
            return {}
    
    def _is_bot_process_running(self) -> bool:
        """
        Check if bot process is running.
        
        Returns:
            True if bot is running, False otherwise
        """
        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and len(cmdline) > 0:
                        cmdline_str = ' '.join(str(c) for c in cmdline)
                        if 'python' in cmdline_str.lower() and 'main.py' in cmdline_str:
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
        except Exception:
            pass
        return False
    
    def _get_last_log_timestamp(self) -> Optional[datetime]:
        """
        Get timestamp of most recent log entry.
        
        Returns:
            Datetime of last log entry or None
        """
        try:
            logs_path = Path(self.logs_dir)
            if not logs_path.exists():
                return None
            
            # Find most recent log file
            log_files = list(logs_path.glob("system.log.*"))
            if not log_files:
                return None
            
            most_recent = max(log_files, key=lambda p: p.stat().st_mtime)
            return datetime.fromtimestamp(most_recent.stat().st_mtime)
        except Exception:
            return None
    
    def _parse_trade_logs(self) -> List[Dict]:
        """
        Parse trade history from log files.
        
        Reads from mode-specific log files:
        - trades_paper.log for PAPER mode
        - trades_live.log for LIVE mode
        - trades_backtest.log for BACKTEST mode
        
        Returns:
            List of trade dictionaries
        """
        trades = []
        try:
            logs_path = Path(self.logs_dir)
            if not logs_path.exists():
                return trades
            
            # Get current run mode from config
            config = self.get_config()
            run_mode = config.get("run_mode", "PAPER").lower()
            
            # Parse current and rotated trade log files
            trade_files = []
            
            # Add mode-specific log file first
            mode_log_file = f"trades_{run_mode}.log"
            current_log = logs_path / mode_log_file
            if current_log.exists():
                trade_files.append(current_log)
            
            # Add rotated log files for this mode
            trade_files.extend(sorted(logs_path.glob(f"{mode_log_file}.*")))
            
            # Fallback to generic trades.log if mode-specific doesn't exist
            if not trade_files:
                generic_log = logs_path / "trades.log"
                if generic_log.exists():
                    trade_files.append(generic_log)
                trade_files.extend(sorted(logs_path.glob("trades.log.*")))
            
            for trade_file in trade_files:
                try:
                    with open(trade_file, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            # Parse trade entries from log
                            # Format: YYYY-MM-DD HH:MM:SS - trading_bot.trades - INFO - TRADE_EXECUTED: {json}
                            if "TRADE_EXECUTED:" in line:
                                try:
                                    # Extract JSON part after "TRADE_EXECUTED: "
                                    json_start = line.find("TRADE_EXECUTED:") + len("TRADE_EXECUTED:")
                                    json_str = line[json_start:].strip()
                                    trade_data = json.loads(json_str)
                                    trades.append(trade_data)
                                except (json.JSONDecodeError, ValueError):
                                    # Skip malformed entries
                                    continue
                except Exception:
                    continue
        except Exception:
            pass
        
        return trades
