#!/usr/bin/env python3
"""
JSON Event Logger for Navigation Data Toolkit

Provides JSON event streaming functionality for all successfully parsed
navigation data (NMEA, ADS-B, NovAtel) to json_events.log file.
"""

import json
import threading
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Union
from pathlib import Path
import uuid
import time
import config
from logger import logger


class JSONEventLogger:
    """
    Logger for streaming navigation events to JSON format.
    
    Handles all successfully parsed navigation data from NMEA, ADS-B, and NovAtel
    parsers and writes them to json_events.log file in JSON Lines format.
    """
    
    def __init__(self, log_file: str = "logs/json_events.log"):
        """
        Initialize JSON event logger.
        
        Args:
            log_file: Path to the JSON events log file
        """
        self.log_file = Path(log_file)
        self.enabled = getattr(config, 'ENABLE_JSON_EVENT_LOGGING', False)
        self.write_lock = threading.Lock()
        self.events_logged = 0
        self.write_errors = 0
        
        if self.enabled:
            self._ensure_log_directory()
            logger.info(f"[JSON] JSON event logging enabled: {self.log_file}")
        else:
            logger.debug("[JSON] JSON event logging disabled")
    
    def _ensure_log_directory(self):
        """Ensure the log directory exists."""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"[JSON] Failed to create log directory: {e}")
            self.enabled = False
    
    def log_navigation_event(self, data: Dict[str, Any], source: str):
        """
        Log a navigation event to JSON format.
        
        Args:
            data: Parsed navigation data dictionary
            source: Data source ("NMEA", "ADS-B", "NovAtel")
        """
        if not self.enabled or not data:
            return
        
        try:
            # Create event record
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": source,
                "data": data
            }
            
            # Write to file (thread-safe)
            self._write_event(event)
            self.events_logged += 1
            
        except Exception as e:
            self.write_errors += 1
            logger.error(f"[JSON] Failed to log navigation event: {e}")
    
    def log_adsb_event(self, data: Dict[str, Any]):
        """
        Log an ADS-B navigation event.
        
        Args:
            data: Parsed ADS-B data dictionary
        """
        self.log_navigation_event(data, "ADS-B")
    
    def log_nmea_event(self, data: Dict[str, Any]):
        """
        Log an NMEA navigation event.
        
        Args:
            data: Parsed NMEA data dictionary
        """
        self.log_navigation_event(data, "NMEA")
    
    def log_novatel_event(self, data: Dict[str, Any]):
        """
        Log a NovAtel navigation event.
        
        Args:
            data: Parsed NovAtel data dictionary
        """
        self.log_navigation_event(data, "NovAtel")
    
    def _write_event(self, event: Dict[str, Any]):
        """
        Write an event to the JSON log file.
        
        Args:
            event: Event dictionary to write
        """
        with self.write_lock:
            try:
                # Convert to JSON string
                json_line = json.dumps(event, default=str, separators=(',', ':'))
                
                # Write to file (append mode)
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json_line + '\n')
                    
            except Exception as e:
                logger.error(f"[JSON] Failed to write event to file: {e}")
                raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get JSON logger statistics."""
        return {
            'json_logging_enabled': self.enabled,
            'json_events_logged': self.events_logged,
            'json_write_errors': self.write_errors,
            'json_log_file': str(self.log_file) if self.enabled else None
        }
    
    def reset_stats(self):
        """Reset logger statistics."""
        self.events_logged = 0
        self.write_errors = 0
    
    def enable(self):
        """Enable JSON logging."""
        self.enabled = True
        self._ensure_log_directory()
        logger.info(f"[JSON] JSON event logging enabled: {self.log_file}")
    
    def disable(self):
        """Disable JSON logging."""
        self.enabled = False
        logger.info("[JSON] JSON event logging disabled")
    
    def is_enabled(self) -> bool:
        """Check if JSON logging is enabled."""
        return self.enabled


class ComprehensiveJSONLogger:
    """
    Comprehensive logger for all decoded navigation messages with rich metadata.
    
    Provides detailed JSON logging with GPS timestamps, signal quality metrics,
    parsing performance data, and raw message data for analysis purposes.
    """
    
    def __init__(self, log_file: str = None):
        """
        Initialize comprehensive JSON logger.
        
        Args:
            log_file: Path to the comprehensive JSON log file
        """
        self.log_file = Path(log_file or getattr(config, 'COMPREHENSIVE_JSON_LOG_FILE', 'logs/decoded_messages.log'))
        self.enabled = getattr(config, 'ENABLE_COMPREHENSIVE_JSON_LOGGING', False)
        self.write_lock = threading.Lock()
        self.messages_logged = 0
        self.write_errors = 0
        
        # Configuration flags
        self.include_raw_data = getattr(config, 'INCLUDE_RAW_MESSAGE_DATA', True)
        self.include_parsing_metadata = getattr(config, 'INCLUDE_PARSING_METADATA', True)
        self.include_gps_metadata = getattr(config, 'INCLUDE_GPS_METADATA', True)
        self.include_signal_quality = getattr(config, 'INCLUDE_SIGNAL_QUALITY', True)
        self.include_performance_metrics = getattr(config, 'INCLUDE_PERFORMANCE_METRICS', True)
        
        if self.enabled:
            self._ensure_log_directory()
            logger.info(f"[COMPREHENSIVE] Comprehensive JSON logging enabled: {self.log_file}")
        else:
            logger.debug("[COMPREHENSIVE] Comprehensive JSON logging disabled")
    
    def _ensure_log_directory(self):
        """Ensure the log directory exists."""
        try:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"[COMPREHENSIVE] Failed to create log directory: {e}")
            self.enabled = False
    
    def log_decoded_message(self,
                          data: Dict[str, Any],
                          source: str,
                          parser_name: str = None,
                          raw_data: Union[bytes, str] = None,
                          parsing_start_time: float = None,
                          parsing_errors: list = None):
        """
        Log a comprehensive decoded message with rich metadata.
        
        Args:
            data: Parsed message data dictionary
            source: Data source ("NMEA", "ADS-B", "NovAtel", "PASSCOM")
            parser_name: Name of the parser used
            raw_data: Raw message data (bytes or hex string)
            parsing_start_time: Start time for parsing performance measurement
            parsing_errors: List of parsing errors/warnings
        """
        if not self.enabled or not data:
            return
        
        parse_end_time = time.time()
        
        try:
            # Create comprehensive event record
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "message_id": str(uuid.uuid4()),
                "source": source,
                "parser": parser_name or f"{source}Parser",
                "decoded_data": data
            }
            
            # Add raw data if enabled and available
            if self.include_raw_data and raw_data:
                event["raw_data"] = self._format_raw_data(raw_data)
            
            # Add parsing metadata if enabled
            if self.include_parsing_metadata:
                event["metadata"] = self._extract_parsing_metadata(data, parsing_errors)
            
            # Add GPS metadata if enabled
            if self.include_gps_metadata:
                event["gps_metadata"] = self._extract_gps_metadata(data)
            
            # Add signal quality if enabled
            if self.include_signal_quality:
                event["signal_quality"] = self._extract_signal_quality(data)
            
            # Add performance metrics if enabled
            if self.include_performance_metrics and parsing_start_time:
                event["performance"] = {
                    "parsing_duration_ms": round((parse_end_time - parsing_start_time) * 1000, 3),
                    "parsing_success": len(parsing_errors or []) == 0,
                    "error_count": len(parsing_errors or [])
                }
            
            # Write to file (thread-safe)
            self._write_event(event)
            self.messages_logged += 1
            
        except Exception as e:
            self.write_errors += 1
            logger.error(f"[COMPREHENSIVE] Failed to log decoded message: {e}")
    
    def _format_raw_data(self, raw_data: Union[bytes, str]) -> Dict[str, Any]:
        """Format raw data for JSON logging."""
        if isinstance(raw_data, bytes):
            return {
                "hex": raw_data.hex().upper(),
                "bytes_length": len(raw_data),
                "encoding": "hex"
            }
        elif isinstance(raw_data, str):
            return {
                "data": raw_data,
                "length": len(raw_data),
                "encoding": "string"
            }
        else:
            return {
                "data": str(raw_data),
                "encoding": "string"
            }
    
    def _extract_parsing_metadata(self, data: Dict[str, Any], parsing_errors: list = None) -> Dict[str, Any]:
        """Extract parsing metadata from decoded data."""
        metadata = {
            "validation_errors": parsing_errors or [],
            "parsing_success": len(parsing_errors or []) == 0
        }
        
        # Add message type if available
        if 'type_code' in data:
            metadata['message_type'] = f"adsb_type_{data['type_code']}"
        elif 'sentence_type' in data:
            metadata['message_type'] = f"nmea_{data['sentence_type']}"
        elif 'message_type' in data:
            metadata['message_type'] = f"novatel_{data['message_type']}"
        
        return metadata
    
    def _extract_gps_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract GPS timing metadata from decoded data."""
        gps_metadata = {}
        
        # GPS week and time (from NovAtel)
        if 'gps_week' in data:
            gps_metadata['gps_week'] = data['gps_week']
        if 'gps_time' in data:
            gps_metadata['gps_time'] = data['gps_time']
            
        # Original timestamps
        if 'parsed_timestamp' in data:
            gps_metadata['parsed_timestamp'] = data['parsed_timestamp'].isoformat() if hasattr(data['parsed_timestamp'], 'isoformat') else str(data['parsed_timestamp'])
        if 'time' in data:
            gps_metadata['original_timestamp'] = str(data['time'])
        if 'date' in data:
            gps_metadata['original_date'] = str(data['date'])
            
        return gps_metadata
    
    def _extract_signal_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract signal quality metrics from decoded data."""
        quality = {}
        
        # Position accuracy
        if 'position_accuracy_m' in data:
            quality['position_accuracy_m'] = data['position_accuracy_m']
        if 'lat_stddev' in data:
            quality['latitude_stddev_m'] = data['lat_stddev']
        if 'lon_stddev' in data:
            quality['longitude_stddev_m'] = data['lon_stddev']
        if 'hgt_stddev' in data:
            quality['height_stddev_m'] = data['hgt_stddev']
            
        # Dilution of precision
        if 'pdop' in data:
            quality['pdop'] = data['pdop']
        if 'hdop' in data:
            quality['hdop'] = data['hdop']
        if 'htdop' in data:
            quality['htdop'] = data['htdop']
            
        # Satellite information
        if 'num_svs' in data:
            quality['num_satellites'] = data['num_svs']
        elif 'satellites' in data:
            quality['num_satellites'] = data['satellites']
            
        # Solution status
        if 'solution_status' in data:
            quality['solution_status'] = data['solution_status']
        if 'position_type' in data:
            quality['position_type'] = data['position_type']
            
        # Fix quality (NMEA)
        if 'fix_quality' in data:
            quality['fix_quality'] = data['fix_quality']
        if 'status' in data:
            quality['status'] = data['status']
            
        return quality
    
    def _write_event(self, event: Dict[str, Any]):
        """
        Write an event to the comprehensive JSON log file.
        
        Args:
            event: Event dictionary to write
        """
        with self.write_lock:
            try:
                # Convert to JSON string
                json_line = json.dumps(event, default=str, separators=(',', ':'))
                
                # Write to file (append mode)
                with open(self.log_file, 'a', encoding='utf-8') as f:
                    f.write(json_line + '\n')
                    
            except Exception as e:
                logger.error(f"[COMPREHENSIVE] Failed to write event to file: {e}")
                raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive logger statistics."""
        return {
            'comprehensive_logging_enabled': self.enabled,
            'comprehensive_messages_logged': self.messages_logged,
            'comprehensive_write_errors': self.write_errors,
            'comprehensive_log_file': str(self.log_file) if self.enabled else None,
            'include_raw_data': self.include_raw_data,
            'include_parsing_metadata': self.include_parsing_metadata,
            'include_gps_metadata': self.include_gps_metadata,
            'include_signal_quality': self.include_signal_quality,
            'include_performance_metrics': self.include_performance_metrics
        }
    
    def reset_stats(self):
        """Reset logger statistics."""
        self.messages_logged = 0
        self.write_errors = 0
    
    def enable(self):
        """Enable comprehensive JSON logging."""
        self.enabled = True
        self._ensure_log_directory()
        logger.info(f"[COMPREHENSIVE] Comprehensive JSON logging enabled: {self.log_file}")
    
    def disable(self):
        """Disable comprehensive JSON logging."""
        self.enabled = False
        logger.info("[COMPREHENSIVE] Comprehensive JSON logging disabled")
    
    def is_enabled(self) -> bool:
        """Check if comprehensive JSON logging is enabled."""
        return self.enabled


# Global instances for use throughout the application
json_event_logger = JSONEventLogger()
comprehensive_json_logger = ComprehensiveJSONLogger()


if __name__ == "__main__":
    # Test both JSON event loggers
    import tempfile
    import os
    
    # Create temporary log files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        temp_basic_log = f.name
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        temp_comprehensive_log = f.name
    
    try:
        print("=== Testing JSON Event Loggers ===\n")
        
        # Test basic logger
        print("1. Testing Basic JSON Event Logger:")
        basic_logger = JSONEventLogger(temp_basic_log)
        basic_logger.enable()
        
        # Test NMEA event
        nmea_data = {
            'latitude': 21.3099,
            'longitude': -157.8581,
            'altitude_m': 123.4,
            'parsed_timestamp': datetime.now(timezone.utc),
            'sentence_type': 'GGA',
            'satellites': 8,
            'hdop': 1.2
        }
        basic_logger.log_nmea_event(nmea_data)
        
        # Test ADS-B event
        adsb_data = {
            'icao': 'A1B2C3',
            'altitude_baro_ft': 35000,
            'latitude': 21.3099,
            'longitude': -157.8581,
            'type_code': 11,
            'parsed_timestamp': datetime.now(timezone.utc)
        }
        basic_logger.log_adsb_event(adsb_data)
        
        # Test NovAtel event
        novatel_data = {
            'latitude': 21.3099,
            'longitude': -157.8581,
            'height': 123.4,
            'solution_status': 'SOL_COMPUTED',
            'message_type': 'BESTPOS',
            'parsed_timestamp': datetime.now(timezone.utc),
            'gps_week': 2264,
            'gps_time': 345678.123,
            'pdop': 1.8,
            'hdop': 1.2,
            'num_svs': 12
        }
        basic_logger.log_novatel_event(novatel_data)
        
        basic_stats = basic_logger.get_stats()
        print("  Basic Logger Stats:")
        for key, value in basic_stats.items():
            print(f"    {key}: {value}")
        
        # Test comprehensive logger
        print("\n2. Testing Comprehensive JSON Logger:")
        comprehensive_logger = ComprehensiveJSONLogger(temp_comprehensive_log)
        comprehensive_logger.enable()
        
        # Test comprehensive logging with rich metadata
        parse_start = time.time()
        time.sleep(0.001)  # Simulate parsing time
        
        comprehensive_logger.log_decoded_message(
            data=nmea_data,
            source="NMEA",
            parser_name="NMEAParser",
            raw_data="$GPGGA,123456.00,2118.5940,N,15748.4860,W,1,08,1.2,123.4,M,0.0,M,,*XX",
            parsing_start_time=parse_start
        )
        
        comprehensive_logger.log_decoded_message(
            data=adsb_data,
            source="ADS-B",
            parser_name="ADSBParser",
            raw_data=bytes.fromhex("8DA1B2C3202CC371C32CE0576098"),
            parsing_start_time=parse_start
        )
        
        comprehensive_logger.log_decoded_message(
            data=novatel_data,
            source="NovAtel",
            parser_name="NovatelParser",
            raw_data=b"#BESTPOSA,COM1,0,83.5,FINESTEERING,2264,345678.123,02000020,bdba,16248;SOL_COMPUTED,SINGLE,21.30990000,-157.85810000,123.4000,0.0000,WGS84,1.2000,1.8000,12,12,0,0,0,06,0,0*12345678",
            parsing_start_time=parse_start,
            parsing_errors=[]
        )
        
        comprehensive_stats = comprehensive_logger.get_stats()
        print("  Comprehensive Logger Stats:")
        for key, value in comprehensive_stats.items():
            print(f"    {key}: {value}")
        
        # Show sample log contents
        print("\n3. Sample Log Contents:")
        print("  Basic Log Sample:")
        with open(temp_basic_log, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:2], 1):
                print(f"    Event {i}: {line.strip()[:100]}...")
        
        print("  Comprehensive Log Sample:")
        with open(temp_comprehensive_log, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines[:1], 1):
                # Pretty print first comprehensive log entry
                event = json.loads(line.strip())
                print(f"    Event {i} keys: {list(event.keys())}")
                if 'performance' in event:
                    print(f"      Parsing time: {event['performance']['parsing_duration_ms']}ms")
                if 'gps_metadata' in event:
                    print(f"      GPS metadata keys: {list(event['gps_metadata'].keys())}")
                if 'signal_quality' in event:
                    print(f"      Signal quality keys: {list(event['signal_quality'].keys())}")
        
        print("\n✓ Both JSON loggers tested successfully")
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        for temp_file in [temp_basic_log, temp_comprehensive_log]:
            if os.path.exists(temp_file):
                os.unlink(temp_file)