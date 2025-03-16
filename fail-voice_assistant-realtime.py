#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env

import asyncio
import websockets
import requests
import json
import base64
import pyaudio
import threading
import time
import logging
import sys

# Retrieve API key from environment variables
API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    logging.error("OPENAI_API_KEY not set. Please set it in the .env file.")
    sys.exit(1)

# API Endpoints
SESSION_ENDPOINT = "https://api.openai.com/v1/realtime/sessions"

# Audio configuration (PCM16, 24kHz, mono)
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 24000         # 24 kHz sample rate
CHUNK = 1024         # Frames per buffer

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# A threading.Event to trigger manual commit from user input
commit_event_flag = threading.Event()

# --- Function Calling Definitions ---
# Sample function for demonstration - we'll implement a simple calculator
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return {"result": a + b}

def get_current_time():
    """Get the current time."""
    return {"time": time.strftime("%Y-%m-%d %H:%M:%S")}

# Map of available functions
AVAILABLE_FUNCTIONS = {
    "calculate_sum": calculate_sum,
    "get_current_time": get_current_time
}

# Function definitions to send to the LLM
FUNCTION_DEFINITIONS = [
    {
        "type": "function",
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
    },
    {
        "type": "function",
        "name": "get_current_time",
        "description": "Get the current time",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
]

# --- Session Creation ---
def create_session(api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-realtime-preview",  # Using the correct Realtime model for voice assistant functionality
        "modalities": ["audio", "text"],
        "instructions": "You are a friendly assistant. When asked about calculations, make use of the calculate_sum function.",
        "tools": FUNCTION_DEFINITIONS
    }
    logging.info("Creating session...")
    try:
        response = requests.post(SESSION_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        session_data = response.json()
        logging.info(f"Session created successfully with ID: {session_data['id']}")
        return session_data
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to create session: {e}")
        if hasattr(e, 'response') and e.response:
            logging.error(f"Response: {e.response.text}")
        sys.exit(1)

# --- WebSocket Communication ---
async def websocket_handler(session_id, client_secret, audio_queue):
    # Note: We need to connect to the WebSocket with API KEY, not client_secret
    uri = f"wss://api.openai.com/v1/realtime/sessions/{session_id}?token={API_KEY}"
    
    # Create a connection
    async with websockets.connect(uri) as ws:
        # Wait for the session.created event before proceeding
        session_created = False
        while not session_created:
            message = await ws.recv()
            event = json.loads(message)
            if event.get("type") == "session.created":
                session_created = True
                logging.info("Session created confirmation received")
        logging.info(f"WebSocket connected to {uri}")
        
        # Create a task to receive messages
        receiver_task = asyncio.create_task(receive_messages(ws, audio_queue))
        
        try:
            # Continuously send events from the audio_queue
            while True:
                event = await audio_queue.get()
                if event is None:  # Sentinel value to close
                    break
                await ws.send(json.dumps(event))
                logging.info(f"Sent event: {event['type']}")
        except Exception as e:
            logging.error(f"Error sending event: {str(e)}")
        finally:
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass

async def receive_messages(ws, audio_queue):
    try:
        async for message in ws:
            event = json.loads(message)
            await process_event(event, ws, audio_queue)
    except Exception as e:
        logging.error(f"Error receiving messages: {str(e)}")

async def process_event(event, ws, audio_queue):
    event_type = event.get("type")
    logging.info(f"Received event: {event_type}")
    
    if event_type == "session.created":
        logging.info("Session created and connected")
    
    elif event_type == "response.message.content.part":
        # Handle text content from the assistant
        if "text" in event:
            text = event.get("text", "")
            if text:
                print(f"\nAssistant: {text}", end="", flush=True)
    
    elif event_type == "response.item.function_call":
        # Handle function call request
        function_call = event.get("function_call", {})
        function_name = function_call.get("name")
        function_args = json.loads(function_call.get("arguments", "{}"))
        
        logging.info(f"Function call requested: {function_name} with args: {function_args}")
        
        # Execute the function if it exists
        if function_name in AVAILABLE_FUNCTIONS:
            try:
                result = AVAILABLE_FUNCTIONS[function_name](**function_args)
                
                # Send function call result back
                function_result_event = {
                    "event_id": f"event_func_result_{int(time.time()*1000)}",
                    "type": "conversation.item.create",
                    "item": {
                        "type": "function_output",
                        "parent_item_id": event.get("item_id"),
                        "name": function_name,
                        "content": json.dumps(result)
                    }
                }
                
                await ws.send(json.dumps(function_result_event))
                logging.info(f"Sent function result for {function_name}: {result}")
            except Exception as e:
                logging.error(f"Error executing function {function_name}: {str(e)}")
        else:
            logging.warning(f"Function {function_name} not found")
    
    elif event_type == "response.done":
        logging.info("Response completed")
        print("\n")  # Add a newline after assistant's response is complete

# --- Audio Capture and Manual Commit ---
def audio_capture_thread(audio_queue, loop):
    p = pyaudio.PyAudio()
    try:
        stream = p.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK)
    except Exception as e:
        logging.error(f"Error opening audio stream: {str(e)}")
        return

    logging.info("Audio capture started. Speak continuously; press Enter to commit the current buffer.")
    audio_frames = []  # Store frames locally if needed

    try:
        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception as e:
                logging.error(f"Error reading audio chunk: {str(e)}")
                continue

            audio_frames.append(data)
            # Base64 encode the audio chunk and create an append event
            encoded_audio = base64.b64encode(data).decode("utf-8")
            append_event = {
                "event_id": f"event_{int(time.time()*1000)}",
                "type": "input_audio_buffer.append",
                "audio": encoded_audio
            }
            # Send the event to the asyncio queue
            asyncio.run_coroutine_threadsafe(audio_queue.put(append_event), loop)

            # Check for manual commit trigger
            if commit_event_flag.is_set():
                commit_event_flag.clear()
                commit_event = {
                    "event_id": f"event_commit_{int(time.time()*1000)}",
                    "type": "input_audio_buffer.commit"
                }
                asyncio.run_coroutine_threadsafe(audio_queue.put(commit_event), loop)
                logging.info("Audio buffer committed (manual trigger).")
                print("\nYou: [Audio input sent]")  # Visual feedback
                
                # Generate a response
                create_response_event = {
                    "event_id": f"event_response_{int(time.time()*1000)}",
                    "type": "response.create",
                    "response": {
                        "modalities": ["text", "audio"],
                        "tools": FUNCTION_DEFINITIONS,
                        "tool_choice": "auto"
                    }
                }
                asyncio.run_coroutine_threadsafe(audio_queue.put(create_response_event), loop)
                
                # Clear the local audio buffer
                audio_frames = []
    except Exception as e:
        logging.error(f"Error in audio capture thread: {str(e)}")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()
        logging.info("Audio capture terminated.")

def wait_for_commit_trigger():
    """
    Blocks waiting for the user to press Enter.
    When Enter is pressed, set the commit flag.
    """
    while True:
        input("Press Enter to commit audio...\n")
        commit_event_flag.set()

# --- Text Mode for Testing ---
def text_input_thread(audio_queue, loop):
    """
    Alternative to audio capture for testing with text input.
    """
    while True:
        user_input = input("\nYou (text mode): ")
        
        if user_input.lower() in ['exit', 'quit']:
            break
            
        # Create a text message event
        text_event = {
            "event_id": f"event_text_{int(time.time()*1000)}",
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": user_input
                    }
                ]
            }
        }
        asyncio.run_coroutine_threadsafe(audio_queue.put(text_event), loop)
        
        # Generate a response
        create_response_event = {
            "event_id": f"event_response_{int(time.time()*1000)}",
            "type": "response.create",
            "response": {
                "modalities": ["text"],
                "tools": FUNCTION_DEFINITIONS,
                "tool_choice": "auto"
            }
        }
        asyncio.run_coroutine_threadsafe(audio_queue.put(create_response_event), loop)

# --- Main Function ---
async def main_async():
    # Create session with OpenAI Realtime API
    session_data = create_session(API_KEY)
    session_id = session_data["id"]
    client_secret = session_data["client_secret"]["value"]

    # Create an asyncio queue to hold events
    audio_queue = asyncio.Queue()

    # Choose input mode
    mode = input("Select input mode (1 for audio, 2 for text): ")
    
    if mode == "1":
        # Start the audio capture thread
        audio_thread = threading.Thread(
            target=audio_capture_thread, 
            args=(audio_queue, asyncio.get_event_loop()), 
            daemon=True
        )
        audio_thread.start()

        # Start a separate thread to listen for manual commit triggers
        commit_thread = threading.Thread(
            target=wait_for_commit_trigger, 
            daemon=True
        )
        commit_thread.start()
    else:
        # Start the text input thread for testing
        text_thread = threading.Thread(
            target=text_input_thread, 
            args=(audio_queue, asyncio.get_event_loop()), 
            daemon=True
        )
        text_thread.start()

    try:
        # Run the WebSocket handler
        await websocket_handler(session_id, client_secret, audio_queue)
    except KeyboardInterrupt:
        logging.info("Interrupted by user. Shutting down...")
    finally:
        # Signal the audio_queue to close
        await audio_queue.put(None)

def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    main()
