"""
Unit tests for GDL90Deframer module
"""

import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gdl90_deframer import GDL90Deframer, deframe_gdl90_data


class TestGDL90Deframer:
    """Test GDL-90 deframing functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.deframer = GDL90Deframer()
    
    def test_initialization(self):
        """Test GDL90Deframer initialization"""
        assert self.deframer.frames_processed == 0
        assert self.deframer.frames_extracted == 0
        assert self.deframer.adsb_messages_found == 0
        assert self.deframer.deframing_errors == 0
        assert self.deframer.byte_unstuff_operations == 0
    
    def test_constants(self):
        """Test that GDL-90 constants are correct"""
        assert GDL90Deframer.FLAG_BYTE == 0x7E
        assert GDL90Deframer.ESCAPE_BYTE == 0x7D
        assert GDL90Deframer.ESCAPE_FLAG == 0x5E
        assert GDL90Deframer.ESCAPE_ESC == 0x5D
        assert GDL90Deframer.MSG_ADSB_LONG == 0x26
        assert GDL90Deframer.MIN_ADSB_PAYLOAD_LENGTH == 14
        assert GDL90Deframer.MAX_ADSB_PAYLOAD_LENGTH == 18
    
    def test_sample_data_deframing(self):
        """Test deframing of known sample data"""
        # Sample GDL-90 data from problem description
        sample_hex = "7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E"
        sample_data = bytes.fromhex(sample_hex)
        
        # Expected output after deframing
        expected_hex = "8B9A7E479967CCD9C82B84D1FFEBCCA0"
        expected_data = bytes.fromhex(expected_hex)
        
        messages = self.deframer.deframe_message(sample_data)
        
        assert len(messages) == 1
        assert messages[0] == expected_data
        
        # Check DF
        df = (messages[0][0] >> 3) & 0x1F
        assert df == 17  # Should be ADS-B DF 17
    
    def test_empty_data(self):
        """Test handling of empty data"""
        result = self.deframer.deframe_message(b'')
        assert result == []
    
    def test_invalid_short_data(self):
        """Test handling of data too short to be valid"""
        short_data = b'\x7E\x26\x7E'
        result = self.deframer.deframe_message(short_data)
        assert result == []
    
    def test_find_frame_boundaries(self):
        """Test frame boundary detection"""
        # Single frame
        single_frame = bytes.fromhex("7E26008B9A7E")
        boundaries = self.deframer._find_frame_boundaries(single_frame)
        assert len(boundaries) == 1
        assert boundaries[0] == (0, 5)
        
        # Multiple frames
        multi_frame = bytes.fromhex("7E26008B9A7E7E2600123456787E")
        boundaries = self.deframer._find_frame_boundaries(multi_frame)
        assert len(boundaries) == 2
        assert boundaries[0] == (0, 5)
        assert boundaries[1] == (6, 13)
        
        # No valid frames (no content between flags)
        invalid_frame = bytes.fromhex("7E7E")
        boundaries = self.deframer._find_frame_boundaries(invalid_frame)
        assert len(boundaries) == 0
    
    def test_unstuff_bytes_flag_escape(self):
        """Test byte unstuffing for flag escape sequence"""
        # 0x7D 0x5E should become 0x7E
        stuffed = bytes.fromhex("26007D5E12")
        expected = bytes.fromhex("26007E12")
        
        result = self.deframer._unstuff_bytes(stuffed)
        assert result == expected
        assert self.deframer.byte_unstuff_operations >= 1
    
    def test_unstuff_bytes_escape_escape(self):
        """Test byte unstuffing for escape escape sequence"""
        # 0x7D 0x5D should become 0x7D
        stuffed = bytes.fromhex("26007D5D12")
        expected = bytes.fromhex("26007D12")
        
        result = self.deframer._unstuff_bytes(stuffed)
        assert result == expected
    
    def test_unstuff_bytes_no_escapes(self):
        """Test byte unstuffing with no escape sequences"""
        normal_data = bytes.fromhex("2600123456")
        result = self.deframer._unstuff_bytes(normal_data)
        assert result == normal_data
    
    def test_unstuff_bytes_invalid_escape(self):
        """Test handling of invalid escape sequences"""
        # 0x7D followed by invalid byte
        invalid_escape = bytes.fromhex("26007D12")
        result = self.deframer._unstuff_bytes(invalid_escape)
        # Should include the 0x7D byte and continue
        expected = bytes.fromhex("26007D12")
        assert result == expected
    
    def test_unstuff_bytes_empty(self):
        """Test unstuffing empty data"""
        result = self.deframer._unstuff_bytes(b'')
        assert result is None
    
    def test_extract_adsb_payload_valid(self):
        """Test extraction of valid ADS-B payload"""
        # Valid ADS-B frame: msg_id=0x26, sub_id=0x00, then 14-byte payload
        frame_data = bytes.fromhex("26008B9A7E479967CCD9C82B84D1FFEBCCA0")
        
        payload = self.deframer._extract_adsb_payload(frame_data)
        expected_payload = bytes.fromhex("8B9A7E479967CCD9C82B84D1FFEBCCA0")
        
        assert payload == expected_payload
    
    def test_extract_adsb_payload_wrong_msg_type(self):
        """Test extraction with wrong message type"""
        # Wrong message ID (not 0x26)
        frame_data = bytes.fromhex("25008B9A7E479967CCD9C82B84D1FFEBCCA0")
        
        payload = self.deframer._extract_adsb_payload(frame_data)
        assert payload is None
    
    def test_extract_adsb_payload_too_short(self):
        """Test extraction with payload too short"""
        # Too short for valid ADS-B payload
        frame_data = bytes.fromhex("26008B9A7E47")
        
        payload = self.deframer._extract_adsb_payload(frame_data)
        assert payload is None
    
    def test_extract_adsb_payload_too_long(self):
        """Test extraction with payload too long"""
        # Too long for reasonable ADS-B payload
        frame_data = bytes.fromhex("26008B9A7E479967CCD9C82B84D1FFEBCCA01234567890ABCDEF")
        
        payload = self.deframer._extract_adsb_payload(frame_data)
        assert payload is None
    
    def test_validate_adsb_message_valid_df17(self):
        """Test validation of valid DF 17 ADS-B message"""
        # DF 17 message (first byte = 0x8B, DF = 17)
        payload = bytes.fromhex("8B9A7E479967CCD9C82B84D1FFEBCCA0")
        
        is_valid = self.deframer._validate_adsb_message(payload)
        assert is_valid is True
    
    def test_validate_adsb_message_valid_df18(self):
        """Test validation of valid DF 18 ADS-B message"""
        # DF 18 message (first byte should have DF = 18)
        payload = bytes.fromhex("909A7E479967CCD9C82B84D1FFEBCCA0")
        
        is_valid = self.deframer._validate_adsb_message(payload)
        assert is_valid is True
    
    def test_validate_adsb_message_invalid_df(self):
        """Test validation of message with invalid DF"""
        # DF 16 message (not valid for ADS-B)
        payload = bytes.fromhex("809A7E479967CCD9C82B84D1FFEBCCA0")
        
        is_valid = self.deframer._validate_adsb_message(payload)
        assert is_valid is False
    
    def test_validate_adsb_message_wrong_length(self):
        """Test validation of message with wrong length"""
        # Too short
        short_payload = bytes.fromhex("8B9A7E479967CCD9C8")
        is_valid = self.deframer._validate_adsb_message(short_payload)
        assert is_valid is False
        
        # Too long
        long_payload = bytes.fromhex("8B9A7E479967CCD9C82B84D1FFEBCCA01234567890")
        is_valid = self.deframer._validate_adsb_message(long_payload)
        assert is_valid is False
    
    def test_is_gdl90_frame_valid(self):
        """Test GDL-90 frame detection for valid frames"""
        valid_frame = bytes.fromhex("7E26008B9A7E479967CCD9C82B84D1FFEBCCA07E")
        
        result = self.deframer.is_gdl90_frame(valid_frame)
        assert result is True
    
    def test_is_gdl90_frame_invalid(self):
        """Test GDL-90 frame detection for invalid frames"""
        # Too short
        too_short = bytes.fromhex("7E26007E")
        assert self.deframer.is_gdl90_frame(too_short) is False
        
        # Doesn't start with flag
        no_start_flag = bytes.fromhex("26008B9A7E479967CCD9C82B84D1FFEBCCA07E")
        assert self.deframer.is_gdl90_frame(no_start_flag) is False
        
        # Doesn't end with flag
        no_end_flag = bytes.fromhex("7E26008B9A7E479967CCD9C82B84D1FFEBCCA0")
        assert self.deframer.is_gdl90_frame(no_end_flag) is False
    
    def test_get_stats(self):
        """Test statistics collection"""
        # Process some data to generate stats
        sample_data = bytes.fromhex("7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E")
        self.deframer.deframe_message(sample_data)
        
        stats = self.deframer.get_stats()
        
        assert 'frames_processed' in stats
        assert 'frames_extracted' in stats
        assert 'adsb_messages_found' in stats
        assert 'deframing_errors' in stats
        assert 'byte_unstuff_operations' in stats
        assert 'success_rate' in stats
        
        assert stats['frames_processed'] >= 1
        assert stats['adsb_messages_found'] >= 1
        assert isinstance(stats['success_rate'], float)
    
    def test_reset_stats(self):
        """Test statistics reset"""
        # Process some data
        sample_data = bytes.fromhex("7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E")
        self.deframer.deframe_message(sample_data)
        
        # Verify stats are non-zero
        assert self.deframer.frames_processed > 0
        
        # Reset stats
        self.deframer.reset_stats()
        
        # Verify stats are reset
        assert self.deframer.frames_processed == 0
        assert self.deframer.frames_extracted == 0
        assert self.deframer.adsb_messages_found == 0
        assert self.deframer.deframing_errors == 0
        assert self.deframer.byte_unstuff_operations == 0
    
    def test_multiple_messages_in_frame(self):
        """Test handling multiple messages in one data block"""
        # Two separate frames
        frame1 = "7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E"
        frame2 = "7E26009C1234567890ABCDEF123456789ABCDEF07E"
        combined_data = bytes.fromhex(frame1 + frame2)
        
        messages = self.deframer.deframe_message(combined_data)
        
        # Should extract both messages
        assert len(messages) >= 1  # At least one should be valid ADS-B
    
    def test_convenience_function(self):
        """Test standalone convenience function"""
        sample_data = bytes.fromhex("7E26008B9A7D5E479967CCD9C82B84D1FFEBCCA07E")
        
        messages = deframe_gdl90_data(sample_data)
        
        assert len(messages) == 1
        expected = bytes.fromhex("8B9A7E479967CCD9C82B84D1FFEBCCA0")
        assert messages[0] == expected


if __name__ == "__main__":
    pytest.main([__file__])