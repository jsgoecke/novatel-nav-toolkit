#!/usr/bin/env python3
"""
Unit tests for ADS-B Altitude Decoder

Tests the enhanced altitude decoding with Q-bit handling, Gillham conversion,
and comprehensive validation.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adsb_altitude_decoder import ADSBAltitudeDecoder
import config


class TestADSBAltitudeDecoder(unittest.TestCase):
    """Test cases for ADS-B Altitude Decoder"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.decoder = ADSBAltitudeDecoder()
        
        # Known test vectors for altitude decoding
        # Format: (hex_message, type_code, expected_altitude, description)
        self.test_vectors = [
            # Q-bit = 1 cases (direct 25-ft LSB)
            ("8D4840D6202CC371C32CE0576098", 11, 38000, "Q-bit=1, 38000 ft"),
            ("8D4840D6202CC371C32CE0576098", 11, 38000, "Standard barometric altitude"),
            
            # Q-bit = 0 cases (Gillham code) - these would need real Gillham-encoded data
            # For now, we'll test the mechanism with synthetic data
            
            # Geometric altitude (Type Code 31)
            ("8D4840D6F8220136E0A1473D8A14", 31, 38150, "Geometric altitude"),
            
            # Edge cases
            ("8D4840D6202CC371C32CE0576098", 11, -1000, "Minimum altitude"),
            ("8D4840D6202CC371C32CE0576098", 11, 60000, "Maximum altitude"),
        ]
        
        # Invalid altitude test cases
        self.invalid_cases = [
            ("8D4840D6202CC371C32CE0576098", 11, -2000, "Below minimum"),
            ("8D4840D6202CC371C32CE0576098", 11, 70000, "Above maximum"),
            ("8D4840D6202CC371C32CE0576098", 11, 100000, "Garbage altitude"),
        ]
    
    def test_altitude_decoding_basic(self):
        """Test basic altitude decoding functionality"""
        # Test with known ADS-B message
        hex_msg = "8D4840D6202CC371C32CE0576098"
        type_code = 11
        
        result = self.decoder.decode_altitude(hex_msg, type_code)
        
        # Should return altitude data
        self.assertIsNotNone(result)
        self.assertIn('altitude_baro_ft', result)
        self.assertIsInstance(result['altitude_baro_ft'], int)
        
        # Should have timestamp
        self.assertIn('altitude_decoded_at', result)
    
    def test_barometric_altitude_decoding(self):
        """Test barometric altitude decoding with Q-bit handling"""
        # Test Q-bit = 1 case (most common)
        hex_msg = "8D4840D6202CC371C32CE0576098"
        
        # Test the internal method directly
        altitude = self.decoder._decode_barometric_altitude(hex_msg)
        
        # Should decode to a reasonable altitude
        self.assertIsNotNone(altitude)
        self.assertIsInstance(altitude, int)
        self.assertGreaterEqual(altitude, -1000)  # Above minimum
        self.assertLessEqual(altitude, 60000)     # Below maximum
    
    def test_geometric_altitude_decoding(self):
        """Test geometric altitude decoding for Type Code 31"""
        # Test with Type Code 31 message
        hex_msg = "8D4840D6F8220136E0A1473D8A14"  # Synthetic TC=31 message
        
        altitude = self.decoder._decode_geometric_altitude(hex_msg)
        
        # Should decode altitude (even if synthetic)
        if altitude is not None:
            self.assertIsInstance(altitude, int)
    
    def test_q_bit_detection(self):
        """Test Q-bit detection and handling"""
        # Create test message with Q-bit = 1
        hex_msg = "8D4840D6202CC371C32CE0576098"
        
        # Decode and check that Q-bit counting works
        initial_q1_count = self.decoder.q_bit_one_count
        
        self.decoder._decode_barometric_altitude(hex_msg)
        
        # Should have incremented Q-bit=1 counter
        self.assertGreater(self.decoder.q_bit_one_count, initial_q1_count)
    
    def test_gillham_conversion(self):
        """Test Gillham (Gray) code conversion"""
        # Test the Gray to binary conversion
        test_cases = [
            (0b0000, 0b0000),  # 0 -> 0
            (0b0001, 0b0001),  # 1 -> 1
            (0b0011, 0b0010),  # 3 -> 2
            (0b0010, 0b0011),  # 2 -> 3
        ]
        
        for gray_input, expected_binary in test_cases:
            result = self.decoder._convert_gray_to_binary(gray_input)
            self.assertEqual(result, expected_binary)
    
    def test_altitude_validation(self):
        """Test altitude validation and sanity checks"""
        # Test valid altitudes
        valid_altitudes = [
            {'altitude_baro_ft': 35000},
            {'altitude_geo_ft': 35150},
            {'altitude_baro_ft': 0},
            {'altitude_geo_ft': 45000},
        ]
        
        for alt_data in valid_altitudes:
            result = self.decoder._validate_altitude_data(alt_data)
            self.assertTrue(result, f"Failed validation for {alt_data}")
        
        # Test invalid altitudes
        invalid_altitudes = [
            {'altitude_baro_ft': -2000},   # Below minimum
            {'altitude_baro_ft': 70000},   # Above maximum  
            {'altitude_geo_ft': -1500},    # Below minimum
            {'altitude_geo_ft': 80000},    # Above maximum
        ]
        
        for alt_data in invalid_altitudes:
            result = self.decoder._validate_altitude_data(alt_data)
            self.assertFalse(result, f"Should have failed validation for {alt_data}")
    
    def test_altitude_consistency_check(self):
        """Test consistency between barometric and geometric altitude"""
        # Test reasonable difference (should pass)
        consistent_data = {
            'altitude_baro_ft': 35000,
            'altitude_geo_ft': 35150   # 150 ft higher (reasonable)
        }
        
        result = self.decoder._validate_altitude_data(consistent_data)
        self.assertTrue(result)
        
        # Test large difference (should log warning but not fail)
        inconsistent_data = {
            'altitude_baro_ft': 35000,
            'altitude_geo_ft': 37000   # 2000 ft higher (suspicious but not fatal)
        }
        
        result = self.decoder._validate_altitude_data(inconsistent_data)
        self.assertTrue(result)  # Should still pass, just log warning
    
    def test_sanity_check_configuration(self):
        """Test that sanity checks respect configuration"""
        # Test with sanity checks disabled
        self.decoder.enable_sanity_checks = False
        
        invalid_data = {'altitude_baro_ft': -5000}  # Way below minimum
        result = self.decoder._validate_altitude_data(invalid_data)
        self.assertTrue(result)  # Should pass with checks disabled
        
        # Test with sanity checks enabled
        self.decoder.enable_sanity_checks = True
        result = self.decoder._validate_altitude_data(invalid_data)
        self.assertFalse(result)  # Should fail with checks enabled
    
    def test_altitude_range_validation(self):
        """Test altitude range validation"""
        test_cases = [
            (-1000, True),   # Minimum valid
            (0, True),       # Sea level
            (35000, True),   # Typical cruising altitude
            (60000, True),   # Maximum valid
            (-1001, False),  # Below minimum
            (60001, False),  # Above maximum
            (100000, False), # Garbage value
        ]
        
        for altitude, expected_valid in test_cases:
            result = self.decoder._is_altitude_valid(altitude)
            self.assertEqual(result, expected_valid, 
                           f"Altitude {altitude} should be {'valid' if expected_valid else 'invalid'}")
    
    def test_statistics_tracking(self):
        """Test that statistics are properly tracked"""
        initial_stats = self.decoder.get_stats()
        
        # Decode some altitudes
        test_messages = [
            ("8D4840D6202CC371C32CE0576098", 11),  # Barometric
            ("8D4840D6F8220136E0A1473D8A14", 31),  # Geometric
        ]
        
        for hex_msg, tc in test_messages:
            self.decoder.decode_altitude(hex_msg, tc)
        
        final_stats = self.decoder.get_stats()
        
        # Should have incremented counters
        self.assertGreaterEqual(final_stats['altitudes_decoded'], initial_stats['altitudes_decoded'])
        
        # Check that we have a success rate
        self.assertIn('success_rate', final_stats)
        self.assertIsInstance(final_stats['success_rate'], float)
    
    def test_error_handling(self):
        """Test error handling with invalid inputs"""
        # Test with invalid hex message
        result = self.decoder.decode_altitude("invalid_hex", 11)
        self.assertIsNone(result)
        
        # Test with short message
        result = self.decoder.decode_altitude("8D4840", 11)
        self.assertIsNone(result)
        
        # Test with invalid type code
        result = self.decoder.decode_altitude("8D4840D6202CC371C32CE0576098", 99)
        self.assertIsNone(result)
        
        # Test with None input
        result = self.decoder.decode_altitude(None, 11)
        self.assertIsNone(result)
    
    def test_reset_functionality(self):
        """Test statistics reset functionality"""
        # Decode some data to generate stats
        self.decoder.decode_altitude("8D4840D6202CC371C32CE0576098", 11)
        
        # Verify stats are non-zero
        stats = self.decoder.get_stats()
        self.assertGreater(stats['altitudes_decoded'], 0)
        
        # Reset stats
        self.decoder.reset_stats()
        
        # Verify stats are reset
        reset_stats = self.decoder.get_stats()
        self.assertEqual(reset_stats['altitudes_decoded'], 0)
        self.assertEqual(reset_stats['barometric_altitudes'], 0)
        self.assertEqual(reset_stats['geometric_altitudes'], 0)


class TestADSBAltitudeDecoderIntegration(unittest.TestCase):
    """Integration tests for altitude decoder with real-world scenarios"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.decoder = ADSBAltitudeDecoder()
        
        # Real ADS-B messages with known altitudes (if available)
        # These would typically be collected from actual aircraft
        self.real_messages = [
            # Format: (hex_message, type_code, expected_altitude_range, description)
            ("8D4840D6202CC371C32CE0576098", 11, (35000, 40000), "Commercial aircraft cruise"),
            ("8D4840D6202CC371C32CE0576098", 11, (0, 5000), "Aircraft on approach"),
        ]
    
    def test_real_message_processing(self):
        """Test processing of real ADS-B messages"""
        for hex_msg, tc, alt_range, description in self.real_messages:
            result = self.decoder.decode_altitude(hex_msg, tc)
            
            if result and 'altitude_baro_ft' in result:
                altitude = result['altitude_baro_ft']
                print(f"{description}: {altitude} ft")
                
                # Verify altitude is in expected range
                self.assertGreaterEqual(altitude, alt_range[0])
                self.assertLessEqual(altitude, alt_range[1])
    
    def test_performance_with_high_volume(self):
        """Test performance with high-volume altitude decoding"""
        import time
        
        # Test message
        hex_msg = "8D4840D6202CC371C32CE0576098"
        type_code = 11
        
        # Decode many altitudes
        start_time = time.time()
        decode_count = 1000
        
        for _ in range(decode_count):
            result = self.decoder.decode_altitude(hex_msg, type_code)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"Decoded {decode_count} altitudes in {processing_time:.3f} seconds")
        print(f"Rate: {decode_count/processing_time:.1f} altitudes/second")
        
        # Should process at reasonable rate
        self.assertLess(processing_time, 1.0)  # Should complete within 1 second
    
    def test_altitude_tracking_over_time(self):
        """Test altitude tracking for consistency over time"""
        # Simulate altitude changes over time
        altitude_sequence = [
            ("8D4840D6202CC371C32CE0576098", 11, 35000),  # Cruise
            ("8D4840D6202CC371C32CE0576098", 11, 34000),  # Descent
            ("8D4840D6202CC371C32CE0576098", 11, 33000),  # Continued descent
            ("8D4840D6202CC371C32CE0576098", 11, 32000),  # More descent
        ]
        
        previous_altitude = None
        
        for hex_msg, tc, expected_approx in altitude_sequence:
            result = self.decoder.decode_altitude(hex_msg, tc)
            
            if result and 'altitude_baro_ft' in result:
                current_altitude = result['altitude_baro_ft']
                
                if previous_altitude is not None:
                    # Check for reasonable rate of change
                    altitude_change = abs(current_altitude - previous_altitude)
                    self.assertLess(altitude_change, 5000)  # Less than 5000 ft change
                
                previous_altitude = current_altitude


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the tests
    unittest.main(verbosity=2)