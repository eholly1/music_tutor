#!/usr/bin/env python3
"""
Test Configuration System

Verifies that the API key is properly loaded from config.ini
"""

import sys
import os

# Add src directory to path for imports
sys.path.append('/Users/sage/Desktop/music_trainer/src')

from utils.config import Config


def main():
    print("🔧 Testing Configuration System")
    print("=" * 40)
    
    # Initialize config
    try:
        config = Config()
        print("✅ Configuration system initialized")
        
        # Test API key loading
        api_key = config.get_anthropic_api_key()
        if api_key:
            # Mask the key for security
            masked_key = api_key[:15] + "..." + api_key[-10:] if len(api_key) > 25 else api_key[:8] + "..."
            print(f"✅ Anthropic API key loaded: {masked_key}")
            
            # Test with Claude evaluator
            try:
                from evaluation.claude_evaluator import ClaudeEvaluator
                evaluator = ClaudeEvaluator(api_key=api_key)
                print(f"✅ Claude evaluator initialized: Available={evaluator.is_available()}")
            except Exception as e:
                print(f"❌ Claude evaluator failed: {e}")
        else:
            print("❌ No API key found")
            print("   Please check that config.ini exists and contains your API key")
        
        # Test other config values
        print(f"\\n📊 Other Configuration:")
        print(f"   Audio Sample Rate: {config.get('audio.sample_rate', 'Not set')}")
        print(f"   Default BPM: {config.get('session.default_bpm', config.get('practice.default_tempo', 'Not set'))}")
        print(f"   Default Difficulty: {config.get('session.default_difficulty', config.get('practice.difficulty_level', 'Not set'))}")
        print(f"   Default Style: {config.get('session.default_style', config.get('practice.style', 'Not set'))}")
        
        # Check if config.ini exists
        config_ini_path = "/Users/sage/Desktop/music_trainer/config.ini"
        if os.path.exists(config_ini_path):
            print(f"\\n✅ config.ini file exists at: {config_ini_path}")
        else:
            print(f"\\n❌ config.ini file not found at: {config_ini_path}")
        
        print(f"\\n🎉 Configuration test completed!")
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
