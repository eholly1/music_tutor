#!/usr/bin/env python3
"""
Phrase Analyzer - Phase 5A Implementation

Converts musical phrases into comprehensive JSON descriptions for AI evaluation.
This system analyzes both bot phrases and student responses, extracting musical
features like pitch patterns, rhythmic structure, and dynamic expression.
"""

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from music.phrase import Phrase, MusicalNote
from utils.logger import get_logger


@dataclass
class PhraseAnalysis:
    """Structured analysis of a musical phrase"""
    phrase_metadata: Dict[str, Any]
    note_analysis: List[Dict[str, Any]]
    rhythmic_analysis: Dict[str, Any]
    melodic_analysis: Dict[str, Any]
    dynamic_analysis: Dict[str, Any]
    musical_features: Dict[str, Any]


class PhraseAnalyzer:
    """
    Comprehensive musical phrase analyzer for LLM evaluation.
    
    Converts Phrase objects into detailed JSON descriptions that capture
    all relevant musical information for AI assessment.
    """
    
    def __init__(self):
        self.logger = get_logger()
        
        # MIDI note name mapping
        self.note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    def analyze_phrase(self, phrase: Phrase, context: Optional[Dict[str, Any]] = None) -> PhraseAnalysis:
        """
        Create comprehensive analysis of a musical phrase.
        
        Args:
            phrase: The musical phrase to analyze
            context: Optional context information (BPM, session info, etc.)
            
        Returns:
            PhraseAnalysis object with complete musical analysis
        """
        self.logger.debug(f"Analyzing phrase: {phrase.name}")
        
        # Analyze different aspects of the phrase
        phrase_metadata = self._analyze_metadata(phrase, context)
        note_analysis = self._analyze_notes(phrase.notes)
        rhythmic_analysis = self._analyze_rhythm(phrase.notes, phrase)
        melodic_analysis = self._analyze_melody(phrase.notes)
        dynamic_analysis = self._analyze_dynamics(phrase.notes)
        musical_features = self._extract_musical_features(phrase.notes, phrase)
        
        return PhraseAnalysis(
            phrase_metadata=phrase_metadata,
            note_analysis=note_analysis,
            rhythmic_analysis=rhythmic_analysis,
            melodic_analysis=melodic_analysis,
            dynamic_analysis=dynamic_analysis,
            musical_features=musical_features
        )
    
    def to_json(self, analysis: PhraseAnalysis, pretty: bool = True) -> str:
        """
        Convert phrase analysis to JSON string.
        
        Args:
            analysis: PhraseAnalysis object
            pretty: Whether to format JSON with indentation
            
        Returns:
            JSON string representation
        """
        data = {
            "phrase_metadata": analysis.phrase_metadata,
            "note_analysis": analysis.note_analysis,
            "rhythmic_analysis": analysis.rhythmic_analysis,
            "melodic_analysis": analysis.melodic_analysis,
            "dynamic_analysis": analysis.dynamic_analysis,
            "musical_features": analysis.musical_features
        }
        
        if pretty:
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return json.dumps(data, ensure_ascii=False)
    
    def _analyze_metadata(self, phrase: Phrase, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract phrase metadata and context information"""
        metadata = {
            "phrase_info": {
                "id": phrase.id,
                "name": phrase.name,
                "style": phrase.style,
                "difficulty": phrase.difficulty,
                "key": phrase.key,
                "tempo": phrase.tempo,
                "bars": phrase.bars,
                "time_signature": phrase.time_signature,
                "total_beats": phrase.get_duration_beats(),
                "note_count": len(phrase.notes)
            }
        }
        
        if context:
            metadata["context"] = context
            
        return metadata
    
    def _analyze_notes(self, notes: List[MusicalNote]) -> List[Dict[str, Any]]:
        """Analyze individual notes with detailed information"""
        note_analysis = []
        
        for i, note in enumerate(notes):
            # Convert MIDI pitch to note name
            octave = (note.pitch // 12) - 1
            note_name = self.note_names[note.pitch % 12]
            full_note_name = f"{note_name}{octave}"
            
            # Calculate end time
            end_time = note.start_time + note.duration
            
            note_data = {
                "index": i,
                "midi_pitch": note.pitch,
                "note_name": full_note_name,
                "octave": octave,
                "start_beat": note.start_time,
                "end_beat": end_time,
                "duration_beats": note.duration,
                "velocity": note.velocity,
                "velocity_category": self._categorize_velocity(note.velocity),
                "pitch_class": note.pitch % 12,
                "position_in_phrase": "start" if note.start_time == 0 else "middle" if end_time < max(n.start_time + n.duration for n in notes) else "end"
            }
            
            note_analysis.append(note_data)
        
        return note_analysis
    
    def _analyze_rhythm(self, notes: List[MusicalNote], phrase: Phrase) -> Dict[str, Any]:
        """Analyze rhythmic patterns and timing"""
        if not notes:
            return {"error": "No notes to analyze"}
        
        # Calculate inter-onset intervals (time between note starts)
        onset_intervals = []
        for i in range(1, len(notes)):
            interval = notes[i].start_time - notes[i-1].start_time
            onset_intervals.append(interval)
        
        # Note durations
        durations = [note.duration for note in notes]
        
        # Beat positions
        beat_positions = [note.start_time % 1.0 for note in notes]  # Position within beat (0.0-1.0)
        
        # Analyze syncopation (notes starting off strong beats)
        syncopated_notes = sum(1 for pos in beat_positions if pos != 0.0)
        
        return {
            "total_notes": len(notes),
            "note_durations": durations,
            "onset_intervals": onset_intervals,
            "beat_positions": beat_positions,
            "average_duration": sum(durations) / len(durations) if durations else 0,
            "duration_variety": len(set(durations)),
            "syncopated_notes": syncopated_notes,
            "syncopation_ratio": syncopated_notes / len(notes) if notes else 0,
            "rhythmic_density": len(notes) / phrase.get_duration_beats(),
            "starts_on_beat": sum(1 for pos in beat_positions if pos == 0.0),
            "timing_analysis": {
                "consistent_timing": len(set(round(interval, 2) for interval in onset_intervals)) <= 2 if onset_intervals else True,
                "rhythmic_pattern": self._identify_rhythmic_pattern(onset_intervals)
            }
        }
    
    def _analyze_melody(self, notes: List[MusicalNote]) -> Dict[str, Any]:
        """Analyze melodic patterns and movement"""
        if len(notes) < 2:
            return {"error": "Need at least 2 notes for melodic analysis"}
        
        # Calculate intervals between consecutive notes
        intervals = []
        for i in range(1, len(notes)):
            interval = notes[i].pitch - notes[i-1].pitch
            intervals.append(interval)
        
        # Calculate pitch range
        pitches = [note.pitch for note in notes]
        pitch_range = max(pitches) - min(pitches)
        
        # Analyze melodic contour
        contour = []
        for interval in intervals:
            if interval > 0:
                contour.append("up")
            elif interval < 0:
                contour.append("down")
            else:
                contour.append("same")
        
        # Identify melodic direction tendencies
        up_moves = contour.count("up")
        down_moves = contour.count("down")
        same_moves = contour.count("same")
        
        return {
            "pitch_range": pitch_range,
            "lowest_note": min(pitches),
            "highest_note": max(pitches),
            "intervals": intervals,
            "interval_sizes": [abs(i) for i in intervals],
            "melodic_contour": contour,
            "direction_analysis": {
                "ascending_moves": up_moves,
                "descending_moves": down_moves,
                "repeated_notes": same_moves,
                "overall_direction": "ascending" if up_moves > down_moves else "descending" if down_moves > up_moves else "static"
            },
            "leap_analysis": {
                "small_steps": sum(1 for i in intervals if abs(i) <= 2),  # Half/whole steps
                "large_steps": sum(1 for i in intervals if 3 <= abs(i) <= 4),  # Minor/major thirds
                "leaps": sum(1 for i in intervals if abs(i) >= 5),  # Perfect fourth or larger
            },
            "pitch_repetition": len(pitches) - len(set(pitches)),
            "average_pitch": sum(pitches) / len(pitches)
        }
    
    def _analyze_dynamics(self, notes: List[MusicalNote]) -> Dict[str, Any]:
        """Analyze dynamic expression and velocity patterns"""
        if not notes:
            return {"error": "No notes to analyze"}
        
        velocities = [note.velocity for note in notes]
        
        # Categorize velocities
        velocity_categories = [self._categorize_velocity(v) for v in velocities]
        category_counts = {}
        for cat in velocity_categories:
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Analyze dynamic changes
        dynamic_changes = []
        for i in range(1, len(velocities)):
            change = velocities[i] - velocities[i-1]
            dynamic_changes.append(change)
        
        return {
            "velocity_range": max(velocities) - min(velocities),
            "average_velocity": sum(velocities) / len(velocities),
            "min_velocity": min(velocities),
            "max_velocity": max(velocities),
            "velocity_categories": category_counts,
            "dynamic_changes": dynamic_changes,
            "has_crescendo": any(change > 10 for change in dynamic_changes),
            "has_diminuendo": any(change < -10 for change in dynamic_changes),
            "dynamic_variety": len(set(velocities)),
            "consistent_dynamics": len(set(velocities)) <= 2
        }
    
    def _extract_musical_features(self, notes: List[MusicalNote], phrase: Phrase) -> Dict[str, Any]:
        """Extract high-level musical features and characteristics"""
        if not notes:
            return {"error": "No notes to analyze"}
        
        # Calculate musical characteristics
        note_density = len(notes) / phrase.get_duration_beats()
        
        # Analyze chord/harmony potential (notes playing simultaneously)
        simultaneous_notes = self._find_simultaneous_notes(notes)
        
        # Analyze rest patterns
        rest_analysis = self._analyze_rests(notes, phrase)
        
        return {
            "musical_style_indicators": {
                "note_density": note_density,
                "density_category": "sparse" if note_density < 1 else "moderate" if note_density < 2 else "dense",
                "harmonic_content": len(simultaneous_notes),
                "monophonic": len(simultaneous_notes) == 0,
                "polyphonic": len(simultaneous_notes) > 0
            },
            "phrase_structure": {
                "starts_immediately": notes[0].start_time == 0.0,
                "ends_early": max(note.start_time + note.duration for note in notes) < phrase.get_duration_beats(),
                "uses_full_phrase": abs(max(note.start_time + note.duration for note in notes) - phrase.get_duration_beats()) < 0.1
            },
            "technical_features": {
                "simultaneous_notes": simultaneous_notes,
                "rest_patterns": rest_analysis,
                "note_overlap": self._calculate_note_overlap(notes)
            },
            "complexity_metrics": {
                "rhythmic_complexity": self._calculate_rhythmic_complexity(notes),
                "melodic_complexity": self._calculate_melodic_complexity(notes),
                "overall_complexity": "simple" if note_density < 1 and len(set(note.duration for note in notes)) <= 2 else "complex"
            }
        }
    
    def _categorize_velocity(self, velocity: int) -> str:
        """Categorize MIDI velocity into musical dynamics"""
        if velocity < 30:
            return "pp"  # pianissimo
        elif velocity < 50:
            return "p"   # piano
        elif velocity < 70:
            return "mp"  # mezzo-piano
        elif velocity < 90:
            return "mf"  # mezzo-forte
        elif velocity < 110:
            return "f"   # forte
        else:
            return "ff"  # fortissimo
    
    def _identify_rhythmic_pattern(self, intervals: List[float]) -> str:
        """Identify common rhythmic patterns"""
        if not intervals:
            return "single_note"
        
        if len(set(round(i, 2) for i in intervals)) == 1:
            return "even_rhythm"
        elif all(i <= 1.0 for i in intervals):
            return "subdivision_pattern"
        else:
            return "mixed_rhythm"
    
    def _find_simultaneous_notes(self, notes: List[MusicalNote]) -> List[Dict[str, Any]]:
        """Find groups of notes that play simultaneously (chords)"""
        simultaneous_groups = []
        
        for i, note1 in enumerate(notes):
            group = [note1]
            for j, note2 in enumerate(notes):
                if i != j:
                    # Check if notes overlap in time
                    if (note1.start_time < note2.start_time + note2.duration and 
                        note2.start_time < note1.start_time + note1.duration):
                        group.append(note2)
            
            if len(group) > 1:
                group_data = {
                    "start_time": min(note.start_time for note in group),
                    "pitches": [note.pitch for note in group],
                    "note_count": len(group)
                }
                if group_data not in simultaneous_groups:
                    simultaneous_groups.append(group_data)
        
        return simultaneous_groups
    
    def _analyze_rests(self, notes: List[MusicalNote], phrase: Phrase) -> Dict[str, Any]:
        """Analyze rest patterns between notes"""
        if len(notes) < 2:
            return {"rest_count": 0, "total_rest_duration": 0}
        
        # Sort notes by start time
        sorted_notes = sorted(notes, key=lambda n: n.start_time)
        
        rests = []
        for i in range(len(sorted_notes) - 1):
            current_end = sorted_notes[i].start_time + sorted_notes[i].duration
            next_start = sorted_notes[i + 1].start_time
            
            if next_start > current_end:
                rest_duration = next_start - current_end
                rests.append(rest_duration)
        
        return {
            "rest_count": len(rests),
            "rest_durations": rests,
            "total_rest_duration": sum(rests),
            "average_rest_duration": sum(rests) / len(rests) if rests else 0,
            "has_rests": len(rests) > 0
        }
    
    def _calculate_note_overlap(self, notes: List[MusicalNote]) -> float:
        """Calculate percentage of notes that overlap with others"""
        if len(notes) <= 1:
            return 0.0
        
        overlapping_count = 0
        for i, note1 in enumerate(notes):
            for j, note2 in enumerate(notes):
                if i != j:
                    if (note1.start_time < note2.start_time + note2.duration and 
                        note2.start_time < note1.start_time + note1.duration):
                        overlapping_count += 1
                        break  # Count each note only once
        
        return overlapping_count / len(notes)
    
    def _calculate_rhythmic_complexity(self, notes: List[MusicalNote]) -> str:
        """Calculate rhythmic complexity based on timing patterns"""
        durations = [note.duration for note in notes]
        unique_durations = len(set(durations))
        
        if unique_durations == 1:
            return "simple"
        elif unique_durations <= 3:
            return "moderate"
        else:
            return "complex"
    
    def _calculate_melodic_complexity(self, notes: List[MusicalNote]) -> str:
        """Calculate melodic complexity based on pitch patterns"""
        if len(notes) < 2:
            return "simple"
        
        pitches = [note.pitch for note in notes]
        pitch_range = max(pitches) - min(pitches)
        unique_pitches = len(set(pitches))
        
        if pitch_range <= 5 and unique_pitches <= 3:
            return "simple"
        elif pitch_range <= 12 and unique_pitches <= 6:
            return "moderate"
        else:
            return "complex"


def analyze_phrase_to_json(phrase: Phrase, context: Optional[Dict[str, Any]] = None, pretty: bool = True) -> str:
    """
    Convenience function to analyze a phrase and return JSON string.
    
    Args:
        phrase: The musical phrase to analyze
        context: Optional context information
        pretty: Whether to format JSON with indentation
        
    Returns:
        JSON string representation of the phrase analysis
    """
    analyzer = PhraseAnalyzer()
    analysis = analyzer.analyze_phrase(phrase, context)
    return analyzer.to_json(analysis, pretty)
