#!/usr/bin/env python3
"""
Teste simples: apenas conectar ao servidor para debug.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 test_connect_only.py <hci_interface>")
        return 1

    adapter_index = int(sys.argv[1].replace('hci', ''))

    print("1. A criar cliente...")
    client = BLEClient(adapter_index=adapter_index)

    print("2. A fazer scan...")
    devices = client.scanner.scan(duration_ms=5000, filter_iot=True)
    print(f"   Encontrados: {len(devices)} dispositivos")

    if not devices:
        print("ERRO: Nenhum servidor encontrado!")
        return 1

    target = devices[0]
    print(f"3. A conectar a {target.address}...")

    conn = client.connect_to_device(target)

    if not conn:
        print("ERRO: Falha ao conectar!")
        return 1

    print("✅ CONECTADO COM SUCESSO!")
    print(f"   Endereço: {conn.address}")
    print(f"   Conectado: {conn.is_connected}")

    print("\n4. A listar serviços...")
    services = conn.get_services()
    print(f"   Serviços encontrados: {len(services)}")
    for svc in services:
        print(f"   - {svc.uuid}")
        for char in svc.characteristics:
            print(f"      -> {char.uuid} ({', '.join(char.capabilities)})")

    print("\n5. A desconectar...")
    client.disconnect_from_device(target.address)
    print("✅ DESCONECTADO")

    return 0

if __name__ == '__main__':
    sys.exit(main())
