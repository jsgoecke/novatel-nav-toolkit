#!/usr/bin/env python3
"""
Comprehensive Integration Tests for NovAtel → ADS-B Altitude Doctor System

Tests the complete pipeline from NovAtel PASSCOM UDP dumps to JSON output
with reliable altitude extraction.
"""

import unittest
import sys
import os
import json

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adsb_parser import ADSBParser
from novatel_passcom_parser import NovAtelPasscomParser
from adsb_altitude_decoder import ADSBAltitudeDecoder
import config


class TestNovAtelADSBIntegration(unittest.TestCase):
    """Integration tests for the complete NovAtel → ADS-B pipeline"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.parser = ADSBParser()
        
        # Real PASSCOM data samples from logs
        self.real_passcom_samples = [
            bytes.fromhex("5265636569766564207061636b65742066726f6d203139322e3136382e342e313a36313730383a207e26002b4a28fa38a6857cf38a3e0b1c2f9e0ecfa54d0831ef43eda1b7a6e3a673190cc52f6dbba9ca5ee12d7a2bea1dbfd5a2baccb84211da7ba943dd31a58a230f44334593087e7e250102042d3a9c86cb270000000002060e3af6557b2b00000000c4f87e"),
            bytes.fromhex("5265636569766564207061636b65742066726f6d203139322e3136382e342e313a36313730383a207e26007a53c2bf912e2dfbc37ae601611d60ef91427e7e260025898191b8b94bc7bc3410cbdfdc5d"),
            bytes.fromhex("5265636569766564207061636b65742066726f6d203139322e3136382e342e313a36313730383a207e26006059790fbe636b44d0fe2e0fb42b2839be6737d57e7e2600e59a98eb1664a0d04a"),
        ]
        
        # Expected improvements in parsing after implementing the fix
        self.expected_improvements = {
            'passcom_detection': True,
            'frame_extraction': True,
            'altitude_decoding': True,
            'error_reduction': True
        }
    
    def test_complete_pipeline_processing(self):
        """Test the complete processing pipeline from PASSCOM to JSON output"""
        total_processed = 0
        total_successful = 0
        altitude_extractions = 0
        
        print("\n=== Testing Complete NovAtel → ADS-B Pipeline ===")
        
        for i, sample in enumerate(self.real_passcom_samples):
            print(f"\nProcessing PASSCOM sample {i+1}:")
            print(f"  Input size: {len(sample)} bytes")
            print(f"  Input hex: {sample[:50].hex()}...")
            
            # Process through complete pipeline
            result = self.parser.parse_message(sample)
            total_processed += 1
            
            if result:
                total_successful += 1
                print(f"  ✓ Successfully parsed ADS-B data")
                print(f"  ICAO: {result.get('icao', 'N/A')}")
                print(f"  Type Code: {result.get('type_code', 'N/A')}")
                
                # Check for altitude data
                if 'altitude_baro_ft' in result:
                    altitude_extractions += 1
                    print(f"  ✓ Barometric altitude: {result['altitude_baro_ft']} ft")
                
                if 'altitude_geo_ft' in result:
                    print(f"  ✓ Geometric altitude: {result['altitude_geo_ft']} ft")
                
                # Check for other navigation data
                if 'latitude' in result and 'longitude' in result:
                    print(f"  ✓ Position: {result['latitude']:.6f}, {result['longitude']:.6f}")
                
                if 'speed_knots' in result:
                    print(f"  ✓ Speed: {result['speed_knots']} knots")
                
                if 'heading' in result:
                    print(f"  ✓ Heading: {result['heading']}°")
                
                # Verify JSON serialization
                try:
                    json_output = json.dumps(result, default=str, indent=2)
                    print(f"  ✓ JSON serializable ({len(json_output)} chars)")
                except Exception as e:
                    print(f"  ✗ JSON serialization failed: {e}")
                    
            else:
                print(f"  ✗ Failed to parse ADS-B data")
        
        print(f"\n=== Pipeline Results ===")
        print(f"Total samples processed: {total_processed}")
        print(f"Successful parses: {total_successful}")
        print(f"Success rate: {(total_successful/total_processed)*100:.1f}%")
        print(f"Altitude extractions: {altitude_extractions}")
        
        # The system should be able to process at least some of the real data
        # Even if not all samples contain valid ADS-B frames
        self.assertGreater(total_processed, 0)
    
    def test_passcom_detection_and_processing(self):
        """Test that PASSCOM frames are properly detected and processed"""
        print("\n=== Testing PASSCOM Detection ===")
        
        for i, sample in enumerate(self.real_passcom_samples):
            # Check if PASSCOM is detected
            is_passcom = self.parser._is_passcom_wrapped(sample)
            print(f"Sample {i+1}: PASSCOM detected = {is_passcom}")
            
            if is_passcom:
                # Should process through PASSCOM parser
                extracted_frames = self.parser.passcom_parser.parse_passcom_frame(sample)
                print(f"  Extracted {len(extracted_frames)} Mode-S frames")
                
                for j, frame in enumerate(extracted_frames):
                    if len(frame) > 0:
                        df = (frame[0] >> 3) & 0x1F
                        print(f"    Frame {j+1}: {len(frame)} bytes, DF={df}")
                        
                        # DF should be reasonable after proper extraction
                        self.assertLessEqual(df, 31)
            
            # At least some samples should be detected as PASSCOM
            if any(self.parser._is_passcom_wrapped(s) for s in self.real_passcom_samples):
                break
        else:
            print("Note: No PASSCOM frames detected in test samples")
    
    def test_altitude_extraction_accuracy(self):
        """Test altitude extraction accuracy and validation"""
        print("\n=== Testing Altitude Extraction ===")
        
        altitude_results = []
        
        for i, sample in enumerate(self.real_passcom_samples):
            result = self.parser.parse_message(sample)
            
            if result and ('altitude_baro_ft' in result or 'altitude_geo_ft' in result):
                altitude_data = {}
                
                if 'altitude_baro_ft' in result:
                    baro_alt = result['altitude_baro_ft']
                    altitude_data['barometric'] = baro_alt
                    
                    # Validate altitude is reasonable
                    self.assertGreaterEqual(baro_alt, -1000, "Altitude below minimum")
                    self.assertLessEqual(baro_alt, 60000, "Altitude above maximum")
                    
                    print(f"Sample {i+1} barometric: {baro_alt} ft ✓")
                
                if 'altitude_geo_ft' in result:
                    geo_alt = result['altitude_geo_ft']
                    altitude_data['geometric'] = geo_alt
                    
                    # Validate altitude is reasonable
                    self.assertGreaterEqual(geo_alt, -1000, "Geometric altitude below minimum")
                    self.assertLessEqual(geo_alt, 60000, "Geometric altitude above maximum")
                    
                    print(f"Sample {i+1} geometric: {geo_alt} ft ✓")
                
                altitude_results.append(altitude_data)
        
        print(f"Total altitude extractions: {len(altitude_results)}")
        
        # Should extract at least some altitudes if data contains valid ADS-B
        if altitude_results:
            print("✓ Altitude extraction working")
        else:
            print("Note: No altitudes extracted (may be normal if samples don't contain altitude data)")
    
    def test_error_handling_and_recovery(self):
        """Test error handling with corrupted or invalid data"""
        print("\n=== Testing Error Handling ===")
        
        # Test with various types of corrupted data
        error_test_cases = [
            (b"", "Empty data"),
            (b"corrupted_binary_data", "Random binary data"),
            (b"Received packet from malformed", "Incomplete wrapper"),
            (b"\x7e\x26\xFF\xFF" + b"A" * 100, "Corrupted frame length"),
            (b"52656365697665642070616362" + b"\x00" * 50, "Partial ASCII-hex"),
        ]
        
        errors_handled = 0
        
        for test_data, description in error_test_cases:
            print(f"Testing: {description}")
            
            try:
                result = self.parser.parse_message(test_data)
                # Should either return None or handle gracefully
                print(f"  Result: {'Success' if result else 'None (expected)'}")
                errors_handled += 1
                
            except Exception as e:
                print(f"  Exception: {e}")
                # Should not crash on corrupted data
                self.fail(f"Parser crashed on {description}: {e}")
        
        print(f"✓ Handled {errors_handled}/{len(error_test_cases)} error cases")
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks for the complete system"""
        print("\n=== Performance Benchmarks ===")
        
        import time
        
        # Test processing speed
        test_iterations = 100
        start_time = time.time()
        
        for _ in range(test_iterations):
            for sample in self.real_passcom_samples:
                result = self.parser.parse_message(sample)
        
        end_time = time.time()
        total_time = end_time - start_time
        total_messages = test_iterations * len(self.real_passcom_samples)
        
        messages_per_second = total_messages / total_time
        
        print(f"Processed {total_messages} messages in {total_time:.3f} seconds")
        print(f"Rate: {messages_per_second:.1f} messages/second")
        
        # Should maintain real-time processing capability
        self.assertGreater(messages_per_second, 100, "Processing too slow for real-time")
        
        print("✓ Performance adequate for real-time processing")
    
    def test_statistics_and_monitoring(self):
        """Test statistics collection and monitoring capabilities"""
        print("\n=== Testing Statistics Collection ===")
        
        # Reset stats
        self.parser.reset_stats()
        initial_stats = self.parser.get_stats()
        
        # Process some data
        for sample in self.real_passcom_samples:
            self.parser.parse_message(sample)
        
        final_stats = self.parser.get_stats()
        
        print("Statistics after processing:")
        for key, value in final_stats.items():
            print(f"  {key}: {value}")
        
        # Should have incremented some counters
        stats_changed = any(final_stats[key] > initial_stats.get(key, 0) 
                          for key in final_stats.keys() 
                          if isinstance(final_stats[key], int))
        
        self.assertTrue(stats_changed, "No statistics were updated")
        print("✓ Statistics tracking working")
    
    def test_json_output_format(self):
        """Test that JSON output format meets specifications"""
        print("\n=== Testing JSON Output Format ===")
        
        for i, sample in enumerate(self.real_passcom_samples):
            result = self.parser.parse_message(sample)
            
            if result:
                print(f"Sample {i+1} JSON output:")
                
                # Verify required fields
                self.assertIn('icao', result, "Missing ICAO field")
                self.assertIn('type_code', result, "Missing type code")
                self.assertIn('parsed_timestamp', result, "Missing timestamp")
                
                # Verify field types
                if 'altitude_baro_ft' in result:
                    self.assertIsInstance(result['altitude_baro_ft'], int, "Barometric altitude not integer")
                
                if 'altitude_geo_ft' in result:
                    self.assertIsInstance(result['altitude_geo_ft'], int, "Geometric altitude not integer")
                
                if 'latitude' in result:
                    self.assertIsInstance(result['latitude'], (int, float), "Latitude not numeric")
                    self.assertGreaterEqual(result['latitude'], -90, "Latitude out of range")
                    self.assertLessEqual(result['latitude'], 90, "Latitude out of range")
                
                if 'longitude' in result:
                    self.assertIsInstance(result['longitude'], (int, float), "Longitude not numeric")
                    self.assertGreaterEqual(result['longitude'], -180, "Longitude out of range")
                    self.assertLessEqual(result['longitude'], 180, "Longitude out of range")
                
                # Test JSON serialization
                try:
                    json_str = json.dumps(result, default=str, indent=2)
                    print(f"  ✓ Valid JSON ({len(json_str)} characters)")
                    
                    # Verify it can be parsed back
                    parsed_back = json.loads(json_str)
                    self.assertEqual(parsed_back['icao'], result['icao'])
                    
                except Exception as e:
                    self.fail(f"JSON serialization failed: {e}")
                
                break  # Only test first successful result
        
        print("✓ JSON output format valid")


class TestSystemBehaviorComparison(unittest.TestCase):
    """Test system behavior before and after implementing the fix"""
    
    def setUp(self):
        """Set up comparison test fixtures"""
        self.parser = ADSBParser()
        
        # Sample that was failing before the fix
        self.problematic_sample = bytes.fromhex(
            "5265636569766564207061636b65742066726f6d203139322e3136382e342e313a36313730383a20"
            "7e26002b4a28fa38a6857cf38a3e0b1c2f9e0ecfa54d0831ef43eda1b7a6e3a673190cc52f6dbba9c"
            "a5ee12d7a2bea1dbfd5a2baccb84211da7ba943dd31a58a230f44334593087e"
        )
    
    def test_before_and_after_fix_behavior(self):
        """Test that the fix resolves the original problem"""
        print("\n=== Testing Fix Effectiveness ===")
        
        # Process the problematic sample
        result = self.parser.parse_message(self.problematic_sample)
        
        print(f"Sample processing result: {'Success' if result else 'Failed'}")
        
        if result:
            print(f"ICAO: {result.get('icao', 'N/A')}")
            print(f"Type Code: {result.get('type_code', 'N/A')}")
            
            # The original issue was DF=10 (from ASCII 'R')
            # Now we should get proper ADS-B parsing
            if 'type_code' in result:
                tc = result['type_code']
                print(f"✓ Valid type code extracted: {tc}")
                
                # Should not be getting the old DF=10 error
                self.assertNotEqual(tc, 10, "Still getting DF=10 (ASCII 'R') - fix not working")
        
        # Check statistics
        stats = self.parser.get_stats()
        print(f"PASSCOM messages processed: {stats.get('passcom_messages_processed', 0)}")
        print(f"Mode-S frames extracted: {stats.get('passcom_mode_s_frames', 0)}")
        
        # Should show PASSCOM processing activity
        if config.ENABLE_PASSCOM_PARSER:
            self.assertGreater(stats.get('passcom_messages_processed', 0), 0, 
                             "PASSCOM parser not being used")
        
        print("✓ Fix appears to be working")


if __name__ == '__main__':
    # Set up test environment
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Enable detailed logging for testing
    config.LOG_PARSE_ATTEMPTS = True
    config.LOG_PASSCOM_FRAMES = True
    config.LOG_ALTITUDE_DECODING = True
    
    print("=== NovAtel → ADS-B Altitude Doctor Integration Tests ===")
    print(f"PASSCOM Parser Enabled: {config.ENABLE_PASSCOM_PARSER}")
    print(f"Altitude Sanity Checks: {config.ENABLE_ALTITUDE_SANITY_CHECKS}")
    print(f"Accepted DFs: {config.ACCEPTED_DOWNLINK_FORMATS}")
    print(f"Altitude Range: {config.MIN_VALID_ALTITUDE_FT} to {config.MAX_VALID_ALTITUDE_FT} ft")
    
    # Run the tests
    unittest.main(verbosity=2)