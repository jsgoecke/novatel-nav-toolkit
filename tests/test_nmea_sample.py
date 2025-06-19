"""
Test script with sample NMEA data to demonstrate the navigation listener
This script simulates UDP data reception without requiring network setup
"""

import time
import threading
from datetime import datetime, timezone

# Sample NMEA sentences from a typical aircraft GPS system
SAMPLE_NMEA_DATA = [
    "$GPGGA,123519,3404.7041778,N,07710.3803362,W,2,10,1.2,1085.6,M,46.9,M,,*42",
    "$GPRMC,123519,A,3404.7041778,N,07710.3803362,W,450.0,095.12,230394,003.1,W*6A",
    "$GPVTG,095.12,T,098.22,M,450.0,N,833.4,K*69",
    "$GPGLL,3404.7041778,N,07710.3803362,W,123519,A*2D",
    "$GPGGA,123520,3404.7045,N,07710.3800,W,2,10,1.2,1086.2,M,46.9,M,,*4E",
    "$GPRMC,123520,A,3404.7045,N,07710.3800,W,451.2,095.8,230394,003.1,W*5C"
]


class MockNMEAParser:
    """Mock NMEA parser that works without pynmea2 dependency"""
    
    def __init__(self):
        self.sentences_parsed = 0
        self.parse_error_count = 0
        self.last_valid_data = {}
    
    def parse_sentence(self, sentence):
        """Parse NMEA sentence using basic string parsing"""
        try:
            if not sentence.startswith('$'):
                return None
                
            # Remove checksum
            if '*' in sentence:
                sentence = sentence.split('*')[0]
            
            parts = sentence.split(',')
            sentence_type = parts[0][3:6]  # Extract sentence type (GGA, RMC, etc.)
            
            data = {}
            
            if sentence_type == 'GGA' and len(parts) >= 15:
                # GGA: Global Positioning System Fix Data
                if parts[2] and parts[4]:  # lat and lon
                    data['latitude'] = self._parse_coordinate(parts[2])
                    data['longitude'] = self._parse_coordinate(parts[4])
                    data['latitude_dir'] = parts[3]
                    data['longitude_dir'] = parts[5]
                if parts[9]:  # altitude
                    data['altitude_m'] = float(parts[9])
                if parts[6]:  # GPS quality
                    data['gps_quality'] = int(parts[6])
                if parts[7]:  # satellites
                    data['satellites'] = int(parts[7])
                    
            elif sentence_type == 'RMC' and len(parts) >= 12:
                # RMC: Recommended Minimum Course
                if parts[3] and parts[5]:  # lat and lon
                    data['latitude'] = self._parse_coordinate(parts[3])
                    data['longitude'] = self._parse_coordinate(parts[5])
                    data['latitude_dir'] = parts[4]
                    data['longitude_dir'] = parts[6]
                if parts[7]:  # speed
                    data['speed_knots'] = float(parts[7])
                if parts[8]:  # heading
                    data['heading'] = float(parts[8])
                data['status'] = parts[2]
                
            elif sentence_type == 'VTG' and len(parts) >= 9:
                # VTG: Track Made Good and Ground Speed
                if parts[1]:  # true track
                    data['heading'] = float(parts[1])
                if parts[5]:  # speed in knots
                    data['speed_knots'] = float(parts[5])
                if parts[7]:  # speed in km/h
                    data['speed_kmh'] = float(parts[7])
            
            if data:
                data['parsed_timestamp'] = datetime.now(timezone.utc)
                self.sentences_parsed += 1
                self.last_valid_data.update(data)
                return data
                
            return None
            
        except Exception as e:
            self.parse_error_count += 1
            return None
    
    def _parse_coordinate(self, coord_str):
        """Parse NMEA coordinate format (DDMM.MMMM) to decimal degrees"""
        if not coord_str:
            return 0.0
        
        # NMEA format: DDMM.MMMM or DDDMM.MMMM
        coord = float(coord_str)
        
        # Extract degrees and minutes
        if coord >= 10000:  # longitude (DDDMM.MMMM)
            degrees = int(coord / 100)
            minutes = coord - (degrees * 100)
        else:  # latitude (DDMM.MMMM)
            degrees = int(coord / 100)
            minutes = coord - (degrees * 100)
        
        # Convert to decimal degrees
        return degrees + (minutes / 60.0)
    
    def get_latest_navigation_data(self):
        """Get latest navigation data with unit conversions"""
        nav_data = self.last_valid_data.copy()
        
        # Convert coordinates to signed decimal degrees
        if 'latitude' in nav_data and 'longitude' in nav_data:
            lat = nav_data['latitude']
            lon = nav_data['longitude']
            
            if nav_data.get('latitude_dir') == 'S':
                lat = -lat
            if nav_data.get('longitude_dir') == 'W':
                lon = -lon
                
            nav_data['latitude_decimal'] = round(lat, 6)
            nav_data['longitude_decimal'] = round(lon, 6)
        
        # Convert altitude to feet
        if 'altitude_m' in nav_data:
            nav_data['altitude_ft'] = round(nav_data['altitude_m'] * 3.28084, 1)
        
        # Convert speed to different units
        if 'speed_knots' in nav_data:
            knots = nav_data['speed_knots']
            nav_data['speed_kmh'] = round(knots * 1.852, 1)
            nav_data['speed_mph'] = round(knots * 1.15078, 1)
        
        return nav_data
    
    def get_stats(self):
        """Get parser statistics"""
        total = self.sentences_parsed + self.parse_error_count
        success_rate = (self.sentences_parsed / max(1, total)) * 100
        return {
            'sentences_parsed': self.sentences_parsed,
            'parse_errors': self.parse_error_count,
            'success_rate': round(success_rate, 1)
        }


def simulate_udp_data(parser, display):
    """Simulate receiving UDP NMEA data"""
    print("Simulating Novatel ProPak6 navigation data...")
    print("This demo shows sample aircraft navigation data\n")
    
    for i, sentence in enumerate(SAMPLE_NMEA_DATA * 3):  # Repeat data 3 times
        # Parse the sentence
        parsed_data = parser.parse_sentence(sentence)
        
        # Get latest navigation data
        nav_data = parser.get_latest_navigation_data()
        stats = parser.get_stats()
        stats['listening'] = True
        stats['displays_rendered'] = i + 1
        
        # Display the data
        display.display(nav_data, stats)
        
        # Wait before next update
        time.sleep(2.0)
    
    print("\nDemo completed!")
    print("To use with real Novatel ProPak6 data:")
    print("1. Install Python and pynmea2: pip install pynmea2")
    print("2. Connect to aircraft WiFi")
    print("3. Run: python main.py")


def main(test_mode=False):
    """Run the test demonstration"""
    try:
        # Add parent directory to path for imports
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Import our display module
        from navigation_display import NavigationDisplay
        
        # Create parser and display
        parser = MockNMEAParser()
        display = NavigationDisplay()
        
        if test_mode:
            # In test mode, just verify imports and basic functionality
            print("Test mode: Verifying NMEA parser functionality...")
            
            # Test parsing a few sample sentences
            for sentence in SAMPLE_NMEA_DATA[:3]:
                parsed_data = parser.parse_sentence(sentence)
                if parsed_data:
                    print(f"✅ Parsed: {sentence[:20]}...")
                else:
                    print(f"❌ Failed to parse: {sentence[:20]}...")
            
            # Get stats
            stats = parser.get_stats()
            print(f"✅ Test complete - Parsed {stats['sentences_parsed']} sentences")
            return True
        else:
            # Run full simulation
            simulate_udp_data(parser, display)
            return True
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    import sys
    test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"
    success = main(test_mode)
    sys.exit(0 if success else 1)