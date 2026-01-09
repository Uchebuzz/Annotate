"""
Configuration module for application settings.

This module handles:
- Application configuration (batch size, etc.)
- Loading and saving configuration
"""

import json
import os
from typing import Dict


CONFIG_FILE = "config.json"
DEFAULT_BATCH_SIZE = 50
DEFAULT_DATA_FILE = "complete_corrected_combined.jsonl"


def load_config() -> Dict:
    """Load configuration from file, returning defaults if file doesn't exist."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Ensure batch_size is present and valid
                if "batch_size" not in config or not isinstance(config["batch_size"], int) or config["batch_size"] < 1:
                    config["batch_size"] = DEFAULT_BATCH_SIZE
                # Ensure data_file is present
                if "data_file" not in config:
                    config["data_file"] = DEFAULT_DATA_FILE
                return config
        except (json.JSONDecodeError, IOError):
            return {"batch_size": DEFAULT_BATCH_SIZE, "data_file": DEFAULT_DATA_FILE}
    return {"batch_size": DEFAULT_BATCH_SIZE, "data_file": DEFAULT_DATA_FILE}


def save_config(config: Dict) -> None:
    """Save configuration to file."""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)


def get_batch_size() -> int:
    """Get the current batch size setting."""
    config = load_config()
    return config.get("batch_size", DEFAULT_BATCH_SIZE)


def set_batch_size(batch_size: int) -> bool:
    """
    Set the batch size.
    
    Args:
        batch_size: Number of records to assign per batch (must be >= 1)
        
    Returns:
        True if successful, False if invalid batch_size
    """
    if batch_size < 1:
        return False
    
    config = load_config()
    config["batch_size"] = batch_size
    save_config(config)
    return True


def get_data_file() -> str:
    """Get the current data file path setting."""
    config = load_config()
    return config.get("data_file", DEFAULT_DATA_FILE)


def set_data_file(data_file: str) -> bool:
    """
    Set the data file path.
    
    Args:
        data_file: Path to the JSONL data file
        
    Returns:
        True if successful
    """
    config = load_config()
    config["data_file"] = data_file
    save_config(config)
    return True

