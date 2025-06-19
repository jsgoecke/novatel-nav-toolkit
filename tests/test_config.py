"""
Unit tests for config module
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


class TestConfig:
    """Test configuration settings and defaults"""
    
    def test_network_configuration_defaults(self):
        """Test network configuration defaults"""
        assert config.UDP_PORT == 4001
        assert config.UDP_HOST == '0.0.0.0'
        assert config.SOCKET_TIMEOUT == 5.0
        assert config.BUFFER_SIZE == 1024
    
    def test_display_configuration_defaults(self):
        """Test display configuration defaults"""
        assert config.UPDATE_INTERVAL == 1.0
        assert config.CLEAR_SCREEN is True
    
    def test_data_configuration_defaults(self):
        """Test data configuration defaults"""
        assert config.COORDINATE_PRECISION == 6
        assert config.ALTITUDE_UNITS == 'both'
        assert config.SPEED_UNITS == 'both'
    
    def test_protocol_configuration_defaults(self):
        """Test protocol configuration defaults"""
        assert config.PROTOCOL_MODE == 'nmea'
        assert config.ADSB_REFERENCE_LAT == 0.0
        assert config.ADSB_REFERENCE_LON == 0.0
    
    def test_logging_configuration_defaults(self):
        """Test logging configuration defaults"""
        assert config.ENABLE_LOGGING is True
        assert config.LOG_FILE == 'logs/navigation_data.log'
        assert config.LOG_RAW_NMEA is True
        assert config.LOG_UDP_TRAFFIC is True
        assert config.LOG_PARSE_ATTEMPTS is True
    
    def test_gdl90_configuration_defaults(self):
        """Test GDL-90 configuration defaults"""
        assert config.GDL90_ENABLED is True
        assert config.LOG_GDL90_FRAMES is True
        assert config.LOG_DEFRAMING_PROCESS is True
        assert config.GDL90_VALIDATE_CHECKSUMS is False
        assert config.GDL90_STRICT_FRAMING is True
    
    def test_error_handling_configuration_defaults(self):
        """Test error handling configuration defaults"""
        assert config.MAX_PARSE_ERRORS == 10
        assert config.RECONNECT_DELAY == 5.0
    
    def test_config_values_types(self):
        """Test that configuration values have expected types"""
        assert isinstance(config.UDP_PORT, int)
        assert isinstance(config.UDP_HOST, str)
        assert isinstance(config.SOCKET_TIMEOUT, float)
        assert isinstance(config.BUFFER_SIZE, int)
        assert isinstance(config.UPDATE_INTERVAL, float)
        assert isinstance(config.CLEAR_SCREEN, bool)
        assert isinstance(config.COORDINATE_PRECISION, int)
        assert isinstance(config.ALTITUDE_UNITS, str)
        assert isinstance(config.SPEED_UNITS, str)
        assert isinstance(config.PROTOCOL_MODE, str)
        assert isinstance(config.ENABLE_LOGGING, bool)
        assert isinstance(config.GDL90_ENABLED, bool)
    
    def test_config_values_ranges(self):
        """Test that configuration values are within expected ranges"""
        assert 1 <= config.UDP_PORT <= 65535
        assert config.SOCKET_TIMEOUT > 0
        assert config.BUFFER_SIZE > 0
        assert config.UPDATE_INTERVAL > 0
        assert config.COORDINATE_PRECISION >= 0
        assert config.ALTITUDE_UNITS in ['feet', 'meters', 'both']
        assert config.SPEED_UNITS in ['knots', 'kmh', 'mph', 'both']
        assert config.PROTOCOL_MODE in ['nmea', 'adsb', 'auto']