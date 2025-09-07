"""
MIDI Controller Input Handler

This module handles MIDI device detection, connection, and real-time input processing.
Phase 2.1 implementation with real MIDI device detection.
"""

import rtmidi
import threading
import time
from typing import List, Optional, Callable, Tuple
from utils.logger import get_logger


class MIDIInputHandler:
    """
    Handles MIDI controller input and device management
    
    This class provides:
    - Real-time MIDI device detection
    - Device connection management
    - MIDI input event processing
    - Connection status monitoring
    """
    
    def __init__(self):
        """Initialize MIDI input handler"""
        self.logger = get_logger()
        self.midi_in = None
        self.connected_device = None
        self.connected_port = None
        self.input_callback = None
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Initialize note processor
        from midi.note_processor import NoteProcessor
        self.note_processor = NoteProcessor()
        
        try:
            # Initialize RtMidi input
            self.midi_in = rtmidi.MidiIn()
            self.logger.info("MIDI Input Handler initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize MIDI: {e}")
            self.midi_in = None
    
    def get_available_devices(self) -> List[str]:
        """
        Get list of available MIDI input devices
        
        Returns:
            List[str]: Device names
        """
        if not self.midi_in:
            self.logger.warning("MIDI not initialized")
            return []
        
        try:
            devices = []
            port_count = self.midi_in.get_port_count()
            
            for i in range(port_count):
                port_name = self.midi_in.get_port_name(i)
                devices.append(port_name)
                self.logger.debug(f"Found MIDI device {i}: {port_name}")
            
            self.logger.info(f"Found {len(devices)} MIDI input devices")
            return devices
            
        except Exception as e:
            self.logger.error(f"Error getting MIDI devices: {e}")
            return []
    
    def connect_device(self, device_name: str) -> bool:
        """
        Connect to specified MIDI device
        
        Args:
            device_name (str): Name of device to connect
            
        Returns:
            bool: True if connection successful
        """
        if not self.midi_in:
            self.logger.error("MIDI not initialized")
            return False
        
        try:
            # Disconnect any existing connection
            self.disconnect_device()
            
            # Find the device port
            port_count = self.midi_in.get_port_count()
            target_port = None
            
            for i in range(port_count):
                port_name = self.midi_in.get_port_name(i)
                if port_name == device_name:
                    target_port = i
                    break
            
            if target_port is None:
                self.logger.error(f"Device '{device_name}' not found")
                return False
            
            # Open the MIDI port
            self.midi_in.open_port(target_port)
            self.connected_device = device_name
            self.connected_port = target_port
            
            # Set up callback for MIDI input
            self.midi_in.set_callback(self._midi_callback)
            
            # Start connection monitoring
            self._start_monitoring()
            
            self.logger.info(f"Successfully connected to MIDI device: {device_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to MIDI device '{device_name}': {e}")
            return False
    
    def connect_device_by_index(self, port_index: int) -> bool:
        """
        Connect to MIDI device by port index
        
        Args:
            port_index (int): Port index to connect to
            
        Returns:
            bool: True if connection successful
        """
        if not self.midi_in:
            self.logger.error("MIDI not initialized")
            return False
        
        try:
            devices = self.get_available_devices()
            if port_index < 0 or port_index >= len(devices):
                self.logger.error(f"Invalid port index: {port_index}")
                return False
            
            device_name = devices[port_index]
            return self.connect_device(device_name)
            
        except Exception as e:
            self.logger.error(f"Failed to connect to port {port_index}: {e}")
            return False
    
    def disconnect_device(self) -> None:
        """Disconnect current MIDI device"""
        try:
            self._stop_monitoring()
            
            if self.midi_in and self.connected_device:
                self.midi_in.close_port()
                self.logger.info(f"Disconnected from MIDI device: {self.connected_device}")
            
            self.connected_device = None
            self.connected_port = None
            
        except Exception as e:
            self.logger.error(f"Error disconnecting MIDI device: {e}")
    
    def set_input_callback(self, callback: Callable) -> None:
        """
        Set callback function for MIDI input events
        
        Args:
            callback: Function to call with MIDI events (message, timestamp)
        """
        self.input_callback = callback
        self.logger.info("MIDI input callback set")
    
    def is_connected(self) -> bool:
        """
        Check if MIDI device is connected
        
        Returns:
            bool: True if device connected
        """
        return self.connected_device is not None
    
    def set_note_processor(self, note_processor) -> None:
        """
        Set note processor for real-time MIDI processing
        
        Args:
            note_processor: NoteProcessor instance
        """
        self.note_processor = note_processor
        self.logger.info("Note processor attached to MIDI handler")
    
    def start_recording(self) -> bool:
        """
        Start recording MIDI input
        
        Returns:
            bool: True if recording started successfully
        """
        if not self.is_connected():
            self.logger.error("Cannot start recording - no MIDI device connected")
            return False
        
        if not self.note_processor:
            self.logger.error("Cannot start recording - no note processor attached")
            return False
        
        self.note_processor.start_session()
        self.is_recording = True
        self.logger.info("Started MIDI recording")
        return True
    
    def stop_recording(self) -> list:
        """
        Stop recording MIDI input and return recorded notes
        
        Returns:
            list: List of recorded MIDINote objects
        """
        if not self.is_recording:
            self.logger.warning("Not currently recording")
            return []
        
        self.is_recording = False
        
        if self.note_processor:
            notes = self.note_processor.stop_session()
            self.logger.info(f"Stopped MIDI recording - captured {len(notes)} notes")
            return notes
        
        return []
    
    def is_recording_active(self) -> bool:
        """Check if MIDI recording is active"""
        return self.is_recording
    
    def get_active_notes(self) -> list:
        """Get currently active (pressed) notes"""
        if self.note_processor:
            return self.note_processor.get_active_notes()
        return []
    
    def get_connected_device(self) -> Optional[str]:
        """
        Get name of currently connected device
        
        Returns:
            str: Device name or None if not connected
        """
        return self.connected_device
    
    def _midi_callback(self, message: Tuple, timestamp: float) -> None:
        """
        Internal callback for MIDI input events
        
        Args:
            message: MIDI message tuple from rtmidi (message_list, delta_time)
            timestamp: Message timestamp
        """
        try:
            # Extract the actual MIDI message bytes
            if isinstance(message, tuple) and len(message) >= 1:
                midi_data = message[0]  # The actual MIDI message list
            else:
                midi_data = message
            
            # Handle timestamp - rtmidi might pass None
            if timestamp is None:
                timestamp = time.time()
            
            # FIRST: Call raw input callback immediately for real-time audio
            if self.input_callback:
                try:
                    self.input_callback(midi_data, timestamp)
                except Exception as e:
                    self.logger.error(f"Error in raw MIDI callback: {e}")
            
            # Process through note processor
            completed_note = self.note_processor.process_midi_event(midi_data, timestamp)
            
            # If we got a completed note, call the external callback (for higher-level processing)
            # This is separate from the raw callback above
            if completed_note and self.input_callback:
                self.input_callback(completed_note, timestamp)
            elif self.input_callback:
                self.input_callback(midi_data, timestamp)
            else:
                self.logger.warning(f"❌ NO EXTERNAL CALLBACK SET - audio synthesis won't work!")
            
            # Log MIDI events for debugging
            if isinstance(midi_data, list) and len(midi_data) >= 1:
                status = midi_data[0]
                msg_type = status & 0xF0
                
                if msg_type in [0x80, 0x90] and len(midi_data) >= 3:  # Note events
                    note_name = self._midi_to_note_name(midi_data[1])
                    velocity = midi_data[2]
                    event_type = "Note ON" if (msg_type == 0x90 and velocity > 0) else "Note OFF"
                    self.logger.debug(f"MIDI {event_type}: {note_name} (vel={velocity})")
                elif msg_type == 0xB0 and len(midi_data) >= 3:  # Control Change
                    self.logger.debug(f"MIDI CC: {midi_data[1]}={midi_data[2]}")
                else:
                    self.logger.debug(f"MIDI: {midi_data}")
                
        except Exception as e:
            self.logger.error(f"Error in MIDI callback: {e}")
            self.logger.debug(f"Message: {message}, Type: {type(message)}")
            self.logger.error(f"Error in MIDI callback: {e}")
    
    def _midi_to_note_name(self, midi_pitch: int) -> str:
        """Convert MIDI pitch number to note name"""
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_pitch // 12) - 1
        note = note_names[midi_pitch % 12]
        return f"{note}{octave}"
    
    def _start_monitoring(self) -> None:
        """Start connection monitoring thread"""
        if self.is_monitoring:
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_connection, daemon=True)
        self.monitor_thread.start()
        self.logger.debug("Started MIDI connection monitoring")
    
    def _stop_monitoring(self) -> None:
        """Stop connection monitoring thread"""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
            self.monitor_thread = None
        self.logger.debug("Stopped MIDI connection monitoring")
    
    def _monitor_connection(self) -> None:
        """Monitor MIDI connection status"""
        while self.is_monitoring:
            try:
                if self.connected_device:
                    # Check if device is still available
                    available_devices = self.get_available_devices()
                    if self.connected_device not in available_devices:
                        self.logger.warning(f"MIDI device {self.connected_device} disconnected")
                        self.connected_device = None
                        self.connected_port = None
                        
                        # Notify callback about disconnection if available
                        if self.input_callback:
                            try:
                                self.input_callback(("device_disconnected",), time.time())
                            except:
                                pass
                
                time.sleep(2.0)  # Check every 2 seconds
                
            except Exception as e:
                self.logger.error(f"Error in connection monitoring: {e}")
                time.sleep(5.0)  # Wait longer on error
    
    def _midi_to_note_name(self, midi_note: int) -> str:
        """
        Convert MIDI note number to note name
        
        Args:
            midi_note (int): MIDI note number (0-127)
            
        Returns:
            str: Note name (e.g., "C4", "F#3")
        """
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_note // 12) - 1
        note_name = note_names[midi_note % 12]
        return f"{note_name}{octave}"
    
    def get_note_processor(self):
        """Get the note processor instance"""
        return self.note_processor
    
    def __del__(self):
        """Cleanup on object destruction"""
        try:
            self.disconnect_device()
        except:
            pass
