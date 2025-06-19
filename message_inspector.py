"""
Message Inspector for UDP Replay System
Provides detailed analysis and inspection of binary messages
"""

import struct
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import config
from logger import logger


class MessageInspector:
    """Detailed analysis and inspection of binary messages"""
    
    def __init__(self):
        self.inspection_count = 0
        self.protocol_signatures = {
            'nmea': [b'$GP', b'$GN', b'$GL', b'$GA'],
            'novatel': [b'\xaa\x44\x12\x1c'],  # Novatel sync pattern
            'adsb': []  # ADS-B doesn't have a fixed signature
        }
    
    def inspect_message(self, binary_data: bytes, message_number: int = 0) -> Dict[str, Any]:
        """
        Perform comprehensive inspection of a binary message
        
        Args:
            binary_data: Raw binary message data
            message_number: Sequential message number for tracking
            
        Returns:
            Dictionary containing inspection results
        """
        self.inspection_count += 1
        
        inspection_result = {
            'message_number': message_number,
            'timestamp': datetime.utcnow().isoformat(),
            'size_bytes': len(binary_data),
            'hex_data': binary_data.hex().upper(),
            'protocol_detected': self.detect_protocol(binary_data),
            'structure_analysis': self.analyze_structure(binary_data),
            'ascii_preview': self.get_ascii_preview(binary_data),
            'checksum_info': self.analyze_checksum(binary_data),
            'data_patterns': self.find_data_patterns(binary_data)
        }
        
        logger.info(f"Message inspection #{self.inspection_count} completed for message {message_number}")
        return inspection_result
    
    def hex_dump(self, binary_data: bytes, bytes_per_line: int = 16, show_ascii: bool = True) -> str:
        """
        Generate hexadecimal dump of binary data
        
        Args:
            binary_data: Raw binary data
            bytes_per_line: Number of bytes to display per line
            show_ascii: Whether to show ASCII representation
            
        Returns:
            Formatted hex dump string
        """
        lines = []
        
        for i in range(0, len(binary_data), bytes_per_line):
            chunk = binary_data[i:i + bytes_per_line]
            
            # Offset
            offset = f"{i:08X}"
            
            # Hex bytes
            hex_bytes = " ".join(f"{b:02X}" for b in chunk)
            hex_bytes = hex_bytes.ljust(bytes_per_line * 3 - 1)
            
            # ASCII representation
            if show_ascii:
                ascii_repr = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)
                line = f"{offset}  {hex_bytes}  |{ascii_repr}|"
            else:
                line = f"{offset}  {hex_bytes}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def get_ascii_preview(self, binary_data: bytes, max_length: int = 100) -> str:
        """
        Get ASCII preview of binary data
        
        Args:
            binary_data: Raw binary data
            max_length: Maximum length of preview
            
        Returns:
            ASCII preview string
        """
        preview_data = binary_data[:max_length]
        ascii_chars = []
        
        for byte in preview_data:
            if 32 <= byte <= 126:  # Printable ASCII
                ascii_chars.append(chr(byte))
            elif byte == 0:
                ascii_chars.append('\\0')
            elif byte == 10:
                ascii_chars.append('\\n')
            elif byte == 13:
                ascii_chars.append('\\r')
            else:
                ascii_chars.append(f'\\x{byte:02x}')
        
        result = "".join(ascii_chars)
        if len(binary_data) > max_length:
            result += "..."
        
        return result
    
    def detect_protocol(self, binary_data: bytes) -> str:
        """
        Attempt to detect the protocol of the binary message
        
        Args:
            binary_data: Raw binary data
            
        Returns:
            Detected protocol name or 'unknown'
        """
        if len(binary_data) == 0:
            return 'empty'
        
        # Check for NMEA
        for signature in self.protocol_signatures['nmea']:
            if binary_data.startswith(signature):
                return 'nmea'
        
        # Check for Novatel
        for signature in self.protocol_signatures['novatel']:
            if binary_data.startswith(signature):
                return 'novatel'
        
        # Check if it's ASCII text (likely NMEA without $ prefix)
        try:
            text = binary_data.decode('ascii')
            if text.startswith('GP') or text.startswith('GN') or text.startswith('GL'):
                return 'nmea_ascii'
        except UnicodeDecodeError:
            pass
        
        # Check for common ADS-B patterns
        if len(binary_data) in [7, 14]:  # Common ADS-B message lengths
            return 'adsb_candidate'
        
        return 'unknown'
    
    def analyze_structure(self, binary_data: bytes) -> Dict[str, Any]:
        """
        Analyze the structure of the binary message
        
        Args:
            binary_data: Raw binary data
            
        Returns:
            Dictionary containing structure analysis
        """
        analysis = {
            'length': len(binary_data),
            'header_bytes': binary_data[:4].hex().upper() if len(binary_data) >= 4 else binary_data.hex().upper(),
            'trailer_bytes': binary_data[-4:].hex().upper() if len(binary_data) >= 4 else binary_data.hex().upper(),
            'null_bytes': binary_data.count(0),
            'printable_bytes': sum(1 for b in binary_data if 32 <= b <= 126),
            'control_bytes': sum(1 for b in binary_data if b < 32),
            'high_bytes': sum(1 for b in binary_data if b > 126)
        }
        
        # Calculate percentages
        if len(binary_data) > 0:
            analysis['printable_percentage'] = (analysis['printable_bytes'] / len(binary_data)) * 100
            analysis['null_percentage'] = (analysis['null_bytes'] / len(binary_data)) * 100
        else:
            analysis['printable_percentage'] = 0
            analysis['null_percentage'] = 0
        
        return analysis
    
    def analyze_checksum(self, binary_data: bytes) -> Dict[str, Any]:
        """
        Analyze potential checksum information
        
        Args:
            binary_data: Raw binary data
            
        Returns:
            Dictionary containing checksum analysis
        """
        checksum_info = {
            'has_potential_checksum': False,
            'checksum_type': 'unknown',
            'checksum_value': None,
            'calculated_checksum': None,
            'checksum_valid': False
        }
        
        if len(binary_data) < 2:
            return checksum_info
        
        # Check for NMEA checksum (asterisk followed by 2 hex digits)
        try:
            text = binary_data.decode('ascii', errors='ignore')
            if '*' in text:
                checksum_pos = text.rfind('*')
                if checksum_pos >= 0 and len(text) >= checksum_pos + 3:
                    checksum_str = text[checksum_pos + 1:checksum_pos + 3]
                    if all(c in '0123456789ABCDEFabcdef' for c in checksum_str):
                        checksum_info['has_potential_checksum'] = True
                        checksum_info['checksum_type'] = 'nmea'
                        checksum_info['checksum_value'] = checksum_str.upper()
                        
                        # Calculate NMEA checksum
                        message_part = text[1:checksum_pos] if text.startswith('$') else text[:checksum_pos]
                        calculated = 0
                        for char in message_part:
                            calculated ^= ord(char)
                        checksum_info['calculated_checksum'] = f"{calculated:02X}"
                        checksum_info['checksum_valid'] = checksum_info['checksum_value'] == checksum_info['calculated_checksum']
        except UnicodeDecodeError:
            pass
        
        # Check for simple byte checksum (last byte)
        if not checksum_info['has_potential_checksum'] and len(binary_data) > 1:
            potential_checksum = binary_data[-1]
            calculated_sum = sum(binary_data[:-1]) & 0xFF
            if potential_checksum == calculated_sum:
                checksum_info['has_potential_checksum'] = True
                checksum_info['checksum_type'] = 'simple_sum'
                checksum_info['checksum_value'] = f"{potential_checksum:02X}"
                checksum_info['calculated_checksum'] = f"{calculated_sum:02X}"
                checksum_info['checksum_valid'] = True
        
        return checksum_info
    
    def find_data_patterns(self, binary_data: bytes) -> List[Dict[str, Any]]:
        """
        Find interesting data patterns in the binary message
        
        Args:
            binary_data: Raw binary data
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        # Look for repeating byte patterns
        for pattern_length in [1, 2, 4]:
            if len(binary_data) >= pattern_length * 3:  # At least 3 repetitions
                for i in range(len(binary_data) - pattern_length * 3 + 1):
                    pattern = binary_data[i:i + pattern_length]
                    repetitions = 1
                    j = i + pattern_length
                    
                    while j + pattern_length <= len(binary_data) and binary_data[j:j + pattern_length] == pattern:
                        repetitions += 1
                        j += pattern_length
                    
                    if repetitions >= 3:
                        patterns.append({
                            'type': 'repeating_bytes',
                            'pattern': pattern.hex().upper(),
                            'repetitions': repetitions,
                            'start_offset': i,
                            'total_length': repetitions * pattern_length
                        })
        
        # Look for null-terminated strings
        null_pos = 0
        while null_pos < len(binary_data):
            try:
                next_null = binary_data.index(0, null_pos)
                if next_null > null_pos:
                    string_data = binary_data[null_pos:next_null]
                    if len(string_data) > 3 and all(32 <= b <= 126 for b in string_data):
                        patterns.append({
                            'type': 'null_terminated_string',
                            'string': string_data.decode('ascii'),
                            'start_offset': null_pos,
                            'length': len(string_data)
                        })
                null_pos = next_null + 1
            except ValueError:
                break
        
        # Look for potential floating point numbers
        if len(binary_data) >= 4:
            for i in range(0, len(binary_data) - 3, 4):
                try:
                    float_val = struct.unpack('<f', binary_data[i:i+4])[0]
                    if not (float_val != float_val):  # Check for NaN
                        if -1000000 < float_val < 1000000:  # Reasonable range
                            patterns.append({
                                'type': 'potential_float',
                                'value': float_val,
                                'start_offset': i,
                                'endianness': 'little'
                            })
                except struct.error:
                    pass
                
                try:
                    float_val = struct.unpack('>f', binary_data[i:i+4])[0]
                    if not (float_val != float_val):  # Check for NaN
                        if -1000000 < float_val < 1000000:  # Reasonable range
                            patterns.append({
                                'type': 'potential_float',
                                'value': float_val,
                                'start_offset': i,
                                'endianness': 'big'
                            })
                except struct.error:
                    pass
        
        return patterns
    
    def get_inspection_stats(self) -> Dict[str, int]:
        """
        Get statistics about inspections performed
        
        Returns:
            Dictionary containing inspection statistics
        """
        return {
            'total_inspections': self.inspection_count
        }
    
    def format_inspection_report(self, inspection_result: Dict[str, Any]) -> str:
        """
        Format an inspection result into a readable report
        
        Args:
            inspection_result: Result from inspect_message()
            
        Returns:
            Formatted report string
        """
        report_lines = []
        
        report_lines.append("=" * 60)
        report_lines.append(f"MESSAGE INSPECTION REPORT #{inspection_result['message_number']}")
        report_lines.append("=" * 60)
        
        report_lines.append(f"Timestamp: {inspection_result['timestamp']}")
        report_lines.append(f"Size: {inspection_result['size_bytes']} bytes")
        report_lines.append(f"Protocol: {inspection_result['protocol_detected']}")
        
        report_lines.append("\nSTRUCTURE ANALYSIS:")
        report_lines.append("-" * 30)
        structure = inspection_result['structure_analysis']
        report_lines.append(f"Header: {structure['header_bytes']}")
        report_lines.append(f"Trailer: {structure['trailer_bytes']}")
        report_lines.append(f"Printable bytes: {structure['printable_bytes']} ({structure['printable_percentage']:.1f}%)")
        report_lines.append(f"Null bytes: {structure['null_bytes']} ({structure['null_percentage']:.1f}%)")
        
        if inspection_result['checksum_info']['has_potential_checksum']:
            report_lines.append(f"\nCHECKSUM INFO:")
            report_lines.append("-" * 30)
            cs_info = inspection_result['checksum_info']
            report_lines.append(f"Type: {cs_info['checksum_type']}")
            report_lines.append(f"Value: {cs_info['checksum_value']}")
            report_lines.append(f"Calculated: {cs_info['calculated_checksum']}")
            report_lines.append(f"Valid: {cs_info['checksum_valid']}")
        
        if inspection_result['data_patterns']:
            report_lines.append(f"\nDATA PATTERNS:")
            report_lines.append("-" * 30)
            for pattern in inspection_result['data_patterns']:
                if pattern['type'] == 'repeating_bytes':
                    report_lines.append(f"Repeating pattern '{pattern['pattern']}' x{pattern['repetitions']} at offset {pattern['start_offset']}")
                elif pattern['type'] == 'null_terminated_string':
                    report_lines.append(f"String '{pattern['string']}' at offset {pattern['start_offset']}")
                elif pattern['type'] == 'potential_float':
                    report_lines.append(f"Potential float {pattern['value']:.6f} ({pattern['endianness']}) at offset {pattern['start_offset']}")
        
        report_lines.append(f"\nASCII PREVIEW:")
        report_lines.append("-" * 30)
        report_lines.append(inspection_result['ascii_preview'])
        
        if len(inspection_result['hex_data']) <= 200:  # Show hex for small messages
            report_lines.append(f"\nHEX DATA:")
            report_lines.append("-" * 30)
            report_lines.append(inspection_result['hex_data'])
        
        report_lines.append("=" * 60)
        
        return "\n".join(report_lines)