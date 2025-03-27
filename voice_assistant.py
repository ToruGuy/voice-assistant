#!/usr/bin/env python3
import os
import sys
from datetime import datetime

# Import from our custom modules
from src.config import logger
from src.audio_handler import SpaceKeyRecorder, play_audio
from src.openai_client import chat_with_gpt, text_to_speech, clear_conversation_history, transcribe_audio
from src.utils import chunk_text_for_tts

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
                print("\nAssistant: ", end="", flush=True)
                full_response = ""
                current_buffer = ""  # Buffer for accumulating text chunks
                
                for chunk in chat_with_gpt(transcription, True):
                    if chunk["type"] == "content":
                        content = chunk["data"]
                        full_response += content
                        print(content, end="", flush=True)
                        
                        # Process text using the chunking utility
                        chunk_to_process, current_buffer = chunk_text_for_tts(content, current_buffer)
                        
                        if chunk_to_process:
                            # Generate and play speech for this chunk
                            logger.info(f"Converting chunk to speech: '{chunk_to_process}'")
                            chunk_audio_path = text_to_speech(chunk_to_process, 2.0)
                            if chunk_audio_path:
                                # Play the generated chunk speech without blocking
                                play_audio(chunk_audio_path, block=False)
                    elif chunk["type"] == "function_response":
                        # Log function responses if needed
                        logger.info(f"Function {chunk['name']} returned: {chunk['data']}")
                    elif chunk["type"] == "error":
                        # Handle errors
                        logger.error(f"Error in streaming: {chunk['data']}")
                        full_response += f"\nError: {chunk['data']}"
                        print(f"\nError: {chunk['data']}")
                
                print()  # Add newline after streaming completes
                
                # Process any remaining text in buffer
                if current_buffer.strip():
                    logger.info(f"Converting final chunk to speech: '{current_buffer}'")
                    chunk_audio_path = text_to_speech(current_buffer, 2.0)
                    if chunk_audio_path:
                        play_audio(chunk_audio_path, block=True)
                
                # Save response to file for debugging
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                response_path = os.path.join(os.getcwd(), "recordings", f"response_{timestamp}.txt")
                with open(response_path, 'w') as f:
                    f.write(full_response)
                print(f"Response saved to: {response_path}")
                
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