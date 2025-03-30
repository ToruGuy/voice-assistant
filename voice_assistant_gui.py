#!/usr/bin/env python3
import os
import sys
from datetime import datetime

# Import from our custom modules
from PyQt5.QtWidgets import QApplication

from src.config import logger
from src.audio_handler import SpaceKeyRecorder, play_audio
from src.openai_client import chat_with_gpt, text_to_speech, clear_conversation_history, transcribe_audio
from src.utils import chunk_text_for_tts
from src.ui.voice_assistant_ui import VoiceAssistantUI

def ensure_recordings_dir():
    """Ensure the recordings directory exists."""
    recordings_dir = os.path.join(os.getcwd(), "recordings")
    if not os.path.exists(recordings_dir):
        os.makedirs(recordings_dir)
        logger.info(f"Created recordings directory: {recordings_dir}")

def ensure_assets():
    """Ensure UI assets are generated."""
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src", "ui", "assets")
    
    # Check for PNG assets
    png_files = [f for f in os.listdir(assets_dir) if f.endswith('.png')]
    if len(png_files) < 4:  # We expect at least 4 PNG files (logo, idle, listening, speaking)
        logger.info("Generating UI assets...")
        # Run the asset generator
        from src.ui.generate_assets import main as generate_assets
        generate_assets()

def main():
    """Main function to run the voice assistant with GUI."""
    try:
        # Ensure recordings directory exists
        ensure_recordings_dir()
        
        # Ensure UI assets are generated
        ensure_assets()
        
        # Initialize the application
        app = QApplication(sys.argv)
        
        # Create the recording handler
        space_recorder = SpaceKeyRecorder()
        
        # Create and display the UI
        ui = VoiceAssistantUI(
            recording_handler=space_recorder,
            transcribe_func=transcribe_audio,
            chat_func=chat_with_gpt,
            tts_func=text_to_speech,
            play_func=play_audio,
            chunk_text_func=chunk_text_for_tts
        )
        ui.show()
        
        # Start the event loop
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting...")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
