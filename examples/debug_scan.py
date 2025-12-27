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
    print("=" * 70)
    print("  DEBUG SCAN - Ver o que o scanner BLE realmente recebe")
    print("=" * 70)
    print()

    # Criar cliente BLE
    client = BLEClient(adapter_index=0)
    print(f"Cliente BLE criado: {client.scanner.adapter.identifier()}")
    print()

    # Scan SEM filtro
    print("A fazer scan de TODOS os dispositivos BLE (sem filtro)...")
    print()

    devices = client.scanner.scan(duration_ms=5000, filter_iot=False)

    print(f"\n✅ Encontrados {len(devices)} dispositivos:")
    print()

    for i, device in enumerate(devices, 1):
        print(f"{i}. {device.address} ({device.name or 'Unknown'})")
        print(f"   RSSI: {device.rssi} dBm")
        print(f"   Service UUIDs: {device.service_uuids if device.service_uuids else 'NENHUM!'}")
        print(f"   Manufacturer Data: {device.manufacturer_data if device.manufacturer_data else 'Nenhum'}")
        print(f"   Tem IoT Service? {device.has_iot_service()}")
        print()

    print()
    print("=" * 70)

    return 0

if __name__ == '__main__':
    sys.exit(main())
