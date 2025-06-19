#!/usr/bin/env python3
"""
Test UDP Replayer and related components
"""

import unittest
import tempfile
import socket
import threading
import time
import json
from pathlib import Path
import sys
import os

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from udp_replayer import UDPReplayer
from message_inspector import MessageInspector
from message_filter import MessageFilter
from breakpoint_manager import BreakpointManager
import config


class TestMessageInspector(unittest.TestCase):
    """Test message inspector functionality"""
    
    def setUp(self):
        self.inspector = MessageInspector()
    
    def test_inspect_nmea_message(self):
        """Test inspection of NMEA message"""
        nmea_data = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\r\n"
        
        result = self.inspector.inspect_message(nmea_data, 1)
        
        self.assertEqual(result['message_number'], 1)
        self.assertEqual(result['size_bytes'], len(nmea_data))
        self.assertEqual(result['protocol_detected'], 'nmea')
        self.assertTrue(result['checksum_info']['has_potential_checksum'])
        self.assertEqual(result['checksum_info']['checksum_type'], 'nmea')
        self.assertTrue(result['checksum_info']['checksum_valid'])
    
    def test_inspect_binary_message(self):
        """Test inspection of binary message"""
        binary_data = bytes([0xAA, 0x44, 0x12, 0x1C, 0x01, 0x02, 0x03, 0x04])
        
        result = self.inspector.inspect_message(binary_data, 2)
        
        self.assertEqual(result['message_number'], 2)
        self.assertEqual(result['size_bytes'], len(binary_data))
        self.assertEqual(result['protocol_detected'], 'novatel')
        self.assertFalse(result['checksum_info']['has_potential_checksum'])
    
    def test_hex_dump(self):
        """Test hex dump generation"""
        data = bytes(range(32))  # 32 bytes: 0x00 to 0x1F
        
        hex_dump = self.inspector.hex_dump(data, bytes_per_line=16)
        
        lines = hex_dump.split('\n')
        self.assertEqual(len(lines), 2)  # Should be 2 lines
        self.assertIn('00000000', lines[0])  # First line should start with offset 0
        self.assertIn('00000010', lines[1])  # Second line should start with offset 16
    
    def test_detect_protocol(self):
        """Test protocol detection"""
        # Test NMEA
        nmea_data = b"$GPGGA,123519,4807.038,N"
        self.assertEqual(self.inspector.detect_protocol(nmea_data), 'nmea')
        
        # Test Novatel
        novatel_data = b"\xaa\x44\x12\x1c\x01\x02\x03"
        self.assertEqual(self.inspector.detect_protocol(novatel_data), 'novatel')
        
        # Test unknown
        unknown_data = b"\x01\x02\x03\x04"
        self.assertEqual(self.inspector.detect_protocol(unknown_data), 'unknown')


class TestMessageFilter(unittest.TestCase):
    """Test message filter functionality"""
    
    def setUp(self):
        self.filter = MessageFilter()
    
    def test_size_filter(self):
        """Test size-based filtering"""
        self.filter.add_size_filter(min_size=10, max_size=20)
        
        # Test messages of different sizes
        small_msg = b"short"  # 5 bytes
        medium_msg = b"medium message"  # 14 bytes
        large_msg = b"this is a very long message"  # 27 bytes
        
        # Small message should be filtered out
        passed, failed = self.filter.apply_filters(small_msg, 1)
        self.assertFalse(passed)
        
        # Medium message should pass
        passed, failed = self.filter.apply_filters(medium_msg, 2)
        self.assertTrue(passed)
        
        # Large message should be filtered out
        passed, failed = self.filter.apply_filters(large_msg, 3)
        self.assertFalse(passed)
    
    def test_pattern_filter(self):
        """Test pattern-based filtering"""
        pattern = b"$GP"
        self.filter.add_pattern_filter(pattern, match_type='starts_with')
        
        # Message that starts with pattern should pass
        nmea_msg = b"$GPGGA,123519,4807.038,N"
        passed, failed = self.filter.apply_filters(nmea_msg, 1)
        self.assertTrue(passed)
        
        # Message that doesn't start with pattern should fail
        other_msg = b"$GLGGA,123519,4807.038,N"
        passed, failed = self.filter.apply_filters(other_msg, 2)
        self.assertFalse(passed)
    
    def test_hex_pattern_filter(self):
        """Test hex pattern filtering"""
        self.filter.add_hex_pattern_filter("AA44", match_type='starts_with')
        
        # Message that starts with hex pattern should pass
        novatel_msg = bytes([0xAA, 0x44, 0x12, 0x1C])
        passed, failed = self.filter.apply_filters(novatel_msg, 1)
        self.assertTrue(passed)
        
        # Message that doesn't start with pattern should fail
        other_msg = bytes([0x01, 0x02, 0x03, 0x04])
        passed, failed = self.filter.apply_filters(other_msg, 2)
        self.assertFalse(passed)
    
    def test_multiple_filters(self):
        """Test multiple filters working together"""
        self.filter.add_size_filter(min_size=10, max_size=50)
        self.filter.add_pattern_filter(b"$GP", match_type='starts_with')
        
        # Message that passes both filters
        good_msg = b"$GPGGA,123519,4807.038,N"
        passed, failed = self.filter.apply_filters(good_msg, 1)
        self.assertTrue(passed)
        
        # Message that fails size filter
        short_msg = b"$GP"
        passed, failed = self.filter.apply_filters(short_msg, 2)
        self.assertFalse(passed)
        
        # Message that fails pattern filter
        wrong_pattern = b"$GLGGA,123519,4807.038,N"
        passed, failed = self.filter.apply_filters(wrong_pattern, 3)
        self.assertFalse(passed)


class TestBreakpointManager(unittest.TestCase):
    """Test breakpoint manager functionality"""
    
    def setUp(self):
        self.bp_manager = BreakpointManager()
    
    def test_error_breakpoint(self):
        """Test error breakpoint"""
        bp_id = self.bp_manager.add_error_breakpoint()
        self.assertIsNotNone(bp_id)
        
        # Context with error should trigger breakpoint
        data = b"test data"
        context = {'parse_error': True}
        hit = self.bp_manager.check_breakpoints(data, 1, context)
        self.assertIsNotNone(hit)
        self.assertEqual(hit['type'], 'error')
        
        # Context without error should not trigger
        context = {'parse_error': False}
        hit = self.bp_manager.check_breakpoints(data, 2, context)
        self.assertIsNone(hit)
    
    def test_pattern_breakpoint(self):
        """Test pattern breakpoint"""
        pattern = b"$GP"
        bp_id = self.bp_manager.add_pattern_breakpoint(pattern)
        self.assertIsNotNone(bp_id)
        
        # Data with pattern should trigger breakpoint
        nmea_data = b"$GPGGA,123519,4807.038,N"
        hit = self.bp_manager.check_breakpoints(nmea_data, 1)
        self.assertIsNotNone(hit)
        self.assertEqual(hit['type'], 'pattern')
        
        # Data without pattern should not trigger
        other_data = b"$GLGGA,123519,4807.038,N"
        hit = self.bp_manager.check_breakpoints(other_data, 2)
        self.assertIsNone(hit)
    
    def test_size_breakpoint(self):
        """Test size breakpoint"""
        bp_id = self.bp_manager.add_size_breakpoint(min_size=20)
        self.assertIsNotNone(bp_id)
        
        # Large message should trigger breakpoint
        large_data = b"this is a message longer than 20 bytes"
        hit = self.bp_manager.check_breakpoints(large_data, 1)
        self.assertIsNotNone(hit)
        
        # Small message should not trigger
        small_data = b"short"
        hit = self.bp_manager.check_breakpoints(small_data, 2)
        self.assertIsNone(hit)
    
    def test_breakpoint_enable_disable(self):
        """Test enabling/disabling breakpoints"""
        bp_id = self.bp_manager.add_error_breakpoint()
        
        # Disable breakpoint
        self.assertTrue(self.bp_manager.disable_breakpoint(bp_id))
        
        # Should not trigger when disabled
        data = b"test"
        context = {'parse_error': True}
        hit = self.bp_manager.check_breakpoints(data, 1, context)
        self.assertIsNone(hit)
        
        # Re-enable breakpoint
        self.assertTrue(self.bp_manager.enable_breakpoint(bp_id))
        
        # Should trigger when enabled
        hit = self.bp_manager.check_breakpoints(data, 2, context)
        self.assertIsNotNone(hit)


class TestUDPReplayer(unittest.TestCase):
    """Test UDP replayer functionality"""
    
    def setUp(self):
        # Create temporary log file with test data
        self.temp_file = tempfile.NamedTemporaryFile(mode='wb', delete=False)
        
        # Write some test messages (binary data)
        test_messages = [
            b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47",
            b"$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A",
            bytes([0xAA, 0x44, 0x12, 0x1C, 0x01, 0x02, 0x03, 0x04]),
            b"$GPVTG,084.4,T,077.8,M,022.4,N,041.5,K*43"
        ]
        
        for msg in test_messages:
            self.temp_file.write(msg + b'\n')
        
        self.temp_file.close()
        
        # Create replayer with unused port
        self.test_port = self._find_free_port()
        self.replayer = UDPReplayer(
            log_file=self.temp_file.name,
            target_host='localhost',
            target_port=self.test_port
        )
        
        # Setup UDP receiver for testing
        self.received_messages = []
        self.receiver_socket = None
        self.receiver_thread = None
    
    def tearDown(self):
        # Cleanup
        if self.replayer:
            self.replayer.stop_replay()
        
        if self.receiver_socket:
            self.receiver_socket.close()
        
        if self.receiver_thread and self.receiver_thread.is_alive():
            self.receiver_thread.join(timeout=1.0)
        
        # Remove temp file
        Path(self.temp_file.name).unlink(missing_ok=True)
    
    def _find_free_port(self):
        """Find a free UDP port for testing"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('localhost', 0))
            return s.getsockname()[1]
    
    def _start_udp_receiver(self):
        """Start UDP receiver for testing"""
        self.receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receiver_socket.settimeout(1.0)
        self.receiver_socket.bind(('localhost', self.test_port))
        
        def receiver_loop():
            try:
                while True:
                    data, addr = self.receiver_socket.recvfrom(1024)
                    self.received_messages.append(data)
            except socket.timeout:
                pass
            except Exception:
                pass
        
        self.receiver_thread = threading.Thread(target=receiver_loop, daemon=True)
        self.receiver_thread.start()
    
    def test_load_message_cache(self):
        """Test loading message cache from file"""
        self.assertTrue(self.replayer.load_message_cache())
        self.assertTrue(self.replayer.cache_loaded)
        self.assertEqual(self.replayer.stats['total_messages_in_file'], 4)
    
    def test_replay_basic(self):
        """Test basic replay functionality"""
        # Start UDP receiver
        self._start_udp_receiver()
        
        # Configure for fast replay
        self.replayer.speed_multiplier = 10.0
        self.replayer.inter_message_delay = 0.01
        
        # Start replay
        self.assertTrue(self.replayer.start_replay())
        
        # Wait for replay to complete
        time.sleep(2.0)
        
        # Stop replay
        self.replayer.stop_replay()
        
        # Check that we received messages
        self.assertGreater(len(self.received_messages), 0)
        
        # Check statistics
        stats = self.replayer.get_replay_stats()
        self.assertGreater(stats['messages_sent'], 0)
        self.assertGreater(stats['bytes_sent'], 0)
    
    def test_replay_with_filters(self):
        """Test replay with message filters"""
        # Add filter to only allow NMEA messages
        self.replayer.message_filter.add_pattern_filter(b"$GP", match_type='starts_with')
        
        # Start UDP receiver
        self._start_udp_receiver()
        
        # Configure for fast replay
        self.replayer.speed_multiplier = 10.0
        self.replayer.inter_message_delay = 0.01
        
        # Start replay
        self.assertTrue(self.replayer.start_replay())
        
        # Wait for replay to complete
        time.sleep(2.0)
        
        # Stop replay
        self.replayer.stop_replay()
        
        # Check that we only received NMEA messages
        for msg in self.received_messages:
            self.assertTrue(msg.startswith(b"$GP"))
        
        # Check filter statistics
        stats = self.replayer.get_replay_stats()
        filter_stats = stats['filter_stats']
        self.assertGreater(filter_stats['messages_filtered'], 0)
    
    def test_message_inspection(self):
        """Test message inspection"""
        # Load cache
        self.assertTrue(self.replayer.load_message_cache())
        
        # Set current message
        self.replayer.current_message_number = 0
        self.replayer.current_message_data = self.replayer.message_cache[0]
        
        # Get message info
        msg_info = self.replayer.get_current_message_info()
        self.assertIsNotNone(msg_info)
        self.assertEqual(msg_info['message_number'], 0)
        self.assertGreater(msg_info['message_size'], 0)
        
        # Inspect message
        inspection = self.replayer.inspect_current_message()
        self.assertIsNotNone(inspection)
        self.assertEqual(inspection['message_number'], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    def test_replay_script_help(self):
        """Test that replay script shows help"""
        import subprocess
        
        try:
            result = subprocess.run(
                [sys.executable, 'replay_udp_events.py', '--help'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            self.assertEqual(result.returncode, 0)
            self.assertIn('UDP Events Replay Tool', result.stdout)
            
        except subprocess.TimeoutExpired:
            self.fail("Script help timed out")
        except FileNotFoundError:
            self.skipTest("replay_udp_events.py not found")


if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)
    
    # Run tests
    unittest.main(verbosity=2)