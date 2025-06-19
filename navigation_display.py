"""
Human-readable display formatter for navigation data
"""

import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any
import config


class NavigationDisplay:
    """Formats and displays navigation data in human-readable format"""
    
    def __init__(self):
        """Initialize display formatter"""
        self.display_count = 0
        
    def format_navigation_data(self, nav_data: Dict[str, Any], stats: Dict[str, Any] = None) -> str:
        """
        Format navigation data for display
        
        Args:
            nav_data: Navigation data dictionary
            stats: Optional statistics dictionary
            
        Returns:
            Formatted string for display
        """
        lines = []
        
        # Header
        lines.append("=" * 50)
        if 'icao' in nav_data:
            lines.append("    Novatel ProPak6 Aviation Data (ADS-B)")
        else:
            lines.append("    Novatel ProPak6 Navigation Data (NMEA)")
        lines.append("=" * 50)
        
        # Timestamp
        if 'parsed_timestamp' in nav_data:
            timestamp = nav_data['parsed_timestamp'].strftime("%Y-%m-%d %H:%M:%S UTC")
            lines.append(f"Timestamp: {timestamp}")
        else:
            lines.append(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        lines.append("")
        
        # Position
        if 'latitude_decimal' in nav_data and 'longitude_decimal' in nav_data:
            lat = nav_data['latitude_decimal']
            lon = nav_data['longitude_decimal']
            
            # Format coordinates with direction
            lat_dir = "N" if lat >= 0 else "S"
            lon_dir = "E" if lon >= 0 else "W"
            
            lines.append(f"Position:  {abs(lat):.{config.COORDINATE_PRECISION}f}°{lat_dir}, {abs(lon):.{config.COORDINATE_PRECISION}f}°{lon_dir}")
        else:
            lines.append("Position:  No GPS fix")
        
        # Altitude
        if 'altitude_m' in nav_data or 'altitude_ft' in nav_data:
            alt_parts = []
            
            if config.ALTITUDE_UNITS in ['feet', 'both'] and 'altitude_ft' in nav_data:
                alt_parts.append(f"{nav_data['altitude_ft']:,.0f} ft")
                
            if config.ALTITUDE_UNITS in ['meters', 'both'] and 'altitude_m' in nav_data:
                alt_parts.append(f"{nav_data['altitude_m']:,.0f} m")
            
            if alt_parts:
                altitude_str = " (".join(alt_parts)
                if len(alt_parts) > 1:
                    altitude_str += ")"
                lines.append(f"Altitude:  {altitude_str}")
        else:
            lines.append("Altitude:  No data")
        
        # Speed
        if any(key in nav_data for key in ['speed_knots', 'speed_kmh', 'speed_mph']):
            speed_parts = []
            
            if config.SPEED_UNITS in ['knots', 'both'] and 'speed_knots' in nav_data:
                speed_parts.append(f"{nav_data['speed_knots']:.1f} knots")
                
            if config.SPEED_UNITS in ['kmh', 'both'] and 'speed_kmh' in nav_data:
                speed_parts.append(f"{nav_data['speed_kmh']:.1f} km/h")
                
            if config.SPEED_UNITS == 'mph' and 'speed_mph' in nav_data:
                speed_parts.append(f"{nav_data['speed_mph']:.1f} mph")
            
            if speed_parts:
                if len(speed_parts) == 1:
                    speed_str = speed_parts[0]
                else:
                    speed_str = f"{speed_parts[0]} ({', '.join(speed_parts[1:])})"
                lines.append(f"Speed:     {speed_str}")
        else:
            lines.append("Speed:     No data")
        
        # Heading
        if 'heading' in nav_data:
            heading = nav_data['heading']
            direction = self._heading_to_direction(heading)
            lines.append(f"Heading:   {heading:03.0f}° ({direction})")
        else:
            lines.append("Heading:   No data")
        
        # GPS Quality
        if 'gps_quality' in nav_data and 'satellites' in nav_data:
            quality = self._gps_quality_text(nav_data['gps_quality'])
            sats = nav_data['satellites']
            lines.append(f"GPS:       {quality} ({sats} satellites)")
        elif 'gps_quality' in nav_data:
            quality = self._gps_quality_text(nav_data['gps_quality'])
            lines.append(f"GPS:       {quality}")
        else:
            lines.append("GPS:       No data")
        
        # ADS-B specific fields
        if 'icao' in nav_data:
            lines.append(f"ICAO:      {nav_data['icao']}")
            
        if 'callsign' in nav_data:
            lines.append(f"Callsign:  {nav_data['callsign']}")
            
        if 'type_code' in nav_data:
            lines.append(f"Type Code: {nav_data['type_code']}")
            
        if 'vertical_rate' in nav_data and nav_data['vertical_rate'] is not None:
            vr = nav_data['vertical_rate']
            direction = "climbing" if vr > 0 else "descending" if vr < 0 else "level"
            lines.append(f"V-Rate:    {abs(vr):,.0f} ft/min {direction}")
        
        # Status
        if 'status' in nav_data:
            status = "Active" if nav_data['status'] == 'A' else "Void"
            lines.append(f"Status:    {status}")
        
        # Statistics (if provided)
        if stats:
            lines.append("")
            lines.append("-" * 30)
            lines.append("Statistics:")
            
            # Handle both NMEA and ADS-B statistics
            if 'sentences_parsed' in stats:
                lines.append(f"  NMEA sentences parsed: {stats['sentences_parsed']}")
            elif 'nmea_sentences_parsed' in stats:
                lines.append(f"  NMEA sentences parsed: {stats['nmea_sentences_parsed']}")
                
            if 'messages_parsed' in stats:
                lines.append(f"  ADS-B messages parsed: {stats['messages_parsed']}")
            elif 'adsb_messages_parsed' in stats:
                lines.append(f"  ADS-B messages parsed: {stats['adsb_messages_parsed']}")
                
            if 'aircraft_tracked' in stats:
                lines.append(f"  Aircraft tracked: {stats['aircraft_tracked']}")
            elif 'adsb_aircraft_tracked' in stats:
                lines.append(f"  Aircraft tracked: {stats['adsb_aircraft_tracked']}")
                
            if 'parse_errors' in stats:
                lines.append(f"  Parse errors: {stats['parse_errors']}")
            elif 'nmea_parse_errors' in stats or 'adsb_parse_errors' in stats:
                nmea_errors = stats.get('nmea_parse_errors', 0)
                adsb_errors = stats.get('adsb_parse_errors', 0)
                total_errors = nmea_errors + adsb_errors
                lines.append(f"  Parse errors: {total_errors} (NMEA: {nmea_errors}, ADS-B: {adsb_errors})")
                
            if 'success_rate' in stats:
                lines.append(f"  Success rate: {stats['success_rate']}%")
            elif 'nmea_success_rate' in stats or 'adsb_success_rate' in stats:
                nmea_rate = stats.get('nmea_success_rate', 0)
                adsb_rate = stats.get('adsb_success_rate', 0)
                if nmea_rate > 0 and adsb_rate > 0:
                    lines.append(f"  Success rate: NMEA {nmea_rate}%, ADS-B {adsb_rate}%")
                elif nmea_rate > 0:
                    lines.append(f"  NMEA success rate: {nmea_rate}%")
                elif adsb_rate > 0:
                    lines.append(f"  ADS-B success rate: {adsb_rate}%")
                
            if 'listening' in stats:
                status = "Active" if stats['listening'] else "Stopped"
                lines.append(f"  UDP Listener: {status}")
        
        lines.append("=" * 50)
        
        return "\n".join(lines)
    
    def display(self, nav_data: Dict[str, Any], stats: Dict[str, Any] = None):
        """
        Display navigation data to console
        
        Args:
            nav_data: Navigation data dictionary
            stats: Optional statistics dictionary
        """
        # Clear screen if configured
        if config.CLEAR_SCREEN:
            self._clear_screen()
        
        # Format and print data
        formatted_data = self.format_navigation_data(nav_data, stats)
        print(formatted_data)
        
        self.display_count += 1
    
    def _clear_screen(self):
        """Clear the console screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def _heading_to_direction(self, heading: float) -> str:
        """
        Convert heading degrees to compass direction
        
        Args:
            heading: Heading in degrees (0-360)
            
        Returns:
            Compass direction string
        """
        directions = [
            "North", "North-Northeast", "Northeast", "East-Northeast",
            "East", "East-Southeast", "Southeast", "South-Southeast",
            "South", "South-Southwest", "Southwest", "West-Southwest",
            "West", "West-Northwest", "Northwest", "North-Northwest"
        ]
        
        # Normalize heading to 0-360
        heading = heading % 360
        
        # Calculate index (16 directions, so 360/16 = 22.5 degrees each)
        index = int((heading + 11.25) / 22.5) % 16
        
        return directions[index]
    
    def _gps_quality_text(self, quality: int) -> str:
        """
        Convert GPS quality code to text
        
        Args:
            quality: GPS quality indicator (0-8)
            
        Returns:
            GPS quality description
        """
        quality_map = {
            0: "Invalid",
            1: "GPS Fix",
            2: "DGPS Fix",
            3: "PPS Fix",
            4: "RTK Fix",
            5: "Float RTK",
            6: "Estimated",
            7: "Manual",
            8: "Simulation"
        }
        
        return quality_map.get(quality, f"Unknown ({quality})")
    
    def get_stats(self) -> Dict[str, int]:
        """Get display statistics"""
        return {
            'displays_rendered': self.display_count
        }