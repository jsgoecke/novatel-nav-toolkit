"""
Interactive Debugger for UDP Replay System
Provides interactive debugging capabilities during replay
"""

import sys
import select
import termios
import tty
import threading
import time
from typing import Optional, Dict, Any, Callable
from datetime import datetime

from logger import logger
from udp_replayer import UDPReplayer
from message_inspector import MessageInspector


class InteractiveDebugger:
    """Interactive debugging interface for UDP replay"""
    
    def __init__(self, replayer: UDPReplayer):
        """
        Initialize interactive debugger
        
        Args:
            replayer: UDPReplayer instance to control
        """
        self.replayer = replayer
        self.inspector = replayer.inspector
        
        # Terminal settings
        self.original_settings = None
        self.raw_mode = False
        
        # Control state
        self.running = False
        self.input_thread: Optional[threading.Thread] = None
        self.display_thread: Optional[threading.Thread] = None
        self.last_display_update = 0
        self.display_interval = 1.0  # seconds
        
        # Display settings
        self.show_hex_dump = False
        self.show_statistics = True
        self.show_filters = True
        self.show_breakpoints = True
        self.hex_dump_lines = 10
        
        # Command history
        self.command_history = []
        self.last_inspection = None
        
        # Key bindings
        self.key_bindings = {
            ' ': self._handle_pause_resume,
            'q': self._handle_quit,
            's': self._handle_step,
            'i': self._handle_inspect,
            'h': self._handle_hex_toggle,
            'f': self._handle_filter_info,
            'b': self._handle_breakpoint_info,
            'j': self._handle_jump,
            'r': self._handle_restart,
            'c': self._handle_clear_screen,
            'S': self._handle_statistics,
            '?': self._handle_help,
            '\x03': self._handle_quit,  # Ctrl+C
            '\x1b': self._handle_escape,  # Escape key
        }
        
        # Status messages
        self.status_message = ""
        self.status_timestamp = 0
    
    def start_interactive_mode(self) -> None:
        """Start interactive debugging mode"""
        if self.running:
            return
        
        try:
            # Setup terminal for raw input
            self._setup_terminal()
            
            self.running = True
            
            # Start input handling thread
            self.input_thread = threading.Thread(target=self._input_loop, daemon=True)
            self.input_thread.start()
            
            # Start display update thread
            self.display_thread = threading.Thread(target=self._display_loop, daemon=True)
            self.display_thread.start()
            
            logger.info("Interactive debugger started")
            self._show_welcome()
            
        except Exception as e:
            logger.error(f"Error starting interactive mode: {e}")
            self._restore_terminal()
    
    def stop_interactive_mode(self) -> None:
        """Stop interactive debugging mode"""
        if not self.running:
            return
        
        self.running = False
        
        # Wait for threads to finish
        if self.input_thread and self.input_thread.is_alive():
            self.input_thread.join(timeout=1.0)
        
        if self.display_thread and self.display_thread.is_alive():
            self.display_thread.join(timeout=1.0)
        
        # Restore terminal
        self._restore_terminal()
        
        logger.info("Interactive debugger stopped")
    
    def _setup_terminal(self) -> None:
        """Setup terminal for raw input"""
        if sys.platform == 'win32':
            # Windows - use different approach
            import msvcrt
            self.raw_mode = True
        else:
            # Unix-like systems
            self.original_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
            self.raw_mode = True
    
    def _restore_terminal(self) -> None:
        """Restore original terminal settings"""
        if not self.raw_mode:
            return
        
        if sys.platform != 'win32' and self.original_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_settings)
        
        self.raw_mode = False
    
    def _input_loop(self) -> None:
        """Input handling loop"""
        try:
            while self.running:
                if sys.platform == 'win32':
                    # Windows input handling
                    import msvcrt
                    if msvcrt.kbhit():
                        key = msvcrt.getch().decode('utf-8', errors='ignore')
                        self._handle_key(key)
                    time.sleep(0.1)
                else:
                    # Unix input handling
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1)
                        self._handle_key(key)
        
        except Exception as e:
            logger.error(f"Error in input loop: {e}")
    
    def _display_loop(self) -> None:
        """Display update loop"""
        try:
            while self.running:
                current_time = time.time()
                
                if current_time - self.last_display_update >= self.display_interval:
                    self._update_display()
                    self.last_display_update = current_time
                
                time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"Error in display loop: {e}")
    
    def _handle_key(self, key: str) -> None:
        """Handle keyboard input"""
        try:
            if key in self.key_bindings:
                self.key_bindings[key]()
            else:
                # Unknown key
                self._set_status(f"Unknown key: {repr(key)} - Press '?' for help")
        
        except Exception as e:
            logger.error(f"Error handling key '{key}': {e}")
            self._set_status(f"Error: {e}")
    
    def _update_display(self) -> None:
        """Update the interactive display"""
        try:
            # Clear screen
            print("\033[2J\033[H", end='')
            
            # Header
            print("=" * 80)
            print("UDP REPLAY INTERACTIVE DEBUGGER")
            print("=" * 80)
            
            # Current status
            stats = self.replayer.get_replay_stats()
            status = "RUNNING" if self.replayer.is_running else "STOPPED"
            if self.replayer.is_paused:
                status += " (PAUSED)"
            
            print(f"Status: {status} | Message: {stats['current_message_number']}/{stats['total_messages_in_file']} "
                  f"({stats['progress_percentage']:.1f}%) | Speed: {self.replayer.speed_multiplier}x")
            
            # Current message info
            msg_info = self.replayer.get_current_message_info()
            if msg_info:
                print(f"Current: {msg_info['message_size']} bytes | Protocol: {msg_info['protocol_detected']}")
                print(f"Preview: {msg_info['ascii_preview'][:60]}...")
            
            print("-" * 80)
            
            # Statistics
            if self.show_statistics:
                print("STATISTICS:")
                print(f"  Messages Sent: {stats['messages_sent']} | Filtered: {stats['messages_filtered']} | "
                      f"Errors: {stats['network_errors']}")
                print(f"  Bytes Sent: {stats['bytes_sent']} | Rate: {stats['messages_per_second']:.1f} msg/s")
                print(f"  Breakpoints Hit: {stats['breakpoints_hit']} | Loops: {stats['replay_loops']}")
                print()
            
            # Filter information
            if self.show_filters:
                filter_stats = stats['filter_stats']
                if filter_stats['active_filter_count'] > 0:
                    print("ACTIVE FILTERS:")
                    for filter_info in filter_stats['active_filters']:
                        print(f"  - {filter_info['name']} ({filter_info['type']})")
                    print(f"  Pass Rate: {filter_stats['pass_rate']:.1f}%")
                    print()
            
            # Breakpoint information
            if self.show_breakpoints:
                bp_stats = stats['breakpoint_stats']
                if bp_stats['enabled_breakpoints'] > 0:
                    print("BREAKPOINTS:")
                    for bp in self.replayer.breakpoint_manager.get_breakpoint_list():
                        status_icon = "✓" if bp['enabled'] else "✗"
                        print(f"  {status_icon} [{bp['id']}] {bp['name']} ({bp['type']})")
                    print()
            
            # Hex dump
            if self.show_hex_dump and self.replayer.current_message_data:
                print("HEX DUMP:")
                hex_dump = self.inspector.hex_dump(
                    self.replayer.current_message_data[:self.hex_dump_lines * 16],
                    bytes_per_line=16
                )
                print(hex_dump)
                print()
            
            # Status message
            if self.status_message and time.time() - self.status_timestamp < 5.0:
                print(f"Status: {self.status_message}")
            
            # Command help
            print("-" * 80)
            print("Commands: [SPACE] Pause/Resume | [s] Step | [i] Inspect | [h] Hex | [q] Quit | [?] Help")
            
            # Force output
            sys.stdout.flush()
        
        except Exception as e:
            logger.error(f"Error updating display: {e}")
    
    def _show_welcome(self) -> None:
        """Show welcome message"""
        print("\033[2J\033[H", end='')  # Clear screen
        print("=" * 80)
        print("UDP REPLAY INTERACTIVE DEBUGGER")
        print("=" * 80)
        print()
        print("Welcome to the interactive debugging mode!")
        print("Use the following keys to control the replay:")
        print()
        print("  [SPACE]  Pause/Resume replay")
        print("  [s]      Step through messages one by one")
        print("  [i]      Inspect current message in detail")
        print("  [h]      Toggle hex dump display")
        print("  [f]      Show filter information")
        print("  [b]      Show breakpoint information")
        print("  [j]      Jump to specific message number")
        print("  [r]      Restart from beginning")
        print("  [c]      Clear screen")
        print("  [S]      Save statistics")
        print("  [q]      Quit interactive mode")
        print("  [?]      Show this help")
        print()
        print("Press any key to start...")
        print("=" * 80)
        sys.stdout.flush()
    
    def _set_status(self, message: str) -> None:
        """Set status message"""
        self.status_message = message
        self.status_timestamp = time.time()
        logger.debug(f"Status: {message}")
    
    # Key handler methods
    def _handle_pause_resume(self) -> None:
        """Handle pause/resume toggle"""
        if self.replayer.is_paused:
            self.replayer.resume_replay()
            self._set_status("Replay resumed")
        else:
            self.replayer.pause_replay()
            self._set_status("Replay paused")
    
    def _handle_quit(self) -> None:
        """Handle quit command"""
        self._set_status("Quitting...")
        self.replayer.stop_replay()
        self.stop_interactive_mode()
    
    def _handle_step(self) -> None:
        """Handle step command"""
        if not self.replayer.step_mode:
            self.replayer.step_mode = True
            self.replayer.pause_replay()
            self._set_status("Step mode enabled - use SPACE to step")
        else:
            if self.replayer.step_single_message():
                self._set_status("Stepped to next message")
            else:
                self._set_status("Cannot step - replay not active")
    
    def _handle_inspect(self) -> None:
        """Handle inspect command"""
        inspection = self.replayer.inspect_current_message()
        if inspection:
            self.last_inspection = inspection
            self._set_status(f"Inspected message {inspection['message_number']} - check logs for details")
            
            # Log detailed inspection
            report = self.inspector.format_inspection_report(inspection)
            logger.info("MESSAGE INSPECTION:\n" + report)
        else:
            self._set_status("No current message to inspect")
    
    def _handle_hex_toggle(self) -> None:
        """Handle hex dump toggle"""
        self.show_hex_dump = not self.show_hex_dump
        self._set_status(f"Hex dump {'enabled' if self.show_hex_dump else 'disabled'}")
    
    def _handle_filter_info(self) -> None:
        """Handle filter information display"""
        filter_summary = self.replayer.message_filter.get_filter_summary()
        self._set_status("Filter info logged")
        logger.info("FILTER INFORMATION:\n" + filter_summary)
    
    def _handle_breakpoint_info(self) -> None:
        """Handle breakpoint information display"""
        bp_summary = self.replayer.breakpoint_manager.get_breakpoint_summary()
        self._set_status("Breakpoint info logged")
        logger.info("BREAKPOINT INFORMATION:\n" + bp_summary)
    
    def _handle_jump(self) -> None:
        """Handle jump to message command"""
        self._set_status("Jump feature requires CLI input - check documentation")
        # Note: This would require more complex input handling for number entry
    
    def _handle_restart(self) -> None:
        """Handle restart command"""
        if self.replayer.jump_to_message(0):
            self._set_status("Restarted from beginning")
        else:
            self._set_status("Cannot restart - replay not ready")
    
    def _handle_clear_screen(self) -> None:
        """Handle clear screen command"""
        print("\033[2J\033[H", end='')
        self._set_status("Screen cleared")
    
    def _handle_statistics(self) -> None:
        """Handle save statistics command"""
        if self.replayer.save_statistics():
            self._set_status("Statistics saved")
        else:
            self._set_status("Error saving statistics")
    
    def _handle_help(self) -> None:
        """Handle help display"""
        self._show_welcome()
        self._set_status("Help displayed")
    
    def _handle_escape(self) -> None:
        """Handle escape key"""
        self._set_status("ESC pressed - Press 'q' to quit")


class SimpleDebugger:
    """Simplified debugger for systems without terminal control"""
    
    def __init__(self, replayer: UDPReplayer):
        self.replayer = replayer
        self.running = False
    
    def start_simple_mode(self) -> None:
        """Start simple debugging mode with basic controls"""
        print("=" * 60)
        print("UDP REPLAY SIMPLE DEBUGGER")
        print("=" * 60)
        print()
        print("Simple debugging mode (no terminal control)")
        print()
        print("Available commands:")
        print("  pause    - Pause the replay")
        print("  resume   - Resume the replay")
        print("  step     - Enable step mode")
        print("  inspect  - Inspect current message")
        print("  stats    - Show statistics")
        print("  quit     - Stop replay and exit")
        print()
        
        self.running = True
        
        try:
            while self.running and self.replayer.is_running:
                try:
                    command = input("Debug> ").strip().lower()
                    
                    if command == 'pause':
                        self.replayer.pause_replay()
                        print("Replay paused")
                    elif command == 'resume':
                        self.replayer.resume_replay()
                        print("Replay resumed")
                    elif command == 'step':
                        self.replayer.step_mode = True
                        self.replayer.pause_replay()
                        print("Step mode enabled")
                    elif command == 'inspect':
                        self._inspect_current_message()
                    elif command == 'stats':
                        self._show_statistics()
                    elif command in ['quit', 'exit', 'q']:
                        self.replayer.stop_replay()
                        self.running = False
                    elif command == 'help':
                        self._show_help()
                    else:
                        print(f"Unknown command: {command}")
                
                except (EOFError, KeyboardInterrupt):
                    self.replayer.stop_replay()
                    self.running = False
                    break
        
        except Exception as e:
            logger.error(f"Error in simple debugger: {e}")
        
        print("Simple debugger stopped")
    
    def _inspect_current_message(self) -> None:
        """Inspect current message"""
        inspection = self.replayer.inspect_current_message()
        if inspection:
            report = self.replayer.inspector.format_inspection_report(inspection)
            print("\n" + report + "\n")
        else:
            print("No current message to inspect")
    
    def _show_statistics(self) -> None:
        """Show current statistics"""
        stats = self.replayer.get_replay_stats()
        
        print("\n" + "=" * 40)
        print("REPLAY STATISTICS")
        print("=" * 40)
        print(f"Messages: {stats['messages_sent']}/{stats['total_messages_in_file']}")
        print(f"Progress: {stats['progress_percentage']:.1f}%")
        print(f"Filtered: {stats['messages_filtered']}")
        print(f"Errors: {stats['network_errors']}")
        print(f"Rate: {stats['messages_per_second']:.1f} msg/s")
        print("=" * 40 + "\n")
    
    def _show_help(self) -> None:
        """Show help"""
        print("\nAvailable commands:")
        print("  pause    - Pause the replay")
        print("  resume   - Resume the replay") 
        print("  step     - Enable step mode")
        print("  inspect  - Inspect current message")
        print("  stats    - Show statistics")
        print("  help     - Show this help")
        print("  quit     - Stop replay and exit")
        print()