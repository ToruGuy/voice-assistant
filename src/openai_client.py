#!/usr/bin/env python3
import json
import tempfile
import requests
import os
from datetime import datetime
from openai import OpenAI

from src.config import logger, API_KEY, CHAT_ENDPOINT, SPEECH_ENDPOINT, TRANSCRIPTION_ENDPOINT, DEFAULT_MODEL, TTS_MODEL, TTS_VOICE
from src.functions import AVAILABLE_FUNCTIONS, FUNCTION_DEFINITIONS

# Initialize the OpenAI client once
client = OpenAI(api_key=API_KEY)

# Global conversation history
conversation_history = []

def chat_with_gpt(user_message, stream=False):
    """Send a message to GPT and handle function calls.
    
    Args:
        user_message (str): The user's message
        stream (bool, optional): Whether to stream the response. Defaults to False.
    
    Returns:
        If stream=False: The assistant's response as a string
        If stream=True: A generator yielding response chunks
    """
    global conversation_history
    
    # Add user message to conversation history
    conversation_history.append({"role": "user", "content": user_message})
    
    logger.info(f"Sending message to model: {DEFAULT_MODEL}...")
    
    try:
        # Convert our function definitions to the format expected by the OpenAI SDK
        tools = FUNCTION_DEFINITIONS
        
        if stream:
            return chat_with_gpt_streaming(tools)
        
        # Call the OpenAI API using the SDK
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=conversation_history,
            tools=tools,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        
        # Check if there's a function call
        if assistant_message.tool_calls:
            tool_calls = assistant_message.tool_calls
            
            # Add the assistant's message with function call to history
            conversation_history.append(assistant_message.model_dump())
            
            # Process each function call
            for tool_call in tool_calls:
                if tool_call.type == "function":
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"Function call: {function_name} with args: {function_args}")
                    
                    # Execute function if it exists
                    if function_name in AVAILABLE_FUNCTIONS:
                        function_response = AVAILABLE_FUNCTIONS[function_name](**function_args)
                        
                        # Add function response to history
                        conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": function_name,
                            "content": json.dumps(function_response)
                        })
                        
                        logger.info(f"Function response: {function_response}")
                    else:
                        logger.warning(f"Function {function_name} not found")
                        
            # Get final response after function call
            return get_final_response()
        else:
            # No function call, just a regular response
            conversation_history.append(assistant_message.model_dump())
            return assistant_message.content
    
    except Exception as e:
        logger.error(f"Error in chat request: {str(e)}")
        return f"Sorry, there was an error communicating with the assistant: {str(e)}"

def chat_with_gpt_streaming(tools):
    """Stream the chat response from the OpenAI API.
    
    Returns:
        Generator: Yields response chunks as they arrive
    """
    try:
        # Call the OpenAI API using the SDK with streaming enabled
        response_stream = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=conversation_history,
            tools=tools,
            tool_choice="auto",
            stream=True
        )
        
        # Track the full message and tool calls
        full_content = ""
        current_tool_calls = []
        current_tool_call = None
        
        # Process the streaming response
        for chunk in response_stream:
            # Initialize an empty delta response to yield
            delta_response = {"content": ""}
            
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_content += content
                delta_response["content"] = content
                yield {"type": "content", "data": content}
            
            # Handle streamed tool calls if present
            if hasattr(chunk.choices[0].delta, 'tool_calls') and chunk.choices[0].delta.tool_calls:
                for tool_call_delta in chunk.choices[0].delta.tool_calls:
                    # Get the tool call index
                    index = tool_call_delta.index
                    
                    # Ensure we have enough elements in our tracking list
                    while len(current_tool_calls) <= index:
                        current_tool_calls.append({
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""}
                        })
                    
                    # Update the tool call information
                    if tool_call_delta.id:
                        current_tool_calls[index]["id"] = tool_call_delta.id
                    
                    if hasattr(tool_call_delta, 'function'):
                        if hasattr(tool_call_delta.function, 'name') and tool_call_delta.function.name:
                            current_tool_calls[index]["function"]["name"] = tool_call_delta.function.name
                        
                        if hasattr(tool_call_delta.function, 'arguments') and tool_call_delta.function.arguments:
                            current_tool_calls[index]["function"]["arguments"] += tool_call_delta.function.arguments
                    
                    # Update the delta response
                    delta_response["tool_calls"] = current_tool_calls
                    yield {"type": "tool_call_update", "data": current_tool_calls}
            
            # Handle finish reason
            if chunk.choices[0].finish_reason:
                yield {"type": "finish", "data": chunk.choices[0].finish_reason}
        
        # After streaming completes, handle tool calls if any were detected
        if current_tool_calls:
            # Create the complete assistant message to add to history
            assistant_message = {
                "role": "assistant",
                "content": full_content,
                "tool_calls": current_tool_calls
            }
            
            # Add the assistant's message to history
            conversation_history.append(assistant_message)
            
            # Process each function call
            for tool_call in current_tool_calls:
                if tool_call["type"] == "function":
                    function_name = tool_call["function"]["name"]
                    function_args = json.loads(tool_call["function"]["arguments"])
                    
                    logger.info(f"Function call: {function_name} with args: {function_args}")
                    
                    # Execute function if it exists
                    if function_name in AVAILABLE_FUNCTIONS:
                        function_response = AVAILABLE_FUNCTIONS[function_name](**function_args)
                        
                        # Add function response to history
                        conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": function_name,
                            "content": json.dumps(function_response)
                        })
                        
                        logger.info(f"Function response: {function_response}")
                        yield {"type": "function_response", "name": function_name, "data": function_response}
                    else:
                        logger.warning(f"Function {function_name} not found")
            
            # Get final response after function calls
            for chunk in get_final_response_streaming():
                yield chunk
        else:
            # No function calls, just add the assistant message to history
            conversation_history.append({
                "role": "assistant",
                "content": full_content
            })
    
    except Exception as e:
        logger.error(f"Error in streaming chat request: {str(e)}")
        yield {"type": "error", "data": f"Sorry, there was an error communicating with the assistant: {str(e)}"}

def get_final_response(stream=False):
    """Get the final response after function calls."""
    logger.info("Getting final response after function execution...")
    
    if stream:
        return get_final_response_streaming()
    
    try:
        # Call the OpenAI API using the SDK
        response = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=conversation_history,
            tools=FUNCTION_DEFINITIONS,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        
        # Add the final response to history
        conversation_history.append(assistant_message.model_dump())
        
        return assistant_message.content
    
    except Exception as e:
        logger.error(f"Error in final response request: {str(e)}")
        return f"Sorry, there was an error getting the final response: {str(e)}"

def get_final_response_streaming():
    """Stream the final response after function calls."""
    logger.info("Streaming final response after function execution...")
    
    try:
        # Call the OpenAI API using the SDK with streaming enabled
        response_stream = client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=conversation_history,
            tools=FUNCTION_DEFINITIONS,
            tool_choice="auto",
            stream=True
        )
        
        full_content = ""
        
        # Process the streaming response
        for chunk in response_stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_content += content
                yield {"type": "content", "data": content}
            
            # Handle finish reason
            if chunk.choices[0].finish_reason:
                yield {"type": "finish", "data": chunk.choices[0].finish_reason}
        
        # Add the final assistant message to history
        conversation_history.append({
            "role": "assistant",
            "content": full_content
        })
    
    except Exception as e:
        logger.error(f"Error in streaming final response request: {str(e)}")
        yield {"type": "error", "data": f"Sorry, there was an error getting the final response: {str(e)}"}

def text_to_speech(text, speed=1.0, instructions=None):
    """Convert text to speech using OpenAI's Text-to-Speech API.
    
    Args:
        text (str): The text to convert to speech
        speed (float, optional): The speed of the generated audio (0.25 to 4.0). Defaults to 1.0.
        instructions (str, optional): Control the voice style with additional instructions. 
                                     Does not work with tts-1 or tts-1-hd. Defaults to None.
    
    Returns:
        str: Path to the generated audio file or None if there was an error
    """
    logger.info("Converting text to speech...")
    
    try:
        # Prepare parameters
        params = {
            "model": TTS_MODEL,
            "voice": TTS_VOICE,
            "input": text,
            "speed": speed
        }
        
        # Add instructions if provided and if we're not using tts-1 or tts-1-hd
        if instructions and not TTS_MODEL.startswith("tts-1"):
            params["instructions"] = instructions
        
        # Use the OpenAI SDK for text-to-speech
        response = client.audio.speech.create(**params)
        
        # Save audio to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            response.stream_to_file(temp_file.name)
            temp_file_path = temp_file.name
        
        return temp_file_path
    
    except Exception as e:
        logger.error(f"Error in text-to-speech request: {str(e)}")
        return None

def clear_conversation_history():
    """Clear the conversation history."""
    global conversation_history
    conversation_history = []
    logger.info("Conversation history cleared.")

def transcribe_audio(audio_data):
    """Transcribe audio data using OpenAI's Whisper API."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temp_file:
        temp_file.write(audio_data.getvalue())
        temp_file.flush()
        
        logger.info("Transcribing audio...")
        
        # Use the existing global client instead of creating a new one
        try:
            with open(temp_file.name, "rb") as audio_file:
                # Use the OpenAI SDK to transcribe the audio
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
                
                logger.info(f"Transcription: {transcription.text}")
                
                # Save transcription to a text file
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                transcript_path = os.path.join(os.getcwd(), "recordings", f"transcript_{timestamp}.txt")
                
                with open(transcript_path, 'w') as f:
                    f.write(transcription.text)
                    
                logger.info(f"Transcription saved to {transcript_path}")
                
                return transcription.text
        except Exception as e:
            logger.error(f"Transcription failed: {str(e)}")
            return None
