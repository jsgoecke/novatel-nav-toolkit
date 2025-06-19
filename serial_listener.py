#!/usr/bin/env python3
"""
Serial Listener Module for Novatel ProPak6 Navigation Data Toolkit

This module provides serial communication capabilities for receiving data from
Novatel GNSS receivers and other serial devices. It handles connection management,
data reception, error handling, and provides a callback-based interface for
data processing.

Key Features:
- Asynchronous serial data reception
- Automatic reconnection on connection loss
- Configurable serial parameters (baud rate, parity, etc.)
- Thread-safe operation
- Port discovery and testing utilities
- Comprehensive error handling and logging

Author: Novatel ProPak6 Navigation Data Toolkit
"""

import threading
import time
import serial
import serial.tools.list_ports
from typing import Callable, Optional, List, Dict, Any
import logging
from datetime import datetime, timezone
import config


class SerialListener:
    """
    Asynchronous serial data listener with automatic reconnection.
    
    This class manages serial communication for receiving navigation data
    from GNSS receivers and other serial devices. It operates in a separate
    thread to avoid blocking the main application.
    
    Example:
        def handle_data(data):
            print(f"Received: {data}")
        
        listener = SerialListener(handle_data)
        if listener.start():
            print("Serial listener started")
            time.sleep(10)
            listener.stop()
    """

    def __init__(self, data_callback: Callable[[bytes], None]):
        """
        Initialize the serial listener.
        
        Args:
            data_callback: Function to call when data is received.
                          Should accept bytes as parameter.
        """
        self.data_callback = data_callback
        self.serial_port: Optional[serial.Serial] = None
        self.listener_thread: Optional[threading.Thread] = None
        self.running = False
        self.connected = False
        
        # Statistics
        self.bytes_received = 0
        self.messages_received = 0
        self.connection_errors = 0
        self.last_data_time: Optional[datetime] = None
        self.start_time: Optional[datetime] = None
        
        # Configuration from config module
        self.port_name = config.SERIAL_PORT
        self.baudrate = config.SERIAL_BAUDRATE
        self.bytesize = config.SERIAL_BYTESIZE
        self.parity = config.SERIAL_PARITY
        self.stopbits = config.SERIAL_STOPBITS
        self.timeout = config.SERIAL_TIMEOUT
        self.xonxoff = config.SERIAL_XONXOFF
        self.rtscts = config.SERIAL_RTSCTS
        self.dsrdtr = config.SERIAL_DSRDTR
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)

    def start(self) -> bool:
        """
        Start the serial listener.
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        with self._lock:
            if self.running:
                self.logger.warning("Serial listener is already running")
                return True
            
            try:
                # Open serial port
                self.serial_port = serial.Serial(
                    port=self.port_name,
                    baudrate=self.baudrate,
                    bytesize=self.bytesize,
                    parity=self.parity,
                    stopbits=self.stopbits,
                    timeout=self.timeout,
                    xonxoff=self.xonxoff,
                    rtscts=self.rtscts,
                    dsrdtr=self.dsrdtr
                )
                
                if not self.serial_port.is_open:
                    self.serial_port.open()
                
                self.connected = True
                self.running = True
                self.start_time = datetime.now(timezone.utc)
                
                # Start listener thread
                self.listener_thread = threading.Thread(
                    target=self._listen_loop,
                    name="SerialListener",
                    daemon=True
                )
                self.listener_thread.start()
                
                self.logger.info(f"Serial listener started on {self.port_name} at {self.baudrate} baud")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to start serial listener: {e}")
                self.connected = False
                self.running = False
                if self.serial_port:
                    try:
                        self.serial_port.close()
                    except:
                        pass
                    self.serial_port = None
                return False

    def stop(self):
        """Stop the serial listener."""
        with self._lock:
            if not self.running:
                return
            
            self.running = False
            self.connected = False
            
            # Close serial port
            if self.serial_port:
                try:
                    self.serial_port.close()
                except Exception as e:
                    self.logger.error(f"Error closing serial port: {e}")
                self.serial_port = None
            
            # Wait for thread to finish
            if self.listener_thread and self.listener_thread.is_alive():
                self.listener_thread.join(timeout=2.0)
            
            self.logger.info("Serial listener stopped")

    def is_listening(self) -> bool:
        """
        Check if the listener is currently active.
        
        Returns:
            bool: True if listening, False otherwise
        """
        return self.running and self.connected

    def _listen_loop(self):
        """Main listening loop (runs in separate thread)."""
        consecutive_errors = 0
        
        while self.running:
            try:
                if not self.serial_port or not self.serial_port.is_open:
                    # Try to reconnect
                    if not self._reconnect():
                        time.sleep(config.SERIAL_RECONNECT_DELAY)
                        continue
                
                # Read data
                data = self.serial_port.read(4096)  # Read up to 4KB
                
                if data:
                    # Update statistics
                    self.bytes_received += len(data)
                    self.messages_received += 1
                    self.last_data_time = datetime.now(timezone.utc)
                    consecutive_errors = 0
                    
                    # Log data if enabled
                    if config.LOG_SERIAL_TRAFFIC:
                        self.logger.debug(f"Received {len(data)} bytes: {data[:50]}...")
                    
                    # Call data callback
                    try:
                        self.data_callback(data)
                    except Exception as e:
                        self.logger.error(f"Error in data callback: {e}")
                
                # Small delay to prevent high CPU usage
                time.sleep(0.001)
                
            except serial.SerialException as e:
                consecutive_errors += 1
                self.connection_errors += 1
                self.connected = False
                
                self.logger.error(f"Serial error: {e}")
                
                if consecutive_errors >= config.MAX_SERIAL_ERRORS:
                    self.logger.error(f"Too many consecutive errors ({consecutive_errors}), stopping")
                    break
                
                # Try to reconnect after delay
                time.sleep(config.SERIAL_RECONNECT_DELAY)
                
            except Exception as e:
                self.logger.error(f"Unexpected error in serial listener: {e}")
                time.sleep(1.0)

    def _reconnect(self) -> bool:
        """
        Attempt to reconnect to the serial port.
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
        try:
            # Close existing connection
            if self.serial_port:
                try:
                    self.serial_port.close()
                except:
                    pass
            
            # Open new connection
            self.serial_port = serial.Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
                xonxoff=self.xonxoff,
                rtscts=self.rtscts,
                dsrdtr=self.dsrdtr
            )
            
            self.connected = True
            self.logger.info(f"Reconnected to {self.port_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Reconnection failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get listener statistics.
        
        Returns:
            dict: Statistics including bytes received, messages, errors, etc.
        """
        now = datetime.now(timezone.utc)
        uptime = (now - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            'listening': self.is_listening(),
            'connected': self.connected,
            'port': self.port_name,
            'baudrate': self.baudrate,
            'bytes_received': self.bytes_received,
            'messages_received': self.messages_received,
            'connection_errors': self.connection_errors,
            'uptime_seconds': round(uptime, 1),
            'last_data_time': self.last_data_time.isoformat() if self.last_data_time else None,
            'data_rate_bps': round(self.bytes_received / max(uptime, 1), 2) if uptime > 0 else 0
        }

    @staticmethod
    def list_available_ports() -> List[Dict[str, str]]:
        """
        List all available serial ports on the system.
        
        Returns:
            list: List of dictionaries with port information
        """
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'name': port.name or 'Unknown',
                'description': port.description or 'No description',
                'hwid': port.hwid or 'Unknown',
                'manufacturer': getattr(port, 'manufacturer', 'Unknown') or 'Unknown'
            })
        return sorted(ports, key=lambda x: x['device'])

    @staticmethod
    def test_port(port_name: str, baudrate: int = 9600, timeout: float = 1.0) -> bool:
        """
        Test if a serial port can be opened.
        
        Args:
            port_name: Name of the port to test
            baudrate: Baud rate to use for testing
            timeout: Connection timeout
            
        Returns:
            bool: True if port can be opened, False otherwise
        """
        try:
            with serial.Serial(port_name, baudrate, timeout=timeout) as test_port:
                return test_port.is_open
        except Exception:
            return False

    def send_data(self, data: bytes) -> bool:
        """
        Send data to the serial port.
        
        Args:
            data: Data to send
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        try:
            if self.serial_port and self.serial_port.is_open:
                bytes_written = self.serial_port.write(data)
                self.serial_port.flush()
                return bytes_written == len(data)
        except Exception as e:
            self.logger.error(f"Error sending data: {e}")
        return False

    def flush_buffers(self):
        """Flush serial port input and output buffers."""
        try:
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.reset_input_buffer()
                self.serial_port.reset_output_buffer()
        except Exception as e:
            self.logger.error(f"Error flushing buffers: {e}")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()