#!/usr/bin/env python3
"""
Network diagnostic tool for UDP navigation listener
Checks port availability, network interfaces, and firewall issues
"""

import socket
import subprocess
import sys
import platform

def check_port_availability(port=4001, host='0.0.0.0'):
    """Check if the specified port is available for binding"""
    logger.info(f"Checking port availability: {host}:{port}")
    
    try:
        # Try to bind to the port
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        test_socket.bind((host, port))
        test_socket.close()
        logger.info(f"✓ Port {port} is available for binding")
        return True
    except Exception as e:
        logger.error(f"✗ Port {port} is NOT available: {e}")
        return False

def check_network_interfaces():
    """Check available network interfaces"""
    print("\nChecking network interfaces:")
    
    try:
        # Get hostname and IP addresses
        hostname = socket.gethostname()
        print(f"Hostname: {hostname}")
        
        # Get all IP addresses for this host
        ip_addresses = socket.getaddrinfo(hostname, None)
        unique_ips = set()
        
        for addr_info in ip_addresses:
            ip = addr_info[4][0]
            if ip not in unique_ips:
                unique_ips.add(ip)
                logger.info(f"  IP Address: {ip}")
        
        # Also check localhost
        localhost_ip = socket.gethostbyname('localhost')
        logger.info(f"  Localhost: {localhost_ip}")
        
    except Exception as e:
        logger.error(f"Error checking network interfaces: {e}")

def check_listening_ports():
    """Check what's currently listening on UDP ports"""
    print("\nChecking listening UDP ports:")
    
    try:
        system = platform.system().lower()
        
        if system == "windows":
            # Use netstat on Windows
            result = subprocess.run(['netstat', '-an', '-p', 'UDP'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                udp_lines = [line for line in lines if 'UDP' in line and ':4001' in line]
                if udp_lines:
                    logger.info("Found processes listening on port 4001:")
                    for line in udp_lines:
                        print(f"  {line.strip()}")
                else:
                    logger.info("No processes found listening on port 4001")
            else:
                logger.error("Could not run netstat command")
        else:
            # Use netstat on Unix-like systems
            result = subprocess.run(['netstat', '-ulnp'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                udp_lines = [line for line in lines if ':4001' in line]
                if udp_lines:
                    logger.info("Found processes listening on port 4001:")
                    for line in udp_lines:
                        logger.info(f"  {line.strip()}")
                else:
                    logger.info("No processes found listening on port 4001")
            else:
                logger.error("Could not run netstat command")
                
    except subprocess.TimeoutExpired:
        logger.error("Netstat command timed out")
    except Exception as e:
        logger.eror(f"Error checking listening ports: {e}")

def test_udp_loopback(port=4001):
    """Test UDP loopback communication"""
    logger.info(f"\nTesting UDP loopback on port {port}:")
    
    try:
        # Create receiver socket
        receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        receiver.settimeout(2.0)
        receiver.bind(('localhost', port))
        
        # Create sender socket
        sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Send test message
        test_message = "TEST_MESSAGE"
        sender.sendto(test_message.encode('utf-8'), ('localhost', port))
        logger.info(f"✓ Sent test message: {test_message}")
        
        # Try to receive
        data, addr = receiver.recvfrom(1024)
        received_message = data.decode('utf-8')
        
        if received_message == test_message:
            logger.info(f"✓ Successfully received test message: {received_message}")
            logger.info(f"✓ UDP loopback is working on port {port}")
            success = True
        else:
            logger.error(f"✗ Received different message: {received_message}")
            success = False
            
        receiver.close()
        sender.close()
        return success
        
    except socket.timeout:
        logger.error(f"✗ Timeout waiting for UDP message")
        return False
    except Exception as e:
        logger.error(f"✗ UDP loopback test failed: {e}")
        return False

def main():
    """Run network diagnostics"""
    logger.info("=" * 50)
    logger.info("Network Diagnostic Tool")
    logger.info("=" * 50)
    
    port = 4000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Error: Invalid port number")
            sys.exit(1)
    
    logger.info(f"Diagnosing UDP port {port}")
    logger.info()
    
    # Run diagnostics
    port_available = check_port_availability(port)
    check_network_interfaces()
    check_listening_ports()
    
    if port_available:
        test_udp_loopback(port)
    
    logger.info("\n" + "=" * 50)
    logger.info("Diagnostic Summary:")
    if port_available:
        logger.info("✓ Port is available and UDP loopback should work")
        logger.info("✓ The navigation listener should be able to bind to the port")
        logger.info("\nNext steps:")
        logger.info("1. Run the navigation listener: python main.py")
        logger.info("2. In another terminal, run the test sender: python test_udp_sender.py")
    else:
        logger.error("✗ Port binding issues detected")
        logger.error("✗ The navigation listener may not start properly")
        logger.errorint("\nTroubleshooting:")
        logger.error("1. Check if another application is using the port")
        logger.error("2. Try a different port with: python main.py -p <port>")
        logger.error("3. Check firewall settings")

if __name__ == "__main__":
    main()