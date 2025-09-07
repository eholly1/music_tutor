# Implementation Plan - Music Trainer MVP

## Overview
This document outlines the phased development approach for building the Music Trainer MVP, focusing on delivering a functional call-and-response practice bot with MIDI input and audio feedback.

## Phase 1: Foundation Setup (Week 1)

### Project Structure
```
music_trainer/
├── src/
│   ├── __init__.py
│   ├── main.py              # Application entry point
│   ├── midi/
│   │   ├── __init__.py
│   │   ├── input_handler.py # MIDI controller interface
│   │   └── note_processor.py # Convert MIDI to musical data
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── synthesizer.py   # Audio generation
│   │   └── player.py        # Audio playback
│   ├── music/
│   │   ├── __init__.py
│   │   ├── phrase.py        # Musical phrase representation
│   │   ├── library.py       # Phrase storage and retrieval
│   │   └── theory.py        # Music theory utilities
│   ├── evaluation/
│   │   ├── __init__.py
│   │   ├── pitch_matcher.py # Pitch accuracy assessment
│   │   └── timing_analyzer.py # Rhythm evaluation
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py   # Primary interface
│   │   ├── practice_view.py # Practice session display
│   │   └── feedback_display.py # Visual feedback
│   └── utils/
│       ├── __init__.py
│       ├── config.py        # Application configuration
│       └── logger.py        # Logging utilities
├── data/
│   ├── phrases/
│   │   └── modal_jazz.json  # Initial phrase library
│   └── user_progress.db     # SQLite database
├── tests/
│   ├── test_midi.py
│   ├── test_audio.py
│   └── test_evaluation.py
├── requirements.txt
├── setup.py
└── README.md
```

### Key Deliverables
- [x] Project repository setup
- [x] Development environment configuration
- [x] Basic project structure
- [x] Dependency management (`requirements.txt`)
- [x] Initial documentation

### Dependencies
```txt
python-rtmidi==1.4.9
sounddevice==0.4.6
numpy==1.24.3
music21==8.3.0
tkinter  # Built-in with Python
sqlite3  # Built-in with Python
pytest==7.4.0
```

## Phase 2: MIDI Input System (Week 2)

### Core Components

#### 2.1 MIDI Controller Detection ✅
- [x] Auto-detect connected USB MIDI devices
- [x] Handle device connection/disconnection
- [x] User selection interface for multiple devices

#### 2.2 Real-time MIDI Processing ✅
- [x] Capture MIDI note on/off events
- [x] Convert MIDI data to musical notation
- [x] Handle velocity and timing information
- [x] Buffer management for phrase recording

### Technical Challenges
- Low-latency MIDI input processing
- Handling MIDI jitter and timing variations
- Graceful device disconnection handling

## Phase 3: Audio Generation & Playback (Week 3)

### Audio Synthesis Engine

#### 3.1 Simple Synthesizer ✅
- [x] Basic waveform generation (sine wave)
- [x] ADSR envelope implementation
- [x] Polyphonic playback capability
- [x] Real-time audio streaming
- [x] Integration with MIDI input for live synthesis

#### 3.2 Piano Roll Visualization ✅
- [x] Real-time scrolling piano roll display
- [x] Note visualization with velocity-based coloring
- [x] Piano key reference lines and octave labels
- [x] Integration with MIDI input for live note display
- [x] Smooth 60 FPS animation
- [x] Positioned at bottom of application window

```python
class PianoRollVisualization:
    def __init__(self, parent, width=800, height=200):
        self.canvas = tk.Canvas(parent, width=width, height=height, bg='black')
        self.width = width
        self.height = height
        self.scroll_speed = 2  # pixels per frame
        self.notes_display = []  # Active note visualizations
        
    def add_note(self, midi_note, velocity, duration):
        """Add a new note visualization to the scrolling reel"""
        note_height = self._calculate_note_height(midi_note)
        note_width = self._calculate_note_width(duration)
        
        # Create red line representing the played note
        note_viz = {
            'midi_note': midi_note,
            'x_position': self.width,  # Start from right edge
            'y_position': note_height,
            'width': note_width,
            'velocity': velocity,
            'canvas_id': None
        }
        
        self.notes_display.append(note_viz)
        self._draw_note(note_viz)
    
    def update_scroll(self):
        """Update animation frame - scroll notes from right to left"""
        for note in self.notes_display[:]:
            note['x_position'] -= self.scroll_speed
            
            # Remove notes that have scrolled off the left edge
            if note['x_position'] + note['width'] < 0:
                self.canvas.delete(note['canvas_id'])
                self.notes_display.remove(note)
            else:
                # Update position on canvas
                self.canvas.coords(note['canvas_id'], 
                                 note['x_position'], note['y_position'],
                                 note['x_position'] + note['width'], note['y_position'] + 3)
    
    def _calculate_note_height(self, midi_note):
        """Map MIDI note to vertical position (C2 to C5 range)"""
        # Map MIDI notes 36-72 (C2 to C5) across the height
        min_note = 36  # C2
        max_note = 72  # C5
        
        if midi_note < min_note:
            midi_note = min_note
        elif midi_note > max_note:
            midi_note = max_note
            
        note_range = max_note - min_note  # 36 semitones
        return self.height - ((midi_note - min_note) / note_range * (self.height - 20)) - 10
    
    def _calculate_note_width(self, duration):
        """Convert note duration to pixel width"""
        return max(5, int(duration * 50))  # Minimum 5px width
    
    def _draw_note(self, note_viz):
        """Draw red line representing the note"""
        canvas_id = self.canvas.create_rectangle(
            note_viz['x_position'], note_viz['y_position'],
            note_viz['x_position'] + note_viz['width'], note_viz['y_position'] + 3,
            fill='red', outline='red'
        )
        note_viz['canvas_id'] = canvas_id
```

#### 3.3 Beats
- [X] Background drummer with genre-specific drum loops
- [X] Customizable BPM in practice session options
- [X] Beat visualization in piano roll (solid lines on beats, dashed on downbeats)
- [X] 4/4 time signature for all genres
- [X] Supported genres: Modal Jazz, Blues, Folk

```python
class DrumEngine:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self.bpm = 100  # Default BPM set to 100
        self.genre = "jazz"
        self.is_playing = False
        self.beat_patterns = {
            'jazz': {'kick': [1, 3], 'snare': [2, 4], 'hihat': [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5]},
            'blues': {'kick': [1, 3], 'snare': [2, 4], 'hihat': [1, 2, 3, 4]},
            'rock': {'kick': [1, 2.5, 3], 'snare': [2, 4], 'hihat': [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5]},
            'funk': {'kick': [1, 1.5, 3, 4.5], 'snare': [2, 4], 'hihat': [1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5]}
        }
    
    def set_bpm(self, bpm):
        """Set the tempo for drum playback"""
        self.bpm = bpm
    
    def set_genre(self, genre):
        """Change drum pattern based on musical genre"""
        if genre in self.beat_patterns:
            self.genre = genre
    
    def start_drumming(self):
        """Begin drum loop playback"""
        self.is_playing = True
    
    def stop_drumming(self):
        """Stop drum loop playback"""
        self.is_playing = False

class PianoRollVisualization:
    def __init__(self, parent, width=800, height=200):
        self.canvas = tk.Canvas(parent, width=width, height=height, bg='black')
        self.width = width
        self.height = height
        self.scroll_speed = 2  # pixels per frame
        self.notes_display = []
        self.bpm = 100  # Default BPM set to 100
        self.pixels_per_beat = 60  # Visual spacing between beats
        
    def draw_beat_lines(self):
        """Draw beat grid lines - solid for beats, dashed for downbeats"""
        beat_spacing = self.pixels_per_beat
        
        # Clear existing beat lines
        self.canvas.delete("beat_line")
        
        # Draw beat lines across the canvas
        for x in range(0, self.width + beat_spacing, beat_spacing):
            beat_number = ((self.width - x) / beat_spacing) % 4 + 1
            
            if beat_number == 1:  # Downbeat (beat 1)
                self.canvas.create_line(x, 0, x, self.height, 
                                      fill='white', width=2, dash=(5, 5), tags="beat_line")
            else:  # Regular beats (2, 3, 4)
                self.canvas.create_line(x, 0, x, self.height, 
                                      fill='gray', width=1, tags="beat_line")
    
    def update_scroll(self):
        """Update animation frame - scroll notes and beat lines from right to left"""
        # Scroll notes
        for note in self.notes_display[:]:
            note['x_position'] -= self.scroll_speed
            
            if note['x_position'] + note['width'] < 0:
                self.canvas.delete(note['canvas_id'])
                self.notes_display.remove(note)
            else:
                self.canvas.coords(note['canvas_id'], 
                                 note['x_position'], note['y_position'],
                                 note['x_position'] + note['width'], note['y_position'] + 3)
        
        # Redraw beat lines to maintain scrolling effect
        self.draw_beat_lines()
```


## Phase 4: Musical Phrase Library (Week 4)

### Musical Phrase Library Development

#### 4.1 Phrase Data Structure
```python
class MusicalNote:
    def __init__(self, pitch, start_time, duration, velocity=80):
        self.pitch = pitch          # MIDI note number (0-127)
        self.start_time = start_time # Beat position within phrase (0.0 = start)
        self.duration = duration    # Note length in beats
        self.velocity = velocity    # Dynamics (0-127)

class Phrase:
    def __init__(self, notes, metadata):
        self.notes = notes          # List of MusicalNote objects
        self.metadata = {
            'style': 'modal_jazz',
            'difficulty': 2,        # 1-5 scale
            'key': 'D_dorian',
            'tempo': 120,
            'bars': 2,              # 1, 2, or 4 bars
            'time_signature': (4, 4),
            'description': 'Simple dorian phrase'
        }
    
    def get_duration_beats(self):
        """Return total duration in beats"""
        return self.metadata['bars'] * self.metadata['time_signature'][0]
    
    def get_duration_seconds(self, bpm):
        """Return total duration in seconds at given BPM"""
        beats_per_second = bpm / 60.0
        return self.get_duration_beats() / beats_per_second
```

#### 4.2 Phrase Library Management
```python
class PhraseLibrary:
    def __init__(self):
        self.phrases = {}  # Organized by style -> difficulty -> phrases
        self.load_phrase_data()
    
    def load_phrase_data(self):
        """Load phrases from JSON files"""
        pass
    
    def get_phrase(self, style, difficulty, bars=None):
        """Retrieve appropriate phrase based on criteria"""
        pass
    
    def filter_phrases(self, style=None, difficulty=None, bars=None):
        """Get list of phrases matching criteria"""
        pass
    
    def add_phrase(self, phrase):
        """Add new phrase to library"""
        pass
```

#### 4.3 Phrase Playback Engine
```python
class PhrasePlayer:
    def __init__(self, audio_engine):
        self.audio_engine = audio_engine
        self.current_phrase = None
        self.is_playing = False
        self.playback_thread = None
    
    def play_phrase(self, phrase, bpm=None):
        """Play a musical phrase through audio synthesis"""
        self.current_phrase = phrase
        effective_bpm = bpm or phrase.metadata['tempo']
        
        # Schedule note events based on timing
        for note in phrase.notes:
            start_time = note.start_time * (60.0 / effective_bpm)
            self._schedule_note(note, start_time)
    
    def _schedule_note(self, note, delay):
        """Schedule a note to play after specified delay"""
        pass
    
    def stop_playback(self):
        """Stop current phrase playback"""
        pass
```

#### 4.4 Phrase Listening States
```python
class PhraseListeningManager:
    def __init__(self, midi_handler, audio_engine):
        self.midi_handler = midi_handler
        self.audio_engine = audio_engine
        self.phrase_player = PhrasePlayer(audio_engine)
        self.current_state = 'idle'
        self.target_phrase = None
        self.student_recording = []
        self.listening_start_time = None
        
    def start_call_response_session(self, phrase):
        """Begin call-and-response with given phrase"""
        self.target_phrase = phrase
        self.current_state = 'playing_call'
        self.phrase_player.play_phrase(phrase)
        
        # Schedule transition to listening state
        phrase_duration = phrase.get_duration_seconds(phrase.metadata['tempo'])
        self._schedule_state_change('waiting_for_response', phrase_duration + 1.0)
    
    def _on_state_change(self, new_state):
        """Handle state transitions"""
        self.current_state = new_state
        
        if new_state == 'waiting_for_response':
            self._start_listening_for_student()
        elif new_state == 'recording_response':
            self._start_recording_phrase()
        elif new_state == 'evaluating_response':
            self._evaluate_student_response()
    
    def _start_listening_for_student(self):
        """Wait for student to start playing"""
        self.student_recording = []
        self.midi_handler.set_note_callback(self._on_student_note)
    
    def _on_student_note(self, midi_note, velocity, is_note_on):
        """Handle incoming MIDI from student"""
        if self.current_state == 'waiting_for_response' and is_note_on:
            # First note starts the recording
            self.current_state = 'recording_response'
            self.listening_start_time = time.time()
            
            # Schedule end of recording based on target phrase duration
            target_duration = self.target_phrase.get_duration_seconds(
                self.target_phrase.metadata['tempo'])
            self._schedule_state_change('evaluating_response', target_duration)
        
        if self.current_state == 'recording_response':
            # Record the note with timestamp
            timestamp = time.time() - self.listening_start_time
            self.student_recording.append({
                'pitch': midi_note,
                'velocity': velocity,
                'timestamp': timestamp,
                'is_note_on': is_note_on
            })
    
    def _evaluate_student_response(self):
        """Process recorded student phrase for evaluation"""
        # Convert raw MIDI events to structured phrase
        student_phrase = self._convert_recording_to_phrase()
        
        # TODO: Pass to evaluation engine in Phase 5
        print(f"Student played {len(student_phrase.notes)} notes")
        
        # Return to idle state
        self.current_state = 'idle'
    
    def _convert_recording_to_phrase(self):
        """Convert MIDI recording to Phrase object"""
        # Process note on/off pairs into notes with durations
        notes = []
        active_notes = {}  # Track note-on events waiting for note-off
        
        for event in self.student_recording:
            if event['is_note_on']:
                active_notes[event['pitch']] = event
            else:
                if event['pitch'] in active_notes:
                    start_event = active_notes[event['pitch']]
                    note = MusicalNote(
                        pitch=event['pitch'],
                        start_time=start_event['timestamp'],
                        duration=event['timestamp'] - start_event['timestamp'],
                        velocity=start_event['velocity']
                    )
                    notes.append(note)
                    del active_notes[event['pitch']]
        
        # Create phrase from recorded notes
        return Phrase(notes, {
            'style': 'student_response',
            'difficulty': 1,
            'bars': self.target_phrase.metadata['bars'],
            'tempo': self.target_phrase.metadata['tempo']
        })
```

### Implementation Strategy
1. **Start Simple**: Begin with single-note phrases for testing
2. **Phrase Durations**: Support 1-bar (4 beats), 2-bar (8 beats), and 4-bar (16 beats)
3. **Timing Assumptions**: Student response duration matches bot phrase duration
4. **State Management**: Clear transitions between bot playing and student recording

## Phase 5: LLM-Based Evaluation Engine (Week 5)

### AI-Powered Performance Assessment

This phase implements an innovative evaluation system that uses Claude AI to provide musical feedback, replacing traditional rule-based evaluation with intelligent, context-aware assessment.

#### 5.1 MIDI-to-JSON Phrase Summarizer
Create a comprehensive analysis system that converts musical phrases into structured JSON descriptions for AI evaluation:

**Core Functionality:**
- **Note-by-note Analysis**: Extract pitch, timing, velocity, and position data for each note
- **Rhythmic Pattern Analysis**: Identify note durations, inter-onset intervals, and rhythmic complexity
- **Melodic Contour Analysis**: Analyze pitch movement, intervals, and melodic direction
- **Dynamic Expression Analysis**: Evaluate velocity patterns and dynamic variation
- **Contextual Metadata**: Include tempo, key signature, musical style, and phrase duration

**Output Format**: Structured JSON that provides Claude with comprehensive musical context for evaluation.

#### 5.2 Claude API Integration
Implement the interface to Anthropic's Claude API for intelligent musical evaluation:

**Evaluation Process:**
- **Prompt Engineering**: Carefully crafted prompts that position Claude as an expert music teacher
- **Structured Input**: Send both target phrase and student performance analyses to Claude
- **Contextual Awareness**: Include difficulty level, musical style, and session progress in evaluation context
- **Structured Output**: Receive JSON-formatted evaluation with scores, feedback, and recommendations
- **Error Handling**: Graceful fallback strategies for API failures

**Evaluation Categories:**
- Pitch accuracy with specific feedback
- Rhythm accuracy and timing assessment
- Musical expression and dynamics
- Overall performance score (0-100)
- Encouraging, actionable improvement suggestions
- Recognition of positive aspects

#### 5.3 Adaptive Difficulty Recommendations
Leverage Claude's intelligence for personalized learning progression:

**Difficulty Assessment:**
- **Performance History Analysis**: Review recent evaluation scores and trends
- **Skill-Specific Recommendations**: Identify areas for focused improvement
- **Adaptive Progression**: Intelligent decisions to increase, decrease, or maintain difficulty
- **Learning Curve Consideration**: Account for individual learning patterns and pacing

**Recommendation System:**
- Analyze last 5 performance attempts
- Consider average scores and improvement trends
- Provide confidence ratings for difficulty changes
- Suggest specific focus areas for practice

#### 5.4 Evaluation Pipeline Integration
Create a complete evaluation workflow that connects all components:

**Pipeline Steps:**
1. **Analysis Phase**: Convert both target and student phrases to JSON format
2. **Evaluation Phase**: Send structured data to Claude for assessment
3. **Storage Phase**: Record evaluation history for adaptive learning
4. **Feedback Phase**: Present results to student in encouraging format
5. **Adaptation Phase**: Use performance data to adjust future challenges

**Session Management:**
- Maintain evaluation history across practice sessions
- Generate session summaries and progress tracking
- Provide performance trends and improvement metrics

### Implementation Strategy

#### Phase 5A: Basic JSON Analysis (Days 1-2)
**Objective**: Build the foundation for musical phrase analysis
- Implement comprehensive MIDI-to-JSON conversion system
- Create analysis algorithms for rhythm, pitch, and dynamics
- Design JSON schema that captures all relevant musical information
- Test analysis accuracy with sample phrases across different styles and difficulties
- Validate JSON output completeness and musical relevance

#### Phase 5B: Claude Integration (Days 3-4)
**Objective**: Establish AI evaluation capability
- Set up Anthropic API integration with proper authentication
- Implement core Claude communication system with error handling
- Design initial evaluation prompt template for musical assessment
- Create structured response parsing for consistent feedback format
- Test basic evaluation pipeline with simple musical examples
- Implement fallback evaluation system for API failures

#### Phase 5C: Prompt Engineering Iteration (Days 5-6)
**Objective**: Refine AI feedback quality to sound musically legitimate
- Test evaluation quality with diverse musical phrase examples
- Iterate on prompt specificity and musical terminology
- Refine feedback tone to be encouraging yet constructive
- Improve technical accuracy of musical observations
- Enhance actionable improvement suggestions
- Create prompt variants optimized for different difficulty levels
- Validate feedback quality against expert musical assessment

#### Phase 5D: Adaptive Difficulty Logic (Days 6-7)
**Objective**: Implement intelligent learning progression
- Design difficulty adjustment prompt system
- Create performance trend analysis algorithms
- Implement learning progression recommendations
- Test adaptive difficulty with simulated performance data
- Validate appropriate challenge progression for different skill levels
- Fine-tune difficulty thresholds and adjustment triggers

### Advantages of LLM-Based Approach

**Musical Intelligence**: Claude provides nuanced musical understanding that goes beyond simple accuracy metrics, considering musical context, style, and expression.

**Natural Language Feedback**: Students receive human-readable, encouraging feedback that sounds like it comes from a knowledgeable music teacher.

**Style Adaptability**: Can evaluate any musical style without requiring hard-coded rules for each genre or musical approach.

**Contextual Awareness**: Considers difficulty level, student progress, session history, and individual learning patterns when providing feedback.

**Iterative Improvement**: Prompts can be continuously refined based on feedback quality and musical accuracy.

**Comprehensive Assessment**: Evaluates multiple dimensions including pitch accuracy, rhythm precision, musical expression, and overall musicality.

### Success Metrics

**Evaluation Accuracy**: Claude feedback aligns with expert musical assessment and provides musically sound observations.

**Student Engagement**: Feedback is encouraging, constructive, and actionable, leading to improved practice motivation.

**Adaptive Progression**: Difficulty adjustments result in appropriate challenge levels that promote steady learning improvement.

**API Reliability**: Achieve >95% successful evaluation requests with robust error handling.

**Response Time**: Complete evaluations within 3-5 seconds to maintain smooth practice flow.

**Musical Legitimacy**: Feedback sounds authentic and knowledgeable to practicing musicians across different skill levels.

## Phase 6: User Interface (Week 6)

### GUI Components

#### 6.1 Main Application Window
- Device selection and connection status
- Practice session controls (start/stop/pause)
- Difficulty and style selection
- BPM slider (range: 60-180 BPM, default: 100 BPM)
- Progress tracking display

#### 6.2 Practice View
```python
class PracticeView:
    def __init__(self):
        self.phrase_display = PhraseNotation()
        self.feedback_panel = FeedbackDisplay()
        self.progress_bar = ProgressIndicator()
    
    def show_target_phrase(self, phrase):
        """Display the phrase user should play"""
        pass
    
    def show_user_attempt(self, recorded_phrase, evaluation):
        """Show what user played with feedback"""
        pass
```

#### 6.3 Visual Feedback System
- Musical notation display (simplified)
- Color-coded accuracy feedback
- Real-time note tracking during recording
- Progress indicators and statistics

### User Experience Flow
1. **Setup**: Device connection and configuration
2. **Style Selection**: Choose musical style and difficulty
3. **Practice Loop**:
   - Bot plays phrase
   - User attempts to replicate
   - Immediate feedback provided
   - Adaptive progression to next challenge
4. **Session Summary**: Performance statistics and progress

## Phase 7: Integration & Testing (Week 7)

### System Integration
- Component integration testing
- End-to-end practice session testing
- Performance optimization
- Cross-platform compatibility testing

### Testing Strategy
```python
# Unit Tests
test_midi_input_processing()
test_audio_synthesis_quality()
test_phrase_evaluation_accuracy()
test_adaptive_difficulty_logic()

# Integration Tests
test_complete_practice_session()
test_device_connection_handling()
test_audio_midi_synchronization()

# User Acceptance Tests
test_beginner_user_experience()
test_intermediate_practice_session()
test_device_compatibility()
```

## Phase 8: Polish & Documentation (Week 8)

### Final Deliverables
- Complete user documentation
- Installation and setup guides
- Troubleshooting documentation
- Code documentation and API reference

### Performance Optimizations
- Audio latency minimization
- MIDI processing efficiency
- Memory usage optimization
- Startup time improvement

## Technical Architecture Decisions

### Key Design Principles
1. **Modularity**: Clear separation of concerns between MIDI, audio, evaluation, and UI
2. **Real-time Performance**: Low-latency processing for responsive interaction
3. **Extensibility**: Architecture that supports future feature additions
4. **Cross-platform**: Works on Windows, macOS, and Linux
5. **User-friendly**: Intuitive interface requiring minimal setup

### Risk Mitigation
- **MIDI Compatibility**: Test with multiple controller types early
- **Audio Latency**: Implement efficient buffering strategies
- **Cross-platform Issues**: Regular testing on all target platforms
- **User Adoption**: Focus on simple, immediate value delivery

## Success Metrics

### MVP Success Criteria
- [ ] Successfully connects to common USB MIDI controllers
- [ ] Audio playback with <50ms latency
- [ ] Accurate pitch detection within 10 cents
- [ ] Rhythm evaluation within 50ms tolerance
- [ ] Smooth practice session experience for 10+ minute sessions
- [ ] Adaptive difficulty that responds appropriately to user performance

### Future Expansion Readiness
- Modular architecture supports phrase library expansion
- Evaluation engine can be enhanced with additional metrics
- Audio synthesis can be upgraded to higher quality instruments
- Interface can accommodate more complex musical concepts

This implementation plan provides a clear roadmap for delivering a functional MVP while establishing the foundation for the ultimate vision of an AI-powered music practice companion.
