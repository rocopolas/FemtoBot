#!/bin/bash
set -e

# Colores para mensajes
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VENV_NAME="venv_bot"

# Ensure we are in the script's directory
cd "$(dirname "$0")"

echo -e "${CYAN}=== LocalBot - Iniciando ===${NC}"

# Verificar si el entorno ya existe y está funcional
if [ -d "$VENV_NAME" ] && [ -f "$VENV_NAME/bin/activate" ]; then
    echo -e "${GREEN}✓ Entorno virtual encontrado.${NC}"
    source "$VENV_NAME"/bin/activate
    
    # Verificar si las dependencias están instaladas
    if python -c "import telegram" 2>/dev/null; then
        echo -e "${GREEN}✓ Dependencias instaladas.${NC}"
    else
        echo -e "${YELLOW}⚠ Faltan dependencias. Instalando...${NC}"
        pip install -r requirements.txt
    fi
else
    echo -e "${CYAN}Creando entorno virtual nuevo...${NC}"
    
    # Verificar Python 3.12
    if ! command -v python3.12 &> /dev/null; then
        echo -e "${RED}Python 3.12 no detectado.${NC}"
        echo -e "${CYAN}Instalando Python 3.12... (te pedirá contraseña)${NC}"
        sudo dnf install python3.12 -y
    else
        echo -e "${GREEN}✓ Python 3.12 detectado.${NC}"
    fi
    
    # Crear entorno virtual
    python3.12 -m venv "$VENV_NAME"
    source "$VENV_NAME"/bin/activate
    
    # Actualizar pip e instalar dependencias
    echo -e "${CYAN}Instalando dependencias...${NC}"
    pip install --upgrade pip --quiet
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        if [ $? -ne 0 ]; then
            echo -e "${RED}Error instalando dependencias${NC}"
            exit 1
        fi
    else
        echo -e "${RED}Error: requirements.txt no encontrado${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}=======================================${NC}"
    echo -e "${GREEN}   ¡INSTALACIÓN COMPLETADA!            ${NC}"
    echo -e "${GREEN}=======================================${NC}"
fi

echo -e ""
echo -e "${GREEN}🚀 Iniciando LocalBot...${NC}"
echo -e ""

# Run the Telegram bot
python src/telegram_bot.py
