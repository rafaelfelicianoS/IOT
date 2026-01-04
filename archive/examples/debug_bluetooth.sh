#!/bin/bash
# Script para diagnosticar problemas de Bluetooth BLE

echo "============================================"
echo "  Diagnóstico Bluetooth BLE"
echo "============================================"
echo ""

echo "1️⃣  Estado do Bluetooth Service:"
sudo systemctl status bluetooth | grep -E "(Active|Loaded)" || echo " Serviço não encontrado"
echo ""

echo "2️⃣  Adaptadores BLE disponíveis:"
hciconfig | grep -E "(hci[0-9]|UP|DOWN|RUNNING)" || echo " Nenhum adaptador encontrado"
echo ""

echo "3️⃣  Estado detalhado dos adaptadores:"
for adapter in /sys/class/bluetooth/hci*; do
    if [ -d "$adapter" ]; then
        hci=$(basename $adapter)
        echo "   $hci:"
        hciconfig $hci 2>/dev/null | grep -E "(BD Address|UP|RUNNING|RX|TX)"
    fi
done
echo ""

echo "4️⃣  Dispositivos BLE paired/connected:"
bluetoothctl devices 2>/dev/null || echo " bluetoothctl não disponível"
echo ""

echo "5️⃣  Conexões BLE ativas:"
sudo hcitool con 2>/dev/null || echo " hcitool não disponível"
echo ""

echo "6️⃣  Verificar se há dispositivos bloqueados (rfkill):"
rfkill list bluetooth || echo " rfkill não disponível"
echo ""

echo "7️⃣  Logs recentes do Bluetooth (últimos 20 erros):"
sudo journalctl -u bluetooth --no-pager --since "5 minutes ago" | grep -i -E "(error|fail|reject)" | tail -20
echo ""

echo "8️⃣  Processos usando Bluetooth:"
ps aux | grep -E "(bluez|bluetooth|hci)" | grep -v grep || echo "ℹ️  Nenhum processo BLE extra encontrado"
echo ""

echo "9️⃣  Servidor IoT a correr?"
ps aux | grep test_packet_receive | grep -v grep && echo " Servidor encontrado" || echo " Servidor NÃO está a correr"
echo ""

echo "============================================"
echo "  Diagnóstico concluído"
echo "============================================"
