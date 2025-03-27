#!/usr/bin/env python3
import os
import tempfile
import sys
import time
import threading
import queue
from datetime import datetime
from pynput import keyboard
import requests

from src.config import logger, API_KEY, TRANSCRIPTION_ENDPOINT
from src.audio_recorder import AudioRecorder, AudioRecorderConfig

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

class AudioQueueManager:
    """Manages a queue of audio files to play sequentially without overlapping."""
    
    def __init__(self):
        """Initialize the audio queue manager."""
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.player_thread = None
        self.stop_requested = False
    
    def start_player(self):
        """Start the audio player thread if not already running."""
        if not self.player_thread or not self.player_thread.is_alive():
            self.stop_requested = False
            self.player_thread = threading.Thread(target=self._player_thread_func)
            self.player_thread.daemon = True
            self.player_thread.start()
    
    def _player_thread_func(self):
        """Audio player thread function that processes the queue."""
        while not self.stop_requested:
            try:
                # Get the next audio file to play with a shorter timeout (reduced from 0.5s)
                file_path = self.audio_queue.get(timeout=0.1)
                
                # Mark as playing
                self.is_playing = True
                
                # Play the audio file (blocking)
                logger.debug(f"Playing audio file: {file_path}")
                if os.path.exists(file_path):
                    # Play the audio with internal play_audio function (always blocking)
                    self._play_audio_internal(file_path)
                    
                    # Clean up temporary files
                    if '/tmp/' in file_path or 'temp' in file_path:
                        try:
                            os.remove(file_path)
                            logger.debug(f"Removed temporary audio file: {file_path}")
                        except Exception as e:
                            logger.error(f"Error removing temp file: {str(e)}")
                else:
                    logger.warning(f"Audio file not found: {file_path}")
                
                # Mark the task as done
                self.audio_queue.task_done()
                self.is_playing = False
                
                # Reduce the delay between chunks by waiting briefly
                # This small delay helps prevent system overload while still keeping transitions smooth
                time.sleep(0.05)
                
            except queue.Empty:
                # No items in the queue
                self.is_playing = False
                
                # Use a shorter sleep when queue is empty to be more responsive
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Error in audio player thread: {str(e)}")
                self.is_playing = False
    
    def _play_audio_internal(self, file_path):
        """Internal function to play audio file with platform-specific commands."""
        try:
            if sys.platform == 'darwin':  # macOS
                os.system(f"afplay {file_path}")
            elif sys.platform == 'linux':
                os.system(f"aplay {file_path}")
            elif sys.platform == 'win32':
                os.system(f"start /wait {file_path}")
            else:
                logger.warning(f"Unsupported platform for audio playback: {sys.platform}")
        except Exception as e:
            logger.error(f"Error playing audio: {str(e)}")
    
    def add_to_queue(self, file_path):
        """Add an audio file to the playback queue.
        
        Args:
            file_path (str): Path to the audio file to play
        """
        if not os.path.exists(file_path):
            logger.warning(f"Audio file does not exist: {file_path}")
            return
        
        # Add to queue
        self.audio_queue.put(file_path)
        
        # Make sure player is running
        self.start_player()
    
    def stop(self):
        """Stop the audio player thread."""
        self.stop_requested = True
        if self.player_thread and self.player_thread.is_alive():
            self.player_thread.join(timeout=1.0)
    
    def wait_for_queue_empty(self, timeout=None):
        """Wait for the audio queue to be empty and not playing.
        
        Args:
            timeout (float, optional): Maximum time to wait in seconds. None means wait indefinitely.
        
        Returns:
            bool: True if queue is empty and not playing, False if timeout occurred
        """
        start_time = time.time()
        while self.is_playing or not self.audio_queue.empty():
            if timeout is not None and time.time() - start_time > timeout:
                return False
            # Reduced wait time for more responsiveness
            time.sleep(0.05)
        return True

# Create a global instance of the audio queue manager
audio_queue_manager = AudioQueueManager()

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

def play_audio(file_path, block=True):
    """Play audio from the given file path.
    
    Args:
        file_path (str): Path to the audio file to play
        block (bool): Whether to block until playback completes (default: True)
    """
    if not os.path.exists(file_path):
        logger.warning(f"Audio file does not exist: {file_path}")
        return
    
    # Use the queue manager for all audio playback to prevent overlapping
    audio_queue_manager.add_to_queue(file_path)
    
    # If block is True, wait for this file and all previous files to finish playing
    if block:
        audio_queue_manager.wait_for_queue_empty()
