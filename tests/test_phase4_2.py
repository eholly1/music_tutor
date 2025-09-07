#!/usr/bin/env python3
"""
Test script for Phase 4.2 Phrase Library Management

This script tests the PhraseLibrary class to ensure it can load, filter,
and manage phrases correctly with the new beat-based format.
"""

import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from music.library import PhraseLibrary, create_scale_phrase_library
from music.phrase import create_simple_scale_phrase


def test_library_initialization():
    """Test PhraseLibrary initialization and basic setup"""
    print("Testing PhraseLibrary initialization...")
    
    library = PhraseLibrary()
    print(f"✓ Library initialized with path: {library.library_path}")
    
    # Test available styles
    styles = library.get_available_styles()
    print(f"✓ Available styles: {styles}")
    
    return library


def test_phrase_loading():
    """Test loading phrases from JSON files"""
    print("\nTesting phrase loading...")
    
    library = PhraseLibrary()
    
    # Test loading modal_jazz style
    success = library.load_style('modal_jazz')
    print(f"✓ Modal jazz loaded: {success}")
    
    if success:
        # Check what was loaded
        phrases = library.get_phrases_by_style('modal_jazz')
        print(f"✓ Loaded {len(phrases)} modal jazz phrases")
        
        if phrases:
            phrase = phrases[0]
            print(f"  - First phrase: {phrase}")
            print(f"  - Notes: {len(phrase.notes)}")
            print(f"  - Duration: {phrase.get_duration_beats()} beats")
            print(f"  - MIDI pitches: {[note.pitch for note in phrase.notes]}")
    
    return library


def test_phrase_filtering():
    """Test phrase filtering and retrieval methods"""
    print("\nTesting phrase filtering...")
    
    library = PhraseLibrary()
    library.load_style('modal_jazz')
    
    # Test filtering by difficulty
    easy_phrases = library.filter_phrases(style='modal_jazz', difficulty=1)
    print(f"✓ Difficulty 1 phrases: {len(easy_phrases)}")
    
    medium_phrases = library.filter_phrases(style='modal_jazz', difficulty=2)
    print(f"✓ Difficulty 2 phrases: {len(medium_phrases)}")
    
    # Test get_phrase method (random selection)
    random_phrase = library.get_phrase('modal_jazz', difficulty=1)
    if random_phrase:
        print(f"✓ Random phrase retrieved: {random_phrase.metadata.get('name', 'unnamed')}")
    
    # Test filtering by bars
    one_bar_phrases = library.filter_phrases(style='modal_jazz', bars=1)
    print(f"✓ 1-bar phrases: {len(one_bar_phrases)}")
    
    return library


def test_library_stats():
    """Test library statistics and information methods"""
    print("\nTesting library statistics...")
    
    library = PhraseLibrary()
    library.load_phrase_data()  # Load all available styles
    
    # Get stats
    stats = library.get_library_stats()
    print(f"✓ Library stats:")
    print(f"  - Total styles: {stats['total_styles']}")
    print(f"  - Total phrases: {stats['total_phrases']}")
    
    for style, style_stats in stats['styles'].items():
        print(f"  - {style}: {style_stats['total_phrases']} phrases")
        for diff_key, count in style_stats['difficulties'].items():
            print(f"    - {diff_key}: {count}")
    
    # Test difficulty levels for a style
    difficulties = library.get_difficulty_levels('modal_jazz')
    print(f"✓ Modal jazz difficulties: {difficulties}")


def test_phrase_creation_and_addition():
    """Test creating and adding new phrases to library"""
    print("\nTesting phrase creation and addition...")
    
    library = PhraseLibrary()
    
    # Create a simple test phrase
    test_phrase = create_simple_scale_phrase(
        root_pitch=60,  # Middle C
        scale_notes=[0, 2, 4, 5],  # C major tetrachord
        difficulty=1,
        style='test_style'
    )
    test_phrase.metadata['id'] = 'test_001'
    test_phrase.metadata['name'] = 'Test C Major'
    
    # Add to library
    library.add_phrase(test_phrase)
    print(f"✓ Added test phrase to library")
    
    # Verify it was added
    retrieved = library.get_phrase('test_style', difficulty=1)
    if retrieved:
        print(f"✓ Retrieved test phrase: {retrieved.metadata['name']}")
        print(f"  - MIDI pitches: {[note.pitch for note in retrieved.notes]}")
    
    return library


def test_utility_functions():
    """Test utility functions for creating phrase libraries"""
    print("\nTesting utility functions...")
    
    # Define some scales
    scales = {
        'major': [0, 2, 4, 5, 7, 9, 11, 12],
        'minor': [0, 2, 3, 5, 7, 8, 10, 12],
        'dorian': [0, 2, 3, 5, 7, 9, 10, 12]
    }
    
    # Create scale library
    root_pitches = [60, 62, 64]  # C, D, E
    scale_library = create_scale_phrase_library(root_pitches, scales, 'generated_scales')
    
    print(f"✓ Created scale library")
    
    # Check what was generated
    stats = scale_library.get_library_stats()
    print(f"✓ Generated library stats: {stats['total_phrases']} phrases")
    
    # Test a generated phrase
    phrase = scale_library.get_phrase('generated_scales', difficulty=1)
    if phrase:
        print(f"✓ Sample generated phrase: {phrase.metadata['name']}")
        print(f"  - Notes: {len(phrase.notes)}")


def test_phrase_by_id():
    """Test retrieving phrases by ID"""
    print("\nTesting phrase retrieval by ID...")
    
    library = PhraseLibrary()
    library.load_style('modal_jazz')
    
    # Get first phrase to find its ID
    phrases = library.get_phrases_by_style('modal_jazz')
    if phrases:
        first_phrase = phrases[0]
        phrase_id = first_phrase.metadata.get('id')
        
        if phrase_id:
            # Retrieve by ID
            retrieved = library.get_phrase_by_id('modal_jazz', phrase_id)
            if retrieved:
                print(f"✓ Retrieved phrase by ID '{phrase_id}': {retrieved.metadata.get('name')}")
            else:
                print(f"✗ Failed to retrieve phrase by ID '{phrase_id}'")
        else:
            print("⚠ First phrase has no ID")


if __name__ == "__main__":
    print("=== Phase 4.2 Phrase Library Management Test ===\n")
    
    try:
        test_library_initialization()
        test_phrase_loading()
        test_phrase_filtering()
        test_library_stats()
        test_phrase_creation_and_addition()
        test_utility_functions()
        test_phrase_by_id()
        
        print("\n=== All tests completed successfully! ===")
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
