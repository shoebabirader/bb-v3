"""Scaled Take Profit Manager for progressive profit-taking strategy.

This module implements a scaled (partial) take profit strategy that progressively
locks in profits at multiple price levels while letting winning positions run.
"""

from typing import Optional, Dict, List
from binance.client import Client

from src.config import Config
from src.models import Position, PartialCloseAction, PartialCloseResult, TPStatus
from src.logger import TradingLogger


class ScaledTakeProfitManager:
    """Manages scaled take profit execution for trading positions.
    
    This class tracks which TP levels have been hit for each position,
    calculates partial close quantities, executes partial closes via Binance API,
    and updates the stop loss ladder as TP levels are reached.
    
    Attributes:
        config: Configuration object with scaled TP settings
        client: Binance API client (optional, None for backtest mode)
        logger: Logger instance for tracking TP actions
        _tp_tracking: Dictionary tracking TP status by symbol
    """
    
    def __init__(self, config: Config, client: Optional[Client] = None):
        """Initialize the Scaled Take Profit Manager.
        
        Args:
            config: Configuration object containing scaled TP parameters
            client: Binance API client (None for backtest mode)
        """
        self.config = config
        self.client = client
        self.logger = TradingLogger(log_dir="logs", config=config)
        self._tp_tracking: Dict[str, TPStatus] = {}
        
        # Validate and log configuration (Requirement 7.5)
        config_errors = self._validate_configuration()
        
        # Log initialization with detailed configuration
        if self.config.enable_scaled_take_profit:
            if config_errors:
                # Log configuration errors
                self.logger.log_system_event(
                    f"Scaled TP Manager initialization WARNING: Configuration has {len(config_errors)} issue(s)",
                    level="WARNING"
                )
                for error in config_errors:
                    self.logger.log_system_event(f"  - {error}", level="WARNING")
            
            self.logger.log_system_event(
                f"Scaled TP Manager initialized with {len(self.config.scaled_tp_levels)} levels"
            )
            # Log each TP level configuration
            for i, level in enumerate(self.config.scaled_tp_levels, 1):
                self.logger.log_system_event(
                    f"  TP{i}: profit={level['profit_pct']*100:.1f}%, "
                    f"close={level['close_pct']*100:.0f}%"
                )
            self.logger.log_system_event(
                f"  Min order size: {self.config.scaled_tp_min_order_size}, "
                f"Fallback to single TP: {self.config.scaled_tp_fallback_to_single}"
            )
        else:
            self.logger.log_system_event(
                "Scaled TP Manager initialized but feature is DISABLED"
            )
    
    def _validate_configuration(self) -> List[str]:
        """Validate scaled TP configuration and return list of warnings.
        
        This performs runtime validation beyond what Config.validate() does,
        checking for potential issues that won't break the system but might
        affect performance.
        
        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []
        
        if not self.config.enable_scaled_take_profit:
            return warnings
        
        # Check if close percentages sum to approximately 1.0
        total_close_pct = sum(level["close_pct"] for level in self.config.scaled_tp_levels)
        if abs(total_close_pct - 1.0) > 0.01:
            warnings.append(
                f"Close percentages sum to {total_close_pct:.2f} instead of 1.0. "
                f"This will be normalized at runtime but may indicate a configuration error."
            )
        
        # Check if profit levels are reasonably spaced
        if len(self.config.scaled_tp_levels) >= 2:
            for i in range(len(self.config.scaled_tp_levels) - 1):
                current_profit = self.config.scaled_tp_levels[i]["profit_pct"]
                next_profit = self.config.scaled_tp_levels[i + 1]["profit_pct"]
                spacing = next_profit - current_profit
                
                # Warn if spacing is very small (< 0.5%)
                if spacing < 0.005:
                    warnings.append(
                        f"TP{i+1} and TP{i+2} are very close ({spacing*100:.2f}% apart). "
                        f"Consider wider spacing for better risk management."
                    )
        
        # Check if minimum order size might cause issues
        if self.config.scaled_tp_min_order_size > 0.01:
            warnings.append(
                f"Minimum order size {self.config.scaled_tp_min_order_size} is relatively large. "
                f"This may cause some TP levels to be skipped for smaller positions."
            )
        
        return warnings
    
    def check_take_profit_levels(
        self, 
        position: Position, 
        current_price: float
    ) -> Optional[PartialCloseAction]:
        """Check if any TP level should be triggered for the current price.
        
        This method checks each configured TP level in order to see if the current
        price has reached the target. It only checks levels that haven't been hit yet.
        
        This method also handles minimum order size requirements:
        - Skips TP levels where the partial quantity is below minimum
        - Closes remaining position if it's below minimum after a partial
        - Falls back to single TP if all partials would be below minimum
        
        Args:
            position: Current position to check
            current_price: Current market price
            
        Returns:
            PartialCloseAction if a TP level is hit, None otherwise
        """
        # If scaled TP is disabled, return None
        if not self.config.enable_scaled_take_profit:
            return None
        
        # Initialize tracking for this symbol if not exists
        if position.symbol not in self._tp_tracking:
            self._initialize_tracking(position)
        
        # Calculate target prices for all TP levels
        target_prices = self._calculate_target_prices(position)
        
        # Get levels already hit
        levels_hit = position.tp_levels_hit
        
        # Check each TP level in order
        for i, tp_config in enumerate(self.config.scaled_tp_levels):
            tp_level = i + 1  # TP levels are 1-indexed
            
            # Skip if this level was already hit
            if tp_level in levels_hit:
                continue
            
            target_price = target_prices[i]
            profit_pct = tp_config["profit_pct"]
            close_pct = tp_config["close_pct"]
            
            # Check if price has reached this TP level
            price_reached = False
            if position.side == "LONG":
                price_reached = current_price >= target_price
            else:  # SHORT
                price_reached = current_price <= target_price
            
            if price_reached:
                # Check if we're skipping TP levels (price gap scenario)
                if tp_level > 1 and (tp_level - 1) not in levels_hit:
                    skipped_levels = [lvl for lvl in range(1, tp_level) if lvl not in levels_hit]
                    self.logger.log_system_event(
                        f"PRICE GAP DETECTED for {position.symbol}: "
                        f"Current price {current_price:.2f} reached TP{tp_level} "
                        f"but skipped TP levels: {skipped_levels}. "
                        f"Processing TP{tp_level} only (earlier levels missed).",
                        level="WARNING"
                    )
                
                # Calculate quantity to close
                quantity = self._calculate_partial_quantity(position, close_pct)
                
                # Check minimum order size
                min_size_result = self._check_minimum_order_size(
                    position, quantity, tp_level, close_pct
                )
                
                # If minimum size check says to skip, continue to next TP level
                if min_size_result["action"] == "skip":
                    self.logger.log_system_event(
                        f"TP{tp_level} skipped for {position.symbol}: "
                        f"quantity {quantity:.4f} below minimum {self.config.scaled_tp_min_order_size:.4f}"
                    )
                    continue
                
                # If minimum size check says to close remaining, adjust quantity
                if min_size_result["action"] == "close_remaining":
                    quantity = min_size_result["adjusted_quantity"]
                    self.logger.log_system_event(
                        f"TP{tp_level} adjusted for {position.symbol}: "
                        f"closing remaining {quantity:.4f} (below minimum)"
                    )
                
                # If minimum size check says to fallback, return None
                if min_size_result["action"] == "fallback":
                    self.logger.log_system_event(
                        f"SCALED TP FALLBACK for {position.symbol}: "
                        f"All partial closes below minimum order size ({self.config.scaled_tp_min_order_size}), "
                        f"reverting to single take profit strategy",
                        level="WARNING"
                    )
                    return None
                
                # Calculate new stop loss
                new_stop_loss = self._calculate_new_stop_loss(
                    position, tp_level, target_prices
                )
                
                # Create and return the action
                action = PartialCloseAction(
                    tp_level=tp_level,
                    profit_pct=profit_pct,
                    close_pct=close_pct,
                    target_price=target_price,
                    quantity=quantity,
                    new_stop_loss=new_stop_loss
                )
                
                # Log TP level hit with all required details (Requirement 7.1)
                self.logger.log_system_event(
                    f"TP{tp_level} HIT for {position.symbol}: "
                    f"price={current_price:.2f}, target={target_price:.2f}, "
                    f"profit={profit_pct*100:.1f}%, "
                    f"closing {close_pct*100:.0f}% ({quantity:.4f} units), "
                    f"new_stop_loss={new_stop_loss:.2f}"
                )
                
                return action
        
        # No TP level hit
        return None
    
    def _calculate_target_prices(self, position: Position) -> List[float]:
        """Calculate target prices for all TP levels.
        
        Args:
            position: Position to calculate targets for
            
        Returns:
            List of target prices, one for each TP level
        """
        target_prices = []
        
        for tp_config in self.config.scaled_tp_levels:
            profit_pct = tp_config["profit_pct"]
            
            if position.side == "LONG":
                # For longs, target is entry price + profit percentage
                target_price = position.entry_price * (1 + profit_pct)
            else:  # SHORT
                # For shorts, target is entry price - profit percentage
                target_price = position.entry_price * (1 - profit_pct)
            
            target_prices.append(target_price)
        
        return target_prices
    
    def _initialize_tracking(self, position: Position) -> None:
        """Initialize TP tracking for a new position.
        
        Args:
            position: Position to initialize tracking for
        """
        target_prices = self._calculate_target_prices(position)
        
        # Determine next TP level and price
        next_tp_level = 1
        next_tp_price = target_prices[0] if target_prices else None
        
        # If position already has some TP levels hit, adjust
        if position.tp_levels_hit:
            next_level_index = len(position.tp_levels_hit)
            if next_level_index < len(self.config.scaled_tp_levels):
                next_tp_level = next_level_index + 1
                next_tp_price = target_prices[next_level_index]
            else:
                next_tp_level = None
                next_tp_price = None
        
        # Calculate remaining size percentage
        if position.original_quantity > 0:
            remaining_size_pct = position.quantity / position.original_quantity
        else:
            remaining_size_pct = 1.0
        
        # Create and store TPStatus
        self._tp_tracking[position.symbol] = TPStatus(
            symbol=position.symbol,
            levels_hit=position.tp_levels_hit.copy(),
            remaining_size_pct=remaining_size_pct,
            current_stop_loss=position.stop_loss,
            next_tp_level=next_tp_level,
            next_tp_price=next_tp_price
        )
    
    def _update_tracking(self, position: Position, tp_level_hit: int, new_stop_loss: float) -> None:
        """Update TP tracking after a TP level is hit.
        
        Args:
            position: Position that hit a TP level
            tp_level_hit: The TP level that was just hit
            new_stop_loss: The new stop loss price
        """
        if position.symbol not in self._tp_tracking:
            self._initialize_tracking(position)
        
        status = self._tp_tracking[position.symbol]
        
        # Update levels hit
        if tp_level_hit not in status.levels_hit:
            status.levels_hit.append(tp_level_hit)
            status.levels_hit.sort()
        
        # Update remaining size percentage
        if position.original_quantity > 0:
            status.remaining_size_pct = position.quantity / position.original_quantity
        
        # Update stop loss
        status.current_stop_loss = new_stop_loss
        
        # Update next TP level and price
        target_prices = self._calculate_target_prices(position)
        next_level_index = len(status.levels_hit)
        
        if next_level_index < len(self.config.scaled_tp_levels):
            status.next_tp_level = next_level_index + 1
            status.next_tp_price = target_prices[next_level_index]
        else:
            # All TP levels hit
            status.next_tp_level = None
            status.next_tp_price = None

    
    def _calculate_partial_quantity(
        self, 
        position: Position, 
        close_pct: float
    ) -> float:
        """Calculate the quantity to close for a partial exit.
        
        This calculates the quantity based on the ORIGINAL position size,
        not the current remaining size. This ensures that close percentages
        sum to 100% of the original position.
        
        For example, with original quantity 1.0:
        - TP1 closes 40% of 1.0 = 0.4
        - TP2 closes 30% of 1.0 = 0.3
        - TP3 closes 30% of 1.0 = 0.3
        Total = 100% of original
        
        Args:
            position: Position to calculate quantity for
            close_pct: Percentage of ORIGINAL position to close (0.0-1.0)
            
        Returns:
            Quantity to close
        """
        # Calculate quantity based on ORIGINAL size, not current remaining
        quantity = position.original_quantity * close_pct
        
        return quantity
    
    def _check_minimum_order_size(
        self,
        position: Position,
        quantity: float,
        tp_level: int,
        close_pct: float
    ) -> dict:
        """Check if a partial close quantity meets minimum order size requirements.
        
        This method implements the minimum order size handling logic:
        1. If quantity is below minimum, skip this TP level
        2. If remaining position after close would be below minimum, close entire remaining
        3. If all partial closes would be below minimum, fall back to single TP
        
        Args:
            position: Position being checked
            quantity: Calculated quantity to close
            tp_level: TP level being checked (1-indexed)
            close_pct: Close percentage for this TP level
            
        Returns:
            Dictionary with:
                - action: "proceed", "skip", "close_remaining", or "fallback"
                - adjusted_quantity: Modified quantity if action is "close_remaining"
        """
        min_size = self.config.scaled_tp_min_order_size
        
        # Check if this partial close is below minimum
        if quantity < min_size:
            # Check if this is the first TP level
            if tp_level == 1 and len(position.tp_levels_hit) == 0:
                # Check if ALL partial closes would be below minimum
                all_below_minimum = True
                for tp_config in self.config.scaled_tp_levels:
                    test_qty = position.original_quantity * tp_config["close_pct"]
                    if test_qty >= min_size:
                        all_below_minimum = False
                        break
                
                # If all partials below minimum and fallback enabled, use single TP
                if all_below_minimum and self.config.scaled_tp_fallback_to_single:
                    return {"action": "fallback", "adjusted_quantity": quantity}
            
            # Skip this TP level and proceed to next
            return {"action": "skip", "adjusted_quantity": quantity}
        
        # Calculate remaining quantity after this close
        remaining_after_close = position.quantity - quantity
        
        # Check if remaining would be below minimum
        if remaining_after_close > 0 and remaining_after_close < min_size:
            # Close the entire remaining position instead
            adjusted_quantity = position.quantity
            return {"action": "close_remaining", "adjusted_quantity": adjusted_quantity}
        
        # Quantity is acceptable, proceed normally
        return {"action": "proceed", "adjusted_quantity": quantity}
    
    def _calculate_new_stop_loss(
        self,
        position: Position,
        tp_level_hit: int,
        target_prices: List[float]
    ) -> float:
        """Calculate the new stop loss after a TP level is hit.
        
        The stop loss ladder works as follows:
        - TP1 hit: Move SL to breakeven (entry price)
        - TP2 hit: Move SL to TP1 price
        - TP3 hit: Move SL to TP2 price
        - etc.
        
        Args:
            position: Position to calculate new stop loss for
            tp_level_hit: The TP level that was just hit (1-indexed)
            target_prices: List of all target prices
            
        Returns:
            New stop loss price
        """
        if tp_level_hit == 1:
            # First TP hit: Move to breakeven
            new_stop_loss = position.entry_price
        else:
            # Subsequent TPs: Move to previous TP level
            prev_tp_index = tp_level_hit - 2  # Convert to 0-indexed and go back one
            new_stop_loss = target_prices[prev_tp_index]
        
        return new_stop_loss
    
    def execute_partial_close(
        self, 
        position: Position, 
        action: PartialCloseAction
    ) -> PartialCloseResult:
        """Execute a partial close order via Binance API with retry logic.
        
        This method is called in PAPER and LIVE modes to actually execute
        the partial close on the exchange. In BACKTEST mode, this is not called.
        
        The method includes:
        - Order placement with reduceOnly flag
        - Order status verification
        - Retry logic (1 retry on failure)
        
        Args:
            position: Position to partially close
            action: Partial close action with details
            
        Returns:
            Result of the partial close execution
        """
        # Check if we have a client (not in backtest mode)
        if self.client is None:
            error_msg = "No Binance client available (backtest mode)"
            self.logger.log_system_event(
                f"PARTIAL CLOSE FAILED: {error_msg}",
                level="ERROR"
            )
            return PartialCloseResult(
                success=False,
                order_id=None,
                filled_quantity=0.0,
                fill_price=0.0,
                realized_profit=0.0,
                error_message=error_msg
            )
        
        # Check minimum order size
        if action.quantity < self.config.scaled_tp_min_order_size:
            error_msg = f"Quantity {action.quantity:.4f} below minimum {self.config.scaled_tp_min_order_size:.4f}"
            self.logger.log_system_event(
                f"PARTIAL CLOSE SKIPPED: TP{action.tp_level} for {position.symbol} - {error_msg}",
                level="WARNING"
            )
            return PartialCloseResult(
                success=False,
                order_id=None,
                filled_quantity=0.0,
                fill_price=0.0,
                realized_profit=0.0,
                error_message=error_msg
            )
        
        # Retry logic: try once, retry once on failure
        max_attempts = 2
        last_error = None
        
        for attempt in range(max_attempts):
            try:
                # Determine order side (opposite of position side)
                order_side = "SELL" if position.side == "LONG" else "BUY"
                
                # Place reduceOnly market order
                attempt_msg = f" (attempt {attempt + 1}/{max_attempts})" if attempt > 0 else ""
                
                # Log order placement with all details (Requirement 7.2)
                self.logger.log_system_event(
                    f"PLACING PARTIAL CLOSE ORDER{attempt_msg}: "
                    f"symbol={position.symbol}, side={order_side}, "
                    f"quantity={action.quantity:.4f}, type=MARKET, reduceOnly=True, "
                    f"TP_level={action.tp_level}"
                )
                
                order = self.client.futures_create_order(
                    symbol=position.symbol,
                    side=order_side,
                    type="MARKET",
                    quantity=action.quantity,
                    reduceOnly=True
                )
                
                # Extract order ID for status verification
                order_id = order.get("orderId")
                
                if not order_id:
                    raise ValueError("Order response missing orderId")
                
                # Verify order status
                order_status = self._verify_order_status(position.symbol, order_id)
                
                if not order_status:
                    raise ValueError(f"Failed to verify order status for order {order_id}")
                
                # Extract order details from verified status
                filled_quantity = float(order_status.get("executedQty", 0))
                status = order_status.get("status")
                
                # Check if order was filled
                if status not in ["FILLED", "PARTIALLY_FILLED"]:
                    raise ValueError(f"Order {order_id} not filled, status: {status}")
                
                # Get fill price (average)
                avg_price = float(order_status.get("avgPrice", 0))
                
                if avg_price == 0 and filled_quantity > 0:
                    # Fallback: calculate from fills if avgPrice not available
                    fills = order.get("fills", [])
                    if fills:
                        total_value = sum(float(fill["price"]) * float(fill["qty"]) for fill in fills)
                        avg_price = total_value / filled_quantity
                
                fill_price = avg_price
                
                # Calculate realized profit
                if position.side == "LONG":
                    realized_profit = (fill_price - position.entry_price) * filled_quantity
                else:  # SHORT
                    realized_profit = (position.entry_price - fill_price) * filled_quantity
                
                # Log partial close completion with all details (Requirement 7.3)
                self.logger.log_system_event(
                    f"PARTIAL CLOSE COMPLETED: "
                    f"TP{action.tp_level} for {position.symbol}, "
                    f"filled_qty={filled_quantity:.4f}, "
                    f"fill_price={fill_price:.2f}, "
                    f"realized_profit=${realized_profit:.2f} ({(realized_profit/position.entry_price/filled_quantity)*100:.2f}%), "
                    f"order_id={order_id}"
                )
                
                # Update tracking after successful partial close
                # Note: Position should be updated by caller before this tracking update
                # This is just for internal tracking state
                
                return PartialCloseResult(
                    success=True,
                    order_id=str(order_id),
                    filled_quantity=filled_quantity,
                    fill_price=fill_price,
                    realized_profit=realized_profit,
                    error_message=None
                )
                
            except Exception as e:
                last_error = str(e)
                error_msg = f"Partial close attempt {attempt + 1}/{max_attempts} failed: {last_error}"
                self.logger.log_system_event(
                    f"PARTIAL CLOSE ERROR: {error_msg} for {position.symbol} TP{action.tp_level}",
                    level="ERROR"
                )
                
                # If this was the last attempt, return failure
                if attempt == max_attempts - 1:
                    final_error_msg = f"All {max_attempts} attempts failed for partial close of {position.symbol}"
                    self.logger.log_system_event(
                        f"PARTIAL CLOSE FAILED: {final_error_msg}. Last error: {last_error}",
                        level="ERROR"
                    )
                    return PartialCloseResult(
                        success=False,
                        order_id=None,
                        filled_quantity=0.0,
                        fill_price=0.0,
                        realized_profit=0.0,
                        error_message=f"Failed after {max_attempts} attempts: {last_error}"
                    )
                
                # Wait a moment before retry (in production, might want exponential backoff)
                import time
                time.sleep(0.5)
        
        # Should never reach here, but just in case
        return PartialCloseResult(
            success=False,
            order_id=None,
            filled_quantity=0.0,
            fill_price=0.0,
            realized_profit=0.0,
            error_message=f"Unexpected error: {last_error}"
        )
    
    def _verify_order_status(self, symbol: str, order_id: int) -> Optional[dict]:
        """Verify the status of an order by querying Binance API.
        
        Args:
            symbol: Trading symbol
            order_id: Order ID to verify
            
        Returns:
            Order status dict if successful, None if failed
        """
        try:
            order_status = self.client.futures_get_order(
                symbol=symbol,
                orderId=order_id
            )
            self.logger.log_system_event(
                f"Order status verified: order_id={order_id}, status={order_status.get('status')}"
            )
            return order_status
        except Exception as e:
            self.logger.log_system_event(
                f"ORDER VERIFICATION FAILED: order_id={order_id}, error={str(e)}",
                level="ERROR"
            )
            return None
    
    def update_stop_loss_ladder(
        self, 
        position: Position, 
        tp_level_hit: int
    ) -> float:
        """Update stop loss after a TP level is hit.
        
        This is a convenience method that calculates the new stop loss
        and ensures it only moves in a favorable direction.
        
        Args:
            position: Position to update stop loss for
            tp_level_hit: The TP level that was just hit
            
        Returns:
            New stop loss price
        """
        target_prices = self._calculate_target_prices(position)
        new_stop_loss = self._calculate_new_stop_loss(
            position, tp_level_hit, target_prices
        )
        
        # Store old stop loss for logging
        old_stop_loss = position.stop_loss
        
        # Ensure stop loss only moves favorably
        if position.side == "LONG":
            # For longs, new SL should be higher than old SL
            new_stop_loss = max(new_stop_loss, position.stop_loss)
        else:  # SHORT
            # For shorts, new SL should be lower than old SL
            new_stop_loss = min(new_stop_loss, position.stop_loss)
        
        # Log stop loss update with old and new levels (Requirement 7.4)
        self.logger.log_system_event(
            f"STOP LOSS UPDATED for {position.symbol} after TP{tp_level_hit}: "
            f"old_SL={old_stop_loss:.2f} -> new_SL={new_stop_loss:.2f} "
            f"(moved {abs(new_stop_loss - old_stop_loss):.2f} points)"
        )
        
        # Update tracking with new stop loss
        self._update_tracking(position, tp_level_hit, new_stop_loss)
        
        return new_stop_loss
    
    def update_tracking_after_partial_close(
        self,
        position: Position,
        tp_level_hit: int,
        new_stop_loss: float
    ) -> None:
        """Update TP tracking after a partial close has been executed.
        
        This should be called by the TradingBot after it has updated the position
        object with the new quantity and stop loss.
        
        Args:
            position: Updated position after partial close
            tp_level_hit: The TP level that was just hit
            new_stop_loss: The new stop loss price
        """
        self._update_tracking(position, tp_level_hit, new_stop_loss)
    
    def get_tp_status(self, symbol: str) -> TPStatus:
        """Get current TP status for a symbol.
        
        Args:
            symbol: Trading symbol to get status for
            
        Returns:
            TPStatus object with current state
        """
        if symbol in self._tp_tracking:
            return self._tp_tracking[symbol]
        
        # Return empty status if not tracking
        return TPStatus(
            symbol=symbol,
            levels_hit=[],
            remaining_size_pct=1.0,
            current_stop_loss=0.0,
            next_tp_level=1,
            next_tp_price=None
        )
    
    def reset_tracking(self, symbol: str) -> None:
        """Reset TP tracking when a position closes.
        
        Args:
            symbol: Trading symbol to reset tracking for
        """
        if symbol in self._tp_tracking:
            del self._tp_tracking[symbol]
            self.logger.log_system_event(f"TP tracking reset for {symbol}")
    
    def get_all_applicable_tp_levels(
        self,
        position: Position,
        current_price: float
    ) -> List[PartialCloseAction]:
        """Get all TP levels that should be triggered at the current price.
        
        This method is useful for handling price gaps where multiple TP levels
        are reached in a single price movement. It returns all applicable TP
        levels in order, which can then be processed sequentially.
        
        This is primarily used in backtest scenarios where we want to process
        all applicable TPs for a single candle. In live trading, the bot
        processes one TP at a time per monitoring loop iteration.
        
        Args:
            position: Current position to check
            current_price: Current market price
            
        Returns:
            List of PartialCloseAction objects for all applicable TP levels
        """
        applicable_actions = []
        
        # Make a copy of the position to simulate processing
        temp_position = Position(
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            quantity=position.quantity,
            leverage=position.leverage,
            stop_loss=position.stop_loss,
            trailing_stop=position.trailing_stop,
            entry_time=position.entry_time,
            unrealized_pnl=position.unrealized_pnl,
            original_quantity=position.original_quantity,
            partial_exits=position.partial_exits.copy(),
            tp_levels_hit=position.tp_levels_hit.copy()
        )
        
        # Check each TP level in sequence
        while True:
            action = self.check_take_profit_levels(temp_position, current_price)
            
            if action is None:
                # No more TP levels to process
                break
            
            # Add this action to the list
            applicable_actions.append(action)
            
            # Simulate the partial close on temp position
            temp_position.quantity -= action.quantity
            temp_position.tp_levels_hit.append(action.tp_level)
            temp_position.stop_loss = action.new_stop_loss
            
            # Safety check: don't process more than configured levels
            if len(applicable_actions) >= len(self.config.scaled_tp_levels):
                break
        
        return applicable_actions
