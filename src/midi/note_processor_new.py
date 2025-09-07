"""
MIDI Note Processing Module

This module processes raw MIDI events and converts them to musical note objects.
Phase 2.2 implementation with real-time note processing.
"""

import time
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from utils.logger import get_logger


@dataclass
class MIDINote:
    """Represents a processed MIDI note with timing information"""
    pitch: int          # MIDI note number (0-127)
    velocity: int       # Note velocity (0-127)  
    timestamp: float    # Note start time relative to session start
    duration: Optional[float] = None  # Note duration in seconds

    def get_note_name(self) -> str:
        """Get the musical note name (e.g., 'C4', 'F#3')"""
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (self.pitch // 12) - 1
        note_name = note_names[self.pitch % 12]
        return f"{note_name}{octave}"

    def get_frequency(self) -> float:
        """Get the fundamental frequency in Hz"""
        return 440.0 * (2.0 ** ((self.pitch - 69) / 12.0))

    def __str__(self) -> str:
        """String representation of the note"""
        duration_str = f", {self.duration:.3f}s" if self.duration else ""
        return f"Note({self.get_note_name()}, vel={self.velocity}{duration_str})"


class NoteProcessor:
    """
    Processes MIDI events and converts them to musical note data
    
    This class handles:
    - Converting MIDI note on/off events to note objects
    - Calculating note durations
    - Filtering and cleaning MIDI data
    - Real-time note event processing
    """
    
    def __init__(self):
        """Initialize the note processor"""
        self.logger = get_logger(__name__)
        
        # Track active notes: pitch -> (velocity, start_timestamp)
        self.active_notes: Dict[int, Tuple[int, float]] = {}
        
        # Completed notes from current session
        self.completed_notes: List[MIDINote] = []
        
        # Session timing
        self.session_start_time: Optional[float] = None
        
        self.logger.info("MIDI note processor initialized")

    def process_midi_event(self, message: List[int], timestamp: float) -> Optional[MIDINote]:
        """
        Process a raw MIDI message and return completed note if available
        
        Args:
            message: Raw MIDI message as list [status, data1, data2, ...]
            timestamp: Message timestamp in seconds
            
        Returns:
            MIDINote: Completed note object or None if note is still active
        """
        try:
            if not message or len(message) < 1:
                return None
            
            # Handle None timestamp
            if timestamp is None:
                timestamp = time.time()
                
            # Initialize session start time on first event
            if self.session_start_time is None:
                self.session_start_time = timestamp
                self.logger.info("Started new MIDI recording session")
            
            status_byte = message[0]
            message_type = status_byte & 0xF0  # Upper 4 bits
            channel = status_byte & 0x0F       # Lower 4 bits
            
            # Handle note events
            if message_type == 0x90 and len(message) >= 3:  # Note On
                pitch = message[1]
                velocity = message[2]
                
                # Note on with velocity 0 is treated as note off
                if velocity == 0:
                    return self._handle_note_off(pitch, velocity, timestamp)
                else:
                    return self._handle_note_on(pitch, velocity, timestamp)
                    
            elif message_type == 0x80 and len(message) >= 3:  # Note Off
                pitch = message[1] 
                velocity = message[2]
                return self._handle_note_off(pitch, velocity, timestamp)
                
            elif message_type == 0xB0 and len(message) >= 3:  # Control Change
                controller = message[1]
                value = message[2]
                self._handle_control_change(controller, value, channel)
                
            elif message_type == 0xC0 and len(message) >= 2:  # Program Change
                program = message[1]
                self._handle_program_change(program, channel)
                
            elif message_type == 0xE0 and len(message) >= 3:  # Pitch Bend
                lsb = message[1]
                msb = message[2]
                self._handle_pitch_bend(lsb, msb, channel)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error processing MIDI event {message}: {e}")
            return None

    def _handle_note_on(self, pitch: int, velocity: int, timestamp: float) -> Optional[MIDINote]:
        """
        Handle MIDI note on event
        
        Args:
            pitch: MIDI note number
            velocity: Note velocity  
            timestamp: Event timestamp
            
        Returns:
            MIDINote: Completed note if this is a retrigger, None otherwise
        """
        if timestamp is None:
            self.logger.warning("Received None timestamp in note on handler")
            return None
            
        completed_note = None
        
        # If note is already active, complete the previous note
        if pitch in self.active_notes:
            prev_velocity, start_time = self.active_notes[pitch]
            if self.session_start_time is not None:
                duration = timestamp - start_time
                note_timestamp = start_time - self.session_start_time
                
                completed_note = MIDINote(
                    pitch=pitch,
                    velocity=prev_velocity,
                    timestamp=note_timestamp,
                    duration=duration
                )
                self.completed_notes.append(completed_note)
        
        # Start new note
        self.active_notes[pitch] = (velocity, timestamp)
        
        return completed_note

    def _handle_note_off(self, pitch: int, velocity: int, timestamp: float) -> Optional[MIDINote]:
        """
        Handle MIDI note off event
        
        Args:
            pitch: MIDI note number
            velocity: Release velocity
            timestamp: Event timestamp
            
        Returns:
            MIDINote: Completed note object or None
        """
        if timestamp is None:
            self.logger.warning("Received None timestamp in note off handler")
            return None
            
        if pitch not in self.active_notes:
            return None
        
        # Get note start info
        start_velocity, start_time = self.active_notes[pitch]
        
        # Calculate duration and relative timestamp
        if self.session_start_time is not None:
            duration = timestamp - start_time
            note_timestamp = start_time - self.session_start_time
        else:
            duration = 0
            note_timestamp = 0
        
        # Create completed note
        completed_note = MIDINote(
            pitch=pitch,
            velocity=start_velocity,
            timestamp=note_timestamp,
            duration=duration
        )
        
        # Remove from active notes and add to completed
        del self.active_notes[pitch]
        self.completed_notes.append(completed_note)
        
        return completed_note

    def _handle_control_change(self, controller: int, value: int, channel: int) -> None:
        """Handle MIDI control change events"""
        pass  # For future implementation
    
    def _handle_program_change(self, program: int, channel: int) -> None:
        """Handle MIDI program change events"""
        pass  # For future implementation
        
    def _handle_pitch_bend(self, lsb: int, msb: int, channel: int) -> None:
        """Handle MIDI pitch bend events"""
        pass  # For future implementation

    def get_active_notes(self) -> List[int]:
        """
        Get list of currently active note pitches
        
        Returns:
            List[int]: List of active MIDI note numbers
        """
        return list(self.active_notes.keys())
    
    def get_completed_notes(self) -> List[MIDINote]:
        """Get all completed notes from current session"""
        return self.completed_notes.copy()
    
    def finalize_notes(self) -> List[MIDINote]:
        """
        Finalize any active notes and return complete note list
        
        Returns:
            List[MIDINote]: List of completed notes
        """
        current_time = time.time()
        if self.session_start_time is not None:
            session_time = current_time - self.session_start_time
        else:
            session_time = 0
        
        # Finalize any notes that are still active
        for pitch, (velocity, timestamp) in self.active_notes.items():
            if self.session_start_time is not None:
                duration = current_time - timestamp
                note_timestamp = timestamp - self.session_start_time
            else:
                duration = 0
                note_timestamp = 0
                
            note = MIDINote(
                pitch=pitch,
                velocity=velocity,
                timestamp=note_timestamp,
                duration=duration
            )
            self.completed_notes.append(note)
        
        # Clear active notes
        self.active_notes.clear()
        
        # Return all completed notes
        return self.completed_notes.copy()

    def clear_session(self) -> None:
        """Clear current session data"""
        self.active_notes.clear()
        self.completed_notes.clear()
        self.session_start_time = None
        self.logger.info("Cleared MIDI session data")
