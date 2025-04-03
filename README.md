# Voice Assistant

A real-time voice assistant built with Python and OpenAI, designed to process voice commands, execute functions, and respond with natural speech.

## Features

- **Voice Recognition**: Press and hold SPACE to record voice input
- **Natural Language Processing**: Powered by OpenAI's GPT models
- **Text-to-Speech**: Converts responses to natural speech
- **Response Streaming**: Processes responses in real-time
- **Function Calling**: Executes commands based on voice input
- **Simple Interface**: Keyboard-based recording system

## Technology Stack

- Python
- OpenAI API (GPT models, transcription, TTS)
- PyAudio

## Getting Started

### Prerequisites

- Python 3.7+
- OpenAI API key

### Installation

1. Clone the repository
   ```
   git clone https://github.com/ToruGuy/voice-assistant.git
   cd voice-assistant
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

4. Create a `.env` file with your OpenAI API key
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

### Usage

Run the voice assistant:
```
python voice_assistant.py
```

- Press and hold SPACE to record
- Release to process your query
- Press ESC to exit

For GUI version:
```
python voice_assistant_gui.py
```

## Project Structure

- `voice_assistant.py`: Command-line interface
- `voice_assistant_gui.py`: Graphical user interface
- `src/`: Core modules
  - `audio_handler.py`: Recording and playback
  - `openai_client.py`: OpenAI API integration
  - `functions.py`: Function calling capabilities
  - `config.py`: Configuration settings
  - `utils.py`: Utility functions
- `recordings/`: Stores audio recordings and logs
- `my-input/`: Input files for the assistant

## Key Features

### Response Streaming

The assistant processes responses as they arrive from the OpenAI API:

- Improved responsiveness with real-time feedback
- More natural conversational flow
- Efficient handling of function calls

### Function Calling

Currently implemented functions:
- `calculate_sum`: Adds numbers
- `get_current_time`: Returns current time

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*Built with Python and OpenAI*
