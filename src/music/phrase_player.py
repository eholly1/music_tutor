"""
Phrase Playback Engine

Handles playing musical phrases through audio synthesis with precise timing.
Supports autonomous phrase cycling and beat-synchronized playback.
"""

import time
import threading
import random
from typing import Optional, Callable, List
from music.phrase import Phrase, MusicalNote
from music.library import PhraseLibrary
from utils.logger import get_logger


class PhrasePlayer:
    """
    Handles playback of musical phrases through audio synthesis
    
    Features:
    - Precise beat-based timing
    - Thread-safe playback scheduling
    - Integration with audio engine
    - Autonomous phrase cycling
    """
    
    def __init__(self, audio_engine):
        """
        Initialize phrase player
        
        Args:
            audio_engine: AudioEngine instance for sound synthesis
        """
        self.logger = get_logger()
        self.audio_engine = audio_engine
        self.current_phrase = None
        self.is_playing = False
        self.playback_thread = None
        self.stop_event = threading.Event()
        self.current_bpm = 120
        
        # Session timing for beat synchronization
        self.session_start_time = None
        self.beat_interval = 60.0 / 120.0  # Will be updated with actual BPM
        
        # Track active notes for proper cleanup
        self.active_notes = set()  # Set of MIDI note numbers currently playing
        self.note_off_threads = []  # List of active note-off threads
        
        # Callback for playback events
        self.playback_started_callback = None
        self.playback_finished_callback = None
        self.note_played_callback = None  # Backward compatibility
        self.note_on_callback = None
        self.note_off_callback = None
        
        self.logger.info("PhrasePlayer initialized")

    def set_session_timing(self, session_start_time, bpm):
        """
        Set session timing parameters for beat synchronization
        
        Args:
            session_start_time: When the session started (time.time())
            bpm: Beats per minute for timing calculations
        """
        self.session_start_time = session_start_time
        self.beat_interval = 60.0 / bpm
        self.current_bpm = bpm
        self.logger.debug(f"Session timing set: start_time={session_start_time:.3f}, bpm={bpm}, beat_interval={self.beat_interval:.3f}")

    def _calculate_next_downbeat(self):
        """
        Calculate when the next downbeat (beat 1) will occur
        Similar to the method in listening_manager.py
        
        Returns:
            float: Time when next downbeat occurs
        """
        if self.session_start_time is None:
            return time.time()  # If no session timing, return immediately
            
        # Constants
        BEATS_PER_MEASURE = 4
        
        # Get current time relative to session start
        current_time = time.time()
        elapsed_time = current_time - self.session_start_time
        
        # Calculate current position in beats
        current_beat_position = elapsed_time / self.beat_interval
        
        # Find current measure and beat within measure
        beats_in_current_measure = current_beat_position % BEATS_PER_MEASURE
        
        # Calculate time until next measure starts (next downbeat)
        if beats_in_current_measure < 0.001:  # Already very close to downbeat
            beats_until_next_downbeat = 0
        else:
            beats_until_next_downbeat = BEATS_PER_MEASURE - beats_in_current_measure
            
        # Convert to wall clock time
        time_until_next_downbeat = beats_until_next_downbeat * self.beat_interval
        next_downbeat_time = current_time + time_until_next_downbeat
        
        self.logger.debug(f"Next downbeat calculation: current_beat={current_beat_position:.3f}, "
                         f"beats_until_next={beats_until_next_downbeat:.3f}, "
                         f"wait_time={time_until_next_downbeat:.3f}s")
        
        return next_downbeat_time
    
    def play_phrase(self, phrase: Phrase, bpm: Optional[int] = None) -> bool:
        """
        Play a musical phrase through audio synthesis
        
        Args:
            phrase: Phrase object to play
            bpm: Override tempo (uses phrase tempo if None)
            
        Returns:
            bool: True if playback started successfully
        """
        if self.is_playing:
            self.logger.warning("Cannot start playback - already playing")
            return False
        
        if not self.audio_engine or not self.audio_engine.is_running:
            self.logger.error("Audio engine not available or not running")
            return False
        
        self.current_phrase = phrase
        self.current_bpm = bpm or phrase.tempo
        self.stop_event.clear()
        
        # Start playback in separate thread
        self.playback_thread = threading.Thread(
            target=self._playback_worker,
            name="PhrasePlayback",
            daemon=True
        )
        self.playback_thread.start()
        
        self.logger.info(f"Started phrase playback: {phrase.metadata.get('description', 'unnamed')} at {self.current_bpm} BPM")
        return True
    
    def stop_playback(self):
        """Stop current phrase playback"""
        if self.is_playing:
            self.stop_event.set()
            
            # Immediately stop all active notes
            for pitch in list(self.active_notes):
                self.audio_engine.note_off(pitch)
            self.active_notes.clear()
            
            # Clear note-off threads (they're daemon threads so they'll terminate)
            self.note_off_threads.clear()
            
            self.logger.info("Stopping phrase playback")
    
    def _playback_worker(self):
        """Worker thread for phrase playback with downbeat synchronization"""
        try:
            self.is_playing = True
            
            # Wait for next downbeat before starting playback
            if self.session_start_time is not None:
                next_downbeat = self._calculate_next_downbeat()
                current_time = time.time()
                wait_time = next_downbeat - current_time
                
                if wait_time > 0:
                    self.logger.info(f"Waiting {wait_time:.3f}s for next downbeat...")
                    # Use stop_event.wait() so we can be interrupted
                    if self.stop_event.wait(wait_time):
                        self.logger.info("Playback interrupted while waiting for downbeat")
                        return
                else:
                    self.logger.debug("Already at or past downbeat, starting immediately")
            
            # Check if we should still proceed after potential wait
            if self.stop_event.is_set():
                self.logger.info("Playback cancelled before starting")
                return
            
            # Notify playback started
            if self.playback_started_callback:
                self.playback_started_callback(self.current_phrase)
            
            # Calculate timing
            beat_duration = 60.0 / self.current_bpm  # seconds per beat
            start_time = time.time()
            
            # Sort notes by start time for proper scheduling
            sorted_notes = sorted(self.current_phrase.notes, key=lambda n: n.start_time)
            
            # Play each note at the correct time
            for note in sorted_notes:
                if self.stop_event.is_set():
                    break
                
                # Calculate when this note should play
                note_time = start_time + (note.start_time * beat_duration)
                current_time = time.time()
                
                # Wait until it's time to play this note
                if note_time > current_time:
                    wait_time = note_time - current_time
                    if self.stop_event.wait(wait_time):
                        break  # Stop event was set during wait
                
                # Play the note
                self._play_note(note)
            
            # Wait for the phrase to complete
            if not self.stop_event.is_set():
                phrase_duration = self.current_phrase.get_duration_seconds(self.current_bpm)
                end_time = start_time + phrase_duration
                remaining_time = end_time - time.time()
                
                if remaining_time > 0:
                    self.stop_event.wait(remaining_time)
            
        except Exception as e:
            self.logger.error(f"Error in phrase playback: {e}")
        finally:
            self.is_playing = False
            
            # Clean up any remaining active notes and threads
            for pitch in list(self.active_notes):
                self.audio_engine.note_off(pitch)
            self.active_notes.clear()
            self.note_off_threads.clear()
            
            # Notify playback finished
            self.logger.info(f"🎯 PHRASE PLAYER: Playback finished, callback: {self.playback_finished_callback}")
            if self.playback_finished_callback:
                self.logger.info(f"🎯 PHRASE PLAYER: Calling playback_finished_callback for phrase: {self.current_phrase.name}")
                self.playback_finished_callback(self.current_phrase)
            else:
                self.logger.info("🎯 PHRASE PLAYER: No playback_finished_callback set")
            
            self.logger.debug("Phrase playback completed")
    
    def _play_note(self, note: MusicalNote):
        """
        Play a single note through the audio engine
        
        Args:
            note: MusicalNote to play
        """
        try:
            # Calculate note duration in seconds
            note_duration_seconds = note.duration * (60.0 / self.current_bpm)
            
            # Trigger note on
            self.audio_engine.note_on(note.pitch, note.velocity)
            
            # Track this note as active
            self.active_notes.add(note.pitch)
            
            # Notify note on callbacks
            if self.note_on_callback:
                self.note_on_callback(note)
            
            # Backward compatibility - also call the old note callback
            if self.note_played_callback:
                self.note_played_callback(note)
            
            # Schedule note off (simplified - immediate scheduling)
            # In a more sophisticated implementation, this could use the audio engine's scheduler
            def note_off_delayed():
                time.sleep(note_duration_seconds)
                if not self.stop_event.is_set():
                    self.audio_engine.note_off(note.pitch)
                # Remove from active notes when done
                self.active_notes.discard(note.pitch)
                
                # Notify note off callback
                if self.note_off_callback:
                    self.note_off_callback(note)
            
            note_off_thread = threading.Thread(target=note_off_delayed, daemon=True)
            note_off_thread.start()
            
            # Track the note-off thread
            self.note_off_threads.append(note_off_thread)
            
            self.logger.debug(f"Played note: MIDI {note.pitch}, vel {note.velocity}, dur {note_duration_seconds:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error playing note {note.pitch}: {e}")
    
    def set_playback_callbacks(self, 
                              started_callback: Optional[Callable] = None,
                              finished_callback: Optional[Callable] = None,
                              note_callback: Optional[Callable] = None,
                              note_on_callback: Optional[Callable] = None,
                              note_off_callback: Optional[Callable] = None):
        """
        Set callbacks for playback events
        
        Args:
            started_callback: Called when playback starts (phrase)
            finished_callback: Called when playback finishes (phrase)  
            note_callback: Called when each note is played (note) - DEPRECATED, use note_on_callback
            note_on_callback: Called when a note starts playing (note)
            note_off_callback: Called when a note stops playing (note)
        """
        self.playback_started_callback = started_callback
        self.playback_finished_callback = finished_callback
        self.note_played_callback = note_callback  # Keep for backward compatibility
        self.note_on_callback = note_on_callback
        self.note_off_callback = note_off_callback


class AutonomousPhrasePlayer:
    """
    Autonomous phrase player that cycles through phrases automatically
    
    Features:
    - Random phrase selection from library
    - Configurable timing between phrases
    - Filtering by style, difficulty, bars
    - Continuous playback loop
    """
    
    def __init__(self, phrase_library: PhraseLibrary, phrase_player: PhrasePlayer):
        """
        Initialize autonomous phrase player
        
        Args:
            phrase_library: PhraseLibrary for phrase selection
            phrase_player: PhrasePlayer for actual playback
        """
        self.logger = get_logger()
        self.phrase_library = phrase_library
        self.phrase_player = phrase_player
        self.is_running = False
        self.autonomous_thread = None
        self.stop_event = threading.Event()
        
        # Configuration
        self.style_filter = None
        self.difficulty_filter = None
        self.bars_filter = None
        self.pause_between_phrases = 2.0  # seconds
        self.override_bpm = None
        
        # Statistics
        self.phrases_played = 0
        self.session_start_time = None
        
        # Set up phrase player callbacks
        self.phrase_player.set_playback_callbacks(
            started_callback=self._on_phrase_started,
            finished_callback=self._on_phrase_finished
        )
        
        self.logger.info("AutonomousPhrasePlayer initialized")
    
    def start_autonomous_playback(self, 
                                 style: Optional[str] = None,
                                 difficulty: Optional[int] = None,
                                 bars: Optional[int] = None,
                                 bpm_override: Optional[int] = None):
        """
        Start autonomous phrase playback
        
        Args:
            style: Filter phrases by style
            difficulty: Filter phrases by difficulty
            bars: Filter phrases by bar count
            bpm_override: Override phrase tempos with this BPM
        """
        if self.is_running:
            self.logger.warning("Autonomous playback already running")
            return False
        
        # Set filters
        self.style_filter = style
        self.difficulty_filter = difficulty
        self.bars_filter = bars
        self.override_bpm = bpm_override
        
        # Reset statistics
        self.phrases_played = 0
        self.session_start_time = time.time()
        
        # Start autonomous thread
        self.stop_event.clear()
        self.autonomous_thread = threading.Thread(
            target=self._autonomous_worker,
            name="AutonomousPlayback",
            daemon=True
        )
        self.autonomous_thread.start()
        
        self.logger.info(f"Started autonomous playback: style={style}, difficulty={difficulty}, bars={bars}")
        return True
    
    def stop_autonomous_playback(self):
        """Stop autonomous phrase playback"""
        if self.is_running:
            self.stop_event.set()
            self.phrase_player.stop_playback()
            self.logger.info("Stopping autonomous playback")
    
    def _autonomous_worker(self):
        """Worker thread for autonomous playback"""
        try:
            self.is_running = True
            self.logger.info("Autonomous playback started")
            
            while not self.stop_event.is_set():
                # Get next phrase
                phrase = self._get_next_phrase()
                
                if phrase is None:
                    self.logger.warning("No phrases available for playback")
                    break
                
                # Play the phrase
                bpm = self.override_bpm or phrase.tempo
                success = self.phrase_player.play_phrase(phrase, bpm)
                
                if not success:
                    self.logger.error("Failed to start phrase playback")
                    break
                
                # Wait for playback to complete
                while self.phrase_player.is_playing and not self.stop_event.is_set():
                    time.sleep(0.1)
                
                if self.stop_event.is_set():
                    break
                
                # Pause between phrases
                if self.pause_between_phrases > 0:
                    self.stop_event.wait(self.pause_between_phrases)
            
        except Exception as e:
            self.logger.error(f"Error in autonomous playback: {e}")
        finally:
            self.is_running = False
            self.logger.info(f"Autonomous playback stopped. Played {self.phrases_played} phrases.")
    
    def _get_next_phrase(self) -> Optional[Phrase]:
        """
        Get the next phrase for playback
        
        Returns:
            Phrase object or None if no phrases available
        """
        try:
            # Get filtered phrases
            phrases = self.phrase_library.filter_phrases(
                style=self.style_filter,
                difficulty=self.difficulty_filter,
                bars=self.bars_filter
            )
            
            if not phrases:
                return None
            
            # Select random phrase
            return random.choice(phrases)
            
        except Exception as e:
            self.logger.error(f"Error getting next phrase: {e}")
            return None
    
    def _on_phrase_started(self, phrase: Phrase):
        """Callback when phrase playback starts"""
        self.logger.info(f"Playing phrase: {phrase.metadata.get('description', 'unnamed')} "
                        f"(difficulty {phrase.difficulty}, {phrase.bars} bars)")
    
    def _on_phrase_finished(self, phrase: Phrase):
        """Callback when phrase playback finishes"""
        self.phrases_played += 1
        self.logger.debug(f"Finished phrase {self.phrases_played}: {phrase.metadata.get('description', 'unnamed')}")
    
    def get_playback_stats(self) -> dict:
        """
        Get statistics about autonomous playback
        
        Returns:
            Dictionary with playback statistics
        """
        if self.session_start_time:
            session_duration = time.time() - self.session_start_time
        else:
            session_duration = 0
        
        return {
            'is_running': self.is_running,
            'phrases_played': self.phrases_played,
            'session_duration': session_duration,
            'current_filters': {
                'style': self.style_filter,
                'difficulty': self.difficulty_filter,
                'bars': self.bars_filter,
                'bpm_override': self.override_bpm
            },
            'pause_between_phrases': self.pause_between_phrases
        }
    
    def set_pause_duration(self, seconds: float):
        """
        Set pause duration between phrases
        
        Args:
            seconds: Pause duration in seconds
        """
        self.pause_between_phrases = max(0.0, seconds)
        self.logger.info(f"Set pause between phrases to {self.pause_between_phrases}s")


# Utility functions for testing and development

def create_test_phrase_player(library_path: str = "data/phrases") -> tuple:
    """
    Create a phrase player setup for testing
    
    Args:
        library_path: Path to phrase library
        
    Returns:
        Tuple of (phrase_library, phrase_player, autonomous_player)
        Note: Requires audio_engine to be provided separately
    """
    phrase_library = PhraseLibrary(library_path)
    phrase_library.load_phrase_data()
    
    # Note: audio_engine needs to be provided by caller
    # phrase_player = PhrasePlayer(audio_engine)
    # autonomous_player = AutonomousPhrasePlayer(phrase_library, phrase_player)
    
    return phrase_library  # Return library for now
