"""Configuration loader for LocalBot."""
import yaml
import os

_config = None

def load_config():
    """Loads configuration from config.yaml."""
    global _config
    # config.yaml is in the project root (parent of utils/)
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    
    with open(config_path, "r", encoding="utf-8") as f:
        _config = yaml.safe_load(f)
    
    return _config

def get_config(key: str, default=None):
    """Gets a config value by key."""
    global _config
    if _config is None:
        load_config()
    return _config.get(key, default)
