"""
Claude AI-based musical phrase evaluation system

This module implements Phase 5 of the Music Trainer - using Claude AI to provide
intelligent, context-aware musical feedback instead of rule-based evaluation.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, Tuple, Callable, List
from dataclasses import dataclass

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    anthropic = None

from music.phrase import Phrase


@dataclass
class ClaudeEvaluation:
    """Structured evaluation result from Claude"""
    grade: str  # Letter grade (A+, A, B+, B, C+, C, D, F)
    positive_feedback: str  # What the student did well
    improvement_feedback: str  # What the student can improve
    recommendation: str  # REPEAT, SIMPLIFY, COMPLEXIFY, or CURRENT_COMPLEXITY_NEW_PHRASE
    confidence: float = 0.0  # Claude's confidence in evaluation (0-1)
    raw_response: str = ""  # Full Claude response for debugging


class ClaudeEvaluator:
    """
    AI-powered musical evaluation using Anthropic's Claude
    
    This class handles the integration with Claude API to provide intelligent
    musical feedback based on structured phrase analysis.
    """
    
    def __init__(self, api_key: Optional[str] = None, session_logger: Optional[Callable[[str], None]] = None):
        """
        Initialize Claude evaluator
        
        Args:
            api_key: Anthropic API key. If None, will look for ANTHROPIC_API_KEY environment variable
            session_logger: Optional function to log to session file
        """
        self.logger = logging.getLogger(__name__)
        self.session_logger = session_logger
        
        if not ANTHROPIC_AVAILABLE:
            self.logger.error("Anthropic package not available. Install with: pip install anthropic")
            self.client = None
            return
        
        try:
            self.client = anthropic.Anthropic(api_key=api_key)
            self.logger.info("Claude evaluator initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Claude client: {e}")
            self.client = None
    
    def _log_to_session(self, content: str) -> None:
        """Log content to session file if session logger is available"""
        if self.session_logger:
            try:
                self.session_logger(content)
            except Exception as e:
                self.logger.error(f"Failed to write to session log: {e}")

    def is_available(self) -> bool:
        """Check if Claude evaluation is available"""
        return self.client is not None
    
    def evaluate_phrase(self, 
                       target_phrase: Phrase, 
                       student_phrase: Phrase,
                       difficulty_level: int = 1,
                       musical_style: str = "modal_jazz",
                       phrase_history: Optional[List[str]] = None) -> Optional[ClaudeEvaluation]:
        """
        Evaluate student's musical phrase performance using Claude AI
        
        Args:
            target_phrase: The phrase the bot played (target)
            student_phrase: The phrase the student played (response)
            difficulty_level: Current difficulty level (1-5)
            musical_style: Musical style context
            phrase_history: List of previous grades for this phrase (for repetition context)
            
        Returns:
            ClaudeEvaluation object with structured feedback, or None if evaluation failed
        """
        if not self.is_available():
            self.logger.error("Claude evaluator not available")
            return None
        
        try:
            # Convert phrases to JSON analysis for Claude
            from evaluation.phrase_analyzer import analyze_phrase_to_json
            
            target_context = {"phrase_type": "bot_phrase"}
            student_context = {"phrase_type": "student_response"}
            
            target_analysis_json = analyze_phrase_to_json(target_phrase, target_context, pretty=False)
            student_analysis_json = analyze_phrase_to_json(student_phrase, student_context, pretty=False)
            
            # Parse JSON strings back to dictionaries for prompt creation
            import json
            target_analysis = json.loads(target_analysis_json)
            student_analysis = json.loads(student_analysis_json)
            
            # Create evaluation prompt
            prompt = self._create_evaluation_prompt(
                target_analysis, 
                student_analysis, 
                difficulty_level, 
                musical_style,
                phrase_history or []
            )
            
            # Send to Claude
            self.logger.info("Sending evaluation request to Claude...")
            
            # Log prompt to session
            self._log_to_session("\n" + "="*80)
            self._log_to_session("🤖 CLAUDE EVALUATION REQUEST:")
            self._log_to_session("="*80)
            self._log_to_session(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            self._log_to_session(f"Model: claude-3-5-sonnet-20241022")
            self._log_to_session(f"Max Tokens: 1000")
            self._log_to_session(f"Temperature: 0.3")
            self._log_to_session("\nPROMPT:")
            self._log_to_session("-" * 40)
            self._log_to_session(prompt)
            self._log_to_session("="*80)
            
            start_time = time.time()
            
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                temperature=0.3,  # Lower temperature for more consistent feedback
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Claude response received in {elapsed_time:.2f}s")
            
            # Log response to session
            response_text = message.content[0].text
            self._log_to_session("\n" + "="*80)
            self._log_to_session("🤖 CLAUDE EVALUATION RESPONSE:")
            self._log_to_session("="*80)
            self._log_to_session(f"Response Time: {elapsed_time:.2f}s")
            self._log_to_session(f"Response Length: {len(response_text)} characters")
            self._log_to_session("\nRESPONSE:")
            self._log_to_session("-" * 40)
            self._log_to_session(response_text)
            self._log_to_session("="*80)
            
            # Parse response
            evaluation = self._parse_claude_response(response_text)
            
            if evaluation:
                self.logger.info(f"Evaluation complete: Grade {evaluation.grade}, Recommendation: {evaluation.recommendation}")
            else:
                self.logger.error("Failed to parse Claude response")
            
            return evaluation
            
        except Exception as e:
            self.logger.error(f"Claude evaluation failed: {e}")
            return None
    
    def _create_evaluation_prompt(self, 
                                target_analysis: Dict[str, Any],
                                student_analysis: Dict[str, Any],
                                difficulty_level: int,
                                musical_style: str,
                                phrase_history: List[str]) -> str:
        """Create the evaluation prompt for Claude"""
        
        # Build phrase history context
        history_context = ""
        if phrase_history:
            attempts_count = len(phrase_history)
            history_context = f"""
**PHRASE REPETITION HISTORY:**
- This phrase has been attempted {attempts_count} time(s) before
- Previous grades: {', '.join(phrase_history)}
- Current attempt: #{attempts_count + 1}
- Note: After 3 attempts, bias against REPEAT unless student shows clear progress
"""
        
        prompt = f"""You are an expert music teacher evaluating a student's performance in a call-and-response exercise.

**CONTEXT:**
- Musical Style: {musical_style}
- Difficulty Level: {difficulty_level}/5
- Exercise: Student listens to a target phrase, then attempts to play it back{history_context}

**TARGET PHRASE (what the student heard):**
{json.dumps(target_analysis, indent=2)}

**STUDENT PERFORMANCE (what the student played):**
{json.dumps(student_analysis, indent=2)}

**EVALUATION TASK:**
Provide encouraging, constructive feedback in exactly this JSON format:

{{
  "grade": "A+|A|B+|B|C+|C|D|F",
  "positive_feedback": "One sentence highlighting what the student did well",
  "improvement_feedback": "One sentence with specific, actionable improvement advice",
  "recommendation": "REPEAT|SIMPLIFY|COMPLEXIFY|CURRENT_COMPLEXITY_NEW_PHRASE",
  "confidence": 0.85
}}

**EVALUATION CRITERIA:**
- Pitch Accuracy: How well did notes match the target?
- Rhythm Accuracy: Was the rhythm approximately correct?
- Overall Completeness: Did they attempt the full phrase?
- If the phrase is close within 8th note accuracy, give at least a B+

**RECOMMENDATION GUIDELINES:**
- REPEAT: Student should practice the same phrase again (grade B or below, or specific issues to work on)
- SIMPLIFY: Student needs an easier phrase (grade C, D or F, struggling with current difficulty)
- COMPLEXIFY: Student ready for harder material (grade B+ or above, demonstrating mastery)
- CURRENT_COMPLEXITY_NEW_PHRASE: Try a different phrase at the same difficulty level (useful when student is stuck on specific phrase after multiple attempts)

**REPETITION BIAS:** After 3 attempts on the same phrase, unles suggesting SIMPLIFY or COMPLEXIFY, strongly favor CURRENT_COMPLEXITY_NEW_PHRASE over REPEAT unless the student shows clear improvement between attempts.

**TONE:** Be encouraging and specific. Focus on musical learning, not just accuracy.

Respond with only the JSON object, no additional text."""

        return prompt
    
    def _parse_claude_response(self, response: str) -> Optional[ClaudeEvaluation]:
        """Parse Claude's response into structured evaluation"""
        try:
            # Clean up response - look for JSON object
            response = response.strip()
            
            # Find JSON boundaries
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                self.logger.error("No JSON object found in Claude response")
                return None
            
            json_str = response[start_idx:end_idx]
            evaluation_data = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['grade', 'positive_feedback', 'improvement_feedback', 'recommendation']
            for field in required_fields:
                if field not in evaluation_data:
                    self.logger.error(f"Missing required field: {field}")
                    return None
            
            # Validate recommendation value
            valid_recommendations = ['REPEAT', 'SIMPLIFY', 'COMPLEXIFY', 'CURRENT_COMPLEXITY_NEW_PHRASE']
            if evaluation_data['recommendation'] not in valid_recommendations:
                self.logger.error(f"Invalid recommendation: {evaluation_data['recommendation']}")
                return None
            
            # Create evaluation object
            return ClaudeEvaluation(
                grade=evaluation_data['grade'],
                positive_feedback=evaluation_data['positive_feedback'],
                improvement_feedback=evaluation_data['improvement_feedback'],
                recommendation=evaluation_data['recommendation'],
                confidence=evaluation_data.get('confidence', 0.0),
                raw_response=response
            )
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response from Claude: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error parsing Claude response: {e}")
            return None
    
    def get_fallback_evaluation(self, 
                              target_phrase: Phrase, 
                              student_phrase: Phrase) -> ClaudeEvaluation:
        """
        Provide fallback evaluation when Claude is unavailable
        
        This implements a simple rule-based evaluation as backup.
        """
        # Simple fallback logic
        note_count_ratio = len(student_phrase.notes) / max(len(target_phrase.notes), 1)
        
        if note_count_ratio >= 0.8:
            grade = "B+"
            positive = "Good effort attempting the full phrase!"
            improvement = "Continue practicing to refine pitch and timing accuracy."
            recommendation = "REPEAT"
        elif note_count_ratio >= 0.5:
            grade = "C+"
            positive = "Nice work on the notes you played!"
            improvement = "Try to play all the notes in the phrase."
            recommendation = "REPEAT"
        else:
            grade = "C"
            positive = "Keep practicing - you're making progress!"
            improvement = "Focus on listening carefully to the full phrase."
            recommendation = "SIMPLIFY"
        
        return ClaudeEvaluation(
            grade=grade,
            positive_feedback=positive,
            improvement_feedback=improvement,
            recommendation=recommendation,
            confidence=0.5,
            raw_response="Fallback evaluation - Claude unavailable"
        )
