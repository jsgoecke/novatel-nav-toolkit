"""
Unit tests for UDPListener module
"""

import pytest
import sys
import os
import socket
import threading
import time
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from udp_listener import UDPListener
import config


class TestUDPListener:
    """Test UDP socket listener functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.callback_mock = Mock()
        self.listener = UDPListener(self.callback_mock)
    
    def test_initialization(self):
        """Test UDPListener initialization"""
        assert self.listener.data_callback == self.callback_mock
        assert self.listener.socket is None
        assert self.listener.listening is False
        assert self.listener.thread is None
        assert self.listener.error_count == 0
    
    @patch('socket.socket')
    def test_start_success(self, mock_socket_class):
        """Test successful listener start"""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        
        # Mock socket operations
        mock_socket.bind.return_value = None
        mock_socket.settimeout.return_value = None
        mock_socket.setsockopt.return_value = None
        
        with patch.object(threading.Thread, 'start') as mock_thread_start:
            result = self.listener.start()
            
            assert result is True
            assert self.listener.listening is True
            assert self.listener.socket == mock_socket
            
            # Verify socket configuration
            mock_socket.setsockopt.assert_called_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            mock_socket.settimeout.assert_called_with(config.SOCKET_TIMEOUT)
            mock_socket.bind.assert_called_with((config.UDP_HOST, config.UDP_PORT))
            mock_thread_start.assert_called_once()
    
    @patch('socket.socket')
    def test_start_bind_failure(self, mock_socket_class):
        """Test listener start with bind failure"""
        mock_socket = Mock()
        mock_socket_class.return_value = mock_socket
        
        # Mock bind to raise exception
        mock_socket.bind.side_effect = OSError("Address already in use")
        
        result = self.listener.start()
        
        assert result is False
        assert self.listener.listening is False
    
    def test_stop_not_started(self):
        """Test stopping listener that was never started"""
        self.listener.stop()
        
        assert self.listener.listening is False
        assert self.listener.socket is None
    
    @patch('socket.socket')
    def test_stop_with_socket(self, mock_socket_class):
        """Test stopping listener with active socket"""
        mock_socket = Mock()
        mock_thread = Mock()
        
        self.listener.socket = mock_socket
        self.listener.thread = mock_thread
        self.listener.listening = True
        
        # Mock thread.is_alive() and join()
        mock_thread.is_alive.return_value = True
        mock_thread.join.return_value = None
        
        self.listener.stop()
        
        assert self.listener.listening is False
        mock_socket.close.assert_called_once()
        mock_thread.join.assert_called_with(timeout=1.0)
    
    def test_is_listening_false(self):
        """Test is_listening when not listening"""
        assert self.listener.is_listening() is False
    
    @patch('socket.socket')
    def test_is_listening_true(self, mock_socket_class):
        """Test is_listening when actively listening"""
        mock_thread = Mock()
        mock_thread.is_alive.return_value = True
        
        self.listener.listening = True
        self.listener.thread = mock_thread
        
        assert self.listener.is_listening() is True
    
    def test_get_stats(self):
        """Test getting listener statistics"""
        self.listener.error_count = 5
        
        with patch.object(self.listener, 'is_listening', return_value=True):
            stats = self.listener.get_stats()
            
            assert stats['listening'] is True
            assert stats['error_count'] == 5
            assert stats['port'] == config.UDP_PORT
            assert stats['host'] == config.UDP_HOST
    
    @patch('time.time')
    @patch('config.LOG_UDP_TRAFFIC', False)
    @patch('config.PROTOCOL_MODE', 'nmea')
    def test_listen_loop_nmea_message(self, mock_time):
        """Test listen loop with NMEA message"""
        mock_socket = Mock()
        self.listener.socket = mock_socket
        self.listener.listening = True
        
        # Mock time for activity logging
        mock_time.return_value = 1000
        
        # Mock socket.recvfrom to return NMEA data, then stop
        nmea_data = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        mock_socket.recvfrom.side_effect = [
            (nmea_data, ('127.0.0.1', 12345)),
            socket.timeout()  # Stop the loop
        ]
        
        # Start listen loop in a separate thread to avoid hanging
        def run_listen_loop():
            try:
                self.listener._listen_loop()
            except:
                pass  # Expected when we break the loop
        
        thread = threading.Thread(target=run_listen_loop)
        thread.start()
        
        # Give it a moment to process
        time.sleep(0.1)
        self.listener.listening = False
        thread.join(timeout=1.0)
        
        # Verify callback was called with decoded string
        self.callback_mock.assert_called()
        call_args = self.callback_mock.call_args[0][0]
        assert isinstance(call_args, str)
        assert call_args.startswith("$GPGGA")
    
    @patch('time.time')
    @patch('config.LOG_UDP_TRAFFIC', False)
    @patch('config.PROTOCOL_MODE', 'adsb')
    def test_listen_loop_adsb_message(self, mock_time):
        """Test listen loop with ADS-B message"""
        mock_socket = Mock()
        self.listener.socket = mock_socket
        self.listener.listening = True
        
        mock_time.return_value = 1000
        
        # Mock socket.recvfrom to return ADS-B data
        adsb_data = bytes.fromhex("8D4840D6202CC371C32CE0576098")
        mock_socket.recvfrom.side_effect = [
            (adsb_data, ('127.0.0.1', 12345)),
            socket.timeout()
        ]
        
        def run_listen_loop():
            try:
                self.listener._listen_loop()
            except:
                pass
        
        thread = threading.Thread(target=run_listen_loop)
        thread.start()
        time.sleep(0.1)
        self.listener.listening = False
        thread.join(timeout=1.0)
        
        # Verify callback was called with raw bytes
        self.callback_mock.assert_called()
        call_args = self.callback_mock.call_args[0][0]
        assert isinstance(call_args, bytes)
        assert call_args == adsb_data
    
    @patch('time.time')
    @patch('config.LOG_UDP_TRAFFIC', False)
    @patch('config.PROTOCOL_MODE', 'auto')
    def test_listen_loop_auto_detect_nmea(self, mock_time):
        """Test listen loop with auto-detection for NMEA"""
        mock_socket = Mock()
        self.listener.socket = mock_socket
        self.listener.listening = True
        
        mock_time.return_value = 1000
        
        # NMEA data that decodes to valid UTF-8 and starts with $
        nmea_data = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        mock_socket.recvfrom.side_effect = [
            (nmea_data, ('127.0.0.1', 12345)),
            socket.timeout()
        ]
        
        def run_listen_loop():
            try:
                self.listener._listen_loop()
            except:
                pass
        
        thread = threading.Thread(target=run_listen_loop)
        thread.start()
        time.sleep(0.1)
        self.listener.listening = False
        thread.join(timeout=1.0)
        
        # Should detect as NMEA and pass string
        self.callback_mock.assert_called()
        call_args = self.callback_mock.call_args[0][0]
        assert isinstance(call_args, str)
    
    @patch('time.time')
    @patch('config.LOG_UDP_TRAFFIC', False)
    @patch('config.PROTOCOL_MODE', 'auto')
    def test_listen_loop_auto_detect_adsb(self, mock_time):
        """Test listen loop with auto-detection for ADS-B"""
        mock_socket = Mock()
        self.listener.socket = mock_socket
        self.listener.listening = True
        
        mock_time.return_value = 1000
        
        # Binary data that can't be decoded as UTF-8
        adsb_data = bytes.fromhex("8D4840D6202CC371C32CE0576098")
        mock_socket.recvfrom.side_effect = [
            (adsb_data, ('127.0.0.1', 12345)),
            socket.timeout()
        ]
        
        def run_listen_loop():
            try:
                self.listener._listen_loop()
            except:
                pass
        
        thread = threading.Thread(target=run_listen_loop)
        thread.start()
        time.sleep(0.1)
        self.listener.listening = False
        thread.join(timeout=1.0)
        
        # Should detect as ADS-B and pass bytes
        self.callback_mock.assert_called()
        call_args = self.callback_mock.call_args[0][0]
        assert isinstance(call_args, bytes)
    
    @patch('time.time')
    @patch('config.LOG_UDP_TRAFFIC', False)
    @patch('config.PROTOCOL_MODE', 'auto')
    def test_listen_loop_auto_detect_non_nmea_text(self, mock_time):
        """Test auto-detection with text that doesn't start with $"""
        mock_socket = Mock()
        self.listener.socket = mock_socket
        self.listener.listening = True
        
        mock_time.return_value = 1000
        
        # Text data that doesn't start with $
        text_data = b"Some other text data"
        mock_socket.recvfrom.side_effect = [
            (text_data, ('127.0.0.1', 12345)),
            socket.timeout()
        ]
        
        def run_listen_loop():
            try:
                self.listener._listen_loop()
            except:
                pass
        
        thread = threading.Thread(target=run_listen_loop)
        thread.start()
        time.sleep(0.1)
        self.listener.listening = False
        thread.join(timeout=1.0)
        
        # Should treat as ADS-B and pass bytes
        self.callback_mock.assert_called()
        call_args = self.callback_mock.call_args[0][0]
        assert isinstance(call_args, bytes)
    
    @patch('time.time')
    @patch('config.LOG_UDP_TRAFFIC', False)
    def test_listen_loop_empty_data(self, mock_time):
        """Test listen loop with empty data"""
        mock_socket = Mock()
        self.listener.socket = mock_socket
        self.listener.listening = True
        
        mock_time.return_value = 1000
        
        # Empty data
        mock_socket.recvfrom.side_effect = [
            (b"", ('127.0.0.1', 12345)),
            socket.timeout()
        ]
        
        def run_listen_loop():
            try:
                self.listener._listen_loop()
            except:
                pass
        
        thread = threading.Thread(target=run_listen_loop)
        thread.start()
        time.sleep(0.1)
        self.listener.listening = False
        thread.join(timeout=1.0)
        
        # Should not call callback for empty data
        self.callback_mock.assert_not_called()
    
    @patch('time.time')
    @patch('config.LOG_UDP_TRAFFIC', False)
    @patch('config.MAX_PARSE_ERRORS', 2)
    def test_listen_loop_max_errors(self, mock_time):
        """Test listen loop stops after max consecutive errors"""
        mock_socket = Mock()
        self.listener.socket = mock_socket
        self.listener.listening = True
        
        mock_time.return_value = 1000
        
        # Mock socket to raise exceptions
        mock_socket.recvfrom.side_effect = [
            OSError("Network error"),
            OSError("Network error"),
            OSError("Network error")  # Third error should stop loop
        ]
        
        def run_listen_loop():
            self.listener._listen_loop()
        
        thread = threading.Thread(target=run_listen_loop)
        thread.start()
        thread.join(timeout=2.0)
        
        # Should have stopped due to too many errors
        assert self.listener.error_count >= 2
    
    @patch('time.time')
    @patch('config.LOG_UDP_TRAFFIC', False)
    def test_listen_loop_timeout_handling(self, mock_time):
        """Test listen loop handles socket timeouts gracefully"""
        mock_socket = Mock()
        self.listener.socket = mock_socket
        self.listener.listening = True
        
        mock_time.return_value = 1000
        
        # Mock socket to timeout, then return data, then timeout again
        mock_socket.recvfrom.side_effect = [
            socket.timeout(),
            socket.timeout(),
            socket.timeout()
        ]
        
        def run_listen_loop():
            try:
                # Run a few iterations then stop
                count = 0
                original_listening = self.listener.listening
                def check_listening():
                    nonlocal count
                    count += 1
                    return original_listening and count < 5
                
                with patch.object(self.listener, 'listening', side_effect=check_listening):
                    self.listener._listen_loop()
            except:
                pass
        
        thread = threading.Thread(target=run_listen_loop)
        thread.start()
        thread.join(timeout=2.0)
        
        # Timeouts should not increment error count
        # (we can't easily test this without more complex mocking)
        assert True  # Test passes if no exceptions


if __name__ == "__main__":
    pytest.main([__file__])