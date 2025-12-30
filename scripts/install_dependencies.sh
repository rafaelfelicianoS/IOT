#!/bin/bash
#
# Script para instalar dependências do sistema para o projeto IoT Network
#

set -e  # Exit on error

echo "========================================="
echo "  IoT Network - Instalação de Dependências"
echo "========================================="
echo ""

# Verificar se está a correr como root
if [ "$EUID" -eq 0 ]; then
    echo "⚠️  NÃO execute este script como root/sudo"
    echo "   O script pedirá sudo quando necessário"
    exit 1
fi

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}1️⃣  A instalar dependências do sistema...${NC}"
echo ""

# Dependências do sistema necessárias
SYSTEM_DEPS=(
    # Build tools
    build-essential
    cmake
    pkg-config

    # Python development
    python3-dev
    python3-pip
    python3-venv

    # D-Bus e GLib (para GATT Server)
    libdbus-1-dev
    libglib2.0-dev
    libgirepository1.0-dev

    # Python D-Bus e GObject (via apt é mais fácil)
    python3-dbus
    python3-gi
    python3-gi-cairo
    gir1.2-gtk-3.0

    # Bluetooth
    bluez
    libbluetooth-dev
)

echo "Pacotes a instalar:"
for pkg in "${SYSTEM_DEPS[@]}"; do
    echo "  - $pkg"
done
echo ""

read -p "Instalar estes pacotes? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
    echo "❌ Instalação cancelada"
    exit 1
fi

echo ""
sudo apt-get update
sudo apt-get install -y "${SYSTEM_DEPS[@]}"

echo ""
echo -e "${GREEN}✅ Dependências do sistema instaladas${NC}"
echo ""

echo -e "${YELLOW}2️⃣  A verificar virtual environment...${NC}"
echo ""

# Verificar se venv existe
if [ ! -d "venv" ]; then
    echo "Virtual environment não encontrado. A criar..."
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment criado${NC}"
else
    echo -e "${GREEN}✅ Virtual environment já existe${NC}"
fi

echo ""
echo -e "${YELLOW}3️⃣  A instalar dependências Python...${NC}"
echo ""

# Ativar venv e instalar requirements
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Instalar requirements
if [ -f "requirements.txt" ]; then
    echo "A instalar requirements.txt..."
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Requirements instalados${NC}"
else
    echo -e "${RED}❌ requirements.txt não encontrado${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}4️⃣  A verificar instalação...${NC}"
echo ""

# Verificar imports críticos
python3 -c "
import sys
errors = []

try:
    import dbus
    print('✅ dbus-python OK')
except ImportError as e:
    errors.append(f'❌ dbus-python: {e}')

try:
    import gi
    print('✅ PyGObject OK')
except ImportError as e:
    errors.append(f'❌ PyGObject: {e}')

try:
    import simplepyble
    print('✅ SimplePyBLE OK')
except ImportError as e:
    errors.append(f'❌ SimplePyBLE: {e}')

try:
    import cryptography
    print('✅ Cryptography OK')
except ImportError as e:
    errors.append(f'❌ Cryptography: {e}')

if errors:
    print('')
    print('ERROS:')
    for err in errors:
        print(f'  {err}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "========================================="
    echo -e "${GREEN}✅ INSTALAÇÃO COMPLETA${NC}"
    echo "========================================="
    echo ""
    echo "Para ativar o virtual environment:"
    echo "  source venv/bin/activate"
    echo ""
    echo "Para testar:"
    echo "  python3 examples/test_connection.py"
    echo "  python3 examples/test_packet_send.py"
    echo ""
else
    echo ""
    echo -e "${RED}❌ Alguns módulos falharam a instalação${NC}"
    echo ""
    echo "Tenta instalar manualmente:"
    echo "  sudo apt-get install python3-dbus python3-gi"
    echo ""
    exit 1
fi
