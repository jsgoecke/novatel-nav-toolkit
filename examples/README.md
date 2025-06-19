# ADS-B Message Parser Example

This directory contains a standalone script for parsing ADS-B (Automatic Dependent Surveillance-Broadcast) messages and outputting the decoded aviation data as JSON.

## Overview

The [`parse_adsb_message.py`](parse_adsb_message.py) script takes raw ADS-B messages in hexadecimal format as command line input and outputs comprehensive JSON containing:
- Input validation and preprocessing details
- Parsing statistics and success metrics
- Decoded aviation data (callsign, position, altitude, velocity, etc.)
- Error handling for invalid inputs

## Prerequisites

- Python 3.6 or higher
- Required Python packages:
  - `pyModeS` (for ADS-B message decoding)
  - `pynmea2` (dependency)

## Installation

1. Install the required dependencies:
   ```bash
   # From the project root directory
   pip install -r requirements.txt
   
   # Or install manually
   pip install pyModeS>=2.13.0 pynmea2==1.19.0
   ```

2. Make the script executable (optional):
   ```bash
   chmod +x examples/parse_adsb_message.py
   ```

## Usage

### Basic Syntax
```bash
python examples/parse_adsb_message.py <hex_message> [options]
```

### Command Line Options
- `--pretty`: Pretty-print JSON output with indentation
- `--verbose`: Enable detailed parsing logs
- `--help`: Show help message and usage examples

### Input Formats

The script accepts ADS-B messages in various hex formats:

1. **Continuous hex string** (most common):
   ```bash
   python examples/parse_adsb_message.py "8D4840D6202CC371C32CE0576098"
   ```

2. **Hex string with spaces**:
   ```bash
   python examples/parse_adsb_message.py "8D 48 40 D6 20 2C C3 71 C3 2C E0 57 60 98"
   ```

3. **Without quotes** (if no spaces):
   ```bash
   python examples/parse_adsb_message.py 8D4840D6202CC371C32CE0576098
   ```

## Examples

### Example 1: Aircraft Identification Message
```bash
python examples/parse_adsb_message.py "8D4840D6202CC371C32CE0576098" --pretty
```

**Output:**
```json
{
  "input": {
    "raw_hex": "8D4840D6202CC371C32CE0576098",
    "raw_bytes": 14,
    "original_input": "8D4840D6202CC371C32CE0576098"
  },
  "parsing": {
    "success": true,
    "parser_stats": {
      "messages_parsed": 1,
      "parse_errors": 0,
      "success_rate": 100.0,
      "aircraft_tracked": 1,
      "gdl90_messages_processed": 0,
      "raw_messages_processed": 1,
      "gdl90_frames_processed": 0,
      "gdl90_adsb_found": 0,
      "gdl90_success_rate": 0.0
    }
  },
  "parsed_data": {
    "icao": "4840d6",
    "type_code": 4,
    "parsed_timestamp": "2025-06-18T06:27:28.676530+00:00",
    "callsign": "KLM1023_",
    "category": 0
  }
}
```

### Example 2: Airborne Position Message
```bash
python examples/parse_adsb_message.py "8D4840D6580B982C8BA874F80820" --pretty
```

**Output:**
```json
{
  "input": {
    "raw_hex": "8D4840D6580B982C8BA874F80820",
    "raw_bytes": 14,
    "original_input": "8D4840D6580B982C8BA874F80820"
  },
  "parsing": {
    "success": true,
    "parser_stats": {
      "messages_parsed": 1,
      "parse_errors": 0,
      "success_rate": 100.0,
      "aircraft_tracked": 1,
      "gdl90_messages_processed": 0,
      "raw_messages_processed": 1,
      "gdl90_frames_processed": 0,
      "gdl90_adsb_found": 0,
      "gdl90_success_rate": 0.0
    }
  },
  "parsed_data": {
    "icao": "4840d6",
    "type_code": 11,
    "parsed_timestamp": "2025-06-18T06:27:37.099365+00:00",
    "altitude_ft": 1225
  }
}
```

### Example 3: Airborne Velocity Message
```bash
python examples/parse_adsb_message.py "8D4840D699133C1CF8E02102C60C" --pretty
```

**Output:**
```json
{
  "input": {
    "raw_hex": "8D4840D699133C1CF8E02102C60C",
    "raw_bytes": 14,
    "original_input": "8D4840D699133C1CF8E02102C60C"
  },
  "parsing": {
    "success": true,
    "parser_stats": {
      "messages_parsed": 1,
      "parse_errors": 0,
      "success_rate": 100.0,
      "aircraft_tracked": 1,
      "gdl90_messages_processed": 0,
      "raw_messages_processed": 1,
      "gdl90_frames_processed": 0,
      "gdl90_adsb_found": 0,
      "gdl90_success_rate": 0.0
    }
  },
  "parsed_data": {
    "icao": "4840d6",
    "type_code": 19,
    "parsed_timestamp": "2025-06-18T06:27:44.360454+00:00",
    "speed_knots": 858,
    "heading": 74.45802426838158,
    "vertical_rate": -3520
  }
}
```

### Example 4: Error Handling
```bash
python examples/parse_adsb_message.py "invalid_hex" --pretty
```

**Output:**
```json
{
  "input": {
    "original_input": "invalid_hex"
  },
  "parsing": {
    "success": false
  },
  "error": "Invalid hex string: invalid_hex"
}
```

## Output Format

### JSON Structure

The script outputs a structured JSON object with the following sections:

#### `input` Section
- `raw_hex`: Cleaned hexadecimal string (uppercase, no spaces)
- `raw_bytes`: Number of bytes in the message
- `original_input`: Original command line input as provided

#### `parsing` Section
- `success`: Boolean indicating if parsing was successful
- `parser_stats`: Detailed statistics from the ADS-B parser
  - `messages_parsed`: Number of messages successfully parsed
  - `parse_errors`: Number of parsing errors encountered
  - `success_rate`: Percentage success rate
  - `aircraft_tracked`: Number of unique aircraft tracked
  - GDL-90 related statistics (for wrapped messages)

#### `parsed_data` Section (only if successful)
Contains decoded aviation data, which may include:
- `icao`: Aircraft ICAO identifier (6-character hex string)
- `type_code`: ADS-B message type code (1-31)
- `parsed_timestamp`: ISO format timestamp when message was parsed
- `callsign`: Aircraft callsign (for identification messages)
- `category`: Aircraft category code
- `altitude_ft`: Altitude in feet (for position messages)
- `latitude`: Aircraft latitude (when position reference is available)
- `longitude`: Aircraft longitude (when position reference is available)
- `speed_knots`: Ground speed in knots (for velocity messages)
- `heading`: Aircraft heading in degrees (for velocity messages)
- `vertical_rate`: Vertical rate of climb/descent in feet per minute

#### `error` Section (only if parsing failed)
- Contains human-readable error message describing the failure

## Message Types Supported

The script can decode various ADS-B message types:

| Type Code | Description | Data Extracted |
|-----------|-------------|----------------|
| 1-4 | Aircraft Identification | Callsign, category |
| 5-8 | Surface Position | Position (requires reference) |
| 9-18 | Airborne Position | Position (requires reference), altitude |
| 19 | Airborne Velocity | Speed, heading, vertical rate |

## Advanced Usage

### Using with Shell Scripts
```bash
#!/bin/bash
# Process multiple messages
messages=(
    "8D4840D6202CC371C32CE0576098"
    "8D4840D6580B982C8BA874F80820"
    "8D4840D699133C1CF8E02102C60C"
)

for msg in "${messages[@]}"; do
    echo "Processing: $msg"
    python examples/parse_adsb_message.py "$msg" --pretty
    echo "---"
done
```

### Verbose Logging
Enable detailed parsing logs to see the internal processing steps:
```bash
python examples/parse_adsb_message.py "8D4840D6202CC371C32CE0576098" --verbose --pretty
```

### Compact Output
For programmatic use, omit the `--pretty` flag for compact JSON:
```bash
python examples/parse_adsb_message.py "8D4840D6202CC371C32CE0576098"
```

## Exit Codes

The script returns different exit codes:
- `0`: Successful parsing
- `1`: Parsing failed (invalid input or message format)

This allows for easy integration with shell scripts and automation tools.

## Troubleshooting

### Common Issues

1. **ModuleNotFoundError: No module named 'pyModeS'**
   ```bash
   pip install pyModeS>=2.13.0
   ```

2. **Invalid hex string error**
   - Ensure the message contains only valid hexadecimal characters (0-9, A-F)
   - ADS-B messages are typically 14 bytes (28 hex characters)
   - Remove any non-hex characters or separators

3. **Message parsing failed**
   - Check that the message is a valid ADS-B message (DF=17, 18, or 19)
   - Some messages may require position references for full decoding
   - Use `--verbose` flag to see detailed parsing information

### Getting Help
```bash
python examples/parse_adsb_message.py --help
```

## Integration

This script can be easily integrated into larger systems:
- **Data pipelines**: Process ADS-B messages in batch
- **Real-time systems**: Parse individual messages from live feeds
- **Analysis tools**: Convert hex messages to structured data for analysis
- **Testing**: Validate ADS-B message parsing functionality

## Notes

- Position decoding requires reference coordinates for CPR (Compact Position Reporting) messages
- Some message types may not contain all possible data fields
- The script handles both GDL-90 wrapped and raw Mode S messages
- Timestamps are in UTC format with ISO 8601 formatting