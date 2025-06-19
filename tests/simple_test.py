#!/usr/bin/env python3
"""
Simple test script that works without external dependencies
Tests core functionality of the navigation system
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_config():
    """Test configuration module"""
    print("Testing config module...")
    try:
        import config
        
        # Test basic config values
        assert hasattr(config, 'UDP_PORT')
        assert hasattr(config, 'UDP_HOST')
        assert hasattr(config, 'PROTOCOL_MODE')
        assert config.UDP_PORT > 0
        assert config.UDP_PORT <= 65535
        
        print("✅ Config module - PASSED")
        return True
    except Exception as e:
        print(f"❌ Config module - FAILED: {e}")
        return False

def test_gdl90_deframer():
    """Test GDL-90 deframer functionality"""
    print("Testing GDL-90 deframer...")
    try:
        from gdl90_deframer import GDL90Deframer, deframe_gdl90_data
        
        # Create deframer
        deframer = GDL90Deframer()
        
        # Test initialization
        assert deframer.frames_processed == 0
        assert deframer.adsb_messages_found == 0
        
        # Test with sample data from problem description
        sample_data = bytes.fromhex("7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E")
        expected_output = bytes.fromhex("8B9A7E479967CCD9C82B84D1FFEBCCA0")
        
        # Disable logging for test
        import config
        original_log = config.LOG_DEFRAMING_PROCESS
        config.LOG_DEFRAMING_PROCESS = False
        
        try:
            messages = deframer.deframe_message(sample_data)
            
            # Verify extraction worked
            assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
            assert messages[0] == expected_output, f"Expected {expected_output.hex()}, got {messages[0].hex()}"
            
            # Check DF field
            df = (messages[0][0] >> 3) & 0x1F
            assert df == 17, f"Expected DF 17, got {df}"
            
            # Test statistics
            stats = deframer.get_stats()
            assert stats['frames_processed'] >= 1
            assert stats['adsb_messages_found'] >= 1
            
            # Test convenience function
            conv_messages = deframe_gdl90_data(sample_data)
            assert conv_messages == messages
            
            # Test frame detection
            assert deframer.is_gdl90_frame(sample_data) == True
            assert deframer.is_gdl90_frame(b"not_gdl90") == False
            
        finally:
            config.LOG_DEFRAMING_PROCESS = original_log
        
        print("✅ GDL-90 deframer - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ GDL-90 deframer - FAILED: {e}")
        return False

def test_navigation_display():
    """Test navigation display functionality"""
    print("Testing navigation display...")
    try:
        from navigation_display import NavigationDisplay
        
        display = NavigationDisplay()
        
        # Test initialization
        assert display.display_count == 0
        
        # Test coordinate formatting
        nav_data = {
            'latitude_decimal': 48.1173,
            'longitude_decimal': -122.4194,  # West longitude
            'altitude_ft': 35000,
            'speed_knots': 450,
            'heading': 280
        }
        
        formatted = display.format_navigation_data(nav_data)
        
        # Verify basic formatting
        assert "48.117300°N" in formatted
        assert "122.419400°W" in formatted  # Should show as West
        assert "35,000 ft" in formatted
        assert "450.0 knots" in formatted
        assert "280°" in formatted
        
        # Test helper functions
        assert display._heading_to_direction(0) == "North"
        assert display._heading_to_direction(90) == "East"
        assert display._heading_to_direction(180) == "South"
        assert display._heading_to_direction(270) == "West"
        
        assert display._gps_quality_text(1) == "GPS Fix"
        assert display._gps_quality_text(99) == "Unknown (99)"
        
        # Test stats
        stats = display.get_stats()
        assert 'displays_rendered' in stats
        
        print("✅ Navigation display - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Navigation display - FAILED: {e}")
        return False

def test_udp_listener():
    """Test UDP listener (without actually binding to socket)"""
    print("Testing UDP listener...")
    try:
        from udp_listener import UDPListener
        
        # Mock callback
        received_data = []
        def callback(data):
            received_data.append(data)
        
        listener = UDPListener(callback)
        
        # Test initialization
        assert listener.data_callback == callback
        assert listener.listening == False
        assert listener.socket is None
        
        # Test stats
        stats = listener.get_stats()
        assert 'listening' in stats
        assert 'error_count' in stats
        assert stats['listening'] == False
        
        print("✅ UDP listener - PASSED")
        return True
        
    except Exception as e:
        print(f"❌ UDP listener - FAILED: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("  Novatel ProPak6 Navigation Data Toolkit - Simple Tests")
    print("=" * 60)
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    print()
    
    tests = [
        test_config,
        test_gdl90_deframer,
        test_navigation_display,
        test_udp_listener
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__} - EXCEPTION: {e}")
            failed += 1
        print()
    
    print("=" * 60)
    print("  TEST SUMMARY")
    print("=" * 60)
    print(f"Total tests: {passed + failed}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 ALL CORE TESTS PASSED!")
        print("\nNote: NMEA and ADS-B parser tests require external dependencies:")
        print("  - pynmea2 (for NMEA parsing)")
        print("  - pyModeS (for ADS-B parsing)")
        print("  - pytest (for full test suite)")
        print("\nInstall dependencies with: pip install -r requirements.txt")
        return 0
    else:
        success_rate = (passed / (passed + failed)) * 100
        print(f"\n📊 Success Rate: {success_rate:.1f}%")
        return 1

if __name__ == "__main__":
    sys.exit(main())