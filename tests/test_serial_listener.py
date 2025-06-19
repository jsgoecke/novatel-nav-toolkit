#!/usr/bin/env python3
"""
Unit tests for SerialListener module

This module tests the serial communication functionality including:
- Serial port connection management
- Data reception and callback handling
- Error handling and reconnection logic
- Port discovery and testing utilities
- Statistics tracking and reporting

Author: Novatel ProPak6 Navigation Data Toolkit
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import threading
import time
from datetime import datetime, timezone
import serial
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serial_listener import SerialListener
import config


class TestSerialListener(unittest.TestCase):
    """Test cases for SerialListener class."""

    def setUp(self):
        """Set up test fixtures."""
        self.data_received = []
        self.callback_called = threading.Event()
        
        def test_callback(data):
            self.data_received.append(data)
            self.callback_called.set()
        
        self.test_callback = test_callback
        self.listener = SerialListener(self.test_callback)

    def tearDown(self):
        """Clean up after tests."""
        if self.listener.is_listening():
            self.listener.stop()
        self.data_received.clear()
        self.callback_called.clear()

    @patch('serial.Serial')
    def test_initialization(self, mock_serial):
        """Test SerialListener initialization."""
        listener = SerialListener(self.test_callback)
        
        self.assertEqual(listener.data_callback, self.test_callback)
        self.assertIsNone(listener.serial_port)
        self.assertIsNone(listener.listener_thread)
        self.assertFalse(listener.running)
        self.assertFalse(listener.connected)
        self.assertEqual(listener.bytes_received, 0)
        self.assertEqual(listener.messages_received, 0)
        self.assertEqual(listener.connection_errors, 0)

    @patch('serial.Serial')
    def test_start_success(self, mock_serial_class):
        """Test successful start of serial listener."""
        # Mock serial port
        mock_port = Mock()
        mock_port.is_open = True
        mock_serial_class.return_value = mock_port
        
        # Start listener
        result = self.listener.start()
        
        # Verify results
        self.assertTrue(result)
        self.assertTrue(self.listener.running)
        self.assertTrue(self.listener.connected)
        self.assertIsNotNone(self.listener.serial_port)
        self.assertIsNotNone(self.listener.listener_thread)
        self.assertTrue(self.listener.listener_thread.is_alive())
        
        # Verify serial port was configured correctly
        mock_serial_class.assert_called_once_with(
            port=config.SERIAL_PORT,
            baudrate=config.SERIAL_BAUDRATE,
            bytesize=config.SERIAL_BYTESIZE,
            parity=config.SERIAL_PARITY,
            stopbits=config.SERIAL_STOPBITS,
            timeout=config.SERIAL_TIMEOUT,
            xonxoff=config.SERIAL_XONXOFF,
            rtscts=config.SERIAL_RTSCTS,
            dsrdtr=config.SERIAL_DSRDTR
        )

    @patch('serial.Serial')
    def test_start_failure(self, mock_serial_class):
        """Test failed start of serial listener."""
        # Mock serial port creation failure
        mock_serial_class.side_effect = serial.SerialException("Port not found")
        
        # Attempt to start listener
        result = self.listener.start()
        
        # Verify failure
        self.assertFalse(result)
        self.assertFalse(self.listener.running)
        self.assertFalse(self.listener.connected)
        self.assertIsNone(self.listener.serial_port)

    @patch('serial.Serial')
    def test_start_already_running(self, mock_serial_class):
        """Test starting listener when already running."""
        # Mock serial port
        mock_port = Mock()
        mock_port.is_open = True
        mock_serial_class.return_value = mock_port
        
        # Start listener first time
        self.listener.start()
        
        # Try to start again
        result = self.listener.start()
        
        # Should return True but not create new connections
        self.assertTrue(result)
        self.assertEqual(mock_serial_class.call_count, 1)

    @patch('serial.Serial')
    def test_stop(self, mock_serial_class):
        """Test stopping serial listener."""
        # Mock serial port
        mock_port = Mock()
        mock_port.is_open = True
        mock_serial_class.return_value = mock_port
        
        # Start and then stop listener
        self.listener.start()
        self.listener.stop()
        
        # Verify stopped state
        self.assertFalse(self.listener.running)
        self.assertFalse(self.listener.connected)
        self.assertIsNone(self.listener.serial_port)
        
        # Verify serial port was closed
        mock_port.close.assert_called_once()

    @patch('serial.Serial')
    def test_data_reception(self, mock_serial_class):
        """Test data reception and callback."""
        # Mock serial port
        mock_port = Mock()
        mock_port.is_open = True
        mock_port.read.side_effect = [b'test data', b'', b'more data', b'']
        mock_serial_class.return_value = mock_port
        
        # Start listener
        self.listener.start()
        
        # Wait for some data to be processed
        time.sleep(0.1)
        
        # Stop listener
        self.listener.stop()
        
        # Verify callback was called with data
        self.assertTrue(len(self.data_received) > 0)
        self.assertIn(b'test data', self.data_received)
        self.assertIn(b'more data', self.data_received)

    @patch('serial.Serial')
    def test_serial_exception_handling(self, mock_serial_class):
        """Test handling of serial exceptions."""
        # Mock serial port that raises exception
        mock_port = Mock()
        mock_port.is_open = True
        mock_port.read.side_effect = serial.SerialException("Connection lost")
        mock_serial_class.return_value = mock_port
        
        # Start listener
        self.listener.start()
        
        # Wait for error to be handled
        time.sleep(0.1)
        
        # Stop listener
        self.listener.stop()
        
        # Verify error was tracked
        self.assertGreater(self.listener.connection_errors, 0)

    @patch('serial.Serial')
    def test_reconnection(self, mock_serial_class):
        """Test automatic reconnection after connection loss."""
        # Mock serial port that fails then succeeds
        mock_port_fail = Mock()
        mock_port_fail.is_open = False
        mock_port_success = Mock()
        mock_port_success.is_open = True
        mock_port_success.read.return_value = b'reconnected'
        
        mock_serial_class.side_effect = [mock_port_fail, mock_port_success]
        
        # Start listener
        self.listener.start()
        
        # Wait for reconnection attempt
        time.sleep(0.1)
        
        # Stop listener
        self.listener.stop()
        
        # Verify reconnection was attempted
        self.assertEqual(mock_serial_class.call_count, 2)

    def test_is_listening(self):
        """Test is_listening status method."""
        # Initially not listening
        self.assertFalse(self.listener.is_listening())
        
        with patch('serial.Serial') as mock_serial_class:
            mock_port = Mock()
            mock_port.is_open = True
            mock_serial_class.return_value = mock_port
            
            # Start listener
            self.listener.start()
            self.assertTrue(self.listener.is_listening())
            
            # Stop listener
            self.listener.stop()
            self.assertFalse(self.listener.is_listening())

    @patch('serial.Serial')
    def test_get_stats(self, mock_serial_class):
        """Test statistics reporting."""
        # Mock serial port
        mock_port = Mock()
        mock_port.is_open = True
        mock_port.read.return_value = b'test data'
        mock_serial_class.return_value = mock_port
        
        # Start listener and let it receive some data
        self.listener.start()
        time.sleep(0.1)
        self.listener.stop()
        
        # Get statistics
        stats = self.listener.get_stats()
        
        # Verify statistics structure
        self.assertIn('listening', stats)
        self.assertIn('connected', stats)
        self.assertIn('port', stats)
        self.assertIn('baudrate', stats)
        self.assertIn('bytes_received', stats)
        self.assertIn('messages_received', stats)
        self.assertIn('connection_errors', stats)
        self.assertIn('uptime_seconds', stats)
        self.assertIn('data_rate_bps', stats)
        
        # Verify some values
        self.assertEqual(stats['port'], config.SERIAL_PORT)
        self.assertEqual(stats['baudrate'], config.SERIAL_BAUDRATE)
        self.assertIsInstance(stats['bytes_received'], int)
        self.assertIsInstance(stats['messages_received'], int)

    @patch('serial.tools.list_ports.comports')
    def test_list_available_ports(self, mock_comports):
        """Test listing available serial ports."""
        # Mock port information
        mock_port1 = Mock()
        mock_port1.device = '/dev/ttyUSB0'
        mock_port1.name = 'USB Serial Port'
        mock_port1.description = 'USB to Serial Adapter'
        mock_port1.hwid = 'USB VID:PID=0403:6001'
        mock_port1.manufacturer = 'FTDI'
        
        mock_port2 = Mock()
        mock_port2.device = '/dev/ttyACM0'
        mock_port2.name = 'ACM Port'
        mock_port2.description = 'Arduino Compatible'
        mock_port2.hwid = 'USB VID:PID=2341:0043'
        mock_port2.manufacturer = 'Arduino'
        
        mock_comports.return_value = [mock_port1, mock_port2]
        
        # List ports
        ports = SerialListener.list_available_ports()
        
        # Verify results
        self.assertEqual(len(ports), 2)
        self.assertEqual(ports[0]['device'], '/dev/ttyACM0')  # Sorted by device name
        self.assertEqual(ports[1]['device'], '/dev/ttyUSB0')
        
        # Verify port information structure
        for port in ports:
            self.assertIn('device', port)
            self.assertIn('name', port)
            self.assertIn('description', port)
            self.assertIn('hwid', port)
            self.assertIn('manufacturer', port)

    @patch('serial.Serial')
    def test_test_port(self, mock_serial_class):
        """Test port testing functionality."""
        # Mock successful port test
        mock_port = Mock()
        mock_port.is_open = True
        mock_serial_class.return_value.__enter__.return_value = mock_port
        
        result = SerialListener.test_port('/dev/ttyUSB0')
        self.assertTrue(result)
        
        # Mock failed port test
        mock_serial_class.side_effect = serial.SerialException("Port not found")
        
        result = SerialListener.test_port('/dev/nonexistent')
        self.assertFalse(result)

    @patch('serial.Serial')
    def test_send_data(self, mock_serial_class):
        """Test sending data through serial port."""
        # Mock serial port
        mock_port = Mock()
        mock_port.is_open = True
        mock_port.write.return_value = 9  # Number of bytes written
        mock_serial_class.return_value = mock_port
        
        # Start listener
        self.listener.start()
        
        # Send data
        test_data = b'test data'
        result = self.listener.send_data(test_data)
        
        # Verify sending
        self.assertTrue(result)
        mock_port.write.assert_called_once_with(test_data)
        mock_port.flush.assert_called_once()
        
        self.listener.stop()

    @patch('serial.Serial')
    def test_send_data_failure(self, mock_serial_class):
        """Test sending data failure handling."""
        # Mock serial port that's not open
        mock_port = Mock()
        mock_port.is_open = False
        mock_serial_class.return_value = mock_port
        
        # Start listener
        self.listener.start()
        
        # Try to send data
        result = self.listener.send_data(b'test data')
        
        # Verify failure
        self.assertFalse(result)
        
        self.listener.stop()

    @patch('serial.Serial')
    def test_flush_buffers(self, mock_serial_class):
        """Test buffer flushing functionality."""
        # Mock serial port
        mock_port = Mock()
        mock_port.is_open = True
        mock_serial_class.return_value = mock_port
        
        # Start listener
        self.listener.start()
        
        # Flush buffers
        self.listener.flush_buffers()
        
        # Verify flush methods were called
        mock_port.reset_input_buffer.assert_called_once()
        mock_port.reset_output_buffer.assert_called_once()
        
        self.listener.stop()

    @patch('serial.Serial')
    def test_context_manager(self, mock_serial_class):
        """Test using SerialListener as context manager."""
        # Mock serial port
        mock_port = Mock()
        mock_port.is_open = True
        mock_serial_class.return_value = mock_port
        
        # Use as context manager
        with SerialListener(self.test_callback) as listener:
            self.assertTrue(listener.is_listening())
        
        # Should be stopped after exiting context
        self.assertFalse(listener.is_listening())

    @patch('serial.Serial')
    def test_callback_exception_handling(self, mock_serial_class):
        """Test handling of exceptions in data callback."""
        # Create callback that raises exception
        def failing_callback(data):
            raise ValueError("Callback error")
        
        listener = SerialListener(failing_callback)
        
        # Mock serial port
        mock_port = Mock()
        mock_port.is_open = True
        mock_port.read.return_value = b'test data'
        mock_serial_class.return_value = mock_port
        
        # Start listener (should not crash despite callback error)
        listener.start()
        time.sleep(0.1)
        listener.stop()
        
        # Listener should still work despite callback exceptions
        self.assertGreater(listener.bytes_received, 0)

    @patch('serial.Serial')
    def test_large_data_handling(self, mock_serial_class):
        """Test handling of large data chunks."""
        # Mock serial port with large data
        large_data = b'X' * 8192  # 8KB of data
        mock_port = Mock()
        mock_port.is_open = True
        mock_port.read.side_effect = [large_data, b'']
        mock_serial_class.return_value = mock_port
        
        # Start listener
        self.listener.start()
        time.sleep(0.1)
        self.listener.stop()
        
        # Verify large data was handled
        self.assertGreater(self.listener.bytes_received, 8000)
        self.assertIn(large_data, self.data_received)

    def test_configuration_parameters(self):
        """Test that configuration parameters are properly set."""
        listener = SerialListener(self.test_callback)
        
        # Verify configuration is loaded from config module
        self.assertEqual(listener.port_name, config.SERIAL_PORT)
        self.assertEqual(listener.baudrate, config.SERIAL_BAUDRATE)
        self.assertEqual(listener.bytesize, config.SERIAL_BYTESIZE)
        self.assertEqual(listener.parity, config.SERIAL_PARITY)
        self.assertEqual(listener.stopbits, config.SERIAL_STOPBITS)
        self.assertEqual(listener.timeout, config.SERIAL_TIMEOUT)
        self.assertEqual(listener.xonxoff, config.SERIAL_XONXOFF)
        self.assertEqual(listener.rtscts, config.SERIAL_RTSCTS)
        self.assertEqual(listener.dsrdtr, config.SERIAL_DSRDTR)


class TestSerialListenerIntegration(unittest.TestCase):
    """Integration tests for SerialListener (requires actual serial hardware)."""

    def setUp(self):
        """Set up integration test fixtures."""
        self.data_received = []
        
        def test_callback(data):
            self.data_received.append(data)
        
        self.test_callback = test_callback

    @unittest.skipUnless(hasattr(serial, 'Serial'), "pyserial not available")
    def test_port_discovery(self):
        """Test actual port discovery (integration test)."""
        ports = SerialListener.list_available_ports()
        
        # Should return a list (empty or with ports)
        self.assertIsInstance(ports, list)
        
        # Each port should have required fields
        for port in ports:
            self.assertIn('device', port)
            self.assertIn('name', port)
            self.assertIn('description', port)
            self.assertIn('hwid', port)
            self.assertIn('manufacturer', port)

    @unittest.skipUnless(hasattr(serial, 'Serial'), "pyserial not available")
    def test_nonexistent_port(self):
        """Test handling of nonexistent serial port."""
        listener = SerialListener(self.test_callback)
        listener.port_name = '/dev/nonexistent_port_12345'
        
        # Should fail gracefully
        result = listener.start()
        self.assertFalse(result)
        self.assertFalse(listener.is_listening())


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.ERROR)  # Suppress debug messages during tests
    
    # Run tests
    unittest.main(verbosity=2)