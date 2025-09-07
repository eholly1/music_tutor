"""
Musical Phrase Representation

Classes for representing musical phrases and notes.
Updated for Phase 4.1 - Beat-based timing and MIDI note numbers.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Tuple
from utils.logger import get_logger


@dataclass
class MusicalNote:
    """Represents a musical note with MIDI pitch, beat-based timing, and dynamics"""
    pitch: int          # MIDI note number (0-127)
    start_time: float   # Beat position within phrase (0.0 = start)
    duration: float     # Note length in beats
    velocity: int = 80  # MIDI velocity (0-127)
    
    def __post_init__(self):
        """Validate MIDI note parameters"""
        if not 0 <= self.pitch <= 127:
            raise ValueError(f"MIDI pitch must be 0-127, got {self.pitch}")
        if not 0 <= self.velocity <= 127:
            raise ValueError(f"MIDI velocity must be 0-127, got {self.velocity}")
        if self.start_time < 0:
            raise ValueError(f"Start time must be >= 0, got {self.start_time}")
        if self.duration <= 0:
            raise ValueError(f"Duration must be > 0, got {self.duration}")


class Phrase:
    """
    Represents a musical phrase with beat-based timing
    
    A phrase consists of a sequence of musical notes with metadata
    about style, difficulty, key, tempo, bars, etc.
    """
    
    def __init__(self, notes: List[MusicalNote], metadata: Dict[str, Any]):
        """
        Initialize musical phrase
        
        Args:
            notes: List of MusicalNote objects
            metadata: Phrase metadata (style, difficulty, key, tempo, bars, etc.)
        """
        self.logger = get_logger()
        self.notes = notes
        self.metadata = self._validate_metadata(metadata)
        self.logger.debug(f"Created phrase: {self.metadata.get('description', 'unnamed')}")
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and set default metadata values"""
        validated = metadata.copy()
        
        # Set defaults for required fields
        validated.setdefault('style', 'modal_jazz')
        validated.setdefault('difficulty', 2)
        validated.setdefault('key', 'D_dorian')
        validated.setdefault('tempo', 120)
        validated.setdefault('bars', 2)
        validated.setdefault('time_signature', (4, 4))
        validated.setdefault('description', 'Musical phrase')
        
        # Validate values
        if not 1 <= validated['difficulty'] <= 5:
            raise ValueError(f"Difficulty must be 1-5, got {validated['difficulty']}")
        if validated['bars'] not in [1, 2, 4]:
            raise ValueError(f"Bars must be 1, 2, or 4, got {validated['bars']}")
        if validated['tempo'] <= 0:
            raise ValueError(f"Tempo must be > 0, got {validated['tempo']}")
        
        return validated
    
    
    @property
    def difficulty(self) -> int:
        """Get phrase difficulty level (1-5)"""
        return self.metadata['difficulty']
    
    @property
    def style(self) -> str:
        """Get phrase musical style"""
        return self.metadata['style']
    
    @property
    def tempo(self) -> int:
        """Get phrase tempo in BPM"""
        return self.metadata['tempo']
    
    @property
    def key(self) -> str:
        """Get phrase key signature"""
        return self.metadata['key']
    
    @property
    def bars(self) -> int:
        """Get phrase length in bars (1, 2, or 4)"""
        return self.metadata['bars']
    
    @property
    def time_signature(self) -> Tuple[int, int]:
        """Get phrase time signature as (numerator, denominator)"""
        return self.metadata['time_signature']
    
    @property
    def id(self) -> str:
        """Get phrase ID"""
        return self.metadata.get('id', 'unknown')
    
    @property
    def name(self) -> str:
        """Get phrase name/description"""
        return self.metadata.get('description', 'Musical phrase')
    
    @property
    def measures(self) -> int:
        """Get phrase length in measures (alias for bars)"""
        return self.bars
    
    def get_duration_beats(self) -> float:
        """
        Return total duration in beats
        
        Returns:
            float: Duration in beats based on bars and time signature
        """
        return self.bars * self.time_signature[0]
    
    def get_duration_seconds(self, bpm: int = None) -> float:
        """
        Return total duration in seconds at given BPM
        
        Args:
            bpm: Beats per minute (uses phrase tempo if not specified)
            
        Returns:
            float: Duration in seconds
        """
        effective_bpm = bpm or self.tempo
        beats_per_second = effective_bpm / 60.0
        return self.get_duration_beats() / beats_per_second
    
    def get_note_at_beat(self, beat_position: float) -> List[MusicalNote]:
        """
        Get all notes that are playing at a specific beat position
        
        Args:
            beat_position: Beat position to check (0.0 = start of phrase)
            
        Returns:
            List of MusicalNote objects active at that beat
        """
        active_notes = []
        for note in self.notes:
            note_end = note.start_time + note.duration
            if note.start_time <= beat_position < note_end:
                active_notes.append(note)
        return active_notes
    
    def get_notes_in_range(self, start_beat: float, end_beat: float) -> List[MusicalNote]:
        """
        Get all notes that start within a beat range
        
        Args:
            start_beat: Start of range (inclusive)
            end_beat: End of range (exclusive)
            
        Returns:
            List of MusicalNote objects starting in range
        """
        notes_in_range = []
        for note in self.notes:
            if start_beat <= note.start_time < end_beat:
                notes_in_range.append(note)
        return notes_in_range
    
    def validate_timing(self) -> bool:
        """
        Validate that all notes fit within the phrase duration
        
        Returns:
            bool: True if all notes are within phrase bounds
        """
        phrase_duration = self.get_duration_beats()
        for note in self.notes:
            note_end = note.start_time + note.duration
            if note_end > phrase_duration:
                self.logger.warning(
                    f"Note extends beyond phrase: note ends at beat {note_end}, "
                    f"phrase ends at beat {phrase_duration}"
                )
                return False
        return True
    
    
    def __len__(self) -> int:
        """Return number of notes in phrase"""
        return len(self.notes)
    
    def __str__(self) -> str:
        """String representation of phrase"""
        description = self.metadata.get('description', 'Unnamed Phrase')
        return (f"Phrase('{description}', {len(self.notes)} notes, "
                f"difficulty {self.difficulty}, {self.bars} bars, {self.tempo} BPM)")
    
    def __repr__(self) -> str:
        """Developer representation of phrase"""
        return (f"Phrase(notes={len(self.notes)}, "
                f"metadata={self.metadata})")
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert phrase to dictionary for JSON serialization
        
        Returns:
            Dict containing phrase data
        """
        return {
            'notes': [
                {
                    'pitch': note.pitch,
                    'start_time': note.start_time,
                    'duration': note.duration,
                    'velocity': note.velocity
                }
                for note in self.notes
            ],
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Phrase':
        """
        Create phrase from dictionary (for JSON deserialization)
        
        Args:
            data: Dictionary containing phrase data
            
        Returns:
            Phrase object
        """
        notes = [
            MusicalNote(
                pitch=note_data['pitch'],
                start_time=note_data['start_time'],
                duration=note_data['duration'],
                velocity=note_data['velocity']
            )
            for note_data in data['notes']
        ]
        return cls(notes, data['metadata'])


# Utility functions for creating common phrase patterns

def create_simple_scale_phrase(root_pitch: int, scale_notes: List[int], 
                              difficulty: int = 1, style: str = 'modal_jazz') -> Phrase:
    """
    Create a simple ascending scale phrase
    
    Args:
        root_pitch: MIDI pitch for root note
        scale_notes: List of scale intervals (semitones from root)
        difficulty: Difficulty level (1-5)
        style: Musical style
        
    Returns:
        Phrase object with scale pattern
    """
    notes = []
    for i, interval in enumerate(scale_notes):
        note = MusicalNote(
            pitch=root_pitch + interval,
            start_time=float(i),  # One note per beat
            duration=0.8,  # Slightly detached
            velocity=80
        )
        notes.append(note)
    
    metadata = {
        'style': style,
        'difficulty': difficulty,
        'key': f'MIDI_{root_pitch}',
        'tempo': 120,
        'bars': max(1, len(scale_notes) // 4),
        'time_signature': (4, 4),
        'description': f'{style.title()} scale phrase'
    }
    
    return Phrase(notes, metadata)


def create_chord_phrase(chord_pitches: List[int], duration_beats: float = 2.0,
                       difficulty: int = 2, style: str = 'modal_jazz') -> Phrase:
    """
    Create a phrase with a single chord
    
    Args:
        chord_pitches: List of MIDI pitches for chord notes
        duration_beats: How long to hold the chord
        difficulty: Difficulty level (1-5)
        style: Musical style
        
    Returns:
        Phrase object with chord
    """
    notes = []
    for pitch in chord_pitches:
        note = MusicalNote(
            pitch=pitch,
            start_time=0.0,  # All notes start together
            duration=duration_beats,
            velocity=70
        )
        notes.append(note)
    
    metadata = {
        'style': style,
        'difficulty': difficulty,
        'key': f'MIDI_{min(chord_pitches)}',
        'tempo': 120,
        'bars': max(1, int(duration_beats) // 4),
        'time_signature': (4, 4),
        'description': f'{style.title()} chord phrase'
    }
    
    return Phrase(notes, metadata)
