"""
Audio synthesis and playback module

This module handles audio generation, synthesis, and playback
for musical phrases and feedback sounds.
"""

from .engine import AudioEngine
from .synthesizer import AudioSynthesizer, ADSREnvelope
from .player import AudioPlayer

__all__ = ['AudioEngine', 'AudioSynthesizer', 'ADSREnvelope', 'AudioPlayer']
