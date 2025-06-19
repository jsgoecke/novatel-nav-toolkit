"""
GDL-90 Deframer for ADS-B Messages
Extracts ADS-B payloads from GDL-90/KISS wrapped UDP data
"""

import time
from typing import List, Optional, Tuple
import config
from logger import logger


class GDL90Deframer:
    """GDL-90/KISS deframer for extracting ADS-B messages"""
    
    # GDL-90 constants
    FLAG_BYTE = 0x7E                    # Frame boundary marker
    ESCAPE_BYTE = 0x7D                  # KISS escape byte
    ESCAPE_FLAG = 0x5E                  # Escaped flag byte (0x7E)
    ESCAPE_ESC = 0x5D                   # Escaped escape byte (0x7D)
    
    # GDL-90 message types
    MSG_ADSB_LONG = 0x26                # ADS-B Long Report (our target)
    
    # Minimum ADS-B payload length after deframing
    MIN_ADSB_PAYLOAD_LENGTH = 14        # 14 bytes = 112 bits (minimum)
    MAX_ADSB_PAYLOAD_LENGTH = 18        # Maximum reasonable length
    
    def __init__(self):
        """Initialize the GDL-90 deframer"""
        self.frames_processed = 0
        self.frames_extracted = 0
        self.adsb_messages_found = 0
        self.deframing_errors = 0
        self.byte_unstuff_operations = 0
        
    def deframe_message(self, raw_data: bytes) -> List[bytes]:
        """
        Extract ADS-B messages from GDL-90 wrapped data
        
        Args:
            raw_data: Raw UDP data containing GDL-90 frames
            
        Returns:
            List of extracted ADS-B message bytes
        """
        if not raw_data:
            return []
            
        if config.LOG_DEFRAMING_PROCESS:
            logger.debug(f"[GDL90] Processing {len(raw_data)} bytes: {raw_data.hex()}")
        
        adsb_messages = []
        
        try:
            # Find all frame boundaries in the data
            frame_boundaries = self._find_frame_boundaries(raw_data)
            
            if config.LOG_DEFRAMING_PROCESS:
                logger.info(f"[GDL90] Found {len(frame_boundaries)} frames")
            
            # Process each frame
            for start_pos, end_pos in frame_boundaries:
                self.frames_processed += 1
                
                # Extract frame content (excluding flags)
                frame_data = raw_data[start_pos + 1:end_pos]
                
                if config.LOG_DEFRAMING_PROCESS:
                    logger.debug(f"[GDL90] Frame {self.frames_processed}: {frame_data.hex()}")
                
                # Unstuff bytes (KISS/HDLC protocol)
                unstuffed_data = self._unstuff_bytes(frame_data)
                
                if not unstuffed_data:
                    continue
                    
                # Extract ADS-B payload if this is an ADS-B frame
                adsb_payload = self._extract_adsb_payload(unstuffed_data)
                
                if adsb_payload:
                    self.adsb_messages_found += 1
                    adsb_messages.append(adsb_payload)
                    
                    if config.LOG_DEFRAMING_PROCESS:
                        logger.info(f"[GDL90] Extracted ADS-B payload: {adsb_payload.hex()}")
                        
            self.frames_extracted += len(adsb_messages)
            
        except Exception as e:
            self.deframing_errors += 1
            if config.LOG_DEFRAMING_PROCESS:
                logger.error(f"[GDL90] Deframing error: {e}")
        
        return adsb_messages
    
    def _find_frame_boundaries(self, data: bytes) -> List[Tuple[int, int]]:
        """
        Find GDL-90 frame boundaries marked by 0x7E flags
        
        Args:
            data: Raw data to search
            
        Returns:
            List of (start_pos, end_pos) tuples for each frame
        """
        boundaries = []
        start_pos = None
        
        for i, byte_val in enumerate(data):
            if byte_val == self.FLAG_BYTE:
                if start_pos is None:
                    # Found frame start
                    start_pos = i
                else:
                    # Found frame end
                    if i > start_pos + 1:  # Must have content between flags
                        boundaries.append((start_pos, i))
                    start_pos = i  # This end flag could be start of next frame
        
        return boundaries
    
    def _unstuff_bytes(self, frame_data: bytes) -> Optional[bytes]:
        """
        Remove KISS/HDLC byte stuffing from frame data
        
        KISS stuffing rules:
        - 0x7D 0x5E → 0x7E (escaped flag)
        - 0x7D 0x5D → 0x7D (escaped escape)
        
        Args:
            frame_data: Frame content between flags
            
        Returns:
            Unstuffed bytes or None if error
        """
        if not frame_data:
            return None
            
        unstuffed = bytearray()
        i = 0
        
        while i < len(frame_data):
            if frame_data[i] == self.ESCAPE_BYTE and i + 1 < len(frame_data):
                # Found escape sequence
                next_byte = frame_data[i + 1]
                
                if next_byte == self.ESCAPE_FLAG:
                    # 0x7D 0x5E → 0x7E
                    unstuffed.append(self.FLAG_BYTE)
                    self.byte_unstuff_operations += 1
                    i += 2
                elif next_byte == self.ESCAPE_ESC:
                    # 0x7D 0x5D → 0x7D
                    unstuffed.append(self.ESCAPE_BYTE)
                    self.byte_unstuff_operations += 1
                    i += 2
                else:
                    # Invalid escape sequence, but continue
                    unstuffed.append(frame_data[i])
                    i += 1
            else:
                # Normal byte
                unstuffed.append(frame_data[i])
                i += 1
        
        return bytes(unstuffed)
    
    def _extract_adsb_payload(self, unstuffed_data: bytes) -> Optional[bytes]:
        """
        Extract ADS-B payload from GDL-90 message
        
        GDL-90 ADS-B Long Report structure:
        Byte 0: Message ID (0x26)
        Byte 1: Sub-ID/Length (0x00)
        Bytes 2-15: 14-byte ADS-B payload
        
        Args:
            unstuffed_data: Unstuffed frame data
            
        Returns:
            14-byte ADS-B payload or None if not ADS-B or invalid
        """
        if len(unstuffed_data) < 2:
            return None
            
        # Check if this is an ADS-B Long Report
        msg_id = unstuffed_data[0]
        
        if msg_id != self.MSG_ADSB_LONG:
            if config.LOG_DEFRAMING_PROCESS:
                logger.warning(f"[GDL90] Skipping non-ADS-B message type: 0x{msg_id:02X}")
            return None
        
        # Extract ADS-B payload (skip 2-byte header, use remaining data)
        if len(unstuffed_data) < 2 + self.MIN_ADSB_PAYLOAD_LENGTH:
            if config.LOG_DEFRAMING_PROCESS:
                logger.warning(f"[GDL90] ADS-B frame too short: {len(unstuffed_data)} bytes")
            return None
        
        # Use all remaining data after header as payload
        adsb_payload = unstuffed_data[2:]
        
        # Validate payload length is reasonable
        if len(adsb_payload) > self.MAX_ADSB_PAYLOAD_LENGTH:
            if config.LOG_DEFRAMING_PROCESS:
                logger.warning(f"[GDL90] ADS-B payload too long: {len(adsb_payload)} bytes")
            return None
        
        # Validate payload
        if self._validate_adsb_message(adsb_payload):
            return adsb_payload
        else:
            if config.LOG_DEFRAMING_PROCESS:
                logger.error(f"[GDL90] Invalid ADS-B payload: {adsb_payload.hex()}")
            return None
    
    def _validate_adsb_message(self, payload: bytes) -> bool:
        """
        Basic validation of ADS-B message payload
        
        Args:
            payload: 14-byte ADS-B message
            
        Returns:
            True if payload appears valid
        """
        if len(payload) < self.MIN_ADSB_PAYLOAD_LENGTH or len(payload) > self.MAX_ADSB_PAYLOAD_LENGTH:
            return False
            
        # Check if first byte looks like a valid DF
        # ADS-B should have DF=17 (10001xxx) or similar
        first_byte = payload[0]
        df = (first_byte >> 3) & 0x1F  # Extract DF from first 5 bits
        
        # Valid ADS-B downlink formats
        valid_dfs = [17, 18, 19]  # DF 17=ADS-B, 18=TIS-B, 19=Military
        
        return df in valid_dfs
    
    def is_gdl90_frame(self, data: bytes) -> bool:
        """
        Check if data appears to be GDL-90 wrapped
        
        Args:
            data: Raw data to check
            
        Returns:
            True if data looks like GDL-90 format
        """
        if len(data) < 4:
            return False
            
        # Look for frame start and reasonable structure
        return (data[0] == self.FLAG_BYTE and 
                data[-1] == self.FLAG_BYTE and
                len(data) > 10)  # Minimum reasonable frame size
    
    def get_stats(self) -> dict:
        """
        Get deframing statistics
        
        Returns:
            Dictionary of statistics
        """
        return {
            'frames_processed': self.frames_processed,
            'frames_extracted': self.frames_extracted,
            'adsb_messages_found': self.adsb_messages_found,
            'deframing_errors': self.deframing_errors,
            'byte_unstuff_operations': self.byte_unstuff_operations,
            'success_rate': round((self.adsb_messages_found / max(1, self.frames_processed)) * 100, 1)
        }
    
    def reset_stats(self):
        """Reset statistics counters"""
        self.frames_processed = 0
        self.frames_extracted = 0
        self.adsb_messages_found = 0
        self.deframing_errors = 0
        self.byte_unstuff_operations = 0


# Convenience function for standalone use
def deframe_gdl90_data(raw_data: bytes) -> List[bytes]:
    """
    Convenience function to deframe GDL-90 data
    
    Args:
        raw_data: Raw GDL-90 data
        
    Returns:
        List of extracted ADS-B messages
    """
    deframer = GDL90Deframer()
    return deframer.deframe_message(raw_data)


if __name__ == "__main__":
    # Test with sample data if run directly
    sample_gdl90 = bytes.fromhex("7E 26 00 8B 9A 7D 5E 47 99 67 CC D9 C8 2B 84 D1 FF EB CC A0 7E")
    
    logger.info("Testing GDL-90 deframer with sample data")
    logger.debug(f"Input:  {sample_gdl90.hex()}")
    
    deframer = GDL90Deframer()
    messages = deframer.deframe_message(sample_gdl90)
    
    for i, msg in enumerate(messages):
        logger.debug(f"Output {i+1}: {msg.hex()}")
        
        # Check DF
        df = (msg[0] >> 3) & 0x1F
        logger.debug(f"         DF: {df}")
    
    logger.info(f"Stats: {deframer.get_stats()}")