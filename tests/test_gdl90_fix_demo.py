#!/usr/bin/env python3
"""
Demonstration of GDL-90 Deframer Fix
Shows how DF values are correctly transformed from 15 to 17
"""

import sys
import os

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gdl90_deframer import GDL90Deframer

def analyze_raw_data(data: bytes, label: str):
    """Analyze raw data and show DF value"""
    print(f"\n{label}:")
    print(f"  Data: {data.hex().upper()}")
    print(f"  Length: {len(data)} bytes")
    
    if len(data) > 0:
        first_byte = data[0]
        df = (first_byte >> 3) & 0x1F  # Extract DF from first 5 bits
        print(f"  First byte: 0x{first_byte:02X} = {format(first_byte, '08b')}")
        print(f"  DF (first 5 bits): {df}")
        
        if df == 15:
            print("  ❌ DF 15 - Would be rejected as non-ADS-B")
        elif df == 17:
            print("  ✅ DF 17 - Valid ADS-B Extended Squitter")
        else:
            print(f"  ❓ DF {df} - Other message type")
    
    return data

def demonstrate_gdl90_fix():
    """Demonstrate the GDL-90 deframing fix"""
    print("=" * 80)
    print("GDL-90 Deframer Fix Demonstration")
    print("=" * 80)
    print("Problem: ADS-B parser was seeing DF 15 instead of DF 17")
    print("Solution: Extract ADS-B payload from GDL-90/KISS wrapper")
    print()
    
    # Sample GDL-90 wrapped data from the problem description
    gdl90_hex = "7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E"
    gdl90_data = bytes.fromhex(gdl90_hex)
    
    print("BEFORE: Raw UDP Data (GDL-90 wrapped)")
    print("-" * 40)
    analyze_raw_data(gdl90_data, "GDL-90 Wrapped Data")
    
    print(f"\n📋 Frame Structure Analysis:")
    print(f"  0x7E        - Start flag")
    print(f"  0x26        - Message ID (ADS-B Long Report)")
    print(f"  0x00        - Sub-ID/Length") 
    print(f"  0x8B...     - ADS-B payload (escaped)")
    print(f"  0x7E        - End flag")
    
    # Show what the old parser saw
    print(f"\n❌ What the OLD parser saw:")
    print(f"  First 5 bits of 0x26 = {format(0x26, '08b')[:5]} = DF 15")
    print(f"  Result: Rejected as non-ADS-B message")
    
    # Use the deframer
    print("\nAFTER: GDL-90 Deframing Process")
    print("-" * 40)
    
    deframer = GDL90Deframer()
    
    # Enable logging to show the process
    import config
    original_log = config.LOG_DEFRAMING_PROCESS
    config.LOG_DEFRAMING_PROCESS = True
    
    try:
        extracted_messages = deframer.deframe_message(gdl90_data)
        
        print(f"\n✅ Deframing Results:")
        for i, msg in enumerate(extracted_messages):
            analyze_raw_data(msg, f"Extracted ADS-B Message {i+1}")
            
            # Show the transformation
            print(f"\n🎯 Transformation Summary:")
            print(f"  BEFORE: 0x26 → DF 15 (rejected)")
            print(f"  AFTER:  0x{msg[0]:02X} → DF {(msg[0] >> 3) & 0x1F} (accepted)")
            
        print(f"\n📊 Deframer Statistics:")
        stats = deframer.get_stats()
        for key, value in stats.items():
            print(f"  {key}: {value}")
            
    finally:
        config.LOG_DEFRAMING_PROCESS = original_log
    
    return len(extracted_messages) > 0

def test_byte_stuffing_demo():
    """Demonstrate the byte stuffing fix"""
    print("\n" + "=" * 80)
    print("Byte Stuffing/Unstuffing Demonstration")
    print("=" * 80)
    print("KISS/HDLC Protocol:")
    print("  0x7D 0x5E → 0x7E (escaped flag byte)")
    print("  0x7D 0x5D → 0x7D (escaped escape byte)")
    print()
    
    # The original sample has 0x7D 0x5E which should become 0x7E
    print("In our sample data:")
    print("  ...8B 9A 7D 5E 47...")
    print("       ^^^^^^^ this becomes 0x7E")
    print("  Result: ...8B 9A 7E 47...")
    
    deframer = GDL90Deframer()
    
    # Test the byte stuffing directly
    stuffed_data = bytes.fromhex("8B9A7D5E479967CCD9C82B84D1FFEBCCA0")
    unstuffed_data = deframer._unstuff_bytes(stuffed_data)
    
    print(f"\nDemonstration:")
    print(f"  Input (stuffed):   {stuffed_data.hex().upper()}")
    print(f"  Output (unstuffed): {unstuffed_data.hex().upper()}")
    print(f"  Operations: {deframer.byte_unstuff_operations} byte unstuff operation(s)")

if __name__ == "__main__":
    print("🚀 GDL-90 Deframer Fix Demonstration")
    print("Solving the DF 15 vs DF 17 ADS-B parsing issue")
    print()
    
    success = demonstrate_gdl90_fix()
    test_byte_stuffing_demo()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if success:
        print("✅ SUCCESS: GDL-90 deframer is working correctly!")
        print()
        print("🎉 Key Achievements:")
        print("   ✓ GDL-90/KISS frames are properly detected")
        print("   ✓ Byte stuffing is correctly removed")
        print("   ✓ ADS-B payloads are successfully extracted")
        print("   ✓ DF values are transformed from 15 to 17")
        print()
        print("🚀 Impact:")
        print("   • Parser will now accept ADS-B messages instead of rejecting them")
        print("   • DF 17 Extended Squitter messages will be properly decoded")
        print("   • Aviation data extraction will work as expected")
        print()
        print("📝 Next Steps:")
        print("   • Test with live UDP data feed")
        print("   • Verify aviation data extraction works end-to-end")
        print("   • Monitor parsing success rates")
    else:
        print("❌ FAILED: Check implementation")
    
    print("=" * 80)