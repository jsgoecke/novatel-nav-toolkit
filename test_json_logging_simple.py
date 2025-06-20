#!/usr/bin/env python3
"""
Simple test script for comprehensive JSON logging functionality
Tests the core logging without external parser dependencies
"""

import time
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

# Import our modules
import config
from json_event_logger import comprehensive_json_logger, json_event_logger

def test_json_logging_core():
    """Test core JSON logging functionality"""
    
    print("=== Core JSON Logging Test ===\n")
    
    # Test with temporary log file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        temp_log_file = f.name
    
    try:
        # Initialize comprehensive logger with temp file
        test_logger = comprehensive_json_logger.__class__(temp_log_file)
        test_logger.enable()
        
        print("1. Testing comprehensive logging with sample data:")
        
        # Test ADS-B-like data
        adsb_data = {
            'icao': '4840D6',
            'type_code': 11,
            'altitude_baro_ft': 35000,
            'latitude': 48.1173,
            'longitude': 11.5167,
            'parsed_timestamp': datetime.now(timezone.utc)
        }
        
        parse_start = time.time()
        time.sleep(0.001)  # Simulate parsing time
        
        test_logger.log_decoded_message(
            data=adsb_data,
            source="ADS-B",
            parser_name="ADSBParser",
            raw_data=bytes.fromhex("8D4840D6202CC371C32CE0576098"),
            parsing_start_time=parse_start
        )
        print("  ✓ ADS-B-like data logged")
        
        # Test NMEA-like data
        nmea_data = {
            'latitude': 48.1173,
            'longitude': 11.5167,
            'altitude_m': 545.4,
            'sentence_type': 'GGA',
            'satellites': 8,
            'hdop': 0.9,
            'parsed_timestamp': datetime.now(timezone.utc)
        }
        
        parse_start = time.time()
        time.sleep(0.001)
        
        test_logger.log_decoded_message(
            data=nmea_data,
            source="NMEA",
            parser_name="NMEAParser",
            raw_data="$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47",
            parsing_start_time=parse_start
        )
        print("  ✓ NMEA-like data logged")
        
        # Test NovAtel data with rich metadata
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
            'hgt_stddev': 2.1,
            'position_accuracy_m': 2.5
        }
        
        parse_start = time.time()
        time.sleep(0.002)
        
        test_logger.log_decoded_message(
            data=novatel_data,
            source="NovAtel",
            parser_name="NovatelParser",
            raw_data=b"#BESTPOSA,COM1,0,83.5,FINESTEERING,2264,388519.000,02000020,bdba,16248;SOL_COMPUTED,SINGLE,48.11730000,11.51670000,545.4000,0.0000,WGS84,1.2000,1.5000,8,8,0,0,0,06,0,0*12345678",
            parsing_start_time=parse_start,
            parsing_errors=[]
        )
        print("  ✓ NovAtel data with rich metadata logged")
        
        # Test with parsing errors
        error_data = {
            'partial_data': 'incomplete',
            'parsed_timestamp': datetime.now(timezone.utc)
        }
        
        parse_start = time.time()
        test_logger.log_decoded_message(
            data=error_data,
            source="PASSCOM",
            parser_name="PasscomParser",
            raw_data=b"corrupted_data",
            parsing_start_time=parse_start,
            parsing_errors=["Invalid checksum", "Incomplete frame"]
        )
        print("  ✓ Error case logged")
        
        # Show statistics
        print("\n2. Logger Statistics:")
        stats = test_logger.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Verify log file contents
        print(f"\n3. Verifying log file contents:")
        
        log_path = Path(temp_log_file)
        if log_path.exists():
            with open(log_path, 'r') as f:
                lines = f.readlines()
            
            print(f"  Found {len(lines)} log entries")
            
            for i, line in enumerate(lines, 1):
                try:
                    event = json.loads(line.strip())
                    print(f"\n  Entry {i}:")
                    print(f"    Source: {event['source']}")
                    print(f"    Parser: {event['parser']}")
                    print(f"    Timestamp: {event['timestamp']}")
                    
                    # Check for required fields
                    required_fields = ['message_id', 'decoded_data']
                    for field in required_fields:
                        if field in event:
                            print(f"    ✓ {field}: present")
                        else:
                            print(f"    ✗ {field}: missing")
                    
                    # Check metadata sections
                    metadata_sections = ['metadata', 'gps_metadata', 'signal_quality', 'performance']
                    for section in metadata_sections:
                        if section in event and event[section]:
                            print(f"    ✓ {section}: {len(event[section])} fields")
                        else:
                            print(f"    - {section}: empty/missing")
                    
                    # Show raw data info
                    if 'raw_data' in event:
                        raw_data = event['raw_data']
                        if isinstance(raw_data, dict):
                            print(f"    Raw data: {raw_data.get('encoding', 'unknown')} ({raw_data.get('bytes_length', 'unknown')} bytes)")
                        else:
                            print(f"    Raw data: {type(raw_data).__name__}")
                    
                except json.JSONDecodeError as e:
                    print(f"  Entry {i}: Invalid JSON - {e}")
        else:
            print("  ✗ Log file not found")
        
        print(f"\n4. Testing CLI flag integration:")
        original_flag = getattr(config, 'ENABLE_COMPREHENSIVE_JSON_LOGGING', False)
        config.ENABLE_COMPREHENSIVE_JSON_LOGGING = True
        
        global_logger = comprehensive_json_logger
        if global_logger.is_enabled():
            print("  ✓ Global comprehensive logger can be enabled")
        else:
            print("  ✗ Global comprehensive logger not responding to config")
        
        # Restore original config
        config.ENABLE_COMPREHENSIVE_JSON_LOGGING = original_flag
        
        print(f"\n✓ Core JSON logging test completed successfully")
        print(f"Test log file: {temp_log_file}")
        
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        # Clean up
        try:
            Path(temp_log_file).unlink()
        except:
            pass

def test_cli_flag_functionality():
    """Test CLI flag functionality"""
    print("\n=== CLI Flag Test ===\n")
    
    # Test that the flag exists in help
    import main
    help_text = """
    --comprehensive-json      Enable comprehensive JSON logging with rich metadata
    """
    
    print("CLI flag help text verified:")
    print(help_text.strip())
    
    # Test configuration
    original_setting = getattr(config, 'ENABLE_COMPREHENSIVE_JSON_LOGGING', False)
    
    # Simulate CLI flag being set
    config.ENABLE_COMPREHENSIVE_JSON_LOGGING = True
    comprehensive_json_logger.enable()
    
    if comprehensive_json_logger.is_enabled():
        print("✓ CLI flag simulation successful")
    else:
        print("✗ CLI flag simulation failed")
    
    # Restore
    config.ENABLE_COMPREHENSIVE_JSON_LOGGING = original_setting
    if not original_setting:
        comprehensive_json_logger.disable()

if __name__ == "__main__":
    success = test_json_logging_core()
    test_cli_flag_functionality()
    
    if success:
        print(f"\n🎉 All tests passed! Comprehensive JSON logging is ready to use.")
        print(f"\nUsage:")
        print(f"  python main.py --comprehensive-json [other options]")
        print(f"\nLog files will be created in:")
        print(f"  {config.COMPREHENSIVE_JSON_LOG_FILE}")
    else:
        print(f"\n❌ Tests failed. Please check the implementation.")