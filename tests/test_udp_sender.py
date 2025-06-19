#!/usr/bin/env python3
"""
Test UDP sender to verify the navigation listener is working
Sends sample NMEA sentences to localhost:4001
"""

import socket
import time
import sys

# Sample NMEA sentences for testing
SAMPLE_NMEA_SENTENCES = [
    "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47",
    "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A",
    "$GPVTG,084.4,T,077.8,M,022.4,N,041.5,K*43",
    "$GPGLL,4807.038,N,01131.000,E,123519,A,*1D"
]

def send_test_data(host='localhost', port=4001, interval=2.0, test_mode=False):
    """
    Send test NMEA data via UDP to test the navigation listener
    
    Args:
        host (str): Target hostname or IP address (default: 'localhost')
        port (int): Target UDP port number (default: 4001)
        interval (float): Time interval between sentences in seconds (default: 2.0)
        test_mode (bool): If True, send limited messages and exit (default: False)
        
    Raises:
        socket.error: If UDP socket operations fail
        KeyboardInterrupt: When user stops the sender with Ctrl+C
    """
    
    print(f"UDP Test Sender")
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
        sentence_count = 0
        cycles = 0
        max_cycles = 2 if test_mode else float('inf')
        
        while cycles < max_cycles:
            for sentence in SAMPLE_NMEA_SENTENCES:
                try:
                    # Send the sentence
                    sock.sendto(sentence.encode('utf-8'), (host, port))
                    sentence_count += 1
                    
                    print(f"Sent #{sentence_count}: {sentence}")
                    
                    if test_mode:
                        time.sleep(0.1)  # Shorter delay in test mode
                    else:
                        time.sleep(interval)
                    
                except Exception as e:
                    print(f"Error sending data: {e}")
                    return False
            
            cycles += 1
            
        print(f"✅ Completed. Total sentences sent: {sentence_count}")
        return True
                    
    except KeyboardInterrupt:
        print(f"\nStopped. Total sentences sent: {sentence_count}")
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
            print("Usage: python test_udp_sender.py [host] [port] [interval] [--test]")
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