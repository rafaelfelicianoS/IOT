#!/bin/bash
# Script para configurar adaptador BLE em modo LE-only e limpar cache

ADAPTER=${1:-hci0}

echo "=========================================="
echo "  Configuração Bluetooth - IoT Network"
echo "=========================================="
echo ""

# 1. Verificar estado atual
echo "1. Estado atual do adaptador $ADAPTER:"
hciconfig $ADAPTER 2>/dev/null
if [ $? -ne 0 ]; then
    echo "ERRO: Adaptador $ADAPTER não encontrado!"
    echo ""
    echo "Adaptadores disponíveis:"
    hciconfig -a | grep "hci" | cut -d: -f1
    exit 1
fi
echo ""

# 2. Descer interface
echo "2. A descer interface..."
sudo hciconfig $ADAPTER down
echo ""

# 3. Configurar para LE-only (desabilitar BR/EDR)
echo "3. A configurar modo LE-only..."
sudo btmgmt -i $ADAPTER bredr off
sudo btmgmt -i $ADAPTER le on
echo ""

# 4. Limpar cache do BlueZ (opcional mas recomendado)
echo "4. A limpar cache do BlueZ..."
sudo systemctl stop bluetooth
sudo rm -rf /var/lib/bluetooth/*
sudo systemctl start bluetooth
sleep 2
echo ""

# 5. Subir interface
echo "5. A levantar interface..."
sudo hciconfig $ADAPTER up
echo ""

# 6. Verificar configuração
echo "6. Configuração final:"
sudo btmgmt -i $ADAPTER info | grep -E "(name|powered|connectable|discoverable|low-energy|br/edr)"
echo ""

echo "=========================================="
echo "  Configuração concluída!"
echo "=========================================="
echo ""
echo "Adaptador $ADAPTER está pronto para uso."
echo ""
