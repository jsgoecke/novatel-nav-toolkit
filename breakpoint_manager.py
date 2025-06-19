"""
Breakpoint Manager for UDP Replay System
Provides advanced debugging with conditional stopping points
"""

from typing import List, Callable, Dict, Any, Optional, Set
from datetime import datetime
from logger import logger
from message_inspector import MessageInspector


class BreakpointManager:
    """Advanced debugging with conditional stopping points"""
    
    def __init__(self, inspector: Optional[MessageInspector] = None):
        self.inspector = inspector or MessageInspector()
        self.breakpoints: List[Dict[str, Any]] = []
        self.hit_breakpoints: List[Dict[str, Any]] = []
        self.enabled = True
        self.stats = {
            'total_checks': 0,
            'breakpoints_hit': 0,
            'messages_stopped': 0
        }
    
    def add_error_breakpoint(self, name: str = "parse_errors") -> int:
        """
        Add breakpoint that triggers on parsing errors
        
        Args:
            name: Name for this breakpoint
            
        Returns:
            Breakpoint ID
        """
        def error_condition(data: bytes, msg_num: int, context: Dict[str, Any]) -> bool:
            # Check if there was a parsing error
            return context.get('parse_error', False)
        
        return self._add_breakpoint(
            condition=error_condition,
            name=name,
            description="Stop on parsing errors",
            breakpoint_type="error"
        )
    
    def add_pattern_breakpoint(self, pattern: bytes, match_type: str = "contains", name: str = None) -> int:
        """
        Add breakpoint that triggers on specific binary patterns
        
        Args:
            pattern: Binary pattern to match
            match_type: Type of matching ('starts_with', 'ends_with', 'contains', 'exact')
            name: Optional name for this breakpoint
            
        Returns:
            Breakpoint ID
        """
        breakpoint_name = name or f"pattern_{pattern.hex()[:8]}_{match_type}"
        
        def pattern_condition(data: bytes, msg_num: int, context: Dict[str, Any]) -> bool:
            if match_type == 'starts_with':
                return data.startswith(pattern)
            elif match_type == 'ends_with':
                return data.endswith(pattern)
            elif match_type == 'contains':
                return pattern in data
            elif match_type == 'exact':
                return data == pattern
            else:
                logger.warning(f"Unknown pattern match type: {match_type}")
                return False
        
        return self._add_breakpoint(
            condition=pattern_condition,
            name=breakpoint_name,
            description=f"Stop on pattern {pattern.hex()} ({match_type})",
            breakpoint_type="pattern",
            pattern=pattern.hex(),
            match_type=match_type
        )
    
    def add_hex_pattern_breakpoint(self, hex_pattern: str, match_type: str = "contains", name: str = None) -> int:
        """
        Add breakpoint for hex pattern (convenience method)
        
        Args:
            hex_pattern: Hex string pattern (e.g., "AA4412")
            match_type: Type of matching
            name: Optional name for this breakpoint
            
        Returns:
            Breakpoint ID
        """
        # Clean up hex pattern
        hex_pattern = hex_pattern.replace(' ', '').replace('0x', '').upper()
        try:
            pattern_bytes = bytes.fromhex(hex_pattern)
            return self.add_pattern_breakpoint(pattern_bytes, match_type, name)
        except ValueError as e:
            logger.error(f"Invalid hex pattern '{hex_pattern}': {e}")
            return -1
    
    def add_count_breakpoint(self, success_count: int = None, error_count: int = None, name: str = None) -> int:
        """
        Add breakpoint that triggers after N successful or failed parses
        
        Args:
            success_count: Stop after this many successful parses
            error_count: Stop after this many parsing errors
            name: Optional name for this breakpoint
            
        Returns:
            Breakpoint ID
        """
        breakpoint_name = name or f"count_s{success_count}_e{error_count}"
        
        # Track counts in the breakpoint data
        bp_data = {
            'success_count': 0,
            'error_count': 0,
            'target_success': success_count,
            'target_error': error_count
        }
        
        def count_condition(data: bytes, msg_num: int, context: Dict[str, Any]) -> bool:
            # Update counts
            if context.get('parse_success', False):
                bp_data['success_count'] += 1
            if context.get('parse_error', False):
                bp_data['error_count'] += 1
            
            # Check if we've hit the target counts
            success_hit = (success_count is not None and bp_data['success_count'] >= success_count)
            error_hit = (error_count is not None and bp_data['error_count'] >= error_count)
            
            return success_hit or error_hit
        
        return self._add_breakpoint(
            condition=count_condition,
            name=breakpoint_name,
            description=f"Stop after {success_count} successes or {error_count} errors",
            breakpoint_type="count",
            custom_data=bp_data
        )
    
    def add_size_breakpoint(self, min_size: int = None, max_size: int = None, name: str = None) -> int:
        """
        Add breakpoint that triggers on message size
        
        Args:
            min_size: Stop on messages >= this size
            max_size: Stop on messages <= this size
            name: Optional name for this breakpoint
            
        Returns:
            Breakpoint ID
        """
        breakpoint_name = name or f"size_{min_size}_{max_size}"
        
        def size_condition(data: bytes, msg_num: int, context: Dict[str, Any]) -> bool:
            size = len(data)
            
            if min_size is not None and size >= min_size:
                return True
            if max_size is not None and size <= max_size:
                return True
            
            return False
        
        return self._add_breakpoint(
            condition=size_condition,
            name=breakpoint_name,
            description=f"Stop on size >= {min_size} or <= {max_size}",
            breakpoint_type="size",
            min_size=min_size,
            max_size=max_size
        )
    
    def add_protocol_breakpoint(self, protocol: str, name: str = None) -> int:
        """
        Add breakpoint that triggers on specific protocol detection
        
        Args:
            protocol: Protocol type to break on
            name: Optional name for this breakpoint
            
        Returns:
            Breakpoint ID
        """
        breakpoint_name = name or f"protocol_{protocol}"
        
        def protocol_condition(data: bytes, msg_num: int, context: Dict[str, Any]) -> bool:
            # Use inspector to detect protocol
            inspection = self.inspector.inspect_message(data, msg_num)
            detected = inspection['protocol_detected']
            return detected.lower() == protocol.lower()
        
        return self._add_breakpoint(
            condition=protocol_condition,
            name=breakpoint_name,
            description=f"Stop on protocol {protocol}",
            breakpoint_type="protocol",
            protocol=protocol
        )
    
    def add_custom_breakpoint(self, condition_func: Callable[[bytes, int, Dict[str, Any]], bool], 
                            name: str, description: str = "") -> int:
        """
        Add custom breakpoint with user-defined condition
        
        Args:
            condition_func: Function that takes (data, msg_num, context) and returns bool
            name: Name for this breakpoint
            description: Description of the breakpoint
            
        Returns:
            Breakpoint ID
        """
        return self._add_breakpoint(
            condition=condition_func,
            name=name,
            description=description or f"Custom breakpoint: {name}",
            breakpoint_type="custom"
        )
    
    def add_consecutive_errors_breakpoint(self, max_consecutive: int = 5, name: str = None) -> int:
        """
        Add breakpoint that triggers on consecutive parsing errors
        
        Args:
            max_consecutive: Stop after this many consecutive errors
            name: Optional name for this breakpoint
            
        Returns:
            Breakpoint ID
        """
        breakpoint_name = name or f"consecutive_errors_{max_consecutive}"
        
        # Track consecutive errors in breakpoint data
        bp_data = {'consecutive_errors': 0}
        
        def consecutive_errors_condition(data: bytes, msg_num: int, context: Dict[str, Any]) -> bool:
            if context.get('parse_error', False):
                bp_data['consecutive_errors'] += 1
                return bp_data['consecutive_errors'] >= max_consecutive
            else:
                bp_data['consecutive_errors'] = 0  # Reset on success
                return False
        
        return self._add_breakpoint(
            condition=consecutive_errors_condition,
            name=breakpoint_name,
            description=f"Stop on {max_consecutive} consecutive parsing errors",
            breakpoint_type="consecutive_errors",
            custom_data=bp_data,
            max_consecutive=max_consecutive
        )
    
    def check_breakpoints(self, data: bytes, message_number: int, context: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Check if any breakpoints should trigger
        
        Args:
            data: Binary message data
            message_number: Sequential message number
            context: Additional context (parsing results, etc.)
            
        Returns:
            Dict with breakpoint info if triggered, None otherwise
        """
        if not self.enabled or not self.breakpoints:
            return None
        
        context = context or {}
        self.stats['total_checks'] += 1
        
        for bp in self.breakpoints:
            if not bp['enabled']:
                continue
            
            try:
                if bp['condition'](data, message_number, context):
                    # Breakpoint hit!
                    hit_info = {
                        'breakpoint_id': bp['id'],
                        'name': bp['name'],
                        'description': bp['description'],
                        'type': bp['type'],
                        'message_number': message_number,
                        'timestamp': datetime.utcnow().isoformat(),
                        'message_size': len(data),
                        'context': context.copy()
                    }
                    
                    # Add breakpoint-specific data
                    for key, value in bp.items():
                        if key not in ['condition', 'id', 'enabled']:
                            hit_info[f'bp_{key}'] = value
                    
                    self.hit_breakpoints.append(hit_info)
                    self.stats['breakpoints_hit'] += 1
                    self.stats['messages_stopped'] += 1
                    
                    logger.info(f"Breakpoint '{bp['name']}' triggered at message {message_number}")
                    return hit_info
                    
            except Exception as e:
                logger.error(f"Error checking breakpoint '{bp['name']}': {e}")
                # Continue checking other breakpoints
        
        return None
    
    def enable_breakpoint(self, breakpoint_id: int) -> bool:
        """Enable a specific breakpoint"""
        for bp in self.breakpoints:
            if bp['id'] == breakpoint_id:
                bp['enabled'] = True
                logger.info(f"Enabled breakpoint {breakpoint_id}: {bp['name']}")
                return True
        return False
    
    def disable_breakpoint(self, breakpoint_id: int) -> bool:
        """Disable a specific breakpoint"""
        for bp in self.breakpoints:
            if bp['id'] == breakpoint_id:
                bp['enabled'] = False
                logger.info(f"Disabled breakpoint {breakpoint_id}: {bp['name']}")
                return True
        return False
    
    def remove_breakpoint(self, breakpoint_id: int) -> bool:
        """Remove a breakpoint completely"""
        for i, bp in enumerate(self.breakpoints):
            if bp['id'] == breakpoint_id:
                removed = self.breakpoints.pop(i)
                logger.info(f"Removed breakpoint {breakpoint_id}: {removed['name']}")
                return True
        return False
    
    def clear_all_breakpoints(self) -> int:
        """Clear all breakpoints"""
        count = len(self.breakpoints)
        self.breakpoints.clear()
        logger.info(f"Cleared all {count} breakpoints")
        return count
    
    def enable_all_breakpoints(self) -> None:
        """Enable all breakpoints"""
        for bp in self.breakpoints:
            bp['enabled'] = True
        logger.info("Enabled all breakpoints")
    
    def disable_all_breakpoints(self) -> None:
        """Disable all breakpoints"""
        for bp in self.breakpoints:
            bp['enabled'] = False
        logger.info("Disabled all breakpoints")
    
    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable the entire breakpoint system"""
        self.enabled = enabled
        logger.info(f"Breakpoint system {'enabled' if enabled else 'disabled'}")
    
    def get_breakpoint_list(self) -> List[Dict[str, Any]]:
        """Get list of all breakpoints"""
        return [{
            'id': bp['id'],
            'name': bp['name'],
            'description': bp['description'],
            'type': bp['type'],
            'enabled': bp['enabled']
        } for bp in self.breakpoints]
    
    def get_breakpoint_stats(self) -> Dict[str, Any]:
        """Get breakpoint statistics"""
        stats = self.stats.copy()
        stats['total_breakpoints'] = len(self.breakpoints)
        stats['enabled_breakpoints'] = sum(1 for bp in self.breakpoints if bp['enabled'])
        stats['disabled_breakpoints'] = len(self.breakpoints) - stats['enabled_breakpoints']
        stats['recent_hits'] = self.hit_breakpoints[-10:]  # Last 10 hits
        return stats
    
    def get_hit_history(self) -> List[Dict[str, Any]]:
        """Get history of breakpoint hits"""
        return self.hit_breakpoints.copy()
    
    def clear_hit_history(self) -> None:
        """Clear breakpoint hit history"""
        self.hit_breakpoints.clear()
        logger.info("Cleared breakpoint hit history")
    
    def format_breakpoint_report(self, hit_info: Dict[str, Any]) -> str:
        """Format a breakpoint hit into a readable report"""
        lines = []
        
        lines.append("=" * 60)
        lines.append(f"BREAKPOINT HIT: {hit_info['name']}")
        lines.append("=" * 60)
        
        lines.append(f"Timestamp: {hit_info['timestamp']}")
        lines.append(f"Message Number: {hit_info['message_number']}")
        lines.append(f"Message Size: {hit_info['message_size']} bytes")
        lines.append(f"Breakpoint Type: {hit_info['type']}")
        lines.append(f"Description: {hit_info['description']}")
        
        # Add type-specific information
        if hit_info['type'] == 'pattern':
            lines.append(f"Pattern: {hit_info.get('bp_pattern', 'N/A')}")
            lines.append(f"Match Type: {hit_info.get('bp_match_type', 'N/A')}")
        elif hit_info['type'] == 'size':
            lines.append(f"Size Range: {hit_info.get('bp_min_size')} - {hit_info.get('bp_max_size')}")
        elif hit_info['type'] == 'protocol':
            lines.append(f"Protocol: {hit_info.get('bp_protocol', 'N/A')}")
        elif hit_info['type'] == 'consecutive_errors':
            lines.append(f"Max Consecutive: {hit_info.get('bp_max_consecutive', 'N/A')}")
        
        # Add context information
        if hit_info['context']:
            lines.append("\nContext Information:")
            lines.append("-" * 30)
            for key, value in hit_info['context'].items():
                lines.append(f"  {key}: {value}")
        
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _add_breakpoint(self, condition: Callable, name: str, description: str, 
                       breakpoint_type: str, **kwargs) -> int:
        """Internal method to add a breakpoint"""
        breakpoint_id = len(self.breakpoints)
        
        breakpoint = {
            'id': breakpoint_id,
            'condition': condition,
            'name': name,
            'description': description,
            'type': breakpoint_type,
            'enabled': True,
            'created': datetime.utcnow().isoformat(),
            **kwargs
        }
        
        self.breakpoints.append(breakpoint)
        logger.info(f"Added breakpoint {breakpoint_id}: {name} ({breakpoint_type})")
        
        return breakpoint_id
    
    def get_breakpoint_summary(self) -> str:
        """Get a summary of all breakpoints"""
        if not self.breakpoints:
            return "No breakpoints configured"
        
        lines = [f"Breakpoints ({len(self.breakpoints)} total, {self.stats['breakpoints_hit']} hits):"]
        
        for bp in self.breakpoints:
            status = "✓" if bp['enabled'] else "✗"
            lines.append(f"  {status} [{bp['id']}] {bp['name']} ({bp['type']}) - {bp['description']}")
        
        return "\n".join(lines)