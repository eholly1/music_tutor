"""
Phrase Library Management

Handles loading, storing, and retrieving musical phrases.
Updated for Phase 4.2 - Beat-based timing and MIDI note numbers.
"""

import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Union
from music.phrase import Phrase, MusicalNote, create_simple_scale_phrase
from utils.logger import get_logger


class PhraseLibrary:
    """
    Manages the musical phrase library
    
    This class handles:
    - Loading phrases from JSON files
    - Filtering phrases by style, difficulty, bars
    - Caching phrases for performance
    - Adding new phrases to the library
    - Converting legacy phrase formats to new beat-based format
    """
    
    def __init__(self, library_path: str = "data/phrases"):
        """
        Initialize phrase library
        
        Args:
            library_path (str): Path to phrase library directory
        """
        self.logger = get_logger()
        self.library_path = Path(library_path)
        self.phrases = {}  # Organized by style -> difficulty -> phrases
        self.loaded_styles = set()  # Track which styles have been loaded
        
        # Note name to MIDI number mapping
        self.note_mapping = self._create_note_mapping()
        
        # Duration mapping (beats)
        self.duration_mapping = {
            'whole': 4.0,
            'half': 2.0,
            'quarter': 1.0,
            'eighth': 0.5,
            'sixteenth': 0.25,
            'dotted_half': 3.0,
            'dotted_quarter': 1.5,
            'dotted_eighth': 0.75
        }
        
        self.logger.info(f"Phrase Library initialized - {library_path}")
    
    def _create_note_mapping(self) -> Dict[str, int]:
        """Create mapping from note names to MIDI numbers"""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        flat_equivalents = {
            'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'
        }
        mapping = {}
        
        for octave in range(10):  # MIDI supports 0-9 octaves
            for i, note in enumerate(notes):
                midi_number = (octave + 1) * 12 + i
                if midi_number <= 127:  # MIDI limit
                    mapping[f"{note}{octave}"] = midi_number
                    
            # Add flat note equivalents for this octave
            for flat_note, sharp_equivalent in flat_equivalents.items():
                if f"{sharp_equivalent}{octave}" in mapping:
                    mapping[f"{flat_note}{octave}"] = mapping[f"{sharp_equivalent}{octave}"]
        
        return mapping
    
    
    def load_phrase_data(self):
        """Load phrases from all available JSON files"""
        styles = self.get_available_styles()
        loaded_count = 0
        
        for style in styles:
            if self.load_style(style):
                loaded_count += 1
        
        self.logger.info(f"Loaded {loaded_count} phrase styles")
        return loaded_count > 0
    
    def load_style(self, style: str) -> bool:
        """
        Load phrases for a specific style
        
        Args:
            style (str): Musical style to load
            
        Returns:
            bool: True if style loaded successfully
        """
        if style in self.loaded_styles:
            self.logger.debug(f"Style {style} already loaded")
            return True
            
        try:
            style_file = self.library_path / f"{style}.json"
            if not style_file.exists():
                self.logger.error(f"Style file not found: {style_file}")
                return False
            
            with open(style_file, 'r') as f:
                data = json.load(f)
            
            # Initialize style structure
            if style not in self.phrases:
                self.phrases[style] = {}
            
            phrases_loaded = 0
            
            for phrase_data in data.get('phrases', []):
                try:
                    phrase = self._parse_phrase_data(phrase_data, style)
                    
                    # Organize by difficulty
                    difficulty = phrase.difficulty
                    if difficulty not in self.phrases[style]:
                        self.phrases[style][difficulty] = []
                    
                    self.phrases[style][difficulty].append(phrase)
                    phrases_loaded += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to parse phrase {phrase_data.get('id', 'unknown')}: {e}")
                    continue
            
            self.loaded_styles.add(style)
            self.logger.info(f"Loaded {phrases_loaded} phrases for style: {style}")
            return phrases_loaded > 0
            
        except Exception as e:
            self.logger.error(f"Error loading style {style}: {e}")
            return False
    
    def _parse_phrase_data(self, phrase_data: Dict, style: str) -> Phrase:
        """
        Parse phrase data from JSON format to Phrase object
        
        Args:
            phrase_data: Raw phrase data from JSON
            style: Musical style name
            
        Returns:
            Phrase object
        """
        notes = []
        current_time = 0.0  # Track beat position
        
        for note_data in phrase_data.get('notes', []):
            # Convert note name to MIDI number if needed
            pitch = note_data['pitch']
            if isinstance(pitch, str):
                if pitch in self.note_mapping:
                    midi_pitch = self.note_mapping[pitch]
                else:
                    self.logger.warning(f"Unknown note name: {pitch}, skipping")
                    continue
            else:
                midi_pitch = int(pitch)  # Already MIDI number
            
            # Convert duration to beats if needed
            duration = note_data['duration']
            if isinstance(duration, str):
                if duration in self.duration_mapping:
                    beat_duration = self.duration_mapping[duration]
                else:
                    self.logger.warning(f"Unknown duration: {duration}, using quarter note")
                    beat_duration = 1.0
            else:
                beat_duration = float(duration)  # Already in beats
            
            # Create note with beat-based timing
            note = MusicalNote(
                pitch=midi_pitch,
                start_time=current_time,
                duration=beat_duration,
                velocity=note_data.get('velocity', 80)
            )
            notes.append(note)
            
            # Advance time for next note (assuming sequential for now)
            current_time += beat_duration
        
        # Create metadata using new format
        metadata = {
            'style': style,
            'difficulty': phrase_data.get('difficulty', 1),
            'key': phrase_data.get('key', 'C'),
            'tempo': phrase_data.get('tempo', 120),
            'bars': self._calculate_bars(current_time, phrase_data.get('time_signature', [4, 4])),
            'time_signature': tuple(phrase_data.get('time_signature', [4, 4])),
            'description': phrase_data.get('description', phrase_data.get('name', 'Unnamed phrase')),
            'id': phrase_data.get('id'),
            'name': phrase_data.get('name')
        }
        
        return Phrase(notes, metadata)
    
    def _calculate_bars(self, total_beats: float, time_signature: List[int]) -> int:
        """
        Calculate number of bars based on total beats and time signature
        
        Args:
            total_beats: Total duration in beats
            time_signature: [numerator, denominator]
            
        Returns:
            Number of bars (1, 2, or 4)
        """
        beats_per_bar = time_signature[0]
        calculated_bars = max(1, round(total_beats / beats_per_bar))
        
        # Constrain to supported values
        if calculated_bars <= 1:
            return 1
        elif calculated_bars <= 2:
            return 2
        else:
            return 4
    
    
    def get_phrase(self, style: str, difficulty: int, bars: Optional[int] = None) -> Optional[Phrase]:
        """
        Retrieve appropriate phrase based on criteria
        
        Args:
            style: Musical style
            difficulty: Difficulty level (1-5)
            bars: Number of bars (1, 2, or 4), optional
            
        Returns:
            Phrase object or None if no matching phrase found
        """
        phrases = self.filter_phrases(style=style, difficulty=difficulty, bars=bars)
        if phrases:
            return random.choice(phrases)  # Return random phrase from matches
        return None
    
    def filter_phrases(self, style: Optional[str] = None, 
                      difficulty: Optional[int] = None, 
                      bars: Optional[int] = None) -> List[Phrase]:
        """
        Get list of phrases matching criteria
        
        Args:
            style: Musical style filter (optional)
            difficulty: Difficulty level filter (optional)
            bars: Number of bars filter (optional)
            
        Returns:
            List of matching Phrase objects
        """
        # If style specified, load it if not already loaded
        if style and style not in self.loaded_styles:
            if not self.load_style(style):
                return []
        
        # Get all phrases or phrases for specific style
        if style:
            style_phrases = self.phrases.get(style, {})
            if difficulty is not None:
                phrases_to_check = style_phrases.get(difficulty, [])
            else:
                # Get all difficulties for this style
                phrases_to_check = []
                for diff_phrases in style_phrases.values():
                    phrases_to_check.extend(diff_phrases)
        else:
            # Get phrases from all styles
            phrases_to_check = []
            for style_data in self.phrases.values():
                for diff_phrases in style_data.values():
                    phrases_to_check.extend(diff_phrases)
        
        # Apply bars filter if specified
        if bars is not None:
            phrases_to_check = [p for p in phrases_to_check if p.bars == bars]
        
        self.logger.debug(f"Filtered phrases: style={style}, difficulty={difficulty}, "
                         f"bars={bars} -> {len(phrases_to_check)} matches")
        
        return phrases_to_check
    
    def add_phrase(self, phrase: Phrase):
        """
        Add new phrase to library
        
        Args:
            phrase: Phrase object to add
        """
        style = phrase.style
        difficulty = phrase.difficulty
        
        # Initialize structure if needed
        if style not in self.phrases:
            self.phrases[style] = {}
        if difficulty not in self.phrases[style]:
            self.phrases[style][difficulty] = []
        
        # Add phrase
        self.phrases[style][difficulty].append(phrase)
        self.loaded_styles.add(style)
        
        self.logger.info(f"Added phrase to library: {style} difficulty {difficulty}")
    
    def get_phrases_by_style(self, style: str) -> List[Phrase]:
        """
        Get all phrases for a specific style
        
        Args:
            style: Musical style
            
        Returns:
            List of all phrases for the style
        """
        return self.filter_phrases(style=style)
    
    
    def get_phrase_by_id(self, style: str, phrase_id: str) -> Optional[Phrase]:
        """
        Get specific phrase by ID
        
        Args:
            style: Musical style
            phrase_id: Phrase identifier
            
        Returns:
            Phrase or None if not found
        """
        phrases = self.get_phrases_by_style(style)
        for phrase in phrases:
            if phrase.metadata.get('id') == phrase_id:
                return phrase
        return None
    
    def get_available_styles(self) -> List[str]:
        """
        Get list of available musical styles
        
        Returns:
            List of available style names from JSON files
        """
        styles = []
        if self.library_path.exists():
            for file_path in self.library_path.glob("*.json"):
                styles.append(file_path.stem)
        return sorted(styles)
    
    def get_difficulty_levels(self, style: str) -> List[int]:
        """
        Get available difficulty levels for a style
        
        Args:
            style: Musical style
            
        Returns:
            List of available difficulty levels
        """
        if style not in self.loaded_styles:
            self.load_style(style)
        
        if style in self.phrases:
            return sorted(self.phrases[style].keys())
        return []
    
    def get_library_stats(self) -> Dict[str, Union[int, Dict]]:
        """
        Get statistics about the loaded phrase library
        
        Returns:
            Dictionary with library statistics
        """
        stats = {
            'total_styles': len(self.loaded_styles),
            'total_phrases': 0,
            'styles': {}
        }
        
        for style, difficulties in self.phrases.items():
            style_count = 0
            style_stats = {}
            
            for difficulty, phrases in difficulties.items():
                phrase_count = len(phrases)
                style_count += phrase_count
                style_stats[f'difficulty_{difficulty}'] = phrase_count
            
            stats['styles'][style] = {
                'total_phrases': style_count,
                'difficulties': style_stats
            }
            stats['total_phrases'] += style_count
        
        return stats
    
    def save_phrase_to_file(self, phrase: Phrase, style: str = None):
        """
        Save a phrase to the appropriate JSON file
        
        Args:
            phrase: Phrase to save
            style: Style name (uses phrase.style if not specified)
        """
        target_style = style or phrase.style
        style_file = self.library_path / f"{target_style}.json"
        
        # Load existing data or create new
        if style_file.exists():
            with open(style_file, 'r') as f:
                data = json.load(f)
        else:
            data = {
                'style': target_style,
                'description': f"{target_style.title()} phrase library",
                'phrases': []
            }
        
        # Convert phrase to JSON format
        phrase_data = {
            'id': phrase.metadata.get('id', f"{target_style}_{len(data['phrases']) + 1:03d}"),
            'name': phrase.metadata.get('name', 'Generated phrase'),
            'difficulty': phrase.difficulty,
            'key': phrase.key,
            'tempo': phrase.tempo,
            'time_signature': list(phrase.time_signature),
            'description': phrase.metadata.get('description', ''),
            'notes': []
        }
        
        # Convert notes to JSON format
        for note in phrase.notes:
            note_data = {
                'pitch': note.pitch,  # Keep as MIDI number
                'start_time': note.start_time,  # Beat position
                'duration': note.duration,  # Duration in beats
                'velocity': note.velocity
            }
            phrase_data['notes'].append(note_data)
        
        # Add to data and save
        data['phrases'].append(phrase_data)
        
        self.library_path.mkdir(parents=True, exist_ok=True)
        with open(style_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Saved phrase {phrase_data['id']} to {style_file}")


# Utility functions for creating and managing phrase libraries

def create_scale_phrase_library(root_pitches: List[int], scales: Dict[str, List[int]], 
                               style: str = 'scales') -> PhraseLibrary:
    """
    Create a phrase library with scale patterns
    
    Args:
        root_pitches: List of root MIDI pitches
        scales: Dictionary of scale_name -> interval_list
        style: Style name for the library
        
    Returns:
        PhraseLibrary with generated scale phrases
    """
    library = PhraseLibrary()
    
    for root in root_pitches:
        for scale_name, intervals in scales.items():
            for difficulty in range(1, 4):  # Create 3 difficulty levels
                note_count = min(4 + difficulty, len(intervals))
                scale_intervals = intervals[:note_count]
                
                phrase = create_simple_scale_phrase(
                    root, scale_intervals, difficulty, style
                )
                phrase.metadata['name'] = f"{scale_name} from {root}"
                phrase.metadata['id'] = f"{style}_{root}_{scale_name}_{difficulty}"
                
                library.add_phrase(phrase)
    
    return library
