#!/bin/bash
# Script para verificar se o ambiente está pronto para testes

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║          Verificação de Ambiente - IoT Network               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# 1. Branch
echo "📍 Branch:"
BRANCH=$(git branch --show-current)
echo "   $BRANCH"
if [ "$BRANCH" != "feature/integration" ]; then
    echo "   ⚠️  Aviso: Não estás no branch feature/integration"
fi
echo ""

# 2. Python
echo "🐍 Python:"
python3 --version
echo ""

# 3. Virtual Environment
echo "📦 Virtual Environment:"
if [ -n "$VIRTUAL_ENV" ]; then
    echo "   ✅ Ativo: $VIRTUAL_ENV"
else
    echo "   ❌ Não ativo! Executa: source venv/bin/activate"
fi
echo ""

# 4. Dependências
echo "📚 Dependências:"
echo -n "   SimpleBLE: "
python3 -c "import simpleble; print('✅ Instalado')" 2>/dev/null || echo "❌ Não instalado (pip install simpleble)"

echo -n "   Bleak: "
python3 -c "import bleak; print('✅ Instalado')" 2>/dev/null || echo "❌ Não instalado (pip install bleak)"

echo -n "   Loguru: "
python3 -c "import loguru; print('✅ Instalado')" 2>/dev/null || echo "❌ Não instalado (pip install loguru)"

echo -n "   D-Bus: "
python3 -c "import dbus; print('✅ Instalado')" 2>/dev/null || echo "❌ Não instalado (apt-get install python3-dbus)"

echo -n "   GLib: "
python3 -c "import gi; print('✅ Instalado')" 2>/dev/null || echo "❌ Não instalado (apt-get install python3-gi)"
echo ""

# 5. Bluetooth
echo "📡 Bluetooth:"
if command -v hciconfig &> /dev/null; then
    hciconfig | grep -E "(hci0|hci1)" | head -1
    echo "   $(hciconfig | grep -c 'UP RUNNING') adaptador(es) ativo(s)"
else
    echo "   ⚠️  hciconfig não encontrado"
fi
echo ""

# 6. Ficheiros principais
echo "📂 Ficheiros principais:"
echo -n "   examples/test_gatt_server.py: "
[ -f "examples/test_gatt_server.py" ] && echo "✅" || echo "❌"

echo -n "   examples/network_cli.py: "
[ -f "examples/network_cli.py" ] && echo "✅" || echo "❌"

echo -n "   examples/test_packet_send_bleak.py: "
[ -f "examples/test_packet_send_bleak.py" ] && echo "✅" || echo "❌"

echo -n "   common/ble/bleak_helper.py: "
[ -f "common/ble/bleak_helper.py" ] && echo "✅" || echo "❌"

echo -n "   common/network/neighbor_discovery.py: "
[ -f "common/network/neighbor_discovery.py" ] && echo "✅" || echo "❌"
echo ""

# 7. Resumo
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "💡 Próximos passos:"
echo ""
echo "1. Se algo está ❌, corrige primeiro"
echo "2. Abre 2 terminais (ou 2 PCs)"
echo "3. Terminal 1 (Server): sudo python3 examples/test_gatt_server.py hci0"
echo "4. Terminal 2 (Client): python3 examples/network_cli.py"
echo "5. No CLI, tenta: scan → connect <address> → status"
echo ""
echo "📖 Guia completo: cat TESTING_GUIDE.md"
echo ""
