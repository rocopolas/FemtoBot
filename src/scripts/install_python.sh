#!/bin/bash

# Auto-install Python 3.12
# Supports: Debian/Ubuntu, Fedora/CentOS/RHEL, Arch Linux

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🔍 Searching for package manager${NC}"

if command -v apt-get &> /dev/null; then
    echo "• Found apt-get (Debian/Ubuntu/Kali)"
    echo "Adding deadsnakes ppa just in case (Ubuntu)..."
    if command -v add-apt-repository &> /dev/null; then
         sudo add-apt-repository -y ppa:deadsnakes/ppa 2>/dev/null || true
    fi
    sudo apt-get update
    sudo apt-get install -y python3.12 python3.12-venv python3.12-dev

elif command -v dnf &> /dev/null; then
    echo "• Found dnf (Fedora/RHEL)"
    sudo dnf install -y python3.12

elif command -v pacman &> /dev/null; then
    echo "• Found pacman (Arch Linux)"
    sudo pacman -S --noconfirm python312
    # Arch usually has 'python' as latest, check if 'python3.12' specific package exists or if 'python' is 3.12+
    # But usually extra/python is whatever is current.
    # explicit python3.12 might be in AUR or specific handling.
    # Falling back to just trying to ensure python is up to date?
    # Arch is usually rolling, so 'python' should be > 3.12. 
    sudo pacman -S --noconfirm python

elif command -v zypper &> /dev/null; then
    echo "• Found zypper (OpenSUSE)"
    sudo zypper install -y python312

else
    echo -e "${RED}❌ No supported package manager found (apt, dnf, pacman, zypper).${NC}"
    echo "Please install Python 3.12 manually."
    exit 1
fi

if command -v python3.12 &> /dev/null; then
    echo -e "${GREEN}✅ Python 3.12 installed successfully!${NC}"
    
    echo -e "${GREEN}📦 Creating virtual environment 'venv_bot'...${NC}"
    python3.12 -m venv venv_bot
    
    if [ -f "venv_bot/bin/pip" ]; then
        echo -e "${GREEN}⬇ Installing femtobot in new environment...${NC}"
        ./venv_bot/bin/pip install --upgrade pip --quiet
        ./venv_bot/bin/pip install femtobot --quiet
        
        echo -e "${GREEN}✅ All set!${NC}"
    else
        echo -e "${RED}⚠ Failed to create virtual environment.${NC}"
        exit 1
    fi

    exit 0
else
    echo -e "${RED}❌ Installation appeared to finish but 'python3.12' command is not found.${NC}"
    exit 1
fi
