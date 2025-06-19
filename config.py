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