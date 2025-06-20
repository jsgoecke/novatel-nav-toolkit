#!/usr/bin/env python3
"""
Unit tests for NovAtel PASSCOM Parser

Tests the parsing of NovAtel PASSCOM/PASSTHROUGH UDP dumps containing ADS-B data.
"""

import unittest
import sys
import os

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from novatel_passcom_parser import NovAtelPasscomParser
import config


class TestNovAtelPasscomParser(unittest.TestCase):
    """Test cases for NovAtel PASSCOM Parser"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.parser = NovAtelPasscomParser()
        
        # Sample PASSCOM data from actual logs
        self.sample_passcom_data = bytes.fromhex(
            "5265636569766564207061636b65742066726f6d203139322e3136382e342e313a36313730383a20"
            "7e26002b4a28fa38a6857cf38a3e0b1c2f9e0ecfa54d0831ef43eda1b7a6e3a673190cc52f6dbba9c"
            "a5ee12d7a2bea1dbfd5a2baccb84211da7ba943dd31a58a230f44334593087e7e250102042d3a9c86"
            "cb270000000002060e3af6557b2b00000000c4f87e"
        )
        
        # ASCII representation: "Received packet from 192.168.4.1:61708: ~&..."
        self.sample_wrapper_text = b"Received packet from 192.168.4.1:61708: "
        
        # Sample ASCII-hex data
        self.sample_ascii_hex = b"8D4840D6202CC371C32CE0576098"
        
        # Expected binary from ASCII-hex
        self.expected_binary = bytes.fromhex("8D4840D6202CC371C32CE0576098")
        
    def test_frame_boundary_detection(self):
        """Test detection of frame boundaries (0x7E 0x26)"""
        # Test with frame marker present
        test_data = b"some_data\x7e\x26\x00\x10more_data"
        boundaries = self.parser.detect_frame_boundaries(test_data)
        self.assertEqual(len(boundaries), 1)
        self.assertEqual(boundaries[0], 9)  # Position of 0x7E
        
        # Test with no frame marker
        test_data = b"no_frame_marker_here"
        boundaries = self.parser.detect_frame_boundaries(test_data)
        self.assertEqual(len(boundaries), 0)
        
        # Test with multiple frame markers
        test_data = b"\x7e\x26\x00\x10data\x7e\x26\x00\x20more"
        boundaries = self.parser.detect_frame_boundaries(test_data)
        self.assertEqual(len(boundaries), 2)
        self.assertEqual(boundaries[0], 0)
        self.assertEqual(boundaries[1], 9)
    
    def test_passcom_frame_detection(self):
        """Test detection of PASSCOM frames"""
        # Test with real PASSCOM data
        self.assertTrue(self.parser.is_passcom_frame(self.sample_passcom_data))
        
        # Test with wrapper text only
        wrapper_data = b"Received packet from 192.168.4.1:61708: some_data"
        self.assertTrue(self.parser.is_passcom_frame(wrapper_data))
        
        # Test with frame marker only
        frame_data = b"some_data\x7e\x26\x00\x10more_data"
        self.assertTrue(self.parser.is_passcom_frame(frame_data))
        
        # Test with neither
        random_data = b"random_binary_data_without_markers"
        self.assertFalse(self.parser.is_passcom_frame(random_data))
    
    def test_wrapper_stripping(self):
        """Test removal of NovAtel wrapper text"""
        # Test data with wrapper
        test_data = self.sample_wrapper_text + b"remaining_data"
        cleaned = self.parser._strip_novatel_wrapper(test_data)
        self.assertEqual(cleaned, b"remaining_data")
        
        # Test data without wrapper
        test_data = b"no_wrapper_data"
        cleaned = self.parser._strip_novatel_wrapper(test_data)
        self.assertEqual(cleaned, test_data)
    
    def test_ascii_hex_conversion(self):
        """Test ASCII-hex to binary conversion"""
        # Test valid ASCII-hex
        result = self.parser._convert_ascii_hex_if_needed(self.sample_ascii_hex)
        self.assertEqual(result, self.expected_binary)
        
        # Test binary data (should pass through unchanged)
        binary_data = b"\x8d\x48\x40\xd6"
        result = self.parser._convert_ascii_hex_if_needed(binary_data)
        self.assertEqual(result, binary_data)
        
        # Test invalid ASCII-hex (should return original)
        invalid_hex = b"GGHHII"  # Invalid hex characters
        result = self.parser._convert_ascii_hex_if_needed(invalid_hex)
        self.assertEqual(result, invalid_hex)
        
        # Test odd-length hex string
        odd_hex = b"8D4840D6202CC371C32CE057609"  # 27 chars (odd)
        result = self.parser._convert_ascii_hex_if_needed(odd_hex)
        # Should truncate to 26 chars and convert
        expected = bytes.fromhex("8D4840D6202CC371C32CE0576")
        self.assertEqual(result, expected)
    
    def test_mode_s_frame_extraction(self):
        """Test extraction of Mode-S frames from binary data"""
        # Create test data with a valid Mode-S frame (DF=17)
        # DF=17 is binary 10001, so first 5 bits are 10001
        test_frame = bytes([0x8D]) + b"\x48\x40\xd6" + b"\x00" * 10  # 14 bytes total
        
        frames = self.parser._extract_mode_s_frames(test_frame)
        self.assertEqual(len(frames), 1)
        self.assertEqual(len(frames[0]), 14)
        self.assertEqual(frames[0][0], 0x8D)  # DF=17
        
        # Test with multiple frames
        double_frame = test_frame + test_frame
        frames = self.parser._extract_mode_s_frames(double_frame)
        self.assertEqual(len(frames), 2)
        
        # Test with invalid DF
        invalid_frame = bytes([0xFF]) + b"\x00" * 13  # DF=31 (invalid)
        frames = self.parser._extract_mode_s_frames(invalid_frame)
        self.assertEqual(len(frames), 0)
    
    def test_frame_extraction_from_buffer(self):
        """Test extraction of complete frames from buffer"""
        # Create test data with frame marker and length
        test_data = b"\x7e\x26\x00\x10" + b"A" * 16  # 16 bytes of data
        
        self.parser.frame_buffer = test_data
        frame_data = self.parser._extract_next_frame()
        
        self.assertIsNotNone(frame_data)
        self.assertEqual(len(frame_data), 16)
        self.assertEqual(frame_data, b"A" * 16)
        
        # Buffer should be empty after extraction
        self.assertEqual(len(self.parser.frame_buffer), 0)
    
    def test_incomplete_frame_handling(self):
        """Test handling of incomplete frames"""
        # Create incomplete frame (missing data)
        incomplete_data = b"\x7e\x26\x00\x10" + b"A" * 8  # Only 8 bytes of 16
        
        self.parser.frame_buffer = incomplete_data
        frame_data = self.parser._extract_next_frame()
        
        # Should return None for incomplete frame
        self.assertIsNone(frame_data)
        
        # Buffer should retain the incomplete frame
        self.assertEqual(len(self.parser.frame_buffer), len(incomplete_data))
    
    def test_complete_parsing_pipeline(self):
        """Test the complete parsing pipeline with real data"""
        # This tests the integration of all components
        frames = self.parser.parse_passcom_frame(self.sample_passcom_data)
        
        # Should extract some frames
        self.assertGreater(len(frames), 0)
        
        # Each frame should be valid Mode-S length
        for frame in frames:
            self.assertIn(len(frame), [14, 28])
            
            # Check that DF is reasonable
            df = (frame[0] >> 3) & 0x1F
            self.assertLessEqual(df, 31)
    
    def test_statistics_tracking(self):
        """Test that statistics are properly tracked"""
        initial_stats = self.parser.get_stats()
        
        # Process some data
        self.parser.parse_passcom_frame(self.sample_passcom_data)
        
        final_stats = self.parser.get_stats()
        
        # Should have incremented counters
        self.assertGreater(final_stats['frames_processed'], initial_stats['frames_processed'])
        
        # Reset stats
        self.parser.reset_stats()
        reset_stats = self.parser.get_stats()
        
        # Should be back to zero
        self.assertEqual(reset_stats['frames_processed'], 0)
    
    def test_buffer_size_limits(self):
        """Test that buffer size is properly limited"""
        # Fill buffer with large amount of data
        large_data = b"A" * 5000
        self.parser.frame_buffer = large_data
        
        # Try to extract frame (should fail but manage buffer size)
        self.parser._extract_next_frame()
        
        # Buffer should be limited in size
        self.assertLessEqual(len(self.parser.frame_buffer), 100)
    
    def test_error_handling(self):
        """Test error handling with corrupted data"""
        # Test with corrupted frame length
        corrupted_data = b"\x7e\x26\xFF\xFF" + b"data"
        
        # Should not crash
        frames = self.parser.parse_passcom_frame(corrupted_data)
        self.assertEqual(len(frames), 0)
        
        # Test with empty data
        frames = self.parser.parse_passcom_frame(b"")
        self.assertEqual(len(frames), 0)
        
        # Test with None data
        try:
            frames = self.parser.parse_passcom_frame(None)
            self.assertEqual(len(frames), 0)
        except:
            pass  # Expected to fail


class TestNovAtelPasscomIntegration(unittest.TestCase):
    """Integration tests for PASSCOM parser with real-world scenarios"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.parser = NovAtelPasscomParser()
        
        # Multiple real PASSCOM samples from logs
        self.real_samples = [
            bytes.fromhex("5265636569766564207061636b65742066726f6d203139322e3136382e342e313a36313730383a207e26002b4a28fa38a6857cf38a3e0b1c2f9e0ecfa54d0831ef43eda1b7a6e3a673190cc52f6dbba9ca5ee12d7a2bea1dbfd5a2baccb84211da7ba943dd31a58a230f44334593087e7e250102042d3a9c86cb270000000002060e3af6557b2b00000000c4f87e"),
            bytes.fromhex("5265636569766564207061636b65742066726f6d203139322e3136382e342e313a36313730383a207e26007a53c2bf912e2dfbc37ae601611d60ef91427e7e260025898191b8b94bc7bc3410cbdfdc5d"),
            bytes.fromhex("5265636569766564207061636b65742066726f6d203139322e3136382e342e313a36313730383a207e26006059790fbe636b44d0fe2e0fb42b2839be6737d57e7e2600e59a98eb1664a0d04a")
        ]
    
    def test_real_data_processing(self):
        """Test processing of real PASSCOM data samples"""
        total_frames = 0
        
        for i, sample in enumerate(self.real_samples):
            frames = self.parser.parse_passcom_frame(sample)
            total_frames += len(frames)
            
            # Log results for debugging
            print(f"Sample {i+1}: {len(sample)} bytes -> {len(frames)} frames")
            
            for j, frame in enumerate(frames):
                df = (frame[0] >> 3) & 0x1F if len(frame) > 0 else -1
                print(f"  Frame {j+1}: {len(frame)} bytes, DF={df}")
        
        print(f"Total frames extracted: {total_frames}")
        
        # Should extract at least some frames
        self.assertGreater(total_frames, 0)
    
    def test_performance_with_high_volume(self):
        """Test performance with high-volume data"""
        import time
        
        # Create large dataset
        large_dataset = self.real_samples * 100  # 300 samples
        
        start_time = time.time()
        total_frames = 0
        
        for sample in large_dataset:
            frames = self.parser.parse_passcom_frame(sample)
            total_frames += len(frames)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        print(f"Processed {len(large_dataset)} samples in {processing_time:.2f} seconds")
        print(f"Rate: {len(large_dataset)/processing_time:.1f} samples/second")
        print(f"Total frames: {total_frames}")
        
        # Should process at reasonable rate
        self.assertLess(processing_time, 10.0)  # Should complete within 10 seconds


if __name__ == '__main__':
    # Set up logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the tests
    unittest.main(verbosity=2)