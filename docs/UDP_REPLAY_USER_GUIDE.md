# UDP Event Replay System - User Guide

## Overview

The UDP Event Replay System allows you to replay binary messages from log files over UDP to test your Novatel navigation toolkit parsers. This is essential for debugging, development, and testing with real flight data in a controlled environment.

## Quick Start

### Basic Usage

```bash
# Simple replay at normal speed
python replay_udp_events.py

# Fast replay for quick testing
python replay_udp_events.py --speed 5.0

# Continuous loop mode
python replay_udp_events.py --loop

# Interactive debugging mode
python replay_udp_events.py --interactive
```

### Testing Your Setup

1. **Start the navigation toolkit** in one terminal:
   ```bash
   python main.py
   ```

2. **Run the replay** in another terminal:
   ```bash
   python replay_udp_events.py --speed 2.0 --verbose
   ```

3. **Observe the results** in the first terminal - you should see parsed navigation data.

## Command Line Options

### Basic Options

- `--file`, `-f`: UDP events log file (default: `data/udp_events.log`)
- `--host`: Target hostname/IP (default: `localhost`)
- `--port`, `-p`: Target UDP port (default: `4001`)
- `--speed`, `-s`: Replay speed multiplier (default: `1.0`)
- `--loop`, `-l`: Enable continuous loop mode
- `--verbose`, `-v`: Enable verbose output

### Debugging Modes

- `--interactive`, `-i`: Interactive debugging with real-time controls
- `--step-mode`: Step through messages one by one
- `--pause-on-error`: Automatically pause when parsing errors occur

### Message Filtering

- `--filter-size SIZE`: Filter by message size
  - Single size: `--filter-size 100`
  - Size range: `--filter-size 100-200`
- `--filter-pattern PATTERN`: Filter by hex pattern (can use multiple times)
  - Example: `--filter-pattern AA44 --filter-pattern GP`
- `--protocol PROTOCOL`: Filter by protocol type
  - Options: `nmea`, `adsb`, `novatel`, `ascii`, `binary`
- `--skip-corrupted`: Skip potentially corrupted messages

### Breakpoints

- `--pause-on-error`: Pause on parsing errors
- `--breakpoint-pattern PATTERN`: Break on hex pattern
- `--breakpoint-size SIZE`: Break on message size
- `--max-consecutive-errors N`: Break after N consecutive errors
- `--inspect-on-breakpoint`: Auto-inspect messages at breakpoints

### Statistics and Output

- `--save-stats`: Save statistics to file on completion
- `--stats-file FILE`: Statistics output file

## Interactive Debugging Mode

When using `--interactive`, you get a real-time debugging interface:

### Key Commands

- **[SPACE]**: Pause/Resume replay
- **[s]**: Enable step-by-step mode
- **[i]**: Inspect current message in detail
- **[h]**: Toggle hex dump display
- **[f]**: Show filter information
- **[b]**: Show breakpoint information
- **[j]**: Jump to specific message (CLI mode)
- **[r]**: Restart from beginning
- **[c]**: Clear screen
- **[S]**: Save statistics
- **[q]**: Quit interactive mode
- **[?]**: Show help

### Display Information

The interactive mode shows:
- Current replay status and progress
- Message statistics (sent, filtered, errors)
- Current message information
- Active filters and breakpoints
- Optional hex dump of current message

## Usage Examples

### Development Testing

```bash
# Test new parser changes with known data
python replay_udp_events.py --loop --speed 2.0

# Debug specific parsing issues
python replay_udp_events.py --interactive --pause-on-error
```

### System Validation

```bash
# Comprehensive system test with statistics
python replay_udp_events.py --save-stats --verbose

# Performance benchmarking
python replay_udp_events.py --speed 10.0 --loop
```

### Message Analysis

```bash
# Step through problematic messages
python replay_udp_events.py --step-mode --inspect-on-breakpoint

# Filter and analyze specific message types
python replay_udp_events.py --filter-size 50-100 --protocol nmea

# Focus on large messages that might cause issues
python replay_udp_events.py --breakpoint-size 200 --interactive
```

### Error Investigation

```bash
# Stop on parsing errors for investigation
python replay_udp_events.py --pause-on-error --interactive

# Break after multiple consecutive errors
python replay_udp_events.py --max-consecutive-errors 3 --inspect-on-breakpoint

# Skip corrupted data and focus on valid messages
python replay_udp_events.py --skip-corrupted --verbose
```

## Configuration

The system uses settings from `config.py`. Key replay-related settings:

```python
# UDP Replay Configuration
REPLAY_LOG_FILE = 'data/udp_events.log'
REPLAY_TARGET_HOST = 'localhost'
REPLAY_TARGET_PORT = 4001
REPLAY_SPEED_MULTIPLIER = 1.0
REPLAY_LOOP_MODE = False
REPLAY_INTER_MESSAGE_DELAY = 0.01  # seconds

# Interactive Debugging
REPLAY_INTERACTIVE_MODE = False
REPLAY_STEP_MODE = False
REPLAY_PAUSE_ON_ERROR = False

# Message Filtering
REPLAY_FILTER_MIN_SIZE = 0
REPLAY_FILTER_MAX_SIZE = float('inf')
REPLAY_SKIP_CORRUPTED = False

# Statistics
REPLAY_ENABLE_STATISTICS = True
REPLAY_SAVE_STATISTICS = False
REPLAY_STATISTICS_FILE = 'logs/replay_statistics.json'
```

## Log File Format

The UDP events log file (`data/udp_events.log`) should contain:
- One binary message per line
- Raw binary data (no timestamps or metadata)
- Messages exactly as received from the live system

## Message Inspection

### Automatic Inspection

Messages are automatically analyzed for:
- **Protocol Detection**: NMEA, Novatel, ADS-B identification
- **Structure Analysis**: Size, headers, printable content
- **Checksum Validation**: NMEA and other checksum verification
- **Data Patterns**: Repeating patterns, strings, potential floats

### Manual Inspection

Use the `--interactive` mode and press `[i]` to inspect the current message, or use `--inspect-on-breakpoint` to automatically inspect when breakpoints are hit.

## Filtering and Breakpoints

### Message Filtering

Filters determine which messages are sent during replay:
- **Size filters**: Include/exclude by byte count
- **Pattern filters**: Match binary patterns or hex strings
- **Protocol filters**: Focus on specific protocols
- **Corruption filters**: Skip malformed messages

### Breakpoints

Breakpoints pause replay when conditions are met:
- **Error breakpoints**: Stop on parsing failures
- **Pattern breakpoints**: Stop on specific binary patterns
- **Size breakpoints**: Stop on large/small messages
- **Count breakpoints**: Stop after N successes/failures

## Performance Considerations

### Speed Control

- `--speed 0.1`: Very slow (1/10th speed) for detailed analysis
- `--speed 1.0`: Real-time replay
- `--speed 10.0`: 10x speed for quick testing
- `--speed 100.0`: Maximum speed for performance testing

### Memory Usage

- Messages are cached in memory for random access
- Large log files may require significant memory
- Use filtering to reduce memory usage if needed

### Network Impact

- Each message is sent as a separate UDP packet
- High-speed replay can generate significant network traffic
- Use `localhost` target to minimize network impact

## Troubleshooting

### Common Issues

1. **"Log file not found"**
   - Verify `data/udp_events.log` exists
   - Use `--file` to specify different location

2. **"Failed to start replay"**
   - Check if target port is already in use
   - Verify network connectivity to target host

3. **"No messages received in navigation toolkit"**
   - Ensure navigation toolkit is listening on correct port
   - Check firewall settings
   - Verify UDP_PORT in config.py matches replay target

4. **"Messages filtered out"**
   - Check filter settings with `--verbose`
   - Use `--filter-pattern` or `--filter-size` appropriately
   - Disable filters to test all messages

### Debug Information

Enable verbose logging for troubleshooting:
```bash
python replay_udp_events.py --verbose --interactive
```

Check the logs directory for detailed information:
- `logs/navigation_data.log`: Main application log
- `logs/replay_statistics.json`: Replay statistics (if saved)

### Performance Issues

If replay is too slow:
- Increase `--speed` multiplier
- Reduce `REPLAY_INTER_MESSAGE_DELAY` in config
- Use filtering to reduce message count

If replay is too fast:
- Decrease `--speed` multiplier
- Use `--step-mode` for manual control
- Add breakpoints to pause at interesting messages

## Integration with Navigation Toolkit

### Setup Process

1. **Configure the navigation toolkit** to listen on UDP port 4001:
   ```python
   # In config.py
   UDP_PORT = 4001
   UDP_HOST = '0.0.0.0'
   PROTOCOL_MODE = 'auto'  # Auto-detect message types
   ```

2. **Start the navigation toolkit**:
   ```bash
   python main.py
   ```

3. **Run the replay** in a separate terminal:
   ```bash
   python replay_udp_events.py
   ```

### Validation

To verify the system is working:
1. Check navigation toolkit logs for received messages
2. Observe navigation display updates
3. Use `--verbose` mode to see sent message confirmation
4. Compare parser statistics before/after replay

### Protocol Modes

The navigation toolkit supports different protocol modes:
- `'nmea'`: NMEA 0183 sentences only
- `'adsb'`: ADS-B binary messages only  
- `'novatel'`: Novatel binary protocol only
- `'auto'`: Automatic protocol detection (recommended)

Use `'auto'` mode to handle mixed message types in your log file.

## Advanced Usage

### Custom Filtering

Create custom filters programmatically:
```python
from message_filter import MessageFilter

filter_obj = MessageFilter()
filter_obj.add_custom_filter(
    lambda data, msg_num: len(data) > 100 and b'GPS' in data,
    name="large_gps_messages",
    description="Large messages containing GPS"
)
```

### Custom Breakpoints

Add sophisticated breakpoints:
```python
from breakpoint_manager import BreakpointManager

bp_manager = BreakpointManager()
bp_manager.add_custom_breakpoint(
    lambda data, msg_num, context: context.get('parse_time', 0) > 0.1,
    name="slow_parsing",
    description="Break on slow parsing (>100ms)"
)
```

### Statistics Analysis

Analyze saved statistics:
```python
import json

with open('logs/replay_statistics.json') as f:
    stats = json.load(f)

print(f"Messages per second: {stats['messages_per_second']:.1f}")
print(f"Filter pass rate: {stats['filter_stats']['pass_rate']:.1f}%")
```

## Best Practices

### Development Workflow

1. **Start with interactive mode** to understand your data
2. **Use filtering** to focus on problematic messages
3. **Set breakpoints** on error conditions
4. **Save statistics** to track improvements
5. **Use loop mode** for continuous testing during development

### Testing Strategy

1. **Unit Testing**: Test individual components
2. **Integration Testing**: Full replay → parse → display pipeline
3. **Performance Testing**: High-speed replay with large datasets
4. **Regression Testing**: Verify changes don't break existing functionality

### Data Management

1. **Keep original log files** as reference
2. **Create filtered subsets** for specific testing
3. **Document message sources** and flight conditions
4. **Version control** log files with code changes

This comprehensive replay system provides powerful capabilities for testing and debugging your navigation toolkit with real flight data in a controlled environment.