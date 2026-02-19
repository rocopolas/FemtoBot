#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${CYAN}=== FemtoBot Installer ===${NC}"
echo "This script will set up FemtoBot on your system."

# Helper Functions
check_cmd() {
    command -v "$1" >/dev/null 2>&1
}

install_pkg() {
    PACKAGE=$1
    if [ -x "$(command -v apt-get)" ]; then
        if sudo -n true 2>/dev/null; then
            echo -e "${YELLOW}Installing $PACKAGE...${NC}"
            sudo apt-get update && sudo apt-get install -y "$PACKAGE"
        else
            echo -e "${YELLOW}Administrator privileges required to install $PACKAGE.${NC}"
            # Check if interactive
            if [ -t 0 ]; then
                read -p "Do you want to run sudo to install $PACKAGE? (y/N) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    sudo apt-get update && sudo apt-get install -y "$PACKAGE"
                else
                    echo -e "${RED}Skipping $PACKAGE installation. Please install it manually.${NC}"
                    return 1
                fi
            else
                 echo -e "${RED}Cannot install $PACKAGE automatically (no sudo access). Please install it manually.${NC}"
                 return 1
            fi
        fi
    elif [ -x "$(command -v pacman)" ]; then
        if sudo -n true 2>/dev/null; then
            echo -e "${YELLOW}Installing $PACKAGE...${NC}"
            sudo pacman -S --noconfirm "$PACKAGE"
        else
             # Check if interactive
            if [ -t 0 ]; then
                read -p "Do you want to run sudo to install $PACKAGE? (y/N) " -n 1 -r
                echo
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    sudo pacman -S --noconfirm "$PACKAGE"
                else
                    echo -e "${RED}Skipping $PACKAGE installation. Please install it manually.${NC}"
                    return 1
                fi
            else
                 echo -e "${RED}Cannot install $PACKAGE automatically (no sudo access).${NC}"
                 return 1
            fi
        fi
        echo -e "${YELLOW}Installing $PACKAGE...${NC}"
        brew install "$PACKAGE"
    else
        echo -e "${RED}Could not install $PACKAGE automatically. Please install it manually.${NC}"
        return 1
    fi
}

PYTHON_EXEC=""
check_python_version() {
    # 1. Try python3.12 explicitly (Preferred)
    if command -v python3.12 >/dev/null 2>&1; then
        PYTHON_EXEC="python3.12"
        return 0
    fi
    # 2. Try python3.13 explicitly
    if command -v python3.13 >/dev/null 2>&1; then
         PYTHON_EXEC="python3.13"
         return 0
    fi

    # 3. Try python3, but check if it is compatible (>= 3.12 AND < 3.14)
    # Python 3.14 breaks pydantic v1 used by chromadb
    if command -v python3 >/dev/null 2>&1; then
        if python3 -c "import sys; exit(0 if (3, 12) <= sys.version_info < (3, 14) else 1)" 2>/dev/null; then
            PYTHON_EXEC="python3"
            return 0
        fi
    fi
    return 1
}

# 0. Check Environment & Clone if needed
echo -e "\n${CYAN}[0/6] Checking environment...${NC}"

# Check if we are in the project directory (look for specific files)
if [ ! -f "pyproject.toml" ] || [ ! -f "requirements.txt" ]; then
    echo -e "${YELLOW}Project files not found in current directory.${NC}"
    echo "Assuming we need to clone the repository..."
    
    # Check for Git
    if ! check_cmd git; then
        echo -e "${YELLOW}Git not found. Installing Git...${NC}"
        install_pkg git
        if ! check_cmd git; then
            echo -e "${RED}Failed to install Git. Please install it manually.${NC}"
            exit 1
        fi
    fi

    REPO_URL="https://github.com/rocopolas/FemtoBot.git"
    echo -e "${CYAN}Cloning $REPO_URL...${NC}"
    
    if git clone "$REPO_URL"; then
        cd FemtoBot || exit 1
        echo -e "${GREEN}✓ Repository cloned and entered.${NC}"
    else
        echo -e "${RED}Failed to clone repository.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Project files found. Running in-place.${NC}"
fi

# 1. Check & Install System Dependencies
echo -e "\n${CYAN}[1/6] Checking system dependencies...${NC}"

# Python 3.12+
if check_python_version; then
    echo -e "${GREEN}✓ Python $($PYTHON_EXEC --version) found${NC}"
else
    echo -e "${YELLOW}Compatible Python (3.12 - 3.13) not found.${NC}"
    echo -e "${YELLOW}Python 3.14+ is currently not supported due to dependency issues.${NC}"
    echo "Attempting to install Python 3.12..."
    
    # Check if we can install it via deadsnakes (Ubuntu) or similar
    if [ -x "$(command -v apt-get)" ]; then
        echo "Adding deadsnakes PPA and installing Python 3.12..."
        # We can't easily auto-add PPA without potential interactions/sudo issues, 
        # but let's try the simple install first.
        install_pkg python3.12
    elif [ -x "$(command -v pacman)" ]; then
        # Arch Linux
        echo "Trying to install python3.12 on Arch..."
        
        if command -v yay >/dev/null 2>&1; then
             echo -e "${YELLOW}Using yay to install python312...${NC}"
             yay -S --noconfirm python312
        else
             # Try 'python312' via pacman if yay is missing
             echo -e "${YELLOW}yay not found. Trying pacman...${NC}"
             if ! install_pkg python312; then
                 echo -e "${RED}Could not install python3.12 automatically via pacman.${NC}"
                 echo -e "${YELLOW}Please install Python 3.12 manually (e.g., from AUR).${NC}"
                 exit 1
             fi
        fi
    else
        install_pkg python3.12
    fi
    
    if ! check_cmd python3.12; then
        echo -e "${RED}Failed to find or install Python 3.12.${NC}"
        echo -e "${YELLOW}Please install Python 3.12 manually and try again.${NC}"
        exit 1
    fi
    PYTHON_EXEC="python3.12"
fi

# FFmpeg
if ! check_cmd ffmpeg; then
    echo -e "${YELLOW}FFmpeg not found.${NC}"
    install_pkg ffmpeg
else
    echo -e "${GREEN}✓ FFmpeg found${NC}"
fi

# Git (Expected to be here now, but good to double check)
if ! check_cmd git; then
    install_pkg git
else
    echo -e "${GREEN}✓ Git found${NC}"
fi

# Ollama
if ! check_cmd ollama; then
    echo -e "${YELLOW}Ollama not found.${NC}"
    echo "Installing Ollama..."
    if ! curl -fsSL https://ollama.com/install.sh | sh; then
         echo -e "${RED}Failed to install Ollama usually due to sudo requirements or network.${NC}"
         echo "Please install Ollama manually: https://ollama.com"
         # Not fatal, user can install later
    fi
else
    echo -e "${GREEN}✓ Ollama found${NC}"
fi

# 2. Virtual Environment Setup
echo -e "\n${CYAN}[2/6] Setting up Virtual Environment...${NC}"
VENV_DIR="venv_bot"

if [ ! -d "$VENV_DIR" ]; then
    $PYTHON_EXEC -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${GREEN}✓ Virtual environment already exists${NC}"
fi

source "$VENV_DIR/bin/activate"

# 3. Install Python Dependencies
echo -e "\n${CYAN}[3/6] Installing Python dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt
# Install the package in editable mode to register the 'femtobot' command within the venv
pip install -e .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${RED}Failed to install dependencies${NC}"
    exit 1
fi

# 4. Configuration Setup
echo -e "\n${CYAN}[4/6] Setting up configuration...${NC}"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo -e "${GREEN}✓ Created .env from example${NC}"
        echo -e "${YELLOW}IMPORTANT: You need to edit .env with your real API keys!${NC}"
    else
        echo -e "${RED}.env.example not found!${NC}"
    fi
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# 5. Global CLI Installation (Mandatory)
echo -e "\n${CYAN}[5/6] Installing 'femtobot' CLI globally...${NC}"

# Use the existing script logic but inline or calling it
TARGET="/usr/local/bin/femtobot"
VENV_PYTHON="$(pwd)/$VENV_DIR/bin/python"

echo "Creating $TARGET ..."

# Installation logic with sudo handling
install_cli() {
    # We use sudo here, user will be prompted if not root/sudoer already
    if sudo bash -c "cat > $TARGET" << EOF
#!/bin/bash
exec "$VENV_PYTHON" -m src.cli "\$@"
EOF
    then
        sudo chmod +x "$TARGET"
        echo -e "${GREEN}✓ 'femtobot' command installed!${NC}"
    else
        echo -e "${RED}Failed to install 'femtobot' command. Please check sudo permissions.${NC}"
        # Do not fail entire script, just warn
    fi
}

install_cli

# 6. Verification
echo -e "\n${CYAN}[6/6] Verifying installation...${NC}"

# Check if ollama is running
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${YELLOW}Ollama is not running. Starting it...${NC}"
    ollama serve > /dev/null 2>&1 &
    sleep 5
fi

# Run doctor
femtobot doctor

femtobot wizard

# 7. Initial Setup
echo -e "\n${CYAN}[7/7] Running initial setup...${NC}"
femtobot setup

echo -e "\n${GREEN}=== Installation Complete! ===${NC}"
echo -e "To start the bot manually, run: ${CYAN}./run.sh${NC}"
echo -e "Or if you installed the CLI: ${CYAN}femtobot start${NC}"
echo -e "Remember to edit your ${YELLOW}.env${NC} file with your Telegram token!"
