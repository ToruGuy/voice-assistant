#!/usr/bin/env python3
from datetime import datetime
from typing import Dict, Any, List

from src.config import logger
# Import the singleton MCP wrapper
from src.mcp_client import _mcp_wrapper

# Local function definitions
def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return {"result": a + b}

def get_current_time():
    """Get the current time."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"time": current_time}

# Base available functions mapping (local only)
BASE_FUNCTIONS = {
    "calculate_sum": calculate_sum,
    "get_current_time": get_current_time
}

# Function definitions for the model (local only)
BASE_FUNCTION_DEFINITIONS = [
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

def get_available_functions() -> Dict[str, Any]:
    """Get all available functions (local + MCP)."""
    try:
        # Get MCP functions
        mcp_functions = _mcp_wrapper.get_function_map()
        
        # Combine with local functions (local functions take priority)
        all_functions = {**mcp_functions, **BASE_FUNCTIONS}
        
        # Log the total number of functions
        total_count = len(all_functions)
        mcp_count = len(mcp_functions)
        if mcp_count > 0:
            logger.info(f"Loaded {total_count} functions ({mcp_count} from MCP servers)")
        
        return all_functions
    except Exception as e:
        logger.error(f"Error getting MCP functions: {str(e)}")
        return BASE_FUNCTIONS

def update_function_definitions() -> List[Dict]:
    """Get function definitions for all available functions (local + MCP)."""
    try:
        # Start with base definitions
        definitions = BASE_FUNCTION_DEFINITIONS.copy()
        
        # Add MCP definitions
        mcp_definitions = _mcp_wrapper.get_tool_definitions_for_openai()
        definitions.extend(mcp_definitions)
        
        return definitions
    except Exception as e:
        logger.error(f"Error getting MCP function definitions: {str(e)}")
        return BASE_FUNCTION_DEFINITIONS

# These exports will be used by other modules
AVAILABLE_FUNCTIONS = get_available_functions()
FUNCTION_DEFINITIONS = update_function_definitions()
