# promptql_mcp_server/config.py

import os
import json
import logging
from pathlib import Path
import dotenv
from typing import Optional

# Configure logging
logger = logging.getLogger("promptql_config")

# Load environment variables from .env file if it exists
dotenv.load_dotenv()

class ConfigManager:
    """Manages configuration for the PromptQL MCP server."""
    
    def __init__(self):
        """Initialize the configuration manager."""
        self.config_dir = Path(os.path.expanduser("~/.promptql-mcp"))
        self.config_file = self.config_dir / "config.json"
        self.config = self._load_config()
    
    def _load_config(self) -> dict:
        """Load configuration from file or environment variables."""
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to load from file
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    config_data = json.load(f)
                    logger.info(f"Loaded configuration from {self.config_file}")
                    return config_data
            except Exception as e:
                logger.error(f"Error loading config file: {e}")
                return {}
        
        # If no file, try environment variables
        config = {}
        env_mappings = {
            "PROMPTQL_API_KEY": "api_key",
            "PROMPTQL_PLAYGROUND_URL": "playground_url",
            "PROMPTQL_AUTH_TOKEN": "auth_token"
        }

        for env_key, config_key in env_mappings.items():
            if os.environ.get(env_key):
                config[config_key] = os.environ.get(env_key)
                logger.info(f"Using {env_key} from environment variables")
        
        # If we got config from env vars, save it to file for persistence
        if config:
            try:
                with open(self.config_file, "w") as f:
                    json.dump(config, f, indent=2)
                os.chmod(self.config_file, 0o600)  # Set file permissions
                logger.info(f"Saved environment config to {self.config_file}")
            except Exception as e:
                logger.error(f"Error saving config file: {e}")
        
        return config
    
    def save_config(self) -> None:
        """Save configuration to file."""
        try:
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=2)
            
            # Set permissions to be readable only by the user
            os.chmod(self.config_file, 0o600)
            logger.info(f"Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get a configuration value."""
        # First try environment variables
        env_key = f"PROMPTQL_{key.upper()}"
        if os.environ.get(env_key):
            return os.environ.get(env_key)
        
        # Then try config file
        return self.config.get(key.lower(), default)
    
    def set(self, key: str, value: str) -> None:
        """Set a configuration value."""
        if not value:
            logger.warning(f"Attempted to set empty value for {key}")
            return
            
        self.config[key.lower()] = value
        self.save_config()
        logger.info(f"Updated configuration for {key}")
    
    def is_configured(self) -> bool:
        """Check if the essential configuration is present."""
        return (bool(self.get("api_key")) and
                bool(self.get("playground_url")) and
                bool(self.get("auth_token")))