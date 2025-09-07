#!/usr/bin/env python3
"""
Basic setup test for Music Trainer

This script tests that the basic project structure and dependencies are working.
Run this to verify Phase 1 setup is complete.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test that core modules can be imported"""
    print("Testing module imports...")
    
    try:
        from utils.logger import setup_logger, get_logger
        print("✓ Logger module imported successfully")
    except ImportError as e:
        print(f"✗ Logger import failed: {e}")
        return False
    
    try:
        from utils.config import Config
        print("✓ Config module imported successfully")
    except ImportError as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    try:
        from gui.main_window import MainWindow
        print("✓ GUI module imported successfully")
    except ImportError as e:
        print(f"✗ GUI import failed: {e}")
        return False
    
    try:
        from midi.input_handler import MIDIInputHandler
        print("✓ MIDI module imported successfully")
    except ImportError as e:
        print(f"✗ MIDI import failed: {e}")
        return False
    
    return True


def test_config():
    """Test configuration system"""
    print("\nTesting configuration system...")
    
    try:
        from utils.logger import setup_logger
        from utils.config import Config
        
        # Setup logger
        logger = setup_logger()
        print("✓ Logger setup successful")
        
        # Test config
        config = Config()
        print("✓ Config initialization successful")
        
        # Test config access
        sample_rate = config.get('audio.sample_rate')
        print(f"✓ Config access successful (sample_rate: {sample_rate})")
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False


def test_data_files():
    """Test that data files exist"""
    print("\nTesting data files...")
    
    # Check phrase library
    phrase_file = project_root / "data" / "phrases" / "modal_jazz.json"
    if phrase_file.exists():
        print("✓ Modal jazz phrase library found")
        
        try:
            import json
            with open(phrase_file, 'r') as f:
                data = json.load(f)
            phrase_count = len(data.get('phrases', []))
            print(f"✓ Phrase library loaded successfully ({phrase_count} phrases)")
            return True
        except Exception as e:
            print(f"✗ Error loading phrase library: {e}")
            return False
    else:
        print("✗ Modal jazz phrase library not found")
        return False


def test_project_structure():
    """Test that project structure is correct"""
    print("\nTesting project structure...")
    
    required_dirs = [
        "src",
        "src/midi",
        "src/audio", 
        "src/music",
        "src/evaluation",
        "src/gui",
        "src/utils",
        "data",
        "data/phrases",
        "tests"
    ]
    
    missing_dirs = []
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if not full_path.exists():
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"✗ Missing directories: {missing_dirs}")
        return False
    else:
        print("✓ All required directories present")
        return True


def main():
    """Run all setup tests"""
    print("Music Trainer - Phase 1 Setup Test")
    print("=" * 40)
    
    tests = [
        test_project_structure,
        test_imports,
        test_config,
        test_data_files
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
    
    print("\n" + "=" * 40)
    print(f"Setup Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 Phase 1 setup is complete and working!")
        print("\nYou can now run the application with:")
        print("  python src/main.py")
        return True
    else:
        print("❌ Setup is incomplete. Please check the errors above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
