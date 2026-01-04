#!/usr/bin/env python3
"""
Test SimpleBLE direct write without characteristic enumeration.
SimpleBLE can connect and write even if characteristics() returns empty.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient
import time

TARGET_ADDRESS = "E0:D3:62:D6:EE:A0"
SERVICE_UUID = "12340000-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "12340001-0000-1000-8000-00805f9b34fb"

def main():
    print(" Iniciando BLE Client...")
    client = BLEClient(adapter_index=0)

    print(" A fazer scan...")
    devices = client.scanner.scan(duration_ms=5000, filter_iot=True)
    if not devices:
        print(" Nenhum dispositivo encontrado!")
        return

    target = None
    for dev in devices:
        if dev.address.upper() == TARGET_ADDRESS.upper():
            target = dev
            break

    if not target:
        print(f" Dispositivo {TARGET_ADDRESS} não encontrado!")
        return

    print(f" Dispositivo encontrado: {target.address}")

    print(f"\n A conectar...")
    conn = client.connect_to_device(target)
    if not conn:
        print(" Falha ao conectar!")
        return

    print(f" Conectado: {conn.is_connected}")

    # Aguardar um pouco
    print("\n A aguardar 2 segundos...")
    time.sleep(2)

    # Tentar escrever DIRETAMENTE sem enumerar características
    print(f"\n  A tentar escrever diretamente para {CHAR_UUID}...")
    test_data = b"Hello from SimpleBLE!"

    try:
        # Usar write_request (com resposta)
        conn.peripheral.write_request(SERVICE_UUID, CHAR_UUID, test_data)
        print(f"    Escrita bem-sucedida!")
    except Exception as e:
        print(f"    Erro: {e}")

    print(f"\n A desconectar...")
    client.disconnect_from_device(TARGET_ADDRESS)
    print(" Desconectado!")

if __name__ == "__main__":
    main()
