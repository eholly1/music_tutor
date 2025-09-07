#!/usr/bin/env python3
"""
Test Claude Integration Demo

This demo tests the Claude AI evaluation system by simulating
a simple call-and-response session with Claude feedback.
"""

import os
import sys
import time

# Add the src directory to Python path for imports
sys.path.append('/Users/sage/Desktop/music_trainer/src')

from music.phrase import Phrase, MusicalNote
from evaluation.claude_evaluator import ClaudeEvaluator


def create_simple_target_phrase():
    """Create a simple 4-note target phrase (C-D-E-F)"""
    notes = [
        MusicalNote(pitch=60, start_time=0.0, duration=1.0, velocity=80),  # C4
        MusicalNote(pitch=62, start_time=1.0, duration=1.0, velocity=80),  # D4  
        MusicalNote(pitch=64, start_time=2.0, duration=1.0, velocity=80),  # E4
        MusicalNote(pitch=65, start_time=3.0, duration=1.0, velocity=80),  # F4
    ]
    
    metadata = {
        'id': 'test_phrase_001',
        'name': 'Simple C Major Scale Segment',
        'style': 'modal_jazz',
        'difficulty': 1,
        'key': 'C_major',
        'tempo': 120,
        'bars': 1,
        'time_signature': (4, 4)
    }
    
    return Phrase(notes, metadata)


def create_student_response_good():
    """Create a good student response (C-D-E-F with slight timing differences)"""
    notes = [
        MusicalNote(pitch=60, start_time=0.1, duration=0.9, velocity=75),  # C4 (slightly late start)
        MusicalNote(pitch=62, start_time=1.0, duration=1.0, velocity=80),  # D4 (perfect)
        MusicalNote(pitch=64, start_time=2.1, duration=0.8, velocity=85),  # E4 (slightly late, shorter)
        MusicalNote(pitch=65, start_time=3.0, duration=1.0, velocity=80),  # F4 (perfect)
    ]
    
    metadata = {
        'id': 'student_response_001',
        'name': 'Student Response',
        'style': 'student_response',
        'difficulty': 1,
        'tempo': 120,
        'bars': 1,
        'time_signature': (4, 4)
    }
    
    return Phrase(notes, metadata)


def create_student_response_poor():
    """Create a poor student response (wrong notes, incomplete)"""
    notes = [
        MusicalNote(pitch=60, start_time=0.0, duration=1.0, velocity=60),  # C4 (correct)
        MusicalNote(pitch=61, start_time=1.2, duration=0.8, velocity=70),  # C#4 (wrong note, late)
        # Missing E4 and F4 entirely
    ]
    
    metadata = {
        'id': 'student_response_002', 
        'name': 'Student Response',
        'style': 'student_response',
        'difficulty': 1,
        'tempo': 120,
        'bars': 1,
        'time_signature': (4, 4)
    }
    
    return Phrase(notes, metadata)


def main():
    print("🎵 Claude AI Evaluation Demo")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set your Claude API key with:")
        print("export ANTHROPIC_API_KEY='your-api-key-here'")
        return
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    # Initialize Claude evaluator
    evaluator = ClaudeEvaluator(api_key=api_key)
    
    if not evaluator.is_available():
        print("❌ Claude evaluator not available")
        return
    
    print("✅ Claude evaluator initialized")
    
    # Create test phrases
    target_phrase = create_simple_target_phrase()
    good_response = create_student_response_good()
    poor_response = create_student_response_poor()
    
    print(f"\\n🎯 Target Phrase: {target_phrase.metadata['name']}")
    print(f"   Notes: {len(target_phrase.notes)} ({[n.pitch for n in target_phrase.notes]})")
    
    # Test 1: Good student response
    print(f"\\n📝 Test 1: Good Student Response")
    print(f"   Notes: {len(good_response.notes)} ({[n.pitch for n in good_response.notes]})")
    print("   🔄 Evaluating with Claude...")
    
    evaluation1 = evaluator.evaluate_phrase(
        target_phrase=target_phrase,
        student_phrase=good_response,
        difficulty_level=1,
        musical_style="modal_jazz"
    )
    
    if evaluation1:
        print(f"   🎭 Grade: {evaluation1.grade}")
        print(f"   ✅ Positive: {evaluation1.positive_feedback}")
        print(f"   🎯 Improvement: {evaluation1.improvement_feedback}")
        print(f"   📊 Recommendation: {evaluation1.recommendation}")
        print(f"   💡 Confidence: {int(evaluation1.confidence * 100)}%")
    else:
        print("   ❌ Evaluation failed")
    
    # Test 2: Poor student response
    print(f"\\n📝 Test 2: Poor Student Response")
    print(f"   Notes: {len(poor_response.notes)} ({[n.pitch for n in poor_response.notes]})")
    print("   🔄 Evaluating with Claude...")
    
    evaluation2 = evaluator.evaluate_phrase(
        target_phrase=target_phrase,
        student_phrase=poor_response,
        difficulty_level=1,
        musical_style="modal_jazz"
    )
    
    if evaluation2:
        print(f"   🎭 Grade: {evaluation2.grade}")
        print(f"   ✅ Positive: {evaluation2.positive_feedback}")
        print(f"   🎯 Improvement: {evaluation2.improvement_feedback}")
        print(f"   📊 Recommendation: {evaluation2.recommendation}")
        print(f"   💡 Confidence: {int(evaluation2.confidence * 100)}%")
    else:
        print("   ❌ Evaluation failed")
    
    # Test 3: Fallback evaluation (when Claude unavailable)
    print(f"\\n📝 Test 3: Fallback Evaluation")
    fallback = evaluator.get_fallback_evaluation(target_phrase, good_response)
    print(f"   🎭 Grade: {fallback.grade}")
    print(f"   ✅ Positive: {fallback.positive_feedback}")
    print(f"   🎯 Improvement: {fallback.improvement_feedback}")
    print(f"   📊 Recommendation: {fallback.recommendation}")
    print(f"   💡 Confidence: {int(fallback.confidence * 100)}%")
    
    print(f"\\n🎉 Claude integration demo completed!")


if __name__ == "__main__":
    main()
