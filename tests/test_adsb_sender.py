#!/usr/bin/env python3
"""
Test ADS-B UDP sender to verify the aviation listener is working
Sends sample ADS-B messages to localhost:4001
"""

import socket
import time
import sys

# Sample ADS-B messages (hex strings) for testing different message types
SAMPLE_ADSB_MESSAGES = [
    "8D40621D58C382D4623706800000",      # Position message (TC 9-18) - Aircraft location
    "8D40621D99B9C5E0A0000000000000",    # Velocity message (TC 19) - Speed and heading
    "8D40621D20230B2C0000000000000000",  # Identification message (TC 1-4) - Callsign
    "8D4CA251EA42A8300000000000000000",  # Position from another aircraft ICAO 4CA251
]

def send_test_data(host='localhost', port=4001, interval=2.0, test_mode=False):
    """
    Send test ADS-B data via UDP to test the aviation listener
    
    Sends a cycle of sample ADS-B messages including position, velocity,
    and identification data to verify the listener can parse aviation data.
    
    Args:
        host (str): Target hostname or IP address (default: 'localhost')
        port (int): Target UDP port number (default: 4001)
        interval (float): Time interval between messages in seconds (default: 2.0)
        test_mode (bool): If True, send limited messages and exit (default: False)
        
    Raises:
        socket.error: If UDP socket operations fail
        KeyboardInterrupt: When user stops the sender with Ctrl+C
        ValueError: If hex message conversion fails
    """
    
    print(f"ADS-B UDP Test Sender")
    print(f"Target: {host}:{port}")
    print(f"Interval: {interval}s")
    if not test_mode:
        print("Press Ctrl+C to stop")
    else:
        print("Test mode: Sending limited messages")
    print("-" * 40)
    
    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    try:
        message_count = 0
        cycles = 0
        max_cycles = 2 if test_mode else float('inf')
        
        while cycles < max_cycles:
            for hex_message in SAMPLE_ADSB_MESSAGES:
                try:
                    # Convert hex string to bytes
                    message_bytes = bytes.fromhex(hex_message)
                    
                    # Send the message
                    sock.sendto(message_bytes, (host, port))
                    message_count += 1
                    
                    print(f"Sent #{message_count}: {hex_message} ({len(message_bytes)} bytes)")
                    
                    if test_mode:
                        time.sleep(0.1)  # Shorter delay in test mode
                    else:
                        time.sleep(interval)
                    
                except Exception as e:
                    print(f"Error sending data: {e}")
                    return False
            
            cycles += 1
            
        print(f"✅ Completed. Total messages sent: {message_count}")
        return True
                    
    except KeyboardInterrupt:
        print(f"\nStopped. Total messages sent: {message_count}")
        return True
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    finally:
        sock.close()

if __name__ == "__main__":
    # Parse command line arguments
    host = 'localhost'
    port = 4001
    interval = 2.0
    test_mode = False
    
    # Check for test mode flag
    if '--test' in sys.argv:
        test_mode = True
        sys.argv.remove('--test')
    
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print("Usage: python test_adsb_sender.py [host] [port] [interval] [--test]")
            print("Defaults: localhost 4001 2.0")
            print("--test: Run in test mode (limited messages)")
            sys.exit(0)
        host = sys.argv[1]
    
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print("Error: Invalid port number")
            sys.exit(1)
    
    if len(sys.argv) > 3:
        try:
            interval = float(sys.argv[3])
        except ValueError:
            print("Error: Invalid interval")
            sys.exit(1)
    
    success = send_test_data(host, port, interval, test_mode)
    sys.exit(0 if success else 1)