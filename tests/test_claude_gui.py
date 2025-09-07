#!/usr/bin/env python3
"""
Simple GUI Test for Claude Feedback Display

Tests the Claude feedback display in the Session Status window
without running a full practice session.
"""

import sys
import tkinter as tk
from tkinter import ttk
import time
import threading

# Add src directory to path
sys.path.append('/Users/sage/Desktop/music_trainer/src')

from evaluation.claude_evaluator import ClaudeEvaluation


class SimpleFeedbackTest:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Claude Feedback Test")
        self.root.geometry("500x400")
        
        self.setup_gui()
        
    def setup_gui(self):
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Claude AI Feedback Test", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Claude AI Feedback section (copied from main_window.py)
        feedback_label = ttk.Label(main_frame, text="AI Feedback:", font=("Arial", 11, "bold"))
        feedback_label.grid(row=1, column=0, sticky=(tk.W,), pady=(0, 5))
        
        # Create text widget with scrollbar for feedback
        feedback_container = ttk.Frame(main_frame)
        feedback_container.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        feedback_container.columnconfigure(0, weight=1)
        feedback_container.rowconfigure(0, weight=1)
        
        self.claude_feedback_text = tk.Text(
            feedback_container,
            height=12,
            width=50,
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
        
        # Buttons to test different feedback types
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, pady=(10, 0))
        
        ttk.Button(button_frame, text="Good Performance", command=self.show_good_feedback).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Poor Performance", command=self.show_poor_feedback).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Evaluating...", command=self.show_evaluating).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Error", command=self.show_error).pack(side=tk.LEFT)
        
        # Initialize with waiting message
        self._update_claude_feedback("🤖 Waiting for your first phrase attempt...")
    
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
            print(f"Failed to update Claude feedback display: {e}")
    
    def _format_claude_feedback(self, evaluation) -> str:
        """Format Claude evaluation for display in the text widget"""
        return f"""🎭 Grade: {evaluation.grade}

✅ What you did well:
{evaluation.positive_feedback}

🎯 What to improve:
{evaluation.improvement_feedback}

📊 Recommendation: {evaluation.recommendation}
{'• Practice this phrase again' if evaluation.recommendation == 'REPEAT' else 
 '• Try an easier phrase' if evaluation.recommendation == 'SIMPLIFY' else 
 '• Ready for a harder challenge!'}

💡 Confidence: {int(evaluation.confidence * 100)}%"""
    
    def show_good_feedback(self):
        """Show example of good performance feedback"""
        evaluation = ClaudeEvaluation(
            grade="A-",
            positive_feedback="Excellent pitch accuracy and consistent timing throughout the phrase!",
            improvement_feedback="Try to add more dynamic expression to bring the phrase to life.",
            recommendation="COMPLEXIFY",
            confidence=0.92
        )
        
        feedback_text = self._format_claude_feedback(evaluation)
        self._update_claude_feedback(feedback_text)
    
    def show_poor_feedback(self):
        """Show example of poor performance feedback"""
        evaluation = ClaudeEvaluation(
            grade="D+",
            positive_feedback="Good effort in attempting the beginning of the phrase.",
            improvement_feedback="Focus on listening more carefully to match the correct pitches and rhythm.",
            recommendation="SIMPLIFY",
            confidence=0.78
        )
        
        feedback_text = self._format_claude_feedback(evaluation)
        self._update_claude_feedback(feedback_text)
    
    def show_evaluating(self):
        """Show evaluating message"""
        self._update_claude_feedback("🤖 Evaluating your performance with Claude AI...")
        
        # Simulate evaluation delay
        def delayed_feedback():
            time.sleep(2)
            self.show_good_feedback()
        
        threading.Thread(target=delayed_feedback, daemon=True).start()
    
    def show_error(self):
        """Show error message"""
        self._update_claude_feedback("❌ AI Evaluation Error: Unable to connect to Claude API")
    
    def run(self):
        """Start the GUI"""
        self.root.mainloop()


def main():
    print("🎵 Claude Feedback Display Test")
    app = SimpleFeedbackTest()
    app.run()


if __name__ == "__main__":
    main()
