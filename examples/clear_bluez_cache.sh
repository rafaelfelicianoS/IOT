#!/bin/bash
# Script para limpar cache do BlueZ e forçar uso de BLE (LE) em vez de Bluetooth Classic (BR/EDR)

echo "🧹 A limpar cache do BlueZ..."
echo ""

# 1. Remover dispositivo do bluetoothctl
echo "1️⃣  A remover dispositivo E0:D3:62:D6:EE:A0 do bluetoothctl..."
bluetoothctl remove E0:D3:62:D6:EE:A0 2>&1 || echo "   (Dispositivo não estava emparelhado)"

# 2. Parar serviço bluetooth
echo ""
echo "2️⃣  A parar serviço bluetooth..."
sudo systemctl stop bluetooth

# 3. Limpar cache do BlueZ (requer sudo)
echo ""
echo "3️⃣  A limpar cache /var/lib/bluetooth/..."
echo "    (Isto vai remover TODOS os dispositivos emparelhados!)"
read -p "    Confirmar? (y/N): " confirm
if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
    sudo rm -rf /var/lib/bluetooth/*/cache
    echo "    ✅ Cache limpo!"
else
    echo "    ⏭️  A saltar limpeza de cache"
fi

# 4. Reiniciar serviço bluetooth
echo ""
echo "4️⃣  A reiniciar serviço bluetooth..."
sudo systemctl start bluetooth
sleep 2

# 5. Verificar estado
echo ""
echo "5️⃣  A verificar estado do bluetooth..."
sudo systemctl status bluetooth | grep -E "(Active|Loaded)"

echo ""
echo "✅ Concluído! Agora podes testar novamente."
echo ""
echo "   Próximo passo:"
echo "   python3 examples/test_packet_send_bleak.py"
echo ""
