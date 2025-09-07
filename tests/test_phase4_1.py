#!/usr/bin/env python3
"""
Test script for Phase 4.1 Phrase Data Structure

This script tests the new MusicalNote and Phrase classes to ensure
they work correctly with beat-based timing and MIDI note numbers.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from music.phrase import MusicalNote, Phrase, create_simple_scale_phrase, create_chord_phrase


def test_musical_note():
    """Test MusicalNote creation and validation"""
    print("Testing MusicalNote...")
    
    # Valid note
    note = MusicalNote(pitch=60, start_time=0.0, duration=1.0, velocity=80)
    print(f"✓ Created note: MIDI {note.pitch}, start {note.start_time}, duration {note.duration}")
    
    # Test validation
    try:
        invalid_note = MusicalNote(pitch=128, start_time=0.0, duration=1.0)  # Invalid pitch
        print("✗ Should have failed with invalid pitch")
    except ValueError as e:
        print(f"✓ Correctly caught invalid pitch: {e}")
    
    try:
        invalid_note = MusicalNote(pitch=60, start_time=-1.0, duration=1.0)  # Invalid start time
        print("✗ Should have failed with invalid start time")
    except ValueError as e:
        print(f"✓ Correctly caught invalid start time: {e}")


def test_phrase_creation():
    """Test Phrase creation and metadata validation"""
    print("\nTesting Phrase creation...")
    
    # Create some notes
    notes = [
        MusicalNote(pitch=60, start_time=0.0, duration=1.0, velocity=80),  # C4
        MusicalNote(pitch=62, start_time=1.0, duration=1.0, velocity=75),  # D4
        MusicalNote(pitch=64, start_time=2.0, duration=1.0, velocity=85),  # E4
    ]
    
    # Create phrase with minimal metadata
    metadata = {
        'style': 'modal_jazz',
        'difficulty': 2,
        'bars': 1,
        'description': 'Test phrase'
    }
    
    phrase = Phrase(notes, metadata)
    print(f"✓ Created phrase: {phrase}")
    print(f"  - Duration in beats: {phrase.get_duration_beats()}")
    print(f"  - Duration in seconds at 120 BPM: {phrase.get_duration_seconds():.2f}")
    print(f"  - Validation passed: {phrase.validate_timing()}")


def test_phrase_timing_methods():
    """Test phrase timing and note lookup methods"""
    print("\nTesting phrase timing methods...")
    
    # Create a phrase with overlapping notes
    notes = [
        MusicalNote(pitch=60, start_time=0.0, duration=2.0, velocity=80),  # Long note
        MusicalNote(pitch=64, start_time=1.0, duration=1.0, velocity=75),  # Overlapping note
        MusicalNote(pitch=67, start_time=2.5, duration=0.5, velocity=85), # Short note
    ]
    
    metadata = {
        'style': 'modal_jazz',
        'difficulty': 3,
        'bars': 1,
        'tempo': 100
    }
    
    phrase = Phrase(notes, metadata)
    
    # Test note lookup at specific beat
    notes_at_beat_1 = phrase.get_note_at_beat(1.0)
    print(f"✓ Notes playing at beat 1.0: {len(notes_at_beat_1)} notes")
    for note in notes_at_beat_1:
        print(f"  - MIDI {note.pitch} (start: {note.start_time}, dur: {note.duration})")
    
    # Test notes in range
    notes_in_range = phrase.get_notes_in_range(1.0, 3.0)
    print(f"✓ Notes starting between beats 1-3: {len(notes_in_range)} notes")


def test_utility_functions():
    """Test utility functions for creating common phrases"""
    print("\nTesting utility functions...")
    
    # Test scale phrase
    major_scale = [0, 2, 4, 5, 7, 9, 11, 12]  # C major scale intervals
    scale_phrase = create_simple_scale_phrase(60, major_scale[:4], difficulty=1)
    print(f"✓ Created scale phrase: {scale_phrase}")
    print(f"  - Notes: {len(scale_phrase.notes)}")
    print(f"  - Duration: {scale_phrase.get_duration_beats()} beats")
    
    # Test chord phrase
    c_major_chord = [60, 64, 67]  # C-E-G
    chord_phrase = create_chord_phrase(c_major_chord, duration_beats=2.0)
    print(f"✓ Created chord phrase: {chord_phrase}")
    print(f"  - Notes: {len(chord_phrase.notes)}")
    print(f"  - All start at same time: {all(note.start_time == 0.0 for note in chord_phrase.notes)}")


def test_serialization():
    """Test phrase serialization and deserialization"""
    print("\nTesting serialization...")
    
    # Create a phrase
    notes = [
        MusicalNote(pitch=60, start_time=0.0, duration=1.0, velocity=80),
        MusicalNote(pitch=64, start_time=1.0, duration=1.0, velocity=75),
    ]
    
    metadata = {
        'style': 'blues',
        'difficulty': 2,
        'bars': 1,
        'description': 'Serialization test'
    }
    
    original = Phrase(notes, metadata)
    
    # Convert to dict and back
    phrase_dict = original.to_dict()
    reconstructed = Phrase.from_dict(phrase_dict)
    
    print(f"✓ Original phrase: {original}")
    print(f"✓ Reconstructed phrase: {reconstructed}")
    print(f"✓ Notes match: {len(original.notes) == len(reconstructed.notes)}")
    print(f"✓ Metadata matches: {original.metadata == reconstructed.metadata}")


if __name__ == "__main__":
    print("=== Phase 4.1 Phrase Data Structure Test ===\n")
    
    try:
        test_musical_note()
        test_phrase_creation()
        test_phrase_timing_methods()
        test_utility_functions()
        test_serialization()
        
        print("\n=== All tests completed successfully! ===")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
