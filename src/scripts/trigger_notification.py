"""
Script triggered by cron to handle notifications.
Sends a desktop notification and appends to the events file.
Designed to be called as a module: python -m src.scripts.trigger_notification "Message"
"""
import sys
import os
import argparse
import logging
from datetime import datetime

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("femtobot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TriggerNotification")

def main():
    parser = argparse.ArgumentParser(description="Trigger a notification.")
    parser.add_argument("message", help="The notification message")
    parser.add_argument("--events-file", help="Path to events file", default="data/events.txt")
    
    args = parser.parse_args()
    message = args.message
    events_file = args.events_file
    
    # 1. Desktop Notification (if notify-send is available)
    try:
        from shutil import which
        if which('notify-send'):
            import subprocess
            subprocess.run(['notify-send', 'FemtoBot Reminder', message], check=False)
    except Exception as e:
        logger.error(f"Failed to send desktop notification: {e}")

    # 2. Append to events file (which the bot watches to send Telegram msgs)
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(events_file), exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} | {message}\n")
            
        logger.info(f"Notification triggered: {message}")
    except Exception as e:
        logger.error(f"Failed to write to events file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
