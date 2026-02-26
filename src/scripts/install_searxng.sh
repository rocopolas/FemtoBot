#!/bin/bash
# SearXNG Installation Script for FemtoBot
# Installs SearXNG using Docker Compose for maximum compatibility

set -e

GREEN='\033[0;32m'
CYAN='\033[0;36m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

INSTALL_DIR="$HOME/searxng-docker"

echo -e "${CYAN}=== SearXNG Docker Installation for FemtoBot ===${NC}"
echo -e "${YELLOW}Using Docker Compose for maximum OS compatibility.${NC}"
echo ""

# Check dependencies
echo -e "${CYAN}[1/4] Checking dependencies...${NC}"
for cmd in git docker docker-compose; do
    # Fallback to 'docker compose' plugin if 'docker-compose' command doesn't exist
    if [ "$cmd" = "docker-compose" ]; then
        if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
            echo -e "${RED}✗ docker-compose (or docker compose plugin) is required. Install it first.${NC}"
            exit 1
        fi
        continue
    fi
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}✗ $cmd is required. Install it first.${NC}"
        exit 1
    fi
done

# Ensure docker daemon is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker daemon is not running or you don't have permissions (try sudo usermod -aG docker \$USER).${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Dependencies OK${NC}"

# Setup directory
echo -e "\n${CYAN}[2/4] Setting up SearXNG Docker environment...${NC}"
if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Directory $INSTALL_DIR already exists, updating...${NC}"
    cd "$INSTALL_DIR"
    git pull origin master --quiet
else
    git clone https://github.com/searxng/searxng-docker.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi
echo -e "${GREEN}✓ Environment ready at $INSTALL_DIR${NC}"

# Configure
echo -e "\n${CYAN}[3/4] Configuring JSON API and keys...${NC}"
cp -n .env.template .env 2>/dev/null || true

# Generate secret key in .env if not exists
if grep -q "SEARXNG_SECRET=" .env; then
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i "s|SEARXNG_SECRET=.*|SEARXNG_SECRET=$SECRET_KEY|g" .env
fi

# Enable JSON format in settings.yml
cat > searxng/settings.yml << SETTINGS
use_default_settings: true

general:
  instance_name: "FemtoBot Search"

search:
  safe_search: 0
  autocomplete: ""
  default_lang: ""
  formats:
    - html
    - json

server:
  port: 8080
  bind_address: "0.0.0.0"
  secret_key: "${SECRET_KEY:-$(openssl rand -hex 32)}"
  limiter: false
  image_proxy: false

ui:
  static_use_hash: true

enabled_plugins:
  - 'Hash plugin'
  - 'Self Information'
  - 'Tracker URL remover'
SETTINGS

echo -e "${GREEN}✓ Settings configured (JSON API enabled)${NC}"

# Ensure proper permissions for the searxng user inside docker
sudo chown -R 977:977 . || echo -e "${YELLOW}Could not chown to 977 (docker mapping), it might still work.${NC}"

# Start Docker
echo -e "\n${CYAN}[4/4] Starting SearXNG via Docker Compose...${NC}"
echo -e "${YELLOW}This may take a minute to pull images and start up.${NC}"

if command -v docker-compose &> /dev/null; then
    docker-compose up -d
else
    docker compose up -d
fi

echo -e "\n${GREEN}=== SearXNG Installation Complete ===${NC}"
echo -e "Wait a few seconds for the container to fully start."
echo -e "URL: ${CYAN}http://localhost:8080${NC}"
echo -e "Test: ${CYAN}curl -s 'http://localhost:8080/search?q=hello&format=json' | python3 -m json.tool | head${NC}"
echo -e "\nMake sure your ${YELLOW}config.yaml${NC} has:"
echo -e "  ${CYAN}SEARXNG_URL: http://localhost:8080${NC}"
