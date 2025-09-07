"""
Audio Player

Handles real-time audio output and playback.
Phase 3.1 implementation with low-latency streaming.
"""

import sounddevice as sd
import numpy as np
import threading
import time
from typing import Optional, Callable
from utils.logger import get_logger


class AudioPlayer:
    """
    Real-time audio playback engine with low-latency streaming
    
    Features:
    - Real-time audio streaming using sounddevice
    - Configurable buffer sizes for latency optimization
    - Audio device management
    - Integration with synthesizer for live playback
    """
    
    def __init__(self, sample_rate=44100, buffer_size=512, channels=1):
        """
        Initialize audio player
        
        Args:
            sample_rate (int): Audio sample rate in Hz
            buffer_size (int): Audio buffer size (lower = less latency)
            channels (int): Number of audio channels (1=mono, 2=stereo)
        """
        self.logger = get_logger()
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.channels = channels
        
        # Audio stream state
        self.stream: Optional[sd.OutputStream] = None
        self.is_playing = False
        self.audio_callback: Optional[Callable] = None
        
        # Thread safety
        self.lock = threading.Lock()
        
        self.logger.info(f"Audio Player initialized - {sample_rate}Hz, buffer={buffer_size}, channels={channels}")
    
    def set_audio_callback(self, callback: Callable[[int], np.ndarray]):
        """
        Set callback function that generates audio data
        
        Args:
            callback: Function that takes (num_samples) and returns audio array
        """
        with self.lock:
            self.audio_callback = callback
            self.logger.debug("Audio callback set")
    
    def start_stream(self):
        """Start real-time audio streaming"""
        try:
            with self.lock:
                if self.is_playing:
                    self.logger.warning("Audio stream already running")
                    return
                
                # Create and start audio stream
                self.stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=np.float32,
                    blocksize=self.buffer_size,
                    callback=self._stream_callback,
                    latency='low'
                )
                
                self.stream.start()
                self.is_playing = True
                self.logger.info("Audio stream started")
                
        except Exception as e:
            self.logger.error(f"Failed to start audio stream: {e}")
            raise
    
    def stop_stream(self):
        """Stop real-time audio streaming"""
        try:
            with self.lock:
                if not self.is_playing:
                    return
                
                if self.stream:
                    self.stream.stop()
                    self.stream.close()
                    self.stream = None
                
                self.is_playing = False
                self.logger.info("Audio stream stopped")
                
        except Exception as e:
            self.logger.error(f"Failed to stop audio stream: {e}")
    
    def _stream_callback(self, outdata: np.ndarray, frames: int, time_info, status):
        """
        Internal callback for audio stream
        
        Args:
            outdata: Output audio buffer to fill
            frames: Number of frames to generate
            time_info: Timing information
            status: Stream status
        """
        try:
            if status:
                self.logger.warning(f"🔊 AUDIO STREAM STATUS: {status}")
            
            # Generate audio data using callback
            if self.audio_callback:
                audio_data = self.audio_callback(frames)
                
                # Check if we got valid audio data
                if audio_data is not None and len(audio_data) > 0:
                    max_level = np.max(np.abs(audio_data))
                    # if max_level > 0.001:  # Only log when there's actual audio content
                    #     self.logger.info(f"🔊 AUDIO STREAM: got {len(audio_data)} samples, max level = {max_level:.3f}")
                
                # Handle mono/stereo conversion
                if self.channels == 1:
                    outdata[:, 0] = audio_data
                else:
                    # Stereo - duplicate mono signal
                    outdata[:, 0] = audio_data
                    outdata[:, 1] = audio_data
            else:
                # No callback - output silence
                self.logger.warning(f"❌ NO AUDIO CALLBACK SET - outputting silence")
                outdata.fill(0.0)
                
        except Exception as e:
            self.logger.error(f"💥 AUDIO STREAM CALLBACK ERROR: {e}")
            import traceback
            self.logger.error(f"💥 TRACEBACK: {traceback.format_exc()}")
            outdata.fill(0.0)  # Output silence on error
    
    def get_audio_devices(self):
        """
        Get list of available audio output devices
        
        Returns:
            list: Available audio devices
        """
        try:
            devices = sd.query_devices()
            output_devices = []
            
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:
                    output_devices.append({
                        'id': i,
                        'name': device['name'],
                        'channels': device['max_output_channels'],
                        'sample_rate': device['default_samplerate']
                    })
            
            self.logger.debug(f"Found {len(output_devices)} audio output devices")
            return output_devices
            
        except Exception as e:
            self.logger.error(f"Failed to query audio devices: {e}")
            return []
    
    def get_latency_info(self) -> dict:
        """
        Get current audio latency information
        
        Returns:
            dict: Latency information
        """
        if self.stream and self.is_playing:
            try:
                latency = self.stream.latency
                # Handle both tuple and single value cases
                if isinstance(latency, (tuple, list)) and len(latency) >= 2:
                    return {
                        'input_latency': latency[0],
                        'output_latency': latency[1],
                        'buffer_size': self.buffer_size,
                        'sample_rate': self.sample_rate
                    }
                else:
                    return {
                        'output_latency': float(latency) if latency else 0.0,
                        'buffer_size': self.buffer_size,
                        'sample_rate': self.sample_rate
                    }
            except Exception as e:
                self.logger.warning(f"Could not get latency info: {e}")
                return {
                    'buffer_size': self.buffer_size,
                    'sample_rate': self.sample_rate
                }
        return {}
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.stop_stream()
        except:
            pass
