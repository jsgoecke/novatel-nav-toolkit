"""
Unit tests for NMEAParser module
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, PropertyMock
from datetime import datetime, timezone
import pynmea2

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nmea_parser import NMEAParser
import config


class TestNMEAParser:
    """Test NMEA sentence parsing functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.parser = NMEAParser()
    
    def test_initialization(self):
        """Test NMEAParser initialization"""
        assert self.parser.parse_error_count == 0
        assert self.parser.sentences_parsed == 0
        assert self.parser.last_valid_data == {}
    
    def test_parse_sentence_empty(self):
        """Test parsing of empty sentence"""
        result = self.parser.parse_sentence("")
        assert result is None
    
    def test_parse_sentence_whitespace(self):
        """Test parsing of whitespace-only sentence"""
        result = self.parser.parse_sentence("   \n\t  ")
        assert result is None
    
    def test_parse_sentence_no_dollar_sign(self):
        """Test parsing of sentence without $ prefix"""
        result = self.parser.parse_sentence("GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47")
        assert result is None
    
    @patch('config.LOG_PARSE_ATTEMPTS', False)
    def test_parse_sentence_valid_gga(self):
        """Test parsing of valid GGA sentence"""
        gga_sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        
        result = self.parser.parse_sentence(gga_sentence)
        
        assert result is not None
        assert 'latitude' in result
        assert 'longitude' in result
        assert 'altitude_m' in result
        assert 'gps_quality' in result
        assert 'satellites' in result
        assert 'parsed_timestamp' in result
        assert self.parser.sentences_parsed == 1
    
    @patch('config.LOG_PARSE_ATTEMPTS', False)
    def test_parse_sentence_valid_rmc(self):
        """Test parsing of valid RMC sentence"""
        rmc_sentence = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        
        result = self.parser.parse_sentence(rmc_sentence)
        
        assert result is not None
        assert 'latitude' in result
        assert 'longitude' in result
        assert 'speed_knots' in result
        assert 'heading' in result
        assert 'status' in result
        assert 'parsed_timestamp' in result
        assert self.parser.sentences_parsed == 1
    
    @patch('config.LOG_PARSE_ATTEMPTS', False)
    def test_parse_sentence_valid_vtg(self):
        """Test parsing of valid VTG sentence"""
        vtg_sentence = "$GPVTG,054.7,T,034.4,M,005.5,N,010.2,K*48"
        
        result = self.parser.parse_sentence(vtg_sentence)
        
        assert result is not None
        assert 'heading' in result
        assert 'speed_knots' in result
        assert 'speed_kmh' in result
        assert 'parsed_timestamp' in result
        assert self.parser.sentences_parsed == 1
    
    @patch('config.LOG_PARSE_ATTEMPTS', False)
    def test_parse_sentence_valid_gll(self):
        """Test parsing of valid GLL sentence"""
        gll_sentence = "$GPGLL,4807.038,N,01131.000,E,123519,A,*09"
        
        result = self.parser.parse_sentence(gll_sentence)
        
        assert result is not None
        assert 'latitude' in result
        assert 'longitude' in result
        assert 'status' in result
        assert 'parsed_timestamp' in result
        assert self.parser.sentences_parsed == 1
    
    def test_parse_sentence_invalid_checksum(self):
        """Test parsing of sentence with invalid checksum"""
        invalid_sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*00"
        
        # Should raise exception due to invalid checksum
        result = self.parser.parse_sentence(invalid_sentence)
        assert result is None
        assert self.parser.parse_error_count == 1
    
    def test_parse_sentence_malformed(self):
        """Test parsing of malformed sentence"""
        malformed_sentence = "$GPGGA,broken,sentence,format"
        
        result = self.parser.parse_sentence(malformed_sentence)
        assert result is None
        assert self.parser.parse_error_count == 1
    
    def test_extract_navigation_data_gga(self):
        """Test extraction of navigation data from GGA message"""
        # Create mock GGA message
        mock_msg = Mock()
        mock_msg.sentence_type = 'GGA'
        mock_msg.latitude = 48.1173
        mock_msg.longitude = 11.5167
        mock_msg.lat_dir = 'N'
        mock_msg.lon_dir = 'E'
        mock_msg.altitude = 545.4
        mock_msg.gps_qual = 1
        mock_msg.num_sats = 8
        mock_msg.timestamp = datetime.now().time()
        
        result = self.parser._extract_navigation_data(mock_msg)
        
        assert result is not None
        assert result['latitude'] == 48.1173
        assert result['longitude'] == 11.5167
        assert result['latitude_dir'] == 'N'
        assert result['longitude_dir'] == 'E'
        assert result['altitude_m'] == 545.4
        assert result['gps_quality'] == 1
        assert result['satellites'] == 8
        assert 'parsed_timestamp' in result
    
    def test_extract_navigation_data_rmc(self):
        """Test extraction of navigation data from RMC message"""
        mock_msg = Mock()
        mock_msg.sentence_type = 'RMC'
        mock_msg.latitude = 48.1173
        mock_msg.longitude = 11.5167
        mock_msg.lat_dir = 'N'
        mock_msg.lon_dir = 'E'
        mock_msg.spd_over_grnd = 22.4
        mock_msg.true_course = 84.4
        mock_msg.timestamp = datetime.now().time()
        mock_msg.datestamp = datetime.now().date()
        mock_msg.status = 'A'
        
        result = self.parser._extract_navigation_data(mock_msg)
        
        assert result is not None
        assert result['latitude'] == 48.1173
        assert result['longitude'] == 11.5167
        assert result['speed_knots'] == 22.4
        assert result['heading'] == 84.4
        assert result['status'] == 'A'
    
    def test_extract_navigation_data_vtg(self):
        """Test extraction of navigation data from VTG message"""
        mock_msg = Mock()
        mock_msg.sentence_type = 'VTG'
        mock_msg.true_track = 54.7
        mock_msg.spd_over_grnd_kts = 5.5
        mock_msg.spd_over_grnd_kmph = 10.2
        
        result = self.parser._extract_navigation_data(mock_msg)
        
        assert result is not None
        assert result['heading'] == 54.7
        assert result['speed_knots'] == 5.5
        assert result['speed_kmh'] == 10.2
    
    def test_extract_navigation_data_gll(self):
        """Test extraction of navigation data from GLL message"""
        mock_msg = Mock()
        mock_msg.sentence_type = 'GLL'
        mock_msg.latitude = 48.1173
        mock_msg.longitude = 11.5167
        mock_msg.lat_dir = 'N'
        mock_msg.lon_dir = 'E'
        mock_msg.timestamp = datetime.now().time()
        mock_msg.status = 'A'
        
        result = self.parser._extract_navigation_data(mock_msg)
        
        assert result is not None
        assert result['latitude'] == 48.1173
        assert result['longitude'] == 11.5167
        assert result['status'] == 'A'
    
    def test_extract_navigation_data_unknown_type(self):
        """Test extraction from unknown sentence type"""
        mock_msg = Mock()
        mock_msg.sentence_type = 'XXX'
        
        result = self.parser._extract_navigation_data(mock_msg)
        
        assert result is None
    
    def test_extract_navigation_data_with_none_values(self):
        """Test extraction handling None values"""
        mock_msg = Mock()
        mock_msg.sentence_type = 'GGA'
        mock_msg.latitude = None
        mock_msg.longitude = None
        mock_msg.altitude = None
        mock_msg.gps_qual = None
        mock_msg.num_sats = None
        mock_msg.timestamp = None
        
        result = self.parser._extract_navigation_data(mock_msg)
        
        # Should return empty dict (which becomes None due to length check)
        assert result is None
    
    def test_extract_navigation_data_exception(self):
        """Test extraction with exception"""
        mock_msg = Mock()
        mock_msg.sentence_type = 'GGA'
        # Make latitude access raise an exception
        type(mock_msg).latitude = PropertyMock(side_effect=Exception("Test error"))
        
        result = self.parser._extract_navigation_data(mock_msg)
        
        assert result is None
    
    def test_get_latest_navigation_data_with_coordinates(self):
        """Test getting latest navigation data with coordinate conversion"""
        self.parser.last_valid_data = {
            'latitude': 48.1173,
            'longitude': 11.5167,
            'latitude_dir': 'N',
            'longitude_dir': 'E',
            'altitude_m': 545.4,
            'speed_knots': 22.4
        }
        
        result = self.parser.get_latest_navigation_data()
        
        assert result['latitude_decimal'] == 48.1173  # North, so positive
        assert result['longitude_decimal'] == 11.5167  # East, so positive
        assert result['altitude_ft'] == round(545.4 * 3.28084, 1)
        assert result['speed_kmh'] == round(22.4 * 1.852, 1)
        assert result['speed_mph'] == round(22.4 * 1.15078, 1)
    
    def test_get_latest_navigation_data_southern_hemisphere(self):
        """Test coordinate conversion for southern hemisphere"""
        self.parser.last_valid_data = {
            'latitude': 33.8688,
            'longitude': 151.2093,
            'latitude_dir': 'S',
            'longitude_dir': 'E'
        }
        
        result = self.parser.get_latest_navigation_data()
        
        assert result['latitude_decimal'] == -33.8688  # South, so negative
        assert result['longitude_decimal'] == 151.2093  # East, so positive
    
    def test_get_latest_navigation_data_western_hemisphere(self):
        """Test coordinate conversion for western hemisphere"""
        self.parser.last_valid_data = {
            'latitude': 40.7128,
            'longitude': 74.0060,
            'latitude_dir': 'N',
            'longitude_dir': 'W'
        }
        
        result = self.parser.get_latest_navigation_data()
        
        assert result['latitude_decimal'] == 40.7128  # North, so positive
        assert result['longitude_decimal'] == -74.0060  # West, so negative
    
    def test_get_latest_navigation_data_no_coordinates(self):
        """Test getting latest data without coordinates"""
        self.parser.last_valid_data = {
            'altitude_m': 545.4,
            'speed_knots': 22.4
        }
        
        result = self.parser.get_latest_navigation_data()
        
        assert 'latitude_decimal' not in result
        assert 'longitude_decimal' not in result
        assert result['altitude_ft'] == round(545.4 * 3.28084, 1)
    
    def test_get_latest_navigation_data_empty(self):
        """Test getting latest data when empty"""
        result = self.parser.get_latest_navigation_data()
        
        assert result == {}
    
    def test_get_latest_navigation_data_is_copy(self):
        """Test that returned data is a copy"""
        self.parser.last_valid_data = {'test': 'value'}
        
        result = self.parser.get_latest_navigation_data()
        
        assert result is not self.parser.last_valid_data
        result['new_key'] = 'new_value'
        assert 'new_key' not in self.parser.last_valid_data
    
    def test_get_stats(self):
        """Test getting parser statistics"""
        self.parser.sentences_parsed = 100
        self.parser.parse_error_count = 5
        
        stats = self.parser.get_stats()
        
        assert stats['sentences_parsed'] == 100
        assert stats['parse_errors'] == 5
        assert stats['success_rate'] == 95.2  # 100/(100+5) * 100, rounded to 1 decimal
    
    def test_get_stats_no_data(self):
        """Test getting statistics with no data"""
        stats = self.parser.get_stats()
        
        assert stats['sentences_parsed'] == 0
        assert stats['parse_errors'] == 0
        assert stats['success_rate'] == 0.0
    
    def test_reset_stats(self):
        """Test resetting parser statistics"""
        self.parser.sentences_parsed = 100
        self.parser.parse_error_count = 5
        
        self.parser.reset_stats()
        
        assert self.parser.sentences_parsed == 0
        assert self.parser.parse_error_count == 0
    
    def test_last_valid_data_accumulation(self):
        """Test that last_valid_data accumulates correctly"""
        # First parse
        gga_sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        result1 = self.parser.parse_sentence(gga_sentence)
        
        assert 'latitude' in self.parser.last_valid_data
        assert 'altitude_m' in self.parser.last_valid_data
        
        # Second parse with different data
        rmc_sentence = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        result2 = self.parser.parse_sentence(rmc_sentence)
        
        # Should accumulate data
        assert 'latitude' in self.parser.last_valid_data  # From both
        assert 'altitude_m' in self.parser.last_valid_data  # From GGA
        assert 'speed_knots' in self.parser.last_valid_data  # From RMC
        assert 'heading' in self.parser.last_valid_data  # From RMC
    
    @patch('config.COORDINATE_PRECISION', 2)
    def test_coordinate_precision_config(self):
        """Test that coordinate precision respects config"""
        self.parser.last_valid_data = {
            'latitude': 48.123456789,
            'longitude': 11.987654321,
            'latitude_dir': 'N',
            'longitude_dir': 'E'
        }
        
        result = self.parser.get_latest_navigation_data()
        
        assert result['latitude_decimal'] == 48.12  # Rounded to 2 decimal places
        assert result['longitude_decimal'] == 11.99  # Rounded to 2 decimal places


if __name__ == "__main__":
    pytest.main([__file__])