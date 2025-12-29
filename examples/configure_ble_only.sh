#!/bin/bash
# Script para configurar adaptador BLE em modo LE-only (desabilitar BR/EDR)
# Isto resolve o erro "br-connection-unknown" quando clientes tentam conectar via Bleak

ADAPTER=${1:-hci0}

echo "🔧 A configurar adaptador $ADAPTER para modo LE-only..."
echo ""

# 1. Verificar estado atual
echo "1️⃣  Estado atual do adaptador:"
hciconfig $ADAPTER
echo ""

# 2. Descer interface
echo "2️⃣  A descer interface..."
sudo hciconfig $ADAPTER down

# 3. Configurar para LE-only (desabilitar BR/EDR)
echo "3️⃣  A configurar modo LE-only..."
sudo btmgmt -i $ADAPTER bredr off
sudo btmgmt -i $ADAPTER le on

# 4. Subir interface
echo "4️⃣  A levantar interface..."
sudo hciconfig $ADAPTER up

# 5. Verificar configuração
echo ""
echo "5️⃣  Configuração final:"
sudo btmgmt -i $ADAPTER info | grep -E "(name|powered|connectable|discoverable|bondable|low-energy|br/edr)"

echo ""
echo "✅ Configuração concluída!"
echo ""
echo "   O adaptador $ADAPTER está agora em modo LE-only."
echo "   Isto força clientes a usarem BLE (LE) em vez de Bluetooth Classic (BR/EDR)."
echo ""
