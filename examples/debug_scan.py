#!/usr/bin/env python3
"""
Debug Scan - Verifica o que o scanner BLE realmente está a receber.
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient
from common.utils.logger import setup_logger

logger = setup_logger("debug_scan")

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 debug_scan.py <hci_interface>")
        print("Exemplo: python3 debug_scan.py hci0")
        print("         python3 debug_scan.py hci1")
        return 1

    adapter_name = sys.argv[1]
    adapter_index = int(adapter_name.replace('hci', ''))

    print("=" * 70)
    print("  DEBUG SCAN - Ver o que o scanner BLE realmente recebe")
    print("=" * 70)
    print(f"  Adaptador: {adapter_name} (índice {adapter_index})")
    print("=" * 70)
    print()

    # Criar cliente BLE
    client = BLEClient(adapter_index=adapter_index)
    print(f"Cliente BLE criado: {client.scanner.adapter.identifier()}")
    print(f"Endereço: {client.scanner.adapter.address()}")
    print()

    # Scan SEM filtro
    print("1️⃣  A fazer scan de TODOS os dispositivos BLE (sem filtro, 10s)...")
    print()

    devices = client.scanner.scan(duration_ms=10000, filter_iot=False)

    print(f"✅ Encontrados {len(devices)} dispositivos BLE totais")
    print()

    if len(devices) == 0:
        print("❌ NENHUM dispositivo BLE encontrado!")
        print()
        print("Isto pode indicar:")
        print("  - Nenhum dispositivo BLE por perto")
        print("  - Problema com o adaptador BLE")
        print("  - Interferência RF")
        print()
    else:
        for i, device in enumerate(devices, 1):
            print(f"{i}. {device.address} ({device.name or 'Unknown'})")
            print(f"   RSSI: {device.rssi} dBm")
            print(f"   Service UUIDs: {device.service_uuids if device.service_uuids else 'NENHUM!'}")
            print(f"   Manufacturer Data: {device.manufacturer_data if device.manufacturer_data else 'Nenhum'}")
            print(f"   Tem IoT Service? {device.has_iot_service()}")
            print()

    print("=" * 70)
    print("2️⃣  A fazer scan COM filtro IoT (10s)...")
    print()

    devices_iot = client.scanner.scan(duration_ms=10000, filter_iot=True)

    print(f"✅ Encontrados {len(devices_iot)} servidores IoT")
    print()

    if len(devices_iot) == 0:
        print("❌ NENHUM servidor IoT encontrado!")
        print()
        print("Certifica-te que:")
        print("  1. O servidor está a correr noutra máquina")
        print("  2. O advertising está ativo")
        print("  3. UUID correto: 12340000-0000-1000-8000-00805f9b34fb")
        print()
    else:
        for i, device in enumerate(devices_iot, 1):
            print(f"{i}. {device.address} ({device.name or 'Unknown'})")
            print(f"   RSSI: {device.rssi} dBm")
            print(f"   Service UUIDs: {device.service_uuids}")
            print()

    print("=" * 70)
    print(f"RESUMO: {len(devices)} BLE totais, {len(devices_iot)} IoT")
    print("=" * 70)

    return 0

if __name__ == '__main__':
    sys.exit(main())
