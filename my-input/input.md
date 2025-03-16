# Voice Assistant with LLM POC

## Goal
- Build a proof-of-concept (POC) voice assistant that leverages an LLM (e.g., GPT-4) with function calling capabilities.
- Demonstrate real-time audio capture, manual commit of the audio buffer, and basic function call handling.
- Keep the design minimal, yet fully functional for rapid prototyping on macOS using Python.

## Mission
- **Showcase Core Capabilities:**  
  Establish a working prototype that creates a session with the LLM, captures and sends audio, and processes responses—including simple function calls.
- **Focus on Simplicity:**  
  Use manual triggers for audio commit and a straightforward WebSocket-based communication for ease of development.
- **Ensure Extensibility:**  
  Provide a solid foundation to add more features (e.g., server-side VAD, audio playback for debugging, additional function calls) later.

## Requirements

### Functional Requirements
- **Session Management:**  
  - Create a session with the LLM using a REST API call.
  - Retrieve and store session details (session ID, client secret, configuration parameters).

- **Audio Capture & Commit:**  
  - Capture audio from the microphone in PCM16 format (24kHz, mono).
  - Send audio in small chunks as Base64 encoded strings.
  - Use a manual commit trigger (e.g., press Enter) to indicate end-of-speech.

- **WebSocket Communication:**  
  - Establish a persistent WebSocket connection to the LLM endpoint.
  - Send audio events and receive responses.
  - Authenticate the connection using the client secret in the Authorization header.

- **Response & Function Handling:**  
  - Process incoming events (e.g., `response.done`) and log them.
  - Detect and handle function call events by executing local functions and sending back results.

### Non-Functional Requirements
- **Platform:**  
  - Develop and test on macOS using Python.
  
- **Performance:**  
  - Aim for real-time (or near real-time) responsiveness in audio capture and processing.
  
- **Debugging & Logging:**  
  - Log all sent and received events.
  - Optionally enable audio playback only in debug mode for testing.
  
- **Security:**  
  - Use environment variables (.env) to securely store API keys.
  
- **Simplicity:**  
  - Keep the architecture minimal and modular to facilitate rapid prototyping and easy future enhancements.

## Architecture

### High-Level Components
- **Session Manager:**  
  - Responsible for creating a session with the LLM via the REST API.
  - Retrieves the session ID and client secret needed for subsequent communication.

- **WebSocket Manager:**  
  - Establishes and maintains a WebSocket connection to the LLM.
  - Sends audio events (append and commit) and receives response events.
  - Uses the client secret for authentication via HTTP headers.

- **Audio Handler:**  
  - Captures audio from the microphone using PyAudio.
  - Encodes audio data in Base64.
  - Implements manual commit (via a user key press) to trigger the end of an audio segment.

- **Conversation Manager:**  
  - Maintains conversation state (tracking messages and responses).
  - Logs all events for debugging and further processing.

- **Function Call Handler:**  
  - Detects function call events.
  - Executes local functions (e.g., calculate sum, get weather) when triggered.
  - Sends function results back as part of the conversation.