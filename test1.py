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

# --- Session Creation ---
def create_session(api_key):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "gpt-4o-realtime-preview-2024-12-17",
        "modalities": ["audio", "text"],
        "instructions": "You are a friendly assistant."
    }
    logging.info("Creating session...")
    response = requests.post(SESSION_ENDPOINT, headers=headers, json=payload)
    if response.status_code == 200:
        session_data = response.json()
        logging.info("Session created: %s", session_data)
        return session_data
    else:
        logging.error("Failed to create session: %s", response.text)
        sys.exit(1)

# --- WebSocket Communication ---
async def websocket_handler(uri, audio_queue):
    async with websockets.connect(uri) as ws:
        logging.info("WebSocket connected to %s", uri)
        # Create a task to receive messages
        receiver_task = asyncio.create_task(receive_messages(ws))
        try:
            # Continuously send events from the audio_queue.
            while True:
                event = await audio_queue.get()
                if event is None:  # Sentinel value to close
                    break
                await ws.send(json.dumps(event))
                logging.info("Sent event: %s", event["type"])
        except Exception as e:
            logging.error("Error sending event: %s", e)
        finally:
            receiver_task.cancel()

async def receive_messages(ws):
    try:
        async for message in ws:
            event = json.loads(message)
            process_event(event)
    except Exception as e:
        logging.error("Error receiving messages: %s", e)

def process_event(event):
    # Log all received events for debugging.
    logging.info("Received event: %s", event)
    # Add additional handling for specific events if needed.
    if event.get("type") == "response.done":
        logging.info("Response completed: %s", event)
    # Handle function calls here if required.

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
        logging.error("Error opening audio stream: %s", e)
        return

    logging.info("Audio capture started. Speak continuously; press Enter to commit the current buffer.")
    audio_frames = []  # Optional: store frames locally if needed

    try:
        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception as e:
                logging.error("Error reading audio chunk: %s", e)
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
                # Optional: clear the local audio buffer if needed
                audio_frames = []
    except Exception as e:
        logging.error("Error in audio capture thread: %s", e)
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

# --- Main Function (Updated) ---
def main():
    # Create session with OpenAI Realtime API
    session_data = create_session(API_KEY)
    session_id = session_data["id"]
    client_secret = session_data["client_secret"]["value"]

    # Update the WebSocket URI to remove token from query params.
    ws_uri = f"wss://api.openai.com/v1/realtime/sessions/{session_id}"
    logging.info("WebSocket URI: %s", ws_uri)

    # Create an asyncio queue to hold audio events
    audio_queue = asyncio.Queue()

    # Get the running event loop
    loop = asyncio.get_event_loop()

    # Start the audio capture thread
    audio_thread = threading.Thread(target=audio_capture_thread, args=(audio_queue, loop), daemon=True)
    audio_thread.start()

    # Start a separate thread to listen for manual commit triggers
    commit_thread = threading.Thread(target=wait_for_commit_trigger, daemon=True)
    commit_thread.start()

    try:
        # Run the WebSocket handler (this call blocks)
        loop.run_until_complete(websocket_handler(ws_uri, audio_queue, client_secret))
    except KeyboardInterrupt:
        logging.info("Interrupted by user. Shutting down...")
    finally:
        # Signal the audio_queue to close and wait a bit for threads to wrap up.
        loop.run_until_complete(audio_queue.put(None))
        time.sleep(1)

# --- Updated WebSocket Communication ---
async def websocket_handler(uri, audio_queue, client_secret):
    async with websockets.connect(uri, extra_headers={"Authorization": f"Bearer {client_secret}"}) as ws:
        logging.info("WebSocket connected to %s", uri)
        # Create a task to receive messages
        receiver_task = asyncio.create_task(receive_messages(ws))
        try:
            # Continuously send events from the audio_queue.
            while True:
                event = await audio_queue.get()
                if event is None:  # Sentinel value to close
                    break
                await ws.send(json.dumps(event))
                logging.info("Sent event: %s", event["type"])
        except Exception as e:
            logging.error("Error sending event: %s", e)
        finally:
            receiver_task.cancel()

if __name__ == "__main__":
    main()