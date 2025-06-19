"""
Unit tests for main module
"""

import pytest
import sys
import os
import signal
import threading
import time
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import NavigationListener, print_usage, main
import config


class TestNavigationListener:
    """Test main NavigationListener class functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        with patch('main.signal.signal'):  # Prevent signal handler registration during test
            self.listener = NavigationListener()
    
    def test_initialization(self):
        """Test NavigationListener initialization"""
        with patch('main.signal.signal') as mock_signal:
            listener = NavigationListener()
            
            assert listener.udp_listener is None
            assert listener.nmea_parser is not None
            assert listener.adsb_parser is not None
            assert listener.display is not None
            assert listener.running is False
            assert listener.display_thread is None
            
            # Verify signal handlers were set up
            assert mock_signal.call_count == 2
            mock_signal.assert_any_call(signal.SIGINT, listener._signal_handler)
            mock_signal.assert_any_call(signal.SIGTERM, listener._signal_handler)
    
    @patch('main.UDPListener')
    @patch('main.threading.Thread')
    def test_start_success(self, mock_thread_class, mock_udp_listener_class):
        """Test successful listener start"""
        # Mock UDP listener
        mock_udp_listener = Mock()
        mock_udp_listener.start.return_value = True
        mock_udp_listener.is_listening.return_value = True
        mock_udp_listener_class.return_value = mock_udp_listener
        
        # Mock display thread
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        # Test the UDP listener creation directly
        result = self.listener._start_udp_listener()
        
        # Verify the result and calls
        assert result is True
        mock_udp_listener_class.assert_called_once()
        mock_udp_listener.start.assert_called_once()
    
    @patch('main.UDPListener')
    def test_start_udp_failure(self, mock_udp_listener_class):
        """Test listener start with UDP failure"""
        mock_udp_listener = Mock()
        mock_udp_listener.start.return_value = False
        mock_udp_listener_class.return_value = mock_udp_listener
        
        result = self.listener.start()
        
        assert result is False
    
    def test_stop(self):
        """Test listener stop"""
        # Set up mocks
        mock_udp_listener = Mock()
        mock_display_thread = Mock()
        mock_display_thread.is_alive.return_value = True
        
        self.listener.udp_listener = mock_udp_listener
        self.listener.display_thread = mock_display_thread
        self.listener.running = True
        
        self.listener.stop()
        
        assert self.listener.running is False
        mock_udp_listener.stop.assert_called_once()
        mock_display_thread.join.assert_called_with(timeout=2.0)
    
    def test_stop_no_udp_listener(self):
        """Test stop with no UDP listener"""
        self.listener.running = True
        
        # Should not raise exception
        self.listener.stop()
        
        assert self.listener.running is False
    
    @patch('config.PROTOCOL_MODE', 'nmea')
    def test_handle_udp_data_nmea_mode(self):
        """Test UDP data handling in NMEA mode"""
        test_data = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        
        with patch.object(self.listener, '_handle_nmea_data') as mock_handle_nmea:
            self.listener._handle_udp_data(test_data)
            
            mock_handle_nmea.assert_called_once_with(test_data)
    
    @patch('config.PROTOCOL_MODE', 'adsb')
    def test_handle_udp_data_adsb_mode(self):
        """Test UDP data handling in ADS-B mode"""
        test_data = bytes.fromhex("8D4840D6202CC371C32CE0576098")
        
        with patch.object(self.listener, '_handle_adsb_data') as mock_handle_adsb:
            self.listener._handle_udp_data(test_data)
            
            mock_handle_adsb.assert_called_once_with(test_data)
    
    @patch('config.PROTOCOL_MODE', 'auto')
    def test_handle_udp_data_auto_mode_bytes(self):
        """Test UDP data handling in auto mode with bytes"""
        test_data = bytes.fromhex("8D4840D6202CC371C32CE0576098")
        
        with patch.object(self.listener, '_handle_adsb_data') as mock_handle_adsb:
            self.listener._handle_udp_data(test_data)
            
            mock_handle_adsb.assert_called_once_with(test_data)
    
    @patch('config.PROTOCOL_MODE', 'auto')
    def test_handle_udp_data_auto_mode_string(self):
        """Test UDP data handling in auto mode with string"""
        test_data = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        
        with patch.object(self.listener, '_handle_nmea_data') as mock_handle_nmea:
            self.listener._handle_udp_data(test_data)
            
            mock_handle_nmea.assert_called_once_with(test_data)
    
    def test_handle_nmea_data_single_sentence(self):
        """Test handling single NMEA sentence"""
        test_data = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        
        with patch.object(self.listener.nmea_parser, 'parse_sentence') as mock_parse:
            mock_parse.return_value = {'latitude': 48.1173, 'longitude': 11.5167}
            
            self.listener._handle_nmea_data(test_data)
            
            mock_parse.assert_called_once_with(test_data)
    
    def test_handle_nmea_data_multiple_sentences(self):
        """Test handling multiple NMEA sentences"""
        test_data = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\n$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        
        with patch.object(self.listener.nmea_parser, 'parse_sentence') as mock_parse:
            mock_parse.return_value = {'test': 'data'}
            
            self.listener._handle_nmea_data(test_data)
            
            assert mock_parse.call_count == 2
    
    def test_handle_nmea_data_with_empty_sentences(self):
        """Test handling NMEA data with empty sentences"""
        test_data = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\n\n\n$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        
        with patch.object(self.listener.nmea_parser, 'parse_sentence') as mock_parse:
            mock_parse.return_value = {'test': 'data'}
            
            self.listener._handle_nmea_data(test_data)
            
            # Should only call parse_sentence for non-empty sentences
            assert mock_parse.call_count == 2
    
    def test_handle_adsb_data(self):
        """Test handling ADS-B data"""
        test_data = bytes.fromhex("8D4840D6202CC371C32CE0576098")
        
        with patch.object(self.listener.adsb_parser, 'parse_message') as mock_parse:
            mock_parse.return_value = {'icao': '4840D6', 'callsign': 'UAL1234'}
            
            self.listener._handle_adsb_data(test_data)
            
            mock_parse.assert_called_once_with(test_data)
    
    @patch('config.PROTOCOL_MODE', 'nmea')
    def test_display_loop_nmea_mode(self):
        """Test display loop in NMEA mode"""
        self.listener.running = True
        
        # Mock parser data
        mock_nav_data = {'latitude': 48.1173, 'longitude': 11.5167}
        mock_stats = {'sentences_parsed': 10}
        
        with patch.object(self.listener.nmea_parser, 'get_latest_navigation_data', return_value=mock_nav_data):
            with patch.object(self.listener.nmea_parser, 'get_stats', return_value=mock_stats):
                with patch.object(self.listener.display, 'display') as mock_display:
                    with patch('time.sleep') as mock_sleep:
                        # Mock sleep to stop after first iteration
                        def stop_after_first(*args):
                            self.listener.running = False
                        
                        mock_sleep.side_effect = stop_after_first
                        
                        self.listener._display_loop()
                        
                        mock_display.assert_called_once()
                        # Verify data was passed to display
                        display_call_args = mock_display.call_args[0]
                        assert display_call_args[0] == mock_nav_data
    
    @patch('config.PROTOCOL_MODE', 'adsb')
    def test_display_loop_adsb_mode(self):
        """Test display loop in ADS-B mode"""
        self.listener.running = True
        
        mock_nav_data = {'icao': '4840D6', 'callsign': 'UAL1234'}
        mock_stats = {'messages_parsed': 5}
        
        with patch.object(self.listener.adsb_parser, 'get_latest_aviation_data', return_value=mock_nav_data):
            with patch.object(self.listener.adsb_parser, 'get_stats', return_value=mock_stats):
                with patch.object(self.listener.display, 'display') as mock_display:
                    with patch('time.sleep') as mock_sleep:
                        def stop_after_first(*args):
                            self.listener.running = False
                        
                        mock_sleep.side_effect = stop_after_first
                        
                        self.listener._display_loop()
                        
                        mock_display.assert_called_once()
    
    @patch('config.PROTOCOL_MODE', 'auto')
    def test_display_loop_auto_mode(self):
        """Test display loop in auto mode"""
        self.listener.running = True
        
        nmea_data = {'latitude': 48.1173}
        adsb_data = {'icao': '4840D6'}
        combined_expected = {'latitude': 48.1173, 'icao': '4840D6'}
        
        with patch.object(self.listener.nmea_parser, 'get_latest_navigation_data', return_value=nmea_data):
            with patch.object(self.listener.adsb_parser, 'get_latest_aviation_data', return_value=adsb_data):
                with patch.object(self.listener.display, 'display') as mock_display:
                    with patch('time.sleep') as mock_sleep:
                        def stop_after_first(*args):
                            self.listener.running = False
                        
                        mock_sleep.side_effect = stop_after_first
                        
                        self.listener._display_loop()
                        
                        mock_display.assert_called_once()
                        # Verify combined data
                        display_call_args = mock_display.call_args[0]
                        assert display_call_args[0] == combined_expected
    
    def test_display_loop_exception_handling(self):
        """Test display loop handles exceptions gracefully"""
        self.listener.running = True
        
        with patch.object(self.listener.nmea_parser, 'get_latest_navigation_data', side_effect=Exception("Test error")):
            with patch('time.sleep') as mock_sleep:
                # Stop after first iteration
                call_count = 0
                def stop_after_first(*args):
                    nonlocal call_count
                    call_count += 1
                    if call_count >= 2:  # Allow for error sleep + normal sleep
                        self.listener.running = False
                
                mock_sleep.side_effect = stop_after_first
                
                # Should not raise exception
                self.listener._display_loop()
                
                # Should have slept due to error
                assert mock_sleep.call_count >= 1
    
    def test_signal_handler(self):
        """Test signal handler"""
        self.listener.running = True
        
        self.listener._signal_handler(signal.SIGINT, None)
        
        assert self.listener.running is False


class TestPrintUsage:
    """Test print_usage function"""
    
    @patch('builtins.print')
    def test_print_usage(self, mock_print):
        """Test that print_usage prints expected content"""
        print_usage()
        
        # Verify print was called multiple times with usage info
        assert mock_print.call_count > 10
        
        # Check for key content in the calls
        all_output = ' '.join([str(call) for call in mock_print.call_args_list])
        assert "Novatel ProPak6 Navigation Data Toolkit" in all_output
        assert "Usage: python main.py" in all_output
        assert "--help" in all_output
        assert "--port" in all_output
        assert "--adsb" in all_output


class TestMain:
    """Test main function and command line argument parsing"""
    
    @patch('main.NavigationListener')
    @patch('sys.argv', ['main.py', '--help'])
    @patch('builtins.print')
    def test_main_help_argument(self, mock_print, mock_listener_class):
        """Test main function with help argument"""
        result = main()
        
        assert result == 0
        # Should not create listener for help
        mock_listener_class.assert_not_called()
    
    @patch('main.NavigationListener')
    @patch('sys.argv', ['main.py', '--port', '5000'])
    def test_main_port_argument(self, mock_listener_class):
        """Test main function with port argument"""
        mock_listener = Mock()
        mock_listener.start.return_value = True
        mock_listener_class.return_value = mock_listener
        
        # Mock config to verify it was changed
        original_port = config.UDP_PORT
        
        try:
            result = main()
            
            assert config.UDP_PORT == 5000
            assert result == 0
            mock_listener.start.assert_called_once()
        finally:
            # Restore original port
            config.UDP_PORT = original_port
    
    @patch('sys.argv', ['main.py', '--port', 'invalid'])
    @patch('builtins.print')
    def test_main_invalid_port(self, mock_print):
        """Test main function with invalid port"""
        result = main()
        
        assert result == 1
    
    @patch('main.NavigationListener')
    @patch('sys.argv', ['main.py', '--verbose'])
    def test_main_verbose_argument(self, mock_listener_class):
        """Test main function with verbose argument"""
        mock_listener = Mock()
        mock_listener.start.return_value = True
        mock_listener_class.return_value = mock_listener
        
        # Store original values
        original_raw_nmea = config.LOG_RAW_NMEA
        original_udp_traffic = config.LOG_UDP_TRAFFIC
        original_parse_attempts = config.LOG_PARSE_ATTEMPTS
        
        try:
            result = main()
            
            assert config.LOG_RAW_NMEA is True
            assert config.LOG_UDP_TRAFFIC is True
            assert config.LOG_PARSE_ATTEMPTS is True
            assert result == 0
        finally:
            # Restore original values
            config.LOG_RAW_NMEA = original_raw_nmea
            config.LOG_UDP_TRAFFIC = original_udp_traffic
            config.LOG_PARSE_ATTEMPTS = original_parse_attempts
    
    @patch('main.NavigationListener')
    @patch('sys.argv', ['main.py', '--no-clear'])
    def test_main_no_clear_argument(self, mock_listener_class):
        """Test main function with no-clear argument"""
        mock_listener = Mock()
        mock_listener.start.return_value = True
        mock_listener_class.return_value = mock_listener
        
        original_clear_screen = config.CLEAR_SCREEN
        
        try:
            result = main()
            
            assert config.CLEAR_SCREEN is False
            assert result == 0
        finally:
            config.CLEAR_SCREEN = original_clear_screen
    
    @patch('main.NavigationListener')
    @patch('sys.argv', ['main.py', '--adsb'])
    @patch('builtins.print')
    def test_main_adsb_argument(self, mock_print, mock_listener_class):
        """Test main function with ADS-B argument"""
        mock_listener = Mock()
        mock_listener.start.return_value = True
        mock_listener_class.return_value = mock_listener
        
        original_protocol_mode = config.PROTOCOL_MODE
        
        try:
            result = main()
            
            assert config.PROTOCOL_MODE == 'adsb'
            assert result == 0
        finally:
            config.PROTOCOL_MODE = original_protocol_mode
    
    @patch('main.NavigationListener')
    @patch('sys.argv', ['main.py', '--nmea'])
    @patch('builtins.print')
    def test_main_nmea_argument(self, mock_print, mock_listener_class):
        """Test main function with NMEA argument"""
        mock_listener = Mock()
        mock_listener.start.return_value = True
        mock_listener_class.return_value = mock_listener
        
        original_protocol_mode = config.PROTOCOL_MODE
        
        try:
            result = main()
            
            assert config.PROTOCOL_MODE == 'nmea'
            assert result == 0
        finally:
            config.PROTOCOL_MODE = original_protocol_mode
    
    @patch('main.NavigationListener')
    @patch('sys.argv', ['main.py', '--auto'])
    @patch('builtins.print')
    def test_main_auto_argument(self, mock_print, mock_listener_class):
        """Test main function with auto argument"""
        mock_listener = Mock()
        mock_listener.start.return_value = True
        mock_listener_class.return_value = mock_listener
        
        original_protocol_mode = config.PROTOCOL_MODE
        
        # Mock the imports that auto mode checks for
        with patch.dict('sys.modules', {'pyModeS': Mock(), 'serial': Mock()}):
            try:
                result = main()
                
                assert config.PROTOCOL_MODE == 'auto'
                assert result == 0
            finally:
                config.PROTOCOL_MODE = original_protocol_mode
    
    @patch('sys.argv', ['main.py', '--unknown-arg'])
    @patch('builtins.print')
    def test_main_unknown_argument(self, mock_print):
        """Test main function with unknown argument"""
        result = main()
        
        assert result == 1
    
    @patch('main.NavigationListener')
    @patch('sys.argv', ['main.py', '--adsb'])
    @patch('builtins.print')
    def test_main_missing_pymodes(self, mock_print, mock_listener_class):
        """Test main function when pyModeS is missing"""
        # Mock import error for pyModeS
        with patch('builtins.__import__', side_effect=ImportError("No module named 'pyModeS'")):
            result = main()
            
            assert result == 1
            mock_listener_class.assert_not_called()
    
    @patch('main.NavigationListener')
    @patch('sys.argv', ['main.py'])
    def test_main_listener_start_failure(self, mock_listener_class):
        """Test main function when listener fails to start"""
        mock_listener = Mock()
        mock_listener.start.return_value = False
        mock_listener_class.return_value = mock_listener
        
        result = main()
        
        assert result == 1
    
    @patch('main.NavigationListener')
    @patch('sys.argv', ['main.py'])
    def test_main_exception_handling(self, mock_listener_class):
        """Test main function handles exceptions gracefully"""
        mock_listener_class.side_effect = Exception("Test error")
        
        with patch('builtins.print') as mock_print:
            result = main()
            
            assert result == 1
            # Should print error message
            mock_print.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])