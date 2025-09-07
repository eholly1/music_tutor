"""
Music theory and phrase representation module

This module contains classes and utilities for representing
musical concepts like phrases, notes, scales, and theory.
"""

from .phrase import MusicalNote, Phrase, create_simple_scale_phrase, create_chord_phrase
from .library import PhraseLibrary, create_scale_phrase_library
from .phrase_player import PhrasePlayer, AutonomousPhrasePlayer
from .listening_manager import PhraseListeningManager, SessionState, ListeningConfig, SessionEvent

__all__ = [
    'MusicalNote',
    'Phrase', 
    'create_simple_scale_phrase',
    'create_chord_phrase',
    'PhraseLibrary',
    'create_scale_phrase_library',
    'PhrasePlayer',
    'AutonomousPhrasePlayer',
    'PhraseListeningManager',
    'SessionState',
    'ListeningConfig',
    'SessionEvent'
]
