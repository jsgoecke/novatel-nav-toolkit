"""
Unit tests for NavigationDisplay module
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from io import StringIO

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from navigation_display import NavigationDisplay
import config


class TestNavigationDisplay:
    """Test navigation data display functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.display = NavigationDisplay()
    
    def test_initialization(self):
        """Test NavigationDisplay initialization"""
        assert self.display.display_count == 0
    
    def test_format_navigation_data_nmea(self):
        """Test formatting NMEA navigation data"""
        nav_data = {
            'latitude_decimal': 48.1173,
            'longitude_decimal': 11.5167,
            'altitude_m': 545.4,
            'altitude_ft': 1789.4,
            'speed_knots': 22.4,
            'speed_kmh': 41.5,
            'speed_mph': 25.8,
            'heading': 84.4,
            'gps_quality': 1,
            'satellites': 8,
            'status': 'A',
            'parsed_timestamp': datetime(2023, 6, 15, 12, 35, 19, tzinfo=timezone.utc)
        }
        
        stats = {
            'sentences_parsed': 100,
            'parse_errors': 5,
            'success_rate': 95.2
        }
        
        result = self.display.format_navigation_data(nav_data, stats)
        
        assert "Novatel ProPak6 Navigation Data (NMEA)" in result
        assert "48.117300°N, 11.516700°E" in result
        assert "1,789 ft" in result
        assert "22.4 knots" in result
        assert "084° (East)" in result
        assert "GPS Fix (8 satellites)" in result
        assert "Active" in result
        assert "NMEA sentences parsed: 100" in result
        assert "Parse errors: 5" in result
        assert "Success rate: 95.2%" in result
    
    def test_format_navigation_data_adsb(self):
        """Test formatting ADS-B aviation data"""
        nav_data = {
            'icao': '4840D6',
            'callsign': 'UAL1234',
            'type_code': 4,
            'latitude_decimal': 37.7749,
            'longitude_decimal': -122.4194,
            'altitude_ft': 35000,
            'speed_knots': 450,
            'heading': 280,
            'vertical_rate': 1500,
            'parsed_timestamp': datetime(2023, 6, 15, 12, 35, 19, tzinfo=timezone.utc)
        }
        
        stats = {
            'messages_parsed': 50,
            'aircraft_tracked': 5,
            'success_rate': 88.5
        }
        
        result = self.display.format_navigation_data(nav_data, stats)
        
        assert "Novatel ProPak6 Aviation Data (ADS-B)" in result
        assert "37.774900°N, 122.419400°W" in result
        assert "35,000 ft" in result
        assert "450.0 knots" in result
        assert "280° (West)" in result
        assert "ICAO:      4840D6" in result
        assert "Callsign:  UAL1234" in result
        assert "Type Code: 4" in result
        assert "1,500 ft/min climbing" in result
        assert "ADS-B messages parsed: 50" in result
        assert "Aircraft tracked: 5" in result
    
    def test_format_navigation_data_no_position(self):
        """Test formatting data with no GPS position"""
        nav_data = {
            'speed_knots': 22.4,
            'heading': 84.4,
            'parsed_timestamp': datetime(2023, 6, 15, 12, 35, 19, tzinfo=timezone.utc)
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "Position:  No GPS fix" in result
        assert "22.4 knots" in result
    
    def test_format_navigation_data_no_altitude(self):
        """Test formatting data with no altitude"""
        nav_data = {
            'latitude_decimal': 48.1173,
            'longitude_decimal': 11.5167,
            'speed_knots': 22.4
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "Altitude:  No data" in result
    
    def test_format_navigation_data_no_speed(self):
        """Test formatting data with no speed"""
        nav_data = {
            'latitude_decimal': 48.1173,
            'longitude_decimal': 11.5167,
            'heading': 84.4
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "Speed:     No data" in result
    
    def test_format_navigation_data_no_heading(self):
        """Test formatting data with no heading"""
        nav_data = {
            'latitude_decimal': 48.1173,
            'longitude_decimal': 11.5167,
            'speed_knots': 22.4
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "Heading:   No data" in result
    
    def test_format_navigation_data_no_gps_data(self):
        """Test formatting data with no GPS quality data"""
        nav_data = {
            'latitude_decimal': 48.1173,
            'longitude_decimal': 11.5167
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "GPS:       No data" in result
    
    @patch('config.ALTITUDE_UNITS', 'feet')
    def test_format_altitude_feet_only(self):
        """Test altitude formatting with feet only"""
        nav_data = {
            'altitude_ft': 1789.4,
            'altitude_m': 545.4
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "1,789 ft" in result
        assert " m" not in result
    
    @patch('config.ALTITUDE_UNITS', 'meters')
    def test_format_altitude_meters_only(self):
        """Test altitude formatting with meters only"""
        nav_data = {
            'altitude_ft': 1789.4,
            'altitude_m': 545.4
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "545 m" in result
        assert " ft" not in result
    
    @patch('config.ALTITUDE_UNITS', 'both')
    def test_format_altitude_both_units(self):
        """Test altitude formatting with both units"""
        nav_data = {
            'altitude_ft': 1789.4,
            'altitude_m': 545.4
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "1,789 ft (545 m)" in result
    
    @patch('config.SPEED_UNITS', 'knots')
    def test_format_speed_knots_only(self):
        """Test speed formatting with knots only"""
        nav_data = {
            'speed_knots': 22.4,
            'speed_kmh': 41.5,
            'speed_mph': 25.8
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "22.4 knots" in result
        assert "km/h" not in result
        assert "mph" not in result
    
    @patch('config.SPEED_UNITS', 'both')
    def test_format_speed_multiple_units(self):
        """Test speed formatting with multiple units"""
        nav_data = {
            'speed_knots': 22.4,
            'speed_kmh': 41.5,
            'speed_mph': 25.8
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "22.4 knots (41.5 km/h)" in result
    
    def test_format_vertical_rate_climbing(self):
        """Test formatting positive vertical rate"""
        nav_data = {
            'vertical_rate': 1500,
            'icao': '4840D6'  # Indicate ADS-B data
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "1,500 ft/min climbing" in result
    
    def test_format_vertical_rate_descending(self):
        """Test formatting negative vertical rate"""
        nav_data = {
            'vertical_rate': -800,
            'icao': '4840D6'
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "800 ft/min descending" in result
    
    def test_format_vertical_rate_level(self):
        """Test formatting zero vertical rate"""
        nav_data = {
            'vertical_rate': 0,
            'icao': '4840D6'
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "0 ft/min level" in result
    
    def test_format_status_active(self):
        """Test formatting active status"""
        nav_data = {
            'status': 'A'
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "Status:    Active" in result
    
    def test_format_status_void(self):
        """Test formatting void status"""
        nav_data = {
            'status': 'V'
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "Status:    Void" in result
    
    def test_format_combined_stats(self):
        """Test formatting combined NMEA and ADS-B statistics"""
        nav_data = {}
        stats = {
            'nmea_sentences_parsed': 75,
            'adsb_messages_parsed': 25,
            'adsb_aircraft_tracked': 3,
            'nmea_parse_errors': 2,
            'adsb_parse_errors': 1,
            'nmea_success_rate': 97.4,
            'adsb_success_rate': 96.2,
            'listening': True
        }
        
        result = self.display.format_navigation_data(nav_data, stats)
        
        assert "NMEA sentences parsed: 75" in result
        assert "ADS-B messages parsed: 25" in result
        assert "Aircraft tracked: 3" in result
        assert "Parse errors: 3 (NMEA: 2, ADS-B: 1)" in result
        assert "Success rate: NMEA 97.4%, ADS-B 96.2%" in result
        assert "UDP Listener: Active" in result
    
    def test_display_clear_screen(self):
        """Test display with screen clearing enabled"""
        nav_data = {'test': 'data'}
        
        with patch('config.CLEAR_SCREEN', True):
            with patch.object(self.display, '_clear_screen') as mock_clear:
                with patch('builtins.print') as mock_print:
                    self.display.display(nav_data)
                    
                    mock_clear.assert_called_once()
                    mock_print.assert_called()
                    assert self.display.display_count == 1
    
    def test_display_no_clear_screen(self):
        """Test display without screen clearing"""
        nav_data = {'test': 'data'}
        
        with patch('config.CLEAR_SCREEN', False):
            with patch.object(self.display, '_clear_screen') as mock_clear:
                with patch('builtins.print') as mock_print:
                    self.display.display(nav_data)
                    
                    mock_clear.assert_not_called()
                    mock_print.assert_called()
    
    @patch('os.name', 'nt')
    @patch('os.system')
    def test_clear_screen_windows(self, mock_system):
        """Test screen clearing on Windows"""
        self.display._clear_screen()
        mock_system.assert_called_with('cls')
    
    @patch('os.name', 'posix')
    @patch('os.system')
    def test_clear_screen_unix(self, mock_system):
        """Test screen clearing on Unix/Linux"""
        self.display._clear_screen()
        mock_system.assert_called_with('clear')
    
    def test_heading_to_direction_north(self):
        """Test heading to direction conversion for North"""
        assert self.display._heading_to_direction(0) == "North"
        assert self.display._heading_to_direction(360) == "North"
        assert self.display._heading_to_direction(5) == "North"
    
    def test_heading_to_direction_northeast(self):
        """Test heading to direction conversion for Northeast"""
        assert self.display._heading_to_direction(45) == "Northeast"
    
    def test_heading_to_direction_east(self):
        """Test heading to direction conversion for East"""
        assert self.display._heading_to_direction(90) == "East"
    
    def test_heading_to_direction_south(self):
        """Test heading to direction conversion for South"""
        assert self.display._heading_to_direction(180) == "South"
    
    def test_heading_to_direction_west(self):
        """Test heading to direction conversion for West"""
        assert self.display._heading_to_direction(270) == "West"
    
    def test_heading_to_direction_wraparound(self):
        """Test heading to direction conversion with values > 360"""
        assert self.display._heading_to_direction(405) == "Northeast"  # 405 % 360 = 45
    
    def test_gps_quality_text_valid_codes(self):
        """Test GPS quality text conversion for valid codes"""
        assert self.display._gps_quality_text(0) == "Invalid"
        assert self.display._gps_quality_text(1) == "GPS Fix"
        assert self.display._gps_quality_text(2) == "DGPS Fix"
        assert self.display._gps_quality_text(3) == "PPS Fix"
        assert self.display._gps_quality_text(4) == "RTK Fix"
        assert self.display._gps_quality_text(5) == "Float RTK"
        assert self.display._gps_quality_text(6) == "Estimated"
        assert self.display._gps_quality_text(7) == "Manual"
        assert self.display._gps_quality_text(8) == "Simulation"
    
    def test_gps_quality_text_invalid_code(self):
        """Test GPS quality text conversion for invalid code"""
        assert self.display._gps_quality_text(99) == "Unknown (99)"
    
    def test_get_stats(self):
        """Test getting display statistics"""
        self.display.display_count = 15
        
        stats = self.display.get_stats()
        
        assert stats['displays_rendered'] == 15
    
    def test_format_navigation_data_no_timestamp(self):
        """Test formatting data without parsed_timestamp"""
        nav_data = {
            'latitude_decimal': 48.1173,
            'longitude_decimal': 11.5167
        }
        
        with patch('navigation_display.datetime') as mock_datetime:
            mock_now = Mock()
            mock_now.strftime.return_value = "2023-06-15 12:35:19 UTC"
            mock_datetime.now.return_value = mock_now
            
            result = self.display.format_navigation_data(nav_data)
            
            assert "2023-06-15 12:35:19 UTC" in result
    
    @patch('config.COORDINATE_PRECISION', 2)
    def test_coordinate_precision(self):
        """Test coordinate precision formatting"""
        nav_data = {
            'latitude_decimal': 48.123456789,
            'longitude_decimal': 11.987654321
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "48.12°N, 11.99°E" in result
    
    def test_southern_western_coordinates(self):
        """Test formatting of southern and western coordinates"""
        nav_data = {
            'latitude_decimal': -33.8688,
            'longitude_decimal': -74.0060
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "33.868800°S, 74.006000°W" in result
    
    def test_format_gps_quality_only(self):
        """Test formatting GPS quality without satellite count"""
        nav_data = {
            'gps_quality': 2
        }
        
        result = self.display.format_navigation_data(nav_data)
        
        assert "GPS:       DGPS Fix" in result


if __name__ == "__main__":
    pytest.main([__file__])