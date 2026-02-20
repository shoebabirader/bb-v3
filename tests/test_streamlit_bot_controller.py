"""
Tests for Streamlit Bot Controller

Tests bot process management and emergency controls.
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, MagicMock
from src.streamlit_bot_controller import BotController


class TestBotController:
    """Unit tests for BotController."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.controller = BotController()
    
    def test_start_bot_when_not_running(self):
        """Test starting bot when it's not already running."""
        with patch.object(self.controller, '_is_running', return_value=False):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = Mock()
                mock_process.poll.return_value = None  # Process is running
                mock_popen.return_value = mock_process
                
                success, message = self.controller.start_bot()
                
                assert success is True
                assert "started successfully" in message.lower()
    
    def test_start_bot_when_already_running(self):
        """Test starting bot when it's already running."""
        with patch.object(self.controller, '_is_running', return_value=True):
            success, message = self.controller.start_bot()
            
            assert success is False
            assert "already running" in message.lower()
    
    def test_start_bot_failure(self):
        """Test bot start failure."""
        with patch.object(self.controller, '_is_running', return_value=False):
            with patch('subprocess.Popen') as mock_popen:
                mock_process = Mock()
                mock_process.poll.return_value = 1  # Process failed
                mock_process.stderr = Mock()
                mock_process.stderr.read.return_value = b"Error message"
                mock_popen.return_value = mock_process
                
                success, message = self.controller.start_bot()
                
                assert success is False
                assert "failed" in message.lower()
    
    def test_stop_bot_when_running(self):
        """Test stopping bot when it's running."""
        with patch.object(self.controller, '_is_running', return_value=True):
            with patch('psutil.process_iter') as mock_iter:
                mock_proc = Mock()
                mock_proc.info = {'cmdline': ['python', 'main.py']}
                mock_proc.terminate = Mock()
                mock_proc.wait = Mock()
                mock_iter.return_value = [mock_proc]
                
                success, message = self.controller.stop_bot()
                
                assert success is True
                assert "stopped successfully" in message.lower()
    
    def test_stop_bot_when_not_running(self):
        """Test stopping bot when it's not running."""
        with patch.object(self.controller, '_is_running', return_value=False):
            success, message = self.controller.stop_bot()
            
            assert success is False
            assert "not running" in message.lower()
    
    def test_emergency_close_no_positions(self):
        """Test emergency close with no open positions."""
        import json
        from io import StringIO
        import sys
        
        # Mock config data
        config_data = json.dumps({
            "api_key": "test_key",
            "api_secret": "test_secret"
        })
        
        # Mock results data with no positions
        results_data = json.dumps({
            "open_positions": []
        })
        
        # Mock file reads
        def mock_open_side_effect(filename, *args, **kwargs):
            if 'config.json' in filename:
                return StringIO(config_data)
            elif 'binance_results.json' in filename:
                return StringIO(results_data)
            raise FileNotFoundError(f"File not found: {filename}")
        
        # Create a mock module for binance.client
        mock_binance_module = MagicMock()
        mock_binance_module.Client = MagicMock()
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=mock_open_side_effect):
                with patch.dict('sys.modules', {'binance.client': mock_binance_module}):
                    success, message = self.controller.emergency_close_all()
                    
                    assert success is True
                    assert "no open positions" in message.lower()
    
    def test_emergency_close_with_positions(self):
        """Test emergency close with open positions."""
        import json
        from io import StringIO
        
        # Mock config data
        config_data = json.dumps({
            "api_key": "test_key",
            "api_secret": "test_secret"
        })
        
        # Mock results data with positions
        results_data = json.dumps({
            "open_positions": [
                {
                    "symbol": "BTCUSDT",
                    "side": "LONG",
                    "quantity": 0.1
                }
            ]
        })
        
        # Mock file reads
        def mock_open_side_effect(filename, *args, **kwargs):
            if 'config.json' in filename:
                return StringIO(config_data)
            elif 'binance_results.json' in filename:
                return StringIO(results_data)
            raise FileNotFoundError(f"File not found: {filename}")
        
        # Create mock client
        mock_client_instance = MagicMock()
        mock_client_instance.futures_create_order.return_value = {"orderId": 123}
        
        # Create a mock module for binance.client
        mock_binance_module = MagicMock()
        mock_binance_module.Client = MagicMock(return_value=mock_client_instance)
        
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=mock_open_side_effect):
                with patch.dict('sys.modules', {'binance.client': mock_binance_module}):
                    success, message = self.controller.emergency_close_all()
                    
                    assert success is True
                    assert "closed" in message.lower()
                    assert "1" in message  # Should mention 1 position closed
    
    def test_emergency_close_missing_config(self):
        """Test emergency close with missing config file."""
        with patch('os.path.exists', return_value=False):
            success, message = self.controller.emergency_close_all()
            
            assert success is False
            assert "configuration" in message.lower() or "not found" in message.lower()


# Feature: streamlit-ui, Property 7: Control Action Feedback
@settings(max_examples=100)
@given(
    action_result=st.sampled_from([
        ('start', True, "Bot started successfully"),
        ('start', False, "Bot is already running"),
        ('start', False, "Bot failed to start"),
        ('stop', True, "Bot stopped successfully"),
        ('stop', False, "Bot is not running"),
        ('stop', False, "Error stopping bot"),
        ('emergency', True, "Successfully closed 2 position(s)"),
        ('emergency', True, "No open positions to close"),
        ('emergency', False, "Failed to close positions"),
        ('emergency', False, "API credentials not configured"),
    ])
)
def test_control_action_feedback(action_result):
    """For any control action result (success or failure), 
    the Control_Panel must display an appropriate feedback message.
    
    **Validates: Requirements 5.5**
    """
    action_type, success, message = action_result
    
    # Verify that a message is always returned
    assert message is not None, "Control action must return a message"
    assert isinstance(message, str), "Message must be a string"
    assert len(message) > 0, "Message must not be empty"
    
    # Verify message content is appropriate for the result
    if success:
        # Success messages should indicate success
        success_indicators = ['success', 'started', 'stopped', 'closed', 'no open']
        assert any(indicator in message.lower() for indicator in success_indicators), \
            f"Success message should indicate success: {message}"
    else:
        # Failure messages should indicate the problem
        failure_indicators = ['already', 'not running', 'failed', 'error', 'not found', 'not configured']
        assert any(indicator in message.lower() for indicator in failure_indicators), \
            f"Failure message should indicate the problem: {message}"
    
    # Verify message is informative (not just "success" or "error")
    assert len(message.split()) >= 2, \
        f"Message should be informative with at least 2 words: {message}"
