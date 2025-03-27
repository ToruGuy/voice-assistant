# Voice Assistant

A real-time voice assistant built with Python and OpenAI, designed to process voice commands, execute functions, and respond with natural speech.

## Features

- **Voice Recognition**: Press and hold the SPACE key to record your voice input
- **Natural Language Processing**: Uses OpenAI's GPT-4o-mini model to understand and respond to queries
- **Text-to-Speech**: Converts responses to natural-sounding speech using OpenAI's TTS
- **Response Streaming**: Receives and processes responses in real-time as they're generated
- **Function Calling**: Executes functions based on voice commands
- **Simple Interface**: Easy-to-use keyboard-based recording system

## Technology Stack

- **Python**: Core programming language
- **OpenAI API**: Powers the AI capabilities (GPT models, transcription, TTS)
- **PyAudio**: Handles audio recording and playback
- **Websockets & Requests**: For API communication

## Getting Started

### Prerequisites

- Python 3.7+
- OpenAI API key

### Installation

1. Clone the repository
   ```
   git clone https://github.com/yourusername/VoiceAssistant.git
   cd VoiceAssistant
   ```

2. Create a virtual environment
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory with your OpenAI API key
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

### Usage

Run the voice assistant:
```
python voice_assistant.py
```

- Press and hold the SPACE key to record your voice
- Release to process your query
- Press ESC to exit

## Project Structure

- `voice_assistant.py`: Main entry point
- `src/`
  - `audio_handler.py`: Handles recording and audio processing
  - `audio_recorder.py`: Low-level audio recording functionality
  - `config.py`: Configuration settings
  - `functions.py`: Defines available functions for the assistant
  - `openai_client.py`: OpenAI API integration with streaming support
  - `utils.py`: Utility functions
- `recordings/`: Stores recordings and response logs
- `my-input/`: Input files for the assistant

## Function Calling

The assistant can execute predefined functions. Currently implemented:

- `calculate_sum`: Adds two numbers
- `get_current_time`: Returns the current time

## Key Features Explained

### Response Streaming

The assistant processes responses as they arrive from the OpenAI API rather than waiting for the complete response. This provides:

- Improved responsiveness with near real-time feedback
- More natural conversational flow
- Better handling of function calls in streaming mode
- Support for both streaming and non-streaming modes

## Future Development

Plans for enhancement include:

- Expanded function calling to execute real-world tasks
- Real-time response capabilities
- Integration with other services and APIs
- Persistent conversation memory
- Custom voice and personality settings

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- OpenAI for providing the API services
- Contributors and testers

---

*This project is designed to be a foundation for building more complex voice-driven applications with real-time function execution capabilities.*
