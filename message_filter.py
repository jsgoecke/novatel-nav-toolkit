"""
Message Filter for UDP Replay System
Provides filtering capabilities for binary messages
"""

import re
from typing import List, Callable, Dict, Any, Optional, Tuple
from logger import logger
import config


class MessageFilter:
    """Filter messages based on various criteria"""
    
    def __init__(self):
        self.filters: List[Callable[[bytes, int], bool]] = []
        self.filter_stats = {
            'messages_processed': 0,
            'messages_passed': 0,
            'messages_filtered': 0,
            'filter_reasons': {}
        }
        self.active_filters = []
    
    def add_size_filter(self, min_size: int = 0, max_size: int = float('inf'), name: str = None) -> None:
        """
        Add size-based filter
        
        Args:
            min_size: Minimum message size in bytes
            max_size: Maximum message size in bytes
            name: Optional name for this filter
        """
        filter_name = name or f"size_{min_size}_{max_size}"
        
        def size_filter(data: bytes, msg_num: int) -> bool:
            passed = min_size <= len(data) <= max_size
            if not passed:
                self._record_filter_reason(filter_name, f"Size {len(data)} not in range [{min_size}, {max_size}]")
            return passed
        
        self.filters.append(size_filter)
        self.active_filters.append({
            'type': 'size',
            'name': filter_name,
            'min_size': min_size,
            'max_size': max_size
        })
        
        logger.info(f"Added size filter: {min_size} <= size <= {max_size}")
    
    def add_pattern_filter(self, pattern: bytes, match_type: str = 'starts_with', name: str = None) -> None:
        """
        Add pattern-based filter
        
        Args:
            pattern: Binary pattern to match
            match_type: Type of matching ('starts_with', 'ends_with', 'contains', 'exact')
            name: Optional name for this filter
        """
        filter_name = name or f"pattern_{pattern.hex()[:8]}_{match_type}"
        
        def pattern_filter(data: bytes, msg_num: int) -> bool:
            if match_type == 'starts_with':
                passed = data.startswith(pattern)
            elif match_type == 'ends_with':
                passed = data.endswith(pattern)
            elif match_type == 'contains':
                passed = pattern in data
            elif match_type == 'exact':
                passed = data == pattern
            else:
                logger.warning(f"Unknown pattern match type: {match_type}")
                passed = True
            
            if not passed:
                self._record_filter_reason(filter_name, f"Pattern {pattern.hex()} not found ({match_type})")
            return passed
        
        self.filters.append(pattern_filter)
        self.active_filters.append({
            'type': 'pattern',
            'name': filter_name,
            'pattern': pattern.hex(),
            'match_type': match_type
        })
        
        logger.info(f"Added pattern filter: {pattern.hex()} ({match_type})")
    
    def add_hex_pattern_filter(self, hex_pattern: str, match_type: str = 'starts_with', name: str = None) -> None:
        """
        Add hex pattern filter (convenience method)
        
        Args:
            hex_pattern: Hex string pattern (e.g., "AA4412")
            match_type: Type of matching
            name: Optional name for this filter
        """
        # Clean up hex pattern
        hex_pattern = hex_pattern.replace(' ', '').replace('0x', '').upper()
        try:
            pattern_bytes = bytes.fromhex(hex_pattern)
            self.add_pattern_filter(pattern_bytes, match_type, name)
        except ValueError as e:
            logger.error(f"Invalid hex pattern '{hex_pattern}': {e}")
    
    def add_protocol_filter(self, protocol: str, name: str = None) -> None:
        """
        Add protocol-based filter
        
        Args:
            protocol: Protocol type ('nmea', 'adsb', 'novatel', 'ascii')
            name: Optional name for this filter
        """
        filter_name = name or f"protocol_{protocol}"
        
        def protocol_filter(data: bytes, msg_num: int) -> bool:
            detected_protocol = self._detect_simple_protocol(data)
            passed = detected_protocol == protocol.lower()
            
            if not passed:
                self._record_filter_reason(filter_name, f"Protocol {detected_protocol} != {protocol}")
            return passed
        
        self.filters.append(protocol_filter)
        self.active_filters.append({
            'type': 'protocol',
            'name': filter_name,
            'protocol': protocol
        })
        
        logger.info(f"Added protocol filter: {protocol}")
    
    def add_corruption_filter(self, skip_corrupted: bool = True, name: str = None) -> None:
        """
        Add corruption detection filter
        
        Args:
            skip_corrupted: If True, filter out corrupted messages
            name: Optional name for this filter
        """
        filter_name = name or f"corruption_{skip_corrupted}"
        
        def corruption_filter(data: bytes, msg_num: int) -> bool:
            is_corrupted = self._detect_corruption(data)
            passed = not (skip_corrupted and is_corrupted)
            
            if not passed:
                self._record_filter_reason(filter_name, "Message appears corrupted")
            return passed
        
        self.filters.append(corruption_filter)
        self.active_filters.append({
            'type': 'corruption',
            'name': filter_name,
            'skip_corrupted': skip_corrupted
        })
        
        logger.info(f"Added corruption filter: skip_corrupted={skip_corrupted}")
    
    def add_custom_filter(self, filter_func: Callable[[bytes, int], bool], name: str, description: str = "") -> None:
        """
        Add custom filter function
        
        Args:
            filter_func: Function that takes (bytes, message_number) and returns bool
            name: Name for this filter
            description: Optional description
        """
        def custom_filter(data: bytes, msg_num: int) -> bool:
            try:
                passed = filter_func(data, msg_num)
                if not passed:
                    self._record_filter_reason(name, "Custom filter rejected message")
                return passed
            except Exception as e:
                logger.error(f"Error in custom filter '{name}': {e}")
                return True  # Pass through on error
        
        self.filters.append(custom_filter)
        self.active_filters.append({
            'type': 'custom',
            'name': name,
            'description': description
        })
        
        logger.info(f"Added custom filter: {name} - {description}")
    
    def add_message_number_filter(self, start_msg: int = 0, end_msg: int = None, name: str = None) -> None:
        """
        Add message number range filter
        
        Args:
            start_msg: Starting message number (inclusive)
            end_msg: Ending message number (inclusive), None for no limit
            name: Optional name for this filter
        """
        filter_name = name or f"msg_range_{start_msg}_{end_msg or 'end'}"
        
        def msg_number_filter(data: bytes, msg_num: int) -> bool:
            if msg_num < start_msg:
                passed = False
                reason = f"Message {msg_num} < start {start_msg}"
            elif end_msg is not None and msg_num > end_msg:
                passed = False
                reason = f"Message {msg_num} > end {end_msg}"
            else:
                passed = True
                reason = None
            
            if not passed:
                self._record_filter_reason(filter_name, reason)
            return passed
        
        self.filters.append(msg_number_filter)
        self.active_filters.append({
            'type': 'message_number',
            'name': filter_name,
            'start_msg': start_msg,
            'end_msg': end_msg
        })
        
        logger.info(f"Added message number filter: {start_msg} to {end_msg or 'end'}")
    
    def apply_filters(self, data: bytes, message_number: int) -> Tuple[bool, List[str]]:
        """
        Apply all active filters to a message
        
        Args:
            data: Binary message data
            message_number: Sequential message number
            
        Returns:
            Tuple of (passed_all_filters, list_of_failed_filter_names)
        """
        self.filter_stats['messages_processed'] += 1
        failed_filters = []
        
        # If no filters are active, pass everything
        if not self.filters:
            self.filter_stats['messages_passed'] += 1
            return True, []
        
        # Apply each filter
        for i, filter_func in enumerate(self.filters):
            try:
                if not filter_func(data, message_number):
                    failed_filters.append(self.active_filters[i]['name'])
            except Exception as e:
                logger.error(f"Error applying filter {i}: {e}")
                # Continue with other filters
        
        passed = len(failed_filters) == 0
        
        if passed:
            self.filter_stats['messages_passed'] += 1
        else:
            self.filter_stats['messages_filtered'] += 1
        
        return passed, failed_filters
    
    def clear_filters(self) -> None:
        """Clear all active filters"""
        self.filters.clear()
        self.active_filters.clear()
        logger.info("All filters cleared")
    
    def get_filter_stats(self) -> Dict[str, Any]:
        """Get filtering statistics"""
        stats = self.filter_stats.copy()
        if stats['messages_processed'] > 0:
            stats['pass_rate'] = (stats['messages_passed'] / stats['messages_processed']) * 100
        else:
            stats['pass_rate'] = 0
        
        stats['active_filter_count'] = len(self.filters)
        stats['active_filters'] = self.active_filters.copy()
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset filtering statistics"""
        self.filter_stats = {
            'messages_processed': 0,
            'messages_passed': 0,
            'messages_filtered': 0,
            'filter_reasons': {}
        }
        logger.info("Filter statistics reset")
    
    def _record_filter_reason(self, filter_name: str, reason: str) -> None:
        """Record why a filter rejected a message"""
        if filter_name not in self.filter_stats['filter_reasons']:
            self.filter_stats['filter_reasons'][filter_name] = []
        
        self.filter_stats['filter_reasons'][filter_name].append(reason)
        
        # Keep only the last 10 reasons per filter to avoid memory bloat
        if len(self.filter_stats['filter_reasons'][filter_name]) > 10:
            self.filter_stats['filter_reasons'][filter_name] = \
                self.filter_stats['filter_reasons'][filter_name][-10:]
    
    def _detect_simple_protocol(self, data: bytes) -> str:
        """Simple protocol detection for filtering"""
        if len(data) == 0:
            return 'empty'
        
        # Check for NMEA
        if data.startswith(b'$GP') or data.startswith(b'$GN') or data.startswith(b'$GL'):
            return 'nmea'
        
        # Check for Novatel
        if data.startswith(b'\xaa\x44\x12\x1c'):
            return 'novatel'
        
        # Check if mostly ASCII
        try:
            text = data.decode('ascii')
            if len([c for c in text if c.isprintable()]) / len(text) > 0.8:
                return 'ascii'
        except UnicodeDecodeError:
            pass
        
        # Assume binary (could be ADS-B)
        return 'binary'
    
    def _detect_corruption(self, data: bytes) -> bool:
        """Simple corruption detection"""
        if len(data) == 0:
            return True
        
        # Check for excessive null bytes
        null_ratio = data.count(0) / len(data)
        if null_ratio > 0.5:
            return True
        
        # Check for repeated byte patterns (potential corruption)
        if len(data) > 10:
            for byte_val in range(256):
                if data.count(byte_val) / len(data) > 0.8:
                    return True
        
        return False
    
    def get_filter_summary(self) -> str:
        """Get a summary of active filters"""
        if not self.active_filters:
            return "No filters active - all messages will pass through"
        
        lines = [f"Active Filters ({len(self.active_filters)}):"]
        for i, filter_info in enumerate(self.active_filters, 1):
            if filter_info['type'] == 'size':
                lines.append(f"  {i}. Size: {filter_info['min_size']} - {filter_info['max_size']} bytes")
            elif filter_info['type'] == 'pattern':
                lines.append(f"  {i}. Pattern: {filter_info['pattern']} ({filter_info['match_type']})")
            elif filter_info['type'] == 'protocol':
                lines.append(f"  {i}. Protocol: {filter_info['protocol']}")
            elif filter_info['type'] == 'corruption':
                lines.append(f"  {i}. Corruption: skip={filter_info['skip_corrupted']}")
            elif filter_info['type'] == 'message_number':
                lines.append(f"  {i}. Message Range: {filter_info['start_msg']} - {filter_info['end_msg']}")
            elif filter_info['type'] == 'custom':
                lines.append(f"  {i}. Custom: {filter_info['name']} - {filter_info['description']}")
        
        return "\n".join(lines)


def create_filter_from_config() -> MessageFilter:
    """Create a message filter from configuration settings"""
    filter_obj = MessageFilter()
    
    # Add size filter if configured
    if hasattr(config, 'REPLAY_FILTER_MIN_SIZE') and hasattr(config, 'REPLAY_FILTER_MAX_SIZE'):
        if config.REPLAY_FILTER_MIN_SIZE > 0 or config.REPLAY_FILTER_MAX_SIZE < float('inf'):
            filter_obj.add_size_filter(
                min_size=config.REPLAY_FILTER_MIN_SIZE,
                max_size=config.REPLAY_FILTER_MAX_SIZE,
                name="config_size"
            )
    
    # Add pattern filters if configured
    if hasattr(config, 'REPLAY_FILTER_PATTERNS') and config.REPLAY_FILTER_PATTERNS:
        for i, pattern in enumerate(config.REPLAY_FILTER_PATTERNS):
            if isinstance(pattern, str):
                filter_obj.add_hex_pattern_filter(pattern, name=f"config_pattern_{i}")
            elif isinstance(pattern, bytes):
                filter_obj.add_pattern_filter(pattern, name=f"config_pattern_{i}")
    
    # Add corruption filter if configured
    if hasattr(config, 'REPLAY_SKIP_CORRUPTED') and config.REPLAY_SKIP_CORRUPTED:
        filter_obj.add_corruption_filter(skip_corrupted=True, name="config_corruption")
    
    return filter_obj