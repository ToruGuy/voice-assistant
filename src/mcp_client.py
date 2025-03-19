#!/usr/bin/env python3
import os
import json
import asyncio
import subprocess
import threading
import tempfile
from contextlib import AsyncExitStack
from typing import Dict, List, Optional, Any, Callable, Union, Tuple

# Import the official MCP SDK
import mcp
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.config import logger
from src.mcp_config import MCPConfig

class MCPWrapper:
    """Simple wrapper for MCP functions."""
    
    def __init__(self):
        """Initialize the MCP wrapper."""
        self.config = MCPConfig()
        self.loop = asyncio.new_event_loop()
        self.sessions = {}
        
    # Server management methods
    def get_servers(self):
        """Get all configured servers."""
        return self.config.servers
    
    def get_enabled_servers(self):
        """Get all enabled servers."""
        return self.config.get_enabled_servers()
    
    def add_server(self, server_id, name, url, enabled=True):
        """Add a new MCP server to the configuration."""
        return self.config.add_server(server_id, name, url, enabled)
    
    def enable_server(self, server_id):
        """Enable an MCP server."""
        result = self.config.enable_server(server_id)
        if result:
            # Clear session for this server to force reconnection
            if server_id in self.sessions:
                del self.sessions[server_id]
        return result
    
    def disable_server(self, server_id):
        """Disable an MCP server."""
        result = self.config.disable_server(server_id)
        if result and server_id in self.sessions:
            # Close and remove session for this server
            try:
                session_data = self.sessions[server_id]
                if isinstance(session_data, tuple):
                    session, process = session_data
                    # Attempt to cleanly stop the process
                    if process and process.poll() is None:
                        process.terminate()
                else:
                    session = session_data
                # Close session
                future = asyncio.run_coroutine_threadsafe(
                    session.close(), 
                    self.loop
                )
                future.result(timeout=5)
            except Exception as e:
                logger.error(f"Error closing session for server {server_id}: {str(e)}")
            finally:
                del self.sessions[server_id]
        return result
    
    def remove_server(self, server_id):
        """Remove an MCP server from the configuration."""
        # First disable it to clean up any active sessions
        if server_id in self.sessions:
            self.disable_server(server_id)
        return self.config.remove_server(server_id)
    
    def _get_server_sessions(self):
        """Get or establish sessions for all enabled servers."""
        # Check for any new servers that need sessions
        for server_id, server in self.config.servers.items():
            if not server.get('enabled', False) or server_id in self.sessions:
                continue
                
            # Handle different server configurations
            if 'url' in server:
                # For URL-based servers
                try:
                    # HTTP transports are not supported in the current SDK version
                    # Will implement when available
                    logger.error(f"URL-based servers not currently supported: {server['url']}")
                except Exception as e:
                    logger.error(f"Error connecting to URL server {server_id}: {str(e)}")
            
            elif 'command' in server and 'args' in server:
                # For command-based servers
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self._connect_to_command_server(server_id, server), 
                        self.loop
                    )
                    session = future.result(timeout=10)
                    if session:
                        self.sessions[server_id] = session
                        logger.info(f"Connected to command-based MCP server: {server_id}")
                except Exception as e:
                    logger.error(f"Error starting command server {server_id}: {str(e)}")
        
        return self.sessions
    
    async def _connect_to_command_server(self, server_id: str, server_config: Dict[str, Any]):
        """Connect to a command-based MCP server."""
        try:
            # Ensure we have the command and args
            command = server_config.get('command')
            args = server_config.get('args', [])
            
            if not command:
                logger.error(f"Missing command for server {server_id}")
                return None
            
            # Create server parameters
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=None  # Use current environment
            )
            
            # Connect to the server
            exit_stack = AsyncExitStack()
            
            # Create a stdio connection
            stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
            read, write = stdio_transport
            
            # Create and initialize the session
            session = await exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            # Log success
            logger.info(f"Successfully initialized session for server {server_id}")
            
            # Store the exit stack for cleanup
            return {
                'session': session,
                'exit_stack': exit_stack
            }
            
        except Exception as e:
            logger.error(f"Error connecting to command server {server_id}: {str(e)}")
            return None
            
    def get_capabilities(self):
        """Get capabilities from all enabled MCP servers."""
        all_capabilities = {}
        sessions = self._get_server_sessions()
        
        for server_id, session_data in sessions.items():
            try:
                # Get the session object
                session = session_data.get('session') if isinstance(session_data, dict) else session_data
                
                if not session:
                    continue
                    
                # Get tools instead of capabilities directly
                future = asyncio.run_coroutine_threadsafe(
                    session.list_tools(), 
                    self.loop
                )
                tools_result = future.result(timeout=5)
                
                # Convert ListToolsResult to a simple list of tool names
                # In MCP SDK 1.4.1, list_tools() returns an object with a 'tools' attribute
                # that contains the list of tool names
                try:
                    # First try to access tools as an attribute
                    if hasattr(tools_result, 'tools'):
                        tool_names = tools_result.tools
                    # Then try to access as a dictionary
                    elif isinstance(tools_result, dict) and 'tools' in tools_result:
                        tool_names = tools_result['tools']
                    # If it's already a list, use it directly
                    elif isinstance(tools_result, list):
                        tool_names = tools_result
                    else:
                        # If all else fails, try to convert to string and log
                        logger.warning(f"Unknown tools result format: {type(tools_result).__name__}")
                        tool_names = []
                        
                    # Format tools as capabilities
                    capabilities = {
                        'tools': tool_names
                    }
                    all_capabilities[server_id] = capabilities
                except Exception as e:
                    logger.error(f"Error processing tools for server {server_id}: {str(e)}")
            except Exception as e:
                logger.error(f"Error getting capabilities from server {server_id}: {str(e)}")
        
        return all_capabilities
    
    def get_all_tools(self):
        """Get all available tools from all servers."""
        tool_map = {}
        capabilities = self.get_capabilities()
        
        for server_id, caps in capabilities.items():
            if not caps or 'tools' not in caps:
                continue
            
            # Get the tools list
            tools = caps['tools']
            
            # Debug log without JSON serialization
            logger.info(f"Tools for server {server_id}: {len(tools)} tools found")
            for t in tools:
                logger.info(f"  - {t}")
            
            # Process each tool based on actual response format
            for tool in tools:
                # The MCP SDK returns Tool objects or other formats
                # Try to extract the necessary information
                if isinstance(tool, dict):
                    # Dictionary format
                    tool_name = tool.get('name')
                    if not tool_name:
                        continue
                    description = tool.get('description', f"MCP tool: {tool_name}")
                    parameters = tool.get('inputSchema', tool.get('parameters', {'type': 'object', 'properties': {}}))
                elif isinstance(tool, str):
                    # String format (just the tool name)
                    tool_name = tool
                    description = f"MCP tool: {tool_name}"
                    parameters = {'type': 'object', 'properties': {}}
                else:
                    # Try to handle Tool object
                    try:
                        # First, try to access attributes directly
                        if hasattr(tool, 'name'):
                            tool_name = tool.name
                            description = getattr(tool, 'description', f"MCP tool: {tool_name}")
                            # Try to get input schema with different possible attributes
                            parameters = getattr(tool, 'inputSchema', None)
                            if parameters is None:
                                parameters = getattr(tool, 'parameters', {'type': 'object', 'properties': {}})
                            # Create a tool dictionary
                            tool = {
                                'name': tool_name,
                                'description': description,
                                'parameters': parameters
                            }
                        else:
                            # If there's no 'name' attribute, we can't use this tool
                            logger.warning(f"Tool missing name attribute: {type(tool).__name__}")
                            continue
                    except Exception as e:
                        logger.warning(f"Failed to process tool of type {type(tool).__name__}: {str(e)}")
                        continue
                
                if tool_name in tool_map:
                    continue
                    
                # Store the tool definition along with its server
                tool_map[tool_name] = (server_id, tool)
        
        # Log the final map of tools
        logger.info(f"Found {len(tool_map)} tools from MCP servers")
        return tool_map
    
    def _normalize_path(self, path):
        """Normalize path for MCP filesystem operations.
        
        Handles special directories like ~/Desktop and ensures proper paths for allowed directories.
        """
        if not path or not isinstance(path, str):
            return path
            
        # Handle desktop paths in various formats
        if path.lower().startswith('desktop/') or path.lower() == 'desktop':
            # Convert to the proper format expected by the filesystem server
            path_suffix = path[len('desktop/'):] if path.lower().startswith('desktop/') else ''
            return f"/users/tako/desktop/{path_suffix}"
        elif path.startswith('~/desktop/') or path.lower() == '~/desktop':
            path_suffix = path[len('~/desktop/'):] if path.startswith('~/desktop/') else ''
            return f"/users/tako/desktop/{path_suffix}"
            
        # If path doesn't start with / and looks like a relative path, prepend desktop path
        if not path.startswith('/') and not path.startswith('C:'):
            return f"/users/tako/desktop/{path}"
            
        return path
            
    def call_tool(self, tool_name, **params):
        """Call a tool by name with the given parameters."""
        # Get all tools and find the one we want
        tools = self.get_all_tools()
        if tool_name not in tools:
            logger.error(f"Tool not found: {tool_name}")
            return None
            
        server_id, _ = tools[tool_name]
        session_data = self.sessions.get(server_id)
        
        if not session_data:
            logger.error(f"No session for server {server_id}")
            return None
        
        # Normalize paths for filesystem operations
        if tool_name in ['read_file', 'write_file', 'create_directory', 'list_directory',
                         'move_file', 'copy_file', 'delete_file', 'search_files', 'get_file_info']:
            logger.info(f"Normalizing paths for filesystem operation: {tool_name}")
            
            # Handle path parameters in different formats
            if 'path' in params:
                original_path = params['path']
                params['path'] = self._normalize_path(params['path'])
                logger.info(f"Normalized path: {original_path} -> {params['path']}")
                
            if 'source' in params:
                params['source'] = self._normalize_path(params['source'])
                
            if 'destination' in params:
                params['destination'] = self._normalize_path(params['destination'])
                
            if 'directory' in params:
                params['directory'] = self._normalize_path(params['directory'])
                
            if 'filepath' in params:
                params['filepath'] = self._normalize_path(params['filepath'])
                
            # Handle list of paths if present
            if 'paths' in params and isinstance(params['paths'], list):
                params['paths'] = [self._normalize_path(p) for p in params['paths']]
            
        try:
            # Get the session object from the session data
            session = session_data.get('session') if isinstance(session_data, dict) else session_data
            
            if not session:
                logger.error(f"Invalid session for server {server_id}")
                return None
                
            # Log the parameters being sent to the tool
            logger.info(f"Calling tool {tool_name} with params: {params}")
                
            # Call the tool using the call_tool method
            future = asyncio.run_coroutine_threadsafe(
                session.call_tool(tool_name, params), 
                self.loop
            )
            result = future.result(timeout=30)  # Allow up to 30 seconds for tool execution
            return result
        except Exception as e:
            logger.error(f"Error calling tool {tool_name}: {str(e)}")
            return None
    
    def get_tool_definitions_for_openai(self):
        """Get tool definitions in OpenAI function format."""
        tools = []
        tool_map = self.get_all_tools()
        
        for tool_name, (server_id, tool) in tool_map.items():
            # Ensure we have all required fields
            if not isinstance(tool, dict):
                logger.warning(f"Tool {tool_name} has invalid format: {type(tool)}")
                continue
                
            # Get or create description and parameters
            description = tool.get('description', f"MCP tool: {tool_name}")
            parameters = tool.get('parameters', {'type': 'object', 'properties': {}})
            
            # Convert MCP tool definition to OpenAI function definition
            tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": description,
                    "parameters": parameters
                }
            })
        
        return tools
    
    def get_function_map(self):
        """Get a mapping of function names to callable wrappers."""
        functions = {}
        tool_map = self.get_all_tools()
        
        for tool_name in tool_map.keys():
            # Create a wrapper that calls the tool
            def make_wrapper(tool_name):
                def wrapper(**params):
                    return self.call_tool(tool_name, **params)
                return wrapper
            
            functions[tool_name] = make_wrapper(tool_name)
        
        return functions

# Initialize the MCP wrapper loop
def _initialize_mcp_wrapper_loop():
    """Initialize the MCP wrapper event loop in a background thread."""
    wrapper = MCPWrapper()
    
    # Start the event loop in a background thread
    def run_event_loop():
        asyncio.set_event_loop(wrapper.loop)
        wrapper.loop.run_forever()
    
    loop_thread = threading.Thread(target=run_event_loop, daemon=True)
    loop_thread.start()
    
    # Give the thread a moment to start
    import time
    time.sleep(0.1)
    
    return wrapper

# Create a singleton instance
_mcp_wrapper = _initialize_mcp_wrapper_loop()
