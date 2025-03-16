#!/usr/bin/env python3
"""
Audio Recorder Module for Voice Assistant

This module handles all audio recording functionality with extensive configuration
options for different recording qualities, formats and debugging capabilities.
"""

import os
import wave
import time
import pyaudio
import logging
import threading
import io
from datetime import datetime
import argparse
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class AudioRecorderConfig:
    """Configuration class for audio recording parameters."""
    
    # Default configuration presets
    PRESETS = {
        "low_quality": {
            "format": pyaudio.paInt16,
            "channels": 1,
            "sample_rate": 8000,
            "chunk_size": 1024,
            "max_record_seconds": 60
        },
        "standard": {
            "format": pyaudio.paInt16,
            "channels": 1,
            "sample_rate": 16000,
            "chunk_size": 1024,
            "max_record_seconds": 60
        },
        "high_quality": {
            "format": pyaudio.paInt16,
            "channels": 1,
            "sample_rate": 24000,
            "chunk_size": 1024,
            "max_record_seconds": 60
        },
        "openai_whisper": {  # Optimized for OpenAI Whisper model
            "format": pyaudio.paInt16,
            "channels": 1,
            "sample_rate": 24000,
            "chunk_size": 1024,
            "max_record_seconds": 30
        }
    }
    
    def __init__(self, preset="openai_whisper", **kwargs):
        """
        Initialize audio recorder configuration.
        
        Args:
            preset (str): Configuration preset name (low_quality, standard, high_quality, openai_whisper)
            **kwargs: Override specific configuration parameters
        """
        if preset not in self.PRESETS:
            logger.warning(f"Unknown preset '{preset}', falling back to 'standard'")
            preset = "standard"
        
        # Load preset
        config = self.PRESETS[preset].copy()
        
        # Override with any provided kwargs
        config.update(kwargs)
        
        # Set attributes
        self.format = config["format"]
        self.channels = config["channels"]
        self.sample_rate = config["sample_rate"]
        self.chunk_size = config["chunk_size"]
        self.max_record_seconds = config["max_record_seconds"]
        
        # Debug options
        self.save_recordings = True
        self.recordings_dir = os.path.join(os.getcwd(), "recordings")
        self.debug_level = logging.INFO
        
        # Apply any remaining kwargs to object attributes
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self):
        """Convert configuration to dictionary."""
        return {
            "format": self.format,
            "channels": self.channels,
            "sample_rate": self.sample_rate,
            "chunk_size": self.chunk_size,
            "max_record_seconds": self.max_record_seconds,
            "save_recordings": self.save_recordings,
            "recordings_dir": self.recordings_dir,
            "debug_level": self.debug_level
        }
    
    def __str__(self):
        """String representation of the configuration."""
        format_names = {
            pyaudio.paInt16: "16-bit PCM",
            pyaudio.paInt24: "24-bit PCM",
            pyaudio.paFloat32: "32-bit Float"
        }
        
        format_name = format_names.get(self.format, str(self.format))
        
        return (
            f"AudioRecorderConfig:\n"
            f"  Format: {format_name}\n"
            f"  Channels: {self.channels}\n"
            f"  Sample Rate: {self.sample_rate} Hz\n"
            f"  Chunk Size: {self.chunk_size}\n"
            f"  Max Record Time: {self.max_record_seconds} seconds\n"
            f"  Save Recordings: {self.save_recordings}\n"
            f"  Recordings Directory: {self.recordings_dir}"
        )


class AudioRecorder:
    """Audio recorder class for capturing and saving audio from the microphone."""
    
    def __init__(self, config=None, device_index=None):
        """
        Initialize the audio recorder.
        
        Args:
            config (AudioRecorderConfig): Configuration for the recorder
            device_index (int): Index of the input device to use (None for default)
        """
        self.config = config or AudioRecorderConfig()
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.stop_event = None
        self.recording_thread = None
        self.device_index = device_index
        self.used_device_info = None
        
        # Ensure recordings directory exists
        if self.config.save_recordings:
            os.makedirs(self.config.recordings_dir, exist_ok=True)
        
        # Configure logger based on config
        logger.setLevel(self.config.debug_level)
        
        # Log which device will be used
        if device_index is not None:
            try:
                device_info = self.audio.get_device_info_by_index(device_index)
                logger.info(f"Selected input device: [{device_index}] {device_info['name']}")
            except Exception as e:
                logger.error(f"Error getting device info for index {device_index}: {str(e)}")
                logger.info("Will use default input device instead")
                self.device_index = None
        else:
            default_device_index = self.audio.get_default_input_device_info()['index']
            device_info = self.audio.get_device_info_by_index(default_device_index)
            logger.info(f"Using default input device: [{default_device_index}] {device_info['name']}")
    
    def list_input_devices(self):
        """List all available input devices."""
        devices = []
        for i in range(self.audio.get_device_count()):
            device_info = self.audio.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': device_info['name'],
                    'channels': device_info['maxInputChannels'],
                    'sample_rate': int(device_info['defaultSampleRate'])
                })
        
        return devices
    
    def _record_thread(self):
        """Internal recording thread function."""
        try:
            # Configure stream with device if specified
            stream_params = {
                "format": self.config.format,
                "channels": self.config.channels,
                "rate": self.config.sample_rate,
                "input": True,
                "frames_per_buffer": self.config.chunk_size
            }
            
            # Add device index if specified
            if self.device_index is not None:
                stream_params["input_device_index"] = self.device_index
            
            # Store which device is actually being used
            if self.device_index is not None:
                self.used_device_info = self.audio.get_device_info_by_index(self.device_index)
            else:
                default_info = self.audio.get_default_input_device_info()
                self.used_device_info = default_info
                
            device_name = self.used_device_info.get('name', 'Unknown')
            device_index = self.used_device_info.get('index', 'Unknown')            
            
            # Open the stream
            stream = self.audio.open(**stream_params)
            
            logger.info(f"Recording started with device [{device_index}] {device_name}, sample rate {self.config.sample_rate}Hz")
            self.frames = []
            start_time = time.time()
            
            while not self.stop_event.is_set() and (time.time() - start_time) < self.config.max_record_seconds:
                data = stream.read(self.config.chunk_size, exception_on_overflow=False)
                self.frames.append(data)
            
            stream.stop_stream()
            stream.close()
            logger.info("Recording stopped")
            
        except Exception as e:
            logger.error(f"Error in recording thread: {str(e)}")
            self.is_recording = False
    
    def start_recording(self):
        """Start the recording process."""
        if self.is_recording:
            logger.warning("Recording is already in progress")
            return False
        
        self.stop_event = threading.Event()
        self.is_recording = True
        self.recording_thread = threading.Thread(target=self._record_thread)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        return True
    
    def stop_recording(self):
        """
        Stop the recording process.
        
        Returns:
            tuple: (wav_buffer, wav_file_path) if recording was successful,
                  (None, None) otherwise
        """
        if not self.is_recording:
            logger.warning("No recording in progress")
            return None, None
        
        self.stop_event.set()
        self.recording_thread.join()
        self.is_recording = False
        
        if not self.frames:
            logger.warning("No audio data was recorded")
            return None, None
        
        wav_buffer = io.BytesIO()
        
        # Save to in-memory buffer
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.config.format))
            wf.setframerate(self.config.sample_rate)
            wf.writeframes(b''.join(self.frames))
        
        wav_buffer.seek(0)
        
        # Save to file if configured
        wav_file_path = None
        if self.config.save_recordings:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            wav_file_path = os.path.join(self.config.recordings_dir, f"recording_{timestamp}.wav")
            
            with wave.open(wav_file_path, 'wb') as wf:
                wf.setnchannels(self.config.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.config.format))
                wf.setframerate(self.config.sample_rate)
                wf.writeframes(b''.join(self.frames))
            
            logger.info(f"Recording saved to {wav_file_path}")
        
        return wav_buffer, wav_file_path
    
    def record_for_duration(self, seconds):
        """
        Record for a specific duration.
        
        Args:
            seconds (float): Duration in seconds to record
            
        Returns:
            tuple: (wav_buffer, wav_file_path) if recording was successful,
                  (None, None) otherwise
        """
        if seconds <= 0:
            logger.error("Duration must be positive")
            return None, None
            
        if seconds > self.config.max_record_seconds:
            logger.warning(f"Requested duration {seconds}s exceeds maximum {self.config.max_record_seconds}s")
            seconds = self.config.max_record_seconds
        
        self.start_recording()
        time.sleep(seconds)
        return self.stop_recording()
    
    def record_until_keypress(self, prompt="Press Enter to stop recording..."):
        """
        Record until a key is pressed.
        
        Args:
            prompt (str): Prompt to display to the user
            
        Returns:
            tuple: (wav_buffer, wav_file_path) if recording was successful,
                  (None, None) otherwise
        """
        self.start_recording()
        input(prompt)
        return self.stop_recording()
    
    def save_audio_metadata(self, wav_file_path, metadata=None):
        """
        Save metadata for an audio recording.
        
        Args:
            wav_file_path (str): Path to the WAV file
            metadata (dict): Additional metadata to save
        """
        if not wav_file_path or not os.path.exists(wav_file_path):
            logger.error("Invalid WAV file path")
            return
            
        metadata = metadata or {}
        base_metadata = {
            "timestamp": datetime.now().isoformat(),
            "duration": len(self.frames) * self.config.chunk_size / self.config.sample_rate,
            "sample_rate": self.config.sample_rate,
            "channels": self.config.channels,
            "format": self.audio.get_sample_size(self.config.format) * 8,  # bits
            "file_size": os.path.getsize(wav_file_path)
        }
        
        # Combine with provided metadata
        base_metadata.update(metadata)
        
        # Save to file
        metadata_path = wav_file_path.replace('.wav', '.json')
        with open(metadata_path, 'w') as f:
            json.dump(base_metadata, f, indent=2)
            
        logger.debug(f"Metadata saved to {metadata_path}")
    
    def close(self):
        """Close the audio recorder and release resources."""
        if self.is_recording:
            self.stop_recording()
            
        self.audio.terminate()
        logger.info("Audio recorder closed")


def get_parser():
    """Create command line argument parser for test mode."""
    parser = argparse.ArgumentParser(description='Audio Recorder Module')
    parser.add_argument('--preset', type=str, default='openai_whisper', 
                        choices=list(AudioRecorderConfig.PRESETS.keys()),
                        help='Audio configuration preset')
    parser.add_argument('--duration', type=float, default=5.0,
                        help='Recording duration in seconds (0 for manual stop)')
    parser.add_argument('--sample-rate', type=int, 
                        help='Override sample rate (Hz)')
    parser.add_argument('--list-devices', action='store_true',
                        help='List available input devices and exit')
    parser.add_argument('--device', type=int, 
                        help='Specify input device index to use')
    parser.add_argument('--no-save', action='store_true',
                        help='Disable saving recordings to disk')
    parser.add_argument('--show-metadata', action='store_true',
                        help='Display full recording metadata after recording')
    return parser


if __name__ == "__main__":
    # Parse command line arguments
    parser = get_parser()
    args = parser.parse_args()
    
    # Create configuration
    config_kwargs = {}
    if args.sample_rate:
        config_kwargs['sample_rate'] = args.sample_rate
    if args.no_save:
        config_kwargs['save_recordings'] = False
    
    config = AudioRecorderConfig(preset=args.preset, **config_kwargs)
    
    # Create recorder instance with optional device selection
    recorder = AudioRecorder(config, device_index=args.device)
    
    print(f"Audio Recorder Test Mode\n{'-' * 30}")
    print(config)
    
    # List devices if requested
    if args.list_devices:
        devices = recorder.list_input_devices()
        print(f"\nAvailable Input Devices ({len(devices)} found):")
        for device in devices:
            print(f"  [{device['index']}] {device['name']} - {device['channels']} channels, {device['sample_rate']}Hz")
        recorder.close()
        exit(0)
    
    try:
        # Start recording
        print("\nStarting recording...")
        if args.duration > 0:
            print(f"Recording for {args.duration} seconds...")
            buffer, file_path = recorder.record_for_duration(args.duration)
        else:
            buffer, file_path = recorder.record_until_keypress()
        
        # Display results
        if buffer:
            print("\nRecording successful!")
            buffer_size = len(buffer.getvalue())
            recording_duration = len(recorder.frames) * recorder.config.chunk_size / recorder.config.sample_rate
            print(f"Recording duration: {recording_duration:.2f} seconds")
            print(f"Buffer size: {buffer_size} bytes")
            
            # Show which device was used
            if recorder.used_device_info:
                device_name = recorder.used_device_info.get('name', 'Unknown')
                device_index = recorder.used_device_info.get('index', 'Unknown')
                print(f"Recorded with device: [{device_index}] {device_name}")
            
            if file_path:
                print(f"File saved: {file_path}")
                
                # Save metadata
                metadata = {
                    "test_mode": True,
                    "command_line_args": vars(args),
                    "device_info": recorder.used_device_info
                }
                recorder.save_audio_metadata(file_path, metadata)
                
                # Show metadata if requested
                if args.show_metadata:
                    print("\nRecording Metadata:")
                    metadata_path = file_path.replace('.wav', '.json')
                    if os.path.exists(metadata_path):
                        with open(metadata_path, 'r') as f:
                            print(json.dumps(json.load(f), indent=2))
        else:
            print("\nRecording failed.")
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        recorder.close()
        print("Test completed.")
