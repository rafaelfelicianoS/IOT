#!/bin/bash
# Script para configurar adaptador Bluetooth em modo LE-only
# Execute após boot: sudo bash fix_bluetooth.sh

echo "🔧 Configurando adaptador Bluetooth para modo LE-only..."

# Configurar hci0 para LE-only
sudo btmgmt -i hci0 power off
sudo btmgmt -i hci0 bredr off
sudo btmgmt -i hci0 le on
sudo btmgmt -i hci0 power on

echo "✅ Configuração aplicada!"
echo ""
echo "Verificar:"
sudo btmgmt -i hci0 info | grep "current settings"
echo ""
echo "Deve mostrar: 'le' (sem 'br/edr')"
