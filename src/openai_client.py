#!/usr/bin/env python3
import json
import tempfile
import requests

from src.config import logger, API_KEY, CHAT_ENDPOINT, SPEECH_ENDPOINT, DEFAULT_MODEL, TTS_MODEL, TTS_VOICE
# We're now importing the functions dynamically, so they can include MCP functions
import src.functions as functions_module

# Custom JSON encoder to handle non-serializable objects like those from MCP SDK
class MCPObjectEncoder(json.JSONEncoder):
    def default(self, obj):
        # Try the base class method first to handle basic types
        try:
            return super().default(obj)
        except TypeError:
            # Handle different types of objects
            logger.info(f"Custom serialization for object of type {type(obj).__name__}")
            
            # For objects with __dict__
            if hasattr(obj, '__dict__'):
                # Get the __dict__ and recursively encode any non-serializable objects within it
                obj_dict = {}
                for k, v in obj.__dict__.items():
                    try:
                        # Attempt to use standard JSON encoding first
                        json.dumps(v)
                        obj_dict[k] = v
                    except (TypeError, OverflowError):
                        # If that fails, use our custom handling
                        if hasattr(v, '__dict__'):
                            obj_dict[k] = self.default(v)  # Recursive serialization
                        elif hasattr(v, 'to_dict'):
                            obj_dict[k] = v.to_dict()
                        elif hasattr(v, 'as_dict'):
                            obj_dict[k] = v.as_dict()
                        else:
                            # Fallback to string representation
                            obj_dict[k] = str(v)
                return obj_dict
            
            # For objects with to_dict or as_dict methods
            elif hasattr(obj, 'to_dict'):
                return obj.to_dict()
            elif hasattr(obj, 'as_dict'):
                return obj.as_dict()
            # For any other object, convert to string
            return str(obj)

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
    
    # Get the latest function definitions (including MCP functions)
    current_function_definitions = functions_module.update_function_definitions()
    
    # Use default model from src.config (o3-mini by default)
    payload = {
        "model": DEFAULT_MODEL,
        "messages": conversation_history,
        "tools": current_function_definitions,
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
                    
                    # Get the latest available functions (including MCP functions)
                    available_functions = functions_module.get_available_functions()
                    
                    # Execute function if it exists
                    if function_name in available_functions:
                        function_response = available_functions[function_name](**function_args)
                        
                        # Add function response to history using our custom encoder
                        try:
                            # Use custom encoder to handle complex objects
                            function_response_json = json.dumps(function_response, cls=MCPObjectEncoder)
                        except Exception as e:
                            # Last resort fallback if custom encoder fails
                            logger.warning(f"Custom encoder failed: {str(e)}. Using string representation as fallback.")
                            function_response_json = json.dumps(f"Function returned: {str(function_response)}")
                            
                        conversation_history.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": function_name,
                            "content": function_response_json
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
    
    # Get the latest function definitions (including MCP functions)
    current_function_definitions = functions_module.update_function_definitions()
    
    # Important: Use the same model as in chat_with_gpt and include tools parameter
    payload = {
        "model": DEFAULT_MODEL,  # Match the model used in the initial request
        "messages": conversation_history,
        "tools": current_function_definitions,  # Include function definitions (including MCP)
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
        
        # Check if the content exists and is not None
        if "content" in assistant_message and assistant_message["content"] is not None:
            return assistant_message["content"]
        else:
            # If content is None or doesn't exist, provide a default response
            logger.warning("Assistant message content is None or missing")
            return "I've processed your request. There seems to be an issue with the file path. Please make sure to use the correct path format for your desktop directory."
    
    except requests.RequestException as e:
        logger.error(f"Error in final response request: {str(e)}")
        return f"Sorry, there was an error getting the final response: {str(e)}"
    
    except Exception as e:
        # Catch any other exceptions that might occur
        logger.error(f"Unexpected error in get_final_response: {str(e)}")
        return f"Sorry, an unexpected error occurred: {str(e)}"

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
