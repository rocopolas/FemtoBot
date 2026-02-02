#!/bin/bash
set -e

# Ensure we are in the script's directory
cd "$(dirname "$0")"

# Check if venv exists
if [ ! -d "venv_bot" ]; then
    echo "Ejecuta ./cargarentorno.sh primero"
    exit 1
fi

# Run the Telegram bot
source venv_bot/bin/activate
python src/telegram_bot.py
