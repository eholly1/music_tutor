"""
Music Theory Utilities

Helper functions for music theory calculations and conversions.
Will be expanded in Phase 4.
"""

import math
from typing import Dict, List
from utils.logger import get_logger


class MusicTheory:
    """
    Music theory utilities and calculations
    
    This class provides:
    - Note name to frequency conversion
    - MIDI note number conversions
    - Scale and mode definitions
    - Interval calculations
    """
    
    # MIDI note 69 (A4) = 440 Hz
    A4_FREQUENCY = 440.0
    A4_MIDI_NUMBER = 69
    
    # Chromatic note names
    NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    def __init__(self):
        """Initialize music theory utilities"""
        self.logger = get_logger()
        self.logger.debug("Music Theory utilities initialized")
    
    @classmethod
    def note_to_frequency(cls, note_name: str) -> float:
        """
        Convert note name to frequency in Hz
        
        Args:
            note_name (str): Note name (e.g., "C4", "F#3")
            
        Returns:
            float: Frequency in Hz
        """
        try:
            # Parse note name (e.g., "C4" -> note="C", octave=4)
            if len(note_name) < 2:
                raise ValueError("Invalid note name format")
            
            if '#' in note_name or 'b' in note_name:
                note = note_name[:-1]
                octave = int(note_name[-1])
            else:
                note = note_name[:-1]
                octave = int(note_name[-1])
            
            # Convert to MIDI note number
            midi_number = cls.note_to_midi_number(note, octave)
            
            # Convert MIDI number to frequency
            return cls.midi_to_frequency(midi_number)
            
        except Exception as e:
            raise ValueError(f"Invalid note name: {note_name}")
    
    @classmethod
    def note_to_midi_number(cls, note: str, octave: int) -> int:
        """
        Convert note name and octave to MIDI note number
        
        Args:
            note (str): Note name (e.g., "C", "F#")
            octave (int): Octave number
            
        Returns:
            int: MIDI note number (0-127)
        """
        # Handle flats and sharps
        if 'b' in note:
            note = note.replace('b', '')
            semitone_offset = -1
        elif '#' in note:
            note = note.replace('#', '')
            semitone_offset = 1
        else:
            semitone_offset = 0
        
        # Get base note index
        if note not in cls.NOTE_NAMES:
            # Handle natural notes
            note_index = ['C', 'D', 'E', 'F', 'G', 'A', 'B'].index(note) * 2
            if note in ['E', 'B']:
                note_index -= 1  # E and B don't have sharps
            elif note > 'C':
                note_index -= 1  # Adjust for missing C#
        else:
            note_index = cls.NOTE_NAMES.index(note)
        
        # Calculate MIDI number
        midi_number = (octave + 1) * 12 + note_index + semitone_offset
        
        return max(0, min(127, midi_number))
    
    @classmethod
    def midi_to_frequency(cls, midi_number: int) -> float:
        """
        Convert MIDI note number to frequency
        
        Args:
            midi_number (int): MIDI note number (0-127)
            
        Returns:
            float: Frequency in Hz
        """
        # Equal temperament formula: f = 440 * 2^((n-69)/12)
        return cls.A4_FREQUENCY * (2.0 ** ((midi_number - cls.A4_MIDI_NUMBER) / 12.0))
    
    @classmethod
    def frequency_to_midi(cls, frequency: float) -> int:
        """
        Convert frequency to nearest MIDI note number
        
        Args:
            frequency (float): Frequency in Hz
            
        Returns:
            int: MIDI note number
        """
        # Inverse of midi_to_frequency
        midi_float = cls.A4_MIDI_NUMBER + 12 * math.log2(frequency / cls.A4_FREQUENCY)
        return int(round(midi_float))
    
    @classmethod
    def get_scale_notes(cls, root: str, scale_type: str = "major") -> List[str]:
        """
        Get notes in a scale
        
        Args:
            root (str): Root note name
            scale_type (str): Scale type (major, minor, dorian, etc.)
            
        Returns:
            List[str]: Notes in the scale
        """
        # Scale interval patterns (semitones)
        patterns = {
            'major': [2, 2, 1, 2, 2, 2, 1],
            'minor': [2, 1, 2, 2, 1, 2, 2],
            'dorian': [2, 1, 2, 2, 2, 1, 2],
            'mixolydian': [2, 2, 1, 2, 2, 1, 2]
        }
        
        if scale_type not in patterns:
            raise ValueError(f"Unknown scale type: {scale_type}")
        
        pattern = patterns[scale_type]
        
        # Start from root note
        root_index = cls.NOTE_NAMES.index(root) if root in cls.NOTE_NAMES else 0
        notes = [cls.NOTE_NAMES[root_index]]
        
        current_index = root_index
        for interval in pattern[:-1]:  # Exclude last interval (back to root)
            current_index = (current_index + interval) % 12
            notes.append(cls.NOTE_NAMES[current_index])
        
        return notes
