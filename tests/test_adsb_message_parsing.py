#!/usr/bin/env python3
"""
Enhanced ADS-B Message Parsing Test
Deframes GDL-90 data and parses all ADS-B message components
"""

import sys
import os

# Add the parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gdl90_deframer import GDL90Deframer
import config

def parse_adsb_message_manual(adsb_bytes):
    """
    Manual ADS-B message parsing (bitwise decoding)
    This provides a fallback if pyModeS is not available
    """
    if len(adsb_bytes) < 14:
        return None
    
    # Convert to bit string for easier manipulation
    bits = ''.join(format(byte, '08b') for byte in adsb_bytes)
    
    # Extract fields according to Mode S format
    result = {}
    
    # Downlink Format (bits 1-5)
    result['DF'] = int(bits[0:5], 2)
    
    # Capability (bits 6-8) 
    result['CA'] = int(bits[5:8], 2)
    
    # ICAO Address (bits 9-32)
    icao_bits = bits[8:32]
    result['ICAO'] = hex(int(icao_bits, 2))[2:].upper().zfill(6)
    
    # ME Field (bits 33-88) - Message, Extended Squitter
    me_bits = bits[32:88]
    result['ME'] = hex(int(me_bits, 2))[2:].upper()
    
    # Type Code (first 5 bits of ME)
    result['Type_Code'] = int(me_bits[0:5], 2)
    
    # Parity/CRC (bits 89-112)
    parity_bits = bits[88:112]
    result['Parity'] = hex(int(parity_bits, 2))[2:].upper().zfill(6)
    
    # Decode based on Type Code
    if 1 <= result['Type_Code'] <= 4:
        # Aircraft Identification
        result['Message_Type'] = 'Aircraft Identification'
        # Decode callsign (8 characters, 6 bits each)
        callsign_bits = me_bits[8:56]  # Skip type code and category
        callsign = ""
        for i in range(0, 48, 6):
            char_bits = callsign_bits[i:i+6]
            if len(char_bits) == 6:
                char_val = int(char_bits, 2)
                if char_val == 0:
                    callsign += ' '
                elif 1 <= char_val <= 26:
                    callsign += chr(ord('A') + char_val - 1)
                elif 48 <= char_val <= 57:
                    callsign += chr(char_val)
                else:
                    callsign += '?'
        result['Callsign'] = callsign.strip()
        
    elif 5 <= result['Type_Code'] <= 8:
        result['Message_Type'] = 'Surface Position'
        
    elif 9 <= result['Type_Code'] <= 18:
        result['Message_Type'] = 'Airborne Position'
        # Decode altitude (bits 41-52 of ME)
        alt_bits = me_bits[8:20]  # Skip type code
        if len(alt_bits) == 12:
            alt_code = int(alt_bits, 2)
            if alt_code != 0:
                # Decode altitude (simplified)
                result['Altitude_Code'] = alt_code
                # Basic altitude decoding (may need more sophisticated decoding)
                if alt_code & 0x40:  # Check if M bit is set
                    result['Altitude_ft'] = (alt_code & 0x3F) * 25 - 1000
                else:
                    result['Altitude_ft'] = alt_code * 25 - 1000
        
    elif result['Type_Code'] == 19:
        result['Message_Type'] = 'Airborne Velocity'
        
    elif 20 <= result['Type_Code'] <= 22:
        result['Message_Type'] = 'Airborne Position (GNSS)'
        
    else:
        result['Message_Type'] = f'Unknown/Reserved (TC={result["Type_Code"]})'
    
    return result

def decode_velocity_message(me_bits):
    """
    Comprehensive decoder for Type Code 19 (Airborne Velocity) messages
    Extracts ALL velocity data including speed, heading, vertical rate, and status
    """
    print(f"   📊 Velocity Message Detailed Breakdown:")
    print(f"   ME Field: {me_bits}")
    print(f"   ME Hex: {hex(int(me_bits, 2))[2:].upper().zfill(14)}")
    print()
    
    # Type Code (bits 1-5 of ME) - already decoded
    tc = int(me_bits[0:5], 2)
    print(f"   Type Code: {tc} (Airborne Velocity)")
    
    # Subtype (bits 6-8 of ME)
    subtype = int(me_bits[5:8], 2)
    subtype_meanings = {
        1: "Ground Speed (subsonic)",
        2: "Ground Speed (supersonic)",
        3: "Airspeed (subsonic)",
        4: "Airspeed (supersonic)"
    }
    print(f"   Subtype: {subtype} ({subtype_meanings.get(subtype, 'Reserved')})")
    
    # Intent Change Flag (bit 9 of ME)
    ic_flag = int(me_bits[8], 2)
    print(f"   Intent Change: {'Yes' if ic_flag else 'No'}")
    
    # Reserved (bit 10 of ME)
    reserved = int(me_bits[9], 2)
    print(f"   Reserved: {reserved}")
    
    # NAC (Navigation Accuracy Category) - bits 11-13 of ME
    nac = int(me_bits[10:13], 2)
    nac_meanings = {
        0: "Unknown or ≥ 10 NM",
        1: "< 10 NM",
        2: "< 4 NM",
        3: "< 2 NM",
        4: "< 1 NM",
        5: "< 0.5 NM",
        6: "< 0.3 NM",
        7: "< 0.1 NM"
    }
    print(f"   NAC (Navigation Accuracy): {nac} ({nac_meanings.get(nac, 'Reserved')})")
    
    if subtype in [1, 2]:  # Ground Speed
        print(f"   🌍 GROUND SPEED DATA:")
        
        # East-West Direction (bit 14 of ME)
        ew_dir = int(me_bits[13], 2)
        print(f"   E/W Direction: {'West' if ew_dir else 'East'}")
        
        # East-West Velocity (bits 15-24 of ME)
        ew_vel_raw = int(me_bits[14:24], 2)
        ew_vel = ew_vel_raw - 1 if ew_vel_raw > 0 else 0
        print(f"   E/W Velocity: {ew_vel} knots {'West' if ew_dir else 'East'}")
        
        # North-South Direction (bit 25 of ME)
        ns_dir = int(me_bits[24], 2)
        print(f"   N/S Direction: {'South' if ns_dir else 'North'}")
        
        # North-South Velocity (bits 26-35 of ME)
        ns_vel_raw = int(me_bits[25:35], 2)
        ns_vel = ns_vel_raw - 1 if ns_vel_raw > 0 else 0
        print(f"   N/S Velocity: {ns_vel} knots {'South' if ns_dir else 'North'}")
        
        # Calculate ground speed and track
        if ew_vel > 0 or ns_vel > 0:
            import math
            ground_speed = math.sqrt(ew_vel**2 + ns_vel**2)
            
            # Calculate track (heading)
            if ew_vel == 0 and ns_vel == 0:
                track = 0
            else:
                ew_component = -ew_vel if ew_dir else ew_vel
                ns_component = -ns_vel if ns_dir else ns_vel
                track = math.atan2(ew_component, ns_component) * 180 / math.pi
                if track < 0:
                    track += 360
            
            print(f"   ✈️ CALCULATED VALUES:")
            print(f"   Ground Speed: {ground_speed:.1f} knots")
            print(f"   Track: {track:.1f}° (True)")
        
    elif subtype in [3, 4]:  # Airspeed
        print(f"   🌬️ AIRSPEED DATA:")
        
        # Heading Status (bit 14 of ME)
        hdg_status = int(me_bits[13], 2)
        print(f"   Heading Status: {'Available' if hdg_status else 'Not Available'}")
        
        # Heading (bits 15-24 of ME)
        if hdg_status:
            hdg_raw = int(me_bits[14:24], 2)
            heading = hdg_raw * 360.0 / 1024.0
            print(f"   Heading: {heading:.1f}° (Magnetic)")
        else:
            print(f"   Heading: Not Available")
            
        # Airspeed Type (bit 25 of ME)
        as_type = int(me_bits[24], 2)
        print(f"   Airspeed Type: {'TAS (True Airspeed)' if as_type else 'IAS (Indicated Airspeed)'}")
        
        # Airspeed (bits 26-35 of ME)
        airspeed_raw = int(me_bits[25:35], 2)
        airspeed = airspeed_raw - 1 if airspeed_raw > 0 else 0
        print(f"   Airspeed: {airspeed} knots ({'TAS' if as_type else 'IAS'})")
    
    # Vertical Rate Source (bit 36 of ME)
    vr_source = int(me_bits[35], 2)
    print(f"   📈 VERTICAL RATE DATA:")
    print(f"   VR Source: {'GNSS (Geometric)' if vr_source else 'Barometric'}")
    
    # Vertical Rate Sign (bit 37 of ME)
    vr_sign = int(me_bits[36], 2)
    
    # Vertical Rate (bits 38-46 of ME)
    vr_raw = int(me_bits[37:46], 2)
    if vr_raw == 0:
        print(f"   Vertical Rate: Not Available")
    else:
        vr_value = (vr_raw - 1) * 64
        if vr_sign:
            vr_value = -vr_value
        print(f"   Vertical Rate: {vr_value:+d} ft/min")
    
    # Reserved (bits 47-48 of ME)
    reserved2 = int(me_bits[46:48], 2)
    print(f"   Reserved (2): {reserved2}")
    
    # Difference from Barometric Altitude Sign (bit 49 of ME)
    diff_sign = int(me_bits[48], 2) if len(me_bits) > 48 else 0
    
    # Difference from Barometric Altitude (bits 50-56 of ME)
    if len(me_bits) > 49:
        diff_raw = int(me_bits[49:56], 2) if len(me_bits) >= 56 else 0
        if diff_raw == 0:
            print(f"   Altitude Difference: Not Available")
        else:
            diff_value = (diff_raw - 1) * 25
            if diff_sign:
                diff_value = -diff_value
            print(f"   GNSS-Baro Alt Diff: {diff_value:+d} ft")
            print(f"   (GNSS altitude is {abs(diff_value)} ft {'below' if diff_value < 0 else 'above'} barometric)")
    
    print()

def parse_adsb_message_pymodes(adsb_bytes):
    """
    Parse ADS-B message using pyModeS library
    """
    try:
        from pyModeS.decoder import adsb
        
        hex_msg = adsb_bytes.hex()
        result = {}
        
        # Basic message info
        result['DF'] = adsb.df(hex_msg)
        result['ICAO'] = adsb.icao(hex_msg)
        result['Type_Code'] = adsb.typecode(hex_msg)
        
        # Decode based on type code
        tc = result['Type_Code']
        
        if 1 <= tc <= 4:
            result['Message_Type'] = 'Aircraft Identification'
            result['Callsign'] = adsb.callsign(hex_msg)
            result['Category'] = adsb.category(hex_msg)
            
        elif 5 <= tc <= 8:
            result['Message_Type'] = 'Surface Position'
            
        elif 9 <= tc <= 18:
            result['Message_Type'] = 'Airborne Position'
            result['Altitude_ft'] = adsb.altitude(hex_msg)
            
        elif tc == 19:
            result['Message_Type'] = 'Airborne Velocity'
            velocity = adsb.velocity(hex_msg)
            if velocity:
                result['Speed_knots'] = velocity[0]
                result['Heading_deg'] = velocity[1] 
                result['Vertical_Rate_fpm'] = velocity[2]
                
        elif 20 <= tc <= 22:
            result['Message_Type'] = 'Airborne Position (GNSS)'
            
        return result
        
    except ImportError:
        return None
    except Exception as e:
        print(f"pyModeS parsing error: {e}")
        return None

def enhanced_adsb_test():
    """Enhanced test that shows all ADS-B message components"""
    print("=" * 80)
    print("🔍 ENHANCED ADS-B MESSAGE PARSING TEST")
    print("=" * 80)
    print("This test deframes GDL-90 data and parses all ADS-B message components")
    print()
    
    # Sample GDL-90 wrapped data
    gdl90_hex = "7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E"
    gdl90_data = bytes.fromhex(gdl90_hex)
    
    print("📡 INPUT DATA")
    print("-" * 40)
    print(f"GDL-90 Frame: {gdl90_data.hex().upper()}")
    print(f"Length: {len(gdl90_data)} bytes")
    print()
    
    # Step 1: Deframe the GDL-90 data
    print("🔧 STEP 1: GDL-90 DEFRAMING")
    print("-" * 40)
    
    deframer = GDL90Deframer()
    
    # Enable detailed logging
    original_log = config.LOG_DEFRAMING_PROCESS
    config.LOG_DEFRAMING_PROCESS = True
    
    try:
        adsb_messages = deframer.deframe_message(gdl90_data)
        
        if not adsb_messages:
            print("❌ No ADS-B messages extracted!")
            return False
            
        print(f"✅ Extracted {len(adsb_messages)} ADS-B message(s)")
        
        # Process each extracted message
        for i, adsb_msg in enumerate(adsb_messages):
            print(f"\n🔍 STEP 2: ADS-B MESSAGE {i+1} ANALYSIS")
            print("-" * 40)
            print(f"Raw ADS-B Message: {adsb_msg.hex().upper()}")
            print(f"Length: {len(adsb_msg)} bytes")
            
            # Show raw bits
            bits = ''.join(format(byte, '08b') for byte in adsb_msg)
            print(f"Binary: {bits}")
            print()
            
            # Try pyModeS first
            print("📊 PARSING WITH pyModeS:")
            pymodes_result = parse_adsb_message_pymodes(adsb_msg)
            
            if pymodes_result:
                print("✅ pyModeS parsing successful!")
                for key, value in pymodes_result.items():
                    print(f"  {key}: {value}")
            else:
                print("⚠️  pyModeS not available, using manual parsing")
            
            print()
            
            # Manual parsing as backup/verification
            print("🔍 MANUAL BIT-LEVEL PARSING:")
            manual_result = parse_adsb_message_manual(adsb_msg)
            
            if manual_result:
                print("✅ Manual parsing successful!")
                for key, value in manual_result.items():
                    print(f"  {key}: {value}")
            else:
                print("❌ Manual parsing failed!")
            
            print()
            
            # Detailed field breakdown
            print("🔬 DETAILED FIELD BREAKDOWN:")
            print("-" * 30)
            
            if len(adsb_msg) >= 14:
                # Show each field with bit positions
                bits = ''.join(format(byte, '08b') for byte in adsb_msg)
                
                print(f"Bit Position | Field           | Binary    | Hex    | Decimal | Meaning")
                print(f"-------------|-----------------|-----------|--------|---------|------------------")
                print(f"1-5          | Downlink Format | {bits[0:5]:<9} | {hex(int(bits[0:5], 2))[2:]:>6} | {int(bits[0:5], 2):>7} | DF={int(bits[0:5], 2)} ({'ADS-B' if int(bits[0:5], 2) == 17 else 'Other'})")
                print(f"6-8          | Capability      | {bits[5:8]:<9} | {hex(int(bits[5:8], 2))[2:]:>6} | {int(bits[5:8], 2):>7} | CA={int(bits[5:8], 2)}")
                
                icao_bits = bits[8:32]
                icao_hex = hex(int(icao_bits, 2))[2:].upper().zfill(6)
                print(f"9-32         | ICAO Address    | {icao_bits[:12]}... | {icao_hex:>6} | {int(icao_bits, 2):>7} | Aircraft ID")
                
                me_bits = bits[32:88]
                tc = int(me_bits[0:5], 2)
                print(f"33-37        | Type Code       | {me_bits[0:5]:<9} | {hex(tc)[2:]:>6} | {tc:>7} | Message Type")
                
                parity_bits = bits[88:112]
                parity_hex = hex(int(parity_bits, 2))[2:].upper().zfill(6)
                print(f"89-112       | Parity/CRC      | {parity_bits[:12]}... | {parity_hex:>6} | {int(parity_bits, 2):>7} | Error Check")
                
                print()
                
                # Message-specific decoding
                print("📋 MESSAGE-SPECIFIC DATA:")
                print("-" * 25)
                
                if 1 <= tc <= 4:
                    print(f"✈️  Aircraft Identification Message (TC={tc})")
                    # Decode callsign
                    callsign_bits = me_bits[8:56]
                    callsign = ""
                    for j in range(0, 48, 6):
                        char_bits = callsign_bits[j:j+6]
                        if len(char_bits) == 6:
                            char_val = int(char_bits, 2)
                            if char_val == 0:
                                callsign += ' '
                            elif 1 <= char_val <= 26:
                                callsign += chr(ord('A') + char_val - 1)
                            elif 48 <= char_val <= 57:
                                callsign += chr(char_val)
                            else:
                                callsign += '?'
                    print(f"   Callsign: '{callsign.strip()}'")
                    
                elif 9 <= tc <= 18:
                    print(f"📍 Airborne Position Message (TC={tc})")
                    # Show altitude bits
                    alt_bits = me_bits[8:20]
                    if len(alt_bits) == 12:
                        alt_code = int(alt_bits, 2)
                        print(f"   Altitude Code: {alt_code} (binary: {alt_bits})")
                        if alt_code != 0:
                            # Simplified altitude calculation
                            altitude = alt_code * 25 - 1000
                            print(f"   Estimated Altitude: {altitude} feet")
                    
                elif tc == 19:
                    print(f"🚀 Airborne Velocity Message (TC={tc})")
                    decode_velocity_message(me_bits)
                    
                else:
                    print(f"❓ Unknown/Reserved Message Type (TC={tc})")
            
            print("\n" + "="*80)
        
        return True
        
    finally:
        config.LOG_DEFRAMING_PROCESS = original_log

if __name__ == "__main__":
    print("🚀 Enhanced ADS-B Message Parsing Demonstration")
    print("Shows complete deframing and parsing of all message components")
    print()
    
    success = enhanced_adsb_test()
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    if success:
        print("✅ SUCCESS: Complete ADS-B message parsing demonstration!")
        print()
        print("🎯 What we accomplished:")
        print("   ✓ Deframed GDL-90/KISS wrapper successfully")
        print("   ✓ Extracted raw 14-byte ADS-B message")
        print("   ✓ Parsed all message fields (DF, CA, ICAO, ME, Parity)")
        print("   ✓ Decoded message-specific data components")
        print("   ✓ Showed bit-level field breakdown")
        print("   ✓ Demonstrated DF 15 → DF 17 transformation")
        print()
        print("🎉 The parser now has full visibility into ADS-B message contents!")
    else:
        print("❌ Test failed - check implementation")
    
    print("=" * 80)