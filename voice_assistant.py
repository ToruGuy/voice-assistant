#!/usr/bin/env python3
import os
import sys
from datetime import datetime

# Import from our custom modules
from config import logger
from audio_handler import SpaceKeyRecorder, transcribe_audio, play_audio
from openai_client import chat_with_gpt, text_to_speech, clear_conversation_history

def ensure_recordings_dir():
    """Ensure the recordings directory exists."""
    recordings_dir = os.path.join(os.getcwd(), "recordings")
    if not os.path.exists(recordings_dir):
        os.makedirs(recordings_dir)
        logger.info(f"Created recordings directory: {recordings_dir}")

def main():
    """Main function to run the voice assistant."""
    try:
        # Ensure recordings directory exists
        ensure_recordings_dir()
        
        # Display initial instructions
        print("\nVoice Assistant with OpenAI")
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
                
                # Text to speech
                audio_path = text_to_speech(response)
                if audio_path:
                    # Play the generated speech
                    play_audio(audio_path)
                    
                    # Clean up the temporary audio file
                    os.remove(audio_path)
                
        except KeyboardInterrupt:
            print("\nExiting voice assistant. Goodbye!")
            
    finally:
        # Clean up resources
        if 'space_recorder' in locals():
            space_recorder.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProgram interrupted by user. Exiting...")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()