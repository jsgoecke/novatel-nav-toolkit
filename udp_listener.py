"""
UDP Socket Listener for Novatel ProPak6 Navigation Data Toolkit
"""

import socket
import threading
import time
from typing import Callable, Optional
import config
from logger import logger, console_print


class UDPListener:
    """UDP socket listener for receiving NMEA navigation data"""
    
    def __init__(self, data_callback: Callable[[str], None]):
        """
        Initialize UDP listener
        
        Args:
            data_callback: Function to call when data is received
        """
        self.data_callback = data_callback
        self.socket: Optional[socket.socket] = None
        self.listening = False
        self.thread: Optional[threading.Thread] = None
        self.error_count = 0
        
    def start(self) -> bool:
        """
        Start listening for UDP data
        
        Returns:
            bool: True if started successfully, False otherwise
        """
        try:
            # Create UDP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.settimeout(config.SOCKET_TIMEOUT)
            
            # Bind to address and port
            self.socket.bind((config.UDP_HOST, config.UDP_PORT))
            
            logger.info(f"UDP Listener started on {config.UDP_HOST}:{config.UDP_PORT}")
            console_print(f"UDP Listener started on {config.UDP_HOST}:{config.UDP_PORT}", force=True)
            
            # Start listening thread
            self.listening = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting UDP listener: {e}")
            console_print(f"Error starting UDP listener: {e}", force=True)
            self.stop()
            return False
    
    def stop(self):
        """Stop listening for UDP data"""
        self.listening = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        logger.info("UDP Listener stopped")
        console_print("UDP Listener stopped", force=True)
    
    def _listen_loop(self):
        """Main listening loop (runs in separate thread)"""
        consecutive_errors = 0
        packets_received = 0
        last_activity_log = time.time()
        
        logger.udp_traffic(f"Starting listen loop on {config.UDP_HOST}:{config.UDP_PORT}")
        logger.udp_traffic(f"Socket timeout: {config.SOCKET_TIMEOUT}s, Buffer size: {config.BUFFER_SIZE}")
        
        while self.listening and self.socket:
            try:
                # Log periodic status if no activity
                current_time = time.time()
                if current_time - last_activity_log > 30:  # Every 30 seconds
                    logger.udp_traffic(f"Still listening... Packets received so far: {packets_received}")
                    last_activity_log = current_time
                
                # Receive data
                data, addr = self.socket.recvfrom(config.BUFFER_SIZE)
                packets_received += 1
                
                logger.udp_traffic(f"Received {len(data)} bytes from {addr}")
                
                # Log raw hex data for debugging corruption
                if config.LOG_HEX_DATA:
                    logger.hex_data(data, "UDP-RAW")
                
                # Handle data based on protocol mode
                if config.PROTOCOL_MODE == 'adsb':
                    # For ADS-B, pass raw bytes
                    logger.udp_traffic(f"ADS-B hex data: {data.hex()}")
                    
                    if data:
                        consecutive_errors = 0
                        last_activity_log = current_time
                        self.data_callback(data)
                    else:
                        logger.udp_traffic(f"Empty ADS-B data received from {addr}")
                            
                elif config.PROTOCOL_MODE == 'nmea':
                    # For NMEA, decode to string with better error handling
                    message = data.decode('utf-8', errors='replace').strip()
                    
                    logger.udp_traffic(f"Decoded NMEA message length: {len(message)} chars")
                    if len(message) > 0:
                        preview = message[:100] + "..." if len(message) > 100 else message
                        logger.udp_traffic(f"NMEA message preview: {repr(preview)}")
                    
                    if message:
                        consecutive_errors = 0
                        last_activity_log = current_time
                        self.data_callback(message)
                    else:
                        logger.udp_traffic(f"Empty NMEA message received from {addr}")
                            
                else:  # auto mode
                    # Try to detect protocol automatically
                    try:
                        # Try to decode as UTF-8 for NMEA
                        message = data.decode('utf-8', errors='strict').strip()
                        if message.startswith('$'):
                            # Looks like NMEA
                            logger.udp_traffic("Auto-detected NMEA data")
                            consecutive_errors = 0
                            last_activity_log = current_time
                            self.data_callback(message)
                        else:
                            # Not NMEA, try as ADS-B
                            logger.udp_traffic("Auto-detected ADS-B data")
                            consecutive_errors = 0
                            last_activity_log = current_time
                            self.data_callback(data)
                    except UnicodeDecodeError:
                        # Binary data, likely ADS-B
                        logger.udp_traffic("Auto-detected binary ADS-B data")
                        consecutive_errors = 0
                        last_activity_log = current_time
                        self.data_callback(data)
                    
            except socket.timeout:
                # Timeout is normal, continue listening
                if packets_received == 0:
                    # Only log timeout if we haven't received any packets yet
                    current_time = time.time()
                    if current_time - last_activity_log > 10:  # Every 10 seconds
                        logger.udp_traffic(f"No data received yet (timeout after {config.SOCKET_TIMEOUT}s)")
                        last_activity_log = current_time
                continue
                
            except Exception as e:
                consecutive_errors += 1
                self.error_count += 1
                
                if consecutive_errors <= 3:  # Only log first few errors
                    logger.error(f"UDP receive error: {e}")
                
                if consecutive_errors >= config.MAX_PARSE_ERRORS:
                    logger.error(f"Too many consecutive UDP errors ({consecutive_errors}), stopping listener")
                    console_print(f"UDP listener stopped due to errors. Check logs for details.", force=True)
                    break
                    
                # Brief pause before retrying
                time.sleep(0.1)
        
        logger.udp_traffic(f"Listen loop ended. Total packets received: {packets_received}")
    
    def is_listening(self) -> bool:
        """Check if listener is currently active"""
        return self.listening and self.thread and self.thread.is_alive()
    
    def get_stats(self) -> dict:
        """Get listener statistics"""
        return {
            'listening': self.is_listening(),
            'error_count': self.error_count,
            'port': config.UDP_PORT,
            'host': config.UDP_HOST
        }