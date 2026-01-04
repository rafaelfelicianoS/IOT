#!/usr/bin/env python3
"""
Script para testar se o advertising está a funcionar.

Este script deve ser executado NO MESMO PC onde o GATT Server está a correr.
Vai fazer scan para verificar se o próprio dispositivo está a anunciar corretamente.

Uso:
    1. Num terminal: sudo python3 examples/test_gatt_server.py hci0
    2. Noutro terminal: python3 examples/test_advertising.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEScanner, SIMPLEBLE_AVAILABLE
from common.utils.constants import IOT_NETWORK_SERVICE_UUID
from common.utils.logger import setup_logger

# Setup logger
logger = setup_logger("test_advertising")


def main():
    """Main function."""

    logger.info("=" * 70)
    logger.info("  Test Advertising - Verifica se o servidor está a anunciar")
    logger.info("=" * 70)
    logger.info("")

    logger.info("ATENÇÃO:")
    logger.info("  Este script deve correr no MESMO PC que o GATT Server")
    logger.info("  O GATT Server deve estar a correr noutro terminal:")
    logger.info("  → sudo python3 examples/test_gatt_server.py hci0")
    logger.info("")

    if not SIMPLEBLE_AVAILABLE:
        logger.error(" SimpleBLE não está instalado!")
        return 1

    try:
        scanner = BLEScanner(adapter_index=0)
    except Exception as e:
        logger.error(f" Erro ao criar BLE Scanner: {e}")
        return 1

    logger.info(f" Scanner iniciado: {scanner.adapter.identifier()} ({scanner.adapter.address()})")
    logger.info("")

    # Fazer 3 scans de 5 segundos cada
    for attempt in range(1, 4):
        logger.info(f" Tentativa {attempt}/3 - A fazer scan de 5 segundos...")

        devices = scanner.scan(duration_ms=5000, filter_iot=False)

        logger.info(f"   Encontrados: {len(devices)} dispositivos")

        # Procurar por "IoT-Node"
        iot_node = None
        for device in devices:
            if device.name and "IoT" in device.name:
                iot_node = device
                break

        if iot_node:
            logger.info("")
            logger.info(" ENCONTRADO 'IoT-Node'!")
            logger.info(f"   Nome: {iot_node.name}")
            logger.info(f"   Endereço: {iot_node.address}")
            logger.info(f"   RSSI: {iot_node.rssi} dBm")
            logger.info("")

            if iot_node.service_uuids:
                logger.info(f"   Service UUIDs anunciados: {len(iot_node.service_uuids)}")
                for uuid in iot_node.service_uuids:
                    if uuid.lower() == IOT_NETWORK_SERVICE_UUID.lower():
                        logger.info(f"       {uuid}  ← IoT Network Service (CORRETO!)")
                    else:
                        logger.info(f"      - {uuid}")

                if iot_node.has_iot_service():
                    logger.info("")
                    logger.info(" ADVERTISING ESTÁ A FUNCIONAR CORRETAMENTE! ")
                    logger.info("")
                    logger.info("O problema NÃO é o advertising.")
                    logger.info("Possíveis causas do client não encontrar:")
                    logger.info("  1. Client e Server em PCs diferentes muito distantes")
                    logger.info("  2. Interferência Bluetooth")
                    logger.info("  3. Adaptador BLE do client com problemas")
                    return 0
                else:
                    logger.warning("")
                    logger.warning("  PROBLEMA: Service UUID incorreto!")
                    logger.warning("")
                    logger.warning(f"UUID esperado: {IOT_NETWORK_SERVICE_UUID}")
                    logger.warning(f"UUIDs anunciados: {iot_node.service_uuids}")
                    logger.warning("")
                    logger.warning("O advertising está ativo mas o UUID está errado.")
                    return 1
            else:
                logger.warning("")
                logger.warning("  PROBLEMA: 'IoT-Node' encontrado mas SEM Service UUIDs!")
                logger.warning("")
                logger.warning("O dispositivo está a anunciar mas não está a incluir")
                logger.warning("o Service UUID no advertising packet.")
                logger.warning("")
                logger.warning("Verifica em test_gatt_server.py:")
                logger.warning("  adv.add_service_uuid(service.uuid)")
                return 1

        if attempt < 3:
            logger.info(f"   'IoT-Node' não encontrado. A tentar novamente...\n")
            time.sleep(1)

    # Não encontrou em nenhuma das 3 tentativas
    logger.error("")
    logger.error(" 'IoT-Node' NÃO ENCONTRADO em 3 tentativas!")
    logger.error("")
    logger.error("Possíveis causas:")
    logger.error("  1. GATT Server não está a correr")
    logger.error("     → Executa: sudo python3 examples/test_gatt_server.py hci0")
    logger.error("")
    logger.error("  2. Advertising não foi registado com sucesso")
    logger.error("     → Verifica se o servidor mostrou: ' GATT Server a correr com Advertising!'")
    logger.error("")
    logger.error("  3. Problema com BlueZ/D-Bus")
    logger.error("     → sudo systemctl restart bluetooth")
    logger.error("")

    if devices:
        logger.error("Dispositivos encontrados (para referência):")
        for device in devices[:5]:  # Mostrar até 5
            logger.error(f"  - {device.name or 'Unknown'} ({device.address})")

    return 1


if __name__ == '__main__':
    sys.exit(main())
