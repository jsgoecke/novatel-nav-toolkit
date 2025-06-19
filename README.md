# Novatel ProPak6 Navigation Data Toolkit

A comprehensive Python application designed for real-time navigation and aviation data processing with the Novatel ProPak6 GNSS receiver. Supports NMEA 0183, ADS-B aviation messages, and native Novatel binary/ASCII protocols with advanced GDL-90 deframing capabilities.

## Features

- **Triple Protocol Support** - NMEA 0183, ADS-B, and Novatel GNSS with protocol auto-detection
- **Multiple interfaces** - UDP network listening and RS-232/RS-422 serial communication
- **Real-time UDP listening** on port 4001 (configurable)
- **Serial port communication** for Novatel GNSS receivers
- **NMEA 0183 parsing** with support for GGA, RMC, VTG, and GLL sentences
- **ADS-B message parsing** with Mode S Extended Squitter (DF=17) decoding
- **Novatel message parsing** - BESTPOS, BESTVEL, INSPVA, INSPVAX (ASCII & Binary)
- **Single message analysis** - Parse individual ADS-B messages for debugging
- **GDL-90 deframing** for extracting ADS-B messages from wrapped UDP data
- **Human-readable display** of GPS coordinates, altitude, speed, heading, and aviation data
- **Multiple unit formats** (feet/meters for altitude, knots/km/h/mph for speed)
- **Live statistics** showing parse success rates and connection status
- **Protocol mode selection** (--nmea, --adsb, --novatel, --auto)
- **Comprehensive logging** with verbose debugging options
- **Error handling** with automatic recovery from network and serial issues
- **Configurable display** with screen clearing and update intervals
- **Serial port discovery** and configuration tools

## Installation

1. Clone or download this repository
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage
```bash
python main.py
```

### Command Line Options
```bash
python main.py [options]

Options:
  -h, --help                Show this help message
  -p, --port PORT           UDP port to listen on (default: 4001)
  -s, --serial PORT         Serial port for Novatel interface (e.g., /dev/ttyUSB0, COM1)
  -b, --baud RATE           Serial baud rate (default: 115200)
  -v, --verbose             Enable verbose logging (shows raw data and parsing details)
  --no-clear                Don't clear screen between updates
  --adsb                    Enable ADS-B mode for aviation data
  --nmea                    Enable NMEA mode for navigation data (default)
  --novatel                 Enable Novatel mode for serial GNSS data
  --auto                    Auto-detect protocol (NMEA/ADS-B/Novatel)
  --parse-message HEX       Parse single raw message and exit
  --list-ports              List available serial ports
```

### Examples
```bash
# Listen for NMEA navigation data over UDP (default)
python main.py --nmea

# Listen for ADS-B aviation data over UDP
python main.py --adsb

# Connect to Novatel GNSS receiver via serial
python main.py --novatel -s /dev/ttyUSB0

# Connect to Novatel on Windows with custom baud rate
python main.py --novatel -s COM1 -b 9600

# Auto-detect all protocol types
python main.py --auto

# Listen on custom UDP port with verbose logging
python main.py -p 5000 -v

# Novatel mode with verbose logging
python main.py --novatel -s /dev/ttyUSB0 -v

# List available serial ports
python main.py --list-ports

# Disable screen clearing for logging to file
python main.py --no-clear > navigation.log

# Parse a single ADS-B message (useful for debugging)
python main.py --parse-message 8D4840D6202CC371C32CE0576098

# Parse ADS-B message with 0x prefix
python main.py --parse-message 0x8D4840D658C382D690C8AC2863A7
```

## Configuration

Edit [`config.py`](config.py) to customize settings:

### Network Settings
- `UDP_PORT`: Port to listen on (default: 4001)
- `UDP_HOST`: Host interface to bind to (default: '0.0.0.0' for all interfaces)
- `SOCKET_TIMEOUT`: Socket timeout in seconds (default: 5.0)
- `BUFFER_SIZE`: UDP receive buffer size (default: 1024)

### Protocol Settings
- `PROTOCOL_MODE`: Protocol selection - 'nmea', 'adsb', 'novatel', or 'auto' (default: 'nmea')
- `ADSB_REFERENCE_LAT`: Reference latitude for ADS-B position decoding
- `ADSB_REFERENCE_LON`: Reference longitude for ADS-B position decoding

### Serial Port Settings (for Novatel interface)
- `SERIAL_PORT`: Serial port device (default: '/dev/ttyUSB0' on Linux/Mac, 'COM1' on Windows)
- `SERIAL_BAUDRATE`: Baud rate (default: 115200, common: 9600, 38400, 115200)
- `SERIAL_BYTESIZE`: Data bits (default: 8, options: 5, 6, 7, 8)
- `SERIAL_PARITY`: Parity checking (default: 'N', options: 'N'=None, 'E'=Even, 'O'=Odd)
- `SERIAL_STOPBITS`: Stop bits (default: 1, options: 1, 1.5, 2)
- `SERIAL_TIMEOUT`: Read timeout in seconds (default: 1.0)
- `SERIAL_XONXOFF`: Software flow control (default: False)
- `SERIAL_RTSCTS`: Hardware RTS/CTS flow control (default: False)
- `SERIAL_DSRDTR`: Hardware DSR/DTR flow control (default: False)

### Display Settings
- `UPDATE_INTERVAL`: Seconds between display updates (default: 1.0)
- `CLEAR_SCREEN`: Whether to clear screen between updates (default: True)
- `COORDINATE_PRECISION`: Decimal places for coordinates (default: 6)
- `ALTITUDE_UNITS`: 'feet', 'meters', or 'both' (default: 'both')
- `SPEED_UNITS`: 'knots', 'kmh', 'mph', or 'both' (default: 'both')

### Logging Settings
- `ENABLE_LOGGING`: Enable file logging (default: True)
- `LOG_FILE`: Log file path (default: 'navigation_data.log')
- `LOG_RAW_NMEA`: Log raw NMEA sentences for debugging
- `LOG_UDP_TRAFFIC`: Log UDP traffic details
- `LOG_PARSE_ATTEMPTS`: Log parsing attempts and results

### GDL-90 Settings
- `GDL90_ENABLED`: Enable GDL-90 deframing (default: True)
- `LOG_GDL90_FRAMES`: Log frame detection details
- `LOG_DEFRAMING_PROCESS`: Log detailed deframing steps
- `GDL90_VALIDATE_CHECKSUMS`: Validate GDL-90 checksums (default: False)
- `GDL90_STRICT_FRAMING`: Strict frame boundary checking (default: True)

### Error Handling Settings
- `MAX_PARSE_ERRORS`: Max consecutive parse errors before warning (default: 10)
- `RECONNECT_DELAY`: Seconds to wait before reconnecting (default: 5.0)

## Sample Output

### NMEA Navigation Mode
```
==================================================
     Novatel ProPak6 Navigation Data (NMEA)
==================================================
Timestamp: 2025-06-16 20:29:05 UTC

Position:  34.052200°N, 118.243700°W
Altitude:  35,000 ft (10,668 m)
Speed:     450.0 knots (833.4 km/h)
Heading:   095° (East)
GPS:       GPS Fix (8 satellites)
Status:    Active

------------------------------
Statistics:
  NMEA sentences parsed: 1247
  Parse errors: 3
  Success rate: 99.8%
  UDP Listener: Active
==================================================
```

### ADS-B Aviation Mode
```
==================================================
     Novatel ProPak6 Aviation Data (ADS-B)
==================================================
Timestamp: 2025-06-16 20:29:05 UTC

Position:  40.123456°N, 74.567890°W
Altitude:  35,000 ft
Speed:     450.0 knots (833.4 km/h)
Heading:   090° (East)
ICAO:      40621D
Callsign:  UAL123
Type Code: 11
V-Rate:    1,200 ft/min climbing

------------------------------
Statistics:
  ADS-B messages parsed: 852
  Aircraft tracked: 3
  GDL-90 frames processed: 425
  Parse errors: 2
  Success rate: 99.8%
  UDP Listener: Active
==================================================
```

### Novatel ProPak6 GNSS Mode
```
==================================================
     Novatel ProPak6 GNSS Data (Native)
==================================================
Timestamp: 2025-06-17 14:29:05 UTC

Position:  34.052200°N, 118.243700°W
Altitude:  35,000 ft (10,668 m)
Speed:     450.0 knots (833.4 km/h)
Heading:   095° (East)
Roll:      2.1° (Right)
Pitch:     3.5° (Up)
INS Status: INS_SOLUTION_GOOD
Position Type: NARROW_INT
Satellites: 12 (GPS), 8 (GLONASS)

------------------------------
Statistics:
  Novatel messages parsed: 245
  ASCII messages: 120
  Binary messages: 125
  Parse errors: 1
  Success rate: 99.6%
  Serial Port: /dev/ttyUSB0 (115200 baud)
==================================================
```

## Single Message Analysis

The `--parse-message` option allows you to analyze individual ADS-B messages for debugging and understanding message content:

```bash
python main.py --parse-message 8D4840D6202CC371C32CE0576098
```

### Sample Output
```
============================================================
ADS-B Message Parser - Single Message Analysis
============================================================
Input message: 8D4840D6202CC371C32CE0576098

Message length: 14 bytes (28 hex chars)
Message bytes: 8D4840D6202CC371C32CE0576098

✅ Message parsed successfully!

Extracted Data:
----------------------------------------
  icao                : 4840d6
  type_code           : 4
  parsed_timestamp    : 2025-06-17 19:55:37 UTC
  callsign            : KLM1023_
  category            : 0

Parser Statistics:
----------------------------------------
  messages_parsed          : 1
  parse_errors             : 0
  success_rate             : 100.0
  aircraft_tracked         : 1
============================================================
```

### Understanding ADS-B Message Types

When analyzing your DS 17 messages (Downlink Format 17 = valid ADS-B):

- **Type Code 1-4**: Aircraft identification (callsign) - **No altitude data**
- **Type Code 9-18**: Airborne position - **Contains altitude data** ✅
- **Type Code 19**: Velocity - **No altitude, but has climb/descent rate**

**If you only see callsign data without altitude:** You're receiving identification messages (TC 1-4). Wait for position messages (TC 9-18) to see altitude data.

## Supported Data Formats

### NMEA 0183 Navigation Data

| Sentence | Description | Data Extracted |
|----------|-------------|----------------|
| **GGA** | Global Positioning System Fix Data | Latitude, longitude, altitude, GPS quality, satellites |
| **RMC** | Recommended Minimum Course | Latitude, longitude, speed, heading, date/time, status |
| **VTG** | Track Made Good and Ground Speed | Heading, speed (knots and km/h) |
| **GLL** | Geographic Position | Latitude, longitude, time, status |

### ADS-B Aviation Data

| Message Type | Description | Data Extracted |
|--------------|-------------|----------------|
| **DF 17** | Extended Squitter | ICAO address, aircraft position, altitude, velocity |
| **TC 1-4** | Aircraft Identification | Callsign, aircraft category |
| **TC 9-18** | Airborne Position | Latitude, longitude, altitude |
| **TC 19** | Airborne Velocity | Ground speed, heading, vertical rate |

### Novatel GNSS Data

| Message Type | Format | Description | Data Extracted |
|--------------|--------|-------------|----------------|
| **BESTPOS** | ASCII/Binary | Best available position | Latitude, longitude, height, accuracy, satellites |
| **BESTVEL** | ASCII/Binary | Best available velocity | Speed, heading, vertical velocity |
| **INSPVA** | ASCII/Binary | INS Position/Velocity/Attitude | Position, velocity, roll, pitch, azimuth |
| **INSPVAX** | ASCII/Binary | Extended INS PVA | INSPVA + standard deviations |
| **BESTXYZ** | ASCII/Binary | ECEF coordinates | X, Y, Z coordinates with accuracy |
| **HEADING** | ASCII/Binary | Vehicle heading | Heading, pitch with accuracy |
| **TIME** | ASCII/Binary | GNSS time information | GPS week, seconds, UTC offset |
| **RANGECMP** | ASCII/Binary | Satellite range data | Raw satellite observations |

### GDL-90 Protocol Support

- **Frame Detection** - Identifies GDL-90 wrapped messages using 0x7E flag bytes
- **KISS Deframing** - Removes HDLC byte stuffing (0x7D escape sequences)
- **Message Extraction** - Extracts 14-byte ADS-B payloads from GDL-90 frames
- **Automatic Processing** - Seamlessly handles both raw and GDL-90 wrapped data

## Architecture

The application consists of several modular components:

### Core Components
- [`main.py`](main.py) - Main application entry point with triple-protocol support
- [`udp_listener.py`](udp_listener.py) - UDP socket handling and data reception
- [`serial_listener.py`](serial_listener.py) - Serial port communication for Novatel GNSS
- [`nmea_parser.py`](nmea_parser.py) - NMEA 0183 sentence parsing and validation
- [`adsb_parser.py`](adsb_parser.py) - ADS-B message parsing with GDL-90 integration
- [`novatel_parser.py`](novatel_parser.py) - Novatel GNSS message parsing (ASCII & Binary)
- [`gdl90_deframer.py`](gdl90_deframer.py) - GDL-90/KISS deframing for ADS-B extraction
- [`navigation_display.py`](navigation_display.py) - Human-readable formatting and display
- [`config.py`](config.py) - Configuration settings and protocol modes

### Testing & Diagnostics
- [`run_tests.py`](run_tests.py) - Comprehensive test runner
- [`network_diagnostic.py`](network_diagnostic.py) - Network connectivity diagnostics
- [`test_udp_sender.py`](test_udp_sender.py) - NMEA test data sender
- [`test_adsb_sender.py`](test_adsb_sender.py) - ADS-B test data sender
- [`test_novatel_serial.py`](test_novatel_serial.py) - Novatel serial interface test suite
- [`tests/`](tests/) - Complete pytest-based test suite

## Network & Serial Setup

### For Network UDP Mode:
1. Connect to the network providing navigation data
2. Ensure your device can receive UDP broadcasts on port 4001
3. Run the application - it will automatically listen for navigation data

### For Novatel ProPak6 GNSS Receiver (Serial Mode):
1. Connect Novatel receiver to your computer via RS-232/RS-422 cable
2. Identify the correct serial port:
   ```bash
   python main.py --list-ports
   ```
3. Start the application with serial parameters:
   ```bash
   python main.py --novatel -s /dev/ttyUSB0 -b 115200
   ```

### Common Novatel ProPak6 Serial Configurations:
- **Standard GPS**: `/dev/ttyUSB0` at 9600 baud
- **High-precision GNSS**: `/dev/ttyUSB0` at 115200 baud
- **Windows**: `COM1`, `COM2`, etc. at various baud rates
- **INS Integration**: Usually 115200 or 230400 baud for high-rate data
- **ProPak6 Default**: 115200 baud with 8N1 (8 data bits, no parity, 1 stop bit)

### For Testing:
You can test the application by sending NMEA sentences via UDP:

```bash
# Example using netcat (Linux/Mac)
echo '$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47' | nc -u localhost 4001

# Example using PowerShell (Windows)
$udpClient = New-Object System.Net.Sockets.UdpClient
$udpClient.Connect("localhost", 4001)
$data = [System.Text.Encoding]::ASCII.GetBytes('$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47')
$udpClient.Send($data, $data.Length)
$udpClient.Close()
```

## Troubleshooting

### Common Issues

1. **"Permission denied" on port binding (UDP)**
   - Try running with administrator/sudo privileges
   - Use a port number > 1024 (e.g., 4001 instead of 401)

2. **"Permission denied" on serial port (Novatel)**
   - Add user to dialout group: `sudo usermod -a -G dialout $USER`
   - Try running with sudo privileges
   - Check port permissions: `ls -l /dev/ttyUSB*`

3. **No data received**
   - **UDP**: Verify the data source is broadcasting on the expected port
   - **Serial**: Check cable connections and port configuration
   - Check firewall settings
   - Ensure you're connected to the correct network
   - Try verbose mode (`-v`) to see if any data is being received

4. **Serial port not found**
   - List available ports: `python main.py --list-ports`
   - Check if device is connected: `dmesg | grep ttyUSB`
   - Try different USB port or cable

5. **Parse errors**
   - Enable verbose logging to see raw sentences/messages
   - Check if the data format matches expected standard
   - Verify checksum validation
   - For Novatel: Check baud rate and port settings

6. **High CPU usage**
   - Increase `UPDATE_INTERVAL` in config.py
   - Disable screen clearing with `--no-clear`

### Debug Mode
Run with verbose logging to see detailed information:
```bash
python main.py -v
```

## Dependencies

- **pynmea2**: Professional NMEA 0183 parsing library (for NMEA mode)
- **pyModeS**: ADS-B message decoding library (for ADS-B mode)
- **pyserial**: Serial port communication library (for Novatel mode)
- **pytest**: Testing framework (for running test suite)
- **Python 3.6+**: Required for modern Python features

Install all dependencies:
```bash
pip install -r requirements.txt
```

### Optional Dependencies
- **pyserial**: Required only for Novatel serial interface support
- **pyModeS**: Required only for ADS-B message parsing

## License

This project is provided as-is for educational and research purposes related to aviation navigation data processing.

## Safety Notice

This tool is intended for monitoring and analysis purposes only. Do not rely on this data for actual navigation or flight operations. Always use certified aviation navigation equipment for flight safety.