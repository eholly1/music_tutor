"""
Main application window for Music Trainer

This module contains the primary GUI window and application logic.
"""

import os
import tkinter as tk
from tkinter import ttk, messagebox
import sys
from utils.logger import get_logger
from audio.engine import AudioEngine

# Phase 4.4 - Import listening manager components
from music.library import PhraseLibrary
from music.phrase_player import PhrasePlayer, AutonomousPhrasePlayer
from music.listening_manager import PhraseListeningManager, SessionState, ListeningConfig, SessionEvent


class PianoRollVisualization:
    """
    Piano roll visualization that shows notes scrolling from right to left
    """
    def __init__(self, parent, width=800, height=200):
        self.canvas = tk.Canvas(parent, width=width, height=height, bg='#1a1a1a')
        self.width = width
        self.height = height
        self.scroll_speed = 2  # pixels per frame
        self.notes_display = []  # Completed note visualizations
        self.active_notes = {}   # Currently held notes (midi_note -> note_viz)
        
        # Beat line properties
        self.beat_lines = []  # List of beat line objects
        self.bpm = 100  # Default BPM
        self.pixels_per_beat = 80  # Visual spacing between beats
        self.last_beat_time = 0  # Track when last beat line was created
        self.drumming_active = False  # Whether to create new beat lines
        self.beat_counter = 0  # Track which beat number (1, 2, 3, 4)
        
        # Synchronized timing
        self.session_start_time = None  # Shared time reference
        self.beat_interval = 60.0 / self.bpm  # seconds per beat
        
        # Draw piano key reference lines
        self._draw_piano_keys()
        
    def _draw_piano_keys(self):
        """Draw reference lines for piano keys"""
        # Draw horizontal lines for C notes (white keys) across the height
        # C2 to C5 range: MIDI notes 36 to 72
        for midi_note in range(36, 73, 12):  # C notes every octave from C2 to C5
            y_pos = self._calculate_note_height(midi_note)
            self.canvas.create_line(0, y_pos, self.width, y_pos, 
                                   fill='#333333', width=1, tags='reference')
            
            # Add octave labels on the left
            octave = (midi_note - 12) // 12
            self.canvas.create_text(10, y_pos - 5, text=f"C{octave}", 
                                   fill='#666666', anchor='w', font=('Arial', 8), tags='reference')
        
        # Draw a center line (middle C = MIDI 60)
        middle_c_y = self._calculate_note_height(60)
        self.canvas.create_line(0, middle_c_y, self.width, middle_c_y, 
                               fill='#555555', width=2, tags='reference')
        self.canvas.create_text(10, middle_c_y - 8, text="Middle C", 
                               fill='#888888', anchor='w', font=('Arial', 8, 'bold'), tags='reference')
        
    def note_on(self, midi_note, velocity):
        """Start a new note - begins with 0 width and will grow over time"""
        # Only display notes within C2-C5 range (MIDI 36-72)
        if midi_note < 36 or midi_note > 72:
            return  # Don't display notes outside our range
            
        note_height = self._calculate_note_height(midi_note)
        
        # Create note visualization starting with 0 width
        note_viz = {
            'midi_note': midi_note,
            'start_x': self.width,  # Fixed start position at right edge
            'x_position': self.width,  # Current right edge of the growing bar
            'y_position': note_height,
            'velocity': velocity,
            'canvas_id': None,
            'is_active': True
        }
        
        # Store as active note
        self.active_notes[midi_note] = note_viz
        self._draw_note(note_viz)
        
    def note_off(self, midi_note):
        """End a note - stops growing and becomes a completed note"""
        # Only process notes within C2-C5 range (MIDI 36-72)
        if midi_note < 36 or midi_note > 72:
            return  # Don't process notes outside our range
            
        if midi_note in self.active_notes:
            note_viz = self.active_notes[midi_note]
            note_viz['is_active'] = False
            
            # Move from active to completed notes
            self.notes_display.append(note_viz)
            del self.active_notes[midi_note]
    
    def autonomy_note_on(self, midi_note, velocity):
        """Start an autonomy note - begins with 0 width and will grow over time (blue bar)"""
        # Only display notes within C2-C5 range (MIDI 36-72)
        if midi_note < 36 or midi_note > 72:
            return  # Don't display notes outside our range
            
        note_height = self._calculate_note_height(midi_note)
        
        # Create note visualization starting with 0 width (like user notes but blue)
        note_viz = {
            'midi_note': midi_note,
            'start_x': self.width,  # Fixed start position at right edge
            'x_position': self.width,  # Current right edge of the growing bar
            'y_position': note_height,
            'velocity': velocity,
            'canvas_id': None,
            'is_active': True,
            'is_autonomy': True  # Flag to distinguish autonomy notes (blue)
        }
        
        # Store as active autonomy note (separate from user notes)
        # Use negative MIDI note numbers to avoid conflicts with user notes
        autonomy_key = f"autonomy_{midi_note}"
        self.active_notes[autonomy_key] = note_viz
        self._draw_note(note_viz)
    
    def autonomy_note_off(self, midi_note):
        """End an autonomy note - stops growing and becomes a completed note"""
        # Only process notes within C2-C5 range (MIDI 36-72)
        if midi_note < 36 or midi_note > 72:
            return  # Don't process notes outside our range
            
        autonomy_key = f"autonomy_{midi_note}"
        if autonomy_key in self.active_notes:
            note_viz = self.active_notes[autonomy_key]
            note_viz['is_active'] = False
            
            # Move from active to completed notes
            self.notes_display.append(note_viz)
            del self.active_notes[autonomy_key]
    
    def update_scroll(self):
        """Update animation frame - scroll notes and grow active ones"""
        # Update completed notes (just scroll)
        for note in self.notes_display[:]:
            note['start_x'] -= self.scroll_speed
            note['x_position'] -= self.scroll_speed
            
            # Remove notes that have scrolled off the left edge
            if note['x_position'] < 0:
                self.canvas.delete(note['canvas_id'])
                self.notes_display.remove(note)
            else:
                # Update position on canvas
                width = note['x_position'] - note['start_x']
                if width > 0:
                    self.canvas.coords(note['canvas_id'], 
                                     note['start_x'], note['y_position'],
                                     note['x_position'], note['y_position'] + 4)
        
        # Update active notes (scroll start position, grow width)
        for midi_note, note in list(self.active_notes.items()):
            note['start_x'] -= self.scroll_speed
            # x_position stays at right edge for growing effect
            
            # Remove if scrolled completely off screen
            if note['start_x'] + (self.width - note['start_x']) < 0:
                self.canvas.delete(note['canvas_id'])
                del self.active_notes[midi_note]
            else:
                # Update the growing bar
                width = self.width - note['start_x']
                if width > 0:
                    self.canvas.coords(note['canvas_id'], 
                                     note['start_x'], note['y_position'],
                                     self.width, note['y_position'] + 4)
        
        # Update beat lines (scroll them like notes)
        for beat_line in self.beat_lines[:]:
            beat_line['x_position'] -= self.scroll_speed
            
            # Remove beat lines that have scrolled off the left edge
            if beat_line['x_position'] < -10:
                self.canvas.delete(beat_line['canvas_id'])
                if beat_line['text_id']:
                    self.canvas.delete(beat_line['text_id'])
                self.beat_lines.remove(beat_line)
            else:
                # Update line position on canvas
                self.canvas.coords(beat_line['canvas_id'], 
                                 beat_line['x_position'], 0,
                                 beat_line['x_position'], self.height)
                # Update text position on canvas
                if beat_line['text_id']:
                    self.canvas.coords(beat_line['text_id'], 
                                     beat_line['x_position'] + 8, 10)
        
        # Create new beat lines if drumming is active
        if self.drumming_active:
            self._check_and_create_beat_line()
    
    def _calculate_note_height(self, midi_note):
        """Map MIDI note to vertical position (C2 to C5 range)"""
        # Map MIDI notes 36-72 (C2 to C5) across the height
        min_note = 36  # C2
        max_note = 72  # C5
        
        # Clamp note to our display range
        if midi_note < min_note:
            midi_note = min_note
        elif midi_note > max_note:
            midi_note = max_note
            
        # Map to height (inverted so higher notes appear at top)
        note_range = max_note - min_note  # 36 semitones
        return self.height - ((midi_note - min_note) / note_range * (self.height - 20)) - 10
    
    def _draw_note(self, note_viz):
        """Draw colored rectangle representing the note"""
        # Check if this is an autonomy note (blue) or user note (red)
        if note_viz.get('is_autonomy', False):
            # Blue color for autonomy notes
            intensity = max(100, int(note_viz['velocity'] / 127 * 255))
            color = f"#4040{intensity:02x}"  # Blue with some red/green for better visibility
            outline_color = '#6060ff'
        else:
            # Red color for user notes
            intensity = max(100, int(note_viz['velocity'] / 127 * 255))
            color = f"#{intensity:02x}4040"  # Red with some green/blue for better visibility
            outline_color = '#ff6060'
        
        # Determine width based on note type
        if note_viz['is_active']:
            # Growing notes (both user and autonomy) start with minimal width
            width = 2  # Start with 2 pixels
        else:
            # Completed notes (both user and autonomy) use calculated width
            width = note_viz['x_position'] - note_viz['start_x']
        
        canvas_id = self.canvas.create_rectangle(
            note_viz['start_x'], note_viz['y_position'],
            note_viz['start_x'] + width, note_viz['y_position'] + 4,
            fill=color, outline=outline_color, width=1
        )
        note_viz['canvas_id'] = canvas_id
        
    def _check_and_create_beat_line(self):
        """Check if it's time to create a new beat line based on synchronized timing"""
        if not self.session_start_time:
            return
            
        import time
        current_time = time.time()
        session_elapsed = current_time - self.session_start_time
        
        # Calculate how many beats should have occurred since session start
        beats_elapsed = int(session_elapsed / self.beat_interval)
        expected_beat_time = self.session_start_time + (beats_elapsed * self.beat_interval)
        
        # Only create beat line if we haven't created one for this beat yet
        if expected_beat_time > self.last_beat_time:
            # Calculate beat number (1, 2, 3, 4) sequentially from start
            self.beat_counter = (beats_elapsed % 4) + 1
            self._create_beat_line()
            self.last_beat_time = expected_beat_time
    
    def _create_beat_line(self):
        """Create a new beat line at the right edge of the piano roll"""
        # beat_counter is now set by _check_and_create_beat_line()
        
        # Create beat line data structure
        beat_line = {
            'x_position': self.width,  # Start at right edge
            'beat_number': self.beat_counter,
            'canvas_id': None,
            'text_id': None  # For beat number label
        }
        
        # Draw the beat line
        if self.beat_counter == 1:  # Downbeat (beat 1) - solid white line
            canvas_id = self.canvas.create_line(
                self.width, 0, self.width, self.height,
                fill='white', width=2, tags="beat_line"
            )
        else:  # Beats 2, 3, 4 - dashed gray lines
            canvas_id = self.canvas.create_line(
                self.width, 0, self.width, self.height,
                fill='gray', width=1, dash=(3, 3), tags="beat_line"
            )
        
        # Add beat number label at the top of the line
        text_id = self.canvas.create_text(
            self.width + 8, 10,  # Position slightly to the right of the line
            text=str(self.beat_counter),
            fill='white',  # White color for visibility
            font=('Arial', 12, 'bold'),
            tags="beat_text"
        )
        
        beat_line['canvas_id'] = canvas_id
        beat_line['text_id'] = text_id
        self.beat_lines.append(beat_line)
    
    def set_bpm(self, bpm):
        """Update the BPM for beat line timing"""
        self.bpm = bpm
        self.beat_interval = 60.0 / bpm  # Update beat interval
        self.pixels_per_beat = max(40, 8000 / bpm)  # Scale inversely with BPM
    
    def start_beat_visualization(self):
        """Start creating beat lines during practice session"""
        import time
        self.session_start_time = time.time()  # Shared timing reference
        self.drumming_active = True
        self.last_beat_time = 0  # Reset beat tracking
        self.beat_counter = 0  # Reset beat counter
        
        # Notify parent about session start time for drum synchronization
        if hasattr(self, 'parent') and hasattr(self.parent, 'set_session_start_time'):
            self.parent.set_session_start_time(self.session_start_time)
    
    def stop_beat_visualization(self):
        """Stop creating new beat lines when practice session ends"""
        self.drumming_active = False
        self.session_start_time = None
        # Note: existing beat lines will continue to scroll until they disappear


class MainWindow:
    """
    Main application window for Music Trainer
    
    This class creates and manages the primary user interface,
    including device setup, practice session controls, and navigation.
    """
    
    def __init__(self, config):
        """
        Initialize the main window
        
        Args:
            config (Config): Application configuration object
        """
        self.config = config
        self.logger = get_logger()
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Music Trainer - AI Practice Bot")
        self.root.geometry(f"{config.get('gui.window_width')}x{config.get('gui.window_height')}")
        
        # Initialize variables
        self.midi_connected = tk.BooleanVar(value=False)
        self.audio_ready = tk.BooleanVar(value=False)
        self.midi_handler = None  # Will be set when MIDI device connects
        self.session_state_label = None  # Will be created in practice controls
        self.complexity_level_label = None  # Will be created in practice controls
        self.ai_grade_label = None  # Will be created in session status
        self.default_style = self.config.get('practice.style')  # Use default style from config
        
        # Initialize audio engine
        try:
            self.audio_engine = AudioEngine()
            self.audio_ready.set(True)
            self.logger.info("Audio engine initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize audio engine: {e}")
            self.audio_engine = None
            messagebox.showwarning("Audio Warning", 
                                 f"Audio engine initialization failed: {e}\n"
                                 "MIDI input will work but no audio output will be available.")
        
        # Phase 4.4 - Initialize call-and-response components
        self.phrase_library = None
        self.phrase_player = None
        self.autonomous_player = None
        self.listening_manager = None
        self.call_response_active = False
        
        # Initialize Phase 4.4 components if audio engine is available
        if self.audio_engine:
            self._initialize_call_response_system()
        
        # Setup UI
        self._setup_menu()
        self._setup_main_interface()
        self._setup_piano_roll()
        self._setup_status_bar()
        
        # Bind window events
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
        
        # Auto-detect and connect MIDI devices
        self.root.after(100, self._auto_detect_midi)  # Delay to ensure UI is ready
        
        self.logger.info("Main window initialized")
    
    def _initialize_call_response_system(self):
        """Initialize Phase 4.4 call-and-response components"""
        try:
            # Create phrase library
            self.phrase_library = PhraseLibrary()
            self.phrase_library.load_style('modal_jazz')
            self.logger.info("Phrase library initialized")
            
            # Create phrase players
            self.phrase_player = PhrasePlayer(self.audio_engine)
            self.autonomous_player = AutonomousPhrasePlayer(self.phrase_library, self.phrase_player)
            self.logger.info("Phrase players initialized")
            
            # Create listening manager
            self.listening_manager = PhraseListeningManager(
                self.phrase_library,
                self.phrase_player,
                self.autonomous_player,
                claude_api_key=self.config.get_anthropic_api_key()  # Get API key from config
            )
            
            # Configure listening behavior
            config = ListeningConfig(
                input_timeout=10.0,    # 10 seconds to respond
                response_measures=1,   # Expect 1 measure response
                bpm=120               # Default BPM (will be updated from GUI)
            )
            self.listening_manager.set_listening_config(config)
            
            # Setup event callbacks for GUI updates
            self._setup_call_response_callbacks()
            
            self.logger.info("Call-and-response system initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize call-and-response system: {e}")
            self.phrase_library = None
            self.phrase_player = None
            self.autonomous_player = None
            self.listening_manager = None
    
    def _setup_call_response_callbacks(self):
        """Setup event callbacks for call-and-response session"""
        if not self.listening_manager:
            return
        
        # Session lifecycle events
        self.listening_manager.add_event_callback('session_started', self._on_call_response_session_started)
        self.listening_manager.add_event_callback('session_stopped', self._on_call_response_session_stopped)
        self.listening_manager.add_event_callback('state_changed', self._on_call_response_state_changed)
        
        # Phrase events
        self.listening_manager.add_event_callback('phrase_playback_started', self._on_phrase_playback_started)
        self.listening_manager.add_event_callback('phrase_playback_finished', self._on_phrase_playback_finished)
        
        # User interaction events
        self.listening_manager.add_event_callback('user_input_detected', self._on_user_input_detected)
        self.listening_manager.add_event_callback('user_response_started', self._on_user_response_started)
        self.listening_manager.add_event_callback('user_response_finished', self._on_user_response_finished)
        self.listening_manager.add_event_callback('input_timeout', self._on_input_timeout)
        
        # Claude AI evaluation events
        self.listening_manager.add_event_callback('claude_evaluation_complete', self._on_claude_evaluation_complete)
        self.listening_manager.add_event_callback('claude_evaluation_error', self._on_claude_evaluation_error)
        self.listening_manager.add_event_callback('feedback_started', self._on_feedback_started)
        self.listening_manager.add_event_callback('feedback_finished', self._on_feedback_finished)
        
        # Setup phrase player note callback for autonomy note visualization
        if self.phrase_player:
            # IMPORTANT: Preserve existing started/finished callbacks when setting note callbacks
            # The listening manager may have already set intercept callbacks that we don't want to overwrite
            existing_started = self.phrase_player.playback_started_callback
            existing_finished = self.phrase_player.playback_finished_callback
            
            self.logger.info(f"🎯 MAIN WINDOW: Preserving existing callbacks - started: {existing_started}, finished: {existing_finished}")
            
            self.phrase_player.set_playback_callbacks(
                started_callback=existing_started,
                finished_callback=existing_finished,
                note_on_callback=self._on_autonomy_note_on,
                note_off_callback=self._on_autonomy_note_off
            )
            
            self.logger.info(f"🎯 MAIN WINDOW: Callbacks after setting - started: {self.phrase_player.playback_started_callback}, finished: {self.phrase_player.playback_finished_callback}")
    
    def _midi_note_callback(self, completed_note, timestamp):
        """
        Callback for MIDI note events - triggers audio synthesis and call-and-response
        
        Args:
            completed_note: MIDINote object with note information
            timestamp: Note event timestamp
        """
        if not self.audio_engine:
            return
        
        try:
            # Extract MIDI note information
            midi_note = completed_note.pitch
            velocity = int(completed_note.velocity * 127)  # Convert back to MIDI range
            
            # Handle call-and-response session
            if self.listening_manager and self.call_response_active:
                # Forward MIDI events to listening manager
                if completed_note.duration and completed_note.duration > 0:
                    # Note on
                    self.listening_manager.on_midi_note_on(midi_note, velocity)
                    # Note off will be called when the note ends
                    # For now we'll simulate it after a short delay since we have completed notes
                    self.root.after(int(completed_note.duration * 1000), 
                                   lambda: self.listening_manager.on_midi_note_off(midi_note))
            
            # Trigger audio synthesis for user feedback
            if completed_note.duration and completed_note.duration > 0:
                # Note with duration - trigger note on/off
                self.audio_engine.note_on(midi_note, velocity)
                # Schedule note off (simplified - immediate for now)
                self.root.after(int(completed_note.duration * 1000), 
                               lambda: self.audio_engine.note_off(midi_note))
            
            self.logger.debug(f"Audio triggered for MIDI note {midi_note}, vel={velocity}")
            
        except Exception as e:
            self.logger.error(f"Error in MIDI note callback: {e}")
    
    def _raw_midi_callback(self, midi_data, timestamp):
        """
        Callback for raw MIDI events - handles note on/off directly
        
        Args:
            midi_data: Raw MIDI message data
            timestamp: Event timestamp
        """
        if not self.audio_engine:
            self.logger.warning(f"❌ NO AUDIO ENGINE - cannot synthesize audio!")
            return
        
        if not self.audio_engine.is_running:
            self.logger.warning(f"❌ AUDIO ENGINE NOT RUNNING - cannot synthesize audio!")
            return
        
        if not isinstance(midi_data, list) or len(midi_data) < 3:
            self.logger.warning(f"❌ INVALID MIDI DATA FORMAT: {midi_data}")
            return
        
        try:
            status = midi_data[0]
            msg_type = status & 0xF0
            
            if msg_type == 0x90 and midi_data[2] > 0:  # Note On
                midi_note = midi_data[1]
                velocity = midi_data[2]
                self.audio_engine.note_on(midi_note, velocity)
                
                # Forward to listening manager for call-and-response
                if self.listening_manager and self.call_response_active:
                    self.logger.info(f"🎯 FORWARDING NOTE ON to listening manager: MIDI {midi_note}, state should be LISTENING")
                    self.listening_manager.on_midi_note_on(midi_note, velocity)
                
                # Start note in piano roll visualization
                if hasattr(self, 'piano_roll'):
                    self.piano_roll.note_on(midi_note, velocity)
                
            elif msg_type == 0x80 or (msg_type == 0x90 and midi_data[2] == 0):  # Note Off
                midi_note = midi_data[1]
                self.audio_engine.note_off(midi_note)
                
                # Forward to listening manager for call-and-response
                if self.listening_manager and self.call_response_active:
                    self.listening_manager.on_midi_note_off(midi_note)
                
                # End note in piano roll visualization
                if hasattr(self, 'piano_roll'):
                    self.piano_roll.note_off(midi_note)
            else:
                self.logger.info(f"ℹ️  OTHER MIDI MESSAGE: 0x{msg_type:02X} - ignoring")
                
        except Exception as e:
            self.logger.error(f"💥 ERROR in raw MIDI callback: {e}")
            import traceback
            self.logger.error(f"💥 TRACEBACK: {traceback.format_exc()}")
    
    def _setup_menu(self):
        """Setup application menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Session", command=self._new_session)
        file_menu.add_command(label="Open Session", command=self._open_session)
        file_menu.add_command(label="Save Session", command=self._save_session)
        file_menu.add_separator()
        file_menu.add_command(label="Preferences", command=self._show_preferences)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_closing)
        
        # Devices menu
        devices_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Devices", menu=devices_menu)
        devices_menu.add_command(label="Setup MIDI", command=self._setup_midi)
        devices_menu.add_command(label="Test Devices", command=self._test_devices)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self._show_help)
        help_menu.add_command(label="About", command=self._show_about)
    
    def _setup_main_interface(self):
        """Setup the main interface components"""
        # Create main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=0)  # Piano roll row
        self.root.rowconfigure(2, weight=0)  # Status bar row
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Header section
        self._setup_header(main_frame)
        
        # Device status section
        self._setup_device_status(main_frame)
        
        # Practice control section
        self._setup_practice_controls(main_frame)
        
        # Session status area
        self._setup_session_status(main_frame)
    
    def _setup_header(self, parent):
        """Setup application header"""
        header_frame = ttk.Frame(parent)
        header_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        title_label = ttk.Label(
            header_frame, 
            text="Music Trainer", 
            font=("Arial", 24, "bold")
        )
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        subtitle_label = ttk.Label(
            header_frame, 
            text="AI-Powered Practice Bot",
            font=("Arial", 12),
            foreground="gray"
        )
        subtitle_label.grid(row=1, column=0, sticky=tk.W)
    
    def _setup_device_status(self, parent):
        """Setup device connection status display"""
        status_frame = ttk.LabelFrame(parent, text="Device Status", padding="10")
        status_frame.grid(row=0, column=1, sticky=(tk.N, tk.E), pady=(0, 20), padx=(10, 0))
        
        # Configure the frame to be 40% of its original width
        status_frame.configure(width=150)  # Reduced from typical wider layout
        
        # MIDI status
        midi_frame = ttk.Frame(status_frame)
        midi_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        ttk.Label(midi_frame, text="MIDI:").grid(row=0, column=0, sticky=tk.W)
        self.midi_status_label = ttk.Label(
            midi_frame, 
            text="Not Connected",
            foreground="red"
        )
        self.midi_status_label.grid(row=1, column=0, sticky=tk.W)
        
        ttk.Button(
            midi_frame, 
            text="Setup", 
            command=self._setup_midi
        ).grid(row=2, column=0, sticky=tk.W, pady=(5, 0))
    
    def _setup_practice_controls(self, parent):
        """Setup practice session controls"""
        control_frame = ttk.LabelFrame(parent, text="Practice Session", padding="10")
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Difficulty selection
        ttk.Label(control_frame, text="Initial Complexity:").grid(row=0, column=0, sticky=tk.W)
        self.difficulty_var = tk.IntVar(value=self.config.get('practice.difficulty_level'))
        difficulty_scale = ttk.Scale(
            control_frame,
            from_=1, to=5,
            orient=tk.HORIZONTAL,
            variable=self.difficulty_var
        )
        difficulty_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
        
        self.difficulty_label = ttk.Label(control_frame, text=f"Level {self.difficulty_var.get()}")
        self.difficulty_label.grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        
        # Update difficulty label when scale changes
        difficulty_scale.configure(command=self._update_difficulty_label)
        
        # BPM selection
        ttk.Label(control_frame, text="BPM (Tempo):").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.bpm_var = tk.IntVar(value=100)  # Default to 100 BPM
        bpm_scale = ttk.Scale(
            control_frame,
            from_=60, to=180,
            orient=tk.HORIZONTAL,
            variable=self.bpm_var
        )
        bpm_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=(10, 0))
        
        self.bpm_label = ttk.Label(control_frame, text=f"{self.bpm_var.get()} BPM")
        self.bpm_label.grid(row=1, column=2, sticky=tk.W, padx=(10, 0), pady=(10, 0))
        
        # Update BPM label when scale changes
        bpm_scale.configure(command=self._update_bpm_label)
        
        # Practice session buttons
        button_frame = ttk.Frame(control_frame)
        button_frame.grid(row=2, column=0, columnspan=3, pady=(20, 0))
        
        self.start_button = ttk.Button(
            button_frame,
            text="Start Practice Session",
            command=self._start_practice,
            style="Accent.TButton"
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(
            button_frame,
            text="Stop Session",
            command=self._stop_practice,
            state="disabled"
        )
        self.stop_button.pack(side=tk.LEFT)
    
    def _setup_session_status(self, parent):
        """Setup session status and information area"""
        status_frame = ttk.LabelFrame(parent, text="Session Status", padding="10")
        status_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure status frame to expand
        status_frame.columnconfigure(0, weight=1)
        status_frame.columnconfigure(1, weight=0)  # Grade column on right
        status_frame.rowconfigure(1, weight=1)
        
        # Session state indicator
        state_frame = ttk.Frame(status_frame)
        state_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        ttk.Label(state_frame, text="Session State:", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        self.session_state_label = ttk.Label(
            state_frame, 
            text="IDLE",
            font=("Arial", 12, "bold"),
            foreground="white"
        )
        self.session_state_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # AI Grade display in top right
        self.ai_grade_label = ttk.Label(
            status_frame,
            text="",
            font=("Arial", 36, "bold"),
            foreground="gold",
            anchor=tk.CENTER
        )
        self.ai_grade_label.grid(row=0, column=1, rowspan=2, sticky=(tk.E, tk.N), padx=(10, 0))
        
        # Complexity indicator
        complexity_frame = ttk.Frame(status_frame)
        complexity_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 15))
        
        ttk.Label(complexity_frame, text="Complexity Level:", font=("Arial", 11, "bold")).pack(side=tk.LEFT)
        self.complexity_level_label = ttk.Label(
            complexity_frame, 
            text="",
            font=("Arial", 12, "bold"),
            foreground="white"
        )
        self.complexity_level_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Claude AI Feedback section
        feedback_label = ttk.Label(status_frame, text="AI Feedback:", font=("Arial", 11, "bold"))
        feedback_label.grid(row=2, column=0, sticky=(tk.W,), pady=(0, 5))
        
        # Create text widget with scrollbar for feedback
        feedback_container = ttk.Frame(status_frame)
        feedback_container.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        feedback_container.columnconfigure(0, weight=1)
        feedback_container.rowconfigure(0, weight=1)
        
        self.claude_feedback_text = tk.Text(
            feedback_container,
            height=14,
            width=40,
            wrap=tk.WORD,
            font=("Arial", 10),
            bg="#f8f9fa",
            fg="#212529",
            state=tk.DISABLED,
            relief=tk.GROOVE,
            borderwidth=1
        )
        self.claude_feedback_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for feedback text
        feedback_scrollbar = ttk.Scrollbar(feedback_container, orient=tk.VERTICAL, command=self.claude_feedback_text.yview)
        feedback_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.claude_feedback_text.config(yscrollcommand=feedback_scrollbar.set)
        
        # Initialize feedback area
        self._update_claude_feedback("🤖 Waiting for your first phrase attempt...")
    
    def _setup_piano_roll(self):
        """Setup piano roll visualization at bottom of window"""
        # Create piano roll frame
        piano_roll_frame = ttk.LabelFrame(self.root, text="Piano Roll", padding="5")
        piano_roll_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=10, pady=(0, 5))
        
        # Configure piano roll frame to expand horizontally
        piano_roll_frame.columnconfigure(0, weight=1)
        
        # Create the piano roll visualization
        self.piano_roll = PianoRollVisualization(piano_roll_frame, width=800, height=150)
        self.piano_roll.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        # Start the animation loop
        self._update_piano_roll()
    
    def _update_piano_roll(self):
        """Update piano roll animation frame"""
        if hasattr(self, 'piano_roll'):
            self.piano_roll.update_scroll()
        # Schedule next update (60 FPS)
        self.root.after(16, self._update_piano_roll)

    def _setup_status_bar(self):
        """Setup status bar at bottom of window"""
        self.status_bar = ttk.Label(
            self.root,
            text="Checking for MIDI devices...",
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        self.status_bar.grid(row=2, column=0, sticky=(tk.W, tk.E))
    
    def _update_difficulty_label(self, value):
        """Update difficulty level label"""
        level = int(float(value))
        self.difficulty_label.config(text=f"Level {level}")
    
    def _update_bpm_label(self, value):
        """Update BPM label and drum tempo if playing"""
        bpm = int(float(value))
        self.bpm_label.config(text=f"{bpm} BPM")
        
        # Update piano roll beat line timing
        self.piano_roll.set_bpm(bpm)
        
        # Update drum tempo in real-time if drums are playing
        if self.audio_engine and self.audio_engine.is_drumming():
            self.audio_engine.set_drum_bpm(bpm)
    
    def _update_claude_feedback(self, message: str):
        """Update the Claude AI feedback display"""
        try:
            self.claude_feedback_text.config(state=tk.NORMAL)
            self.claude_feedback_text.delete(1.0, tk.END)
            self.claude_feedback_text.insert(1.0, message)
            self.claude_feedback_text.config(state=tk.DISABLED)
            # Auto-scroll to bottom
            self.claude_feedback_text.see(tk.END)
        except Exception as e:
            self.logger.error(f"Failed to update Claude feedback display: {e}")
    
    def _update_ai_grade_display(self, grade: str):
        """Update the AI grade display with color coding"""
        try:
            if not hasattr(self, 'ai_grade_label') or not self.ai_grade_label:
                return
            
            if grade:
                # Map grades to colors
                grade_colors = {
                    'A+': '#00ff00',  # Bright green
                    'A': '#00cc00',   # Green
                    'A-': '#66cc00',  # Light green
                    'B+': '#99cc00',  # Yellow-green
                    'B': '#cccc00',   # Yellow
                    'B-': '#cc9900',  # Orange-yellow
                    'C+': '#cc6600',  # Orange
                    'C': '#cc3300',   # Red-orange
                    'C-': '#cc0000',  # Red
                    'D': '#990000',   # Dark red
                    'F': '#660000'    # Very dark red
                }
                
                color = grade_colors.get(grade, '#ffffff')  # Default to white
                self.ai_grade_label.config(text=grade, foreground=color)
            else:
                # Clear the grade display
                self.ai_grade_label.config(text="", foreground="#ffffff")
                
        except Exception as e:
            self.logger.error(f"Failed to update AI grade display: {e}")
    
    def _on_style_changed(self, event):
        """Handle style selection change - now uses default style"""
        genre = self.default_style
        
        # Update drum pattern in real-time if drums are playing
        if self.audio_engine and self.audio_engine.is_drumming():
            self.audio_engine.set_drum_genre(genre)
            self.logger.info(f"Changed drum style to {genre} during playback")
    
    # Event handlers (placeholder implementations)
    def _new_session(self):
        """Start a new practice session"""
        self.logger.info("New session requested")
        messagebox.showinfo("New Session", "New session functionality will be implemented in Phase 2")
    
    def _open_session(self):
        """Open existing practice session"""
        self.logger.info("Open session requested")
        messagebox.showinfo("Open Session", "Open session functionality will be implemented in Phase 2")
    
    def _save_session(self):
        """Save current practice session"""
        self.logger.info("Save session requested")
        messagebox.showinfo("Save Session", "Save session functionality will be implemented in Phase 2")
    
    def _show_preferences(self):
        """Show application preferences"""
        self.logger.info("Preferences requested")
        messagebox.showinfo("Preferences", "Preferences dialog will be implemented in Phase 2")
    
    def _auto_detect_midi(self):
        """Automatically detect and connect to MIDI devices on startup"""
        self.logger.info("Auto-detecting MIDI devices...")
        
        try:
            from midi.input_handler import MIDIInputHandler
            
            # Create MIDI handler for detection
            midi_handler = MIDIInputHandler()
            devices = midi_handler.get_available_devices()
            
            if len(devices) == 1:
                # Exactly one device found - auto-connect
                device_name = devices[0]
                self.logger.info(f"Found single MIDI device: {device_name} - attempting auto-connection")
                
                success = midi_handler.connect_device(device_name)
                if success:
                    # Set up MIDI callback for audio synthesis
                    if self.audio_engine:
                        midi_handler.set_input_callback(self._raw_midi_callback)
                        
                        try:
                            self.audio_engine.start()
                            self.logger.info("Audio engine started for real-time synthesis")
                        except Exception as e:
                            self.logger.error(f"Failed to start audio engine: {e}")
                    
                    # Update main window status
                    audio_status = " (Audio: ON)" if self.audio_engine and self.audio_engine.is_running else " (Audio: OFF)"
                    self.midi_status_label.config(text=f"Connected: {device_name}{audio_status}", foreground="green")
                    self.midi_connected.set(True)
                    
                    # Store MIDI handler reference
                    self.midi_handler = midi_handler
                    
                    self.logger.info(f"Successfully auto-connected to {device_name}")
                    
                    # Show brief notification
                    self.status_bar.config(text=f"Auto-connected to MIDI device: {device_name}")
                else:
                    self.logger.warning(f"Failed to auto-connect to {device_name}")
                    
            elif len(devices) > 1:
                # Multiple devices found - let user choose
                self.logger.info(f"Found {len(devices)} MIDI devices - user selection required")
                self.status_bar.config(text=f"Found {len(devices)} MIDI devices - use Devices > Setup MIDI to connect")
                
            else:
                # No devices found
                self.logger.info("No MIDI devices found during auto-detection")
                self.status_bar.config(text="No MIDI devices found - connect a device and use Devices > Setup MIDI")
                
        except ImportError as e:
            self.logger.error(f"MIDI auto-detection failed - rtmidi not available: {e}")
        except Exception as e:
            self.logger.error(f"Error during MIDI auto-detection: {e}")
    
    def _setup_midi(self):
        """Setup MIDI controller"""
        self.logger.info("MIDI setup requested")
        
        # Import here to avoid issues if rtmidi not available
        try:
            from midi.input_handler import MIDIInputHandler
            
            # Create MIDI setup dialog
            setup_window = tk.Toplevel(self.root)
            setup_window.title("MIDI Controller Setup")
            setup_window.geometry("500x400")
            setup_window.grab_set()  # Make it modal
            
            # Create MIDI handler for detection
            midi_handler = MIDIInputHandler()
            
            # Main frame
            main_frame = ttk.Frame(setup_window, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Title
            title_label = ttk.Label(main_frame, text="MIDI Controller Setup", font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Device detection section
            detection_frame = ttk.LabelFrame(main_frame, text="Available MIDI Devices", padding="10")
            detection_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            # Device list
            device_listbox = tk.Listbox(detection_frame, height=6)
            device_listbox.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            
            # Refresh button
            def refresh_devices():
                device_listbox.delete(0, tk.END)
                devices = midi_handler.get_available_devices()
                
                if devices:
                    for device in devices:
                        device_listbox.insert(tk.END, device)
                    status_label.config(text=f"Found {len(devices)} MIDI device(s)", foreground="green")
                else:
                    device_listbox.insert(tk.END, "No MIDI devices found")
                    status_label.config(text="No MIDI devices detected", foreground="red")
            
            refresh_button = ttk.Button(detection_frame, text="Refresh Devices", command=refresh_devices)
            refresh_button.pack(pady=(0, 10))
            
            # Status label
            status_label = ttk.Label(detection_frame, text="Click 'Refresh Devices' to scan")
            status_label.pack()
            
            # Connection section
            connection_frame = ttk.Frame(main_frame)
            connection_frame.pack(fill=tk.X)
            
            # Connect button
            def connect_device():
                selection = device_listbox.curselection()
                if not selection:
                    messagebox.showwarning("No Selection", "Please select a MIDI device to connect.")
                    return
                
                device_name = device_listbox.get(selection[0])
                if device_name == "No MIDI devices found":
                    return
                
                success = midi_handler.connect_device(device_name)
                if success:
                    # Set up MIDI callback for audio synthesis
                    if self.audio_engine:
                        # Set the raw MIDI callback for real-time audio
                        midi_handler.set_input_callback(self._raw_midi_callback)
                        
                        # Start the audio engine
                        try:
                            self.audio_engine.start()
                            self.logger.info("Audio engine started for real-time synthesis")
                        except Exception as e:
                            self.logger.error(f"Failed to start audio engine: {e}")
                            messagebox.showwarning("Audio Warning", 
                                                 f"MIDI connected but audio engine failed to start: {e}")
                    
                    messagebox.showinfo("Success", f"Successfully connected to {device_name}\n"
                                                  f"Audio synthesis: {'Enabled' if self.audio_engine else 'Disabled'}")
                    
                    # Update main window status
                    audio_status = " (Audio: ON)" if self.audio_engine and self.audio_engine.is_running else " (Audio: OFF)"
                    self.midi_status_label.config(text=f"Connected: {device_name}{audio_status}", foreground="green")
                    self.midi_connected.set(True)
                    
                    # Store MIDI handler reference in main window
                    self.midi_handler = midi_handler
                    
                    setup_window.destroy()
                else:
                    messagebox.showerror("Connection Failed", f"Failed to connect to {device_name}")
            
            connect_button = ttk.Button(connection_frame, text="Connect Selected Device", command=connect_device)
            connect_button.pack(side=tk.LEFT, padx=(0, 10))
            
            # Close button
            close_button = ttk.Button(connection_frame, text="Close", command=setup_window.destroy)
            close_button.pack(side=tk.RIGHT)
            
            # Initial device scan
            refresh_devices()
            
        except ImportError as e:
            self.logger.error(f"MIDI setup failed - rtmidi not available: {e}")
            messagebox.showerror("MIDI Error", 
                               "MIDI functionality is not available.\n"
                               "Please install python-rtmidi:\n"
                               "pip install python-rtmidi")
    
    def _test_devices(self):
        """Test device connections"""
        self.logger.info("Device test requested")
        messagebox.showinfo("Device Test", "Device testing will be implemented in Phase 2")
    
    def _start_practice(self):
        """Start practice session with call-and-response functionality"""
        self.logger.info("Practice session start requested")
        
        if not self.audio_engine:
            messagebox.showwarning("No Audio", "Audio engine not available - cannot start practice session")
            return
        
        if not self.listening_manager:
            messagebox.showerror("Error", "Call-and-response system not initialized")
            return
        
        try:
            # Get settings from UI
            bpm = self.bpm_var.get()
            style = self.default_style  # Use default style
            difficulty = self.difficulty_var.get()
            
            # Update listening manager configuration
            config = ListeningConfig(
                input_timeout=10.0,
                response_measures=1,
                bpm=bpm
            )
            self.listening_manager.set_listening_config(config)
            
            # Start beat visualization in piano roll first (establishes timing)
            self.piano_roll.start_beat_visualization()
            
            # Share session timing with listening manager for beat-aligned phrases
            if hasattr(self.piano_roll, 'session_start_time') and self.piano_roll.session_start_time:
                self.listening_manager.set_session_timing(
                    self.piano_roll.session_start_time, 
                    bpm
                )
            
            # Start call-and-response session
            success = self.listening_manager.start_session(
                style='modal_jazz',  # Use modal_jazz style for now
                difficulty=difficulty,
                bpm=bpm
            )
            
            if success:
                # Update UI state
                self.start_button.config(state="disabled")
                self.stop_button.config(state="normal")
                
                self.logger.info(f"Started call-and-response session: modal_jazz level {difficulty} at {bpm} BPM")
                
                # Also start background drums for rhythm support
                self.audio_engine.set_drum_bpm(bpm)
                self.audio_engine.set_drum_genre(style)
                if hasattr(self.piano_roll, 'session_start_time'):
                    self.audio_engine.start_drums(session_start_time=self.piano_roll.session_start_time)
                else:
                    self.audio_engine.start_drums()
                
            else:
                messagebox.showerror("Error", "Failed to start call-and-response session")
                self.piano_roll.stop_beat_visualization()
                
        except Exception as e:
            self.logger.error(f"Failed to start practice session: {e}")
            messagebox.showerror("Error", f"Failed to start practice session: {e}")
            self.piano_roll.stop_beat_visualization()
    
    def _stop_practice(self):
        """Stop practice session"""
        self.logger.info("Practice session stop requested")
        
        try:
            # Stop call-and-response session
            if self.listening_manager and self.listening_manager.is_session_active():
                self.listening_manager.stop_session()
            
            # Stop background drums
            if self.audio_engine:
                self.audio_engine.stop_drums()
            
            # Stop beat visualization in piano roll
            self.piano_roll.stop_beat_visualization()
            
            # Update UI state
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            
            # Reset session state display
            self._update_session_state_display('idle')
            
            self.logger.info("Stopped practice session")
            
        except Exception as e:
            self.logger.error(f"Failed to stop practice session: {e}")
            messagebox.showerror("Error", f"Failed to stop practice session: {e}")
            self._reset_practice_ui()
    
    def _reset_practice_ui(self):
        """Reset practice UI to initial state"""
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self._update_session_state_display('idle')
        self._update_ai_grade_display("")  # Clear grade display
    
    def _show_help(self):
        """Show user guide"""
        messagebox.showinfo("Help", "User guide will be available in Phase 8")
    
    def _show_about(self):
        """Show about dialog"""
        about_text = """Music Trainer v0.1.0

AI-Powered Music Practice Bot

An intelligent practice companion that helps musicians develop their ear and repertoire through interactive call-and-response sessions.

© 2025 Music Trainer Team"""
        messagebox.showinfo("About Music Trainer", about_text)
    
    def _on_closing(self):
        """Handle window closing"""
        self.logger.info("Application closing requested")
        
        # Stop call-and-response session if active
        if self.listening_manager and self.listening_manager.is_session_active():
            self.logger.info("Stopping active call-and-response session before closing")
            self.listening_manager.stop_session()
        
        # Stop audio engine
        if self.audio_engine:
            try:
                self.audio_engine.stop()
                self.logger.info("Audio engine stopped")
            except Exception as e:
                self.logger.error(f"Error stopping audio engine: {e}")
        
        # Disconnect MIDI device if connected
        if self.midi_handler and self.midi_handler.is_connected():
            self.logger.info("Disconnecting MIDI device before closing")
            self.midi_handler.disconnect_device()
        
        # Save configuration before closing
        self.config.save()
        
        # Close the application
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the application main loop"""
        self.logger.info("Starting GUI main loop")
        self.root.mainloop()
    
    # Phase 4.4 - Call-and-Response Event Callbacks
    
    def _on_call_response_session_started(self, event: SessionEvent):
        """Called when call-and-response session starts"""
        data = event.data
        self.call_response_active = True
        self.logger.info(f"Call-and-response session started: {data['style']} at {data['bpm']} BPM")
        
        # Update status bar
        self.status_bar.config(text=f"Practice session active: {data['style']} (Level {data['difficulty']})")
    
    def _on_call_response_session_stopped(self, event: SessionEvent):
        """Called when call-and-response session stops"""
        data = event.data
        self.call_response_active = False
        phrases_completed = data.get('phrases_completed', 0)
        duration = data.get('session_duration', 0)
        
        self.logger.info(f"Call-and-response session ended: {phrases_completed} phrases in {duration:.1f}s")
        
        # Update status bar
        device_status = "MIDI connected" if self.midi_connected.get() else "No MIDI device"
        self.status_bar.config(text=f"Ready - {device_status}")
    
    def _on_call_response_state_changed(self, event: SessionEvent):
        """Called when call-and-response state changes"""
        data = event.data
        new_state = data['new_state']
        
        # Update status bar
        if new_state == 'playback':
            self.status_bar.config(text="🎵 Bot is playing phrase - listen carefully...")
        elif new_state == 'waiting_for_input':
            self.status_bar.config(text="👂 Your turn! Play any note to start your response...")
        elif new_state == 'recording_response':
            self.status_bar.config(text="🎤 Recording your response...")
        
        # Update session state indicator
        self._update_session_state_display(new_state)
        
        self.logger.debug(f"Call-and-response state: {data['old_state']} → {new_state}")
    
    def _update_session_state_display(self, state):
        """Update the session state label with bold white font"""
        if not self.session_state_label:
            return
            
        # Map states to display text - all in bold white font
        state_display = {
            'idle': 'IDLE',
            'playback': 'PLAYBACK',
            'listening': 'LISTENING',
            'waiting_for_input': 'WAITING FOR INPUT',
            'recording_response': 'RECORDING RESPONSE'
        }
        
        display_text = state_display.get(state.lower(), state.upper())
        self.session_state_label.config(text=display_text, foreground="white")
        
        # Update complexity level display
        self._update_complexity_display()
    
    def _update_complexity_display(self):
        """Update the complexity level indicator"""
        if not self.complexity_level_label:
            return
        
        # Get current complexity from listening manager
        if self.listening_manager and hasattr(self.listening_manager, 'current_phrase'):
            current_phrase = self.listening_manager.current_phrase
            if current_phrase and hasattr(current_phrase, 'metadata'):
                difficulty = current_phrase.metadata.get('difficulty', 1)
                complexity_visual = self._get_complexity_visual(difficulty)
                self.complexity_level_label.config(text=f"{complexity_visual}", foreground="white")
            else:
                self.complexity_level_label.config(text="Complexity: ", foreground="white")
        else:
            self.complexity_level_label.config(text="Complexity: ", foreground="white")
    
    def _get_complexity_visual(self, difficulty: int) -> str:
        """Convert difficulty number to visual blocks"""
        # Ensure difficulty is in valid range
        difficulty = max(1, min(5, difficulty))
        
        # Create visual representation with filled and empty blocks
        filled_blocks = "▣" * difficulty
        empty_blocks = "□" * (5 - difficulty)
        return filled_blocks + empty_blocks
    
    def _on_phrase_playback_started(self, event: SessionEvent):
        """Called when bot starts playing a phrase"""
        data = event.data
        phrase_name = data.get('phrase_name', 'phrase')
        measures = data.get('measures', 1)
        
        self.logger.info(f"Bot playing: {phrase_name} ({measures} measures)")
    
    def _on_phrase_playback_finished(self, event: SessionEvent):
        """Called when bot finishes playing a phrase"""
        data = event.data
        self.logger.info(f"Bot finished playing: {data.get('phrase_id', 'phrase')}")
    
    def _on_user_input_detected(self, event: SessionEvent):
        """Called when user starts playing their response"""
        data = event.data
        note = data.get('note', 0)
        velocity = data.get('velocity', 0)
        
        # Convert MIDI note to note name for display
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note // 12) - 1
        note_name = note_names[note % 12] + str(octave)
        
        self.logger.info(f"User response detected: {note_name} (velocity {velocity})")
    
    def _on_user_response_started(self, event: SessionEvent):
        """Called when user response recording starts"""
        data = event.data
        expected_duration = data.get('expected_duration', 0)
        self.logger.info(f"Recording user response ({expected_duration:.1f}s expected)")
    
    def _on_user_response_finished(self, event: SessionEvent):
        """Called when user response recording ends"""
        data = event.data
        expected = data.get('expected_duration', 0)
        actual = data.get('actual_duration', 0)
        
        self.logger.info(f"User response complete: {actual:.1f}s (expected {expected:.1f}s)")
    
    def _on_input_timeout(self, event: SessionEvent):
        """Called when user doesn't respond in time"""
        data = event.data
        timeout = data.get('timeout_duration', 0)
        self.logger.info(f"No response after {timeout:.1f}s - continuing to next phrase")
    
    def _on_feedback_started(self, event: SessionEvent):
        """Called when feedback state begins"""
        self._update_claude_feedback("🤖 Evaluating your performance with Claude AI...")
        self.logger.info("Feedback phase started - Claude evaluation in progress")
    
    def _on_claude_evaluation_complete(self, event: SessionEvent):
        """Called when Claude AI evaluation is complete"""
        evaluation = event.data.get('evaluation')
        if evaluation:
            # Format Claude feedback for display
            feedback_text = self._format_claude_feedback(evaluation)
            self._update_claude_feedback(feedback_text)
            
            # Update the big grade display
            self._update_ai_grade_display(evaluation.grade)
            
            self.logger.info(f"Claude evaluation complete: {evaluation.grade} ({evaluation.recommendation})")
        else:
            self._update_claude_feedback("❌ Evaluation failed - please try again")
            self._update_ai_grade_display("")  # Clear grade on failure
    
    def _on_claude_evaluation_error(self, event: SessionEvent):
        """Called when Claude AI evaluation encounters an error"""
        error = event.data.get('error', 'Unknown error')
        self._update_claude_feedback(f"❌ AI Evaluation Error: {error}")
        self._update_ai_grade_display("")  # Clear grade on error
        self.logger.error(f"Claude evaluation error: {error}")
    
    def _on_feedback_finished(self, event: SessionEvent):
        """Called when feedback phase is complete"""
        phrases_completed = event.data.get('phrases_completed', 0)
        self.logger.info(f"Feedback complete - {phrases_completed} phrases completed")
    
    def _format_claude_feedback(self, evaluation) -> str:
        """Format Claude evaluation for display in the text widget"""
        return f"""✅ What you did well:
{evaluation.positive_feedback}

🎯 What to improve:
{evaluation.improvement_feedback}

📊 Recommendation: {evaluation.recommendation}
{'• Practice this phrase again' if evaluation.recommendation == 'REPEAT' else 
 '• Try an easier phrase' if evaluation.recommendation == 'SIMPLIFY' else 
 '• Ready for a harder challenge!' if evaluation.recommendation == 'COMPLEXIFY' else
 '• Try a different phrase at this difficulty level' if evaluation.recommendation == 'CURRENT_COMPLEXITY_NEW_PHRASE' else
 '• Continue practicing'}"""
    
    def _on_autonomy_note_on(self, note):
        """Called when the autonomous player starts a note - begin blue bar in piano roll"""
        if hasattr(self, 'piano_roll') and self.piano_roll:
            # Start blue bar for autonomy note
            self.piano_roll.autonomy_note_on(note.pitch, note.velocity)
            self.logger.debug(f"🔵 Autonomy note started: MIDI {note.pitch}, vel {note.velocity}")
    
    def _on_autonomy_note_off(self, note):
        """Called when the autonomous player ends a note - complete blue bar in piano roll"""
        if hasattr(self, 'piano_roll') and self.piano_roll:
            # End blue bar for autonomy note
            self.piano_roll.autonomy_note_off(note.pitch)
            self.logger.debug(f"🔵 Autonomy note ended: MIDI {note.pitch}")
