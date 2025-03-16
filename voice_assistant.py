#!/usr/bin/env python3
import os
import json
import time
import base64
import logging
import threading
import wave
import io
import tempfile
import sys
from datetime import datetime

# Third-party imports
import requests
import pyaudio
from dotenv import load_dotenv
from pynput import keyboard

# Local imports
from audio_recorder import AudioRecorder, AudioRecorderConfig

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    logging.error("OPENAI_API_KEY not found in environment variables.")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Audio Configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000  # 24kHz for OpenAI's audio model
CHUNK = 1024
MAX_RECORD_SECONDS = 30  # Max recording length in seconds

# OpenAI API endpoints
TRANSCRIPTION_ENDPOINT = "https://api.openai.com/v1/audio/transcriptions"
CHAT_ENDPOINT = "https://api.openai.com/v1/chat/completions"
SPEECH_ENDPOINT = "https://api.openai.com/v1/audio/speech"

# Global conversation history
conversation_history = []

# Function definitions
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return {"result": a + b}

def get_current_time():
    """Get the current time."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"time": current_time}

# Available functions
AVAILABLE_FUNCTIONS = {
    "calculate_sum": calculate_sum,
    "get_current_time": get_current_time
}

# Function definitions for the model
FUNCTION_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "calculate_sum",
            "description": "Calculate the sum of two numbers",
            "parameters": {
                "type": "object",
                "properties": {
                    "a": {"type": "number", "description": "The first number"},
                    "b": {"type": "number", "description": "The second number"}
                },
                "required": ["a", "b"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current time",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

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

def chat_with_gpt(user_message):
    """Send a message to GPT-4o and handle function calls."""
    global conversation_history
    
    # Add user message to conversation history
    conversation_history.append({"role": "user", "content": user_message})
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Use gpt-4o or gpt-4o-mini for text-based chat
    payload = {
        "model": "gpt-4o",
        "messages": conversation_history,
        "tools": FUNCTION_DEFINITIONS,
        "tool_choice": "auto"
    }
    
    logger.info("Sending message to GPT-4o...")
    
    try:
        response = requests.post(CHAT_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        assistant_message = response_data["choices"][0]["message"]
        
        # Check if there's a function call
        if "tool_calls" in assistant_message:
            tool_calls = assistant_message["tool_calls"]
            
            # Add the assistant's message with function call to history
            conversation_history.append(assistant_message)
            
            # Process each function call
            for tool_call in tool_calls:
                if tool_call["type"] == "function":
                    function_call = tool_call["function"]
                    function_name = function_call["name"]
                    function_args = json.loads(function_call["arguments"])
                    
                    logger.info(f"Function call: {function_name} with args: {function_args}")
                    
                    # Execute function if it exists
                    if function_name in AVAILABLE_FUNCTIONS:
                        function_response = AVAILABLE_FUNCTIONS[function_name](**function_args)
                        
                        # Add function response to history
                        conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": function_name,
                            "content": json.dumps(function_response)
                        })
                        
                        logger.info(f"Function response: {function_response}")
                    else:
                        logger.warning(f"Function {function_name} not found")
                        
            # Get final response after function call
            return get_final_response()
        else:
            # No function call, just a regular response
            conversation_history.append(assistant_message)
            return assistant_message["content"]
    
    except requests.RequestException as e:
        logger.error(f"Error in chat request: {str(e)}")
        return "Sorry, there was an error communicating with the assistant."

def get_final_response():
    """Get the final response after function calls."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-4o-audio-preview",
        "messages": conversation_history,
    }
    
    try:
        response = requests.post(CHAT_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        assistant_message = response_data["choices"][0]["message"]
        
        # Add the final response to history
        conversation_history.append(assistant_message)
        
        return assistant_message["content"]
    
    except requests.RequestException as e:
        logger.error(f"Error in final response request: {str(e)}")
        return "Sorry, there was an error getting the final response."

def text_to_speech(text):
    """Convert text to speech using OpenAI's Text-to-Speech API."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": "alloy"
    }
    
    logger.info("Converting text to speech...")
    
    try:
        response = requests.post(SPEECH_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        # Save audio to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        
        return temp_file_path
    
    except requests.RequestException as e:
        logger.error(f"Error in text-to-speech request: {str(e)}")
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

def main():
    """Main function to run the voice assistant."""
    try:
        # Display initial instructions
        print("\nVoice Assistant with GPT-4o Audio")
        print("--------------------------------")
        print("Press and hold SPACE to record, release to stop.")
        print("Press ESC to exit.\n")
        
        space_recorder = SpaceKeyRecorder()
        
        try:
            while True:
                print("\nWaiting for you to press SPACE to start recording...")
                
                # Wait for space key to be pressed and released
                wav_buffer, wav_filename = space_recorder.wait_for_space_key_recording()
                
                if wav_buffer is None:
                    logger.info("No recording captured or user exited.")
                    # Check if the listener is still running
                    if not space_recorder.listener.running:
                        print("Exiting voice assistant. Goodbye!")
                        break
                    continue
                
                print("Processing your recording...")
                
                # Transcribe audio
                transcription = transcribe_audio(wav_buffer)
                
                if transcription is None:
                    logger.error("Failed to transcribe audio.")
                    continue
                    
                print(f"You said: {transcription}")
                    
                # Send to GPT for processing
                response = chat_with_gpt(transcription)
                print(f"\nAssistant: {response}")
                
                # Save response to file for debugging
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                response_path = os.path.join(os.getcwd(), "recordings", f"response_{timestamp}.txt")
                with open(response_path, 'w') as f:
                    f.write(response)
                print(f"Response saved to: {response_path}")
                
                # Convert response to speech and play it
                audio_file = text_to_speech(response)
                
                if audio_file:
                    play_audio(audio_file)
                
        finally:
            # Clean up resources
            space_recorder.close()
            
    except KeyboardInterrupt:
        print("\nVoice assistant terminated.")
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram terminated by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)
