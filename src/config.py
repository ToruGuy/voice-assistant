#!/usr/bin/env python3
import os
import logging
import sys
import pyaudio
from dotenv import load_dotenv

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

# Default model settings
DEFAULT_MODEL = "gpt-4o-mini"  # Using o3-mini as default per user preferences
TTS_MODEL = "tts-1"
TTS_VOICE = "alloy"
