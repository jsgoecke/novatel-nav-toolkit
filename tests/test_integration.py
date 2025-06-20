"""
Integration tests for the entire navigation system
"""

import pytest
import sys
import os
import threading
import time
import socket
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import NavigationListener
from udp_listener import UDPListener
from nmea_parser import NMEAParser
from adsb_parser import ADSBParser
from navigation_display import NavigationDisplay
import config


class TestSystemIntegration:
    """Test integration of all system components"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Store original config values
        self.original_config = {
            'LOG_PARSE_ATTEMPTS': config.LOG_PARSE_ATTEMPTS,
            'LOG_UDP_TRAFFIC': config.LOG_UDP_TRAFFIC,
            'LOG_RAW_NMEA': config.LOG_RAW_NMEA,
            'LOG_DEFRAMING_PROCESS': config.LOG_DEFRAMING_PROCESS,
            'CLEAR_SCREEN': config.CLEAR_SCREEN
        }
        
        # Disable logging for tests
        config.LOG_PARSE_ATTEMPTS = False
        config.LOG_UDP_TRAFFIC = False
        config.LOG_RAW_NMEA = False
        config.LOG_DEFRAMING_PROCESS = False
        config.CLEAR_SCREEN = False
    
    def teardown_method(self):
        """Restore original config"""
        for key, value in self.original_config.items():
            setattr(config, key, value)
    
    def test_nmea_end_to_end_processing(self):
        """Test complete NMEA processing pipeline"""
        # Create components
        nmea_parser = NMEAParser()
        display = NavigationDisplay()
        
        # Test data
        gga_sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        rmc_sentence = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        
        # Process sentences
        gga_result = nmea_parser.parse_sentence(gga_sentence)
        rmc_result = nmea_parser.parse_sentence(rmc_sentence)
        
        # Verify parsing worked
        assert gga_result is not None
        assert rmc_result is not None
        
        # Get combined navigation data
        nav_data = nmea_parser.get_latest_navigation_data()
        
        # Verify data accumulation
        assert 'latitude_decimal' in nav_data
        assert 'longitude_decimal' in nav_data
        assert 'altitude_ft' in nav_data
        assert 'speed_knots' in nav_data
        assert 'heading' in nav_data
        
        # Test display formatting
        parser_stats = nmea_parser.get_stats()
        display_output = display.format_navigation_data(nav_data, parser_stats)
        
        # Verify display contains expected data
        assert "48.117300°N, 11.516667°E" in display_output
        assert "NMEA sentences parsed: 2" in display_output
        assert "Success rate:" in display_output
    
    def test_adsb_end_to_end_processing(self):
        """Test complete ADS-B processing pipeline"""
        # Create components
        adsb_parser = ADSBParser()
        display = NavigationDisplay()
        
        # Test with GDL-90 wrapped ADS-B data
        gdl90_data = bytes.fromhex("7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E")
        
        # Mock PASSCOM parser to return False so GDL-90 path is taken
        with patch.object(adsb_parser, '_is_passcom_wrapped', return_value=False):
            # Mock GDL-90 deframing
            with patch.object(adsb_parser.gdl90_deframer, 'is_gdl90_frame', return_value=True):
                with patch.object(adsb_parser.gdl90_deframer, 'deframe_message') as mock_deframe:
                    # Mock deframer to return valid ADS-B message
                    mock_deframe.return_value = [bytes.fromhex("8D4840D6202CC371C32CE0576098")]
                    
                    # Mock pyModeS responses for the expected deframed message
                    with patch('adsb_parser.adsb') as mock_adsb:
                        mock_adsb.df.return_value = 17
                        mock_adsb.icao.return_value = "4840D6"
                        mock_adsb.typecode.return_value = 4
                        mock_adsb.callsign.return_value = "UAL1234 "
                        mock_adsb.category.return_value = 2
                        
                        # Process message
                        result = adsb_parser.parse_message(gdl90_data)
                        
                        # Verify parsing worked
                        assert result is not None
                        assert result['icao'] == "4840D6"
                        assert result['callsign'] == "UAL1234"
            
            # Get aviation data
            aviation_data = adsb_parser.get_latest_aviation_data()
            
            # Verify data
            assert aviation_data['icao'] == "4840D6"
            assert aviation_data['callsign'] == "UAL1234"
            
            # Test display formatting
            parser_stats = adsb_parser.get_stats()
            display_output = display.format_navigation_data(aviation_data, parser_stats)
            
            # Verify display contains expected data
            assert "Novatel ProPak6 Aviation Data (ADS-B)" in display_output
            assert "ICAO:      4840D6" in display_output
            assert "Callsign:  UAL1234" in display_output
    
    def test_udp_listener_integration(self):
        """Test UDP listener integration with parsers"""
        received_data = []
        
        def data_callback(data):
            received_data.append(data)
        
        # Create UDP listener
        listener = UDPListener(data_callback)
        
        # Test is_listening when not started
        assert listener.is_listening() is False
        
        # Test stats
        stats = listener.get_stats()
        assert stats['listening'] is False
        assert stats['error_count'] == 0
        assert stats['port'] == config.UDP_PORT
        assert stats['host'] == config.UDP_HOST
        
        # Note: We can't easily test actual UDP communication without
        # complex mocking or real network setup, so we test the interface
    
    @patch('config.PROTOCOL_MODE', 'auto')
    def test_auto_protocol_detection(self):
        """Test automatic protocol detection"""
        with patch('main.signal.signal'):
            listener = NavigationListener()
        
        # Test NMEA detection
        nmea_data = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        
        with patch.object(listener.nmea_parser, 'parse_sentence') as mock_nmea_parse:
            mock_nmea_parse.return_value = {'latitude': 48.1173}
            
            listener._handle_udp_data(nmea_data)
            
            mock_nmea_parse.assert_called_once()
        
        # Test ADS-B detection
        adsb_data = bytes.fromhex("8D4840D6202CC371C32CE0576098")
        
        with patch.object(listener.adsb_parser, 'parse_message') as mock_adsb_parse:
            mock_adsb_parse.return_value = {'icao': '4840D6'}
            
            listener._handle_udp_data(adsb_data)
            
            mock_adsb_parse.assert_called_once()
    
    def test_statistics_aggregation(self):
        """Test that statistics are properly aggregated across components"""
        nmea_parser = NMEAParser()
        adsb_parser = ADSBParser()
        display = NavigationDisplay()
        
        # Process some NMEA data
        nmea_parser.parse_sentence("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47")
        nmea_parser.parse_sentence("$GPGGA,broken,sentence,format")  # This should increment error count
        
        # Process some ADS-B data
        with patch('adsb_parser.adsb') as mock_adsb:
            mock_adsb.df.return_value = 17
            mock_adsb.icao.return_value = "4840D6"
            mock_adsb.typecode.return_value = 4
            
            adsb_parser.parse_message(bytes.fromhex("8D4840D6202CC371C32CE0576098"))
        
        # Display some data
        display.display({'test': 'data'})
        display.display({'test': 'data2'})
        
        # Get all statistics
        nmea_stats = nmea_parser.get_stats()
        adsb_stats = adsb_parser.get_stats()
        display_stats = display.get_stats()
        
        # Verify statistics
        assert nmea_stats['sentences_parsed'] == 1  # Only valid sentence counted
        assert nmea_stats['parse_errors'] == 1
        assert adsb_stats['messages_parsed'] == 1
        assert display_stats['displays_rendered'] == 2
    
    def test_error_handling_robustness(self):
        """Test that components handle errors gracefully"""
        nmea_parser = NMEAParser()
        adsb_parser = ADSBParser()
        
        # Test NMEA parser with various invalid inputs
        invalid_inputs = [
            "",  # Empty
            "NotNMEA",  # No $ prefix
            "$GPGGA,invalid,checksum*00",  # Invalid checksum
            "$GPGGA,malformed,data",  # Malformed
            None  # None input (should be handled by caller)
        ]
        
        for invalid_input in invalid_inputs:
            if invalid_input is not None:
                result = nmea_parser.parse_sentence(invalid_input)
                assert result is None  # Should handle gracefully
        
        # Test ADS-B parser with invalid inputs
        invalid_adsb_inputs = [
            b"",  # Empty bytes
            b"too_short",  # Too short
            b"invalid_binary_data_that_is_long_enough_but_not_valid",  # Invalid but long enough
        ]
        
        for invalid_input in invalid_adsb_inputs:
            result = adsb_parser.parse_message(invalid_input)
            # Should either return None or handle gracefully without crashing
            assert result is None or isinstance(result, dict)
    
    def test_configuration_impact(self):
        """Test that configuration changes affect system behavior"""
        display = NavigationDisplay()
        
        # Test coordinate precision
        nav_data = {
            'latitude_decimal': 48.123456789,
            'longitude_decimal': 11.987654321
        }
        
        with patch('config.COORDINATE_PRECISION', 2):
            result = display.format_navigation_data(nav_data)
            assert "48.12°N, 11.99°E" in result
        
        with patch('config.COORDINATE_PRECISION', 4):
            result = display.format_navigation_data(nav_data)
            assert "48.1235°N, 11.9877°E" in result
        
        # Test altitude units
        nav_data_with_altitude = {
            'altitude_ft': 1000,
            'altitude_m': 305
        }
        
        with patch('config.ALTITUDE_UNITS', 'feet'):
            result = display.format_navigation_data(nav_data_with_altitude)
            assert "1,000 ft" in result
            assert " m" not in result
        
        with patch('config.ALTITUDE_UNITS', 'meters'):
            result = display.format_navigation_data(nav_data_with_altitude)
            assert "305 m" in result
            assert " ft" not in result
        
        with patch('config.ALTITUDE_UNITS', 'both'):
            result = display.format_navigation_data(nav_data_with_altitude)
            assert "1,000 ft (305 m)" in result
    
    def test_data_flow_consistency(self):
        """Test that data flows consistently through the system"""
        # This test verifies that data parsed by one component
        # is properly accessible by other components
        
        nmea_parser = NMEAParser()
        
        # Parse a sentence with position data
        gga_sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        result = nmea_parser.parse_sentence(gga_sentence)
        
        # Verify initial parsing
        assert result is not None
        assert 'latitude' in result
        assert 'longitude' in result
        
        # Get the processed navigation data
        nav_data = nmea_parser.get_latest_navigation_data()
        
        # Verify coordinate conversion
        assert nav_data['latitude_decimal'] == 48.1173  # Should be positive (North)
        assert nav_data['longitude_decimal'] == 11.516667  # Should be positive (East)
        
        # Parse another sentence with speed data
        rmc_sentence = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        result2 = nmea_parser.parse_sentence(rmc_sentence)
        
        # Get updated navigation data
        updated_nav_data = nmea_parser.get_latest_navigation_data()
        
        # Verify data accumulation - should have both position and speed
        assert 'latitude_decimal' in updated_nav_data
        assert 'longitude_decimal' in updated_nav_data
        assert 'speed_knots' in updated_nav_data
        assert 'heading' in updated_nav_data
        
        # Verify unit conversions are applied
        assert 'speed_kmh' in updated_nav_data
        assert 'speed_mph' in updated_nav_data
        assert 'altitude_ft' in updated_nav_data  # From GGA sentence


if __name__ == "__main__":
    pytest.main([__file__])