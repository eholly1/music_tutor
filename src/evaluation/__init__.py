"""
Performance evaluation module

This module contains algorithms for evaluating user performance,
including pitch accuracy, timing analysis, and adaptive difficulty.
"""

from .phrase_analyzer import PhraseAnalyzer, PhraseAnalysis, analyze_phrase_to_json

__all__ = ['PhraseAnalyzer', 'PhraseAnalysis', 'analyze_phrase_to_json']
