#!/usr/bin/python3
"""
ADS-B Message Parser Example Script

This script demonstrates how to parse individual ADS-B (Automatic Dependent 
Surveillance-Broadcast) messages and extract aviation data. It serves as both
a standalone utility and an educational example of ADS-B message processing.

ADS-B messages are transmitted by aircraft to provide real-time information
about their position, velocity, identification, and other flight parameters.
This script uses the pyModeS library to decode these messages and outputs
structured JSON data.

Key Features:
- Supports various hex input formats (with/without spaces)
- Comprehensive error handling and validation
- Detailed parsing statistics and metadata
- JSON output for easy integration with other systems
- Support for all major ADS-B message types (identification, position, velocity)

Usage:
    python parse_adsb_message.py <hex_message> [options]

Examples:
    python parse_adsb_message.py "8D4840D6202CC371C32CE0576098"
    python parse_adsb_message.py "8D 48 40 D6 20 2C C3 71 C3 2C E0 57 60 98"
    python parse_adsb_message.py 8D4840D6202CC371C32CE0576098 --pretty

Author: Generated for Novatel ProPak6 Navigation Data Toolkit
License: See project LICENSE file
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any, Union

# Add parent directory to Python path to access project modules
# This allows the script to import the main ADS-B parser without requiring
# installation as a package
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the main ADS-B parser and configuration
from adsb_parser import ADSBParser
import config


def clean_hex_input(hex_input: str) -> str:
    """
    Clean and validate hexadecimal input string for ADS-B message parsing.
    
    This function handles various input formats commonly used for hex data:
    - Removes spaces, dashes, colons, and other common separators
    - Validates that all characters are valid hexadecimal digits
    - Ensures even number of characters (each byte requires 2 hex digits)
    - Converts to uppercase for consistency
    
    ADS-B messages are typically 14 bytes (112 bits) long, which corresponds
    to 28 hexadecimal characters. However, this function accepts any valid
    hex string length to accommodate different message types.
    
    Args:
        hex_input (str): Raw hex string input that may contain spaces, 
                        dashes, colons, or other separators
                        
    Returns:
        str: Clean hex string in uppercase without separators
        
    Raises:
        ValueError: If input contains non-hex characters or has odd length
        
    Examples:
        >>> clean_hex_input("8D 48 40 D6 20 2C")
        "8D4840D6202C"
        >>> clean_hex_input("8d-48-40-d6")
        "8D4840D6"
    """
    # Remove common separators that are often used in hex representations
    # This makes the script more user-friendly by accepting various formats
    cleaned = hex_input.replace(' ', '').replace('-', '').replace(':', '').strip()
    
    # Validate that all characters are valid hexadecimal digits (0-9, A-F, a-f)
    # Using int() conversion is more reliable than character-by-character checking
    try:
        int(cleaned, 16)  # This will raise ValueError if not valid hex
    except ValueError:
        raise ValueError(f"Invalid hex string: {hex_input}")
    
    # Ensure even number of characters (each byte requires exactly 2 hex digits)
    # Odd-length hex strings would indicate incomplete byte data
    if len(cleaned) % 2 != 0:
        raise ValueError(f"Hex string must have even number of characters: {cleaned}")
    
    # Convert to uppercase for consistency in output and processing
    return cleaned.upper()


def hex_to_bytes(hex_string: str) -> bytes:
    """
    Convert a clean hexadecimal string to bytes object.
    
    This is a simple wrapper around bytes.fromhex() that provides
    clearer error context and documentation for the conversion process.
    
    Args:
        hex_string (str): Clean hex string (no spaces, even length)
        
    Returns:
        bytes: Binary representation of the hex string
        
    Examples:
        >>> hex_to_bytes("8D4840D6")
        b'\x8dH@\xd6'
    """
    return bytes.fromhex(hex_string)


def parse_adsb_message(raw_message: str) -> Dict[str, Any]:
    """
    Parse an ADS-B message and return comprehensive results.
    
    This is the main parsing function that orchestrates the entire process:
    1. Input validation and cleaning
    2. Message parsing using the ADS-B parser
    3. Result formatting and error handling
    4. Statistics collection
    
    The function returns a structured dictionary containing:
    - Input metadata (original input, cleaned hex, byte count)
    - Parsing results (success/failure, statistics)
    - Decoded aviation data (if successful)
    - Error information (if failed)
    
    Args:
        raw_message (str): Raw ADS-B message in hex format
        
    Returns:
        Dict[str, Any]: Comprehensive parsing results including:
            - input: Input processing details
            - parsing: Success status and parser statistics  
            - parsed_data: Decoded aviation data (if successful)
            - error: Error message (if failed)
            
    Examples:
        >>> result = parse_adsb_message("8D4840D6202CC371C32CE0576098")
        >>> result['parsing']['success']
        True
        >>> result['parsed_data']['callsign']
        "KLM1023_"
    """
    try:
        # Step 1: Clean and validate the input hex string
        # This handles user-friendly input formats and ensures data integrity
        clean_hex = clean_hex_input(raw_message)
        
        # Step 2: Convert hex string to binary data
        # ADS-B messages are processed as binary data by the parser
        message_bytes = hex_to_bytes(clean_hex)
        
        # Step 3: Configure parser logging
        # Temporarily disable verbose logging unless explicitly requested
        # This prevents cluttering the JSON output with debug information
        original_log_setting = config.LOG_PARSE_ATTEMPTS
        config.LOG_PARSE_ATTEMPTS = False
        
        # Step 4: Create ADS-B parser instance
        # The parser handles both raw Mode S and GDL-90 wrapped messages
        parser = ADSBParser()
        
        # Step 5: Parse the message
        # This is where the actual ADS-B decoding happens using pyModeS
        result = parser.parse_message(message_bytes)
        
        # Step 6: Restore original logging configuration
        config.LOG_PARSE_ATTEMPTS = original_log_setting
        
        # Step 7: Build comprehensive output structure
        # The output includes metadata, statistics, and parsed data
        output = {
            # Input section: Details about the raw input and processing
            'input': {
                'raw_hex': clean_hex,           # Cleaned hex string
                'raw_bytes': len(message_bytes), # Message length in bytes
                'original_input': raw_message    # Original user input
            },
            # Parsing section: Success status and detailed statistics
            'parsing': {
                'success': result is not None,  # Boolean success indicator
                'parser_stats': parser.get_stats() # Detailed parser statistics
            }
        }
        
        # Step 8: Process successful parsing results
        if result:
            # Convert datetime objects to ISO format for JSON serialization
            # Python datetime objects are not JSON serializable by default
            formatted_result = {}
            for key, value in result.items():
                if hasattr(value, 'isoformat'):  # Check if it's a datetime object
                    formatted_result[key] = value.isoformat()
                else:
                    formatted_result[key] = value
            
            # Add parsed aviation data to output
            output['parsed_data'] = formatted_result
        else:
            # Add error message for failed parsing
            output['error'] = 'Failed to parse message - may not be a valid ADS-B message'
        
        return output
        
    except Exception as e:
        # Step 9: Handle any errors during processing
        # Return structured error information for debugging
        return {
            'input': {
                'original_input': raw_message
            },
            'parsing': {
                'success': False
            },
            'error': str(e)
        }


def main():
    """
    Main function that handles command line interface and program execution.
    
    This function:
    1. Sets up command line argument parsing
    2. Processes user input and options
    3. Calls the parsing function
    4. Formats and outputs results
    5. Sets appropriate exit codes
    
    The CLI supports various options for different use cases:
    - Pretty printing for human readability
    - Verbose logging for debugging
    - Flexible input handling
    
    Exit codes:
    - 0: Successful parsing
    - 1: Parsing failed or invalid input
    """
    
    # Configure command line argument parser
    # Using RawDescriptionHelpFormatter preserves formatting in help text
    parser = argparse.ArgumentParser(
        description='Parse ADS-B messages and output structured JSON data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    %(prog)s "8D4840D6202CC371C32CE0576098"
        Parse aircraft identification message (basic output)
        
    %(prog)s "8D 48 40 D6 20 2C C3 71 C3 2C E0 57 60 98" --pretty
        Parse with spaces in input, pretty-print JSON
        
    %(prog)s 8D4840D6202CC371C32CE0576098 --verbose
        Parse with detailed logging enabled
        
    %(prog)s "8D4840D6580B982C8BA874F80820" --pretty
        Parse airborne position message

Input Format:
    The script accepts ADS-B messages in hexadecimal format with or without
    spaces, dashes, or other common separators. Messages are typically 14 bytes
    (28 hex characters) long.

Message Types Supported:
    - Aircraft Identification (TC 1-4): Callsign, category
    - Surface Position (TC 5-8): Position data (requires reference)
    - Airborne Position (TC 9-18): Position and altitude data
    - Airborne Velocity (TC 19): Speed, heading, vertical rate

Output Format:
    Structured JSON containing input details, parsing statistics, and decoded
    aviation data. Use --pretty for human-readable formatting.
        """
    )
    
    # Define command line arguments
    
    # Required positional argument: the ADS-B message to parse
    parser.add_argument(
        'message',
        help='Raw ADS-B message in hexadecimal format (with or without spaces/separators)'
    )
    
    # Optional flag: pretty-print JSON output
    parser.add_argument(
        '--pretty',
        action='store_true',
        help='Pretty-print JSON output with indentation for readability'
    )
    
    # Optional flag: enable verbose logging
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose parsing logs to see detailed processing steps'
    )
    
    # Parse command line arguments
    args = parser.parse_args()
    
    # Configure logging based on user preference
    # Verbose mode shows internal parser operations and debugging information
    if args.verbose:
        config.LOG_PARSE_ATTEMPTS = True
        print("Verbose logging enabled - showing detailed parsing steps:")
        print(f"Input message: {args.message}")
        print("=" * 50)
    
    # Parse the ADS-B message
    # This is the main processing step that does all the work
    result = parse_adsb_message(args.message)
    
    # Output results in requested format
    if args.pretty:
        # Pretty-printed JSON with 2-space indentation for human readability
        print(json.dumps(result, indent=2))
    else:
        # Compact JSON for programmatic use or minimal output
        print(json.dumps(result))
    
    # Set exit code based on parsing success
    # This allows shell scripts and other programs to detect success/failure
    if not result.get('parsing', {}).get('success', False):
        # Exit with code 1 to indicate parsing failure
        sys.exit(1)
    # Exit with code 0 (default) for successful parsing


# Standard Python idiom: only run main() when script is executed directly
# This allows the script to be imported as a module without running main()
if __name__ == '__main__':
    main()