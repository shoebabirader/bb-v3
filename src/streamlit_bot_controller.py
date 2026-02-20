"""
Streamlit Bot Controller

Manages the trading bot process lifecycle (start/stop/restart).
Provides emergency controls for closing positions.
"""

import sys
import time
import psutil
import subprocess
from typing import Tuple


class BotController:
    """Controls the trading bot process."""
    
    def __init__(self, bot_script: str = "main.py"):
        """
        Initialize the bot controller.
        
        Args:
            bot_script: Path to the bot's main script
        """
        self.bot_script = bot_script
        self.process = None
    
    def start_bot(self) -> Tuple[bool, str]:
        """
        Start the trading bot process.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if self._is_running():
            return False, "Bot is already running"
        
        try:
            self.process = subprocess.Popen(
                [sys.executable, self.bot_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == 'win32' else 0
            )
            time.sleep(2)  # Wait for startup
            
            if self.process.poll() is None:
                return True, "Bot started successfully"
            else:
                stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                return False, f"Bot failed to start: {stderr[:200]}"
        except Exception as e:
            return False, f"Error starting bot: {str(e)}"
    
    def stop_bot(self) -> Tuple[bool, str]:
        """
        Stop the trading bot process gracefully.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self._is_running():
            return False, "Bot is not running"
        
        try:
            # Find and terminate the process
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if cmdline and len(cmdline) > 0:
                        cmdline_str = ' '.join(str(c) for c in cmdline)
                        if 'python' in cmdline_str.lower() and 'main.py' in cmdline_str:
                            proc.terminate()
                            try:
                                proc.wait(timeout=10)
                            except psutil.TimeoutExpired:
                                proc.kill()
                            return True, "Bot stopped successfully"
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            return False, "Bot process not found"
        except Exception as e:
            return False, f"Error stopping bot: {str(e)}"
    
    def restart_bot(self) -> Tuple[bool, str]:
        """
        Restart the trading bot process.
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        # Stop the bot first
        if self._is_running():
            success, message = self.stop_bot()
            if not success:
                return False, f"Failed to stop bot: {message}"
            time.sleep(2)  # Wait for clean shutdown
        
        # Start the bot
        return self.start_bot()
    
    def emergency_close_all(self, require_confirmation: bool = True) -> Tuple[bool, str]:
        """
        Close all open positions immediately.
        
        Reads open positions from binance_results.json and closes them
        via the Binance API. This is an emergency function that should
        be used with caution.
        
        Args:
            require_confirmation: If True, caller must handle confirmation
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        import json
        import os
        from binance.client import Client
        from src.config import Config
        
        try:
            # Load configuration to get API credentials
            config_path = "config/config.json"
            if not os.path.exists(config_path):
                return False, "Configuration file not found"
            
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            api_key = config_data.get('api_key', '')
            api_secret = config_data.get('api_secret', '')
            
            if not api_key or not api_secret:
                return False, "API credentials not configured"
            
            # Initialize Binance client
            client = Client(api_key, api_secret)
            
            # Get open positions from results file
            results_path = "binance_results.json"
            if not os.path.exists(results_path):
                return False, "No positions data found"
            
            with open(results_path, 'r') as f:
                results = json.load(f)
            
            open_positions = results.get('open_positions', [])
            
            if not open_positions:
                return True, "No open positions to close"
            
            # Close each position
            closed_count = 0
            errors = []
            
            for position in open_positions:
                try:
                    symbol = position.get('symbol')
                    side = position.get('side')
                    quantity = position.get('quantity')
                    
                    if not all([symbol, side, quantity]):
                        errors.append(f"Invalid position data: {position}")
                        continue
                    
                    # Determine order side (opposite of position side)
                    order_side = 'SELL' if side == 'LONG' else 'BUY'
                    
                    # Place market order to close position
                    order = client.futures_create_order(
                        symbol=symbol,
                        side=order_side,
                        type='MARKET',
                        quantity=quantity,
                        reduceOnly=True
                    )
                    
                    closed_count += 1
                    
                except Exception as e:
                    errors.append(f"Failed to close {symbol}: {str(e)}")
            
            # Build result message
            if closed_count == len(open_positions):
                return True, f"Successfully closed {closed_count} position(s)"
            elif closed_count > 0:
                error_msg = "; ".join(errors[:3])  # Limit error details
                return True, f"Closed {closed_count}/{len(open_positions)} positions. Errors: {error_msg}"
            else:
                error_msg = "; ".join(errors[:3])
                return False, f"Failed to close positions: {error_msg}"
                
        except Exception as e:
            return False, f"Emergency close failed: {str(e)}"
    
    def _is_running(self) -> bool:
        """
        Check if bot is currently running.
        
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
