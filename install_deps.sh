#!/bin/bash
#
# Script de instalação de dependências do sistema e Python
# Execute com: sudo bash install_deps.sh
#

set -e

echo "=================================================="
echo "  IoT Bluetooth Network - Instalação"
echo "=================================================="
echo ""

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Verificar se está a correr como root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Por favor, execute como root: sudo bash install_deps.sh${NC}"
    exit 1
fi

echo -e "${BLUE}[1/4] A atualizar repositórios...${NC}"
apt-get update -qq

echo -e "${BLUE}[2/4] A instalar dependências do sistema...${NC}"
apt-get install -y \
    bluez bluez-tools libbluetooth-dev \
    python3-dbus python3-gi libglib2.0-dev \
    python3-dev python3-pip python3-venv \
    build-essential pkg-config \
    libdbus-1-dev libgirepository1.0-dev \
    bluetooth

echo -e "${BLUE}[3/4] A verificar Bluetooth...${NC}"
systemctl status bluetooth --no-pager | head -3

echo -e "${BLUE}[4/4] A configurar Python virtual environment...${NC}"

# Voltar ao user normal para criar venv
ORIGINAL_USER=${SUDO_USER:-$USER}
ORIGINAL_HOME=$(eval echo ~$ORIGINAL_USER)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"

cd "$PROJECT_DIR"

# Criar venv como user normal com acesso aos pacotes do sistema
sudo -u $ORIGINAL_USER python3 -m venv --system-site-packages venv

# Instalar dependências Python
sudo -u $ORIGINAL_USER bash << 'EOF'
source venv/bin/activate
pip install --upgrade pip -q
# Instalar apenas os pacotes que não vêm do sistema
pip install loguru python-dotenv typer rich cryptography bleak simplepyble -q
echo "✅ Dependências Python instaladas!"
EOF

echo ""
echo -e "${GREEN}=================================================="
echo -e "  ✅ Instalação concluída com sucesso!"
echo -e "==================================================${NC}"
echo ""
echo "Próximos passos:"
echo "  1. Os scripts iot-node e iot-sink ativam o venv automaticamente"
echo "  2. Testar Node: ./iot-node interactive"
echo "  3. Testar Sink: ./iot-sink interactive hci0"
echo ""
echo "Verificar Bluetooth:"
echo "  - hciconfig"
echo "  - bluetoothctl scan on"
echo ""
