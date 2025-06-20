"""
Configuration settings for Novatel ProPak6 Navigation Data Toolkit
"""

# Network Configuration
UDP_PORT = 4001
UDP_HOST = '0.0.0.0'  # Listen on all interfaces
SOCKET_TIMEOUT = 5.0  # seconds
BUFFER_SIZE = 1024

# Display Configuration
UPDATE_INTERVAL = 1.0  # seconds between display updates
CLEAR_SCREEN = True    # Clear screen between updates

# Data Configuration
COORDINATE_PRECISION = 6  # decimal places for lat/lon
ALTITUDE_UNITS = 'both'   # 'feet', 'meters', or 'both'
SPEED_UNITS = 'both'      # 'knots', 'kmh', 'mph', or 'both'

# Protocol Configuration
PROTOCOL_MODE = 'nmea'    # 'nmea', 'adsb', 'novatel', or 'auto'
ADSB_REFERENCE_LAT = 0.0  # Reference latitude for ADS-B position decoding
ADSB_REFERENCE_LON = 0.0  # Reference longitude for ADS-B position decoding

# Serial Port Configuration (for Novatel interface)
SERIAL_PORT = '/dev/ttyUSB0'    # Serial port device (Linux/Mac) or 'COM1' (Windows)
SERIAL_BAUDRATE = 115200        # Baud rate (common: 9600, 38400, 115200)
SERIAL_BYTESIZE = 8             # Data bits (5, 6, 7, 8)
SERIAL_PARITY = 'N'             # Parity ('N'=None, 'E'=Even, 'O'=Odd, 'M'=Mark, 'S'=Space)
SERIAL_STOPBITS = 1             # Stop bits (1, 1.5, 2)
SERIAL_TIMEOUT = 1.0            # Read timeout in seconds
SERIAL_XONXOFF = False          # Software flow control
SERIAL_RTSCTS = False           # Hardware (RTS/CTS) flow control
SERIAL_DSRDTR = False           # Hardware (DSR/DTR) flow control

# Logging Configuration
ENABLE_LOGGING = True
LOG_FILE = 'logs/navigation_data.log'
LOG_RAW_NMEA = True
LOG_UDP_TRAFFIC = True
LOG_PARSE_ATTEMPTS = True
LOG_SERIAL_TRAFFIC = True      # Log serial port communication
LOG_NOVATEL_MESSAGES = True    # Log Novatel message parsing
LOG_HEX_DATA = True            # Log raw hex data for debugging corruption

# GDL-90 Configuration
GDL90_ENABLED = True                    # Enable GDL-90 deframing
LOG_GDL90_FRAMES = True                 # Log frame detection
LOG_DEFRAMING_PROCESS = True            # Log detailed deframing steps
GDL90_VALIDATE_CHECKSUMS = False        # Validate GDL-90 checksums (if present)
GDL90_STRICT_FRAMING = True             # Strict frame boundary checking

# Error Handling
MAX_PARSE_ERRORS = 10       # Max consecutive parse errors before warning
RECONNECT_DELAY = 5.0       # seconds to wait before reconnecting
MAX_SERIAL_ERRORS = 5       # Max consecutive serial errors before stopping
SERIAL_RECONNECT_DELAY = 2.0 # seconds to wait before serial reconnection

# UDP Replay Configuration
REPLAY_LOG_FILE = 'data/udp_events.log'
REPLAY_TARGET_HOST = 'localhost'
REPLAY_TARGET_PORT = 4001
REPLAY_SPEED_MULTIPLIER = 1.0
REPLAY_LOOP_MODE = False
REPLAY_INTER_MESSAGE_DELAY = 0.01  # seconds

# Interactive Debugging
REPLAY_INTERACTIVE_MODE = False
REPLAY_STEP_MODE = False
REPLAY_PAUSE_ON_ERROR = False
REPLAY_HEX_DUMP_WIDTH = 16
REPLAY_MAX_INSPECT_BYTES = 1024

# Message Filtering
REPLAY_FILTER_MIN_SIZE = 0
REPLAY_FILTER_MAX_SIZE = float('inf')
REPLAY_FILTER_PATTERNS = []
REPLAY_SKIP_CORRUPTED = False

# Breakpoints
REPLAY_BREAKPOINT_ON_ERRORS = False
REPLAY_BREAKPOINT_PATTERNS = []
REPLAY_MAX_CONSECUTIVE_ERRORS = 10

# Statistics
REPLAY_ENABLE_STATISTICS = True
REPLAY_STATISTICS_INTERVAL = 100  # messages
REPLAY_SAVE_STATISTICS = False
REPLAY_STATISTICS_FILE = 'logs/replay_statistics.json'

# NovAtel PASSCOM Settings
ENABLE_PASSCOM_PARSER = True
LOG_PASSCOM_FRAMES = False
LOG_ALTITUDE_DECODING = False
PASSCOM_FRAME_TIMEOUT_MS = 1000

# Altitude Validation
MIN_VALID_ALTITUDE_FT = -1000
MAX_VALID_ALTITUDE_FT = 60000
ENABLE_ALTITUDE_SANITY_CHECKS = True
ALTITUDE_CHANGE_RATE_LIMIT_FPM = 6000  # Maximum climb/descent rate

# Frame Filtering
ACCEPTED_DOWNLINK_FORMATS = [17, 18]  # ADS-B ES
REQUIRE_CRC_VALIDATION = True
ENABLE_GEOMETRIC_ALTITUDE = True

# Performance Settings
PASSCOM_BUFFER_SIZE = 4096
MAX_FRAMES_PER_PACKET = 10

# JSON Event Logging
ENABLE_JSON_EVENT_LOGGING = False   # Enable JSON event streaming to json_events.log
JSON_EVENTS_LOG_FILE = 'logs/json_events.log'  # JSON events log file path

# Comprehensive JSON Logging (separate from basic JSON events)
ENABLE_COMPREHENSIVE_JSON_LOGGING = False  # Comprehensive decoded message logging
COMPREHENSIVE_JSON_LOG_FILE = 'logs/decoded_messages.log'  # Comprehensive log file
INCLUDE_RAW_MESSAGE_DATA = True  # Include raw hex/binary data in logs
INCLUDE_PARSING_METADATA = True  # Include parsing timestamps and statistics
INCLUDE_GPS_METADATA = True     # Include GPS week, time, and timing data
INCLUDE_SIGNAL_QUALITY = True   # Include PDOP, HDOP, accuracy, satellite count
INCLUDE_PERFORMANCE_METRICS = True  # Include parsing duration and validation