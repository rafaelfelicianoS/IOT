#!/usr/bin/env python3
"""
Testa conexão ao servidor GATT e leitura de DeviceInfo.
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient
from common.utils.logger import setup_logger

logger = setup_logger("test_connection")

TARGET_SERVER = "E0:D3:62:D6:EE:A0"


def main():
    print("=" * 70)
    print("  TEST CONNECTION - Conectar ao servidor e ler DeviceInfo")
    print("=" * 70)
    print()

    # Criar cliente
    print("1️⃣  A criar cliente BLE...")
    client = BLEClient()
    print(f"   ✅ Cliente criado: {client.scanner.adapter.identifier()}")
    print()

    # Fazer scan (SEM filtro para garantir que vemos tudo)
    print(f"2️⃣  A fazer scan para encontrar {TARGET_SERVER}...")
    devices = client.scanner.scan(duration_ms=5000, filter_iot=False)
    print(f"   ✅ Scan concluído: {len(devices)} dispositivos encontrados")
    print()

    # Procurar o servidor
    target = None
    for dev in devices:
        if dev.address.upper() == TARGET_SERVER.upper():
            target = dev
            break

    if not target:
        print(f"❌ Servidor {TARGET_SERVER} NÃO encontrado no scan!")
        print()
        print("Dispositivos encontrados:")
        for i, dev in enumerate(devices, 1):
            print(f"  [{i}] {dev.address} - {dev.name or 'Unknown'} (RSSI: {dev.rssi} dBm)")
        return 1

    print(f"✅ Servidor encontrado!")
    print(f"   Address: {target.address}")
    print(f"   Name: {target.name or 'Unknown'}")
    print(f"   RSSI: {target.rssi} dBm")
    print(f"   Service UUIDs: {target.service_uuids if target.service_uuids else 'Nenhum'}")
    print(f"   Tem IoT Service? {target.has_iot_service()}")
    print()

    # Conectar
    print("3️⃣  A conectar ao servidor...")
    conn = client.connect_to_device(target)

    if not conn:
        print("❌ Falha ao conectar!")
        return 1

    print(f"   ✅ Conectado com sucesso!")
    print()

    # Ler DeviceInfo
    print("4️⃣  A ler DeviceInfo...")
    try:
        device_info = client.read_device_info(conn)
        print(f"   ✅ DeviceInfo lido com sucesso!")
        print(f"      NID: {device_info.nid}")
        print(f"      Hop count: {device_info.hop_count}")
        print(f"      Device type: {device_info.device_type}")
        print()
        success = True
    except Exception as e:
        print(f"   ❌ Erro ao ler DeviceInfo: {e}")
        import traceback
        traceback.print_exc()
        print()
        success = False

    # Desconectar
    print("5️⃣  A desconectar...")
    client.disconnect_from_device(target.address)
    print("   ✅ Desconectado")
    print()

    print("=" * 70)
    if success:
        print("  ✅ SUCESSO - Conexão e leitura funcionaram!")
    else:
        print("  ❌ FALHA - Não foi possível ler DeviceInfo")
    print("=" * 70)
    print()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
