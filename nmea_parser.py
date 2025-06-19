"""
NMEA 0183 Parser for Navigation Data
"""

import re
import pynmea2
from datetime import datetime, timezone
from typing import Dict, Optional, Any
import config
from logger import logger


class NMEAParser:
    """Parser for NMEA 0183 navigation sentences"""
    
    def __init__(self):
        """Initialize NMEA parser"""
        self.parse_error_count = 0
        self.sentences_parsed = 0
        self.last_valid_data = {}
        
    def parse_sentence(self, sentence: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single NMEA sentence
        
        Args:
            sentence: Raw NMEA sentence string
            
        Returns:
            Dict with parsed navigation data or None if parsing failed
        """
        try:
            sentence = sentence.strip()
            
            logger.nmea_parse(f"Attempting to parse: {repr(sentence)}")
            
            # Skip empty sentences
            if not sentence:
                logger.nmea_parse("Skipping empty sentence")
                return None
                
            # Ensure sentence starts with $
            if not sentence.startswith('$'):
                logger.nmea_parse(f"Skipping sentence - doesn't start with '$': {repr(sentence)}")
                return None
                
            # Parse using pynmea2
            if config.LOG_PARSE_ATTEMPTS:
                logger.nmea_parse("Parsing with pynmea2...")
            
            msg = pynmea2.parse(sentence)
            
            logger.nmea_parse(f"Successfully parsed sentence type: {getattr(msg, 'sentence_type', 'unknown')}")
            
            # Extract data based on sentence type
            nav_data = self._extract_navigation_data(msg)
            
            if nav_data:
                logger.nmea_parse(f"Extracted navigation data: {nav_data}")
                # Only count sentences that successfully extract data
                self.sentences_parsed += 1
                # Update last valid data
                self.last_valid_data.update(nav_data)
                return nav_data
            else:
                logger.nmea_parse(f"No navigation data extracted from sentence type: {getattr(msg, 'sentence_type', 'unknown')}")
                # Increment error count for sentences that parse but have no extractable data
                self.parse_error_count += 1
                
            return None
            
        except Exception as e:
            self.parse_error_count += 1
            logger.error(f"NMEA parse error for '{sentence}': {e}")
            return None
    
    def _extract_navigation_data(self, msg) -> Optional[Dict[str, Any]]:
        """
        Extract navigation data from parsed NMEA message
        
        Args:
            msg: Parsed pynmea2 message object
            
        Returns:
            Dict with extracted navigation data
        """
        data = {}
        
        try:
            # GGA - Global Positioning System Fix Data
            if hasattr(msg, 'sentence_type') and msg.sentence_type == 'GGA':
                if msg.latitude and msg.longitude:
                    data['latitude'] = float(msg.latitude)
                    data['longitude'] = float(msg.longitude)
                    data['latitude_dir'] = msg.lat_dir
                    data['longitude_dir'] = msg.lon_dir
                    
                if msg.altitude is not None:
                    data['altitude_m'] = float(msg.altitude)
                    
                if msg.gps_qual is not None:
                    data['gps_quality'] = int(msg.gps_qual)
                    
                if msg.num_sats is not None:
                    data['satellites'] = int(msg.num_sats)
                    
                if msg.timestamp:
                    data['time'] = msg.timestamp
            
            # RMC - Recommended Minimum Course
            elif hasattr(msg, 'sentence_type') and msg.sentence_type == 'RMC':
                if msg.latitude and msg.longitude:
                    data['latitude'] = float(msg.latitude)
                    data['longitude'] = float(msg.longitude)
                    data['latitude_dir'] = msg.lat_dir
                    data['longitude_dir'] = msg.lon_dir
                    
                if msg.spd_over_grnd is not None:
                    data['speed_knots'] = float(msg.spd_over_grnd)
                    
                if msg.true_course is not None:
                    data['heading'] = float(msg.true_course)
                    
                if msg.timestamp and msg.datestamp:
                    data['time'] = msg.timestamp
                    data['date'] = msg.datestamp
                    
                data['status'] = msg.status
            
            # VTG - Track Made Good and Ground Speed
            elif hasattr(msg, 'sentence_type') and msg.sentence_type == 'VTG':
                if msg.true_track is not None:
                    data['heading'] = float(msg.true_track)
                    
                if msg.spd_over_grnd_kts is not None:
                    data['speed_knots'] = float(msg.spd_over_grnd_kts)
                    
                if msg.spd_over_grnd_kmph is not None:
                    data['speed_kmh'] = float(msg.spd_over_grnd_kmph)
            
            # GLL - Geographic Position
            elif hasattr(msg, 'sentence_type') and msg.sentence_type == 'GLL':
                if msg.latitude and msg.longitude:
                    data['latitude'] = float(msg.latitude)
                    data['longitude'] = float(msg.longitude)
                    data['latitude_dir'] = msg.lat_dir
                    data['longitude_dir'] = msg.lon_dir
                    
                if msg.timestamp:
                    data['time'] = msg.timestamp
                    
                data['status'] = msg.status
            
            # Add timestamp for all data
            if data:
                data['parsed_timestamp'] = datetime.now(timezone.utc)
                
            return data if data else None
            
        except Exception as e:
            if config.LOG_RAW_NMEA:
                logger.error(f"NMEA data extraction error: {e}")
            return None
    
    def get_latest_navigation_data(self) -> Dict[str, Any]:
        """
        Get the most recent complete navigation data
        
        Returns:
            Dict with latest navigation data
        """
        # Convert coordinates to decimal degrees
        nav_data = self.last_valid_data.copy()
        
        if 'latitude' in nav_data and 'longitude' in nav_data:
            # Convert to signed decimal degrees
            lat = nav_data['latitude']
            lon = nav_data['longitude']
            
            if nav_data.get('latitude_dir') == 'S':
                lat = -lat
            if nav_data.get('longitude_dir') == 'W':
                lon = -lon
                
            nav_data['latitude_decimal'] = round(lat, config.COORDINATE_PRECISION)
            nav_data['longitude_decimal'] = round(lon, config.COORDINATE_PRECISION)
        
        # Convert altitude to feet if available
        if 'altitude_m' in nav_data:
            nav_data['altitude_ft'] = round(nav_data['altitude_m'] * 3.28084, 1)
        
        # Convert speed to different units
        if 'speed_knots' in nav_data:
            knots = nav_data['speed_knots']
            nav_data['speed_kmh'] = round(knots * 1.852, 1)
            nav_data['speed_mph'] = round(knots * 1.15078, 1)
        
        return nav_data
    
    def get_stats(self) -> Dict[str, int]:
        """Get parser statistics"""
        return {
            'sentences_parsed': self.sentences_parsed,
            'parse_errors': self.parse_error_count,
            'success_rate': round((self.sentences_parsed / max(1, self.sentences_parsed + self.parse_error_count)) * 100, 1)
        }
    
    def reset_stats(self):
        """Reset parser statistics"""
        self.parse_error_count = 0
        self.sentences_parsed = 0