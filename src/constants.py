"""Global constants for FemtoBot."""
import os



# Determine the absolute project root based on this file's location
_ABS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = _ABS_ROOT

# Detect if running in "Dev Mode" (inside a git repo or local clone)
_GIT_DIR = os.path.join(PROJECT_ROOT, ".git")
IS_DEV_MODE = os.path.exists(_GIT_DIR)

# User-specific directory for pip installs
USER_FEMTOBOT_DIR = os.path.expanduser("~/.femtobot")

if IS_DEV_MODE:
    # In dev mode, keep everything local to the repo
    CONFIG_DIR = PROJECT_ROOT
    DATA_DIR = os.path.join(PROJECT_ROOT, "data")
else:
    # In user mode (pip install), use the home directory
    CONFIG_DIR = USER_FEMTOBOT_DIR
    DATA_DIR = os.path.join(USER_FEMTOBOT_DIR, "data")

# These remain in the package structure
if IS_DEV_MODE:
    ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
else:
    # In user mode, assets are installed as a package
    # We can use importlib.resources or just assume they are relative to site-packages
    # For simplicity, if we made 'assets' a package, it should be importable.
    # But let's fallback to site-packages logic if needed.
    # However, ASSETS_DIR is used for direct file access.
    try:
        import importlib.resources
        # Python 3.9+
        with importlib.resources.path("assets", "styles.tcss") as p:
             ASSETS_DIR = os.path.dirname(p)
    except (ImportError, TypeError, FileNotFoundError):
        # Fallback
        ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
UTILS_DIR = os.path.join(PROJECT_ROOT, "utils")
