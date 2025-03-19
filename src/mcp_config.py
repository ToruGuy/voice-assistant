#!/usr/bin/env python3
import os
import json
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "mcp_servers.json")

class MCPConfig:
    """Configuration manager for MCP servers."""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize MCP configuration.
        
        Args:
            config_path: Path to the MCP servers configuration file. If None, uses default path.
        """
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self.servers = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load MCP server configurations from file."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    self.servers = json.load(f)
                logger.info(f"Loaded MCP server configuration from {self.config_path}")
            else:
                logger.warning(f"MCP configuration file not found at {self.config_path}")
                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                # Create default config
                self.servers = {
                    "default": {
                        "name": "Default MCP Server",
                        "url": "http://localhost:8000",
                        "enabled": False
                    }
                }
                self._save_config()
        except Exception as e:
            logger.error(f"Error loading MCP configuration: {str(e)}")
            self.servers = {}
    
    def _save_config(self) -> None:
        """Save current MCP server configurations to file."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.servers, f, indent=4)
            logger.info(f"Saved MCP server configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving MCP configuration: {str(e)}")
    
    def get_server(self, server_id: str) -> Dict:
        """
        Get configuration for a specific MCP server.
        
        Args:
            server_id: The identifier of the server to retrieve
            
        Returns:
            Dictionary containing server configuration
        """
        return self.servers.get(server_id, {})
    
    def get_enabled_servers(self) -> List[Dict]:
        """
        Get all enabled MCP servers.
        
        Returns:
            List of enabled server configurations
        """
        return [server for server_id, server in self.servers.items() 
                if server.get('enabled', False)]
    
    def add_server(self, server_id: str, name: str, url: str, enabled: bool = True) -> None:
        """
        Add a new MCP server configuration.
        
        Args:
            server_id: Unique identifier for the server
            name: Display name for the server
            url: Server URL
            enabled: Whether the server is enabled
        """
        self.servers[server_id] = {
            "name": name,
            "url": url,
            "enabled": enabled
        }
        self._save_config()
    
    def update_server(self, server_id: str, **kwargs) -> bool:
        """
        Update an existing MCP server configuration.
        
        Args:
            server_id: The identifier of the server to update
            **kwargs: Configuration properties to update
            
        Returns:
            True if server was updated, False if server was not found
        """
        if server_id in self.servers:
            self.servers[server_id].update(kwargs)
            self._save_config()
            return True
        return False
    
    def remove_server(self, server_id: str) -> bool:
        """
        Remove an MCP server configuration.
        
        Args:
            server_id: The identifier of the server to remove
            
        Returns:
            True if server was removed, False if server was not found
        """
        if server_id in self.servers:
            del self.servers[server_id]
            self._save_config()
            return True
        return False
    
    def enable_server(self, server_id: str) -> bool:
        """Enable an MCP server."""
        return self.update_server(server_id, enabled=True)
    
    def disable_server(self, server_id: str) -> bool:
        """Disable an MCP server."""
        return self.update_server(server_id, enabled=False)
