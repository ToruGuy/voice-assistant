#!/usr/bin/env python3
from datetime import datetime
from src.config import logger

# Function definitions
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return {"result": a + b}

def get_current_time():
    """Get the current time."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"time": current_time}

# Available functions mapping
AVAILABLE_FUNCTIONS = {
    "calculate_sum": calculate_sum,
    "get_current_time": get_current_time
}

# Function definitions for the model
FUNCTION_DEFINITIONS = [
    {
        "type": "function",
        "function": {
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
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Get the current time",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]
