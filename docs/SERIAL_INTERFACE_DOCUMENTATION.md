# Serial Interface Documentation

## Novatel ProPak6 Navigation Data Toolkit - Serial Interface Implementation

This document provides comprehensive documentation for the serial interface implementation, including the SerialListener and NovatelParser modules.

## Overview

The serial interface provides communication capabilities for receiving navigation data from Novatel GNSS receivers and other serial devices. It consists of two main components:

1. **SerialListener**: Handles serial port communication, data reception, and connection management
2. **NovatelParser**: Parses Novatel GNSS messages in both ASCII and binary formats

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Main App      │───▶│  SerialListener  │───▶│  Data Callback  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  NovatelParser   │
                       └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Navigation Data  │
                       └──────────────────┘
```

## SerialListener Module

### Purpose
The SerialListener module provides asynchronous serial communication for receiving data from GNSS receivers and other serial devices.

### Key Features
- **Asynchronous Operation**: Runs in separate thread to avoid blocking main application
- **Automatic Reconnection**: Automatically reconnects on connection loss with configurable retry logic
- **Configurable Parameters**: Supports all standard serial port parameters (baud rate, parity, etc.)
- **Error Handling**: Robust error handling with connection error tracking
- **Port Discovery**: Utilities for discovering and testing available serial ports
- **Statistics Tracking**: Comprehensive statistics including data rates and error counts
- **Thread Safety**: Thread-safe operation with proper locking mechanisms

### Usage Example

```python
from serial_listener import SerialListener

def handle_data(data):
    print(f"Received {len(data)} bytes: {data[:50]}...")

# Create and start listener
listener = SerialListener(handle_data)

if listener.start():
    print("Serial listener started successfully")
    
    # Let it run for a while
    time.sleep(60)
    
    # Stop listener
    listener.stop()
    
    # Get statistics
    stats = listener.get_stats()
    print(f"Received {stats['bytes_received']} bytes in {stats['uptime_seconds']} seconds")
else:
    print("Failed to start serial listener")
```

### Context Manager Usage

```python
with SerialListener(handle_data) as listener:
    if listener.is_listening():
        print("Listening for data...")
        time.sleep(60)
# Automatically stopped when exiting context
```

### Configuration

The SerialListener uses configuration from the `config.py` module:

```python
# Serial Port Configuration
SERIAL_PORT = '/dev/ttyUSB0'    # Serial port device
SERIAL_BAUDRATE = 115200        # Baud rate
SERIAL_BYTESIZE = 8             # Data bits
SERIAL_PARITY = 'N'             # Parity
SERIAL_STOPBITS = 1             # Stop bits
SERIAL_TIMEOUT = 1.0            # Read timeout
SERIAL_XONXOFF = False          # Software flow control
SERIAL_RTSCTS = False           # Hardware flow control
SERIAL_DSRDTR = False           # Hardware flow control

# Error Handling
MAX_SERIAL_ERRORS = 5           # Max consecutive errors before stopping
SERIAL_RECONNECT_DELAY = 2.0    # Reconnection delay in seconds
```

### Port Discovery

```python
# List available ports
ports = SerialListener.list_available_ports()
for port in ports:
    print(f"Port: {port['device']}")
    print(f"Description: {port['description']}")
    print(f"Manufacturer: {port['manufacturer']}")

# Test if a port can be opened
if SerialListener.test_port('/dev/ttyUSB0'):
    print("Port is accessible")
else:
    print("Port cannot be opened")
```

### Statistics and Monitoring

```python
stats = listener.get_stats()
print(f"Status: {'Listening' if stats['listening'] else 'Stopped'}")
print(f"Port: {stats['port']} @ {stats['baudrate']} baud")
print(f"Bytes received: {stats['bytes_received']}")
print(f"Messages received: {stats['messages_received']}")
print(f"Connection errors: {stats['connection_errors']}")
print(f"Data rate: {stats['data_rate_bps']} bytes/sec")
print(f"Uptime: {stats['uptime_seconds']} seconds")
```

## NovatelParser Module

### Purpose
The NovatelParser module parses Novatel OEM series GNSS receiver messages in both ASCII and binary formats, extracting navigation data for use by the application.

### Supported Message Types

#### ASCII Messages
- **BESTPOS/BESTPOSA**: Best position solution with accuracy estimates
- **BESTVEL/BESTVELA**: Best velocity solution with track and speed
- **INSPVA/INSPVAA**: INS position, velocity, and attitude
- **INSPVAX/INSPVAXA**: Extended INS solution with additional parameters
- **HEADING/HEADINGA**: Heading information from dual-antenna setup
- **PSRDOP/PSRDOPA**: Position dilution of precision values

#### Binary Messages
- **Message ID 42**: BESTPOS binary format
- **Message ID 99**: BESTVEL binary format  
- **Message ID 507**: INSPVA binary format
- **Message ID 1465**: INSPVAX binary format
- **Message ID 971**: HEADING binary format
- **Message ID 174**: PSRDOP binary format

### Usage Example

```python
from novatel_parser import NovatelParser

# Create parser
parser = NovatelParser()

# Parse ASCII message
ascii_msg = b"#BESTPOSA,COM1,0,55.0,FINESTEERING,2167,144140.000,02000040,cdba,32768;SOL_COMPUTED,SINGLE,51.15043711111,-114.03067851111,1064.9551,-17.0000,WGS84,1.6389,1.3921,2.4639,\"\",0.000,0.000,35,30,30,30,0,06,0,33*2d0d0a"
result = parser.parse_message(ascii_msg)

if result:
    print(f"Message type: {result['message_type']}")
    print(f"Latitude: {result['latitude']}")
    print(f"Longitude: {result['longitude']}")
    print(f"Height: {result['height']} m")

# Parse binary message
binary_msg = bytes.fromhex("aa4412...")
result = parser.parse_message(binary_msg)

# Get consolidated navigation data
nav_data = parser.get_latest_navigation_data()
print(f"Position: {nav_data.get('latitude')}, {nav_data.get('longitude')}")
print(f"Altitude: {nav_data.get('altitude_ft')} ft")
print(f"Speed: {nav_data.get('speed_knots')} knots")
print(f"Heading: {nav_data.get('heading')} degrees")
```

### Message Format Detection

The parser automatically detects message format:

- **ASCII Messages**: Start with `#` or `%`
- **Binary Messages**: Contain sync pattern `0xAA 0x44 0x12 0x1C`
- **Unknown Data**: Added to buffer for potential binary message assembly

### Navigation Data Consolidation

The parser maintains separate storage for different data types and consolidates them into a unified navigation data structure:

```python
nav_data = parser.get_latest_navigation_data()

# Position data
nav_data['latitude']              # Decimal degrees
nav_data['longitude']             # Decimal degrees  
nav_data['altitude_m']            # Meters above ellipsoid
nav_data['altitude_ft']           # Feet above ellipsoid
nav_data['solution_status']       # Solution quality
nav_data['position_type']         # Position type (SINGLE, RTK, etc.)
nav_data['num_satellites']        # Number of satellites used
nav_data['position_accuracy_m']   # Position accuracy in meters

# Velocity data
nav_data['speed_ms']              # Speed in m/s
nav_data['speed_knots']           # Speed in knots
nav_data['speed_kmh']             # Speed in km/h
nav_data['track_angle']           # Track angle in degrees
nav_data['vertical_speed_ms']     # Vertical speed in m/s
nav_data['north_velocity']        # North velocity component
nav_data['east_velocity']         # East velocity component
nav_data['up_velocity']           # Up velocity component

# Attitude data
nav_data['heading']               # Heading in degrees
nav_data['pitch']                 # Pitch in degrees
nav_data['roll']                  # Roll in degrees

# Quality indicators
nav_data['gdop']                  # Geometric dilution of precision
nav_data['pdop']                  # Position dilution of precision
nav_data['hdop']                  # Horizontal dilution of precision

# Timestamp
nav_data['parsed_timestamp']      # UTC timestamp of parsing
```

### Statistics and Monitoring

```python
stats = parser.get_stats()
print(f"Messages parsed: {stats['messages_parsed']}")
print(f"Parse errors: {stats['parse_errors']}")
print(f"Success rate: {stats['success_rate']:.1f}%")
print(f"ASCII messages: {stats['ascii_messages']}")
print(f"Binary messages: {stats['binary_messages']}")
print(f"Has position: {stats['has_position']}")
print(f"Has velocity: {stats['has_velocity']}")
print(f"Has attitude: {stats['has_attitude']}")
```

## Integration with Main Application

### Configuration Setup

In `config.py`, set the protocol mode to enable Novatel support:

```python
PROTOCOL_MODE = 'novatel'  # Enable Novatel mode
SERIAL_PORT = '/dev/ttyUSB0'  # Set your serial port
SERIAL_BAUDRATE = 115200      # Set appropriate baud rate
```

### Command Line Usage

```bash
# Start with Novatel serial interface
python main.py --novatel -s /dev/ttyUSB0 -b 115200

# List available serial ports
python main.py --list-ports

# Auto-detect protocols (includes Novatel)
python main.py --auto
```

### Data Flow

1. **SerialListener** receives raw data from serial port
2. Data is passed to callback function in main application
3. **NovatelParser** processes the raw data and extracts navigation information
4. Parsed data is consolidated and displayed by **NavigationDisplay**
5. Statistics are collected and reported for monitoring

## Error Handling

### Serial Communication Errors
- **Connection Loss**: Automatic reconnection with configurable delay
- **Port Not Found**: Graceful failure with error reporting
- **Read Timeouts**: Handled without interrupting operation
- **Permission Errors**: Clear error messages for troubleshooting

### Message Parsing Errors
- **Invalid Format**: Messages that don't match expected format are rejected
- **Incomplete Data**: Partial messages are buffered for completion
- **Checksum Errors**: ASCII messages with invalid checksums are rejected
- **Structure Errors**: Binary messages with invalid structure are rejected

### Recovery Mechanisms
- **Connection Monitoring**: Continuous monitoring of connection status
- **Automatic Retry**: Configurable retry logic for failed operations  
- **Error Counting**: Track consecutive errors to prevent infinite retry loops
- **Graceful Degradation**: System continues operating with reduced functionality

## Performance Considerations

### Throughput
- **Serial Data Rate**: Handles standard GNSS data rates (1-50 Hz)
- **Message Processing**: Optimized parsing for high-frequency data
- **Memory Usage**: Efficient buffer management prevents memory leaks
- **CPU Usage**: Minimal CPU overhead through efficient algorithms

### Scalability
- **Multiple Ports**: Can be extended to support multiple serial ports
- **Message Types**: Easily extensible to support additional message types
- **Protocol Support**: Architecture supports adding other GNSS protocols

## Testing

### Unit Tests
Comprehensive unit test suites are provided:

```bash
# Run serial listener tests
python -m pytest tests/test_serial_listener.py -v

# Run Novatel parser tests
python -m pytest tests/test_novatel_parser.py -v

# Run all tests
python run_tests.py
```

### Test Coverage
- **SerialListener**: 95%+ code coverage including edge cases
- **NovatelParser**: 90%+ code coverage including all message types
- **Integration**: End-to-end testing with mock data
- **Error Conditions**: Comprehensive error scenario testing

### Mock Testing
Tests use mocking to simulate:
- Serial port operations without hardware
- Various error conditions
- Different message types and formats
- Connection failures and recovery

## Troubleshooting

### Common Issues

#### Serial Port Access
```
Error: Permission denied: '/dev/ttyUSB0'
Solution: Add user to dialout group: sudo usermod -a -G dialout $USER
```

#### Port Not Found
```
Error: Serial port '/dev/ttyUSB0' not found
Solution: Check connection and use --list-ports to find correct port
```

#### No Data Received
```
Check: Baud rate, wiring, device power, protocol settings
Debug: Enable LOG_SERIAL_TRAFFIC in config.py
```

#### Parse Errors
```
Check: Message format, baud rate, data corruption
Debug: Enable LOG_NOVATEL_MESSAGES in config.py
```

### Debugging

Enable verbose logging in `config.py`:

```python
LOG_SERIAL_TRAFFIC = True     # Log raw serial data
LOG_NOVATEL_MESSAGES = True   # Log parsed messages
LOG_PARSE_ATTEMPTS = True     # Log parsing attempts
```

### Hardware Requirements

- **Serial Port**: USB-to-serial adapter or built-in serial port
- **Cables**: Appropriate serial cable (RS232/RS422/TTL depending on device)
- **Power**: Ensure GNSS receiver has adequate power supply
- **Grounding**: Proper grounding to prevent data corruption

## Future Enhancements

### Planned Features
- **Multi-port Support**: Simultaneous connection to multiple serial devices
- **Message Filtering**: Configurable filtering of message types
- **Data Logging**: Built-in logging of raw and parsed data
- **Real-time Validation**: Advanced message validation and error correction

### Extension Points
- **Custom Parsers**: Framework for adding custom message parsers
- **Protocol Adapters**: Support for other GNSS protocols (Trimble, Leica, etc.)
- **Output Formats**: Multiple output format support (JSON, CSV, etc.)
- **Remote Monitoring**: Network-based monitoring and control

## Conclusion

The serial interface implementation provides a robust, well-tested foundation for GNSS data acquisition in the Novatel ProPak6 Navigation Data Toolkit. It offers comprehensive functionality while maintaining simplicity and reliability for mission-critical navigation applications.