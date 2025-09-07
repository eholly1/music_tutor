#!/usr/bin/env python3
"""
MIDI Device Detection Test

This script tests the MIDI controller detection functionality
and shows available MIDI input devices.
"""

import sys
from pathlib import Path

# Add src directory to Python path
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

from utils.logger import setup_logger
from midi.input_handler import MIDIInputHandler


def test_midi_detection():
    """Test MIDI device detection"""
    print("MIDI Controller Detection Test")
    print("=" * 40)
    
    # Setup logging
    logger = setup_logger()
    
    try:
        # Initialize MIDI handler
        print("Initializing MIDI handler...")
        midi_handler = MIDIInputHandler()
        
        if not midi_handler.midi_in:
            print("❌ Failed to initialize MIDI system")
            return False
        
        print("✅ MIDI system initialized successfully")
        
        # Get available devices
        print("\nScanning for MIDI input devices...")
        devices = midi_handler.get_available_devices()
        
        if not devices:
            print("❌ No MIDI input devices found")
            print("\nTroubleshooting tips:")
            print("1. Make sure your MIDI controller is connected via USB")
            print("2. Check that the device is powered on")
            print("3. Try reconnecting the USB cable")
            print("4. Check if the device appears in your system's MIDI settings")
            return False
        
        print(f"✅ Found {len(devices)} MIDI input device(s):")
        for i, device in enumerate(devices):
            print(f"  {i}: {device}")
        
        # Test connection to first device
        if devices:
            print(f"\nTesting connection to: {devices[0]}")
            success = midi_handler.connect_device(devices[0])
            
            if success:
                print("✅ Successfully connected to MIDI device!")
                print(f"Connected device: {midi_handler.get_connected_device()}")
                
                # Test basic MIDI input
                print("\nMIDI device is ready for input.")
                print("Try playing a note on your controller to test...")
                print("(This test doesn't capture input yet - that's Phase 2.2)")
                
                # Disconnect
                midi_handler.disconnect_device()
                print("✅ Device disconnected successfully")
                return True
            else:
                print("❌ Failed to connect to MIDI device")
                return False
        
    except Exception as e:
        print(f"❌ Error during MIDI detection test: {e}")
        logger.error(f"MIDI detection test failed: {e}", exc_info=True)
        return False


def main():
    """Main test function"""
    success = test_midi_detection()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 MIDI Controller Detection Test PASSED!")
        print("\nYour MIDI controller is ready for use with Music Trainer.")
    else:
        print("❌ MIDI Controller Detection Test FAILED!")
        print("\nPlease check your MIDI controller connection and try again.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
