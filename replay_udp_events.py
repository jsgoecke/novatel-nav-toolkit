#!/usr/bin/env python3
"""
UDP Events Replay Script
Main command-line interface for replaying UDP events from log files
"""

import sys
import argparse
import signal
import time
from pathlib import Path
from typing import Optional

# Import our modules
import config
from logger import logger, console_print
from udp_replayer import UDPReplayer
from interactive_debugger import InteractiveDebugger, SimpleDebugger
from message_filter import MessageFilter
from breakpoint_manager import BreakpointManager


class ReplayController:
    """Main controller for UDP replay operations"""
    
    def __init__(self):
        self.replayer: Optional[UDPReplayer] = None
        self.debugger: Optional[InteractiveDebugger] = None
        self.simple_debugger: Optional[SimpleDebugger] = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def run_replay(self, args) -> int:
        """
        Run the UDP replay with specified arguments
        
        Args:
            args: Parsed command line arguments
            
        Returns:
            Exit code (0 = success, 1 = error)
        """
        try:
            # Create replayer instance
            self.replayer = UDPReplayer(
                log_file=args.file,
                target_host=args.host,
                target_port=args.port
            )
            
            # Configure replayer settings
            self.replayer.speed_multiplier = args.speed
            self.replayer.loop_mode = args.loop
            self.replayer.step_mode = args.step_mode
            self.replayer.interactive_mode = args.interactive
            
            # Setup message filters
            self._setup_filters(args)
            
            # Setup breakpoints
            self._setup_breakpoints(args)
            
            # Setup callbacks
            self._setup_callbacks(args)
            
            # Load message cache
            console_print("Loading message cache...", force=True)
            if not self.replayer.load_message_cache():
                console_print("Failed to load message cache", force=True)
                return 1
            
            stats = self.replayer.get_replay_stats()
            console_print(f"Loaded {stats['total_messages_in_file']} messages", force=True)
            
            # Show configuration
            self._show_configuration(args)
            
            # Start replay
            console_print("Starting UDP replay...", force=True)
            if not self.replayer.start_replay():
                console_print("Failed to start replay", force=True)
                return 1
            
            self.running = True
            
            # Handle different modes
            if args.interactive:
                return self._run_interactive_mode()
            elif args.step_mode:
                return self._run_step_mode()
            else:
                return self._run_normal_mode()
        
        except KeyboardInterrupt:
            console_print("\nInterrupted by user", force=True)
            return 0
        except Exception as e:
            console_print(f"Error: {e}", force=True)
            logger.error(f"Replay error: {e}")
            return 1
        finally:
            self._cleanup()
    
    def _setup_filters(self, args) -> None:
        """Setup message filters based on arguments"""
        if args.filter_size:
            try:
                if '-' in args.filter_size:
                    min_size, max_size = map(int, args.filter_size.split('-'))
                else:
                    min_size = int(args.filter_size)
                    max_size = min_size
                
                self.replayer.message_filter.add_size_filter(min_size, max_size)
                console_print(f"Added size filter: {min_size}-{max_size} bytes", force=True)
            except ValueError:
                console_print(f"Invalid size filter format: {args.filter_size}", force=True)
        
        if args.filter_pattern:
            for pattern in args.filter_pattern:
                self.replayer.message_filter.add_hex_pattern_filter(pattern)
                console_print(f"Added pattern filter: {pattern}", force=True)
        
        if args.protocol:
            self.replayer.message_filter.add_protocol_filter(args.protocol)
            console_print(f"Added protocol filter: {args.protocol}", force=True)
        
        if args.skip_corrupted:
            self.replayer.message_filter.add_corruption_filter(skip_corrupted=True)
            console_print("Added corruption filter", force=True)
    
    def _setup_breakpoints(self, args) -> None:
        """Setup breakpoints based on arguments"""
        bp_manager = self.replayer.breakpoint_manager
        
        if args.pause_on_error:
            bp_manager.add_error_breakpoint()
            console_print("Added error breakpoint", force=True)
        
        if args.breakpoint_pattern:
            for pattern in args.breakpoint_pattern:
                bp_manager.add_hex_pattern_breakpoint(pattern)
                console_print(f"Added pattern breakpoint: {pattern}", force=True)
        
        if args.breakpoint_size:
            try:
                if '-' in args.breakpoint_size:
                    min_size, max_size = map(int, args.breakpoint_size.split('-'))
                else:
                    size = int(args.breakpoint_size)
                    min_size, max_size = size, size
                
                bp_manager.add_size_breakpoint(min_size, max_size)
                console_print(f"Added size breakpoint: {min_size}-{max_size} bytes", force=True)
            except ValueError:
                console_print(f"Invalid breakpoint size format: {args.breakpoint_size}", force=True)
        
        if args.max_consecutive_errors:
            bp_manager.add_consecutive_errors_breakpoint(args.max_consecutive_errors)
            console_print(f"Added consecutive errors breakpoint: {args.max_consecutive_errors}", force=True)
    
    def _setup_callbacks(self, args) -> None:
        """Setup event callbacks"""
        if args.verbose:
            def on_message_sent(data: bytes, msg_num: int):
                console_print(f"Sent message {msg_num}: {len(data)} bytes", force=True)
            
            self.replayer.set_message_sent_callback(on_message_sent)
        
        def on_breakpoint_hit(hit_info):
            console_print(f"\nBreakpoint hit: {hit_info['name']} at message {hit_info['message_number']}", force=True)
            if args.inspect_on_breakpoint:
                inspection = self.replayer.inspect_current_message()
                if inspection:
                    report = self.replayer.inspector.format_inspection_report(inspection)
                    logger.info("BREAKPOINT INSPECTION:\n" + report)
        
        self.replayer.set_breakpoint_hit_callback(on_breakpoint_hit)
        
        def on_error(error_type: str, exception: Exception):
            console_print(f"Error ({error_type}): {exception}", force=True)
        
        self.replayer.set_error_callback(on_error)
        
        def on_completion(stats):
            self._show_completion_stats(stats)
        
        self.replayer.set_completion_callback(on_completion)
    
    def _show_configuration(self, args) -> None:
        """Show current configuration"""
        console_print("=" * 60, force=True)
        console_print("UDP REPLAY CONFIGURATION", force=True)
        console_print("=" * 60, force=True)
        console_print(f"Log file: {args.file}", force=True)
        console_print(f"Target: {args.host}:{args.port}", force=True)
        console_print(f"Speed: {args.speed}x", force=True)
        console_print(f"Loop mode: {args.loop}", force=True)
        console_print(f"Step mode: {args.step_mode}", force=True)
        console_print(f"Interactive: {args.interactive}", force=True)
        
        # Show filter summary
        filter_summary = self.replayer.message_filter.get_filter_summary()
        if "No filters" not in filter_summary:
            console_print("\nFilters:", force=True)
            console_print(filter_summary, force=True)
        
        # Show breakpoint summary
        bp_summary = self.replayer.breakpoint_manager.get_breakpoint_summary()
        if "No breakpoints" not in bp_summary:
            console_print("\nBreakpoints:", force=True)
            console_print(bp_summary, force=True)
        
        console_print("=" * 60, force=True)
    
    def _run_interactive_mode(self) -> int:
        """Run in interactive debugging mode"""
        try:
            # Try advanced interactive mode first
            self.debugger = InteractiveDebugger(self.replayer)
            self.debugger.start_interactive_mode()
            
            # Wait for replay to complete or user to quit
            while self.running and self.replayer.is_running:
                time.sleep(0.1)
            
            return 0
        
        except Exception as e:
            logger.warning(f"Advanced interactive mode failed: {e}")
            console_print("Falling back to simple debugging mode...", force=True)
            
            # Fall back to simple mode
            self.simple_debugger = SimpleDebugger(self.replayer)
            self.simple_debugger.start_simple_mode()
            
            return 0
    
    def _run_step_mode(self) -> int:
        """Run in step-by-step mode"""
        console_print("Step mode - press Enter to advance, 'q' to quit", force=True)
        
        try:
            while self.running and self.replayer.is_running:
                # Show current message info
                msg_info = self.replayer.get_current_message_info()
                if msg_info:
                    console_print(f"\nMessage {msg_info['message_number']}: "
                                 f"{msg_info['message_size']} bytes, "
                                 f"protocol: {msg_info['protocol_detected']}", force=True)
                    console_print(f"Preview: {msg_info['ascii_preview'][:80]}...", force=True)
                
                user_input = input("Press Enter to continue, 'i' to inspect, 'q' to quit: ").strip().lower()
                
                if user_input in ['q', 'quit']:
                    break
                elif user_input in ['i', 'inspect']:
                    inspection = self.replayer.inspect_current_message()
                    if inspection:
                        report = self.replayer.inspector.format_inspection_report(inspection)
                        print(report)
                else:
                    # Step to next message
                    self.replayer.step_single_message()
            
            return 0
        
        except (EOFError, KeyboardInterrupt):
            return 0
    
    def _run_normal_mode(self) -> int:
        """Run in normal mode"""
        console_print("Replay running... Press Ctrl+C to stop", force=True)
        
        try:
            # Show periodic statistics
            last_stats_time = time.time()
            stats_interval = 10.0  # seconds
            
            while self.running and self.replayer.is_running:
                current_time = time.time()
                
                if current_time - last_stats_time >= stats_interval:
                    stats = self.replayer.get_replay_stats()
                    console_print(f"Progress: {stats['progress_percentage']:.1f}% | "
                                 f"Messages: {stats['messages_sent']} | "
                                 f"Rate: {stats['messages_per_second']:.1f} msg/s", force=True)
                    last_stats_time = current_time
                
                time.sleep(1.0)
            
            return 0
        
        except KeyboardInterrupt:
            return 0
    
    def _show_completion_stats(self, stats) -> None:
        """Show completion statistics"""
        console_print("\n" + "=" * 60, force=True)
        console_print("REPLAY COMPLETED", force=True)
        console_print("=" * 60, force=True)
        console_print(f"Total messages processed: {stats['messages_processed']}", force=True)
        console_print(f"Messages sent: {stats['messages_sent']}", force=True)
        console_print(f"Messages filtered: {stats['messages_filtered']}", force=True)
        console_print(f"Network errors: {stats['network_errors']}", force=True)
        console_print(f"Bytes sent: {stats['bytes_sent']}", force=True)
        console_print(f"Breakpoints hit: {stats['breakpoints_hit']}", force=True)
        console_print(f"Replay loops: {stats['replay_loops']}", force=True)
        
        if stats['session_start'] and stats['session_end']:
            from datetime import datetime
            start = datetime.fromisoformat(stats['session_start'])
            end = datetime.fromisoformat(stats['session_end'])
            duration = (end - start).total_seconds()
            console_print(f"Duration: {duration:.1f} seconds", force=True)
            
            if duration > 0:
                console_print(f"Average rate: {stats['messages_sent'] / duration:.1f} msg/s", force=True)
        
        console_print("=" * 60, force=True)
    
    def _cleanup(self) -> None:
        """Cleanup resources"""
        self.running = False
        
        if self.debugger:
            self.debugger.stop_interactive_mode()
        
        if self.replayer:
            self.replayer.stop_replay()
            
            # Save statistics if configured
            if config.REPLAY_SAVE_STATISTICS:
                if self.replayer.save_statistics():
                    console_print(f"Statistics saved to {config.REPLAY_STATISTICS_FILE}", force=True)
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        console_print(f"\nReceived signal {signum}", force=True)
        self.running = False
        
        if self.replayer:
            self.replayer.stop_replay()


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser"""
    parser = argparse.ArgumentParser(
        description="UDP Events Replay Tool for Novatel Navigation Toolkit",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Basic replay
  %(prog)s --speed 2.0 --loop                # Fast continuous replay
  %(prog)s --interactive --pause-on-error    # Interactive debugging
  %(prog)s --step-mode --inspect-on-breakpoint # Step-by-step analysis
  %(prog)s --filter-size 100-200             # Filter by message size
  %(prog)s --protocol nmea --verbose         # NMEA messages only
        """
    )
    
    # Basic options
    parser.add_argument(
        '--file', '-f',
        default=config.REPLAY_LOG_FILE,
        help=f'UDP events log file (default: {config.REPLAY_LOG_FILE})'
    )
    
    parser.add_argument(
        '--host',
        default=config.REPLAY_TARGET_HOST,
        help=f'Target hostname/IP (default: {config.REPLAY_TARGET_HOST})'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=config.REPLAY_TARGET_PORT,
        help=f'Target UDP port (default: {config.REPLAY_TARGET_PORT})'
    )
    
    parser.add_argument(
        '--speed', '-s',
        type=float,
        default=config.REPLAY_SPEED_MULTIPLIER,
        help=f'Replay speed multiplier (default: {config.REPLAY_SPEED_MULTIPLIER})'
    )
    
    parser.add_argument(
        '--loop', '-l',
        action='store_true',
        default=config.REPLAY_LOOP_MODE,
        help='Enable continuous loop mode'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    # Debugging modes
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        default=config.REPLAY_INTERACTIVE_MODE,
        help='Enable interactive debugging mode'
    )
    
    parser.add_argument(
        '--step-mode',
        action='store_true',
        default=config.REPLAY_STEP_MODE,
        help='Enable step-by-step mode'
    )
    
    # Message filtering
    parser.add_argument(
        '--filter-size',
        help='Filter by message size (e.g., "100" or "100-200")'
    )
    
    parser.add_argument(
        '--filter-pattern',
        action='append',
        help='Filter by hex pattern (can be used multiple times)'
    )
    
    parser.add_argument(
        '--protocol',
        choices=['nmea', 'adsb', 'novatel', 'ascii', 'binary'],
        help='Filter by protocol type'
    )
    
    parser.add_argument(
        '--skip-corrupted',
        action='store_true',
        help='Skip potentially corrupted messages'
    )
    
    # Breakpoints
    parser.add_argument(
        '--pause-on-error',
        action='store_true',
        default=config.REPLAY_PAUSE_ON_ERROR,
        help='Pause replay on parsing errors'
    )
    
    parser.add_argument(
        '--breakpoint-pattern',
        action='append',
        help='Add breakpoint for hex pattern (can be used multiple times)'
    )
    
    parser.add_argument(
        '--breakpoint-size',
        help='Add breakpoint for message size (e.g., "100" or "100-200")'
    )
    
    parser.add_argument(
        '--max-consecutive-errors',
        type=int,
        default=config.REPLAY_MAX_CONSECUTIVE_ERRORS,
        help=f'Break on N consecutive errors (default: {config.REPLAY_MAX_CONSECUTIVE_ERRORS})'
    )
    
    parser.add_argument(
        '--inspect-on-breakpoint',
        action='store_true',
        help='Automatically inspect messages when breakpoints hit'
    )
    
    # Statistics and output
    parser.add_argument(
        '--save-stats',
        action='store_true',
        help='Save statistics to file on completion'
    )
    
    parser.add_argument(
        '--stats-file',
        default=config.REPLAY_STATISTICS_FILE,
        help=f'Statistics output file (default: {config.REPLAY_STATISTICS_FILE})'
    )
    
    return parser


def main() -> int:
    """Main entry point"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Validate log file
    if not Path(args.file).exists():
        console_print(f"Error: Log file not found: {args.file}", force=True)
        return 1
    
    # Update config if needed
    if args.save_stats:
        config.REPLAY_SAVE_STATISTICS = True
    if args.stats_file != config.REPLAY_STATISTICS_FILE:
        config.REPLAY_STATISTICS_FILE = args.stats_file
    
    # Show startup info
    console_print("UDP Events Replay Tool", force=True)
    console_print("=" * 40, force=True)
    
    # Create and run controller
    controller = ReplayController()
    return controller.run_replay(args)


if __name__ == "__main__":
    sys.exit(main())