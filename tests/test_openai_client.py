import io
import json
import os
import tempfile
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch
import src.openai_client as openai_client
# Import functions and global variables from openai_client.py
from src.openai_client import (
    chat_with_gpt,
    chat_with_gpt_streaming,
    get_final_response,
    get_final_response_streaming,
    text_to_speech,
    clear_conversation_history,
    transcribe_audio,
    conversation_history,
    FUNCTION_DEFINITIONS,  # Used for streaming tests
    AVAILABLE_FUNCTIONS  # May be useful for extended testing
)

# Dummy classes to simulate OpenAI API responses.
class DummyMessage:
    def __init__(self, content, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []
    
    def model_dump(self):
        return {"role": "assistant", "content": self.content, "tool_calls": self.tool_calls}

class DummyChoice:
    def __init__(self, content, tool_calls=None):
        self.message = DummyMessage(content, tool_calls)

class DummyResponse:
    def __init__(self, choices):
        self.choices = choices

# Helper to simulate streaming responses.
def dummy_streaming_response(chunks):
    for chunk in chunks:
        yield chunk

class DummyChunk:
    def __init__(self, content="", finish_reason=None, tool_calls_delta=None):
        self.choices = [MagicMock()]
        self.choices[0].delta = MagicMock()
        self.choices[0].delta.content = content
        # Optionally simulate tool call deltas.
        self.choices[0].delta.tool_calls = tool_calls_delta if tool_calls_delta else None
        self.choices[0].finish_reason = finish_reason

class OpenAIClientTests(unittest.TestCase):
    def setUp(self):
        # Clear conversation history before each test
        clear_conversation_history()

    @patch("src.openai_client.client.chat.completions.create")
    def test_chat_with_gpt_exception(self, mock_create):
        # Force an exception to test error handling.
        mock_create.side_effect = Exception("API failure")
        response = chat_with_gpt("Hello")
        self.assertIn("Sorry, there was an error communicating with the assistant", response)

    @patch("src.openai_client.client.chat.completions.create")
    def test_get_final_response(self, mock_create):
        dummy_choice = DummyChoice("Final response")
        mock_create.return_value = DummyResponse([dummy_choice])
        response = get_final_response()
        self.assertEqual(response, "Final response")

    @patch("src.openai_client.client.chat.completions.create")
    def test_get_final_response_exception(self, mock_create):
        mock_create.side_effect = Exception("Final response failure")
        response = get_final_response()
        self.assertIn("Sorry, there was an error getting the final response", response)

    @patch("src.openai_client.client.audio.speech.create")
    def test_text_to_speech(self, mock_speech_create):
        # Create a dummy response that writes audio data to a file.
        dummy_response = MagicMock()
        dummy_response.stream_to_file = lambda file_path: open(file_path, "wb").write(b"audio data")
        mock_speech_create.return_value = dummy_response
        
        file_path = text_to_speech("Hello world")
        self.assertTrue(os.path.exists(file_path))
        # Clean up the temporary file.
        os.remove(file_path)

    @patch("src.openai_client.client.audio.transcriptions.create")
    def test_transcribe_audio(self, mock_transcribe_create):
        # Set up a dummy transcription response.
        dummy_transcription = MagicMock()
        dummy_transcription.text = "Transcribed text"
        mock_transcribe_create.return_value = dummy_transcription
        
        # Create a dummy audio stream.
        audio_data = io.BytesIO(b"dummy audio data")
        # Create a recordings directory if it does not exist.
        recordings_dir = os.path.join(os.getcwd(), "recordings")
        os.makedirs(recordings_dir, exist_ok=True)
        
        transcription_text = transcribe_audio(audio_data)
        self.assertEqual(transcription_text, "Transcribed text")
        
        # Verify that a transcript file was created.
        transcript_files = os.listdir(recordings_dir)
        self.assertTrue(any("transcript_" in filename for filename in transcript_files))
        
        # Clean up created files.
        for filename in transcript_files:
            os.remove(os.path.join(recordings_dir, filename))
        os.rmdir(recordings_dir)

    @patch("src.openai_client.client.chat.completions.create")
    def test_chat_with_gpt_streaming_no_tool_calls(self, mock_create):
        # Simulate streaming content without tool call updates.
        chunks = [
            DummyChunk(content="Chunk 1, "),
            DummyChunk(content="Chunk 2", finish_reason="stop")
        ]
        mock_create.return_value = dummy_streaming_response(chunks)
        
        outputs = list(chat_with_gpt_streaming(FUNCTION_DEFINITIONS))
        content_chunks = [chunk for chunk in outputs if chunk["type"] == "content"]
        finish_chunks = [chunk for chunk in outputs if chunk["type"] == "finish"]
        
        combined_content = "".join(chunk["data"] for chunk in content_chunks)
        self.assertEqual(combined_content, "Chunk 1, Chunk 2")
        self.assertTrue(any(chunk["data"] == "stop" for chunk in finish_chunks))

    @patch("src.openai_client.client.chat.completions.create")
    def test_get_final_response_streaming(self, mock_create):
        chunks = [
            DummyChunk(content="Final chunk 1, "),
            DummyChunk(content="Final chunk 2", finish_reason="stop")
        ]
        mock_create.return_value = dummy_streaming_response(chunks)
        
        outputs = list(get_final_response_streaming())
        content = "".join(chunk["data"] for chunk in outputs if chunk["type"] == "content")
        self.assertEqual(content, "Final chunk 1, Final chunk 2")
        self.assertTrue(any(chunk["data"] == "stop" for chunk in outputs if chunk["type"] == "finish"))

if __name__ == "__main__":
    unittest.main()
