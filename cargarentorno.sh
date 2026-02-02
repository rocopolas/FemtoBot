#!/bin/bash

# Colores para mensajes
GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

VENV_NAME="venv_bot"

echo -e "${CYAN}=== LocalBot - Configuración del Entorno ===${NC}"

# Verificar si el entorno ya existe y está funcional
if [ -d "$VENV_NAME" ] && [ -f "$VENV_NAME/bin/activate" ]; then
    echo -e "${GREEN}✓ Entorno virtual encontrado.${NC}"
    source "$VENV_NAME"/bin/activate
    
    # Verificar si las dependencias están instaladas (chequear una librería clave)
    if python -c "import telegram" 2>/dev/null; then
        echo -e "${GREEN}✓ Dependencias ya instaladas.${NC}"
        echo -e ""
        echo -e "${GREEN}=======================================${NC}"
        echo -e "${GREEN}   ¡ENTORNO LISTO!                     ${NC}"
        echo -e "${GREEN}=======================================${NC}"
        echo -e ""
        echo -e "${GREEN}✓ Estás dentro del entorno virtual${NC}"
        echo -e "Ejecuta: ${CYAN}python telegram_bot.py${NC}"
        # Spawn interactive bash keeping the venv active
        exec bash --norc --noprofile -c "source $VENV_NAME/bin/activate && exec bash"
    else
        echo -e "${YELLOW}⚠ Faltan dependencias. Instalando...${NC}"
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
fi

# Actualizar pip
echo -e "${CYAN}Actualizando pip...${NC}"
pip install --upgrade pip --quiet

# Instalar librerías desde requirements.txt
echo -e "${CYAN}Instalando dependencias desde requirements.txt...${NC}"

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
echo -e "${GREEN}   ¡INSTALACIÓN COMPLETADA CON ÉXITO!  ${NC}"
echo -e "${GREEN}=======================================${NC}"
echo -e ""
echo -e "Entrando al entorno virtual..."
# Ejecutar nuevo bash con el venv activado
exec bash --rcfile <(echo "source $VENV_NAME/bin/activate; echo -e '${GREEN}✓ Estás dentro del entorno virtual${NC}'; echo 'Ejecuta: python telegram_bot.py'")