# Installation Guide - Novatel ProPak6 Navigation Data Toolkit

## Prerequisites

### 1. Install Python
- **Windows**: Download from [python.org](https://www.python.org/downloads/) or install from Microsoft Store
- **macOS**: Install via Homebrew: `brew install python3` or download from python.org
- **Linux**: Install via package manager: `sudo apt install python3 python3-pip` (Ubuntu/Debian)

### 2. Verify Python Installation
```bash
python --version
# or
python3 --version
```

Python 3.6+ is required.

## Installation Steps

### 1. Download Project Files
Ensure you have all these files in your project directory:

**Core Application:**
- `main.py` - Main application with dual-protocol support
- `udp_listener.py` - UDP socket handling
- `nmea_parser.py` - NMEA sentence parsing
- `adsb_parser.py` - ADS-B message parsing
- `gdl90_deframer.py` - GDL-90/KISS deframing
- `navigation_display.py` - Display formatting
- `config.py` - Configuration settings

**Testing & Diagnostics:**
- `network_diagnostic.py` - Network troubleshooting
- `run_tests.py` - Test runner
- `simple_test.py` - Dependency-free testing
- `test_udp_sender.py` - NMEA test data sender
- `test_adsb_sender.py` - ADS-B test data sender
- `tests/` - Complete test suite

**Documentation:**
- `requirements.txt` - Python dependencies
- `README.md` - Usage instructions
- `INSTALLATION.md` - This installation guide
- `TROUBLESHOOTING.md` - Troubleshooting guide

### 2. Install Dependencies
```bash
# Install all required Python packages
pip install -r requirements.txt

# Or if pip is not in PATH:
python -m pip install -r requirements.txt

# Or install manually:
pip install pynmea2==1.19.0 pyModeS>=2.13.0 pytest>=7.0.0
```

**Dependencies:**
- `pynmea2` - NMEA 0183 parsing (required for NMEA mode)
- `pyModeS` - ADS-B message decoding (required for ADS-B mode)
- `pytest` - Testing framework (optional, for running tests)

### 3. Test Installation
Run the simple test to verify core functionality:
```bash
python simple_test.py
```

This tests all core modules without requiring external dependencies.

For comprehensive testing (requires all dependencies):
```bash
python run_tests.py
```

This will show demonstrations with sample Novatel ProPak6 navigation and aviation data.

## Usage

### 1. Connect to Network
- Connect your device to the network providing navigation data
- Ensure you can receive UDP broadcasts on port 4001

### 2. Choose Protocol Mode

The application supports three modes:

**NMEA Mode (Navigation Data):**
```bash
python main.py --nmea
```

**ADS-B Mode (Aviation Data):**
```bash
python main.py --adsb
```

**Auto-Detect Mode (Both):**
```bash
python main.py --auto
```

### 3. Additional Options
```bash
# Custom port
python main.py --adsb -p 5000

# Verbose logging (shows raw data and parsing details)
python main.py --adsb -v

# Disable screen clearing (good for logging)
python main.py --nmea --no-clear

# Help
python main.py -h
```

### 4. Expected Output

**NMEA Navigation Mode:**
```
==================================================
     Novatel ProPak6 Navigation Data (NMEA)
==================================================
Timestamp: 2025-06-16 20:36:40 UTC

Position:  34.078403°N, 77.172339°W
Altitude:  35,000 ft (10,668 m)
Speed:     450.0 knots (833.4 km/h)
Heading:   095° (East)
GPS:       DGPS Fix (10 satellites)
Status:    Active

------------------------------
Statistics:
  NMEA sentences parsed: 1247
  Parse errors: 3
  Success rate: 99.8%
  UDP Listener: Active
==================================================
```

**ADS-B Aviation Mode:**
```
==================================================
     Novatel ProPak6 Aviation Data (ADS-B)
==================================================
Timestamp: 2025-06-16 20:36:40 UTC

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

## Troubleshooting

### Python Not Found
- **Windows**: Add Python to PATH or reinstall with "Add to PATH" option
- **macOS/Linux**: Use `python3` instead of `python`

### Permission Denied (Port Binding)
- Run with administrator/sudo privileges
- Use a port > 1024 (default 4001 should work)

### No Data Received
- Verify aircraft is broadcasting on port 4001
- Check firewall settings
- Ensure correct WiFi network connection
- Try verbose mode: `python main.py -v`

### Import Errors
**For NMEA mode:**
- Ensure pynmea2 is installed: `pip install pynmea2`

**For ADS-B mode:**
- Ensure pyModeS is installed: `pip install pyModeS`
- Note: pyModeS has additional dependencies that may require compilation

**For complete functionality:**
- Install all dependencies: `pip install -r requirements.txt`
- Check Python version (requires 3.6+)

### Protocol-Specific Issues
**If ADS-B mode fails to start:**
- Verify pyModeS installation: `python -c "import pyModeS; print('OK')"`
- Try NMEA mode first: `python main.py --nmea`

**If no ADS-B data is parsed:**
- Check if data is GDL-90 wrapped (automatic detection should handle this)
- Enable verbose logging: `python main.py --adsb -v`
- Ensure UDP data contains Mode S messages (DF=17)

## Network Configuration

### Firewall Settings
Ensure your firewall allows:
- Incoming UDP traffic on port 4001
- Python application network access

### Network Interface
The application binds to all network interfaces (0.0.0.0) by default.
To bind to a specific interface, modify `UDP_HOST` in `config.py`.

## Testing Without Aircraft

### Network Diagnostics
First, check your network setup:
```bash
python network_diagnostic.py
```

### Test with Simulated Data

**For NMEA testing:**
```bash
# Terminal 1: Start listener
python main.py --nmea -v

# Terminal 2: Send test data
python test_udp_sender.py
```

**For ADS-B testing:**
```bash
# Terminal 1: Start listener
python main.py --adsb -v

# Terminal 2: Send test data
python test_adsb_sender.py
```

### Manual Test Data
Send test data manually with netcat:

**NMEA:**
```bash
echo '$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47' | nc -u localhost 4001
```

**ADS-B (hexadecimal):**
```bash
echo -ne '\x8B\x9A\x7E\x47\x99\x67\xCC\xD9\xC8\x2B\x84\xD1\xFF\xEB\xCC\xA0' | nc -u localhost 4001
```

**Windows PowerShell (NMEA):**
```powershell
$udpClient = New-Object System.Net.Sockets.UdpClient
$udpClient.Connect("localhost", 4001)
$data = [System.Text.Encoding]::ASCII.GetBytes('$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47')
$udpClient.Send($data, $data.Length)
$udpClient.Close()
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the README.md for detailed documentation
3. Enable verbose logging: `python main.py -v`
4. Check the configuration in `config.py`