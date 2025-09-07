#!/usr/bin/env python3
"""
Test script for Phase 4.3 Phrase Playback Engine

This script tests the PhrasePlayer and AutonomousPhrasePlayer classes
to ensure they can play phrases correctly through audio synthesis.
"""

import sys
import os
import time

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from music.phrase_player import PhrasePlayer, AutonomousPhrasePlayer
from music.library import PhraseLibrary
from music.phrase import create_simple_scale_phrase, create_chord_phrase
# from audio.engine import AudioEngine  # Skip for testing


class MockAudioEngine:
    """Mock audio engine for testing without actual audio output"""
    
    def __init__(self):
        self.is_running = True
        self.active_notes = set()
        self.note_events = []  # Track all note events for testing
    
    def note_on(self, pitch, velocity):
        """Mock note on"""
        self.active_notes.add(pitch)
        self.note_events.append(('note_on', pitch, velocity, time.time()))
        print(f"🎵 Note ON:  MIDI {pitch:3d}, velocity {velocity:3d}")
    
    def note_off(self, pitch):
        """Mock note off"""
        self.active_notes.discard(pitch)
        self.note_events.append(('note_off', pitch, time.time()))
        print(f"🎵 Note OFF: MIDI {pitch:3d}")
    
    def get_note_events(self):
        """Get all recorded note events"""
        return self.note_events.copy()
    
    def clear_events(self):
        """Clear recorded events"""
        self.note_events.clear()


def test_phrase_player_basic():
    """Test basic PhrasePlayer functionality"""
    print("Testing basic PhrasePlayer functionality...")
    
    # Create mock audio engine
    audio_engine = MockAudioEngine()
    
    # Create phrase player
    phrase_player = PhrasePlayer(audio_engine)
    print(f"✓ PhrasePlayer created")
    
    # Create a simple test phrase
    test_phrase = create_simple_scale_phrase(
        root_pitch=60,  # Middle C
        scale_notes=[0, 2, 4, 5],  # C major tetrachord
        difficulty=1,
        style='test'
    )
    test_phrase.metadata['description'] = 'Test C Major Scale'
    
    print(f"✓ Test phrase created: {test_phrase}")
    print(f"  - Duration: {test_phrase.get_duration_beats()} beats")
    print(f"  - Notes: {[note.pitch for note in test_phrase.notes]}")
    
    return phrase_player, test_phrase, audio_engine


def test_phrase_playback():
    """Test phrase playback with timing"""
    print("\nTesting phrase playback...")
    
    phrase_player, test_phrase, audio_engine = test_phrase_player_basic()
    
    # Set up callbacks to track playback
    playback_events = []
    
    def on_started(phrase):
        playback_events.append(('started', phrase.metadata.get('description')))
        print(f"🎼 Playback started: {phrase.metadata.get('description')}")
    
    def on_finished(phrase):
        playback_events.append(('finished', phrase.metadata.get('description')))
        print(f"🎼 Playback finished: {phrase.metadata.get('description')}")
    
    def on_note(note):
        playback_events.append(('note', note.pitch, note.velocity))
    
    phrase_player.set_playback_callbacks(on_started, on_finished, on_note)
    
    # Test playback
    start_time = time.time()
    success = phrase_player.play_phrase(test_phrase, bpm=120)  # Fast tempo for testing
    print(f"✓ Playback started: {success}")
    
    # Wait for playback to complete
    while phrase_player.is_playing:
        time.sleep(0.1)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"✓ Playback completed in {duration:.2f} seconds")
    print(f"✓ Playback events: {len(playback_events)}")
    
    # Check audio events
    note_events = audio_engine.get_note_events()
    note_on_count = len([e for e in note_events if e[0] == 'note_on'])
    print(f"✓ Audio note events: {len(note_events)} total, {note_on_count} note-ons")
    
    return phrase_player, audio_engine


def test_phrase_library_integration():
    """Test phrase player with actual phrase library"""
    print("\nTesting phrase library integration...")
    
    # Create phrase library
    library = PhraseLibrary()
    success = library.load_style('modal_jazz')
    print(f"✓ Library loaded: {success}")
    
    if success:
        phrases = library.get_phrases_by_style('modal_jazz')
        print(f"✓ Available phrases: {len(phrases)}")
        
        if phrases:
            # Test with first phrase
            phrase = phrases[0]
            print(f"✓ Testing phrase: {phrase.metadata.get('description')}")
            
            # Create audio engine and phrase player
            audio_engine = MockAudioEngine()
            phrase_player = PhrasePlayer(audio_engine)
            
            # Play the phrase
            success = phrase_player.play_phrase(phrase, bpm=140)  # Fast for testing
            print(f"✓ Started library phrase playback: {success}")
            
            # Wait for completion
            while phrase_player.is_playing:
                time.sleep(0.1)
            
            print(f"✓ Library phrase playback completed")
            
            # Check results
            note_events = audio_engine.get_note_events()
            print(f"✓ Note events from library phrase: {len(note_events)}")


def test_autonomous_player():
    """Test autonomous phrase player"""
    print("\nTesting autonomous phrase player...")
    
    # Create components
    library = PhraseLibrary()
    library.load_style('modal_jazz')
    
    audio_engine = MockAudioEngine()
    phrase_player = PhrasePlayer(audio_engine)
    autonomous_player = AutonomousPhrasePlayer(library, phrase_player)
    
    print(f"✓ Autonomous player created")
    
    # Configure for fast testing
    autonomous_player.set_pause_duration(0.5)  # Short pause
    
    # Start autonomous playback
    success = autonomous_player.start_autonomous_playback(
        style='modal_jazz',
        difficulty=1,  # Easy phrases only
        bpm_override=180  # Very fast for testing
    )
    print(f"✓ Autonomous playback started: {success}")
    
    # Let it run for a few seconds
    test_duration = 4.0
    print(f"⏱ Running autonomous playback for {test_duration} seconds...")
    time.sleep(test_duration)
    
    # Stop autonomous playback
    autonomous_player.stop_autonomous_playback()
    
    # Wait for it to stop
    while autonomous_player.is_running:
        time.sleep(0.1)
    
    print(f"✓ Autonomous playback stopped")
    
    # Get statistics
    stats = autonomous_player.get_playback_stats()
    print(f"✓ Playback statistics:")
    print(f"  - Phrases played: {stats['phrases_played']}")
    print(f"  - Session duration: {stats['session_duration']:.2f} seconds")
    print(f"  - Filters: {stats['current_filters']}")
    
    # Check audio events
    note_events = audio_engine.get_note_events()
    print(f"✓ Total note events from autonomous playback: {len(note_events)}")
    
    return autonomous_player, stats


def test_autonomous_filtering():
    """Test autonomous player with different filters"""
    print("\nTesting autonomous player filtering...")
    
    # Create setup
    library = PhraseLibrary()
    library.load_style('modal_jazz')
    
    # Test different difficulty filters
    for difficulty in [1, 2, 3]:
        phrases = library.filter_phrases(style='modal_jazz', difficulty=difficulty)
        print(f"✓ Difficulty {difficulty} phrases: {len(phrases)}")
    
    # Test different bar filters
    for bars in [1, 2, 4]:
        phrases = library.filter_phrases(style='modal_jazz', bars=bars)
        print(f"✓ {bars}-bar phrases: {len(phrases)}")
    
    print(f"✓ Filtering tests completed")


def test_concurrent_playback():
    """Test that multiple playback requests are handled correctly"""
    print("\nTesting concurrent playback handling...")
    
    phrase_player, test_phrase, audio_engine = test_phrase_player_basic()
    
    # Start first playback
    success1 = phrase_player.play_phrase(test_phrase, bpm=120)
    print(f"✓ First playback started: {success1}")
    
    # Try to start second playback (should fail)
    success2 = phrase_player.play_phrase(test_phrase, bpm=120)
    print(f"✓ Second playback rejected: {not success2}")
    
    # Wait for first to complete
    while phrase_player.is_playing:
        time.sleep(0.1)
    
    # Now second should work
    success3 = phrase_player.play_phrase(test_phrase, bpm=120)
    print(f"✓ Third playback started after first completed: {success3}")
    
    # Clean up
    phrase_player.stop_playback()
    while phrase_player.is_playing:
        time.sleep(0.1)
    
    print(f"✓ Concurrent playback test completed")


def test_playback_timing():
    """Test playback timing accuracy"""
    print("\nTesting playback timing...")
    
    # Create a chord phrase with simultaneous notes
    chord_phrase = create_chord_phrase([60, 64, 67], duration_beats=2.0)  # C major chord
    chord_phrase.metadata['description'] = 'Test Timing Chord'
    
    audio_engine = MockAudioEngine()
    phrase_player = PhrasePlayer(audio_engine)
    
    # Play at different tempos and measure timing
    for bpm in [60, 120, 180]:
        print(f"  Testing at {bpm} BPM...")
        
        audio_engine.clear_events()
        start_time = time.time()
        
        phrase_player.play_phrase(chord_phrase, bpm=bpm)
        
        # Wait for playback to complete
        while phrase_player.is_playing:
            time.sleep(0.01)
        
        end_time = time.time()
        actual_duration = end_time - start_time
        expected_duration = chord_phrase.get_duration_seconds(bpm)
        
        print(f"    Expected: {expected_duration:.2f}s, Actual: {actual_duration:.2f}s")
        
        # Check timing accuracy (allow some tolerance)
        timing_error = abs(actual_duration - expected_duration)
        if timing_error < 0.2:  # 200ms tolerance
            print(f"    ✓ Timing accurate (error: {timing_error:.3f}s)")
        else:
            print(f"    ⚠ Timing error: {timing_error:.3f}s")
    
    print(f"✓ Timing test completed")


if __name__ == "__main__":
    print("=== Phase 4.3 Phrase Playback Engine Test ===\n")
    
    try:
        test_phrase_player_basic()
        test_phrase_playback()
        test_phrase_library_integration()
        test_autonomous_player()
        test_autonomous_filtering()
        test_concurrent_playback()
        test_playback_timing()
        
        print("\n=== All tests completed successfully! ===")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
