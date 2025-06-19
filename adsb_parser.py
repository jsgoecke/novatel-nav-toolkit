"""
ADS-B Message Parser for Aviation Data
Enhanced with GDL-90 deframing support
"""

import time
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from pyModeS.decoder import adsb
import config
from gdl90_deframer import GDL90Deframer
from logger import logger


class ADSBParser:
    """Parser for ADS-B aviation messages"""
    
    def __init__(self):
        """Initialize ADS-B parser"""
        self.parse_error_count = 0
        self.messages_parsed = 0
        self.last_valid_data = {}
        self.aircraft_data = {}  # Store data by ICAO address
        self.gdl90_deframer = GDL90Deframer()
        self.gdl90_messages_processed = 0
        self.raw_messages_processed = 0
        
    def parse_message(self, message: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse a single ADS-B message (with GDL-90 deframing support)
        
        Args:
            message: Raw message bytes (could be GDL-90 wrapped or raw Mode S)
            
        Returns:
            Dict with parsed aviation data or None if parsing failed
        """
        try:
            if config.LOG_PARSE_ATTEMPTS:
                logger.info(f"[ADSB] Attempting to parse: {message.hex()}")
            
            # Skip empty messages
            if not message:
                if config.LOG_PARSE_ATTEMPTS:
                    logger.error(f"[ADSB] Skipping empty message")
                return None
            
            # Preprocess message to handle GDL-90 wrapping
            processed_messages = self._preprocess_message(message)
            
            if not processed_messages:
                if config.LOG_PARSE_ATTEMPTS:
                    logger.error(f"[ADSB] No valid messages after preprocessing")
                return None
            
            # Process each extracted message
            for adsb_payload in processed_messages:
                result = self._parse_adsb_payload(adsb_payload)
                if result:
                    return result  # Return first successful parse
            
            return None
            
        except Exception as e:
            self.parse_error_count += 1
            logger.error(f"[ADSB] Parse error: {e}")
            return None
    
    def _preprocess_message(self, raw_message: bytes) -> List[bytes]:
        """
        Preprocess raw message to extract ADS-B payloads
        
        Handles both GDL-90 wrapped and raw Mode S messages
        
        Args:
            raw_message: Raw message bytes
            
        Returns:
            List of ADS-B payload bytes
        """
        # Check if this looks like GDL-90 wrapped data
        if self._is_gdl90_wrapped(raw_message):
            if config.LOG_PARSE_ATTEMPTS:
                logger.info(f"[ADSB] Detected GDL-90 wrapped data")
            
            self.gdl90_messages_processed += 1
            
            # Use GDL-90 deframer to extract ADS-B messages
            deframed_messages = self.gdl90_deframer.deframe_message(raw_message)
            
            if config.LOG_PARSE_ATTEMPTS and deframed_messages:
                logger.info(f"[ADSB] Deframed {len(deframed_messages)} ADS-B messages")
                for i, msg in enumerate(deframed_messages):
                    df = (msg[0] >> 3) & 0x1F
                    logger.info(f"[ADSB] Deframed message {i+1}: {msg.hex()} (DF={df})")
            
            return deframed_messages
        else:
            if config.LOG_PARSE_ATTEMPTS:
                logger.info(f"[ADSB] Treating as raw Mode S message")
            
            self.raw_messages_processed += 1
            
            # Return as single raw message
            return [raw_message]
    
    def _is_gdl90_wrapped(self, data: bytes) -> bool:
        """
        Detect if data appears to be GDL-90 wrapped
        
        Args:
            data: Raw message bytes
            
        Returns:
            True if data looks like GDL-90 format
        """
        return self.gdl90_deframer.is_gdl90_frame(data)
    
    def _parse_adsb_payload(self, adsb_payload: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse a single ADS-B payload (14 bytes)
        
        Args:
            adsb_payload: 14-byte ADS-B message payload
            
        Returns:
            Dict with parsed aviation data or None if parsing failed
        """
        # Convert bytes to hex string for pyModeS
        if isinstance(adsb_payload, bytes):
            raw_msg = adsb_payload.hex()
        else:
            raw_msg = adsb_payload
            
        if config.LOG_PARSE_ATTEMPTS:
            logger.info(f"[ADSB] Processing ADS-B payload: {raw_msg}")
            
        # Get the Downlink Format
        df = adsb.df(raw_msg)
        
        if config.LOG_PARSE_ATTEMPTS:
            logger.info(f"[ADSB] Downlink Format: {df}")
        
        # Check if it's an ADS-B message (DF=17, 18, or 19)
        if df not in [17, 18, 19]:
            if config.LOG_PARSE_ATTEMPTS:
                logger.error(f"[ADSB] Not an ADS-B message (DF={df}), skipping")
            return None
            
        self.messages_parsed += 1
        
        # Extract basic information
        icao = adsb.icao(raw_msg)
        tc = adsb.typecode(raw_msg)
        
        if config.LOG_PARSE_ATTEMPTS:
            logger.info(f"[ADSB] ICAO: {icao}, Type Code: {tc}")
        
        # Extract data based on message type
        aviation_data = self._extract_aviation_data(raw_msg, icao, tc)
        
        if aviation_data:
            if config.LOG_PARSE_ATTEMPTS:
                logger.info(f"[ADSB] Extracted aviation data: {aviation_data}")
            
            # Update aircraft-specific data
            if icao not in self.aircraft_data:
                self.aircraft_data[icao] = {}
            
            self.aircraft_data[icao].update(aviation_data)
            self.last_valid_data.update(aviation_data)
            return aviation_data
        else:
            if config.LOG_PARSE_ATTEMPTS:
                logger.info(f"[ADSB] No aviation data extracted from type code: {tc}")
            
        return None
    
    def _extract_aviation_data(self, raw_msg: str, icao: str, tc: int) -> Optional[Dict[str, Any]]:
        """Extract aviation data from ADS-B message"""
        data = {'icao': icao, 'type_code': tc, 'parsed_timestamp': datetime.now(timezone.utc)}
        
        try:
            # Aircraft identification (TC 1-4)
            if 1 <= tc <= 4:
                data['callsign'] = adsb.callsign(raw_msg).strip()
                data['category'] = adsb.category(raw_msg)
            
            # Surface position (TC 5-8) or Airborne position (TC 9-18)
            elif 5 <= tc <= 18:
                # Try to get position if available
                try:
                    lat, lon = adsb.position_with_ref(raw_msg, 0, 0, 0, 0)  # Needs reference
                    if lat and lon:
                        data['latitude'] = lat
                        data['longitude'] = lon
                except:
                    pass
                
                # Get altitude for airborne messages
                if 9 <= tc <= 18:
                    alt = adsb.altitude(raw_msg)
                    if alt:
                        data['altitude_ft'] = alt
            
            # Airborne velocity (TC 19)
            elif tc == 19:
                velocity = adsb.velocity(raw_msg)
                if velocity:
                    data['speed_knots'] = velocity[0] if velocity[0] else None
                    data['heading'] = velocity[1] if velocity[1] else None
                    data['vertical_rate'] = velocity[2] if velocity[2] else None
            
            return data if len(data) > 3 else None  # Return only if we got more than basic fields
            
        except Exception as e:
            if config.LOG_PARSE_ATTEMPTS:
                logger.error(f"[ADSB] Data extraction error: {e}")
            return None
    
    def get_latest_aviation_data(self) -> Dict[str, Any]:
        """Get the most recent aviation data"""
        return self.last_valid_data.copy()
    
    def get_aircraft_data(self) -> Dict[str, Dict[str, Any]]:
        """Get all aircraft data by ICAO"""
        return self.aircraft_data.copy()
    
    def get_stats(self) -> Dict[str, int]:
        """Get parser statistics"""
        gdl90_stats = self.gdl90_deframer.get_stats()
        
        return {
            'messages_parsed': self.messages_parsed,
            'parse_errors': self.parse_error_count,
            'success_rate': round((self.messages_parsed / max(1, self.messages_parsed + self.parse_error_count)) * 100, 1),
            'aircraft_tracked': len(self.aircraft_data),
            'gdl90_messages_processed': self.gdl90_messages_processed,
            'raw_messages_processed': self.raw_messages_processed,
            'gdl90_frames_processed': gdl90_stats['frames_processed'],
            'gdl90_adsb_found': gdl90_stats['adsb_messages_found'],
            'gdl90_success_rate': gdl90_stats['success_rate']
        }
    
    def reset_stats(self):
        """Reset parser statistics"""
        self.parse_error_count = 0
        self.messages_parsed = 0
        self.gdl90_messages_processed = 0
        self.raw_messages_processed = 0
        self.gdl90_deframer.reset_stats()
