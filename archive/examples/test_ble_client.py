#!/usr/bin/env python3
"""
Exemplo de teste do BLE Client.

Este script faz scan de dispositivos BLE e permite conectar a um deles.

Uso:
    python3 examples/test_ble_client.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient, SIMPLEBLE_AVAILABLE
from common.utils.constants import (
    IOT_NETWORK_SERVICE_UUID,
    CHAR_DEVICE_INFO_UUID,
    CHAR_NEIGHBOR_TABLE_UUID,
)
from common.utils.nid import NID
from common.utils.logger import setup_logger

# Setup logger
logger = setup_logger("test_ble_client")


def main():
    """Main function."""

    logger.info("=" * 60)
    logger.info("  BLE Client Test - IoT Network Scanner")
    logger.info("=" * 60)
    logger.info("")

    if not SIMPLEBLE_AVAILABLE:
        logger.error(" SimpleBLE não está instalado!")
        logger.error("")
        logger.error("Para instalar:")
        logger.error("  pip install simplepyble")
        logger.error("")
        logger.error("Ou:")
        logger.error("  sudo apt install python3-simplepyble")
        return 1

    try:
        client = BLEClient(adapter_index=0)
    except Exception as e:
        logger.error(f" Erro ao criar BLE Client: {e}")
        logger.error("")
        logger.error("Verifica:")
        logger.error("  1. Bluetooth está ativo? (sudo systemctl status bluetooth)")
        logger.error("  2. Adaptador existe? (hciconfig)")
        return 1

    # Fazer scan de dispositivos IoT
    logger.info(" A fazer scan de dispositivos IoT...")
    logger.info("   (aguarda 5 segundos)")
    logger.info("")

    devices = client.scan_iot_devices(duration_ms=5000)

    if not devices:
        logger.warning("  Nenhum dispositivo IoT encontrado")
        logger.info("")
        logger.info("Certifica-te que:")
        logger.info("  1. O GATT Server está a correr (test_gatt_server.py)")
        logger.info("  2. O advertising está ativo")
        logger.info("  3. O dispositivo está próximo")
        return 0

    # Mostrar dispositivos encontrados
    logger.info(f" Encontrados {len(devices)} dispositivos IoT:")
    logger.info("")
    for i, device in enumerate(devices, 1):
        logger.info(f"  {i}. {device}")
        logger.info(f"     Address: {device.address}")
        logger.info(f"     RSSI: {device.rssi} dBm")
        if device.service_uuids:
            logger.info(f"     Services: {len(device.service_uuids)}")
        logger.info("")

    # Conectar ao primeiro dispositivo
    logger.info("=" * 60)
    logger.info(f" A conectar ao primeiro dispositivo: {devices[0].address}")
    logger.info("=" * 60)
    logger.info("")

    conn = client.connect_to_device(devices[0])
    if not conn:
        logger.error(" Falha ao conectar")
        return 1

    logger.info(" Conectado com sucesso!")
    logger.info("")

    # Explorar serviços GATT
    logger.info(" A explorar serviços GATT...")
    services = conn.get_services()

    logger.info(f"   Encontrados {len(services)} serviços:")
    logger.info("")

    for service in services:
        logger.info(f"    Service: {service.uuid}")
        for char in service.characteristics:
            caps_str = ', '.join(char.capabilities)
            logger.info(f"      - Characteristic: {char.uuid}")
            logger.info(f"        Capabilities: {caps_str}")
        logger.info("")

    # Ler DeviceInfo
    logger.info("=" * 60)
    logger.info(" A ler DeviceInfo Characteristic...")
    logger.info("=" * 60)
    logger.info("")

    device_info_data = conn.read_characteristic(
        IOT_NETWORK_SERVICE_UUID,
        CHAR_DEVICE_INFO_UUID
    )

    if device_info_data:
        logger.info(f" DeviceInfo lida: {len(device_info_data)} bytes")
        logger.info(f"   Dados (hex): {device_info_data.hex()}")

        # Parse: NID (16) + hop_count (1) + device_type (1)
        if len(device_info_data) >= 18:
            nid_bytes = device_info_data[:16]
            hop_count = device_info_data[16]
            device_type_byte = device_info_data[17]

            nid = NID(nid_bytes)
            device_type = 'sink' if device_type_byte == 0 else 'node'

            logger.info("")
            logger.info(f"    NID: {nid.to_string()}")
            logger.info(f"      Short: {nid}")
            logger.info(f"    Hop Count: {hop_count}")
            logger.info(f"     Device Type: {device_type}")
    else:
        logger.error(" Falha ao ler DeviceInfo")

    logger.info("")

    # Ler Neighbor Table
    logger.info("=" * 60)
    logger.info(" A ler NeighborTable Characteristic...")
    logger.info("=" * 60)
    logger.info("")

    neighbor_data = conn.read_characteristic(
        IOT_NETWORK_SERVICE_UUID,
        CHAR_NEIGHBOR_TABLE_UUID
    )

    if neighbor_data:
        logger.info(f" NeighborTable lida: {len(neighbor_data)} bytes")
        logger.info(f"   Dados (hex): {neighbor_data.hex()}")

        # Parse: num_neighbors (1) + N * (NID (16) + hop_count (1))
        if len(neighbor_data) >= 1:
            num_neighbors = neighbor_data[0]
            logger.info(f"    Número de vizinhos: {num_neighbors}")

            if num_neighbors > 0:
                logger.info("")
                offset = 1
                for i in range(num_neighbors):
                    if offset + 17 <= len(neighbor_data):
                        nid_bytes = neighbor_data[offset:offset+16]
                        hop_count = neighbor_data[offset+16]

                        neighbor_nid = NID(nid_bytes)
                        logger.info(f"   {i+1}. NID: {neighbor_nid}")
                        logger.info(f"      Hop Count: {hop_count}")

                        offset += 17
    else:
        logger.error(" Falha ao ler NeighborTable")

    logger.info("")

    # Desconectar
    logger.info("=" * 60)
    logger.info(" A desconectar...")
    logger.info("=" * 60)

    conn.disconnect()
    logger.info(" Desconectado")
    logger.info("")

    return 0


if __name__ == '__main__':
    sys.exit(main())
