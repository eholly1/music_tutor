"""
Audio Engine

Integrates synthesizer and player for real-time audio output.
Phase 3.1 implementation with Phase 3.3 drum engine integration.
"""

import time
import numpy as np
from typing import Optional
from .synthesizer import AudioSynthesizer
from .player import AudioPlayer
from .drum_engine import DrumEngine
from utils.logger import get_logger


class AudioEngine:
    """
    High-level audio engine that coordinates synthesis and playback
    
    Features:
    - Real-time MIDI-to-audio conversion
    - Low-latency audio streaming
    - Simple interface for note triggering
    - Automatic audio device management
    """
    
    def __init__(self, sample_rate=44100, buffer_size=512):
        """
        Initialize audio engine
        
        Args:
            sample_rate (int): Audio sample rate in Hz
            buffer_size (int): Audio buffer size for latency control
        """
        self.logger = get_logger()
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        
        # Create synthesizer and player
        self.synthesizer = AudioSynthesizer(sample_rate, buffer_size)
        self.player = AudioPlayer(sample_rate, buffer_size)
        
        # Create drum engine
        self.drum_engine = DrumEngine(self, sample_rate)
        
        # Set up audio callback
        self.player.set_audio_callback(self._mixed_audio_callback)
        
        # Engine state
        self.is_running = False
        
        self.logger.info(f"Audio Engine initialized - {sample_rate}Hz, buffer={buffer_size}")
    
    def _mixed_audio_callback(self, frames):
        """Audio callback that mixes synthesizer and drum audio"""
        # Get synthesizer audio
        synth_audio = self.synthesizer.generate_audio_buffer(frames)
        
        # Get drum audio if drums are playing
        if self.drum_engine.is_playing:
            drum_audio = self.drum_engine.get_drum_audio(frames)
            # Mix synthesizer and drum audio
            mixed_audio = synth_audio + drum_audio * 0.6  # Reduce drum volume slightly
            # Prevent clipping
            mixed_audio = np.clip(mixed_audio, -1.0, 1.0)
            return mixed_audio
        else:
            return synth_audio
    
    def start(self):
        """Start the audio engine"""
        try:
            if self.is_running:
                self.logger.warning("Audio engine already running")
                return
            
            # Start audio streaming
            self.player.start_stream()
            self.is_running = True
            
            self.logger.info("Audio Engine started")
            
        except Exception as e:
            self.logger.error(f"Failed to start audio engine: {e}")
            raise
    
    def stop(self):
        """Stop the audio engine"""
        try:
            if not self.is_running:
                return
            
            # Stop all notes and audio stream
            self.synthesizer.stop_all_notes()
            self.player.stop_stream()
            self.is_running = False
            
            self.logger.info("Audio Engine stopped")
            
        except Exception as e:
            self.logger.error(f"Failed to stop audio engine: {e}")
    
    def note_on(self, midi_note: int, velocity: int):
        """
        Trigger a note on event
        
        Args:
            midi_note (int): MIDI note number (0-127)
            velocity (int): Note velocity (0-127)
        """
        self.logger.info(f"🎶 AUDIO ENGINE note_on() called: MIDI {midi_note}, velocity {velocity}")
        
        if not self.is_running:
            self.logger.warning("❌ AUDIO ENGINE NOT RUNNING - note ignored")
            return
        
        self.synthesizer.note_on(midi_note, velocity)
    
    def note_off(self, midi_note: int):
        """
        Trigger a note off event
        
        Args:
            midi_note (int): MIDI note number (0-127)
        """
        self.logger.info(f"🎶 AUDIO ENGINE note_off() called: MIDI {midi_note}")
        
        if not self.is_running:
            self.logger.warning("❌ AUDIO ENGINE NOT RUNNING - note ignored")
            return
        
        self.synthesizer.note_off(midi_note)
    
    # Drum Engine Controls
    
    def start_drums(self, session_start_time=None):
        """Start background drum pattern with optional synchronized timing"""
        if session_start_time:
            self.drum_engine.start_drumming(session_start_time=session_start_time)
        else:
            self.drum_engine.start_drumming()
    
    def stop_drums(self):
        """Stop background drum pattern"""
        self.drum_engine.stop_drumming()
    
    def set_drum_bpm(self, bpm: int):
        """Set drum tempo"""
        self.drum_engine.set_bpm(bpm)
    
    def set_drum_genre(self, genre: str):
        """Set drum pattern genre"""
        self.drum_engine.set_genre(genre)
    
    def is_drumming(self) -> bool:
        """Check if drums are currently playing"""
        return self.drum_engine.is_playing
    
    def get_status(self) -> dict:
        """
        Get current engine status
        
        Returns:
            dict: Engine status information
        """
        return {
            'running': self.is_running,
            'active_notes': self.synthesizer.get_active_note_count(),
            'sample_rate': self.sample_rate,
            'buffer_size': self.buffer_size,
            'latency_info': self.player.get_latency_info()
        }
    
    def get_audio_devices(self):
        """Get available audio devices"""
        return self.player.get_audio_devices()
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.stop()
        except:
            pass
