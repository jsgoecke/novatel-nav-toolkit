"""
UDP Event Replayer for Novatel Navigation Data Toolkit
Core functionality to read and replay binary log data
"""

import socket
import time
import threading
from typing import Optional, Callable, Dict, Any, List, Tuple
from pathlib import Path
from datetime import datetime
import json

import config
from logger import logger
from message_inspector import MessageInspector
from message_filter import MessageFilter, create_filter_from_config
from breakpoint_manager import BreakpointManager


class UDPReplayer:
    """Core UDP replayer for reading and sending binary log data"""
    
    def __init__(self, log_file: str = None, target_host: str = None, target_port: int = None):
        """
        Initialize UDP replayer
        
        Args:
            log_file: Path to UDP events log file
            target_host: Target hostname/IP for UDP packets
            target_port: Target port for UDP packets
        """
        self.log_file = log_file or config.REPLAY_LOG_FILE
        self.target_host = target_host or config.REPLAY_TARGET_HOST
        self.target_port = target_port or config.REPLAY_TARGET_PORT
        
        # Core components
        self.inspector = MessageInspector()
        self.message_filter = create_filter_from_config()
        self.breakpoint_manager = BreakpointManager(self.inspector)
        
        # Replay control
        self.socket: Optional[socket.socket] = None
        self.is_running = False
        self.is_paused = False
        self.replay_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        
        # Replay settings
        self.speed_multiplier = config.REPLAY_SPEED_MULTIPLIER
        self.loop_mode = config.REPLAY_LOOP_MODE
        self.inter_message_delay = config.REPLAY_INTER_MESSAGE_DELAY
        self.step_mode = config.REPLAY_STEP_MODE
        self.interactive_mode = config.REPLAY_INTERACTIVE_MODE
        
        # Statistics
        self.stats = {
            'session_start': None,
            'session_end': None,
            'total_messages_in_file': 0,
            'messages_processed': 0,
            'messages_sent': 0,
            'messages_filtered': 0,
            'messages_skipped': 0,
            'parsing_errors': 0,
            'network_errors': 0,
            'bytes_sent': 0,
            'current_message_number': 0,
            'replay_loops': 0,
            'breakpoints_hit': 0,
            'average_message_size': 0,
            'messages_per_second': 0,
            'bytes_per_second': 0
        }
        
        # Message tracking
        self.current_message_data: Optional[bytes] = None
        self.current_message_number = 0
        self.message_cache: List[bytes] = []
        self.cache_loaded = False
        
        # Callbacks
        self.on_message_sent: Optional[Callable[[bytes, int], None]] = None
        self.on_breakpoint_hit: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_error: Optional[Callable[[str, Exception], None]] = None
        self.on_completion: Optional[Callable[[Dict[str, Any]], None]] = None
    
    def load_message_cache(self) -> bool:
        """
        Load all messages from log file into memory cache
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Loading messages from {self.log_file}")
            
            if not Path(self.log_file).exists():
                logger.error(f"Log file not found: {self.log_file}")
                return False
            
            self.message_cache.clear()
            
            with open(self.log_file, 'rb') as f:
                line_count = 0
                for line in f:
                    line_count += 1
                    line = line.strip()
                    
                    if len(line) == 0:
                        continue  # Skip empty lines
                    
                    self.message_cache.append(line)
            
            self.stats['total_messages_in_file'] = len(self.message_cache)
            self.cache_loaded = True
            
            logger.info(f"Loaded {len(self.message_cache)} messages from log file ({line_count} total lines)")
            return True
            
        except Exception as e:
            logger.error(f"Error loading message cache: {e}")
            if self.on_error:
                self.on_error("cache_load_error", e)
            return False
    
    def start_replay(self, speed_multiplier: float = None, loop_mode: bool = None, 
                    step_mode: bool = None) -> bool:
        """
        Start the replay process
        
        Args:
            speed_multiplier: Replay speed (1.0 = real-time)
            loop_mode: Whether to loop continuously
            step_mode: Whether to enable step-by-step mode
            
        Returns:
            True if started successfully
        """
        if self.is_running:
            logger.warning("Replay is already running")
            return False
        
        # Update settings if provided
        if speed_multiplier is not None:
            self.speed_multiplier = speed_multiplier
        if loop_mode is not None:
            self.loop_mode = loop_mode
        if step_mode is not None:
            self.step_mode = step_mode
        
        # Load message cache if not already loaded
        if not self.cache_loaded:
            if not self.load_message_cache():
                return False
        
        # Create UDP socket
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            logger.info(f"Created UDP socket for target {self.target_host}:{self.target_port}")
        except Exception as e:
            logger.error(f"Failed to create UDP socket: {e}")
            if self.on_error:
                self.on_error("socket_creation_error", e)
            return False
        
        # Reset control events
        self.stop_event.clear()
        self.pause_event.clear()
        
        # Initialize statistics
        self.stats['session_start'] = datetime.utcnow().isoformat()
        self.stats['session_end'] = None
        self.stats['messages_processed'] = 0
        self.stats['messages_sent'] = 0
        self.stats['messages_filtered'] = 0
        self.stats['messages_skipped'] = 0
        self.stats['parsing_errors'] = 0
        self.stats['network_errors'] = 0
        self.stats['bytes_sent'] = 0
        self.stats['current_message_number'] = 0
        self.stats['replay_loops'] = 0
        self.stats['breakpoints_hit'] = 0
        
        # Start replay thread
        self.is_running = True
        self.replay_thread = threading.Thread(target=self._replay_loop, daemon=True)
        self.replay_thread.start()
        
        logger.info(f"Started UDP replay: {len(self.message_cache)} messages, "
                   f"speed={self.speed_multiplier}x, loop={self.loop_mode}, "
                   f"step={self.step_mode}")
        
        return True
    
    def stop_replay(self) -> None:
        """Stop the replay process"""
        if not self.is_running:
            return
        
        logger.info("Stopping UDP replay...")
        self.is_running = False
        self.stop_event.set()
        
        # Wait for replay thread to finish
        if self.replay_thread and self.replay_thread.is_alive():
            self.replay_thread.join(timeout=5.0)
        
        # Close socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # Finalize statistics
        self.stats['session_end'] = datetime.utcnow().isoformat()
        
        logger.info("UDP replay stopped")
        
        if self.on_completion:
            self.on_completion(self.stats.copy())
    
    def pause_replay(self) -> None:
        """Pause the replay process"""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            self.pause_event.set()
            logger.info("UDP replay paused")
    
    def resume_replay(self) -> None:
        """Resume the replay process"""
        if self.is_running and self.is_paused:
            self.is_paused = False
            self.pause_event.clear()
            logger.info("UDP replay resumed")
    
    def step_single_message(self) -> bool:
        """
        Send a single message (for step mode)
        
        Returns:
            True if message was sent, False if no more messages
        """
        if not self.step_mode or not self.is_running:
            return False
        
        # Resume briefly to send one message
        if self.is_paused:
            self.pause_event.clear()
            time.sleep(0.1)  # Allow one message to be processed
            self.pause_event.set()
            return True
        
        return False
    
    def jump_to_message(self, message_number: int) -> bool:
        """
        Jump to a specific message number
        
        Args:
            message_number: Target message number (0-based)
            
        Returns:
            True if successful
        """
        if not self.cache_loaded or message_number < 0 or message_number >= len(self.message_cache):
            return False
        
        self.current_message_number = message_number
        self.stats['current_message_number'] = message_number
        
        logger.info(f"Jumped to message {message_number}")
        return True
    
    def get_current_message_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current message"""
        if not self.current_message_data or self.current_message_number < 0:
            return None
        
        return {
            'message_number': self.current_message_number,
            'message_size': len(self.current_message_data),
            'hex_preview': self.current_message_data[:50].hex().upper(),
            'ascii_preview': self.inspector.get_ascii_preview(self.current_message_data, 100),
            'protocol_detected': self.inspector.detect_protocol(self.current_message_data)
        }
    
    def inspect_current_message(self) -> Optional[Dict[str, Any]]:
        """Perform detailed inspection of current message"""
        if not self.current_message_data:
            return None
        
        return self.inspector.inspect_message(self.current_message_data, self.current_message_number)
    
    def get_replay_stats(self) -> Dict[str, Any]:
        """Get comprehensive replay statistics"""
        stats = self.stats.copy()
        
        # Calculate derived statistics
        if stats['messages_processed'] > 0:
            stats['average_message_size'] = stats['bytes_sent'] / stats['messages_sent'] if stats['messages_sent'] > 0 else 0
            
            # Calculate rates if session is running
            if stats['session_start'] and self.is_running:
                start_time = datetime.fromisoformat(stats['session_start'])
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                
                if elapsed > 0:
                    stats['messages_per_second'] = stats['messages_processed'] / elapsed
                    stats['bytes_per_second'] = stats['bytes_sent'] / elapsed
        
        # Add component statistics
        stats['filter_stats'] = self.message_filter.get_filter_stats()
        stats['breakpoint_stats'] = self.breakpoint_manager.get_breakpoint_stats()
        stats['inspector_stats'] = self.inspector.get_inspection_stats()
        
        # Add current status
        stats['is_running'] = self.is_running
        stats['is_paused'] = self.is_paused
        stats['cache_loaded'] = self.cache_loaded
        stats['progress_percentage'] = (stats['current_message_number'] / stats['total_messages_in_file'] * 100) if stats['total_messages_in_file'] > 0 else 0
        
        return stats
    
    def save_statistics(self, filename: str = None) -> bool:
        """
        Save statistics to JSON file
        
        Args:
            filename: Output filename
            
        Returns:
            True if successful
        """
        filename = filename or config.REPLAY_STATISTICS_FILE
        
        try:
            stats = self.get_replay_stats()
            # Create directory if needed
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
            
            with open(filename, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            
            logger.info(f"Statistics saved to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving statistics: {e}")
            return False
    
    def _replay_loop(self) -> None:
        """Main replay loop (runs in separate thread)"""
        try:
            logger.info("Starting replay loop")
            
            while self.is_running and not self.stop_event.is_set():
                # Process all messages in cache
                for i, message_data in enumerate(self.message_cache):
                    if self.stop_event.is_set():
                        break
                    
                    # Handle pause
                    if self.is_paused or self.step_mode:
                        self.pause_event.wait()
                        if self.stop_event.is_set():
                            break
                        
                        # In step mode, pause after each message
                        if self.step_mode:
                            self.pause_event.set()
                    
                    self.current_message_number = i
                    self.current_message_data = message_data
                    self.stats['current_message_number'] = i
                    self.stats['messages_processed'] += 1
                    
                    # Apply message filters
                    passed_filter, failed_filters = self.message_filter.apply_filters(message_data, i)
                    
                    if not passed_filter:
                        self.stats['messages_filtered'] += 1
                        logger.debug(f"Message {i} filtered out: {failed_filters}")
                        continue
                    
                    # Check breakpoints
                    context = {'parse_success': False, 'parse_error': False}  # Will be updated by callback
                    breakpoint_hit = self.breakpoint_manager.check_breakpoints(message_data, i, context)
                    
                    if breakpoint_hit:
                        self.stats['breakpoints_hit'] += 1
                        logger.info(f"Breakpoint hit at message {i}: {breakpoint_hit['name']}")
                        
                        if self.on_breakpoint_hit:
                            self.on_breakpoint_hit(breakpoint_hit)
                        
                        # Pause on breakpoint
                        self.is_paused = True
                        self.pause_event.set()
                        continue
                    
                    # Send UDP message
                    try:
                        self.socket.sendto(message_data, (self.target_host, self.target_port))
                        self.stats['messages_sent'] += 1
                        self.stats['bytes_sent'] += len(message_data)
                        
                        logger.debug(f"Sent message {i}: {len(message_data)} bytes")
                        
                        if self.on_message_sent:
                            self.on_message_sent(message_data, i)
                        
                    except Exception as e:
                        self.stats['network_errors'] += 1
                        logger.error(f"Error sending message {i}: {e}")
                        
                        if self.on_error:
                            self.on_error("network_send_error", e)
                    
                    # Apply inter-message delay
                    if self.inter_message_delay > 0:
                        delay = self.inter_message_delay / self.speed_multiplier
                        time.sleep(delay)
                
                # Handle loop mode
                if self.loop_mode and self.is_running and not self.stop_event.is_set():
                    self.stats['replay_loops'] += 1
                    logger.info(f"Starting replay loop #{self.stats['replay_loops'] + 1}")
                else:
                    break
            
            logger.info("Replay loop completed")
            
        except Exception as e:
            logger.error(f"Error in replay loop: {e}")
            if self.on_error:
                self.on_error("replay_loop_error", e)
        
        finally:
            self.is_running = False
    
    def set_message_sent_callback(self, callback: Callable[[bytes, int], None]) -> None:
        """Set callback for when messages are sent"""
        self.on_message_sent = callback
    
    def set_breakpoint_hit_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set callback for when breakpoints are hit"""
        self.on_breakpoint_hit = callback
    
    def set_error_callback(self, callback: Callable[[str, Exception], None]) -> None:
        """Set callback for errors"""
        self.on_error = callback
    
    def set_completion_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set callback for replay completion"""
        self.on_completion = callback