#!/usr/bin/env python3
import json
import tempfile
import requests

from config import logger, API_KEY, CHAT_ENDPOINT, SPEECH_ENDPOINT, DEFAULT_MODEL, TTS_MODEL, TTS_VOICE
from functions import AVAILABLE_FUNCTIONS, FUNCTION_DEFINITIONS

# Global conversation history
conversation_history = []

def chat_with_gpt(user_message):
    """Send a message to GPT and handle function calls."""
    global conversation_history
    
    # Add user message to conversation history
    conversation_history.append({"role": "user", "content": user_message})
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Use default model from config (o3-mini by default)
    payload = {
        "model": DEFAULT_MODEL,
        "messages": conversation_history,
        "tools": FUNCTION_DEFINITIONS,
        "tool_choice": "auto"
    }
    
    logger.info(f"Sending message to model: {DEFAULT_MODEL}...")
    
    try:
        response = requests.post(CHAT_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        assistant_message = response_data["choices"][0]["message"]
        
        # Check if there's a function call
        if "tool_calls" in assistant_message:
            tool_calls = assistant_message["tool_calls"]
            
            # Add the assistant's message with function call to history
            conversation_history.append(assistant_message)
            
            # Process each function call
            for tool_call in tool_calls:
                if tool_call["type"] == "function":
                    function_call = tool_call["function"]
                    function_name = function_call["name"]
                    function_args = json.loads(function_call["arguments"])
                    
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
                    else:
                        logger.warning(f"Function {function_name} not found")
                        
            # Get final response after function call
            return get_final_response()
        else:
            # No function call, just a regular response
            conversation_history.append(assistant_message)
            return assistant_message["content"]
    
    except requests.RequestException as e:
        logger.error(f"Error in chat request: {str(e)}")
        return f"Sorry, there was an error communicating with the assistant: {str(e)}"

def get_final_response():
    """Get the final response after function calls."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Important: Use the same model as in chat_with_gpt and include tools parameter
    payload = {
        "model": DEFAULT_MODEL,  # Match the model used in the initial request
        "messages": conversation_history,
        "tools": FUNCTION_DEFINITIONS,  # Include function definitions
        "tool_choice": "auto"  # Let the model decide whether to call functions
    }
    
    logger.info("Getting final response after function execution...")
    
    try:
        response = requests.post(CHAT_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        response_data = response.json()
        assistant_message = response_data["choices"][0]["message"]
        
        # Add the final response to history
        conversation_history.append(assistant_message)
        
        return assistant_message["content"]
    
    except requests.RequestException as e:
        logger.error(f"Error in final response request: {str(e)}")
        return f"Sorry, there was an error getting the final response: {str(e)}"

def text_to_speech(text):
    """Convert text to speech using OpenAI's Text-to-Speech API."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": TTS_MODEL,
        "input": text,
        "voice": TTS_VOICE
    }
    
    logger.info("Converting text to speech...")
    
    try:
        response = requests.post(SPEECH_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        
        # Save audio to a temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        
        return temp_file_path
    
    except requests.RequestException as e:
        logger.error(f"Error in text-to-speech request: {str(e)}")
        return None

def clear_conversation_history():
    """Clear the conversation history."""
    global conversation_history
    conversation_history = []
    logger.info("Conversation history cleared.")
