"""
Configuration management for Music Trainer application
"""

import json
import os
import configparser
from pathlib import Path
from typing import Dict, Any, Optional
from utils.logger import get_logger


class Config:
    """
    Application configuration manager
    
    Handles loading, saving, and accessing configuration values
    with sensible defaults for the Music Trainer application.
    Supports both JSON config files and INI files with API keys.
    """
    
    DEFAULT_CONFIG = {
        "audio": {
            "sample_rate": 44100,
            "buffer_size": 512,
            "channels": 2,
            "latency": "low"
        },
        "midi": {
            "auto_connect": True,
            "device_name": None,
            "input_channel": None  # None means all channels
        },
        "practice": {
            "default_tempo": 120,
            "metronome_enabled": True,
            "difficulty_level": 2,
            "style": "modal_jazz"
        },
        "evaluation": {
            "pitch_tolerance_cents": 25,
            "timing_tolerance_ms": 100,
            "performance_window_size": 5
        },
        "gui": {
            "theme": "default",
            "window_width": 1000,
            "window_height": 700,
            "auto_save_session": True
        },
        "anthropic": {
            "api_key": None,
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 1000,
            "temperature": 0.3
        },
        "paths": {
            "phrase_library": "data/phrases",
            "user_data": "data/user_progress.db",
            "recordings": "data/recordings"
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_file (str, optional): Path to config file. 
                                       Defaults to 'config.json'
        """
        self.logger = get_logger()
        self.config_file = Path(config_file or "config.json")
        self.ini_config_file = Path("config.ini")  # INI file for API keys
        self._config = self.DEFAULT_CONFIG.copy()
        
        # Load existing config if it exists
        self.load()
        
        # Load API keys and sensitive config from INI file
        self.load_ini_config()
    
    def load(self) -> None:
        """Load configuration from JSON file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    self._merge_config(user_config)
                    self.logger.info(f"Loaded configuration from {self.config_file}")
            else:
                self.logger.info("No config file found, using defaults")
                self.save()  # Create default config file
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            self.logger.info("Using default configuration")
    
    def load_ini_config(self) -> None:
        """Load configuration from INI file (for API keys and sensitive data)"""
        try:
            if self.ini_config_file.exists():
                config_parser = configparser.ConfigParser()
                config_parser.read(self.ini_config_file)
                
                # Load Anthropic API key
                if 'anthropic' in config_parser and 'api_key' in config_parser['anthropic']:
                    api_key = config_parser['anthropic']['api_key'].strip()
                    if api_key:
                        self._config['anthropic']['api_key'] = api_key
                        self.logger.info("Loaded Anthropic API key from config.ini")
                
                # Load other settings if present
                for section_name in config_parser.sections():
                    if section_name in self._config:
                        for key, value in config_parser[section_name].items():
                            if key in self._config[section_name]:
                                # Try to convert to appropriate type
                                try:
                                    if isinstance(self._config[section_name][key], int):
                                        self._config[section_name][key] = int(value)
                                    elif isinstance(self._config[section_name][key], float):
                                        self._config[section_name][key] = float(value)
                                    elif isinstance(self._config[section_name][key], bool):
                                        self._config[section_name][key] = value.lower() in ('true', '1', 'yes')
                                    else:
                                        self._config[section_name][key] = value
                                except ValueError:
                                    self._config[section_name][key] = value
                
                self.logger.info(f"Loaded INI configuration from {self.ini_config_file}")
            else:
                self.logger.info("No config.ini file found - API key will need to be set via environment variable")
                
        except Exception as e:
            self.logger.error(f"Error loading INI config: {e}")
    
    def get_anthropic_api_key(self) -> Optional[str]:
        """Get Anthropic API key from config or environment variable"""
        # Try config file first
        api_key = self._config.get('anthropic', {}).get('api_key')
        if api_key:
            return api_key
        
        # Fall back to environment variable
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            self.logger.info("Using Anthropic API key from environment variable")
            return api_key
        
        self.logger.warning("No Anthropic API key found in config.ini or environment variable")
        return None
    
    def save(self) -> None:
        """Save current configuration to file"""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            self.logger.info(f"Saved configuration to {self.config_file}")
        except Exception as e:
            self.logger.error(f"Error saving config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation
        
        Args:
            key (str): Configuration key (e.g., 'audio.sample_rate')
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value using dot notation
        
        Args:
            key (str): Configuration key (e.g., 'audio.sample_rate')
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        # Navigate to parent of target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        self.logger.debug(f"Set config {key} = {value}")
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section (str): Section name (e.g., 'audio')
        
        Returns:
            Dictionary containing section configuration
        """
        return self._config.get(section, {}).copy()
    
    def get_summary(self) -> str:
        """Get a summary of current configuration for logging"""
        return (
            f"Audio: {self.get('audio.sample_rate')}Hz, "
            f"MIDI: auto_connect={self.get('midi.auto_connect')}, "
            f"Practice: {self.get('practice.style')} "
            f"(level {self.get('practice.difficulty_level')})"
        )
    
    def _merge_config(self, user_config: Dict[str, Any]) -> None:
        """
        Merge user configuration with defaults
        
        Args:
            user_config (dict): User configuration to merge
        """
        def merge_dict(default: Dict, user: Dict) -> Dict:
            result = default.copy()
            for key, value in user.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = merge_dict(result[key], value)
                else:
                    result[key] = value
            return result
        
        self._config = merge_dict(self._config, user_config)
