"""Data management for historical and real-time market data."""

from typing import List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
import time
import logging
import threading

from binance.client import Client
from binance.exceptions import BinanceAPIException
from binance import ThreadedWebsocketManager

from src.models import Candle
from src.config import Config
from src.rate_limiter import RateLimiter

# Configure logging
logger = logging.getLogger(__name__)


class DataManager:
    """Manages historical and real-time market data from Binance.
    
    Handles:
    - Fetching historical kline data for backtesting
    - Managing WebSocket connections for real-time data
    - Validating data completeness and detecting gaps
    - Maintaining circular buffers for memory efficiency
    """
    
    def __init__(self, config: Config, client: Optional[Client] = None):
        """Initialize DataManager.
        
        Args:
            config: Configuration object
            client: Binance API client (optional, created if not provided)
        """
        self.config = config
        self.client = client
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            max_requests_per_minute=config.api_rate_limit_per_minute,
            warning_threshold=0.7  # Start warning at 70% capacity
        )
        logger.info(f"Rate limiter initialized: {config.api_rate_limit_per_minute} requests/min")
        
        # Multi-symbol support: Store buffers per symbol
        # Structure: {symbol: {timeframe: deque}}
        self._symbol_buffers = {}
        
        # Legacy single-symbol buffers (for backward compatibility)
        self.candles_5m: deque = deque(maxlen=500)
        self.candles_15m: deque = deque(maxlen=500)
        self.candles_1h: deque = deque(maxlen=500)
        self.candles_4h: deque = deque(maxlen=500)
        
        # Cache for fetched data to avoid redundant API calls
        # Structure: {symbol: {timeframe: {'data': List[Candle], 'timestamp': float}}}
        self._data_cache = {}
        self._cache_ttl_seconds = 60  # Cache valid for 60 seconds
        
        # WebSocket manager
        self.websocket_manager: Optional[ThreadedWebsocketManager] = None
        self._ws_connected = False
        self._ws_reconnect_attempts = 0
        self._max_reconnect_attempts = 5
        self._reconnect_lock = threading.Lock()
        
        # WebSocket stream keys per symbol
        # Structure: {symbol: {timeframe: stream_key}}
        self._stream_keys = {}
        
        # Callback for candle updates (can be set externally)
        self.on_candle_callback: Optional[Callable[[Candle, str], None]] = None
    
    def _get_symbol_buffer(self, symbol: str, timeframe: str) -> deque:
        """Get or create buffer for a specific symbol and timeframe.
        
        Args:
            symbol: Trading symbol (e.g., "XRPUSDT")
            timeframe: Timeframe (e.g., "15m")
            
        Returns:
            Deque buffer for the symbol/timeframe combination
        """
        if symbol not in self._symbol_buffers:
            self._symbol_buffers[symbol] = {}
        
        if timeframe not in self._symbol_buffers[symbol]:
            self._symbol_buffers[symbol][timeframe] = deque(maxlen=500)
        
        return self._symbol_buffers[symbol][timeframe]
    
    def fetch_historical_data(self, days: int = 90, timeframe: str = "15m", use_cache: bool = True, symbol: Optional[str] = None) -> List[Candle]:
        """Fetch historical kline data from Binance.
        
        Args:
            days: Number of days of historical data to fetch
            timeframe: Timeframe for candles (e.g., "5m", "15m", "1h", "4h")
            use_cache: Whether to use cached data if available
            symbol: Trading symbol (uses config.symbol if not provided)
            
        Returns:
            List of Candle objects sorted by timestamp
            
        Raises:
            ValueError: If data contains gaps or is incomplete
            BinanceAPIException: If API request fails
        """
        if self.client is None:
            raise ValueError("Binance client not initialized. Cannot fetch historical data.")
        
        # Use provided symbol or fall back to config symbol
        fetch_symbol = symbol if symbol is not None else self.config.symbol
        
        # Check cache if enabled
        if use_cache and self._is_cache_valid(fetch_symbol, timeframe):
            logger.debug(f"Using cached data for {fetch_symbol} {timeframe}")
            return self._data_cache[fetch_symbol][timeframe]['data']
        
        # Calculate start time
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        # Convert to milliseconds
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)
        
        # Fetch klines from Binance
        try:
            # Acquire rate limit permission before making API call
            if not self.rate_limiter.acquire(timeout=30.0):
                raise BinanceAPIException("Rate limit timeout - too many requests")
            
            logger.debug(f"Fetching historical data: {fetch_symbol} {timeframe} ({days} days)")
            
            # Use futures_klines for Futures API
            klines = self.client.futures_klines(
                symbol=fetch_symbol,
                interval=self._convert_timeframe_to_binance_interval(timeframe),
                startTime=start_ms,
                endTime=end_ms
            )
            
            logger.debug(f"Received {len(klines)} klines for {fetch_symbol} {timeframe}")
            
        except BinanceAPIException as e:
            # Re-raise the original exception instead of creating a new one incorrectly
            logger.error(f"Failed to fetch historical data for {fetch_symbol}: {e}")
            raise
        
        # Convert to Candle objects
        candles = []
        for kline in klines:
            candle = Candle(
                timestamp=int(kline[0]),
                open=float(kline[1]),
                high=float(kline[2]),
                low=float(kline[3]),
                close=float(kline[4]),
                volume=float(kline[5])
            )
            candles.append(candle)
        
        # Validate data completeness
        self._validate_data_completeness(candles, timeframe)
        
        # Store in symbol-specific buffer
        buffer = self._get_symbol_buffer(fetch_symbol, timeframe)
        buffer.extend(candles)
        
        # Also store in legacy buffers if this is the primary symbol
        if fetch_symbol == self.config.symbol:
            if timeframe == "5m":
                self.candles_5m.extend(candles)
            elif timeframe == "15m":
                self.candles_15m.extend(candles)
            elif timeframe == "1h":
                self.candles_1h.extend(candles)
            elif timeframe == "4h":
                self.candles_4h.extend(candles)
        
        # Update cache
        self._update_cache(fetch_symbol, timeframe, candles)
        
        return candles
    
    def _convert_timeframe_to_binance_interval(self, timeframe: str) -> str:
        """Convert timeframe string to Binance interval constant.
        
        Args:
            timeframe: Timeframe string (e.g., "15m", "1h")
            
        Returns:
            Binance interval constant (e.g., Client.KLINE_INTERVAL_15MINUTE)
        """
        interval_map = {
            "1m": Client.KLINE_INTERVAL_1MINUTE,
            "3m": Client.KLINE_INTERVAL_3MINUTE,
            "5m": Client.KLINE_INTERVAL_5MINUTE,
            "15m": Client.KLINE_INTERVAL_15MINUTE,
            "30m": Client.KLINE_INTERVAL_30MINUTE,
            "1h": Client.KLINE_INTERVAL_1HOUR,
            "2h": Client.KLINE_INTERVAL_2HOUR,
            "4h": Client.KLINE_INTERVAL_4HOUR,
            "6h": Client.KLINE_INTERVAL_6HOUR,
            "8h": Client.KLINE_INTERVAL_8HOUR,
            "12h": Client.KLINE_INTERVAL_12HOUR,
            "1d": Client.KLINE_INTERVAL_1DAY,
        }
        
        if timeframe not in interval_map:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        return interval_map[timeframe]
    
    def _is_cache_valid(self, symbol: str, timeframe: str) -> bool:
        """Check if cached data is still valid.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe to check
            
        Returns:
            True if cache is valid, False otherwise
        """
        if symbol not in self._data_cache:
            return False
        
        if timeframe not in self._data_cache[symbol]:
            return False
        
        cache_entry = self._data_cache[symbol][timeframe]
        if cache_entry['data'] is None:
            return False
        
        # Check if cache has expired
        current_time = time.time()
        cache_age = current_time - cache_entry['timestamp']
        
        return cache_age < self._cache_ttl_seconds
    
    def _update_cache(self, symbol: str, timeframe: str, data: List[Candle]) -> None:
        """Update cache with new data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            data: Candle data to cache
        """
        if symbol not in self._data_cache:
            self._data_cache[symbol] = {}
        
        self._data_cache[symbol][timeframe] = {
            'data': data,
            'timestamp': time.time()
        }
    
    def clear_cache(self, timeframe: Optional[str] = None) -> None:
        """Clear cached data.
        
        Args:
            timeframe: Specific timeframe to clear, or None to clear all
        """
        if timeframe is None:
            # Clear all caches
            for tf in self._data_cache:
                self._data_cache[tf] = {'data': None, 'timestamp': 0}
            logger.debug("Cleared all data caches")
        elif timeframe in self._data_cache:
            self._data_cache[timeframe] = {'data': None, 'timestamp': 0}
            logger.debug(f"Cleared cache for {timeframe}")
    
    def get_synchronized_candles(self, reference_timestamp: int, timeframes: Optional[List[str]] = None) -> dict:
        """Get candles from all timeframes synchronized to a reference timestamp.
        
        This method ensures all timeframes are aligned by finding the candle that
        contains or is closest to the reference timestamp for each timeframe.
        
        Args:
            reference_timestamp: Reference timestamp in milliseconds
            timeframes: List of timeframes to synchronize (default: all supported)
            
        Returns:
            Dictionary mapping timeframe to synchronized Candle, or None if not available
        """
        if timeframes is None:
            timeframes = ['5m', '15m', '1h', '4h']
        
        result = {}
        
        for tf in timeframes:
            candle = self._find_candle_at_timestamp(tf, reference_timestamp)
            result[tf] = candle
        
        return result
    
    def _find_candle_at_timestamp(self, timeframe: str, timestamp: int) -> Optional[Candle]:
        """Find the candle that contains or is closest to the given timestamp.
        
        Args:
            timeframe: Timeframe to search
            timestamp: Target timestamp in milliseconds
            
        Returns:
            Candle object or None if not found
        """
        # Get the appropriate buffer
        if timeframe == '5m':
            buffer = self.candles_5m
        elif timeframe == '15m':
            buffer = self.candles_15m
        elif timeframe == '1h':
            buffer = self.candles_1h
        elif timeframe == '4h':
            buffer = self.candles_4h
        else:
            return None
        
        if len(buffer) == 0:
            return None
        
        # Get timeframe duration
        tf_ms = self._get_timeframe_milliseconds(timeframe)
        
        # Find the candle that contains this timestamp
        # A candle at timestamp T covers the period [T, T + tf_ms)
        best_candle = None
        min_distance = float('inf')
        
        for candle in buffer:
            # Check if timestamp falls within this candle's period
            if candle.timestamp <= timestamp < candle.timestamp + tf_ms:
                return candle
            
            # Track closest candle as fallback
            distance = abs(candle.timestamp - timestamp)
            if distance < min_distance:
                min_distance = distance
                best_candle = candle
        
        # Return closest candle if exact match not found
        return best_candle
    
    def is_data_stale(self, timeframe: str, max_age_seconds: Optional[int] = None) -> bool:
        """Check if data for a timeframe is stale.
        
        Args:
            timeframe: Timeframe to check
            max_age_seconds: Maximum age in seconds (default: 2x timeframe period)
            
        Returns:
            True if data is stale or missing, False otherwise
        """
        # Get the appropriate buffer
        if timeframe == '5m':
            buffer = self.candles_5m
        elif timeframe == '15m':
            buffer = self.candles_15m
        elif timeframe == '1h':
            buffer = self.candles_1h
        elif timeframe == '4h':
            buffer = self.candles_4h
        else:
            return True  # Unknown timeframe is considered stale
        
        if len(buffer) == 0:
            return True  # No data is stale
        
        # Get the most recent candle
        latest_candle = buffer[-1]
        
        # Calculate age of latest candle
        current_time_ms = int(time.time() * 1000)
        age_ms = current_time_ms - latest_candle.timestamp
        
        # Determine max allowed age
        if max_age_seconds is None:
            # Default: 2x the timeframe period
            tf_ms = self._get_timeframe_milliseconds(timeframe)
            max_age_ms = tf_ms * 2
        else:
            max_age_ms = max_age_seconds * 1000
        
        return age_ms > max_age_ms
    
    def get_data_status(self) -> dict:
        """Get status of all timeframe data buffers.
        
        Returns:
            Dictionary with status information for each timeframe
        """
        status = {}
        
        for tf in ['5m', '15m', '1h', '4h']:
            if tf == '5m':
                buffer = self.candles_5m
            elif tf == '15m':
                buffer = self.candles_15m
            elif tf == '1h':
                buffer = self.candles_1h
            else:  # '4h'
                buffer = self.candles_4h
            
            if len(buffer) == 0:
                status[tf] = {
                    'available': False,
                    'count': 0,
                    'stale': True,
                    'latest_timestamp': None
                }
            else:
                latest = buffer[-1]
                status[tf] = {
                    'available': True,
                    'count': len(buffer),
                    'stale': self.is_data_stale(tf),
                    'latest_timestamp': latest.timestamp,
                    'latest_close': latest.close
                }
        
        return status
    
    def _get_timeframe_milliseconds(self, timeframe: str) -> int:
        """Get the duration of a timeframe in milliseconds.
        
        Args:
            timeframe: Timeframe string (e.g., "15m", "1h")
            
        Returns:
            Duration in milliseconds
        """
        timeframe_ms = {
            "1m": 60 * 1000,
            "3m": 3 * 60 * 1000,
            "5m": 5 * 60 * 1000,
            "15m": 15 * 60 * 1000,
            "30m": 30 * 60 * 1000,
            "1h": 60 * 60 * 1000,
            "2h": 2 * 60 * 60 * 1000,
            "4h": 4 * 60 * 60 * 1000,
            "6h": 6 * 60 * 60 * 1000,
            "8h": 8 * 60 * 60 * 1000,
            "12h": 12 * 60 * 60 * 1000,
            "1d": 24 * 60 * 60 * 1000,
        }
        
        if timeframe not in timeframe_ms:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        return timeframe_ms[timeframe]
    
    def _validate_data_completeness(self, candles: List[Candle], timeframe: str) -> None:
        """Validate that candle data contains no gaps.
        
        Args:
            candles: List of Candle objects to validate
            timeframe: Expected timeframe between candles
            
        Raises:
            ValueError: If data contains gaps larger than the timeframe interval
        """
        if len(candles) < 2:
            return  # Not enough data to validate gaps
        
        expected_interval_ms = self._get_timeframe_milliseconds(timeframe)
        
        # Allow 10% tolerance for timing variations
        max_allowed_gap = expected_interval_ms * 1.1
        
        gaps = []
        for i in range(1, len(candles)):
            time_diff = candles[i].timestamp - candles[i-1].timestamp
            
            if time_diff > max_allowed_gap:
                gaps.append({
                    'index': i,
                    'prev_timestamp': candles[i-1].timestamp,
                    'curr_timestamp': candles[i].timestamp,
                    'gap_ms': time_diff,
                    'expected_ms': expected_interval_ms
                })
        
        if gaps:
            gap_details = "\n".join([
                f"  Gap at index {g['index']}: {g['gap_ms']}ms "
                f"(expected {g['expected_ms']}ms) between "
                f"{datetime.fromtimestamp(g['prev_timestamp']/1000)} and "
                f"{datetime.fromtimestamp(g['curr_timestamp']/1000)}"
                for g in gaps[:5]  # Show first 5 gaps
            ])
            
            raise ValueError(
                f"Historical data contains {len(gaps)} gap(s) larger than "
                f"the {timeframe} interval:\n{gap_details}"
            )
    
    def get_latest_candles(self, timeframe: str, count: int, symbol: Optional[str] = None) -> List[Candle]:
        """Retrieve most recent candles for indicator calculation.
        
        Args:
            timeframe: Timeframe to retrieve ("5m", "15m", "1h", or "4h")
            count: Number of candles to retrieve
            symbol: Trading symbol (uses config.symbol if not provided)
            
        Returns:
            List of most recent Candle objects
        """
        # Use provided symbol or fall back to config symbol
        fetch_symbol = symbol if symbol is not None else self.config.symbol
        
        # Try to get from symbol-specific buffer first
        if fetch_symbol in self._symbol_buffers and timeframe in self._symbol_buffers[fetch_symbol]:
            buffer = self._symbol_buffers[fetch_symbol][timeframe]
            result_len = min(len(buffer), count)
            logger.info(f"get_latest_candles: {fetch_symbol} {timeframe} - found in symbol_buffers, returning {result_len} candles")
        else:
            # Fall back to legacy buffers for primary symbol
            if fetch_symbol == self.config.symbol:
                if timeframe == "5m":
                    buffer = self.candles_5m
                elif timeframe == "15m":
                    buffer = self.candles_15m
                elif timeframe == "1h":
                    buffer = self.candles_1h
                elif timeframe == "4h":
                    buffer = self.candles_4h
                else:
                    raise ValueError(f"Unsupported timeframe: {timeframe}")
                result_len = min(len(buffer), count)
                logger.info(f"get_latest_candles: {fetch_symbol} {timeframe} - found in legacy buffers, returning {result_len} candles")
            else:
                # No data available for this symbol/timeframe
                logger.warning(f"get_latest_candles: {fetch_symbol} {timeframe} - NOT FOUND in symbol_buffers, returning empty list")
                logger.warning(f"  Available symbols in _symbol_buffers: {list(self._symbol_buffers.keys())}")
                if fetch_symbol in self._symbol_buffers:
                    logger.warning(f"  Available timeframes for {fetch_symbol}: {list(self._symbol_buffers[fetch_symbol].keys())}")
                return []
        
        # Return last 'count' candles
        if len(buffer) < count:
            return list(buffer)
        else:
            return list(buffer)[-count:]
    
    def start_websocket_streams(self, symbol: Optional[str] = None):
        """Initialize WebSocket connections for real-time data.
        
        Establishes WebSocket connections for 5m, 15m, 1h, and 4h kline streams.
        Automatically handles connection management and reconnection.
        
        Args:
            symbol: Symbol to start streams for. If None, uses config.symbol
        
        Raises:
            ValueError: If Binance client is not initialized
        """
        if self.client is None:
            raise ValueError("Binance client not initialized. Cannot start WebSocket streams.")
        
        # Use provided symbol or fall back to config.symbol
        stream_symbol = symbol if symbol is not None else self.config.symbol
        
        # Initialize WebSocket manager if not already created
        if self.websocket_manager is None:
            self.websocket_manager = ThreadedWebsocketManager(
                api_key=self.config.api_key,
                api_secret=self.config.api_secret
            )
            self.websocket_manager.start()
            logger.info("WebSocket manager started")
        
        # Initialize stream keys for this symbol if not exists
        if stream_symbol not in self._stream_keys:
            self._stream_keys[stream_symbol] = {}
        
        # Start 5m kline stream
        self._stream_keys[stream_symbol]['5m'] = self.websocket_manager.start_kline_socket(
            callback=lambda msg: self._handle_kline_message(msg, '5m'),
            symbol=stream_symbol.lower(),
            interval=Client.KLINE_INTERVAL_5MINUTE
        )
        logger.info(f"Started 5m kline stream for {stream_symbol}")
        
        # Start 15m kline stream
        self._stream_keys[stream_symbol]['15m'] = self.websocket_manager.start_kline_socket(
            callback=lambda msg: self._handle_kline_message(msg, '15m'),
            symbol=stream_symbol.lower(),
            interval=Client.KLINE_INTERVAL_15MINUTE
        )
        logger.info(f"Started 15m kline stream for {stream_symbol}")
        
        # Start 1h kline stream
        self._stream_keys[stream_symbol]['1h'] = self.websocket_manager.start_kline_socket(
            callback=lambda msg: self._handle_kline_message(msg, '1h'),
            symbol=stream_symbol.lower(),
            interval=Client.KLINE_INTERVAL_1HOUR
        )
        logger.info(f"Started 1h kline stream for {stream_symbol}")
        
        # Start 4h kline stream
        self._stream_keys[stream_symbol]['4h'] = self.websocket_manager.start_kline_socket(
            callback=lambda msg: self._handle_kline_message(msg, '4h'),
            symbol=stream_symbol.lower(),
            interval=Client.KLINE_INTERVAL_4HOUR
        )
        logger.info(f"Started 4h kline stream for {stream_symbol}")
        
        self._ws_connected = True
        self._ws_reconnect_attempts = 0
    
    def _handle_kline_message(self, msg: dict, timeframe: str):
        """Handle incoming kline WebSocket message.
        
        Args:
            msg: WebSocket message containing kline data
            timeframe: Timeframe of the kline ('15m' or '1h')
        """
        try:
            # Check if message contains error
            if 'e' in msg and msg['e'] == 'error':
                logger.error(f"WebSocket error for {timeframe}: {msg}")
                self._handle_websocket_disconnect()
                return
            
            # Extract kline data
            if 'k' not in msg:
                logger.warning(f"Received message without kline data: {msg}")
                return
            
            kline = msg['k']
            
            # Extract symbol from message
            symbol = kline.get('s', self.config.symbol).upper()
            
            # Only process closed candles
            if not kline['x']:
                return
            
            # Create Candle object
            candle = Candle(
                timestamp=int(kline['t']),
                open=float(kline['o']),
                high=float(kline['h']),
                low=float(kline['l']),
                close=float(kline['c']),
                volume=float(kline['v'])
            )
            
            # Update candle buffer for this symbol
            self.on_candle_update(candle, timeframe, symbol)
            
        except Exception as e:
            logger.error(f"Error processing kline message for {timeframe}: {e}")
    
    def _handle_websocket_disconnect(self):
        """Handle WebSocket disconnection event.
        
        Triggers reconnection logic with exponential backoff.
        """
        logger.warning("WebSocket disconnection detected")
        self._ws_connected = False
        self.reconnect_websocket()
    
    def on_candle_update(self, candle: Candle, timeframe: str, symbol: Optional[str] = None):
        """Callback for new candle data from WebSocket.
        
        Updates the appropriate candle buffer and calls external callback if set.
        
        Args:
            candle: New candle data
            timeframe: Timeframe of the candle ('5m', '15m', '1h', or '4h')
            symbol: Symbol for the candle. If None, uses config.symbol
        """
        # Use provided symbol or fall back to config.symbol
        candle_symbol = symbol if symbol is not None else self.config.symbol
        
        # Add to symbol-specific buffer
        buffer = self._get_symbol_buffer(candle_symbol, timeframe)
        buffer.append(candle)
        logger.debug(f"Added {timeframe} candle for {candle_symbol}: timestamp={candle.timestamp}, close={candle.close}")
        
        # Also update legacy buffers for backward compatibility (only for config.symbol)
        if candle_symbol == self.config.symbol:
            if timeframe == '5m':
                self.candles_5m.append(candle)
            elif timeframe == '15m':
                self.candles_15m.append(candle)
            elif timeframe == '1h':
                self.candles_1h.append(candle)
            elif timeframe == '4h':
                self.candles_4h.append(candle)
        
        # Call external callback if set
        if self.on_candle_callback is not None:
            try:
                self.on_candle_callback(candle, timeframe)
            except Exception as e:
                logger.error(f"Error in candle callback: {e}")
    
    def reconnect_websocket(self):
        """Handle WebSocket reconnection with exponential backoff.
        
        Attempts to reconnect up to 5 times with exponentially increasing delays.
        Uses thread lock to prevent multiple simultaneous reconnection attempts.
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        with self._reconnect_lock:
            # Check if already connected
            if self._ws_connected:
                logger.info("WebSocket already connected, skipping reconnection")
                return True
            
            # Check if max attempts reached
            if self._ws_reconnect_attempts >= self._max_reconnect_attempts:
                logger.error(f"Max reconnection attempts ({self._max_reconnect_attempts}) reached. Giving up.")
                return False
            
            self._ws_reconnect_attempts += 1
            
            # Calculate exponential backoff delay: 2^(attempt-1) seconds
            # Attempt 1: 1s, Attempt 2: 2s, Attempt 3: 4s, Attempt 4: 8s, Attempt 5: 16s
            delay = 2 ** (self._ws_reconnect_attempts - 1)
            
            logger.info(
                f"Reconnection attempt {self._ws_reconnect_attempts}/{self._max_reconnect_attempts} "
                f"after {delay}s delay"
            )
            
            # Wait with exponential backoff
            time.sleep(delay)
            
            try:
                # Stop existing WebSocket manager if it exists
                if self.websocket_manager is not None:
                    try:
                        self.websocket_manager.stop()
                        logger.info("Stopped existing WebSocket manager")
                    except Exception as e:
                        logger.warning(f"Error stopping WebSocket manager: {e}")
                    
                    self.websocket_manager = None
                
                # Restart WebSocket streams
                self.start_websocket_streams()
                
                logger.info("WebSocket reconnection successful")
                return True
                
            except Exception as e:
                logger.error(f"Reconnection attempt {self._ws_reconnect_attempts} failed: {e}")
                
                # If not at max attempts, try again
                if self._ws_reconnect_attempts < self._max_reconnect_attempts:
                    return self.reconnect_websocket()
                else:
                    return False
    
    def stop_websocket_streams(self):
        """Stop WebSocket streams and clean up resources.
        
        Should be called during graceful shutdown.
        """
        if self.websocket_manager is not None:
            try:
                self.websocket_manager.stop()
                logger.info("WebSocket streams stopped")
            except Exception as e:
                logger.error(f"Error stopping WebSocket streams: {e}")
            finally:
                self.websocket_manager = None
                self._ws_connected = False
    
    def is_websocket_connected(self) -> bool:
        """Check if WebSocket is currently connected.
        
        Returns:
            bool: True if connected, False otherwise
        """
        return self._ws_connected
    
    def get_reconnect_attempts(self) -> int:
        """Get the current number of reconnection attempts.
        
        Returns:
            int: Number of reconnection attempts made
        """
        return self._ws_reconnect_attempts
    
    def cleanup_old_data(self, lookback_days: int = 7):
        """Remove data older than the specified lookback period.
        
        This method removes candles older than the lookback period to free memory.
        Should be called periodically (e.g., every 6 hours).
        
        Args:
            lookback_days: Number of days to keep (default: 7)
        """
        cutoff_timestamp = int((time.time() - (lookback_days * 24 * 60 * 60)) * 1000)
        
        removed_counts = {}
        
        # Clean up each timeframe buffer
        for timeframe, buffer_name in [
            ('5m', 'candles_5m'),
            ('15m', 'candles_15m'),
            ('1h', 'candles_1h'),
            ('4h', 'candles_4h')
        ]:
            buffer = getattr(self, buffer_name)
            original_count = len(buffer)
            
            # Remove old candles
            # Since deque doesn't support efficient filtering, we'll recreate it
            new_buffer = deque(
                (candle for candle in buffer if candle.timestamp >= cutoff_timestamp),
                maxlen=buffer.maxlen
            )
            
            setattr(self, buffer_name, new_buffer)
            removed_count = original_count - len(new_buffer)
            removed_counts[timeframe] = removed_count
            
            if removed_count > 0:
                logger.info(
                    f"Cleaned up {removed_count} old candles from {timeframe} buffer "
                    f"(kept {len(new_buffer)} candles)"
                )
        
        # Clear old cache entries
        self.clear_cache()
        
        total_removed = sum(removed_counts.values())
        logger.info(
            f"Data cleanup complete: removed {total_removed} total candles "
            f"older than {lookback_days} days"
        )
        
        return removed_counts
    
    def get_memory_usage_estimate(self) -> dict:
        """Estimate memory usage of candle buffers.
        
        Returns:
            Dictionary with memory usage estimates for each timeframe
        """
        import sys
        
        usage = {}
        total_bytes = 0
        
        for timeframe, buffer_name in [
            ('5m', 'candles_5m'),
            ('15m', 'candles_15m'),
            ('1h', 'candles_1h'),
            ('4h', 'candles_4h')
        ]:
            buffer = getattr(self, buffer_name)
            
            # Estimate size: each Candle object is roughly 100 bytes
            # (6 floats × 8 bytes + overhead)
            estimated_bytes = len(buffer) * 100
            total_bytes += estimated_bytes
            
            usage[timeframe] = {
                'candle_count': len(buffer),
                'estimated_bytes': estimated_bytes,
                'estimated_mb': estimated_bytes / (1024 * 1024)
            }
        
        usage['total'] = {
            'estimated_bytes': total_bytes,
            'estimated_mb': total_bytes / (1024 * 1024)
        }
        
        return usage
