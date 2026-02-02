import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.tui import LocalBotApp

def main():
    app = LocalBotApp()
    app.run()

if __name__ == "__main__":
    main()
