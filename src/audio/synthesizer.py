"""
Audio Synthesizer

Generates audio waveforms for musical playback.
Phase 3.1 implementation with real-time synthesis.
"""

import numpy as np
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, List
from utils.logger import get_logger


@dataclass
class ActiveNote:
    """Represents a currently playing note"""
    midi_note: int
    frequency: float
    velocity: float
    start_time: float
    phase: float = 0.0
    
    
class ADSREnvelope:
    """ADSR (Attack, Decay, Sustain, Release) envelope generator"""
    
    def __init__(self, attack=0.01, decay=0.1, sustain=0.7, release=0.3):
        """
        Initialize ADSR envelope
        
        Args:
            attack (float): Attack time in seconds
            decay (float): Decay time in seconds  
            sustain (float): Sustain level (0.0-1.0)
            release (float): Release time in seconds
        """
        self.attack = attack
        self.decay = decay
        self.sustain = sustain
        self.release = release
    
    def get_amplitude(self, time_since_start: float, note_released: bool = False, 
                     time_since_release: float = 0.0) -> float:
        """
        Calculate envelope amplitude at given time
        
        Args:
            time_since_start: Time since note started
            note_released: Whether note has been released
            time_since_release: Time since note was released
            
        Returns:
            float: Amplitude multiplier (0.0-1.0)
        """
        if note_released:
            # Release phase
            if time_since_release >= self.release:
                return 0.0
            return self.sustain * (1.0 - time_since_release / self.release)
        
        if time_since_start < self.attack:
            # Attack phase
            return time_since_start / self.attack
        elif time_since_start < self.attack + self.decay:
            # Decay phase
            decay_progress = (time_since_start - self.attack) / self.decay
            return 1.0 - decay_progress * (1.0 - self.sustain)
        else:
            # Sustain phase
            return self.sustain


class AudioSynthesizer:
    """
    Real-time audio synthesis engine for generating musical sounds
    
    Features:
    - Polyphonic playback (multiple simultaneous notes)
    - ADSR envelope shaping
    - Real-time note triggering
    - Low-latency audio generation
    """
    
    def __init__(self, sample_rate=44100, buffer_size=512):
        """
        Initialize audio synthesizer
        
        Args:
            sample_rate (int): Audio sample rate in Hz
            buffer_size (int): Audio buffer size for real-time processing
        """
        self.logger = get_logger()
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        
        # Active notes dictionary (midi_note -> ActiveNote)
        self.active_notes: Dict[int, ActiveNote] = {}
        self.released_notes: Dict[int, tuple] = {}  # midi_note -> (ActiveNote, release_time)
        
        # Envelope generator
        self.envelope = ADSREnvelope()
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Audio generation state
        self.master_volume = 0.3  # Prevent clipping
        
        self.logger.info(f"Audio Synthesizer initialized - {sample_rate}Hz, buffer={buffer_size}")
    
    def midi_to_frequency(self, midi_note: int) -> float:
        """
        Convert MIDI note number to frequency in Hz
        
        Args:
            midi_note (int): MIDI note number (0-127)
            
        Returns:
            float: Frequency in Hz
        """
        # A4 (440Hz) is MIDI note 69
        return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))
    
    def note_on(self, midi_note: int, velocity: int):
        """
        Trigger a note on event
        
        Args:
            midi_note (int): MIDI note number (0-127)
            velocity (int): Note velocity (0-127)
        """
        self.logger.info(f"🎵 SYNTHESIZER note_on() called: MIDI {midi_note}, velocity {velocity}")
        
        with self.lock:
            frequency = self.midi_to_frequency(midi_note)
            velocity_float = velocity / 127.0
            
            # Remove from released notes if it was there
            if midi_note in self.released_notes:
                del self.released_notes[midi_note]
                self.logger.info(f"🗑️  REMOVED from released notes: {midi_note}")
            
            # Create new active note
            self.active_notes[midi_note] = ActiveNote(
                midi_note=midi_note,
                frequency=frequency,
                velocity=velocity_float,
                start_time=time.time(),
                phase=0.0
            )
    
    def note_off(self, midi_note: int):
        """
        Trigger a note off event
        
        Args:
            midi_note (int): MIDI note number (0-127)
        """
        self.logger.info(f"🎵 SYNTHESIZER note_off() called: MIDI {midi_note}")
        
        with self.lock:
            if midi_note in self.active_notes:
                note = self.active_notes[midi_note]
                del self.active_notes[midi_note]
                
                # Move to released notes for envelope release phase
                self.released_notes[midi_note] = (note, time.time())
                
                self.logger.info(f"✅ MOVED TO RELEASED NOTES: MIDI {midi_note}")
                self.logger.info(f"📊 ACTIVE NOTES: {len(self.active_notes)}, RELEASED NOTES: {len(self.released_notes)}")
            else:
                self.logger.warning(f"⚠️  NOTE NOT FOUND IN ACTIVE NOTES: {midi_note}")
    
    def note_off(self, midi_note: int):
        """
        Trigger a note off event
        
        Args:
            midi_note (int): MIDI note number (0-127)
        """
        with self.lock:
            if midi_note in self.active_notes:
                note = self.active_notes[midi_note]
                del self.active_notes[midi_note]
                
                # Move to released notes for envelope release phase
                self.released_notes[midi_note] = (note, time.time())
                
                self.logger.debug(f"Note OFF: MIDI {midi_note}")
    
    def generate_audio_buffer(self, num_samples: int) -> np.ndarray:
        """
        Generate audio buffer with current active notes
        
        Args:
            num_samples (int): Number of audio samples to generate
            
        Returns:
            np.ndarray: Audio samples (mono)
        """
        buffer = np.zeros(num_samples, dtype=np.float32)
        current_time = time.time()
        
        with self.lock:
            total_notes = len(self.active_notes) + len(self.released_notes)
            
            # Process active notes
            for note in list(self.active_notes.values()):
                note_buffer = self._generate_note_samples(note, num_samples, current_time)
                buffer += note_buffer
            
            # Process released notes (in release phase)
            for midi_note, (note, release_time) in list(self.released_notes.items()):
                note_buffer = self._generate_note_samples(
                    note, num_samples, current_time, release_time
                )
                buffer += note_buffer
                
                # Remove completely faded notes
                time_since_release = current_time - release_time
                if time_since_release >= self.envelope.release:
                    del self.released_notes[midi_note]
        
        # Apply master volume and clipping protection
        buffer *= self.master_volume
        buffer = np.clip(buffer, -1.0, 1.0)
        
        return buffer
    
    def _generate_note_samples(self, note: ActiveNote, num_samples: int, 
                              current_time: float, release_time: Optional[float] = None) -> np.ndarray:
        """
        Generate audio samples for a single note
        
        Args:
            note: The note to generate
            num_samples: Number of samples to generate
            current_time: Current timestamp
            release_time: Time when note was released (if any)
            
        Returns:
            np.ndarray: Audio samples for this note
        """
        samples = np.zeros(num_samples, dtype=np.float32)
        dt = 1.0 / self.sample_rate
        
        time_since_start = current_time - note.start_time
        note_released = release_time is not None
        time_since_release = (current_time - release_time) if release_time else 0.0
        
        for i in range(num_samples):
            # Calculate envelope amplitude
            sample_time_since_start = time_since_start + (i * dt)
            sample_time_since_release = time_since_release + (i * dt) if note_released else 0.0
            
            amplitude = self.envelope.get_amplitude(
                sample_time_since_start, note_released, sample_time_since_release
            )
            
            if amplitude <= 0.0:
                break
            
            # Generate sine wave sample
            sample = np.sin(note.phase) * note.velocity * amplitude
            samples[i] = sample
            
            # Update phase
            note.phase += 2.0 * np.pi * note.frequency * dt
            if note.phase >= 2.0 * np.pi:
                note.phase -= 2.0 * np.pi
        
        return samples
    
    def get_active_note_count(self) -> int:
        """Get number of currently active notes"""
        with self.lock:
            return len(self.active_notes) + len(self.released_notes)
    
    def stop_all_notes(self):
        """Stop all currently playing notes"""
        with self.lock:
            self.active_notes.clear()
            self.released_notes.clear()
            self.logger.debug("All notes stopped")
