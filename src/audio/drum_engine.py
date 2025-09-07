"""
Drum Engine

Generates drum patterns and sounds for background rhythm.
Phase 3.3 implementation - Background drummer with genre-specific patterns.
"""

import numpy as np
import threading
import time
from typing import Dict, List, Optional
from utils.logger import get_logger


class DrumSynthesizer:
    """
    Synthesizes drum sounds using procedural audio generation
    
    Generates kick, snare, and hi-hat sounds without requiring sample files.
    """
    
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.logger = get_logger()
    
    def generate_kick(self, velocity=1.0, duration=0.5):
        """Generate kick drum sound using low-frequency synthesis"""
        samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, samples)
        
        # Frequency sweep from 60Hz to 30Hz for punch
        freq_start, freq_end = 60, 30
        freq = freq_start + (freq_end - freq_start) * t / duration
        
        # Generate sine wave with frequency sweep
        wave = np.sin(2 * np.pi * freq * t)
        
        # Sharp attack, quick decay envelope
        envelope = np.exp(-t * 15) * velocity
        
        # Add some click for attack
        click = np.exp(-t * 100) * 0.3 * velocity
        
        return (wave * envelope + click).astype(np.float32)
    
    def generate_snare(self, velocity=1.0, duration=0.2):
        """Generate snare drum using noise + tone"""
        samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, samples)
        
        # White noise component
        noise = np.random.normal(0, 0.5, samples)
        
        # Tonal component around 200Hz
        tone = np.sin(2 * np.pi * 200 * t) * 0.3
        
        # Sharp attack, medium decay
        envelope = np.exp(-t * 20) * velocity
        
        # High-frequency emphasis
        high_freq = np.sin(2 * np.pi * 8000 * t) * 0.1 * np.exp(-t * 50)
        
        return ((noise + tone + high_freq) * envelope).astype(np.float32)
    
    def generate_hihat(self, velocity=1.0, duration=0.1):
        """Generate hi-hat using filtered high-frequency noise"""
        samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, samples)
        
        # High-frequency noise
        noise = np.random.normal(0, 0.3, samples)
        
        # Very sharp attack and quick decay
        envelope = np.exp(-t * 80) * velocity
        
        # High-pass filter effect (simple)
        filtered_noise = np.diff(np.concatenate([[0], noise]))
        if len(filtered_noise) < len(envelope):
            filtered_noise = np.concatenate([filtered_noise, [0]])
        
        return (filtered_noise * envelope).astype(np.float32)


class DrumPattern:
    """Represents a drum pattern for a specific genre"""
    
    def __init__(self, name: str, kick_pattern: List[float], 
                 snare_pattern: List[float], hihat_pattern: List[float]):
        self.name = name
        self.kick_pattern = kick_pattern    # Beat positions (1.0, 1.5, 2.0, etc.)
        self.snare_pattern = snare_pattern
        self.hihat_pattern = hihat_pattern
        self.beats_per_measure = 4  # 4/4 time signature


class DrumEngine:
    """
    Background drummer that plays genre-specific patterns
    
    Integrates with the existing AudioEngine to provide rhythmic accompaniment
    during practice sessions.
    """
    
    def __init__(self, audio_engine, sample_rate=44100):
        self.audio_engine = audio_engine
        self.sample_rate = sample_rate
        self.synthesizer = DrumSynthesizer(sample_rate)
        self.logger = get_logger()
        
        # Playback state
        self.bpm = 100  # Default BPM
        self.is_playing = False
        self.current_genre = "modal_jazz"
        self.playback_thread = None
        self.stop_event = threading.Event()
        
        # Synchronized timing
        self.session_start_time = None  # Shared timing reference
        
        # Audio mixing buffers
        self.drum_buffer = []  # Queue of drum audio samples to be mixed
        self.buffer_lock = threading.Lock()
        
        # Track last beat triggers to avoid duplicates
        self.last_triggered = {'kick': 0, 'snare': 0, 'hihat': 0}
        
        # Define drum patterns for each genre
        self.patterns = {
            'modal_jazz': DrumPattern(
                'Modal Jazz',
                kick_pattern=[1.0, 3.0],  # Beats 1 and 3
                snare_pattern=[2.0, 4.0],  # Beats 2 and 4
                hihat_pattern=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]  # Swing eighth notes
            ),
            'blues': DrumPattern(
                'Blues',
                kick_pattern=[1.0, 3.0],
                snare_pattern=[2.0, 4.0],
                hihat_pattern=[1.0, 2.0, 3.0, 4.0]  # Quarter notes
            ),
            'folk': DrumPattern(
                'Folk',
                kick_pattern=[1.0, 3.0],
                snare_pattern=[2.0, 4.0],
                hihat_pattern=[1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5]  # Light eighth notes
            )
        }
        
        self.logger.info("Drum Engine initialized with synthesized drum sounds")
    
    def set_bpm(self, bpm: int):
        """Set the tempo for drum playback"""
        self.bpm = max(60, min(180, bpm))  # Clamp to reasonable range
        self.logger.info(f"Drum BPM set to {self.bpm}")
    
    def set_genre(self, genre: str):
        """Change drum pattern based on musical genre"""
        if genre in self.patterns:
            self.current_genre = genre
            self.logger.info(f"Drum pattern changed to {genre}")
        else:
            self.logger.warning(f"Unknown genre: {genre}, keeping {self.current_genre}")
    
    def start_drumming(self, session_start_time=None):
        """Begin drum loop playback with optional synchronized timing"""
        if self.is_playing:
            return
        
        self.is_playing = True
        self.stop_event.clear()
        
        # Store synchronized timing reference if provided
        self.session_start_time = session_start_time
        
        self.playback_thread = threading.Thread(target=self._drum_loop, daemon=True)
        self.playback_thread.start()
        self.logger.info(f"Started drumming: {self.current_genre} at {self.bpm} BPM")
        if session_start_time:
            self.logger.info(f"Using synchronized timing reference: {session_start_time}")
    
    def stop_drumming(self):
        """Stop drum loop playback"""
        if not self.is_playing:
            return
        
        self.is_playing = False
        self.stop_event.set()
        if self.playback_thread:
            self.playback_thread.join(timeout=1.0)
        self.logger.info("Stopped drumming")
    
    def _drum_loop(self):
        """Main drum loop - runs in separate thread"""
        pattern = self.patterns[self.current_genre]
        beat_duration = 60.0 / self.bpm  # Duration of one beat in seconds
        measure_duration = beat_duration * 4  # 4/4 time
        
        # Use synchronized timing if available, otherwise use current time
        start_time = self.session_start_time if self.session_start_time else time.time()
        
        # Initialize beat boundary detection
        previous_beat_position = None
        
        while not self.stop_event.is_set():
            current_time = time.time()
            elapsed = current_time - start_time
            
            # Calculate position within current measure
            measure_position = (elapsed % measure_duration) / beat_duration + 1.0
            
            # Check if we should trigger any drum sounds using boundary detection
            self._check_and_trigger_drums_boundary(measure_position, previous_beat_position, pattern)
            
            # Update previous position for next iteration
            previous_beat_position = measure_position
            
            # Sleep briefly to avoid excessive CPU usage
            time.sleep(0.01)  # 10ms resolution
    
    def _check_and_trigger_drums_boundary(self, current_beat: float, previous_beat: float, pattern: DrumPattern):
        """Check if any drums should be triggered using beat boundary detection"""
        if previous_beat is None:
            return  # Skip first iteration since we need previous position
        
        current_time = time.time()
        
        # Helper function to detect if we crossed a beat boundary
        def crossed_beat(target_beat: float) -> bool:
            # Handle wraparound: if we went from ~5.0 back to ~1.0
            if previous_beat > 4.5 and current_beat < 1.5:
                # Wraparound case: check if target is 1.0 or if we crossed it before wrapping
                return (target_beat == 1.0) or (target_beat > previous_beat)
            else:
                # Normal case: check if we crossed the target beat
                return previous_beat < target_beat <= current_beat
        
        # Check kick drum
        for kick_beat in pattern.kick_pattern:
            if crossed_beat(kick_beat):
                if current_time - self.last_triggered['kick'] > 0.2:  # Prevent rapid re-triggers
                    self._trigger_kick()
                    self.last_triggered['kick'] = current_time
        
        # Check snare drum  
        for snare_beat in pattern.snare_pattern:
            if crossed_beat(snare_beat):
                if current_time - self.last_triggered['snare'] > 0.2:
                    self._trigger_snare()
                    self.last_triggered['snare'] = current_time
        
        # Check hi-hat
        for hihat_beat in pattern.hihat_pattern:
            if crossed_beat(hihat_beat):
                if current_time - self.last_triggered['hihat'] > 0.15:  # Hi-hat can be more frequent
                    self._trigger_hihat()
                    self.last_triggered['hihat'] = current_time

    def _check_and_trigger_drums(self, beat_position: float, pattern: DrumPattern):
        """Check if any drums should be triggered at current beat position"""
        tolerance = 0.1  # 100ms tolerance for timing
        current_time = time.time()
        
        # Check kick drum
        for kick_beat in pattern.kick_pattern:
            if abs(beat_position - kick_beat) < tolerance:
                if current_time - self.last_triggered['kick'] > 0.2:  # Prevent rapid re-triggers
                    self._trigger_kick()
                    self.last_triggered['kick'] = current_time
        
        # Check snare drum  
        for snare_beat in pattern.snare_pattern:
            if abs(beat_position - snare_beat) < tolerance:
                if current_time - self.last_triggered['snare'] > 0.2:
                    self._trigger_snare()
                    self.last_triggered['snare'] = current_time
        
        # Check hi-hat
        for hihat_beat in pattern.hihat_pattern:
            if abs(beat_position - hihat_beat) < tolerance:
                if current_time - self.last_triggered['hihat'] > 0.15:  # Hi-hat can be more frequent
                    self._trigger_hihat()
                    self.last_triggered['hihat'] = current_time
    
    def _trigger_kick(self):
        """Trigger kick drum sound"""
        kick_audio = self.synthesizer.generate_kick(velocity=0.15)  # Further reduced to 2/3 of previous volume (0.23 → 0.15)
        self._play_drum_audio(kick_audio)
        self.logger.debug("🥁 Triggered KICK drum")
    
    def _trigger_snare(self):
        """Trigger snare drum sound"""
        snare_audio = self.synthesizer.generate_snare(velocity=0.14)  # Further reduced to 2/3 of previous volume (0.21 → 0.14)
        self._play_drum_audio(snare_audio)
        self.logger.debug("🥁 Triggered SNARE drum")
    
    def _trigger_hihat(self):
        """Trigger hi-hat sound"""
        hihat_audio = self.synthesizer.generate_hihat(velocity=0.08)  # Further reduced to 2/3 of previous volume (0.12 → 0.08)
        self._play_drum_audio(hihat_audio)
        self.logger.debug("🥁 Triggered HI-HAT")
    
    def _play_drum_audio(self, audio_data):
        """Send drum audio to the audio buffer for mixing"""
        with self.buffer_lock:
            self.drum_buffer.append(audio_data)
            # Keep buffer from growing too large
            if len(self.drum_buffer) > 10:
                self.drum_buffer.pop(0)
    
    def get_drum_audio(self, num_samples):
        """Get drum audio for mixing with main audio stream"""
        with self.buffer_lock:
            if not self.drum_buffer:
                return np.zeros(num_samples, dtype=np.float32)
            
            # Mix all drum samples in buffer
            mixed_audio = np.zeros(num_samples, dtype=np.float32)
            
            # Process each drum sample in the buffer
            remaining_buffer = []
            for drum_sample in self.drum_buffer:
                if len(drum_sample) <= num_samples:
                    # Entire sample fits in this audio chunk
                    mixed_audio[:len(drum_sample)] += drum_sample
                else:
                    # Sample is longer than this chunk
                    mixed_audio += drum_sample[:num_samples]
                    # Keep the remaining part for next time
                    remaining_buffer.append(drum_sample[num_samples:])
            
            # Update buffer with remaining samples
            self.drum_buffer = remaining_buffer
            
            # Limit volume to prevent clipping
            mixed_audio = np.clip(mixed_audio, -1.0, 1.0)
            
            return mixed_audio
