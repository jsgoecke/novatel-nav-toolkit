"""
Unit tests for ADSBParser module
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adsb_parser import ADSBParser
import config


class TestADSBParser:
    """Test ADS-B message parsing functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.parser = ADSBParser()
    
    def test_initialization(self):
        """Test ADSBParser initialization"""
        assert self.parser.parse_error_count == 0
        assert self.parser.messages_parsed == 0
        assert self.parser.last_valid_data == {}
        assert self.parser.aircraft_data == {}
        assert self.parser.gdl90_messages_processed == 0
        assert self.parser.raw_messages_processed == 0
        assert self.parser.gdl90_deframer is not None
    
    def test_parse_message_empty(self):
        """Test parsing of empty message"""
        result = self.parser.parse_message(b'')
        assert result is None
    
    def test_parse_message_none(self):
        """Test parsing of None message"""
        result = self.parser.parse_message(None)
        assert result is None
    
    @patch('config.LOG_PARSE_ATTEMPTS', False)
    def test_parse_message_gdl90_wrapped(self):
        """Test parsing of GDL-90 wrapped message"""
        # Sample GDL-90 wrapped ADS-B message
        gdl90_data = bytes.fromhex("7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E")
        
        with patch.object(self.parser.gdl90_deframer, 'is_gdl90_frame', return_value=True):
            with patch.object(self.parser.gdl90_deframer, 'deframe_message') as mock_deframe:
                # Mock deframer to return valid ADS-B message
                mock_deframe.return_value = [bytes.fromhex("8D4840D6202CC371C32CE0576098")]
                
                with patch('adsb_parser.adsb') as mock_adsb:
                    mock_adsb.df.return_value = 17
                    mock_adsb.icao.return_value = "4840D6"
                    mock_adsb.typecode.return_value = 4
                    mock_adsb.callsign.return_value = "UAL1234 "
                    mock_adsb.category.return_value = 2
                    
                    result = self.parser.parse_message(gdl90_data)
                    
                    assert result is not None
                    assert 'icao' in result
                    assert result['icao'] == "4840D6"
                    assert self.parser.gdl90_messages_processed == 1
    
    @patch('config.LOG_PARSE_ATTEMPTS', False)
    def test_parse_message_raw_adsb(self):
        """Test parsing of raw ADS-B message"""
        # Raw ADS-B message (DF 17)
        raw_adsb = bytes.fromhex("8D4840D6202CC371C32CE0576098")
        
        with patch.object(self.parser.gdl90_deframer, 'is_gdl90_frame', return_value=False):
            with patch('adsb_parser.adsb') as mock_adsb:
                mock_adsb.df.return_value = 17
                mock_adsb.icao.return_value = "4840D6"
                mock_adsb.typecode.return_value = 4
                mock_adsb.callsign.return_value = "UAL1234 "
                mock_adsb.category.return_value = 2
                
                result = self.parser.parse_message(raw_adsb)
                
                assert result is not None
                assert 'icao' in result
                assert result['icao'] == "4840D6"
                assert self.parser.raw_messages_processed == 1
    
    def test_is_gdl90_wrapped(self):
        """Test GDL-90 frame detection"""
        # Should delegate to GDL90Deframer
        test_data = b'test_data'
        
        with patch.object(self.parser.gdl90_deframer, 'is_gdl90_frame') as mock_is_gdl90:
            mock_is_gdl90.return_value = True
            
            result = self.parser._is_gdl90_wrapped(test_data)
            
            assert result is True
            mock_is_gdl90.assert_called_once_with(test_data)
    
    def test_preprocess_message_gdl90(self):
        """Test message preprocessing for GDL-90 data"""
        gdl90_data = bytes.fromhex("7E26008B9A7E479967CCD9C82B84D1FFEBCCA07E")
        
        with patch.object(self.parser, '_is_gdl90_wrapped', return_value=True):
            with patch.object(self.parser.gdl90_deframer, 'deframe_message') as mock_deframe:
                mock_deframe.return_value = [bytes.fromhex("8B9A7E479967CCD9C82B84D1FFEBCCA0")]
                
                result = self.parser._preprocess_message(gdl90_data)
                
                assert len(result) == 1
                assert self.parser.gdl90_messages_processed == 1
    
    def test_preprocess_message_raw(self):
        """Test message preprocessing for raw data"""
        raw_data = bytes.fromhex("8D4840D6202CC371C32CE0576098")
        
        with patch.object(self.parser, '_is_gdl90_wrapped', return_value=False):
            result = self.parser._preprocess_message(raw_data)
            
            assert len(result) == 1
            assert result[0] == raw_data
            assert self.parser.raw_messages_processed == 1
    
    @patch('config.LOG_PARSE_ATTEMPTS', False)
    def test_parse_adsb_payload_invalid_df(self):
        """Test parsing ADS-B payload with invalid downlink format"""
        # Message with DF != 17,18,19
        invalid_adsb = bytes.fromhex("404840D6202CC371C32CE0576098")
        
        with patch('adsb_parser.adsb.df', return_value=16):  # Invalid DF
            result = self.parser._parse_adsb_payload(invalid_adsb)
            
            assert result is None
    
    @patch('config.LOG_PARSE_ATTEMPTS', False)
    def test_parse_adsb_payload_valid_df17(self):
        """Test parsing valid DF 17 ADS-B payload"""
        valid_adsb = bytes.fromhex("8D4840D6202CC371C32CE0576098")
        
        with patch('adsb_parser.adsb') as mock_adsb:
            mock_adsb.df.return_value = 17
            mock_adsb.icao.return_value = "4840D6"
            mock_adsb.typecode.return_value = 4
            mock_adsb.callsign.return_value = "UAL1234 "
            mock_adsb.category.return_value = 2
            
            result = self.parser._parse_adsb_payload(valid_adsb)
            
            assert result is not None
            assert result['icao'] == "4840D6"
            assert result['type_code'] == 4
            assert result['callsign'] == "UAL1234"
            assert self.parser.messages_parsed == 1
    
    def test_parse_adsb_payload_hex_string_input(self):
        """Test parsing ADS-B payload with hex string input"""
        hex_string = "8D4840D6202CC371C32CE0576098"
        
        with patch('adsb_parser.adsb') as mock_adsb:
            mock_adsb.df.return_value = 17
            mock_adsb.icao.return_value = "4840D6"
            mock_adsb.typecode.return_value = 4
            
            result = self.parser._parse_adsb_payload(hex_string)
            
            # Should handle string input
            mock_adsb.df.assert_called_with(hex_string)
    
    def test_extract_aviation_data_identification(self):
        """Test extraction of aircraft identification data (TC 1-4)"""
        with patch('adsb_parser.adsb') as mock_adsb:
            mock_adsb.callsign.return_value = "UAL1234 "
            mock_adsb.category.return_value = 2
            
            result = self.parser._extract_aviation_data("test_msg", "4840D6", 4)
            
            assert result is not None
            assert result['icao'] == "4840D6"
            assert result['type_code'] == 4
            assert result['callsign'] == "UAL1234"
            assert result['category'] == 2
            assert 'parsed_timestamp' in result
    
    def test_extract_aviation_data_position(self):
        """Test extraction of position data (TC 9-18)"""
        with patch('adsb_parser.adsb') as mock_adsb:
            mock_adsb.position_with_ref.return_value = (37.7749, -122.4194)
            mock_adsb.altitude.return_value = 35000
            
            result = self.parser._extract_aviation_data("test_msg", "4840D6", 11)
            
            assert result is not None
            assert result['latitude'] == 37.7749
            assert result['longitude'] == -122.4194
            assert result['altitude_ft'] == 35000
    
    def test_extract_aviation_data_velocity(self):
        """Test extraction of velocity data (TC 19)"""
        with patch('adsb_parser.adsb') as mock_adsb:
            mock_adsb.velocity.return_value = (450, 280, 1500)  # speed, heading, vertical_rate
            
            result = self.parser._extract_aviation_data("test_msg", "4840D6", 19)
            
            assert result is not None
            assert result['speed_knots'] == 450
            assert result['heading'] == 280
            assert result['vertical_rate'] == 1500
    
    def test_extract_aviation_data_with_none_values(self):
        """Test extraction handling None values from pyModeS"""
        with patch('adsb_parser.adsb') as mock_adsb:
            mock_adsb.velocity.return_value = (None, 280, None)
            
            result = self.parser._extract_aviation_data("test_msg", "4840D6", 19)
            
            assert result is not None
            assert result['speed_knots'] is None
            assert result['heading'] == 280
            assert result['vertical_rate'] is None
    
    def test_extract_aviation_data_exception(self):
        """Test extraction with exception from pyModeS"""
        with patch('adsb_parser.adsb.callsign', side_effect=Exception("Parse error")):
            result = self.parser._extract_aviation_data("test_msg", "4840D6", 4)
            
            assert result is None
    
    def test_extract_aviation_data_insufficient_data(self):
        """Test extraction that returns insufficient data"""
        # Should return None if only basic fields are extracted
        result = self.parser._extract_aviation_data("test_msg", "4840D6", 99)  # Invalid TC
        
        assert result is None  # Only basic fields, should return None
    
    def test_get_latest_aviation_data(self):
        """Test getting latest aviation data"""
        test_data = {'icao': '4840D6', 'callsign': 'UAL1234'}
        self.parser.last_valid_data = test_data
        
        result = self.parser.get_latest_aviation_data()
        
        assert result == test_data
        assert result is not self.parser.last_valid_data  # Should be a copy
    
    def test_get_aircraft_data(self):
        """Test getting aircraft data"""
        test_data = {'4840D6': {'callsign': 'UAL1234'}}
        self.parser.aircraft_data = test_data
        
        result = self.parser.get_aircraft_data()
        
        assert result == test_data
        assert result is not self.parser.aircraft_data  # Should be a copy
    
    def test_get_stats(self):
        """Test getting parser statistics"""
        self.parser.messages_parsed = 10
        self.parser.parse_error_count = 2
        self.parser.aircraft_data = {'4840D6': {}, '123456': {}}
        self.parser.gdl90_messages_processed = 5
        self.parser.raw_messages_processed = 5
        
        with patch.object(self.parser.gdl90_deframer, 'get_stats') as mock_get_stats:
            mock_get_stats.return_value = {
                'frames_processed': 5,
                'adsb_messages_found': 3,
                'success_rate': 60.0
            }
            
            stats = self.parser.get_stats()
            
            assert stats['messages_parsed'] == 10
            assert stats['parse_errors'] == 2
            assert stats['success_rate'] == 83.3  # 10/(10+2) * 100, rounded to 1 decimal
            assert stats['aircraft_tracked'] == 2
            assert stats['gdl90_messages_processed'] == 5
            assert stats['raw_messages_processed'] == 5
            assert stats['gdl90_frames_processed'] == 5
            assert stats['gdl90_adsb_found'] == 3
            assert stats['gdl90_success_rate'] == 60.0
    
    def test_reset_stats(self):
        """Test resetting parser statistics"""
        # Set some non-zero values
        self.parser.parse_error_count = 5
        self.parser.messages_parsed = 10
        self.parser.gdl90_messages_processed = 3
        self.parser.raw_messages_processed = 7
        
        with patch.object(self.parser.gdl90_deframer, 'reset_stats') as mock_reset:
            self.parser.reset_stats()
            
            assert self.parser.parse_error_count == 0
            assert self.parser.messages_parsed == 0
            assert self.parser.gdl90_messages_processed == 0
            assert self.parser.raw_messages_processed == 0
            mock_reset.assert_called_once()
    
    def test_aircraft_data_accumulation(self):
        """Test that aircraft data accumulates correctly"""
        # First parse for aircraft
        with patch('adsb_parser.adsb') as mock_adsb:
            mock_adsb.df.return_value = 17
            mock_adsb.icao.return_value = "4840D6"
            mock_adsb.typecode.return_value = 4
            mock_adsb.callsign.return_value = "UAL1234 "
            mock_adsb.category.return_value = 2
            
            result1 = self.parser._parse_adsb_payload(bytes.fromhex("8D4840D6202CC371C32CE0576098"))
            
            assert "4840D6" in self.parser.aircraft_data
            assert self.parser.aircraft_data["4840D6"]["callsign"] == "UAL1234"
        
        # Second parse for same aircraft with position data
        with patch('adsb_parser.adsb') as mock_adsb:
            mock_adsb.df.return_value = 17
            mock_adsb.icao.return_value = "4840D6"
            mock_adsb.typecode.return_value = 11
            mock_adsb.position_with_ref.return_value = (37.7749, -122.4194)
            mock_adsb.altitude.return_value = 35000
            
            result2 = self.parser._parse_adsb_payload(bytes.fromhex("8D4840D658A302E6F15700D05448"))
            
            # Should accumulate data for same aircraft
            assert self.parser.aircraft_data["4840D6"]["callsign"] == "UAL1234"  # Previous data preserved
            assert self.parser.aircraft_data["4840D6"]["latitude"] == 37.7749  # New data added
    
    def test_parse_message_exception_handling(self):
        """Test that parse_message handles exceptions gracefully"""
        with patch.object(self.parser, '_preprocess_message', side_effect=Exception("Test error")):
            result = self.parser.parse_message(b'test_data')
            
            assert result is None
            assert self.parser.parse_error_count == 1


if __name__ == "__main__":
    pytest.main([__file__])