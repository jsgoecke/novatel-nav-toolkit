#!/usr/bin/env python3
"""
Test script for comprehensive JSON logging functionality
"""

import time
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Import our modules
import config
from json_event_logger import comprehensive_json_logger
from adsb_parser import ADSBParser
from nmea_parser import NMEAParser

def test_comprehensive_json_logging():
    """Test comprehensive JSON logging with all parsers"""
    
    # Enable comprehensive logging
    config.ENABLE_COMPREHENSIVE_JSON_LOGGING = True
    comprehensive_json_logger.enable()
    
    print("=== Comprehensive JSON Logging Test ===\n")
    
    # Test ADS-B parsing with comprehensive logging
    print("1. Testing ADS-B comprehensive logging:")
    adsb_parser = ADSBParser()
    
    # Sample ADS-B message (airborne position)
    adsb_hex = "8D4840D6202CC371C32CE0576098"
    adsb_bytes = bytes.fromhex(adsb_hex)
    
    parse_start = time.time()
    result = adsb_parser.parse_message(adsb_bytes)
    
    if result:
        comprehensive_json_logger.log_decoded_message(
            data=result,
            source="ADS-B",
            parser_name="ADSBParser",
            raw_data=adsb_bytes,
            parsing_start_time=parse_start
        )
        print(f"  ✓ ADS-B message logged: ICAO={result.get('icao', 'N/A')}")
    else:
        print("  ✗ ADS-B parsing failed")
    
    # Test NMEA parsing with comprehensive logging  
    print("\n2. Testing NMEA comprehensive logging:")
    nmea_parser = NMEAParser()
    
    # Sample NMEA GGA sentence
    nmea_sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
    
    parse_start = time.time()
    result = nmea_parser.parse_sentence(nmea_sentence)
    
    if result:
        comprehensive_json_logger.log_decoded_message(
            data=result,
            source="NMEA",
            parser_name="NMEAParser", 
            raw_data=nmea_sentence,
            parsing_start_time=parse_start
        )
        print(f"  ✓ NMEA message logged: Type={result.get('sentence_type', 'N/A')}")
    else:
        print("  ✗ NMEA parsing failed")
    
    # Test with rich metadata (simulated NovAtel)
    print("\n3. Testing rich metadata logging:")
    
    novatel_data = {
        'latitude': 48.1173,
        'longitude': 11.5167,
        'height': 545.4,
        'solution_status': 'SOL_COMPUTED',
        'position_type': 'SINGLE',
        'message_type': 'BESTPOS',
        'gps_week': 2264,
        'gps_time': 388519.000,
        'parsed_timestamp': datetime.now(timezone.utc),
        'num_svs': 8,
        'pdop': 1.8,
        'hdop': 0.9,
        'lat_stddev': 1.2,
        'lon_stddev': 1.5,
        'hgt_stddev': 2.1
    }
    
    parse_start = time.time()
    time.sleep(0.001)  # Simulate processing time
    
    comprehensive_json_logger.log_decoded_message(
        data=novatel_data,
        source="NovAtel",
        parser_name="NovatelParser",
        raw_data=b"#BESTPOSA,COM1,0,83.5,FINESTEERING,2264,388519.000,02000020,bdba,16248;SOL_COMPUTED,SINGLE,48.11730000,11.51670000,545.4000,0.0000,WGS84,1.2000,1.5000,8,8,0,0,0,06,0,0*12345678",
        parsing_start_time=parse_start
    )
    print(f"  ✓ NovAtel message logged with rich metadata")
    
    # Show statistics
    print("\n4. Logger Statistics:")
    stats = comprehensive_json_logger.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Read and display sample log entries
    print(f"\n5. Sample log entries from {comprehensive_json_logger.log_file}:")
    
    if comprehensive_json_logger.log_file.exists():
        with open(comprehensive_json_logger.log_file, 'r') as f:
            lines = f.readlines()
            
        for i, line in enumerate(lines[:3], 1):  # Show first 3 entries
            try:
                event = json.loads(line.strip())
                print(f"\n  Entry {i}:")
                print(f"    Source: {event['source']}")
                print(f"    Parser: {event['parser']}")
                print(f"    Message ID: {event['message_id']}")
                
                if 'performance' in event:
                    print(f"    Parse Time: {event['performance']['parsing_duration_ms']}ms")
                
                if 'gps_metadata' in event and event['gps_metadata']:
                    print(f"    GPS Metadata: {list(event['gps_metadata'].keys())}")
                
                if 'signal_quality' in event and event['signal_quality']:
                    print(f"    Signal Quality: {list(event['signal_quality'].keys())}")
                
                if 'raw_data' in event:
                    raw_preview = str(event['raw_data'])[:50] + "..." if len(str(event['raw_data'])) > 50 else str(event['raw_data'])
                    print(f"    Raw Data: {raw_preview}")
                    
            except json.JSONDecodeError:
                print(f"  Entry {i}: Invalid JSON")
    else:
        print("  No log file found")
    
    print(f"\n✓ Comprehensive JSON logging test completed")
    print(f"Log file: {comprehensive_json_logger.log_file}")

if __name__ == "__main__":
    test_comprehensive_json_logging()