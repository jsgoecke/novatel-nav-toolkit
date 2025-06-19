# Novatel ProPak6 Navigation Data Toolkit - Troubleshooting Guide

## Problem: Application shows "No GPS fix" and 0 sentences/messages parsed

This guide will help you diagnose why the navigation/aviation listener isn't receiving or parsing data.

## Supported Protocols

The application now supports two protocols:
- **NMEA 0183**: Maritime navigation data (GPS coordinates, speed, heading)
- **ADS-B**: Aviation data (aircraft position, altitude, speed, callsign)

## Protocol Selection

Choose the appropriate protocol mode:

```bash
# For NMEA navigation data (default)
python main.py --nmea

# For ADS-B aviation data
python main.py --adsb

# Auto-detect protocol
python main.py --auto
```

## Step 1: Run Network Diagnostics

First, check if there are any network-level issues:

```bash
python network_diagnostic.py
```

This will:
- Check if port 4001 is available for binding
- Show your network interfaces and IP addresses
- Check if any other processes are using port 4001
- Test UDP loopback communication

**Expected Output:**
```
✓ Port 4001 is available for binding
✓ UDP loopback is working on port 4001
```

**If you see errors:**
- Port already in use: Try a different port with `python main.py -p 4002`
- Network issues: Check firewall settings or network configuration

## Step 2: Run the Navigation Listener with Full Logging

Start the main application with comprehensive logging enabled:

```bash
python main.py -v
```

**What to look for in the output:**

### 2.1 Startup Messages
You should see:
```
[MAIN] Creating UDP listener...
[MAIN] Starting UDP listener...
[UDP] Starting listen loop on 0.0.0.0:4001
[UDP] Socket timeout: 5.0s, Buffer size: 1024
[MAIN] UDP listener started successfully
```

### 2.2 Waiting for Data
If no data is being received, you'll see:
```
[UDP] No data received yet (timeout after 5.0s)
[UDP] Still listening... Packets received so far: 0
```

This indicates the UDP listener is working but no data is being sent to port 4001.

### 2.3 Data Reception (if working)
When data is received, you should see:
```
[UDP] Received 67 bytes from ('192.168.1.100', 12345)
[UDP] Decoded message length: 67 chars
[UDP] Message preview: '$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47'
[MAIN] Received UDP data callback with 67 characters
[MAIN] Split into 1 sentences
[MAIN] Processing sentence 1/1: '$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47'
[NMEA] Attempting to parse: '$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47'
[NMEA] Successfully parsed sentence type: GGA
[NMEA] Extracted navigation data: {'latitude': 48.1173, 'longitude': 1.51667, ...}
```

## Step 3: Test with Simulated Data

If no real data is being received, test with simulated NMEA data:

### 3.1 In one terminal, start the listener:
```bash
python main.py -v
```

### 3.2 In another terminal, run the appropriate test sender:

For NMEA testing:
```bash
python test_udp_sender.py
```

For ADS-B testing:
```bash
python test_adsb_sender.py
```

**Expected behavior:**
- The test sender should show: `Sent #1: $GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47`
- The listener should show all the logging messages from Step 2.3
- The display should show actual GPS coordinates instead of "No GPS fix"

## Step 4: Diagnose Specific Issues

### Issue: UDP listener starts but no packets received
**Symptoms:**
```
[UDP] No data received yet (timeout after 5.0s)
[UDP] Still listening... Packets received so far: 0
```

**Possible causes:**
1. **No data source**: Nothing is sending NMEA data to port 4001
2. **Wrong port**: Data is being sent to a different port
3. **Firewall blocking**: Windows Firewall or antivirus blocking UDP traffic
4. **Network interface**: Data being sent to wrong IP address

**Solutions:**
1. Verify your GPS/navigation device is configured to send UDP data to your computer's IP on port 4001
2. Check device documentation for UDP output settings
3. Temporarily disable Windows Firewall to test
4. Use `ipconfig` to verify your computer's IP address

### Issue: Packets received but parsing fails
**Symptoms:**
```
[UDP] Received 50 bytes from ('192.168.1.100', 12345)
[NMEA] Parse error for '$INVALID_SENTENCE': ...
```

**Possible causes:**
1. **Invalid NMEA format**: Data isn't proper NMEA 0183 sentences
2. **Corrupted data**: Network issues causing data corruption
3. **Wrong protocol**: Device sending different protocol (not NMEA)

**Solutions:**
1. Check the raw data being received (shown in logs)
2. Verify device is set to NMEA 0183 output mode
3. Check for line ending issues (should be \r\n or \n)

### Issue: Parsing succeeds but no navigation data extracted
**Symptoms:**
```
[NMEA] Successfully parsed sentence type: XXX
[NMEA] No navigation data extracted from sentence type: XXX
```

**Possible causes:**
1. **Unsupported sentence type**: Receiving NMEA sentences not handled by the parser
2. **Empty fields**: NMEA sentences have valid format but no actual GPS data

**Solutions:**
1. Check what sentence types you're receiving (GSA, GSV, etc.)
2. Ensure GPS has a fix before expecting position data
3. Wait for GGA, RMC, VTG, or GLL sentences which contain position/navigation data

## Step 5: Common Configuration Issues

### Wrong IP Address
If your GPS device is on a different network segment:
```bash
# Check your network configuration
ipconfig  # Windows
ifconfig  # Linux/Mac

# The device should send data to one of your IP addresses
```

### Wrong Port
If your device sends to a different port:
```bash
python main.py -p 4002  # Use different port
```

### Firewall Issues
Windows may block UDP traffic. Test by:
1. Temporarily disabling Windows Firewall
2. Adding an exception for Python or the specific port
3. Running as Administrator

## Step 6: Advanced Debugging

### Monitor Network Traffic
Use Wireshark or similar to monitor UDP traffic on port 4001:
1. Install Wireshark
2. Capture on your network interface
3. Filter by `udp.port == 4001`
4. Check if packets are arriving

### Check Device Configuration
Common GPS/navigation device settings:
- **Output Protocol**: NMEA 0183
- **Output Rate**: 1-10 Hz
- **UDP Target IP**: Your computer's IP address
- **UDP Target Port**: 4001
- **Sentence Types**: Enable GGA, RMC, VTG, GLL

## Expected Working Output

### NMEA Mode Output
When NMEA navigation data is working correctly:

```
==================================================
    Novatel ProPak6 Navigation Data (NMEA)
==================================================
Timestamp: 2025-06-16 21:12:52 UTC

Position:  48.117300°N, 1.516670°E
Altitude:  545 ft (166 m)
Speed:     22.4 knots (41.5 km/h)
Heading:   084° (East)
GPS:       GPS Fix (8 satellites)

------------------------------
Statistics:
  NMEA sentences parsed: 15
  Parse errors: 0
  Success rate: 100.0%
  UDP Listener: Active
==================================================
```

### ADS-B Mode Output
When ADS-B aviation data is working correctly:

```
==================================================
    Novatel ProPak6 Aviation Data (ADS-B)
==================================================
Timestamp: 2025-06-16 21:12:52 UTC

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
  ADS-B messages parsed: 25
  Aircraft tracked: 3
  Parse errors: 0
  Success rate: 100.0%
  UDP Listener: Active
==================================================
```

## Getting Help

If you're still having issues:

1. **Save the full log output** from running `python main.py -v`
2. **Run the network diagnostic** and save its output
3. **Check your GPS device manual** for UDP output configuration
4. **Verify network connectivity** between your device and computer

The comprehensive logging should help identify exactly where the data flow is breaking down.