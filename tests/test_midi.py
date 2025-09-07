"""
Test suite for MIDI functionality

Tests for MIDI input handling and note processing.
Phase 2.1 implementation with real MIDI device testing.
"""

import pytest
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from midi.input_handler import MIDIInputHandler
from midi.note_processor import NoteProcessor, MIDINote


class TestMIDIInputHandler:
    """Test cases for MIDI input handler"""
    
    def test_initialization(self):
        """Test MIDI handler initialization"""
        handler = MIDIInputHandler()
        assert handler is not None
        # MIDI system should initialize properly (may be None if no MIDI available)
        
    def test_get_available_devices(self):
        """Test device enumeration"""
        handler = MIDIInputHandler()
        devices = handler.get_available_devices()
        assert isinstance(devices, list)
        # Don't assert specific devices since they depend on hardware
    
    def test_device_connection_nonexistent(self):
        """Test connection to non-existent device fails gracefully"""
        handler = MIDIInputHandler()
        result = handler.connect_device("NonExistentDevice123")
        assert result is False
        assert not handler.is_connected()
    
    def test_callback_setting(self):
        """Test setting input callback"""
        handler = MIDIInputHandler()
        
        def dummy_callback(message, timestamp):
            pass
        
        handler.set_input_callback(dummy_callback)
        assert handler.input_callback == dummy_callback
    
    def test_disconnect_when_not_connected(self):
        """Test that disconnect works even when not connected"""
        handler = MIDIInputHandler()
        # Should not raise exception
        handler.disconnect_device()
        assert not handler.is_connected()
    
    def test_get_connected_device(self):
        """Test getting connected device name"""
        handler = MIDIInputHandler()
        assert handler.get_connected_device() is None
        
        # After successful connection, should return device name
        # (This would require a real device to test properly)


class TestMIDINote:
    """Test cases for MIDI note data structure"""
    
    def test_midi_note_creation(self):
        """Test MIDI note data structure"""
        note = MIDINote(pitch=60, velocity=80, timestamp=1.0, duration=0.5)
        assert note.pitch == 60
        assert note.velocity == 80
        assert note.timestamp == 1.0
        assert note.duration == 0.5
    
    def test_midi_note_without_duration(self):
        """Test MIDI note creation without duration"""
        note = MIDINote(pitch=72, velocity=100, timestamp=2.5)
        assert note.pitch == 72
        assert note.velocity == 100
        assert note.timestamp == 2.5
        assert note.duration is None


class TestNoteProcessor:
    """Test cases for note processor"""
    
    def test_initialization(self):
        """Test note processor initialization"""
        processor = NoteProcessor()
        assert processor is not None
        assert isinstance(processor.active_notes, dict)
    
    def test_finalize_notes(self):
        """Test finalizing notes"""
        processor = NoteProcessor()
        notes = processor.finalize_notes()
        assert isinstance(notes, list)


# Integration test for real MIDI hardware (if available)
class TestMIDIIntegration:
    """Integration tests for MIDI hardware (requires connected device)"""
    
    def test_real_device_detection(self):
        """Test detection of real MIDI devices"""
        handler = MIDIInputHandler()
        devices = handler.get_available_devices()
        
        if devices:
            print(f"Found MIDI devices: {devices}")
            # If devices are available, test connection to first one
            first_device = devices[0]
            success = handler.connect_device(first_device)
            
            if success:
                assert handler.is_connected()
                assert handler.get_connected_device() == first_device
                handler.disconnect_device()
                assert not handler.is_connected()
            else:
                print(f"Could not connect to {first_device} - may be in use")
        else:
            print("No MIDI devices detected - skipping hardware test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
