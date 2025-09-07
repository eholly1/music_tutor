#!/usr/bin/env python3
"""
Real-time MIDI Input Test

This script tests real-time MIDI processing with your controller.
Play notes on your EWI5000 to see them captured and processed in real-time.
"""

import sys
import time
import threading
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from utils.logger import setup_logger
from midi.input_handler import MIDIInputHandler
from midi.note_processor import NoteProcessor


class RealTimeMIDITest:
    """Real-time MIDI input testing class"""
    
    def __init__(self):
        self.logger = setup_logger()
        self.midi_handler = MIDIInputHandler()
        self.note_processor = NoteProcessor()
        self.running = False
        
        # Connect note processor to MIDI handler
        self.midi_handler.set_note_processor(self.note_processor)
        
        # Set up note event callbacks for real-time display
        self.note_processor.add_note_callback(self.on_note_event)
    
    def on_note_event(self, event_type, note):
        """Callback for real-time note events"""
        if event_type == 'start':
            print(f"🎵 Note ON:  {note.get_note_name()} (vel={note.velocity}) - {note.get_frequency():.1f}Hz")
        elif event_type == 'complete':
            print(f"🎵 Note OFF: {note.get_note_name()} (vel={note.velocity}) - Duration: {note.duration:.3f}s")
    
    def connect_to_device(self):
        """Connect to the first available MIDI device"""
        devices = self.midi_handler.get_available_devices()
        
        if not devices:
            print("❌ No MIDI devices found!")
            return False
        
        print(f"Found MIDI devices: {devices}")
        
        # Connect to first device (should be your EWI5000)
        device_name = devices[0]
        success = self.midi_handler.connect_device(device_name)
        
        if success:
            print(f"✅ Connected to: {device_name}")
            return True
        else:
            print(f"❌ Failed to connect to: {device_name}")
            return False
    
    def start_recording_test(self):
        """Start recording MIDI input for a specified duration"""
        print("\n" + "="*60)
        print("🎹 REAL-TIME MIDI INPUT TEST")
        print("="*60)
        print("Play notes on your EWI5000!")
        print("Notes will appear in real-time as you play them.")
        print("Press Ctrl+C to stop the test.")
        print("="*60)
        
        # Start recording
        if not self.midi_handler.start_recording():
            print("❌ Failed to start recording")
            return
        
        print("🔴 Recording started - play some notes!")
        self.running = True
        
        try:
            # Keep the test running until interrupted
            while self.running:
                time.sleep(0.1)
                
                # Show currently active notes
                active_notes = self.midi_handler.get_active_notes()
                if active_notes:
                    note_names = [note.get_note_name() for note in active_notes]
                    print(f"🎯 Active notes: {', '.join(note_names)}", end='\r')
        
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping test...")
            self.running = False
        
        # Stop recording and show results
        recorded_notes = self.midi_handler.stop_recording()
        
        print(f"\n🎵 Recording completed!")
        print(f"📊 Total notes recorded: {len(recorded_notes)}")
        
        if recorded_notes:
            print("\n📝 Recorded Notes Summary:")
            print("-" * 50)
            for i, note in enumerate(recorded_notes):
                print(f"{i+1:2d}. {note}")
            
            # Calculate some basic statistics
            pitches = [note.pitch for note in recorded_notes]
            durations = [note.duration for note in recorded_notes if note.duration]
            
            if pitches:
                min_pitch = min(pitches)
                max_pitch = max(pitches)
                print(f"\n📈 Statistics:")
                print(f"   Pitch range: {self._midi_to_note_name(min_pitch)} to {self._midi_to_note_name(max_pitch)}")
                print(f"   MIDI range: {min_pitch} to {max_pitch}")
            
            if durations:
                avg_duration = sum(durations) / len(durations)
                min_duration = min(durations)
                max_duration = max(durations)
                print(f"   Average note duration: {avg_duration:.3f}s")
                print(f"   Duration range: {min_duration:.3f}s to {max_duration:.3f}s")
        
        print("\n✅ Real-time MIDI test completed!")
    
    def _midi_to_note_name(self, midi_pitch):
        """Convert MIDI pitch to note name"""
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_pitch // 12) - 1
        note = note_names[midi_pitch % 12]
        return f"{note}{octave}"
    
    def cleanup(self):
        """Clean up resources"""
        if self.midi_handler:
            self.midi_handler.disconnect_device()


def main():
    """Main test function"""
    print("Real-time MIDI Input Test for Music Trainer")
    print("=" * 50)
    
    test = RealTimeMIDITest()
    
    try:
        # Connect to MIDI device
        if not test.connect_to_device():
            return False
        
        # Run the real-time test
        test.start_recording_test()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False
    
    finally:
        test.cleanup()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
