#!/usr/bin/env python3
import os
import sys
import json
import argparse
from datetime import datetime

# Import from our custom modules
from src.config import logger
from src.audio_handler import SpaceKeyRecorder, transcribe_audio, play_audio
from src.openai_client import chat_with_gpt, text_to_speech, clear_conversation_history
# Import our MCP wrapper
from src.mcp_client import _mcp_wrapper

def ensure_recordings_dir():
    """Ensure the recordings directory exists."""
    recordings_dir = os.path.join(os.getcwd(), "recordings")
    if not os.path.exists(recordings_dir):
        os.makedirs(recordings_dir)
        logger.info(f"Created recordings directory: {recordings_dir}")

def configure_mcp(args):
    """Configure MCP servers based on command line arguments."""
    
    if args.list_servers:
        print("\nConfigured MCP Servers:")
        print("------------------------")
        servers = _mcp_wrapper.get_servers()
        for server_id, server in servers.items():
            status = "Enabled" if server.get("enabled", False) else "Disabled"
            print(f"ID: {server_id}")
            print(f"  Name: {server.get('name', 'Unnamed')}")
            print(f"  URL: {server.get('url', 'No URL')}")
            print(f"  Status: {status}\n")
        return True
    
    if args.add_server:
        parts = args.add_server.split(',')
        if len(parts) < 3:
            print("Error: Adding a server requires ID,NAME,URL format")
            return False
        
        server_id, name, url = parts[0], parts[1], parts[2]
        enabled = True if len(parts) <= 3 or parts[3].lower() in ('true', 'yes', '1') else False
        
        _mcp_wrapper.add_server(server_id, name, url, enabled)
        print(f"Added MCP server: {name} at {url} (Enabled: {enabled})")
        return True
    
    if args.enable_server:
        if _mcp_wrapper.enable_server(args.enable_server):
            print(f"Enabled MCP server: {args.enable_server}")
        else:
            print(f"Error: Server {args.enable_server} not found")
        return True
    
    if args.disable_server:
        if _mcp_wrapper.disable_server(args.disable_server):
            print(f"Disabled MCP server: {args.disable_server}")
        else:
            print(f"Error: Server {args.disable_server} not found")
        return True
    
    if args.remove_server:
        if _mcp_wrapper.remove_server(args.remove_server):
            print(f"Removed MCP server: {args.remove_server}")
        else:
            print(f"Error: Server {args.remove_server} not found")
        return True
    
    return False

def main():
    """Main function to run the voice assistant."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Voice Assistant with OpenAI and MCP support")
    
    # MCP configuration arguments
    mcp_group = parser.add_argument_group('MCP Configuration')
    mcp_group.add_argument('--list-servers', action='store_true', help='List configured MCP servers')
    mcp_group.add_argument('--add-server', metavar='ID,NAME,URL[,ENABLED]', help='Add a new MCP server')
    mcp_group.add_argument('--enable-server', metavar='ID', help='Enable an MCP server')
    mcp_group.add_argument('--disable-server', metavar='ID', help='Disable an MCP server')
    mcp_group.add_argument('--remove-server', metavar='ID', help='Remove an MCP server')
    
    args = parser.parse_args()
    
    # Handle MCP configuration if needed
    if configure_mcp(args):
        return
    
    try:
        # Ensure recordings directory exists
        ensure_recordings_dir()
        
        # Display initial instructions
        print("\nVoice Assistant with OpenAI and MCP")
        print("----------------------------------")
        print("Press and hold SPACE to record, release to stop.")
        print("Press ESC to exit.\n")
        
        # Initialize MCP wrapper (happens automatically on import)
        enabled_servers = _mcp_wrapper.get_enabled_servers()
        if enabled_servers:
            print(f"MCP enabled with {len(enabled_servers)} active servers:")
            for server in enabled_servers:
                print(f"  - {server.get('name', 'Unnamed')} ({server.get('url', 'No URL')})")
        else:
            print("MCP is disabled. Use --list-servers to see available servers")
            print("and --enable-server ID to enable a server.")
        print()
        
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