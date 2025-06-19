#!/usr/bin/env python3
"""
Integration tests for UDP Replay System
Tests the complete replay workflow including all components
"""

import unittest
import tempfile
import socket
import threading
import time
import json
import sys
import os
from pathlib import Path

# Add parent directory to path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from udp_replayer import UDPReplayer
from message_inspector import MessageInspector
from message_filter import MessageFilter
from breakpoint_manager import BreakpointManager
from interactive_debugger import SimpleDebugger
import config


class TestReplayIntegration(unittest.TestCase):
    """Integration tests for the complete UDP replay system"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary log file with realistic test data
        self.temp_file = tempfile.NamedTemporaryFile(mode='wb', delete=False)
        
        # Write mixed protocol test messages
        test_messages = [
            # NMEA sentences
            b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47",
            b"$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A",
            b"$GPVTG,084.4,T,077.8,M,022.4,N,041.5,K*43",
            
            # Novatel binary-like messages
            bytes([0xAA, 0x44, 0x12, 0x1C]) + b"BESTPOS" + bytes(20),
            bytes([0xAA, 0x44, 0x12, 0x1C]) + b"BESTVEL" + bytes(15),
            
            # ADS-B-like messages (various sizes)
            bytes([0x8D, 0x48, 0x40, 0xD6, 0x20, 0x2C, 0xC3, 0x71, 0xC3, 0x2C, 0xE0, 0x57, 0x60, 0x98]),
            bytes([0x8D, 0x40, 0x62, 0x1D, 0x58, 0xC3, 0x82, 0xD6, 0x90, 0xC8, 0xAC, 0x28, 0x63, 0xA7]),
            
            # Edge cases
            b"",  # Empty message
            b"x" * 300,  # Large message
            bytes([0x00, 0x01, 0x02, 0x03, 0x04]),  # Short binary
        ]
        
        for msg in test_messages:
            self.temp_file.write(msg + b'\n')
        
        self.temp_file.close()
        
        # Create test port
        self.test_port = self._find_free_port()
    
    def tearDown(self):
        """Clean up test environment"""
        Path(self.temp_file.name).unlink(missing_ok=True)
    
    def _find_free_port(self):
        """Find a free UDP port for testing"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('localhost', 0))
            return s.getsockname()[1]
    
    def test_complete_replay_workflow(self):
        """Test the complete replay workflow from start to finish"""
        # Create replayer
        replayer = UDPReplayer(
            log_file=self.temp_file.name,
            target_host='localhost',
            target_port=self.test_port
        )
        
        # Configure for fast testing
        replayer.speed_multiplier = 10.0
        replayer.inter_message_delay = 0.001
        
        # Load cache
        self.assertTrue(replayer.load_message_cache())
        self.assertGreater(replayer.stats['total_messages_in_file'], 0)
        
        # Setup UDP receiver to verify messages are sent
        received_messages = []
        receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver_socket.settimeout(0.5)
        receiver_socket.bind(('localhost', self.test_port))
        
        def receive_messages():
            try:
                while True:
                    data, addr = receiver_socket.recvfrom(1024)
                    received_messages.append(data)
            except socket.timeout:
                pass
            except Exception:
                pass
        
        receiver_thread = threading.Thread(target=receive_messages, daemon=True)
        receiver_thread.start()
        
        # Start replay
        self.assertTrue(replayer.start_replay())
        
        # Wait for replay to complete
        time.sleep(2.0)
        
        # Stop replay
        replayer.stop_replay()
        receiver_socket.close()
        
        # Verify results
        stats = replayer.get_replay_stats()
        self.assertGreater(stats['messages_sent'], 0)
        self.assertGreater(len(received_messages), 0)
        
        # Verify some messages were received
        self.assertLessEqual(len(received_messages), stats['messages_sent'])
    
    def test_filtering_integration(self):
        """Test message filtering integration"""
        replayer = UDPReplayer(
            log_file=self.temp_file.name,
            target_host='localhost',
            target_port=self.test_port
        )
        
        # Add size filter to only allow medium-sized messages
        replayer.message_filter.add_size_filter(min_size=10, max_size=100)
        
        # Load and start replay
        self.assertTrue(replayer.load_message_cache())
        self.assertTrue(replayer.start_replay(speed_multiplier=20.0))
        
        # Let it run briefly
        time.sleep(1.0)
        replayer.stop_replay()
        
        # Check filter statistics
        stats = replayer.get_replay_stats()
        filter_stats = stats['filter_stats']
        
        # Should have filtered some messages
        self.assertGreater(filter_stats['messages_processed'], 0)
        if filter_stats['messages_filtered'] > 0:
            self.assertLess(filter_stats['pass_rate'], 100.0)
    
    def test_breakpoint_integration(self):
        """Test breakpoint integration"""
        replayer = UDPReplayer(
            log_file=self.temp_file.name,
            target_host='localhost',
            target_port=self.test_port
        )
        
        # Add breakpoint for NMEA messages
        bp_id = replayer.breakpoint_manager.add_pattern_breakpoint(b"$GP")
        self.assertIsNotNone(bp_id)
        
        # Track breakpoint hits
        breakpoint_hits = []
        def on_breakpoint(hit_info):
            breakpoint_hits.append(hit_info)
        
        replayer.set_breakpoint_hit_callback(on_breakpoint)
        
        # Load and start replay
        self.assertTrue(replayer.load_message_cache())
        self.assertTrue(replayer.start_replay(speed_multiplier=20.0))
        
        # Let it run briefly
        time.sleep(1.0)
        replayer.stop_replay()
        
        # Should have hit breakpoints
        self.assertGreater(len(breakpoint_hits), 0)
        
        # Verify breakpoint information
        first_hit = breakpoint_hits[0]
        self.assertEqual(first_hit['type'], 'pattern')
        self.assertIn('message_number', first_hit)
    
    def test_message_inspection_integration(self):
        """Test message inspection integration"""
        inspector = MessageInspector()
        
        # Test with NMEA message
        nmea_data = b"$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        inspection = inspector.inspect_message(nmea_data, 1)
        
        # Verify inspection results
        self.assertEqual(inspection['protocol_detected'], 'nmea')
        self.assertTrue(inspection['checksum_info']['has_potential_checksum'])
        self.assertEqual(inspection['checksum_info']['checksum_type'], 'nmea')
        
        # Test with binary data
        binary_data = bytes([0xAA, 0x44, 0x12, 0x1C, 0x01, 0x02, 0x03, 0x04])
        inspection = inspector.inspect_message(binary_data, 2)
        
        self.assertEqual(inspection['protocol_detected'], 'novatel')
        self.assertFalse(inspection['checksum_info']['has_potential_checksum'])
        
        # Test hex dump functionality
        hex_dump = inspector.hex_dump(binary_data)
        self.assertIn('AA44121C', hex_dump.replace(' ', ''))
    
    def test_simple_debugger_integration(self):
        """Test simple debugger integration"""
        replayer = UDPReplayer(
            log_file=self.temp_file.name,
            target_host='localhost',
            target_port=self.test_port
        )
        
        # Load cache
        self.assertTrue(replayer.load_message_cache())
        
        # Create simple debugger
        debugger = SimpleDebugger(replayer)
        
        # Test that debugger can access replayer functions
        self.assertIsNotNone(debugger.replayer)
        self.assertTrue(debugger.replayer.cache_loaded)
    
    def test_error_handling_integration(self):
        """Test error handling in integration scenarios"""
        # Test with non-existent file
        replayer = UDPReplayer(
            log_file='/nonexistent/file.log',
            target_host='localhost',
            target_port=self.test_port
        )
        
        # Should fail gracefully
        self.assertFalse(replayer.load_message_cache())
        
        # Test with invalid port
        replayer2 = UDPReplayer(
            log_file=self.temp_file.name,
            target_host='localhost',
            target_port=-1  # Invalid port
        )
        
        # Should handle gracefully
        self.assertTrue(replayer2.load_message_cache())
        # Start might fail but shouldn't crash
        try:
            replayer2.start_replay()
            replayer2.stop_replay()
        except Exception as e:
            # Should fail gracefully without crashing
            self.assertIsInstance(e, (OSError, ValueError))
    
    def test_statistics_integration(self):
        """Test statistics collection and saving"""
        replayer = UDPReplayer(
            log_file=self.temp_file.name,
            target_host='localhost',
            target_port=self.test_port
        )
        
        # Load and run brief replay
        self.assertTrue(replayer.load_message_cache())
        self.assertTrue(replayer.start_replay(speed_multiplier=50.0))
        
        time.sleep(0.5)
        replayer.stop_replay()
        
        # Get statistics
        stats = replayer.get_replay_stats()
        
        # Verify statistics structure
        required_keys = [
            'messages_processed', 'messages_sent', 'bytes_sent',
            'total_messages_in_file', 'session_start', 'session_end',
            'filter_stats', 'breakpoint_stats', 'inspector_stats'
        ]
        
        for key in required_keys:
            self.assertIn(key, stats)
        
        # Test statistics saving
        temp_stats_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_stats_file.close()
        
        try:
            self.assertTrue(replayer.save_statistics(temp_stats_file.name))
            
            # Verify file was created and contains valid JSON
            with open(temp_stats_file.name, 'r') as f:
                saved_stats = json.load(f)
            
            # Should contain the same keys
            for key in required_keys:
                self.assertIn(key, saved_stats)
                
        finally:
            Path(temp_stats_file.name).unlink(missing_ok=True)
    
    def test_multiple_filter_types_integration(self):
        """Test multiple filter types working together"""
        replayer = UDPReplayer(
            log_file=self.temp_file.name,
            target_host='localhost',
            target_port=self.test_port
        )
        
        # Add multiple filters
        replayer.message_filter.add_size_filter(min_size=5, max_size=200)
        replayer.message_filter.add_pattern_filter(b"GP", match_type='contains')
        replayer.message_filter.add_corruption_filter(skip_corrupted=True)
        
        # Load and run
        self.assertTrue(replayer.load_message_cache())
        self.assertTrue(replayer.start_replay(speed_multiplier=50.0))
        
        time.sleep(0.5)
        replayer.stop_replay()
        
        # Check that filters were applied
        stats = replayer.get_replay_stats()
        filter_stats = stats['filter_stats']
        
        self.assertEqual(filter_stats['active_filter_count'], 3)
        self.assertGreater(filter_stats['messages_processed'], 0)


if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    Path('logs').mkdir(exist_ok=True)
    
    # Run tests
    unittest.main(verbosity=2)