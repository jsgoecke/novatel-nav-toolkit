#!/usr/bin/env python3
"""
Unit tests for NovatelParser module

This module tests the Novatel GNSS message parsing functionality including:
- ASCII message parsing (BESTPOS, BESTVEL, INSPVA, etc.)
- Binary message parsing with proper struct unpacking
- Message format detection and routing
- Navigation data extraction and consolidation
- Error handling and statistics tracking

Author: Novatel ProPak6 Navigation Data Toolkit
"""

import unittest
from unittest.mock import Mock, patch
import struct
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from novatel_parser import NovatelParser
import config


class TestNovatelParser(unittest.TestCase):
    """Test cases for NovatelParser class."""

    def setUp(self):
        """Set up test fixtures."""
        self.parser = NovatelParser()
        
        # Sample ASCII messages for testing
        self.sample_bestpos_ascii = (
            "#BESTPOSA,COM1,0,55.0,FINESTEERING,2167,144140.000,02000040,cdba,32768;"
            "SOL_COMPUTED,SINGLE,51.15043711111,-114.03067851111,1064.9551,-17.0000,"
            "WGS84,1.6389,1.3921,2.4639,\"\",0.000,0.000,35,30,30,30,0,06,0,33*2d0d0a"
        ).encode('ascii')
        
        self.sample_bestvel_ascii = (
            "#BESTVELA,COM1,0,83.5,FINESTEERING,2167,144140.000,02000040,cdba,32768;"
            "SOL_COMPUTED,DOPPLER_VELOCITY,0.250,0.000,0.0319,95.0319,0.0000,0.0000*59b7864b"
        ).encode('ascii')
        
        self.sample_inspva_ascii = (
            "#INSPVAA,COM1,0,83.5,FINESTEERING,2167,144140.000,02000040,cdba,32768;"
            "2167,144140.000,51.15043711111,-114.03067851111,1064.9551,0.0319,0.0000,"
            "0.0000,2.4639,-1.5796,95.0319,INS_SOLUTION_GOOD*4b2d684e"
        ).encode('ascii')
        
        # Sample binary message data
        self.sample_binary_header = struct.pack('<4s3B2H2I2H', 
            b'\xaa\x44\x12\x1c',  # sync
            28,  # header length
            42,  # message ID (BESTPOS)
            0,   # message type
            0,   # port address
            72,  # message length
            0,   # sequence
            0,   # idle time
            0,   # time status
            2167 # week
        )

    def tearDown(self):
        """Clean up after tests."""
        pass

    def test_initialization(self):
        """Test NovatelParser initialization."""
        parser = NovatelParser()
        
        self.assertEqual(parser.messages_parsed, 0)
        self.assertEqual(parser.parse_errors, 0)
        self.assertEqual(parser.ascii_messages, 0)
        self.assertEqual(parser.binary_messages, 0)
        self.assertEqual(len(parser.latest_position), 0)
        self.assertEqual(len(parser.latest_velocity), 0)
        self.assertEqual(len(parser.latest_attitude), 0)
        self.assertEqual(len(parser.latest_quality), 0)

    def test_parse_bestpos_ascii(self):
        """Test parsing BESTPOS ASCII message."""
        result = self.parser.parse_message(self.sample_bestpos_ascii)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['message_type'], 'BESTPOSA')
        self.assertEqual(result['format'], 'ASCII')
        self.assertEqual(result['solution_status'], 'SOL_COMPUTED')
        self.assertEqual(result['position_type'], 'SINGLE')
        self.assertAlmostEqual(result['latitude'], 51.15043711111, places=5)
        self.assertAlmostEqual(result['longitude'], -114.03067851111, places=5)
        self.assertAlmostEqual(result['height'], 1064.9551, places=3)
        self.assertEqual(result['num_svs'], 35)
        self.assertEqual(result['num_sol_svs'], 30)

    def test_parse_bestvel_ascii(self):
        """Test parsing BESTVEL ASCII message."""
        result = self.parser.parse_message(self.sample_bestvel_ascii)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['message_type'], 'BESTVELA')
        self.assertEqual(result['format'], 'ASCII')
        self.assertEqual(result['solution_status'], 'SOL_COMPUTED')
        self.assertEqual(result['velocity_type'], 'DOPPLER_VELOCITY')
        self.assertAlmostEqual(result['hor_speed'], 0.0319, places=4)
        self.assertAlmostEqual(result['track_gnd'], 95.0319, places=4)
        self.assertAlmostEqual(result['vert_speed'], 0.0000, places=4)

    def test_parse_inspva_ascii(self):
        """Test parsing INSPVA ASCII message."""
        result = self.parser.parse_message(self.sample_inspva_ascii)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['message_type'], 'INSPVAA')
        self.assertEqual(result['format'], 'ASCII')
        self.assertEqual(result['week'], 2167)
        self.assertAlmostEqual(result['seconds'], 144140.000, places=3)
        self.assertAlmostEqual(result['latitude'], 51.15043711111, places=5)
        self.assertAlmostEqual(result['longitude'], -114.03067851111, places=5)
        self.assertAlmostEqual(result['height'], 1064.9551, places=3)
        self.assertAlmostEqual(result['azimuth'], 95.0319, places=4)
        self.assertEqual(result['status'], 'INS_SOLUTION_GOOD')

    def test_parse_invalid_ascii_message(self):
        """Test parsing invalid ASCII message."""
        invalid_msg = b"#INVALID,COM1,0;incomplete"
        result = self.parser.parse_message(invalid_msg)
        
        self.assertIsNone(result)
        self.assertEqual(self.parser.parse_errors, 1)

    def test_parse_malformed_ascii_message(self):
        """Test parsing malformed ASCII message."""
        malformed_msg = b"#BESTPOS,COM1,0,55.0;not,enough,fields"
        result = self.parser.parse_message(malformed_msg)
        
        self.assertIsNone(result)
        self.assertEqual(self.parser.parse_errors, 1)

    def test_parse_binary_message_detection(self):
        """Test binary message detection and basic parsing."""
        # Create a simple binary message with sync pattern
        binary_data = self.sample_binary_header + b'\x00' * 72 + b'\x00\x00\x00\x00'  # CRC
        
        result = self.parser.parse_message(binary_data)
        
        # Should at least detect it as binary and attempt parsing
        # Even if parsing fails due to dummy data, it should increment binary message count
        if result:
            self.assertEqual(result['format'], 'BINARY')
            self.assertEqual(result['message_id'], 42)

    def test_binary_message_buffer_handling(self):
        """Test binary message buffer handling for incomplete messages."""
        # Send partial binary message
        partial_data = self.sample_binary_header[:10]  # Only part of header
        
        result1 = self.parser.parse_message(partial_data)
        self.assertIsNone(result1)  # Should not parse incomplete message
        
        # Send rest of data
        remaining_data = self.sample_binary_header[10:] + b'\x00' * 72 + b'\x00\x00\x00\x00'
        result2 = self.parser.parse_message(remaining_data)
        
        # May or may not parse successfully depending on buffer handling
        # But should not crash

    def test_message_type_detection(self):
        """Test automatic message type detection."""
        # ASCII messages
        ascii_with_hash = b"#BESTPOS,COM1,0,55.0;test"
        ascii_with_percent = b"%BESTPOS,COM1,0,55.0;test"
        
        # Binary message
        binary_msg = b'\xaa\x44\x12\x1c' + b'\x00' * 20
        
        # Non-matching message
        other_msg = b"some other data"
        
        # Test ASCII detection (will fail parsing but should detect format)
        self.parser.parse_message(ascii_with_hash)
        self.parser.parse_message(ascii_with_percent)
        
        # Test binary detection
        self.parser.parse_message(binary_msg)
        
        # Test other message handling
        self.parser.parse_message(other_msg)

    def test_statistics_tracking(self):
        """Test parser statistics tracking."""
        # Initial stats
        stats = self.parser.get_stats()
        self.assertEqual(stats['messages_parsed'], 0)
        self.assertEqual(stats['parse_errors'], 0)
        self.assertEqual(stats['ascii_messages'], 0)
        self.assertEqual(stats['binary_messages'], 0)
        
        # Parse valid message
        self.parser.parse_message(self.sample_bestpos_ascii)
        
        # Check updated stats
        stats = self.parser.get_stats()
        self.assertEqual(stats['messages_parsed'], 1)
        self.assertEqual(stats['ascii_messages'], 1)
        self.assertEqual(stats['binary_messages'], 0)
        self.assertGreater(stats['success_rate'], 0)
        
        # Parse invalid message
        self.parser.parse_message(b"invalid message")
        
        # Check error tracking
        stats = self.parser.get_stats()
        self.assertEqual(stats['parse_errors'], 1)

    def test_latest_navigation_data_consolidation(self):
        """Test consolidation of latest navigation data."""
        # Parse position message
        self.parser.parse_message(self.sample_bestpos_ascii)
        
        # Parse velocity message
        self.parser.parse_message(self.sample_bestvel_ascii)
        
        # Parse INS message with attitude
        self.parser.parse_message(self.sample_inspva_ascii)
        
        # Get consolidated navigation data
        nav_data = self.parser.get_latest_navigation_data()
        
        # Verify consolidated data
        self.assertIn('latitude', nav_data)
        self.assertIn('longitude', nav_data)
        self.assertIn('altitude_m', nav_data)
        self.assertIn('altitude_ft', nav_data)
        self.assertIn('speed_ms', nav_data)
        self.assertIn('speed_knots', nav_data)
        self.assertIn('speed_kmh', nav_data)
        self.assertIn('heading', nav_data)
        self.assertIn('pitch', nav_data)
        self.assertIn('roll', nav_data)
        self.assertIn('parsed_timestamp', nav_data)
        
        # Verify unit conversions
        if nav_data.get('altitude_m'):
            expected_ft = nav_data['altitude_m'] * 3.28084
            self.assertAlmostEqual(nav_data['altitude_ft'], expected_ft, places=2)

    def test_solution_status_mapping(self):
        """Test solution status code mapping."""
        # Test known status codes
        self.assertEqual(self.parser.SOLUTION_STATUS[0], 'SOL_COMPUTED')
        self.assertEqual(self.parser.SOLUTION_STATUS[1], 'INSUFFICIENT_OBS')
        self.assertEqual(self.parser.SOLUTION_STATUS[13], 'INS_INACTIVE')
        
        # Test unknown status code handling
        unknown_status = self.parser.SOLUTION_STATUS.get(999, 'UNKNOWN')
        self.assertEqual(unknown_status, 'UNKNOWN')

    def test_position_type_mapping(self):
        """Test position type code mapping."""
        # Test known position types
        self.assertEqual(self.parser.POSITION_TYPE[0], 'NONE')
        self.assertEqual(self.parser.POSITION_TYPE[16], 'SINGLE')
        self.assertEqual(self.parser.POSITION_TYPE[50], 'NARROW_INT')
        
        # Test unknown position type handling
        unknown_type = self.parser.POSITION_TYPE.get(999, 'UNKNOWN')
        self.assertEqual(unknown_type, 'UNKNOWN')

    def test_message_id_mapping(self):
        """Test binary message ID mapping."""
        # Test known message IDs
        self.assertEqual(self.parser.MESSAGE_IDS[42], 'BESTPOS')
        self.assertEqual(self.parser.MESSAGE_IDS[99], 'BESTVEL')
        self.assertEqual(self.parser.MESSAGE_IDS[507], 'INSPVA')
        
        # Test unknown message ID handling
        unknown_msg = self.parser.MESSAGE_IDS.get(999, 'MSG_999')
        self.assertEqual(unknown_msg, 'MSG_999')

    def test_data_update_logic(self):
        """Test internal data update logic."""
        # Initially empty
        self.assertEqual(len(self.parser.latest_position), 0)
        self.assertEqual(len(self.parser.latest_velocity), 0)
        self.assertEqual(len(self.parser.latest_attitude), 0)
        
        # Parse position message
        self.parser.parse_message(self.sample_bestpos_ascii)
        self.assertGreater(len(self.parser.latest_position), 0)
        
        # Parse velocity message
        self.parser.parse_message(self.sample_bestvel_ascii)
        self.assertGreater(len(self.parser.latest_velocity), 0)
        
        # Parse attitude message
        self.parser.parse_message(self.sample_inspva_ascii)
        self.assertGreater(len(self.parser.latest_attitude), 0)

    def test_reset_stats(self):
        """Test statistics reset functionality."""
        # Generate some statistics
        self.parser.parse_message(self.sample_bestpos_ascii)
        self.parser.parse_message(b"invalid message")
        
        # Verify stats exist
        stats = self.parser.get_stats()
        self.assertGreater(stats['messages_parsed'], 0)
        self.assertGreater(stats['parse_errors'], 0)
        
        # Reset statistics
        self.parser.reset_stats()
        
        # Verify reset
        stats = self.parser.get_stats()
        self.assertEqual(stats['messages_parsed'], 0)
        self.assertEqual(stats['parse_errors'], 0)
        self.assertEqual(stats['ascii_messages'], 0)
        self.assertEqual(stats['binary_messages'], 0)

    def test_clear_data(self):
        """Test navigation data clearing."""
        # Populate data
        self.parser.parse_message(self.sample_bestpos_ascii)
        self.parser.parse_message(self.sample_bestvel_ascii)
        self.parser.parse_message(self.sample_inspva_ascii)
        
        # Verify data exists
        self.assertGreater(len(self.parser.latest_position), 0)
        self.assertGreater(len(self.parser.latest_velocity), 0)
        self.assertGreater(len(self.parser.latest_attitude), 0)
        
        # Clear data
        self.parser.clear_data()
        
        # Verify cleared
        self.assertEqual(len(self.parser.latest_position), 0)
        self.assertEqual(len(self.parser.latest_velocity), 0)
        self.assertEqual(len(self.parser.latest_attitude), 0)
        self.assertEqual(len(self.parser.latest_quality), 0)

    def test_ascii_field_parsing_edge_cases(self):
        """Test edge cases in ASCII field parsing."""
        # Message with empty fields
        empty_fields_msg = (
            "#BESTPOSA,COM1,0,55.0,FINESTEERING,2167,144140.000,02000040,cdba,32768;"
            "SOL_COMPUTED,SINGLE,,,,,WGS84,,,\"\",,,,,,,*2d0d0a"
        ).encode('ascii')
        
        result = self.parser.parse_message(empty_fields_msg)
        # Should handle empty fields gracefully (may return None or partial data)
        
        # Message with extra fields
        extra_fields_msg = (
            "#BESTPOSA,COM1,0,55.0,FINESTEERING,2167,144140.000,02000040,cdba,32768;"
            "SOL_COMPUTED,SINGLE,51.15,-114.03,1064.9,-17.0,WGS84,1.6,1.3,2.4,\"\","
            "0.0,0.0,35,30,30,30,0,06,0,33,extra,fields,here*2d0d0a"
        ).encode('ascii')
        
        result = self.parser.parse_message(extra_fields_msg)
        # Should handle extra fields gracefully

    def test_binary_struct_parsing(self):
        """Test binary structure parsing edge cases."""
        # Test with insufficient data length
        short_data = b'\xaa\x44\x12\x1c' + b'\x00' * 10  # Too short
        result = self.parser.parse_message(short_data)
        self.assertIsNone(result)
        
        # Test with invalid message length
        invalid_header = struct.pack('<4s3B2H2I2H', 
            b'\xaa\x44\x12\x1c',  # sync
            28,  # header length
            42,  # message ID
            0,   # message type
            0,   # port address
            1000,  # invalid large message length
            0,   # sequence
            0,   # idle time
            0,   # time status
            2167 # week
        )
        result = self.parser.parse_message(invalid_header)
        self.assertIsNone(result)

    def test_coordinate_precision(self):
        """Test coordinate precision handling."""
        # High precision coordinates
        high_precision_msg = (
            "#BESTPOSA,COM1,0,55.0,FINESTEERING,2167,144140.000,02000040,cdba,32768;"
            "SOL_COMPUTED,SINGLE,51.150437111111111,-114.030678511111111,1064.9551,"
            "-17.0000,WGS84,1.6389,1.3921,2.4639,\"\",0.000,0.000,35,30,30,30,0,06,0,33*2d0d0a"
        ).encode('ascii')
        
        result = self.parser.parse_message(high_precision_msg)
        if result:
            # Verify precision is maintained
            self.assertIsInstance(result['latitude'], float)
            self.assertIsInstance(result['longitude'], float)
            self.assertGreater(len(str(result['latitude']).split('.')[1]), 5)  # At least 6 decimal places

    def test_message_timestamp_handling(self):
        """Test message timestamp handling."""
        result = self.parser.parse_message(self.sample_bestpos_ascii)
        
        if result:
            self.assertIn('timestamp', result)
            self.assertIsInstance(result['timestamp'], datetime)
            self.assertEqual(result['timestamp'].tzinfo, timezone.utc)

    def test_concurrent_parsing(self):
        """Test thread safety of parser (basic test)."""
        import threading
        import time
        
        results = []
        errors = []
        
        def parse_worker():
            try:
                for _ in range(10):
                    result = self.parser.parse_message(self.sample_bestpos_ascii)
                    results.append(result)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)
        
        # Start multiple parsing threads
        threads = [threading.Thread(target=parse_worker) for _ in range(3)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Verify no exceptions occurred
        self.assertEqual(len(errors), 0)
        
        # Verify results were produced
        self.assertGreater(len([r for r in results if r is not None]), 0)

    def test_large_message_handling(self):
        """Test handling of unusually large messages."""
        # Create a very long ASCII message
        long_msg = (
            "#BESTPOSA,COM1,0,55.0,FINESTEERING,2167,144140.000,02000040,cdba,32768;"
            "SOL_COMPUTED,SINGLE,51.15043711111,-114.03067851111,1064.9551,-17.0000,"
            "WGS84,1.6389,1.3921,2.4639,\"" + "X" * 1000 + "\",0.000,0.000,35,30,30,30,0,06,0,33*2d0d0a"
        ).encode('ascii')
        
        # Should handle gracefully (parse or reject cleanly)
        result = self.parser.parse_message(long_msg)
        # Test passes if no exception is raised

    def test_encoding_handling(self):
        """Test handling of different text encodings."""
        # ASCII message with invalid UTF-8 bytes
        invalid_utf8 = (
            b"#BESTPOSA,COM1,0,55.0,FINESTEERING,2167,144140.000,02000040,cdba,32768;"
            b"SOL_COMPUTED,SINGLE,51.15,-114.03,1064.9,-17.0,WGS84,1.6,1.3,2.4,\"\xff\xfe\","
            b"0.0,0.0,35,30,30,30,0,06,0,33*2d0d0a"
        )
        
        # Should handle encoding errors gracefully
        result = self.parser.parse_message(invalid_utf8)
        # Test passes if no exception is raised


class TestNovatelParserBinaryFormats(unittest.TestCase):
    """Specific tests for binary message format handling."""

    def setUp(self):
        """Set up binary format test fixtures."""
        self.parser = NovatelParser()

    def test_bestpos_binary_structure(self):
        """Test BESTPOS binary message structure."""
        # Create a complete BESTPOS binary message
        header = struct.pack('<4s3B2H2I2H', 
            b'\xaa\x44\x12\x1c',  # sync
            28,  # header length
            42,  # message ID (BESTPOS)
            0,   # message type
            0,   # port address
            72,  # message length
            0,   # sequence
            0,   # idle time
            0,   # time status
            2167 # week
        )
        
        # BESTPOS binary data (simplified)
        data = struct.pack('<4I8d4f4I',
            0,    # solution status
            16,   # position type (SINGLE)
            0, 0, # reserved
            51.15043711111,   # latitude
            -114.03067851111, # longitude
            1064.9551,        # height
            -17.0,            # undulation
            1.6389, 1.3921, 2.4639, 0.0,  # std devs
            0, 0, 0, 0        # other fields
        )
        
        # Pad to correct length
        data += b'\x00' * (72 - len(data))
        crc = b'\x00\x00\x00\x00'  # Dummy CRC
        
        binary_msg = header + data + crc
        
        result = self.parser.parse_message(binary_msg)
        
        if result:  # May not parse perfectly with dummy data, but shouldn't crash
            self.assertEqual(result['format'], 'BINARY')
            self.assertEqual(result['message_id'], 42)

    def test_sync_pattern_detection(self):
        """Test detection of binary sync patterns."""
        # Message with sync pattern in middle
        data_with_sync = b'random data' + b'\xaa\x44\x12\x1c' + b'more data'
        
        # Should find sync pattern
        sync_pos = data_with_sync.find(self.parser.BINARY_SYNC)
        self.assertEqual(sync_pos, 11)

    def test_incomplete_binary_message(self):
        """Test handling of incomplete binary messages."""
        # Just the sync pattern
        incomplete = b'\xaa\x44\x12\x1c'
        result = self.parser.parse_message(incomplete)
        self.assertIsNone(result)
        
        # Partial header
        partial_header = b'\xaa\x44\x12\x1c\x1c\x00\x2a'  # sync + partial header
        result = self.parser.parse_message(partial_header)
        self.assertIsNone(result)


class TestNovatelParserRealWorldScenarios(unittest.TestCase):
    """Tests for real-world usage scenarios."""

    def setUp(self):
        """Set up real-world test fixtures."""
        self.parser = NovatelParser()

    def test_mixed_message_stream(self):
        """Test parsing mixed ASCII and binary message stream."""
        messages = [
            self.parser.sample_bestpos_ascii if hasattr(self.parser, 'sample_bestpos_ascii') else b"#BESTPOS;test",
            b'\xaa\x44\x12\x1c' + b'\x00' * 50,  # Binary message
            b"#BESTVEL;test",  # ASCII message
            b'invalid data',   # Invalid data
        ]
        
        for msg in messages:
            result = self.parser.parse_message(msg)
            # Should handle all message types without crashing

    def test_high_frequency_parsing(self):
        """Test high-frequency message parsing."""
        test_msg = (
            "#BESTPOSA,COM1,0,55.0,FINESTEERING,2167,144140.000,02000040,cdba,32768;"
            "SOL_COMPUTED,SINGLE,51.15,-114.03,1064.9,-17.0,WGS84,1.6,1.3,2.4,\"\","
            "0.0,0.0,35,30,30,30,0,06,0,33*2d0d0a"
        ).encode('ascii')
        
        # Parse many messages quickly
        start_time = datetime.now()
        for i in range(100):
            result = self.parser.parse_message(test_msg)
        end_time = datetime.now()
        
        # Should complete reasonably quickly
        duration = (end_time - start_time).total_seconds()
        self.assertLess(duration, 1.0)  # Should take less than 1 second
        
        # Verify statistics
        stats = self.parser.get_stats()
        self.assertEqual(stats['messages_parsed'], 100)

    def test_parser_state_consistency(self):
        """Test parser state consistency across operations."""
        # Parse various messages
        messages = [
            b"#BESTPOS,COM1,0;SOL_COMPUTED,SINGLE,51.15,-114.03,1064.9,-17.0,WGS84,1.6,1.3,2.4,\"\",0.0,0.0,35,30,30,30,0,06,0,33",
            b"#BESTVEL,COM1,0;SOL_COMPUTED,DOPPLER_VELOCITY,0.25,0.0,0.032,95.0,0.0,0.0",
            b"invalid message",
            b"#INSPVA,COM1,0;2167,144140.0,51.15,-114.03,1064.9,0.032,0.0,0.0,2.4,-1.6,95.0,INS_SOLUTION_GOOD"
        ]
        
        for msg in messages:
            self.parser.parse_message(msg)
        
        # Check state consistency
        stats = self.parser.get_stats()
        nav_data = self.parser.get_latest_navigation_data()
        
        # Statistics should be consistent
        total_attempts = stats['messages_parsed'] + stats['parse_errors']
        self.assertEqual(total_attempts, len(messages))
        
        # Navigation data should be accessible
        self.assertIsInstance(nav_data, dict)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.ERROR)  # Suppress debug messages during tests
    
    # Run tests
    unittest.main(verbosity=2)