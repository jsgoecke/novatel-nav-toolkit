#!/usr/bin/env python3
"""
Integration tests for PASSCOM/PASSTHROUGH functionality in ADS-B Parser

Tests the complete integration of the NovAtel PASSCOM parser with the
enhanced ADS-B parser system.
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adsb_parser import ADSBParser
import config


class TestPasscomIntegration(unittest.TestCase):
    """Test PASSCOM integration with ADS-B parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = ADSBParser()
        
        # Real PASSCOM data sample
        self.passcom_sample = bytes.fromhex(
            "5265636569766564207061636b65742066726f6d203139322e3136382e342e313a36313730383a20"
            "7e26002b4a28fa38a6857cf38a3e0b1c2f9e0ecfa54d0831ef43eda1b7a6e3a673190cc52f6dbba9c"
            "a5ee12d7a2bea1dbfd5a2baccb84211da7ba943dd31a58a230f44334593087e"
        )
    
    def test_passcom_detection_integration(self):
        """Test that PASSCOM data is properly detected in the ADS-B parser"""
        # Should detect PASSCOM wrapper
        is_passcom = self.parser._is_passcom_wrapped(self.passcom_sample)
        self.assertTrue(is_passcom)
        
        # Should NOT detect as GDL-90
        is_gdl90 = self.parser._is_gdl90_wrapped(self.passcom_sample)
        self.assertFalse(is_gdl90)
    
    def test_passcom_preprocessing_integration(self):
        """Test PASSCOM preprocessing integration"""
        # Should use PASSCOM parser for preprocessing
        with patch.object(self.parser.passcom_parser, 'parse_passcom_frame') as mock_passcom:
            mock_passcom.return_value = [bytes.fromhex("8D4840D6202CC371C32CE0576098")]
            
            result = self.parser._preprocess_message(self.passcom_sample)
            
            # Should return Mode-S frames from PASSCOM parser
            self.assertEqual(len(result), 1)
            mock_passcom.assert_called_once_with(self.passcom_sample)
            
            # Should increment PASSCOM counter
            self.assertEqual(self.parser.passcom_messages_processed, 1)
    
    def test_passcom_full_pipeline_integration(self):
        """Test complete PASSCOM processing pipeline"""
        # Mock the PASSCOM parser and ADS-B decoding
        with patch.object(self.parser.passcom_parser, 'parse_passcom_frame') as mock_passcom:
            mock_passcom.return_value = [bytes.fromhex("8D4840D6202CC371C32CE0576098")]
            
            with patch('adsb_parser.adsb') as mock_adsb:
                mock_adsb.df.return_value = 17
                mock_adsb.icao.return_value = "4840D6"
                mock_adsb.typecode.return_value = 11
                
                # Mock altitude decoder
                with patch.object(self.parser.altitude_decoder, 'decode_altitude') as mock_altitude:
                    mock_altitude.return_value = {'altitude_baro_ft': 35000}
                    
                    result = self.parser.parse_message(self.passcom_sample)
                    
                    # Should successfully parse and extract data
                    self.assertIsNotNone(result)
                    self.assertEqual(result['icao'], "4840D6")
                    self.assertEqual(result['type_code'], 11)
                    self.assertEqual(result['altitude_baro_ft'], 35000)
    
    def test_passcom_statistics_integration(self):
        """Test that PASSCOM statistics are properly integrated"""
        # Process some PASSCOM data
        with patch.object(self.parser.passcom_parser, 'parse_passcom_frame') as mock_passcom:
            mock_passcom.return_value = [bytes.fromhex("8D4840D6202CC371C32CE0576098")]
            
            # Mock the PASSCOM parser stats
            mock_stats = {
                'frames_processed': 1,
                'success_rate': 100.0,
                'mode_s_frames_extracted': 1,
                'ascii_hex_conversions': 0
            }
            self.parser.passcom_parser.get_stats = MagicMock(return_value=mock_stats)
            
            # Process message
            self.parser._preprocess_message(self.passcom_sample)
            
            # Get integrated stats
            stats = self.parser.get_stats()
            
            # Should include PASSCOM stats
            self.assertGreater(stats['passcom_messages_processed'], 0)
            self.assertIn('passcom_frames_processed', stats)
            self.assertIn('passcom_success_rate', stats)
            self.assertIn('passcom_mode_s_frames', stats)
    
    def test_passcom_vs_gdl90_priority(self):
        """Test that PASSCOM detection takes priority over GDL-90"""
        # Create data that could be detected as both
        mixed_data = self.passcom_sample
        
        with patch.object(self.parser.gdl90_deframer, 'is_gdl90_frame', return_value=True):
            # Even if GDL-90 deframer thinks it's GDL-90, PASSCOM should take priority
            result = self.parser._preprocess_message(mixed_data)
            
            # Should have processed as PASSCOM, not GDL-90
            self.assertEqual(self.parser.passcom_messages_processed, 1)
            self.assertEqual(self.parser.gdl90_messages_processed, 0)
    
    def test_passcom_error_handling_integration(self):
        """Test error handling in PASSCOM integration"""
        # Test with corrupted PASSCOM data that has the wrapper but bad frame data
        corrupted_data = b"Received packet from 192.168.4.1:61708: \x7e\x26\xff\xff" + b"corrupted"
        
        # Should handle gracefully without crashing
        result = self.parser.parse_message(corrupted_data)
        
        # Should return None but not crash
        self.assertIsNone(result)
        
        # Should still have processed it as PASSCOM attempt
        self.assertGreater(self.parser.passcom_messages_processed, 0)


class TestAltitudeDecoderIntegration(unittest.TestCase):
    """Test altitude decoder integration with ADS-B parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = ADSBParser()
    
    def test_altitude_decoder_integration(self):
        """Test that altitude decoder is properly integrated"""
        test_message = "8D4840D6202CC371C32CE0576098"
        
        # Mock altitude decoder response
        with patch.object(self.parser.altitude_decoder, 'decode_altitude') as mock_altitude:
            mock_altitude.return_value = {
                'altitude_baro_ft': 35000,
                'altitude_decoded_at': '2024-01-01T12:00:00Z'
            }
            
            result = self.parser._extract_aviation_data(test_message, "4840D6", 11)
            
            # Should call altitude decoder
            mock_altitude.assert_called_once_with(test_message, 11)
            
            # Should include altitude data
            self.assertIn('altitude_baro_ft', result)
            self.assertEqual(result['altitude_baro_ft'], 35000)
    
    def test_geometric_altitude_integration(self):
        """Test geometric altitude decoding integration"""
        test_message = "8D4840D6F8220136E0A1473D8A14"  # Type Code 31
        
        # Enable geometric altitude in config
        original_geo = getattr(config, 'ENABLE_GEOMETRIC_ALTITUDE', True)
        config.ENABLE_GEOMETRIC_ALTITUDE = True
        
        try:
            with patch.object(self.parser.altitude_decoder, 'decode_altitude') as mock_altitude:
                mock_altitude.return_value = {'altitude_geo_ft': 35150}
                
                result = self.parser._extract_aviation_data(test_message, "4840D6", 31)
                
                # Should call altitude decoder for geometric altitude
                mock_altitude.assert_called_once_with(test_message, 31)
                
                # Should include geometric altitude
                self.assertIn('altitude_geo_ft', result)
                self.assertEqual(result['altitude_geo_ft'], 35150)
        finally:
            config.ENABLE_GEOMETRIC_ALTITUDE = original_geo
    
    def test_altitude_validation_integration(self):
        """Test that altitude validation is properly integrated"""
        test_message = "8D4840D6202CC371C32CE0576098"
        
        # Test with invalid altitude (should be filtered out)
        with patch.object(self.parser.altitude_decoder, 'decode_altitude') as mock_altitude:
            mock_altitude.return_value = None  # Decoder rejects invalid altitude
            
            result = self.parser._extract_aviation_data(test_message, "4840D6", 11)
            
            # Should still return basic data but no altitude data
            if result:
                self.assertNotIn('altitude_baro_ft', result)
                self.assertNotIn('altitude_geo_ft', result)
            else:
                # If result is None, that's also acceptable for invalid data
                self.assertIsNone(result)
    
    def test_altitude_statistics_integration(self):
        """Test altitude decoder statistics integration"""
        # Process some altitude data
        test_message = "8D4840D6202CC371C32CE0576098"
        
        with patch.object(self.parser.altitude_decoder, 'decode_altitude') as mock_altitude:
            mock_altitude.return_value = {'altitude_baro_ft': 35000}
            
            # Mock altitude decoder stats
            mock_stats = {
                'altitudes_decoded': 1,
                'barometric_altitudes': 1,
                'geometric_altitudes': 0,
                'success_rate': 100.0,
                'sanity_check_failures': 0
            }
            self.parser.altitude_decoder.get_stats = MagicMock(return_value=mock_stats)
            
            # Process message
            self.parser._extract_aviation_data(test_message, "4840D6", 11)
            
            # Get integrated stats
            stats = self.parser.get_stats()
            
            # Should include altitude decoder stats
            self.assertIn('altitudes_decoded', stats)
            self.assertIn('barometric_altitudes', stats)
            self.assertIn('altitude_decode_success_rate', stats)


if __name__ == '__main__':
    # Run the tests
    unittest.main(verbosity=2)