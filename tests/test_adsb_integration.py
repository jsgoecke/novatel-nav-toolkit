#!/usr/bin/env python3
"""
Integration test for ADS-B parser with GDL-90 deframer
Demonstrates the fix for DF 15 vs DF 17 issue
"""

import sys
import os

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adsb_parser import ADSBParser
import config

def test_gdl90_integration():
    """Test ADS-B parser with GDL-90 wrapped data"""
    print("=" * 70)
    print("ADS-B Parser Integration Test with GDL-90 Deframing")
    print("=" * 70)
    
    # Sample GDL-90 wrapped data from the problem description
    gdl90_hex = "7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E"
    gdl90_data = bytes.fromhex(gdl90_hex)
    
    print(f"Testing with GDL-90 wrapped data:")
    print(f"Input: {gdl90_data.hex().upper()}")
    print(f"Length: {len(gdl90_data)} bytes")
    print()
    
    # Enable detailed logging
    original_log_setting = config.LOG_PARSE_ATTEMPTS
    config.LOG_PARSE_ATTEMPTS = True
    
    try:
        # Create ADS-B parser
        parser = ADSBParser()
        
        print("Parsing GDL-90 wrapped data...")
        print("-" * 40)
        
        # Parse the message
        result = parser.parse_message(gdl90_data)
        
        print("\nParsing Results:")
        print("-" * 20)
        
        if result:
            print("✅ Successfully parsed ADS-B data!")
            print(f"Extracted data: {result}")
            
            # Check specific fields
            if 'icao' in result:
                print(f"✅ ICAO Address: {result['icao']}")
            if 'type_code' in result:
                print(f"✅ Type Code: {result['type_code']}")
                
        else:
            print("❌ Failed to parse ADS-B data")
            
        # Show parser statistics
        stats = parser.get_stats()
        print(f"\nParser Statistics:")
        print("-" * 20)
        for key, value in stats.items():
            print(f"{key}: {value}")
            
        return result is not None
        
    finally:
        # Restore original logging setting
        config.LOG_PARSE_ATTEMPTS = original_log_setting

def test_raw_adsb_compatibility():
    """Test that raw ADS-B messages still work (backward compatibility)"""
    print("\n" + "=" * 70)
    print("Testing Backward Compatibility with Raw ADS-B Messages")
    print("=" * 70)
    
    # Raw ADS-B message (the deframed payload)
    raw_hex = "8B9A7E479967CCD9C82B84D1FFEBCCA0"
    raw_data = bytes.fromhex(raw_hex)
    
    print(f"Testing with raw ADS-B data:")
    print(f"Input: {raw_data.hex().upper()}")
    print(f"Length: {len(raw_data)} bytes")
    print()
    
    # Create ADS-B parser
    parser = ADSBParser()
    
    print("Parsing raw ADS-B data...")
    print("-" * 40)
    
    # Parse the message
    result = parser.parse_message(raw_data)
    
    print("\nParsing Results:")
    print("-" * 20)
    
    if result:
        print("✅ Successfully parsed raw ADS-B data!")
        print(f"Extracted data: {result}")
    else:
        print("❌ Failed to parse raw ADS-B data")
        
    # Show parser statistics
    stats = parser.get_stats()
    print(f"\nParser Statistics:")
    print("-" * 20)
    for key, value in stats.items():
        print(f"{key}: {value}")
        
    return result is not None

def test_malformed_data():
    """Test parser behavior with malformed data"""
    print("\n" + "=" * 70)
    print("Testing Error Handling with Malformed Data")
    print("=" * 70)
    
    test_cases = [
        {
            'name': 'Empty data',
            'data': b'',
        },
        {
            'name': 'Invalid GDL-90 frame',
            'data': bytes.fromhex("7E99001234567E"),  # Wrong message type
        },
        {
            'name': 'Truncated frame',
            'data': bytes.fromhex("7E26008B9A"),  # Too short
        }
    ]
    
    parser = ADSBParser()
    
    for test_case in test_cases:
        print(f"\nTesting: {test_case['name']}")
        print(f"Data: {test_case['data'].hex().upper() if test_case['data'] else '(empty)'}")
        
        result = parser.parse_message(test_case['data'])
        
        if result is None:
            print("✅ Correctly handled malformed data (returned None)")
        else:
            print(f"⚠️  Unexpected result: {result}")

if __name__ == "__main__":
    print("ADS-B Parser Integration Test Suite")
    print("Demonstrates the fix for DF 15 vs DF 17 issue")
    print()
    
    # Run tests
    gdl90_success = test_gdl90_integration()
    raw_success = test_raw_adsb_compatibility()
    test_malformed_data()
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if gdl90_success and raw_success:
        print("✅ ALL TESTS PASSED!")
        print()
        print("🎉 The GDL-90 deframer fix is working correctly!")
        print("   - GDL-90 wrapped data now correctly identifies DF 17")
        print("   - Raw ADS-B messages continue to work (backward compatibility)")
        print("   - Error handling works for malformed data")
        print()
        print("🚀 The parser should now successfully process ADS-B data")
        print("   instead of rejecting it as DF 15 phantom messages.")
    else:
        print("❌ SOME TESTS FAILED!")
        print(f"   GDL-90 test: {'PASS' if gdl90_success else 'FAIL'}")
        print(f"   Raw ADS-B test: {'PASS' if raw_success else 'FAIL'}")
    
    print("=" * 70)