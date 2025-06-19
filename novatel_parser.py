#!/usr/bin/env python3
"""
Novatel Parser Module for ProPak6 Navigation Data Toolkit

This module provides parsing capabilities for Novatel GNSS receiver messages.
It supports both ASCII and binary message formats commonly used in aviation
and precision navigation applications.

Supported Message Types:
- BESTPOS/BESTPOSA: Best position solution
- BESTVEL/BESTVELA: Best velocity solution
- INSPVA/INSPVAA: INS position, velocity, and attitude
- INSPVAX/INSPVAXA: Extended INS position, velocity, and attitude
- HEADING/HEADINGA: Heading information
- PSRDOP/PSRDOPA: Position dilution of precision

Message Formats:
- ASCII: Human-readable comma-separated format
- Binary: Compact binary format for high-rate data

Author: Novatel ProPak6 Navigation Data Toolkit
"""

import struct
import logging
from typing import Dict, Any, Optional, Union, List
from datetime import datetime, timezone
import binascii
import config


class NovatelParser:
    """
    Parser for Novatel GNSS receiver messages.
    
    This class handles parsing of Novatel OEM series messages in both ASCII
    and binary formats. It extracts navigation data including position,
    velocity, attitude, and quality indicators.
    
    Example:
        parser = NovatelParser()
        
        # Parse ASCII message
        ascii_msg = "#BESTPOSA,COM1,0,55.0,FINESTEERING,2167,144140.000,02000040,cdba,32768;SOL_COMPUTED,SINGLE,51.15043711111,-114.03067851111,1064.9551,-17.0000,WGS84,1.6389,1.3921,2.4639,\"\",0.000,0.000,35,30,30,30,0,06,0,33*2d0d0a"
        result = parser.parse_message(ascii_msg.encode())
        
        # Parse binary message
        binary_msg = bytes.fromhex("aa4412...")
        result = parser.parse_message(binary_msg)
    """

    # Novatel binary message sync pattern
    BINARY_SYNC = b'\xaa\x44\x12\x1c'
    
    # Message IDs for binary messages
    MESSAGE_IDS = {
        42: 'BESTPOS',
        99: 'BESTVEL',
        507: 'INSPVA',
        1465: 'INSPVAX',
        971: 'HEADING',
        174: 'PSRDOP'
    }
    
    # Solution status codes
    SOLUTION_STATUS = {
        0: 'SOL_COMPUTED',
        1: 'INSUFFICIENT_OBS',
        2: 'NO_CONVERGENCE',
        3: 'SINGULARITY',
        4: 'COV_TRACE',
        5: 'TEST_DIST',
        6: 'COLD_START',
        7: 'V_H_LIMIT',
        8: 'VARIANCE',
        9: 'RESIDUALS',
        10: 'DELTA_POS',
        11: 'NEGATIVE_VAR',
        12: 'INTEGRITY_WARNING',
        13: 'INS_INACTIVE',
        14: 'INS_ALIGNING',
        15: 'INS_BAD',
        16: 'IMU_UNPLUGGED',
        17: 'PENDING',
        18: 'INVALID_FIX'
    }
    
    # Position type codes
    POSITION_TYPE = {
        0: 'NONE',
        1: 'FIXEDPOS',
        2: 'FIXEDHEIGHT',
        8: 'DOPPLER_VELOCITY',
        16: 'SINGLE',
        17: 'PSRDIFF',
        18: 'WAAS',
        19: 'PROPAGATED',
        20: 'OMNISTAR',
        32: 'L1_FLOAT',
        33: 'IONOFREE_FLOAT',
        34: 'NARROW_FLOAT',
        48: 'L1_INT',
        49: 'WIDE_INT',
        50: 'NARROW_INT',
        68: 'RTK_DIRECT_INS',
        69: 'INS_SBAS',
        70: 'INS_PSRSP',
        71: 'INS_PSRDIFF',
        72: 'INS_RTKFLOAT',
        73: 'INS_RTKFIXED',
        74: 'INS_OMNISTAR',
        75: 'INS_OMNISTAR_HP',
        76: 'INS_OMNISTAR_XP',
        77: 'OMNISTAR_HP',
        78: 'OMNISTAR_XP',
        79: 'PPP_CONVERGING',
        80: 'PPP',
        81: 'OPERATIONAL',
        82: 'WARNING',
        83: 'OUT_OF_BOUNDS',
        84: 'INS_PPP_CONVERGING',
        85: 'INS_PPP',
        86: 'UNKNOWN'
    }

    def __init__(self):
        """Initialize the Novatel parser."""
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.messages_parsed = 0
        self.parse_errors = 0
        self.ascii_messages = 0
        self.binary_messages = 0
        
        # Latest navigation data
        self.latest_position = {}
        self.latest_velocity = {}
        self.latest_attitude = {}
        self.latest_quality = {}
        
        # Message buffers for binary parsing
        self.binary_buffer = b''

    def parse_message(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse a Novatel message from raw data.
        
        Args:
            data: Raw message data (bytes)
            
        Returns:
            dict: Parsed navigation data, or None if parsing failed
        """
        try:
            # Check if it's ASCII or binary
            if data.startswith(b'#') or data.startswith(b'%'):
                return self._parse_ascii_message(data)
            elif self.BINARY_SYNC in data:
                return self._parse_binary_message(data)
            else:
                # Try to add to buffer for potential binary message
                self.binary_buffer += data
                if len(self.binary_buffer) > 4096:  # Limit buffer size
                    self.binary_buffer = self.binary_buffer[-2048:]
                
                # Check buffer for complete binary message
                return self._parse_binary_message(self.binary_buffer)
                
        except Exception as e:
            self.parse_errors += 1
            if config.LOG_NOVATEL_MESSAGES:
                self.logger.error(f"Error parsing Novatel message: {e}")
            return None

    def _parse_ascii_message(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse ASCII Novatel message."""
        try:
            message = data.decode('ascii', errors='ignore').strip()
            
            # Remove log indicators
            if message.startswith('#'):
                message = message[1:]
            elif message.startswith('%'):
                message = message[1:]
            
            # Split header and body
            if ';' not in message:
                return None
                
            header_part, body_part = message.split(';', 1)
            
            # Parse header
            header_fields = header_part.split(',')
            if len(header_fields) < 10:
                return None
                
            message_name = header_fields[0].upper()
            
            # Parse body based on message type
            result = None
            if message_name.startswith('BESTPOS'):
                result = self._parse_bestpos_ascii(body_part)
            elif message_name.startswith('BESTVEL'):
                result = self._parse_bestvel_ascii(body_part)
            elif message_name.startswith('INSPVA'):
                result = self._parse_inspva_ascii(body_part)
            elif message_name.startswith('INSPVAX'):
                result = self._parse_inspvax_ascii(body_part)
            elif message_name.startswith('HEADING'):
                result = self._parse_heading_ascii(body_part)
            elif message_name.startswith('PSRDOP'):
                result = self._parse_psrdop_ascii(body_part)
            
            if result:
                result['message_type'] = message_name
                result['format'] = 'ASCII'
                result['timestamp'] = datetime.now(timezone.utc)
                self.messages_parsed += 1
                self.ascii_messages += 1
                self._update_latest_data(result)
                
            return result
            
        except Exception as e:
            self.parse_errors += 1
            if config.LOG_NOVATEL_MESSAGES:
                self.logger.error(f"Error parsing ASCII message: {e}")
            return None

    def _parse_binary_message(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse binary Novatel message."""
        try:
            # Find sync pattern
            sync_pos = data.find(self.BINARY_SYNC)
            if sync_pos == -1:
                return None
            
            # Need at least header + sync
            if len(data) < sync_pos + 28:
                return None
                
            # Extract header
            header_data = data[sync_pos:sync_pos + 28]
            
            # Parse header
            header = struct.unpack('<4s3B2H2I2H', header_data)
            sync, hdr_len, msg_id, msg_type, port_addr, msg_len, seq, idle_time, time_status, week = header
            
            # Calculate total message length
            total_length = hdr_len + msg_len + 4  # +4 for CRC
            
            # Check if we have complete message
            if len(data) < sync_pos + total_length:
                return None
            
            # Extract message data
            msg_data = data[sync_pos + hdr_len:sync_pos + hdr_len + msg_len]
            
            # Parse based on message ID
            result = None
            message_name = self.MESSAGE_IDS.get(msg_id, f'MSG_{msg_id}')
            
            if msg_id == 42:  # BESTPOS
                result = self._parse_bestpos_binary(msg_data)
            elif msg_id == 99:  # BESTVEL
                result = self._parse_bestvel_binary(msg_data)
            elif msg_id == 507:  # INSPVA
                result = self._parse_inspva_binary(msg_data)
            elif msg_id == 1465:  # INSPVAX
                result = self._parse_inspvax_binary(msg_data)
            elif msg_id == 971:  # HEADING
                result = self._parse_heading_binary(msg_data)
            elif msg_id == 174:  # PSRDOP
                result = self._parse_psrdop_binary(msg_data)
            
            if result:
                result['message_type'] = message_name
                result['format'] = 'BINARY'
                result['message_id'] = msg_id
                result['timestamp'] = datetime.now(timezone.utc)
                result['gps_week'] = week
                result['gps_time'] = idle_time / 1000.0
                self.messages_parsed += 1
                self.binary_messages += 1
                self._update_latest_data(result)
                
            # Clean up buffer
            self.binary_buffer = data[sync_pos + total_length:]
            
            return result
            
        except Exception as e:
            self.parse_errors += 1
            if config.LOG_NOVATEL_MESSAGES:
                self.logger.error(f"Error parsing binary message: {e}")
            return None

    def _parse_bestpos_ascii(self, body: str) -> Optional[Dict[str, Any]]:
        """Parse BESTPOS ASCII message."""
        fields = body.split(',')
        if len(fields) < 21:
            return None
            
        try:
            return {
                'solution_status': fields[0],
                'position_type': fields[1],
                'latitude': float(fields[2]),
                'longitude': float(fields[3]),
                'height': float(fields[4]),
                'undulation': float(fields[5]),
                'datum': fields[6],
                'lat_stddev': float(fields[7]),
                'lon_stddev': float(fields[8]),
                'hgt_stddev': float(fields[9]),
                'base_station_id': fields[10],
                'diff_age': float(fields[11]),
                'sol_age': float(fields[12]),
                'num_svs': int(fields[13]),
                'num_sol_svs': int(fields[14]),
                'num_gg_l1': int(fields[15]),
                'num_gg_l1_l2': int(fields[16]),
                'ext_sol_stat': int(fields[18]) if len(fields) > 18 else 0
            }
        except (ValueError, IndexError):
            return None

    def _parse_bestvel_ascii(self, body: str) -> Optional[Dict[str, Any]]:
        """Parse BESTVEL ASCII message."""
        fields = body.split(',')
        if len(fields) < 11:
            return None
            
        try:
            return {
                'solution_status': fields[0],
                'velocity_type': fields[1],
                'latency': float(fields[2]),
                'diff_age': float(fields[3]),
                'hor_speed': float(fields[4]),
                'track_gnd': float(fields[5]),
                'vert_speed': float(fields[6]),
                'reserved': float(fields[7])
            }
        except (ValueError, IndexError):
            return None

    def _parse_inspva_ascii(self, body: str) -> Optional[Dict[str, Any]]:
        """Parse INSPVA ASCII message."""
        fields = body.split(',')
        if len(fields) < 11:
            return None
            
        try:
            return {
                'week': int(fields[0]),
                'seconds': float(fields[1]),
                'latitude': float(fields[2]),
                'longitude': float(fields[3]),
                'height': float(fields[4]),
                'north_velocity': float(fields[5]),
                'east_velocity': float(fields[6]),
                'up_velocity': float(fields[7]),
                'roll': float(fields[8]),
                'pitch': float(fields[9]),
                'azimuth': float(fields[10]),
                'status': fields[11] if len(fields) > 11 else 'UNKNOWN'
            }
        except (ValueError, IndexError):
            return None

    def _parse_inspvax_ascii(self, body: str) -> Optional[Dict[str, Any]]:
        """Parse INSPVAX ASCII message."""
        fields = body.split(',')
        if len(fields) < 20:
            return None
            
        try:
            return {
                'ins_status': int(fields[0]),
                'pos_type': int(fields[1]),
                'latitude': float(fields[2]),
                'longitude': float(fields[3]),
                'height': float(fields[4]),
                'undulation': float(fields[5]),
                'north_velocity': float(fields[6]),
                'east_velocity': float(fields[7]),
                'up_velocity': float(fields[8]),
                'roll': float(fields[9]),
                'pitch': float(fields[10]),
                'azimuth': float(fields[11]),
                'lat_stddev': float(fields[12]),
                'lon_stddev': float(fields[13]),
                'hgt_stddev': float(fields[14]),
                'north_vel_stddev': float(fields[15]),
                'east_vel_stddev': float(fields[16]),
                'up_vel_stddev': float(fields[17]),
                'roll_stddev': float(fields[18]),
                'pitch_stddev': float(fields[19]),
                'azimuth_stddev': float(fields[20]) if len(fields) > 20 else 0.0
            }
        except (ValueError, IndexError):
            return None

    def _parse_heading_ascii(self, body: str) -> Optional[Dict[str, Any]]:
        """Parse HEADING ASCII message."""
        fields = body.split(',')
        if len(fields) < 8:
            return None
            
        try:
            return {
                'solution_status': fields[0],
                'position_type': fields[1],
                'length': float(fields[2]),
                'heading': float(fields[3]),
                'pitch': float(fields[4]),
                'reserved': float(fields[5]),
                'heading_stddev': float(fields[6]),
                'pitch_stddev': float(fields[7])
            }
        except (ValueError, IndexError):
            return None

    def _parse_psrdop_ascii(self, body: str) -> Optional[Dict[str, Any]]:
        """Parse PSRDOP ASCII message."""
        fields = body.split(',')
        if len(fields) < 6:
            return None
            
        try:
            return {
                'gdop': float(fields[0]),
                'pdop': float(fields[1]),
                'hdop': float(fields[2]),
                'htdop': float(fields[3]),
                'tdop': float(fields[4]),
                'cutoff': float(fields[5]) if len(fields) > 5 else 0.0
            }
        except (ValueError, IndexError):
            return None

    def _parse_bestpos_binary(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse BESTPOS binary message."""
        try:
            if len(data) < 72:
                return None
                
            unpacked = struct.unpack('<4I8d4f4I', data[:72])
            
            return {
                'solution_status': self.SOLUTION_STATUS.get(unpacked[0], 'UNKNOWN'),
                'position_type': self.POSITION_TYPE.get(unpacked[1], 'UNKNOWN'),
                'latitude': unpacked[4],
                'longitude': unpacked[5],
                'height': unpacked[6],
                'undulation': unpacked[7],
                'lat_stddev': unpacked[12],
                'lon_stddev': unpacked[13],
                'hgt_stddev': unpacked[14],
                'num_svs': unpacked[16],
                'num_sol_svs': unpacked[17]
            }
        except (struct.error, IndexError):
            return None

    def _parse_bestvel_binary(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse BESTVEL binary message."""
        try:
            if len(data) < 44:
                return None
                
            unpacked = struct.unpack('<4I4d4f', data[:44])
            
            return {
                'solution_status': self.SOLUTION_STATUS.get(unpacked[0], 'UNKNOWN'),
                'velocity_type': self.POSITION_TYPE.get(unpacked[1], 'UNKNOWN'),
                'latency': unpacked[4],
                'diff_age': unpacked[5],
                'hor_speed': unpacked[6],
                'track_gnd': unpacked[7],
                'vert_speed': unpacked[8]
            }
        except (struct.error, IndexError):
            return None

    def _parse_inspva_binary(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse INSPVA binary message."""
        try:
            if len(data) < 88:
                return None
                
            unpacked = struct.unpack('<I2d9d4I', data[:88])
            
            return {
                'week': unpacked[0],
                'seconds': unpacked[1],
                'latitude': unpacked[2],
                'longitude': unpacked[3],
                'height': unpacked[4],
                'north_velocity': unpacked[5],
                'east_velocity': unpacked[6],
                'up_velocity': unpacked[7],
                'roll': unpacked[8],
                'pitch': unpacked[9],
                'azimuth': unpacked[10],
                'ins_status': unpacked[11]
            }
        except (struct.error, IndexError):
            return None

    def _parse_inspvax_binary(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse INSPVAX binary message."""
        try:
            if len(data) < 126:
                return None
                
            # Complex binary structure - simplified for key fields
            unpacked = struct.unpack('<2I14d8f', data[:126])
            
            return {
                'ins_status': unpacked[0],
                'pos_type': unpacked[1],
                'latitude': unpacked[2],
                'longitude': unpacked[3],
                'height': unpacked[4],
                'undulation': unpacked[5],
                'north_velocity': unpacked[6],
                'east_velocity': unpacked[7],
                'up_velocity': unpacked[8],
                'roll': unpacked[9],
                'pitch': unpacked[10],
                'azimuth': unpacked[11],
                'lat_stddev': unpacked[16],
                'lon_stddev': unpacked[17],
                'hgt_stddev': unpacked[18]
            }
        except (struct.error, IndexError):
            return None

    def _parse_heading_binary(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse HEADING binary message."""
        try:
            if len(data) < 32:
                return None
                
            unpacked = struct.unpack('<4I4f', data[:32])
            
            return {
                'solution_status': self.SOLUTION_STATUS.get(unpacked[0], 'UNKNOWN'),
                'position_type': self.POSITION_TYPE.get(unpacked[1], 'UNKNOWN'),
                'length': unpacked[4],
                'heading': unpacked[5],
                'pitch': unpacked[6],
                'heading_stddev': unpacked[7]
            }
        except (struct.error, IndexError):
            return None

    def _parse_psrdop_binary(self, data: bytes) -> Optional[Dict[str, Any]]:
        """Parse PSRDOP binary message."""
        try:
            if len(data) < 24:
                return None
                
            unpacked = struct.unpack('<6f', data[:24])
            
            return {
                'gdop': unpacked[0],
                'pdop': unpacked[1],
                'hdop': unpacked[2],
                'htdop': unpacked[3],
                'tdop': unpacked[4],
                'cutoff': unpacked[5]
            }
        except (struct.error, IndexError):
            return None

    def _update_latest_data(self, parsed_data: Dict[str, Any]):
        """Update latest navigation data storage."""
        msg_type = parsed_data.get('message_type', '').upper()
        
        if 'BESTPOS' in msg_type or 'INSPVA' in msg_type:
            if 'latitude' in parsed_data and 'longitude' in parsed_data:
                self.latest_position.update(parsed_data)
                
        if 'BESTVEL' in msg_type or 'INSPVA' in msg_type:
            if any(key in parsed_data for key in ['hor_speed', 'north_velocity', 'east_velocity']):
                self.latest_velocity.update(parsed_data)
                
        if 'INSPVA' in msg_type or 'HEADING' in msg_type:
            if any(key in parsed_data for key in ['roll', 'pitch', 'azimuth', 'heading']):
                self.latest_attitude.update(parsed_data)
                
        if 'PSRDOP' in msg_type:
            self.latest_quality.update(parsed_data)

    def get_latest_navigation_data(self) -> Dict[str, Any]:
        """
        Get the latest consolidated navigation data.
        
        Returns:
            dict: Latest navigation data with standardized keys
        """
        nav_data = {}
        
        # Position data
        if self.latest_position:
            nav_data.update({
                'latitude': self.latest_position.get('latitude'),
                'longitude': self.latest_position.get('longitude'),
                'altitude_m': self.latest_position.get('height'),
                'altitude_ft': self.latest_position.get('height', 0) * 3.28084,
                'solution_status': self.latest_position.get('solution_status'),
                'position_type': self.latest_position.get('position_type'),
                'num_satellites': self.latest_position.get('num_svs', 0),
                'position_accuracy_m': max(
                    self.latest_position.get('lat_stddev', 0),
                    self.latest_position.get('lon_stddev', 0),
                    self.latest_position.get('hgt_stddev', 0)
                )
            })
        
        # Velocity data
        if self.latest_velocity:
            nav_data.update({
                'speed_ms': self.latest_velocity.get('hor_speed'),
                'speed_knots': self.latest_velocity.get('hor_speed', 0) * 1.944,
                'speed_kmh': self.latest_velocity.get('hor_speed', 0) * 3.6,
                'track_angle': self.latest_velocity.get('track_gnd'),
                'vertical_speed_ms': self.latest_velocity.get('vert_speed'),
                'north_velocity': self.latest_velocity.get('north_velocity'),
                'east_velocity': self.latest_velocity.get('east_velocity'),
                'up_velocity': self.latest_velocity.get('up_velocity')
            })
        
        # Attitude data
        if self.latest_attitude:
            nav_data.update({
                'heading': self.latest_attitude.get('azimuth') or self.latest_attitude.get('heading'),
                'pitch': self.latest_attitude.get('pitch'),
                'roll': self.latest_attitude.get('roll')
            })
        
        # Quality data
        if self.latest_quality:
            nav_data.update({
                'gdop': self.latest_quality.get('gdop'),
                'pdop': self.latest_quality.get('pdop'),
                'hdop': self.latest_quality.get('hdop')
            })
        
        # Add timestamp
        nav_data['parsed_timestamp'] = datetime.now(timezone.utc)
        
        return nav_data

    def get_stats(self) -> Dict[str, Any]:
        """
        Get parser statistics.
        
        Returns:
            dict: Statistics including messages parsed, errors, etc.
        """
        return {
            'messages_parsed': self.messages_parsed,
            'parse_errors': self.parse_errors,
            'ascii_messages': self.ascii_messages,
            'binary_messages': self.binary_messages,
            'success_rate': (self.messages_parsed / max(1, self.messages_parsed + self.parse_errors)) * 100,
            'has_position': bool(self.latest_position),
            'has_velocity': bool(self.latest_velocity),
            'has_attitude': bool(self.latest_attitude),
            'has_quality': bool(self.latest_quality)
        }

    def reset_stats(self):
        """Reset parser statistics."""
        self.messages_parsed = 0
        self.parse_errors = 0
        self.ascii_messages = 0
        self.binary_messages = 0

    def clear_data(self):
        """Clear all stored navigation data."""
        self.latest_position.clear()
        self.latest_velocity.clear()
        self.latest_attitude.clear()
        self.latest_quality.clear()