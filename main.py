"""
Novatel ProPak6 Navigation Data Toolkit
Main application entry point
"""

import sys
import time
import signal
import threading
from datetime import datetime
from typing import Optional

# Import config always (no dependencies)
import config
from logger import logger, console_print
from json_event_logger import json_event_logger, comprehensive_json_logger

# Import required modules at module level for testing
try:
    from udp_listener import UDPListener
    from nmea_parser import NMEAParser
    from adsb_parser import ADSBParser
    from navigation_display import NavigationDisplay
except ImportError:
    # Will be handled in NavigationListener.__init__
    pass


class NavigationListener:
    """Main application class for Novatel ProPak6 navigation data toolkit"""
    
    def __init__(self):
        """Initialize the navigation listener"""
        # Import modules only when creating the listener
        try:
            from udp_listener import UDPListener
            from nmea_parser import NMEAParser
            from adsb_parser import ADSBParser
            from navigation_display import NavigationDisplay
            
            self.udp_listener: Optional[UDPListener] = None
            self.serial_listener = None
            self.nmea_parser = NMEAParser()
            self.adsb_parser = ADSBParser()
            self.novatel_parser = None
            self.display = NavigationDisplay()
            
            # Import Novatel components only if needed
            if config.PROTOCOL_MODE == 'novatel':
                from serial_listener import SerialListener
                from novatel_parser import NovatelParser
                self.novatel_parser = NovatelParser()
                
        except ImportError as e:
            logger.error(f"Error importing required modules: {e}")
            console_print("Error importing required modules. Check logs for details.", force=True)
            console_print("Make sure all dependencies are installed: pip install -r requirements.txt", force=True)
            raise
            
        self.running = False
        self.display_thread: Optional[threading.Thread] = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def start(self):
        """Start the navigation listener"""
        console_print("=" * 60, force=True)
        if config.PROTOCOL_MODE == 'novatel':
            console_print("Starting Novatel ProPak6 Serial Navigation Toolkit...", force=True)
        else:
            console_print("Starting Novatel ProPak6 UDP Navigation Toolkit...", force=True)
        console_print("=" * 60, force=True)
        
        # Log configuration details to file
        logger.main_process("Starting navigation listener")
        logger.info(f"Configuration - Protocol Mode: {config.PROTOCOL_MODE}")
        
        if config.PROTOCOL_MODE == 'novatel':
            logger.info(f"Serial Port: {config.SERIAL_PORT}")
            logger.info(f"Serial Baudrate: {config.SERIAL_BAUDRATE}")
            logger.info(f"Serial Config: {config.SERIAL_BYTESIZE}{config.SERIAL_PARITY}{config.SERIAL_STOPBITS}")
            logger.info(f"Serial Timeout: {config.SERIAL_TIMEOUT}s")
        else:
            logger.info(f"UDP Host: {config.UDP_HOST}")
            logger.info(f"UDP Port: {config.UDP_PORT}")
            logger.info(f"Socket Timeout: {config.SOCKET_TIMEOUT}s")
            logger.info(f"Buffer Size: {config.BUFFER_SIZE} bytes")
        
        logger.info(f"Update Interval: {config.UPDATE_INTERVAL}s")
        logger.info(f"Logging to: {config.LOG_FILE}")
        
        if config.PROTOCOL_MODE == 'novatel':
            console_print("Expected Novatel messages: BESTPOS, BESTVEL, INSPVA, INSPVAX", force=True)
        else:
            console_print("Expected NMEA 0183 sentences: GGA, RMC, VTG, GLL", force=True)
        console_print("Press Ctrl+C to stop", force=True)
        console_print("=" * 60, force=True)
        
        # Start appropriate listener based on protocol mode
        success = False
        
        if config.PROTOCOL_MODE == 'novatel':
            success = self._start_serial_listener()
        else:
            success = self._start_udp_listener()
        
        if not success:
            return False
        
        # Start display update thread
        logger.main_process("Starting display thread...")
        self.running = True
        self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
        self.display_thread.start()
        
        logger.main_process("Display thread started")
        logger.main_process("Entering main loop - waiting for data...")
        console_print("Listening for navigation data... (check logs/navigation_data.log for details)", force=True)
        
        # Main loop
        try:
            loop_count = 0
            while self.running:
                time.sleep(1.0)
                loop_count += 1
                
                # Log periodic status
                if loop_count % 30 == 0:  # Every 30 seconds
                    if config.PROTOCOL_MODE == 'novatel' and self.novatel_parser:
                        stats = self.novatel_parser.get_stats()
                        logger.main_process(f"Status check - Messages parsed: {stats['messages_parsed']}, Errors: {stats['parse_errors']}")
                    else:
                        stats = self.nmea_parser.get_stats()
                        logger.main_process(f"Status check - Sentences parsed: {stats['sentences_parsed']}, Errors: {stats['parse_errors']}")
                
                # Check if listener is still running
                if config.PROTOCOL_MODE == 'novatel':
                    if self.serial_listener and not self.serial_listener.is_listening():
                        logger.error("Serial listener stopped unexpectedly")
                        console_print("Serial listener stopped unexpectedly", force=True)
                        break
                else:
                    if self.udp_listener and not self.udp_listener.is_listening():
                        logger.error("UDP listener stopped unexpectedly")
                        console_print("UDP listener stopped unexpectedly", force=True)
                        break
                    
        except KeyboardInterrupt:
            logger.main_process("Keyboard interrupt received")
            console_print("\nShutting down...", force=True)
        
        self.stop()
        return True
    
    def _start_udp_listener(self) -> bool:
        """Start UDP listener"""
        # Create UDP listener with callback
        logger.main_process("Creating UDP listener...")
        self.udp_listener = UDPListener(self._handle_udp_data)
        
        # Start UDP listener
        logger.main_process("Starting UDP listener...")
        if not self.udp_listener.start():
            logger.error("Failed to start UDP listener")
            console_print("Failed to start UDP listener", force=True)
            return False
        
        logger.main_process("UDP listener started successfully")
        return True
    
    def _start_serial_listener(self) -> bool:
        """Start serial listener for Novatel"""
        try:
            from serial_listener import SerialListener
            
            # Create serial listener with callback
            logger.main_process("Creating serial listener...")
            self.serial_listener = SerialListener(self._handle_serial_data)
            
            # Start serial listener
            logger.main_process("Starting serial listener...")
            if not self.serial_listener.start():
                logger.error("Failed to start serial listener")
                return False
            
            logger.main_process("Serial listener started successfully")
            return True
            
        except ImportError as e:
            logger.error(f"Serial communication not available: {e}")
            logger.error("Install pyserial: pip install pyserial")
            return False
    
    def stop(self):
        """Stop the navigation listener"""
        logger.main_process("Stopping navigation listener...")
        console_print("Stopping navigation listener...", force=True)
        
        self.running = False
        
        if self.udp_listener:
            self.udp_listener.stop()
        
        if self.serial_listener:
            self.serial_listener.stop()
        
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=2.0)
        
        logger.main_process("Navigation listener stopped")
        console_print("Navigation listener stopped", force=True)
    
    def _handle_serial_data(self, data):
        """
        Handle incoming serial data from Novatel
        
        Args:
            data: Raw serial data (bytes)
        """
        if config.LOG_SERIAL_TRAFFIC:
            logger.serial_traffic(f"Received serial data callback with {len(data)} bytes")
        
        # Parse Novatel message
        if self.novatel_parser:
            parse_start_time = time.time()
            parsed_data = self.novatel_parser.parse_message(data)
            
            if parsed_data:
                if config.LOG_NOVATEL_MESSAGES:
                    logger.novatel_msg(f"Successfully parsed Novatel data: {parsed_data}")
                # Log to comprehensive JSON if enabled
                comprehensive_json_logger.log_decoded_message(
                    data=parsed_data,
                    source="NovAtel",
                    parser_name="NovatelParser",
                    raw_data=data,
                    parsing_start_time=parse_start_time
                )
            else:
                if config.LOG_NOVATEL_MESSAGES:
                    logger.novatel_msg("No data extracted from Novatel message")
    
    def _handle_udp_data(self, data):
        """
        Handle incoming UDP data
        
        Args:
            data: Raw UDP data (string for NMEA, bytes for ADS-B)
        """
        if config.PROTOCOL_MODE == 'adsb':
            self._handle_adsb_data(data)
        elif config.PROTOCOL_MODE == 'nmea':
            self._handle_nmea_data(data)
        elif config.PROTOCOL_MODE == 'novatel':
            # Novatel over UDP (less common, but possible)
            self._handle_novatel_data(data)
        else:  # auto mode
            # Try to detect protocol automatically
            if isinstance(data, bytes):
                # Could be ADS-B or Novatel binary
                if data.startswith(b'\xaa\x44\x12\x1c'):  # Novatel sync
                    self._handle_novatel_data(data)
                else:
                    self._handle_adsb_data(data)
            else:
                # Could be NMEA or Novatel ASCII
                text = str(data).strip()
                if text.startswith('#') or text.startswith('%'):
                    self._handle_novatel_data(data.encode('ascii'))
                else:
                    self._handle_nmea_data(data)
    
    def _handle_novatel_data(self, data):
        """Handle Novatel data (from UDP or serial)"""
        if config.LOG_UDP_TRAFFIC:
            logger.udp_traffic(f"Received Novatel data callback with {len(data)} bytes")
        
        # Parse Novatel message
        if self.novatel_parser:
            parse_start_time = time.time()
            parsed_data = self.novatel_parser.parse_message(data)
            
            if parsed_data:
                if config.LOG_NOVATEL_MESSAGES:
                    logger.novatel_msg(f"Successfully parsed Novatel data: {parsed_data}")
                # Log to comprehensive JSON if enabled
                comprehensive_json_logger.log_decoded_message(
                    data=parsed_data,
                    source="NovAtel",
                    parser_name="NovatelParser",
                    raw_data=data,
                    parsing_start_time=parse_start_time
                )
            else:
                if config.LOG_NOVATEL_MESSAGES:
                    logger.novatel_msg("No data extracted from Novatel message")
    
    def _handle_nmea_data(self, data: str):
        """Handle NMEA data"""
        logger.main_process(f"Received NMEA data callback with {len(data)} characters")
        
        # Log raw data for debugging corruption
        if config.LOG_HEX_DATA:
            raw_bytes = data.encode('utf-8', errors='replace')
            logger.hex_data(raw_bytes, "NMEA-RAW")
        
        # Split data into individual NMEA sentences
        sentences = data.strip().split('\n')
        
        logger.main_process(f"Split into {len(sentences)} sentences")
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if sentence:
                logger.main_process(f"Processing sentence {i+1}/{len(sentences)}: {repr(sentence)}")
                
                # Parse NMEA sentence
                parse_start_time = time.time()
                parsed_data = self.nmea_parser.parse_sentence(sentence)
                
                if parsed_data:
                    logger.main_process(f"Successfully parsed NMEA data: {parsed_data}")
                    # Log to JSON events if enabled
                    json_event_logger.log_nmea_event(parsed_data)
                    # Log to comprehensive JSON if enabled
                    comprehensive_json_logger.log_decoded_message(
                        data=parsed_data,
                        source="NMEA",
                        parser_name="NMEAParser",
                        raw_data=sentence,
                        parsing_start_time=parse_start_time
                    )
                else:
                    logger.main_process("No data extracted from NMEA sentence")
                
                # Log raw NMEA if configured
                logger.nmea_raw(sentence)
                if parsed_data:
                    logger.nmea_parse(f"Parsed: {parsed_data}")
            else:
                logger.main_process(f"Skipping empty sentence {i+1}")
    
    def _handle_adsb_data(self, data: bytes):
        """Handle ADS-B data"""
        logger.udp_traffic(f"Received ADS-B data callback with {len(data)} bytes")
        
        # Parse ADS-B message
        parse_start_time = time.time()
        parsed_data = self.adsb_parser.parse_message(data)
        
        if parsed_data:
            logger.info(f"Successfully parsed ADS-B data: {parsed_data}")
            # Log to JSON events if enabled
            json_event_logger.log_adsb_event(parsed_data)
            # Log to comprehensive JSON if enabled
            comprehensive_json_logger.log_decoded_message(
                data=parsed_data,
                source="ADS-B",
                parser_name="ADSBParser",
                raw_data=data,
                parsing_start_time=parse_start_time
            )
        else:
            logger.debug("No data extracted from ADS-B message")
    
    def _display_loop(self):
        """Display update loop (runs in separate thread)"""
        while self.running:
            try:
                # Get latest data based on protocol mode
                if config.PROTOCOL_MODE == 'adsb':
                    nav_data = self.adsb_parser.get_latest_aviation_data()
                    parser_stats = self.adsb_parser.get_stats()
                elif config.PROTOCOL_MODE == 'nmea':
                    nav_data = self.nmea_parser.get_latest_navigation_data()
                    parser_stats = self.nmea_parser.get_stats()
                elif config.PROTOCOL_MODE == 'novatel':
                    nav_data = self.novatel_parser.get_latest_navigation_data() if self.novatel_parser else {}
                    parser_stats = self.novatel_parser.get_stats() if self.novatel_parser else {}
                else:  # auto mode - combine all
                    nmea_data = self.nmea_parser.get_latest_navigation_data()
                    adsb_data = self.adsb_parser.get_latest_aviation_data()
                    novatel_data = self.novatel_parser.get_latest_navigation_data() if self.novatel_parser else {}
                    
                    # Combine data with precedence: Novatel > ADS-B > NMEA
                    nav_data = {**nmea_data, **adsb_data, **novatel_data}
                    
                    nmea_stats = self.nmea_parser.get_stats()
                    adsb_stats = self.adsb_parser.get_stats()
                    novatel_stats = self.novatel_parser.get_stats() if self.novatel_parser else {}
                    
                    parser_stats = {
                        'nmea_' + k: v for k, v in nmea_stats.items()
                    }
                    parser_stats.update({
                        'adsb_' + k: v for k, v in adsb_stats.items()
                    })
                    parser_stats.update({
                        'novatel_' + k: v for k, v in novatel_stats.items()
                    })
                
                # Get other statistics
                listener_stats = {}
                if self.udp_listener:
                    listener_stats.update(self.udp_listener.get_stats())
                if self.serial_listener:
                    listener_stats.update(self.serial_listener.get_stats())
                
                display_stats = self.display.get_stats()
                
                # Combine statistics
                combined_stats = {**parser_stats, **listener_stats, **display_stats}
                
                # Display data
                self.display.display(nav_data, combined_stats)
                
                # Wait for next update
                time.sleep(config.UPDATE_INTERVAL)
                
            except Exception as e:
                logger.error(f"Display error: {e}")
                time.sleep(1.0)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        logger.main_process(f"Received signal {signum}")
        console_print(f"\nReceived signal {signum}", force=True)
        self.running = False


def parse_single_message(message_hex: str) -> int:
    """
    Parse a single ADS-B message and display comprehensive results
    
    Args:
        message_hex: Hex string of the raw message to parse
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    logger.info("=" * 60)
    logger.info("ADS-B Message Parser - Single Message Analysis")
    logger.info("=" * 60)
    logger.info(f"Input message: {message_hex}")
    
    try:
        # Import ADS-B parser only when needed
        try:
            from adsb_parser import ADSBParser
        except ImportError as e:
            logger.error(f"Failed to import ADS-B parser - {e}")
            logger.error("Make sure all dependencies are installed: pip install -r requirements.txt")
            return 1
        
        # Convert hex string to bytes
        if message_hex.startswith('0x') or message_hex.startswith('0X'):
            message_hex = message_hex[2:]
        
        # Remove any spaces or non-hex characters
        message_hex = ''.join(c for c in message_hex if c in '0123456789abcdefABCDEF')
        
        if len(message_hex) % 2 != 0:
            logger.error("Hex string must have even number of characters")
            return 1
            
        message_bytes = bytes.fromhex(message_hex)
        logger.info(f"Message length: {len(message_bytes)} bytes ({len(message_hex)} hex chars)")
        logger.info(f"Message bytes: {message_bytes.hex().upper()}")
        
        # Enable detailed logging for this parse
        original_log_setting = config.LOG_PARSE_ATTEMPTS
        config.LOG_PARSE_ATTEMPTS = True
        
        # Create parser and parse message
        parser = ADSBParser()
        parse_start_time = time.time()
        result = parser.parse_message(message_bytes)
        
        # Log to comprehensive JSON if enabled
        if result and comprehensive_json_logger.is_enabled():
            comprehensive_json_logger.log_decoded_message(
                data=result,
                source="ADS-B",
                parser_name="ADSBParser",
                raw_data=message_bytes,
                parsing_start_time=parse_start_time
            )
            logger.info(f"Logged to comprehensive JSON: {comprehensive_json_logger.log_file}")
        
        # Restore original logging setting
        config.LOG_PARSE_ATTEMPTS = original_log_setting
        
        logger.info("=" * 60)
        logger.info("PARSING RESULTS")
        logger.info("=" * 60)
        
        if result:
            logger.info("✅ Message parsed successfully!")
            logger.info("Extracted Data:")
            logger.info("-" * 40)
            for key, value in result.items():
                if key == 'parsed_timestamp':
                    logger.info(f"  {key:20}: {value.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                else:
                    logger.info(f"  {key:20}: {value}")
        else:
            logger.info("❌ Message parsing failed")
            logger.info("This could be due to:")
            logger.info("  - Invalid message format")
            logger.info("  - Unsupported downlink format")
            logger.info("  - Corrupted data")
            logger.info("  - Message type not implemented")
        
        logger.info("Parser Statistics:")
        logger.info("-" * 40)
        stats = parser.get_stats()
        for key, value in stats.items():
            logger.info(f"  {key:25}: {value}")
        
        logger.info("Message Analysis Complete")
        logger.info("=" * 60)
        
        return 0 if result else 1
        
    except ValueError as e:
        logger.error(f"Invalid hex string - {e}")
        return 1
    except Exception as e:
        logger.error(f"Failed to parse message - {e}")
        return 1


def print_usage():
    """Print usage information"""
    print("Novatel ProPak6 Navigation Data Toolkit")
    print("=" * 60)
    print("Usage: python main.py [options]")
    print()
    print("Options:")
    print("  -h, --help                Show this help message")
    print("  -p, --port PORT           UDP port to listen on (default: 4001)")
    print("  -s, --serial PORT         Serial port for Novatel interface (e.g., /dev/ttyUSB0, COM1)")
    print("  -b, --baud RATE           Serial baud rate (default: 115200)")
    print("  -v, --verbose             Enable verbose logging")
    print("  --json-events             Stream parsed data to json_events.log")
    print("  --comprehensive-json      Enable comprehensive JSON logging with rich metadata")
    print("  --no-clear                Don't clear screen between updates")
    print("  --adsb                    Enable ADS-B mode for aviation data")
    print("  --nmea                    Enable NMEA mode for navigation data (default)")
    print("  --novatel                 Enable Novatel mode for serial GNSS data")
    print("  --auto                    Auto-detect protocol (NMEA/ADS-B/Novatel)")
    print("  --parse-message HEX       Parse single raw message and exit")
    print("  --list-ports              List available serial ports")
    print()
    print("Examples:")
    print("  python main.py --nmea                    # Listen for NMEA over UDP")
    print("  python main.py --adsb -v                 # Listen for ADS-B with verbose logging")
    print("  python main.py --novatel -s /dev/ttyUSB0 # Connect to Novatel via serial")
    print("  python main.py --novatel -s COM1 -b 9600 # Windows serial at 9600 baud")
    print("  python main.py --auto                    # Auto-detect all protocols")
    print("  python main.py --parse-message 8D4840D6202CC371C32CE0576098")
    print("  python main.py --list-ports              # Show available serial ports")
    print()
    print("Configuration:")
    print(f"  Protocol Mode: {config.PROTOCOL_MODE}")
    print(f"  UDP Port: {config.UDP_PORT}")
    print(f"  Serial Port: {config.SERIAL_PORT}")
    print(f"  Serial Baud: {config.SERIAL_BAUDRATE}")
    print(f"  Update Interval: {config.UPDATE_INTERVAL}s")
    print(f"  Coordinate Precision: {config.COORDINATE_PRECISION} decimal places")
    print(f"  Altitude Units: {config.ALTITUDE_UNITS}")
    print(f"  Speed Units: {config.SPEED_UNITS}")
    print()
    print("Supported Data Formats:")
    print("  NMEA 0183: GGA, RMC, VTG, GLL sentences")
    print("  ADS-B: Mode S Extended Squitter (DF=17) messages")
    print("  Novatel: BESTPOS, BESTVEL, INSPVA, INSPVAX (ASCII & Binary)")


def list_serial_ports():
    """List available serial ports"""
    try:
        from serial_listener import SerialListener
        ports = SerialListener.list_available_ports()
        
        print("Available Serial Ports:")
        print("=" * 30)
        if ports:
            for port in ports:
                # Test if port can be opened
                if SerialListener.test_port(port):
                    print(f"  {port} ✅ (accessible)")
                else:
                    print(f"  {port} ❌ (in use or restricted)")
        else:
            print("  No serial ports found")
        
        return 0
        
    except ImportError:
        print("Error: pyserial is required to list serial ports")
        print("Install with: pip install pyserial")
        return 1


def main():
    """Main entry point"""
    # Parse command line arguments
    i = 1
    parse_message_hex = None
    
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg in ['-h', '--help']:
            print_usage()
            return 0
        elif arg in ['-p', '--port'] and i + 1 < len(sys.argv):
            try:
                config.UDP_PORT = int(sys.argv[i + 1])
                i += 1  # Skip next argument
            except ValueError:
                print("Error: Invalid port number")
                return 1
        elif arg in ['-s', '--serial'] and i + 1 < len(sys.argv):
            config.SERIAL_PORT = sys.argv[i + 1]
            i += 1  # Skip next argument
        elif arg in ['-b', '--baud'] and i + 1 < len(sys.argv):
            try:
                config.SERIAL_BAUDRATE = int(sys.argv[i + 1])
                i += 1  # Skip next argument
            except ValueError:
                print("Error: Invalid baud rate")
                return 1
        elif arg in ['-v', '--verbose']:
            config.LOG_RAW_NMEA = True
            config.LOG_UDP_TRAFFIC = True
            config.LOG_PARSE_ATTEMPTS = True
            config.LOG_SERIAL_TRAFFIC = True
            config.LOG_NOVATEL_MESSAGES = True
        elif arg == '--json-events':
            config.ENABLE_JSON_EVENT_LOGGING = True
            logger.info("JSON event logging enabled")
        elif arg == '--comprehensive-json':
            config.ENABLE_COMPREHENSIVE_JSON_LOGGING = True
            comprehensive_json_logger.enable()
            logger.info("Comprehensive JSON logging enabled")
        elif arg == '--no-clear':
            config.CLEAR_SCREEN = False
        elif arg == '--adsb':
            config.PROTOCOL_MODE = 'adsb'
            logger.info("ADS-B mode enabled")
        elif arg == '--nmea':
            config.PROTOCOL_MODE = 'nmea'
            logger.info("NMEA mode enabled")
        elif arg == '--novatel':
            config.PROTOCOL_MODE = 'novatel'
            logger.info("Novatel mode enabled")
        elif arg == '--auto':
            config.PROTOCOL_MODE = 'auto'
            logger.info("Auto-detect mode enabled")
        elif arg == '--list-ports':
            return list_serial_ports()
        elif arg == '--parse-message' and i + 1 < len(sys.argv):
            parse_message_hex = sys.argv[i + 1]
            i += 1  # Skip next argument
        else:
            print(f"Unknown argument: {arg}")
            print("Use -h or --help for usage information")
            return 1
        
        i += 1
    
    # Handle single message parsing mode
    if parse_message_hex:
        return parse_single_message(parse_message_hex)
    
    # Check dependencies based on protocol mode
    if config.PROTOCOL_MODE in ['adsb', 'auto']:
        try:
            import pyModeS
        except ImportError:
            print("Error: pyModeS is required for ADS-B mode")
            print("Install with: pip install -r requirements.txt")
            return 1
    
    if config.PROTOCOL_MODE in ['novatel', 'auto']:
        try:
            import serial
        except ImportError:
            print("Error: pyserial is required for Novatel serial mode")
            print("Install with: pip install pyserial")
            return 1
    
    # Create and start navigation listener
    try:
        listener = NavigationListener()
        success = listener.start()
        return 0 if success else 1
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())