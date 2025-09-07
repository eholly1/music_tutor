#!/usr/bin/env python3
"""
Phrase Listening Manager - Phase 4.4

Manages the state machine for call-and-response practice sessions.
Coordinates between playback and listening phases, detecting user input
and managing phrase timing expectations.
"""

import time
import threading
import os
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass

from .phrase import Phrase, MusicalNote
from .phrase_player import PhrasePlayer, AutonomousPhrasePlayer
from .library import PhraseLibrary
from evaluation.claude_evaluator import ClaudeEvaluator, ClaudeEvaluation
from utils.logger import get_logger


class SessionState(Enum):
    """States for call-and-response practice session"""
    IDLE = "idle"
    PLAYBACK = "playback"
    LISTENING = "listening"
    RECORDING_RESPONSE = "recording_response"
    FEEDBACK = "feedback"


@dataclass
class ListeningConfig:
    """Configuration for listening behavior"""
    input_timeout: float = 10.0  # Max seconds to wait for user input
    response_measures: int = 1   # Expected measures in user response
    bpm: int = 120              # Beats per minute for timing
    
    def get_response_duration(self) -> float:
        """Calculate expected response duration in seconds"""
        beats_per_measure = 4  # Assuming 4/4 time
        total_beats = self.response_measures * beats_per_measure
        return (total_beats * 60.0) / self.bpm


@dataclass
class SessionEvent:
    """Event data for session state changes"""
    event_type: str
    timestamp: float
    state: SessionState
    data: Optional[Dict[str, Any]] = None


class PhraseListeningManager:
    """
    Manages call-and-response practice sessions with state-based coordination.
    
    Coordinates between:
    - Playback phase: Bot plays phrase from library
    - Listening phase: Waits for user input and records response
    """
    
    def __init__(self, 
                 phrase_library: PhraseLibrary,
                 phrase_player: PhrasePlayer,
                 autonomous_player: AutonomousPhrasePlayer,
                 claude_api_key: Optional[str] = None):
        self.library = phrase_library
        self.phrase_player = phrase_player
        self.autonomous_player = autonomous_player
        self.logger = get_logger()
        
        # Claude AI evaluator
        self.claude_evaluator = ClaudeEvaluator(api_key=claude_api_key, session_logger=self._write_to_session_log)
        if self.claude_evaluator.is_available():
            self.logger.info("Claude AI evaluator initialized successfully")
        else:
            self.logger.warning("Claude AI evaluator not available - using fallback evaluation")
        
        # Session state
        self.state = SessionState.IDLE
        self.config = ListeningConfig()
        self.session_active = False
        
        # Timing and control
        self._state_lock = threading.Lock()
        self._listening_thread: Optional[threading.Thread] = None
        self._stop_listening = threading.Event()
        
        # Beat-aligned timing (Phase 4.4 fix)
        self.session_start_time: Optional[float] = None
        self.beat_interval: float = 60.0 / 120.0  # Default to 120 BPM, will be updated
        
        # MIDI input tracking
        self._midi_notes_playing = set()
        self._user_input_detected = False
        self._response_start_time: Optional[float] = None
        
        # MIDI recording for student response analysis
        self._recording_active = False
        self._recorded_midi_events: List[Dict[str, Any]] = []
        self._active_note_starts: Dict[int, float] = {}  # Track note-on times for duration calculation
        
        # Session tracking
        self.current_phrase: Optional[Phrase] = None
        self.phrases_completed = 0
        self.session_start_time: Optional[float] = None
        self._last_student_phrase: Optional[Phrase] = None  # Store for Claude evaluation
        
        # Store initial session parameters for consistent phrase selection
        self._initial_difficulty: Optional[int] = None
        self._initial_style: str = 'modal_jazz'  # Default style
        
        # Phrase repetition tracking for Claude context
        self._phrase_attempt_history: Dict[str, List[str]] = {}  # phrase_id -> list of grades
        self._current_phrase_attempts = 0
        self._last_recommendation: Optional[str] = None  # Store last Claude recommendation
        
        # Session logging
        self._session_log_file: Optional[str] = None
        self._session_log_path: Optional[Path] = None
        
        # Event callbacks
        self.event_callbacks: Dict[str, Callable[[SessionEvent], None]] = {}
        
        # Setup phrase player callbacks for the autonomous player's internal phrase player
        # We'll intercept the callbacks and add our own logic
        self._original_started_callback = None
        self._original_finished_callback = None
        self._setup_phrase_player_callbacks()
    
    def _setup_phrase_player_callbacks(self) -> None:
        """Setup callbacks to intercept phrase playback events"""
        # IMPORTANT: Use the autonomous player's phrase player, not our direct phrase player
        # because the autonomous player is what actually plays the phrases
        actual_phrase_player = self.autonomous_player.phrase_player
        
        # Store original callbacks if they exist
        self._original_started_callback = actual_phrase_player.playback_started_callback
        self._original_finished_callback = actual_phrase_player.playback_finished_callback
        
        self.logger.info(f"🎯 SETTING UP CALLBACKS - Original started: {self._original_started_callback}, finished: {self._original_finished_callback}")
        
        # Set our intercepting callbacks on the actual phrase player that will be used
        actual_phrase_player.set_playback_callbacks(
            started_callback=self._intercept_phrase_started,
            finished_callback=self._intercept_phrase_finished
        )
        
        self.logger.info(f"🎯 CALLBACKS SET - New started: {actual_phrase_player.playback_started_callback}, finished: {actual_phrase_player.playback_finished_callback}")
    
    def _intercept_phrase_started(self, phrase: Phrase) -> None:
        """Intercept phrase started event and add our logic"""
        self.logger.info(f"🎯 INTERCEPTED PHRASE STARTED: {phrase.name}")
        # Call original callback if it exists
        if self._original_started_callback:
            self._original_started_callback(phrase)
        
        # Add our listening manager logic
        self._on_phrase_started(phrase, self.config.bpm)
    
    def _intercept_phrase_finished(self, phrase: Phrase) -> None:
        """Intercept phrase finished event and add our logic"""
        self.logger.info(f"🎯 INTERCEPTED PHRASE FINISHED: {phrase.name}")
        # Call original callback if it exists
        if self._original_finished_callback:
            self._original_finished_callback(phrase)
        
        # Add our listening manager logic
        self._on_phrase_finished(phrase)
    
    def set_listening_config(self, config: ListeningConfig) -> None:
        """Update listening configuration"""
        with self._state_lock:
            self.config = config
            # Update beat interval when BPM changes
            self.beat_interval = 60.0 / config.bpm
    
    def set_session_timing(self, session_start_time: float, bpm: int) -> None:
        """Set synchronized session timing from piano roll"""
        with self._state_lock:
            self.session_start_time = session_start_time
            self.beat_interval = 60.0 / bpm
            self.config.bpm = bpm  # Keep config in sync
    
    def add_event_callback(self, event_type: str, callback: Callable[[SessionEvent], None]) -> None:
        """Add callback for session events"""
        self.event_callbacks[event_type] = callback
    
    def remove_event_callback(self, event_type: str) -> None:
        """Remove event callback"""
        self.event_callbacks.pop(event_type, None)
    
    def _emit_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Emit session event to callbacks"""
        event = SessionEvent(
            event_type=event_type,
            timestamp=time.time(),
            state=self.state,
            data=data or {}
        )
        
        callback = self.event_callbacks.get(event_type)
        if callback:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event callback for {event_type}: {e}")
    
    def _create_session_log_file(self) -> None:
        """Create a new session log file with timestamp"""
        try:
            # Create logs directory if it doesn't exist
            project_root = Path(__file__).parent.parent.parent  # Go up to project root
            logs_dir = project_root / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            # Create timestamped filename
            timestamp = datetime.now().strftime("%Y%m%d_%H:%M:%S")
            filename = f"session_{timestamp}.txt"
            self._session_log_path = logs_dir / filename
            
            # Create the file and write session header
            with open(self._session_log_path, 'w', encoding='utf-8') as f:
                f.write(f"Music Trainer Session Log\n")
                f.write(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"=" * 80 + "\n\n")
            
            self.logger.info(f"Created session log file: {self._session_log_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to create session log file: {e}")
            self._session_log_path = None
    
    def _write_to_session_log(self, content: str) -> None:
        """Write content to the session log file"""
        if not self._session_log_path:
            return
            
        try:
            with open(self._session_log_path, 'a', encoding='utf-8') as f:
                f.write(content + "\n")
        except Exception as e:
            self.logger.error(f"Failed to write to session log: {e}")
    
    def _close_session_log(self) -> None:
        """Close the session log file with session summary"""
        if not self._session_log_path:
            return
            
        try:
            session_duration = time.time() - (self.session_start_time or 0)
            with open(self._session_log_path, 'a', encoding='utf-8') as f:
                f.write(f"\n" + "=" * 80 + "\n")
                f.write(f"Session ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Duration: {session_duration:.1f} seconds\n")
                f.write(f"Phrases completed: {self.phrases_completed}\n")
                f.write("=" * 80 + "\n")
            
            self.logger.info(f"Closed session log: {self._session_log_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to close session log: {e}")
        finally:
            self._session_log_path = None
    
    def start_session(self, 
                     style: str = 'modal_jazz',
                     difficulty: int = 1,
                     bpm: Optional[int] = None) -> bool:
        """
        Start a call-and-response practice session.
        
        Args:
            style: Musical style to practice
            difficulty: Difficulty level (1-3)
            bpm: Beats per minute (uses config default if None)
            
        Returns:
            True if session started successfully
        """
        with self._state_lock:
            if self.session_active:
                return False
            
            # Update config if BPM provided
            if bpm is not None:
                self.config.bpm = bpm
            
            # CREATE SESSION LOG FILE
            self._create_session_log_file()
            
            # Reset session state
            self.session_active = True
            self.phrases_completed = 0
            # Don't set session_start_time here - use the one from piano roll if available
            if not self.session_start_time:
                self.session_start_time = time.time()  # Fallback if no timing provided
            self._user_input_detected = False
            self._response_start_time = None
            self._midi_notes_playing.clear()
            
            # Store initial session parameters for phrase selection
            self._initial_difficulty = difficulty
            self._initial_style = style
            
            # Configure autonomous player
            self.autonomous_player.set_pause_duration(0.1)  # Minimal pause since we handle timing
            
            # Start in playback state
            self._change_state(SessionState.PLAYBACK)
            
            # Note: Removed initial downbeat waiting to start phrases immediately
            
            # Start autonomous playback
            success = self.autonomous_player.start_autonomous_playback(
                style=style,
                difficulty=difficulty,
                bpm_override=self.config.bpm
            )
            
            if success:
                self._emit_event('session_started', {
                    'style': style,
                    'difficulty': difficulty,
                    'bpm': self.config.bpm
                })
                return True
            else:
                self.session_active = False
                self._change_state(SessionState.IDLE)
                return False
    
    def stop_session(self) -> None:
        """Stop the current practice session"""
        with self._state_lock:
            if not self.session_active:
                return
            
            # Stop autonomous playback
            self.autonomous_player.stop_autonomous_playback()
            
            # Stop listening thread
            self._stop_listening.set()
            
            # Reset state
            self.session_active = False
            self._change_state(SessionState.IDLE)
            
            # Calculate session stats
            session_duration = time.time() - (self.session_start_time or 0)
            
            # CLOSE SESSION LOG FILE
            self._close_session_log()
            
            self._emit_event('session_stopped', {
                'phrases_completed': self.phrases_completed,
                'session_duration': session_duration
            })
        
        # Wait for listening thread to finish
        if self._listening_thread and self._listening_thread.is_alive():
            self._listening_thread.join(timeout=1.0)
    
    def _change_state(self, new_state: SessionState) -> None:
        """Change session state and handle state-specific logic"""
        old_state = self.state
        self.state = new_state
        
        self.logger.info(f"State transition: {old_state.value} → {new_state.value}")
        
        # Handle state entry logic
        if new_state == SessionState.PLAYBACK:
            self._enter_playback_state()
        elif new_state == SessionState.LISTENING:
            self._enter_listening_state()
        elif new_state == SessionState.RECORDING_RESPONSE:
            self._enter_recording_state()
        elif new_state == SessionState.FEEDBACK:
            self._enter_feedback_state()
        elif new_state == SessionState.IDLE:
            self._enter_idle_state()
        
        self._emit_event('state_changed', {
            'old_state': old_state.value,
            'new_state': new_state.value
        })
    
    def _enter_playback_state(self) -> None:
        """Enter PLAYBACK state - play current phrase once"""
        if not self.session_active:
            return
            
        self.logger.info("🎯 ENTERING PLAYBACK STATE")
        
        # Handle Claude recommendations for phrase selection
        if self._last_recommendation:
            if self._last_recommendation in ['SIMPLIFY', 'COMPLEXIFY', 'CURRENT_COMPLEXITY_NEW_PHRASE']:
                # Clear current phrase to force selection of a new one
                self.current_phrase = None
                self.logger.info(f"Clearing current phrase due to recommendation: {self._last_recommendation}")
            elif self._last_recommendation == 'REPEAT':
                # Keep current phrase for repetition
                self.logger.info(f"Keeping current phrase due to recommendation: {self._last_recommendation}")
        
        # Get a phrase to play if we don't have one
        if not self.current_phrase:
            # Use initial difficulty and style for phrase selection
            target_difficulty = self._initial_difficulty or 1  # Default to difficulty 1
            target_style = self._initial_style or 'modal_jazz'  # Default to modal_jazz
            
            # Handle Claude recommendations that affect difficulty
            if self._last_recommendation == 'SIMPLIFY':
                target_difficulty = max(1, target_difficulty - 1)
                # Update the stored initial difficulty to persist the change
                self._initial_difficulty = target_difficulty
                self.logger.info(f"🎯 SIMPLIFY recommendation: reducing difficulty to {target_difficulty} (persisted)")
            elif self._last_recommendation == 'COMPLEXIFY':
                target_difficulty = min(5, target_difficulty + 1) 
                # Update the stored initial difficulty to persist the change
                self._initial_difficulty = target_difficulty
                self.logger.info(f"🎯 COMPLEXIFY recommendation: increasing difficulty to {target_difficulty} (persisted)")
            elif self._last_recommendation == 'CURRENT_COMPLEXITY_NEW_PHRASE':
                # Keep same difficulty, just get a new phrase
                self.logger.info(f"🎯 NEW_PHRASE recommendation: keeping difficulty {target_difficulty}")
            
            # Clear the recommendation after processing difficulty adjustment
            self._last_recommendation = None
            
            # Get phrases filtered by difficulty and style
            phrases = self.library.filter_phrases(
                style=target_style,
                difficulty=target_difficulty
            )
            
            if phrases:
                import random
                self.current_phrase = random.choice(phrases)
                self.logger.info(f"🎯 Selected phrase: {self.current_phrase.name} (ID: {self.current_phrase.id}, difficulty: {self.current_phrase.difficulty})")
                # Reset attempt counter for new phrase
                self._current_phrase_attempts = 0
                if self.current_phrase.id not in self._phrase_attempt_history:
                    self._phrase_attempt_history[self.current_phrase.id] = []
            else:
                self.logger.error(f"No phrases available for style='{target_style}' difficulty={target_difficulty}")
                # Fallback to any phrase from the style
                fallback_phrases = self.library.get_phrases_by_style(target_style)
                if fallback_phrases:
                    self.current_phrase = random.choice(fallback_phrases)
                    self.logger.warning(f"🎯 Fallback: Selected any phrase: {self.current_phrase.name} (difficulty: {self.current_phrase.difficulty})")
                else:
                    self.logger.error("No phrases available for playback")
                    return
        else:
            # Continuing with current phrase - increment attempt counter
            self._current_phrase_attempts += 1
            self.logger.info(f"🎯 Repeating phrase: {self.current_phrase.name} (Attempt #{self._current_phrase_attempts + 1})")
        
        # Play the phrase once (non-looping)
        self.logger.info(f"🎯 Starting playback of phrase: {self.current_phrase.name}")
        
        # Set session timing on phrase player for downbeat synchronization
        self.phrase_player.set_session_timing(self.session_start_time, self.config.bpm)
        
        self.phrase_player.play_phrase(self.current_phrase, bpm=self.config.bpm)
        
        self._emit_event('phrase_playback_started', {
            'phrase_id': self.current_phrase.id,
            'phrase_name': self.current_phrase.name,
            'measures': self.current_phrase.measures
        })
    
    def _enter_listening_state(self) -> None:
        """Enter LISTENING state - wait for user input"""
        if not self.session_active:
            return
            
        self._user_input_detected = False
        self._midi_notes_playing.clear()
        
        # Start listening thread
        self._stop_listening.clear()
        self._listening_thread = threading.Thread(
            target=self._listening_worker,
            daemon=True
        )
        self._listening_thread.start()
        
        self._emit_event('listening_started', {
            'phrase_id': self.current_phrase.id if self.current_phrase else None,
            'expected_measures': self.current_phrase.measures if self.current_phrase else 1
        })
    
    def _enter_recording_state(self) -> None:
        """Enter RECORDING_RESPONSE state - record user's response"""
        if not self.session_active:
            return
            
        # Recording already started in on_midi_note_on when first input was detected
        # Just ensure recording is active and start the response timer thread
        if not self._recording_active:
            # Fallback in case we get here without input detection
            self._response_start_time = time.time()
            self._recording_active = True
            self._recorded_midi_events = []
            self._active_note_starts = {}
        
        # Calculate response duration based on current phrase
        if self.current_phrase:
            self.config.response_measures = self.current_phrase.measures
        
        response_duration = self.config.get_response_duration()
        
        # Start response recording thread
        threading.Thread(
            target=self._recording_worker,
            args=(response_duration,),
            daemon=True
        ).start()
        
        self._emit_event('user_response_started', {
            'expected_duration': response_duration,
            'expected_measures': self.config.response_measures
        })
    
    def _enter_feedback_state(self) -> None:
        """Enter FEEDBACK state - evaluate student performance with Claude AI"""
        if not self.session_active:
            return
            
        # Start Claude evaluation in a separate thread
        threading.Thread(
            target=self._claude_evaluation_worker,
            daemon=True
        ).start()
        
        self._emit_event('feedback_started', {
            'evaluation_type': 'claude_ai'
        })
    
    def _claude_evaluation_worker(self) -> None:
        """Worker thread for Claude AI evaluation"""
        try:
            # Perform Claude evaluation
            if self.current_phrase and self._last_student_phrase:
                evaluation = self._evaluate_with_claude()
                
                # Emit evaluation event with results
                self._emit_event('claude_evaluation_complete', {
                    'evaluation': evaluation
                })
                
                # Brief pause to show feedback, then continue
                time.sleep(3.0)
                
            else:
                self.logger.warning("Cannot evaluate - missing target or student phrase")
                # Emit fallback evaluation
                fallback_evaluation = self.claude_evaluator.get_fallback_evaluation(
                    self.current_phrase or Phrase([], {}),
                    self._last_student_phrase or Phrase([], {})
                )
                self._emit_event('claude_evaluation_complete', {
                    'evaluation': fallback_evaluation
                })
                time.sleep(2.0)
                
        except Exception as e:
            self.logger.error(f"Claude evaluation failed: {e}")
            # Emit error event
            self._emit_event('claude_evaluation_error', {
                'error': str(e)
            })
            time.sleep(1.0)
        
        # Evaluation complete, go back to playback for next phrase
        with self._state_lock:
            if self.session_active:
                self.phrases_completed += 1
                self._emit_event('feedback_finished', {
                    'phrases_completed': self.phrases_completed
                })
                self._change_state(SessionState.PLAYBACK)
    
    def _evaluate_with_claude(self) -> ClaudeEvaluation:
        """Perform Claude AI evaluation of student performance"""
        try:
            # Get current difficulty from phrase metadata
            difficulty_level = 1
            if self.current_phrase and 'difficulty' in self.current_phrase.metadata:
                difficulty_level = self.current_phrase.metadata['difficulty']
            
            # Get musical style from phrase metadata
            musical_style = "modal_jazz"
            if self.current_phrase and 'style' in self.current_phrase.metadata:
                musical_style = self.current_phrase.metadata['style']
            
            self.logger.info(f"Requesting Claude evaluation (difficulty={difficulty_level}, style={musical_style})")
            
            # Get phrase history for context
            phrase_history = []
            if self.current_phrase and self.current_phrase.id in self._phrase_attempt_history:
                phrase_history = self._phrase_attempt_history[self.current_phrase.id]
            
            # Call Claude evaluator
            evaluation = self.claude_evaluator.evaluate_phrase(
                target_phrase=self.current_phrase,
                student_phrase=self._last_student_phrase,
                difficulty_level=difficulty_level,
                musical_style=musical_style,
                phrase_history=phrase_history
            )
            
            if evaluation:
                self.logger.info(f"Claude evaluation: Grade={evaluation.grade}, Recommendation={evaluation.recommendation}")
                
                # Store the grade in phrase history
                if self.current_phrase and self.current_phrase.id:
                    if self.current_phrase.id not in self._phrase_attempt_history:
                        self._phrase_attempt_history[self.current_phrase.id] = []
                    self._phrase_attempt_history[self.current_phrase.id].append(evaluation.grade)
                    self.logger.debug(f"Updated phrase history for {self.current_phrase.id}: {self._phrase_attempt_history[self.current_phrase.id]}")
                
                # Store recommendation for next phrase selection
                self._last_recommendation = evaluation.recommendation
                
                return evaluation
            else:
                self.logger.warning("Claude evaluation returned None, using fallback")
                return self.claude_evaluator.get_fallback_evaluation(
                    self.current_phrase, self._last_student_phrase
                )
                
        except Exception as e:
            self.logger.error(f"Error during Claude evaluation: {e}")
            return self.claude_evaluator.get_fallback_evaluation(
                self.current_phrase or Phrase([], {}),
                self._last_student_phrase or Phrase([], {})
            )
    
    def _enter_idle_state(self) -> None:
        """Enter IDLE state - stop all activity"""
        self.session_active = False
        self._stop_listening.set()
        
        # Stop autonomous player if running
        if hasattr(self.autonomous_player, 'stop'):
            self.autonomous_player.stop()
        
        self._emit_event('session_stopped', {})
    
    def _calculate_bar_duration(self) -> float:
        """Calculate duration of one bar in seconds"""
        beats_per_bar = 4  # Assuming 4/4 time
        return (beats_per_bar * 60.0) / self.config.bpm
    
    def _on_phrase_started(self, phrase: Phrase, bpm: int) -> None:
        """Called when phrase player starts a phrase"""
        self.logger.info(f"🎯 PHRASE STARTED CALLBACK: {phrase.name} (ID: {phrase.id})")
        with self._state_lock:
            if not self.session_active:
                self.logger.info("🎯 Session not active, ignoring phrase started")
                return
            
            # Update current phrase info
            self.current_phrase = phrase
            
            # Only emit event if we're already in PLAYBACK state
            # (state transition and phrase selection is handled by _enter_playback_state)
            if self.state == SessionState.PLAYBACK:
                self.logger.info(f"🎯 Emitting phrase_playback_started event")
                self._emit_event('phrase_playback_started', {
                    'phrase_id': phrase.id,
                    'phrase_name': phrase.name,
                    'measures': phrase.measures,
                    'bpm': bpm
                })
            else:
                self.logger.info(f"🎯 Not in PLAYBACK state (current: {self.state.value}), not emitting event")
    
    def _on_phrase_finished(self, phrase: Phrase) -> None:
        """Called when phrase player finishes a phrase"""
        self.logger.info(f"🎯 PHRASE FINISHED CALLBACK: {phrase.name} (ID: {phrase.id})")
        with self._state_lock:
            if not self.session_active:
                self.logger.info("🎯 Session not active, ignoring phrase finished")
                return
            
            self.logger.info(f"🎯 Current state: {self.state.value}")
            
            # Only transition to LISTENING if we're currently in PLAYBACK
            if self.state == SessionState.PLAYBACK:
                # LOG BOT PHRASE JSON AT END OF PLAYBACK STAGE
                try:
                    from evaluation.phrase_analyzer import analyze_phrase_to_json
                    context = {
                        "phrase_type": "bot_phrase",
                        "session_bpm": self.config.bpm,
                        "playback_time": time.time(),
                        "session_state": "ending_playback"
                    }
                    bot_phrase_json = analyze_phrase_to_json(phrase, context, pretty=True)
                    
                    # Write to session log instead of command line
                    log_content = (
                        f"{'=' * 80}\n"
                        f"🤖 BOT PHRASE JSON SUMMARY (END OF PLAYBACK):\n"
                        f"{'=' * 80}\n"
                        f"{bot_phrase_json}\n"
                        f"{'=' * 80}\n"
                    )
                    self._write_to_session_log(log_content)
                    
                    # Also print a brief summary to command line
                    print(f"🤖 Bot played: {phrase.name} - logged to session file")
                    
                except Exception as e:
                    self.logger.error(f"Error generating bot phrase JSON: {e}")
                
                # Update expected response measures based on phrase
                self.config.response_measures = phrase.measures
                self.logger.info(f"🎯 Transitioning from PLAYBACK to LISTENING")
                
                # Transition to listening state
                self._change_state(SessionState.LISTENING)
                
                self._emit_event('phrase_playback_finished', {
                    'phrase_id': phrase.id,
                    'expected_measures': phrase.measures,
                    'timeout': self.config.input_timeout
                })
            else:
                self.logger.info(f"🎯 Not in PLAYBACK state (current: {self.state.value}), not transitioning")
    
    def _listening_worker(self) -> None:
        """Worker thread for listening phase - wait for user input"""
        # Wait for user input
        input_detected = self._wait_for_user_input()
        
        if not input_detected or self._stop_listening.is_set():
            # Timeout or session stopped
            with self._state_lock:
                if self.session_active:
                    self._emit_event('input_timeout', {
                        'timeout_duration': self.config.input_timeout
                    })
                    # Go back to PLAYBACK to replay the phrase
                    self._change_state(SessionState.PLAYBACK)
            return
        
        # User input detected, transition to recording response
        with self._state_lock:
            if self.session_active:
                self._change_state(SessionState.RECORDING_RESPONSE)
    
    def _recording_worker(self, duration: float) -> None:
        """Worker thread for recording user response"""
        # Wait for the response duration
        time.sleep(duration)
        
        # STOP MIDI RECORDING AND ANALYZE STUDENT PHRASE
        self._recording_active = False
        
        # Recording complete, transition to feedback
        with self._state_lock:
            if self.session_active:
                actual_duration = time.time() - (self._response_start_time or 0)
                
                # CONVERT RECORDED MIDI TO PHRASE AND LOG JSON
                try:
                    student_phrase = self._convert_midi_recording_to_phrase()
                    if student_phrase:
                        # Store for Claude evaluation
                        self._last_student_phrase = student_phrase
                        
                        from evaluation.phrase_analyzer import analyze_phrase_to_json
                        context = {
                            "phrase_type": "student_response",
                            "session_bpm": self.config.bpm,
                            "recording_duration": actual_duration,
                            "expected_duration": duration,
                            "target_phrase_id": self.current_phrase.id if self.current_phrase else "unknown",
                            "session_state": "ending_recording"
                        }
                        student_phrase_json = analyze_phrase_to_json(student_phrase, context, pretty=True)
                        
                        # Write to session log instead of command line
                        log_content = (
                            f"{'=' * 80}\n"
                            f"👨‍🎓 STUDENT PHRASE JSON SUMMARY (END OF RECORDING):\n"
                            f"{'=' * 80}\n"
                            f"{student_phrase_json}\n"
                            f"{'=' * 80}\n"
                        )
                        self._write_to_session_log(log_content)
                        
                        # Print brief summary to command line
                        note_count = len(student_phrase.notes)
                        print(f"👨‍🎓 Student played {note_count} note(s) - logged to session file")
                        
                    else:
                        # Clear stored phrase if no notes recorded
                        self._last_student_phrase = None
                        
                        # Log no notes recorded
                        log_content = (
                            f"{'=' * 80}\n"
                            f"👨‍🎓 STUDENT PHRASE: No notes recorded\n"
                            f"{'=' * 80}\n"
                        )
                        self._write_to_session_log(log_content)
                        print("👨‍🎓 Student played: No notes recorded - logged to session file")
                        
                except Exception as e:
                    self.logger.error(f"Error generating student phrase JSON: {e}")
                    # Log error to session file
                    log_content = (
                        f"{'=' * 80}\n"
                        f"👨‍🎓 STUDENT PHRASE: Error analyzing response - {e}\n"
                        f"{'=' * 80}\n"
                    )
                    self._write_to_session_log(log_content)
                    print(f"👨‍🎓 Student phrase analysis error - logged to session file")
                
                self._emit_event('user_response_finished', {
                    'expected_duration': duration,
                    'actual_duration': actual_duration
                })
                
                # Update session stats
                self.phrases_completed += 1
                
                # Transition to feedback state
                self._change_state(SessionState.FEEDBACK)
    
    def _feedback_worker(self, duration: float) -> None:
        """Worker thread for feedback phase"""
        # Wait for feedback duration (placeholder - 1 bar)
        time.sleep(duration)
        
        # Feedback complete, go back to playback
        with self._state_lock:
            if self.session_active:
                self._emit_event('feedback_finished', {
                    'duration': duration
                })
                
                # Transition back to playback for next phrase
                self._change_state(SessionState.PLAYBACK)
    
    def _wait_for_user_input(self) -> bool:
        """
        Wait for user to start playing notes.
        
        Returns:
            True if input detected, False if timeout
        """
        start_time = time.time()
        
        while not self._stop_listening.is_set():
            # Check for timeout
            if time.time() - start_time > self.config.input_timeout:
                return False
            
            # Check if user input detected
            if self._user_input_detected:
                self._user_input_detected = False  # Reset flag
                return True
            
            # Small delay to avoid busy waiting
            time.sleep(0.05)
        
        return False
    
    def _continue_session(self) -> None:
        """Continue to next phrase in session, waiting for next downbeat (beat 1)"""
        if not self.session_active:
            return
        
        # Calculate next downbeat (beat 1) based on synchronized timing
        if self.session_start_time:
            next_downbeat_time = self._calculate_next_downbeat()
            current_time = time.time()
            
            if next_downbeat_time > current_time:
                wait_time = next_downbeat_time - current_time
                # Only wait if it's a short time - avoid long delays
                if wait_time < 0.5:  # Less than half a second
                    self.logger.debug(f"Waiting {wait_time:.2f}s for next downbeat")
                    time.sleep(wait_time)
                else:
                    # If the wait would be too long, just start immediately
                    self.logger.debug(f"Skipping long wait ({wait_time:.2f}s), starting immediately")
        else:
            # No synchronized timing, start immediately
            pass
        
        if self.session_active:
            self._change_state(SessionState.PLAYBACK)
            # Autonomous player will automatically play next phrase
    
    def _calculate_next_downbeat(self) -> float:
        """Calculate the time of the next downbeat (beat 1)"""
        if not self.session_start_time:
            return time.time() + 0.5  # Fallback
        
        current_time = time.time()
        session_elapsed = current_time - self.session_start_time
        
        # Calculate how many beats have passed since session start
        beats_elapsed = session_elapsed / self.beat_interval
        
        # Find the next beat 1 (beat numbers: 1, 5, 9, 13, etc.)
        # This means every 4 beats starting from beat 1
        current_beat = (beats_elapsed % 4) + 1
        
        if current_beat <= 1.0:
            # We're currently before or at beat 1, use the current beat 1
            next_beat_1 = int(beats_elapsed // 4) * 4 + 1
        else:
            # We're after beat 1, wait for the next beat 1 (next group of 4)
            next_beat_1 = (int(beats_elapsed // 4) + 1) * 4 + 1
        
        # Convert back to time
        next_downbeat_time = self.session_start_time + ((next_beat_1 - 1) * self.beat_interval)
        
        # Ensure we don't schedule in the past
        if next_downbeat_time <= current_time:
            # Add one full measure (4 beats) to get the next opportunity
            next_downbeat_time += 4 * self.beat_interval
        
        return next_downbeat_time
    
    # MIDI Input Interface
    def on_midi_note_on(self, note: int, velocity: int) -> None:
        """Called when MIDI note starts"""
        self.logger.info(f"🎯 MIDI NOTE ON: note={note}, velocity={velocity}, current_state={self.state.value}")
        
        self._midi_notes_playing.add(note)
        
        # Detect start of user input during listening phase FIRST
        with self._state_lock:
            if (self.state == SessionState.LISTENING and 
                not self._user_input_detected):
                self.logger.info(f"🎯 USER INPUT DETECTED: note={note}, transitioning to RECORDING_RESPONSE")
                self._user_input_detected = True
                
                # IMMEDIATELY START RECORDING TO CAPTURE THE FIRST NOTE
                self._response_start_time = time.time()
                self._recording_active = True
                self._recorded_midi_events = []
                self._active_note_starts = {}
                
                # Record this first note immediately
                timestamp = time.time() - self._response_start_time
                self._recorded_midi_events.append({
                    'type': 'note_on',
                    'note': note,
                    'velocity': velocity,
                    'timestamp': timestamp
                })
                self._active_note_starts[note] = timestamp
                
                self._emit_event('user_input_detected', {
                    'note': note,
                    'velocity': velocity,
                    'time_since_phrase_end': time.time() - (self._response_start_time or time.time())
                })
            else:
                # Record MIDI events during recording phase (for subsequent notes)
                if self._recording_active and self._response_start_time:
                    timestamp = time.time() - self._response_start_time
                    self._recorded_midi_events.append({
                        'type': 'note_on',
                        'note': note,
                        'velocity': velocity,
                        'timestamp': timestamp
                    })
                    self._active_note_starts[note] = timestamp
                else:
                    self.logger.info(f"🎯 MIDI NOTE ON ignored: state={self.state.value}, input_detected={self._user_input_detected}")

    def on_midi_note_off(self, note: int) -> None:
        """Called when MIDI note ends"""
        self.logger.info(f"🎯 MIDI NOTE OFF: note={note}, current_state={self.state.value}")
        self._midi_notes_playing.discard(note)
        
        # Record MIDI events during recording phase
        if self._recording_active and self._response_start_time:
            timestamp = time.time() - self._response_start_time
            self._recorded_midi_events.append({
                'type': 'note_off',
                'note': note,
                'timestamp': timestamp
            })
            # Remove from active notes tracking
            self._active_note_starts.pop(note, None)    # Status and Info Methods
    def get_session_state(self) -> SessionState:
        """Get current session state"""
        return self.state
    
    def is_session_active(self) -> bool:
        """Check if session is currently active"""
        return self.session_active
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        if not self.session_start_time:
            return {}
        
        return {
            'session_duration': time.time() - self.session_start_time,
            'phrases_completed': self.phrases_completed,
            'current_state': self.state.value,
            'current_phrase': self.current_phrase.name if self.current_phrase else None,
            'bpm': self.config.bpm,
            'expected_measures': self.config.response_measures
        }
    
    def get_listening_config(self) -> ListeningConfig:
        """Get current listening configuration"""
        return self.config
    
    def _convert_midi_recording_to_phrase(self) -> Optional[Phrase]:
        """
        Convert recorded MIDI events to a Phrase object for analysis.
        
        Returns:
            Phrase object representing the student's response, or None if no valid notes
        """
        if not self._recorded_midi_events:
            return None
        
        try:
            # Process note on/off pairs into MusicalNote objects
            notes = []
            active_notes = {}  # Track note-on events waiting for note-off
            
            # Convert timestamps to beat positions based on session BPM
            beats_per_second = self.config.bpm / 60.0
            
            for event in self._recorded_midi_events:
                if event['type'] == 'note_on':
                    active_notes[event['note']] = event
                elif event['type'] == 'note_off':
                    if event['note'] in active_notes:
                        start_event = active_notes[event['note']]
                        
                        # Calculate beat positions
                        start_beat = start_event['timestamp'] * beats_per_second
                        duration_beats = (event['timestamp'] - start_event['timestamp']) * beats_per_second
                        
                        # Create MusicalNote
                        note = MusicalNote(
                            pitch=event['note'],
                            start_time=start_beat,
                            duration=max(0.1, duration_beats),  # Minimum duration
                            velocity=start_event['velocity']
                        )
                        notes.append(note)
                        del active_notes[event['note']]
            
            # Handle any notes that were still "on" at the end of recording
            for note_num, start_event in active_notes.items():
                start_beat = start_event['timestamp'] * beats_per_second
                # Use a default duration of 0.5 beats for unclosed notes
                duration_beats = 0.5
                
                note = MusicalNote(
                    pitch=note_num,
                    start_time=start_beat,
                    duration=duration_beats,
                    velocity=start_event['velocity']
                )
                notes.append(note)
            
            if not notes:
                return None
            
            # Create phrase metadata
            phrase_duration_beats = max(note.start_time + note.duration for note in notes)
            estimated_bars = max(1, int(phrase_duration_beats / 4))  # Estimate bars based on duration
            
            metadata = {
                'id': f'student_response_{int(time.time())}',
                'description': 'Student Response',
                'style': 'student_response',
                'difficulty': 1,  # Default difficulty
                'key': 'unknown',  # Can't determine key from MIDI alone
                'tempo': self.config.bpm,
                'bars': min(estimated_bars, 4),  # Cap at 4 bars
                'time_signature': (4, 4),
                'recorded_events': len(self._recorded_midi_events),
                'recording_duration': self._recorded_midi_events[-1]['timestamp'] if self._recorded_midi_events else 0
            }
            
            return Phrase(notes, metadata)
            
        except Exception as e:
            self.logger.error(f"Error converting MIDI recording to phrase: {e}")
            return None
