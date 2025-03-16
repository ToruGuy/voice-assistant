#!/usr/bin/env python3
import os
import tempfile
import sys
import time
from datetime import datetime
from pynput import keyboard
import requests

from config import logger, API_KEY, TRANSCRIPTION_ENDPOINT
from audio_recorder import AudioRecorder, AudioRecorderConfig

class SpaceKeyRecorder:
    """Record audio while the space key is held down."""
    
    def __init__(self):
        """Initialize the space key recorder."""
        self.recorder = None
        self.is_recording = False
        self.space_pressed = False
        self.listener = None
        # Create a recorder with OpenAI Whisper optimized settings
        config = AudioRecorderConfig(preset="openai_whisper")
        self.recorder = AudioRecorder(config=config)
        
    def on_press(self, key):
        """Handle key press events."""
        if key == keyboard.Key.space and not self.space_pressed:
            self.space_pressed = True
            if not self.is_recording:
                logger.info("Space pressed - Starting recording...")
                self.is_recording = True
                self.recorder.start_recording()
    
    def on_release(self, key):
        """Handle key release events."""
        if key == keyboard.Key.space and self.space_pressed:
            self.space_pressed = False
            if self.is_recording:
                logger.info("Space released - Stopping recording...")
                self.is_recording = False
                return self.recorder.stop_recording()
        elif key == keyboard.Key.esc:
            # Stop listener
            return False
        return None, None
    
    def start_listening(self):
        """Start listening for keyboard events."""
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release)
        self.listener.start()
        
    def stop_listening(self):
        """Stop listening for keyboard events."""
        if self.listener:
            self.listener.stop()
            
    def wait_for_space_key_recording(self):
        """Wait for user to press and release space key to record audio."""
        if not self.listener or not self.listener.running:
            self.start_listening()
            
        logger.info("Press and hold SPACE to record, release to stop. Press ESC to exit.")
        
        # Wait for recording to complete (space key released)
        while self.listener.running and not self.is_recording:
            time.sleep(0.1)  # Small delay to prevent CPU hogging
            
        while self.listener.running and self.is_recording:
            time.sleep(0.1)  # Wait while recording
            
        # If recording was just completed, return the result
        if not self.is_recording and self.recorder.frames:
            # Return the last recording result
            return self.recorder.stop_recording()
            
        return None, None
        
    def close(self):
        """Clean up resources."""
        self.stop_listening()
        if self.recorder:
            self.recorder.close()

def transcribe_audio(audio_data):
    """Transcribe audio data using OpenAI's Whisper API."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
        temp_file.write(audio_data.getvalue())
        temp_file.flush()
        
        logger.info("Transcribing audio...")
        
        with open(temp_file.name, "rb") as audio_file:
            files = {"file": (os.path.basename(temp_file.name), audio_file, "audio/wav")}
            headers = {"Authorization": f"Bearer {API_KEY}"}
            data = {"model": "whisper-1"}
            
            response = requests.post(
                TRANSCRIPTION_ENDPOINT,
                headers=headers,
                files=files,
                data=data
            )
            
            if response.status_code == 200:
                transcription = response.json()
                logger.info(f"Transcription: {transcription['text']}")
                
                # Save transcription to a text file in the same directory as the audio file
                audio_dirname = os.path.dirname(temp_file.name)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                transcript_path = os.path.join(os.getcwd(), "recordings", f"transcript_{timestamp}.txt")
                
                with open(transcript_path, 'w') as f:
                    f.write(transcription['text'])
                    
                logger.info(f"Transcription saved to {transcript_path}")
                
                return transcription['text']
            else:
                logger.error(f"Transcription failed: {response.text}")
                return None

def play_audio(file_path):
    """Play audio from the given file path."""
    if sys.platform == 'darwin':  # macOS
        os.system(f"afplay {file_path}")
    elif sys.platform == 'linux':
        os.system(f"aplay {file_path}")
    elif sys.platform == 'win32':
        os.system(f"start {file_path}")
    else:
        logger.warning(f"Unsupported platform for audio playback: {sys.platform}")
