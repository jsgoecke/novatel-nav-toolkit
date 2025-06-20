#!/usr/bin/env python3
"""
NovAtel PASSCOM/PASSTHROUGH Parser Module

This module provides parsing capabilities for NovAtel PASSCOM and PASSTHROUGH
UDP dumps containing ADS-B data. It handles the NovAtel wrapper format,
frame boundary detection, ASCII-hex conversion, and Mode-S frame extraction.

Author: NASA G-III Navigation Validation System
"""

import struct
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone
import re
import config
from logger import logger


class NovAtelPasscomParser:
    """
    Parser for NovAtel PASSCOM/PASSTHROUGH wrapped ADS-B data.
    
    Handles:
    - Frame boundary detection (0x7E 0x26 markers)
    - NovAtel wrapper stripping
    - ASCII-hex to binary conversion
    - Mode-S frame extraction (14/28 byte frames)
    """
    
    # NovAtel frame markers
    FRAME_START_MARKER = b'\x7e\x26'  # ~& start-of-record
    
    # Wrapper patterns
    WRAPPER_PATTERN = re.compile(rb'Received packet from [^:]+:\d+: ')
    
    def __init__(self):
        """Initialize the PASSCOM parser."""
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.frames_processed = 0
        self.frames_parsed_successfully = 0
        self.wrapper_strip_count = 0
        self.ascii_hex_conversions = 0
        self.mode_s_frames_extracted = 0
        self.parse_errors = 0
        
        # Buffer for incomplete frames
        self.frame_buffer = b''
        
    def parse_passcom_frame(self, raw_data: bytes) -> List[bytes]:
        """
        Parse NovAtel PASSCOM frame and extract Mode-S frames.
        
        Args:
            raw_data: Raw UDP packet data containing PASSCOM wrapper
            
        Returns:
            List of extracted Mode-S frame bytes (14 or 28 bytes each)
        """
        try:
            self.frames_processed += 1
            
            if config.LOG_PASSCOM_FRAMES:
                logger.info(f"[PASSCOM] Processing frame: {raw_data[:50].hex()}...")
            
            # Add data to buffer for processing
            self.frame_buffer += raw_data
            
            # Extract all complete frames from buffer
            extracted_frames = []
            
            while True:
                frame_data = self._extract_next_frame()
                if not frame_data:
                    break
                    
                mode_s_frames = self._process_frame_data(frame_data)
                extracted_frames.extend(mode_s_frames)
            
            if extracted_frames:
                self.frames_parsed_successfully += 1
                
            return extracted_frames
            
        except Exception as e:
            self.parse_errors += 1
            logger.error(f"[PASSCOM] Parse error: {e}")
            return []
    
    def _extract_next_frame(self) -> Optional[bytes]:
        """
        Extract the next complete frame from the buffer.
        
        Returns:
            Frame data bytes, or None if no complete frame available
        """
        try:
            # Find frame start marker
            marker_pos = self.frame_buffer.find(self.FRAME_START_MARKER)
            if marker_pos == -1:
                # No frame marker found, keep last 100 bytes in case marker spans buffer boundary
                if len(self.frame_buffer) > 100:
                    self.frame_buffer = self.frame_buffer[-100:]
                return None
            
            # Remove data before marker
            if marker_pos > 0:
                self.frame_buffer = self.frame_buffer[marker_pos:]
            
            # Check if we have enough data for length field
            if len(self.frame_buffer) < 4:  # marker (2) + length (2)
                return None
            
            # Extract data length (big-endian)
            data_length = struct.unpack('>H', self.frame_buffer[2:4])[0]
            
            if config.LOG_PASSCOM_FRAMES:
                logger.debug(f"[PASSCOM] Frame data length: {data_length}")
            
            # Check if we have complete frame
            total_frame_length = 4 + data_length  # marker + length + data
            if len(self.frame_buffer) < total_frame_length:
                return None
            
            # Extract frame data
            frame_data = self.frame_buffer[4:total_frame_length]
            
            # Remove processed frame from buffer
            self.frame_buffer = self.frame_buffer[total_frame_length:]
            
            return frame_data
            
        except Exception as e:
            logger.error(f"[PASSCOM] Frame extraction error: {e}")
            return None
    
    def _process_frame_data(self, frame_data: bytes) -> List[bytes]:
        """
        Process extracted frame data to get Mode-S frames.
        
        Args:
            frame_data: Raw frame data after NovAtel header
            
        Returns:
            List of Mode-S frame bytes
        """
        try:
            # Strip NovAtel wrapper text
            cleaned_data = self._strip_novatel_wrapper(frame_data)
            if not cleaned_data:
                return []
            
            # Convert ASCII-hex to binary if needed
            binary_data = self._convert_ascii_hex_if_needed(cleaned_data)
            if not binary_data:
                return []
            
            # Extract Mode-S frames
            mode_s_frames = self._extract_mode_s_frames(binary_data)
            
            return mode_s_frames
            
        except Exception as e:
            logger.error(f"[PASSCOM] Frame processing error: {e}")
            return []
    
    def _strip_novatel_wrapper(self, data: bytes) -> Optional[bytes]:
        """
        Strip NovAtel wrapper text from frame data.
        
        Args:
            data: Frame data potentially containing wrapper text
            
        Returns:
            Cleaned data with wrapper removed, or None if invalid
        """
        try:
            # Check if data starts with wrapper pattern
            match = self.WRAPPER_PATTERN.match(data)
            if match:
                self.wrapper_strip_count += 1
                # Remove wrapper text
                cleaned_data = data[match.end():]
                
                if config.LOG_PASSCOM_FRAMES:
                    logger.debug(f"[PASSCOM] Stripped wrapper, remaining: {len(cleaned_data)} bytes")
                
                return cleaned_data
            else:
                # No wrapper found, return as-is
                return data
                
        except Exception as e:
            logger.error(f"[PASSCOM] Wrapper stripping error: {e}")
            return None
    
    def _convert_ascii_hex_if_needed(self, data: bytes) -> Optional[bytes]:
        """
        Convert ASCII-hex to binary if the data is ASCII-hex encoded.
        
        Args:
            data: Data bytes that might be ASCII-hex
            
        Returns:
            Binary data, or None if conversion failed
        """
        try:
            # Check if first byte looks like ASCII hex digit
            if len(data) == 0:
                return None
                
            first_byte = data[0]
            
            # Check if it's an ASCII digit or hex letter
            if (48 <= first_byte <= 57) or (65 <= first_byte <= 70) or (97 <= first_byte <= 102):
                # Looks like ASCII hex, try to convert
                try:
                    # Convert to string and remove any whitespace
                    hex_string = data.decode('ascii').strip().replace(' ', '').replace('\n', '').replace('\r', '')
                    
                    # Ensure even length for hex conversion
                    if len(hex_string) % 2 != 0:
                        hex_string = hex_string[:-1]  # Remove last character if odd length
                    
                    # Convert hex string to bytes
                    binary_data = bytes.fromhex(hex_string)
                    
                    self.ascii_hex_conversions += 1
                    
                    if config.LOG_PASSCOM_FRAMES:
                        logger.debug(f"[PASSCOM] ASCII-hex converted: {len(hex_string)} chars -> {len(binary_data)} bytes")
                    
                    return binary_data
                    
                except (ValueError, UnicodeDecodeError):
                    # Not valid ASCII hex, treat as binary
                    pass
            
            # Not ASCII hex or conversion failed, return as binary
            return data
            
        except Exception as e:
            logger.error(f"[PASSCOM] ASCII-hex conversion error: {e}")
            return None
    
    def _extract_mode_s_frames(self, binary_data: bytes) -> List[bytes]:
        """
        Extract Mode-S frames (14 or 28 bytes) from binary data.
        
        Args:
            binary_data: Binary data containing Mode-S frames
            
        Returns:
            List of Mode-S frame bytes
        """
        try:
            frames = []
            offset = 0
            
            while offset < len(binary_data):
                # Try to identify frame length by checking DF field
                if offset + 1 >= len(binary_data):
                    break
                
                # Extract first byte to get DF (Downlink Format)
                first_byte = binary_data[offset]
                df = (first_byte >> 3) & 0x1F
                
                # Determine frame length based on DF
                if df in [0, 4, 5, 11, 16, 20, 21]:
                    # Short frame (56 bits = 7 bytes, but we need 14 for CRC)
                    frame_length = 14
                elif df in [16, 17, 18, 19, 20, 21, 24]:
                    # Long frame (112 bits = 14 bytes, but extended to 28)
                    frame_length = 28
                else:
                    # Unknown DF, try 14 bytes as default
                    frame_length = 14
                
                # Check if we have enough data for this frame
                if offset + frame_length > len(binary_data):
                    # Try with shorter frame
                    if frame_length == 28 and offset + 14 <= len(binary_data):
                        frame_length = 14
                    else:
                        break
                
                # Extract frame
                frame = binary_data[offset:offset + frame_length]
                
                # Validate frame has reasonable DF
                frame_df = (frame[0] >> 3) & 0x1F
                if 0 <= frame_df <= 31:  # Valid DF range
                    frames.append(frame)
                    self.mode_s_frames_extracted += 1
                    
                    if config.LOG_PASSCOM_FRAMES:
                        logger.debug(f"[PASSCOM] Extracted Mode-S frame: DF={frame_df}, length={frame_length}")
                
                offset += frame_length
            
            return frames
            
        except Exception as e:
            logger.error(f"[PASSCOM] Mode-S extraction error: {e}")
            return []
    
    def detect_frame_boundaries(self, data: bytes) -> List[int]:
        """
        Detect all frame boundary positions in data.
        
        Args:
            data: Raw data to search for frame boundaries
            
        Returns:
            List of byte positions where frame markers are found
        """
        positions = []
        offset = 0
        
        while True:
            pos = data.find(self.FRAME_START_MARKER, offset)
            if pos == -1:
                break
            positions.append(pos)
            offset = pos + 1
        
        return positions
    
    def is_passcom_frame(self, data: bytes) -> bool:
        """
        Check if data appears to be a PASSCOM frame.
        
        Args:
            data: Data to check
            
        Returns:
            True if data looks like PASSCOM format
        """
        # Check for frame marker
        if self.FRAME_START_MARKER in data:
            return True
        
        # Check for wrapper pattern
        if self.WRAPPER_PATTERN.search(data):
            return True
        
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get parser statistics."""
        return {
            'frames_processed': self.frames_processed,
            'frames_parsed_successfully': self.frames_parsed_successfully,
            'success_rate': round((self.frames_parsed_successfully / max(1, self.frames_processed)) * 100, 1),
            'wrapper_strip_count': self.wrapper_strip_count,
            'ascii_hex_conversions': self.ascii_hex_conversions,
            'mode_s_frames_extracted': self.mode_s_frames_extracted,
            'parse_errors': self.parse_errors,
            'buffer_size': len(self.frame_buffer)
        }
    
    def reset_stats(self):
        """Reset parser statistics."""
        self.frames_processed = 0
        self.frames_parsed_successfully = 0
        self.wrapper_strip_count = 0
        self.ascii_hex_conversions = 0
        self.mode_s_frames_extracted = 0
        self.parse_errors = 0
    
    def clear_buffer(self):
        """Clear the internal frame buffer."""
        self.frame_buffer = b''


if __name__ == "__main__":
    # Test the parser with sample data
    import sys
    
    logging.basicConfig(level=logging.DEBUG)
    parser = NovAtelPasscomParser()
    
    # Sample PASSCOM data (from logs)
    sample_data = bytes.fromhex("5265636569766564207061636b65742066726f6d203139322e3136382e342e313a36313730383a207e26002b4a28fa38a6857cf38a3e0b1c2f9e0ecfa54d0831ef43eda1b7a6e3a673190cc52f6dbba9ca5ee12d7a2bea1dbfd5a2baccb84211da7ba943dd31a58a230f44334593087e7e250102042d3a9c86cb270000000002060e3af6557b2b00000000c4f87e")
    
    print("Testing NovAtel PASSCOM Parser")
    print(f"Sample data length: {len(sample_data)} bytes")
    
    frames = parser.parse_passcom_frame(sample_data)
    print(f"Extracted {len(frames)} Mode-S frames")
    
    for i, frame in enumerate(frames):
        df = (frame[0] >> 3) & 0x1F
        print(f"Frame {i+1}: {frame.hex()} (DF={df}, {len(frame)} bytes)")
    
    print("\nParser Statistics:")
    stats = parser.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")