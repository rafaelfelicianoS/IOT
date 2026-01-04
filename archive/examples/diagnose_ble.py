#!/usr/bin/env python3
"""
Script de diagnóstico BLE - encontra TODOS os dispositivos e mostra detalhes.

Este script faz scan SEM filtro para diagnosticar problemas de descoberta.
Mostra todos os dispositivos BLE encontrados, com ou sem IoT Network Service.

Uso:
    python3 examples/diagnose_ble.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEScanner, SIMPLEBLE_AVAILABLE
from common.utils.constants import IOT_NETWORK_SERVICE_UUID
from common.utils.logger import setup_logger

# Setup logger
logger = setup_logger("diagnose_ble")


def main():
    """Main function."""

    logger.info("=" * 70)
    logger.info("  BLE Diagnostic Tool - Scan ALL Devices")
    logger.info("=" * 70)
    logger.info("")

    if not SIMPLEBLE_AVAILABLE:
        logger.error(" SimpleBLE não está instalado!")
        logger.error("")
        logger.error("Para instalar:")
        logger.error("  pip install simplepyble")
        return 1

    try:
        scanner = BLEScanner(adapter_index=0)
    except Exception as e:
        logger.error(f" Erro ao criar BLE Scanner: {e}")
        logger.error("")
        logger.error("Verifica:")
        logger.error("  1. Bluetooth está ativo? (sudo systemctl status bluetooth)")
        logger.error("  2. Adaptador existe? (hciconfig)")
        return 1

    logger.info(f" Scanner BLE iniciado")
    logger.info(f"   Adaptador: {scanner.adapter.identifier()}")
    logger.info(f"   Endereço: {scanner.adapter.address()}")
    logger.info("")

    # Fazer scan de TODOS os dispositivos (sem filtro)
    logger.info(" A fazer scan de TODOS os dispositivos BLE...")
    logger.info("   Duração: 10 segundos (scan mais longo para aumentar chances)")
    logger.info("   ATENÇÃO: Sem filtro - vai mostrar tudo!")
    logger.info("")

    devices = scanner.scan(duration_ms=10000, filter_iot=False)

    logger.info("=" * 70)
    logger.info(f" RESULTADOS DO SCAN")
    logger.info("=" * 70)
    logger.info(f"Total de dispositivos BLE encontrados: {len(devices)}")
    logger.info("")

    if not devices:
        logger.warning("  NENHUM dispositivo BLE encontrado!")
        logger.warning("")
        logger.warning("Isto indica um problema com:")
        logger.warning("  1. Adaptador Bluetooth não está a funcionar")
        logger.warning("  2. Bluetooth desligado")
        logger.warning("  3. Nenhum dispositivo BLE por perto")
        logger.warning("")
        logger.warning("Testa:")
        logger.warning("  sudo hciconfig hci0 up")
        logger.warning("  sudo systemctl restart bluetooth")
        logger.warning("  bluetoothctl")
        logger.warning("  > scan on")
        return 1

    # Mostrar todos os dispositivos encontrados
    iot_devices = []
    other_devices = []

    for device in devices:
        if device.has_iot_service():
            iot_devices.append(device)
        else:
            other_devices.append(device)

    # Mostrar dispositivos IoT (se houver)
    if iot_devices:
        logger.info(" DISPOSITIVOS IoT NETWORK ENCONTRADOS:")
        logger.info("")
        for i, device in enumerate(iot_devices, 1):
            logger.info(f"  [{i}] {device.name or 'Unknown'}")
            logger.info(f"      Endereço BLE: {device.address}")
            logger.info(f"      RSSI: {device.rssi} dBm")
            logger.info(f"      Service UUIDs anunciados:")
            for uuid in device.service_uuids:
                uuid_str = str(uuid)
                marker = "  ← IoT Network Service" if uuid_str.lower() == IOT_NETWORK_SERVICE_UUID.lower() else ""
                logger.info(f"        - {uuid_str}{marker}")
            if device.manufacturer_data:
                logger.info(f"      Manufacturer Data: {len(device.manufacturer_data)} entries")
            logger.info("")
    else:
        logger.warning("  NENHUM dispositivo IoT Network encontrado")
        logger.warning(f"    (procurando por Service UUID: {IOT_NETWORK_SERVICE_UUID})")
        logger.warning("")

    # Mostrar outros dispositivos
    if other_devices:
        logger.info(" OUTROS DISPOSITIVOS BLE (não-IoT):")
        logger.info("")
        for i, device in enumerate(other_devices, 1):
            logger.info(f"  [{i}] {device.name or 'Unknown'}")
            logger.info(f"      Endereço BLE: {device.address}")
            logger.info(f"      RSSI: {device.rssi} dBm")

            if device.service_uuids:
                logger.info(f"      Service UUIDs anunciados: {len(device.service_uuids)}")
                for uuid in device.service_uuids:
                    uuid_str = str(uuid)
                    marker = "  ← IoT Network Service" if uuid_str.lower() == IOT_NETWORK_SERVICE_UUID.lower() else ""
                    logger.info(f"        - {uuid_str}{marker}")
            else:
                logger.info(f"      Service UUIDs: <nenhum UUID anunciado>")

            if device.manufacturer_data:
                logger.info(f"      Manufacturer Data: {len(device.manufacturer_data)} entries")
            logger.info("")

    # Resumo final
    logger.info("=" * 70)
    logger.info(" RESUMO DO DIAGNÓSTICO")
    logger.info("=" * 70)
    logger.info(f"Total de dispositivos: {len(devices)}")
    logger.info(f"Dispositivos IoT Network: {len(iot_devices)}")
    logger.info(f"Outros dispositivos: {len(other_devices)}")
    logger.info("")

    if iot_devices:
        logger.info(" DIAGNÓSTICO: Tudo OK!")
        logger.info("   O GATT Server está a anunciar corretamente.")
        logger.info("   Podes usar test_ble_client.py para conectar.")
    else:
        logger.warning("  DIAGNÓSTICO: Problema identificado!")
        logger.warning("")
        if not devices:
            logger.warning("CAUSA: Adaptador BLE não está a funcionar ou nenhum dispositivo por perto")
        else:
            logger.warning("CAUSA: GATT Server não está a correr ou não está a anunciar o Service UUID correto")
            logger.warning("")
            logger.warning("Verifica no PC do servidor:")
            logger.warning("  1. GATT Server está a correr?")
            logger.warning("     → sudo python3 examples/test_gatt_server.py hci0")
            logger.warning("")
            logger.warning("  2. Procura por 'IoT-Node' na lista acima")
            logger.warning("     → Se aparecer mas sem Service UUID, o advertising está mal configurado")
            logger.warning("     → Se não aparecer, o servidor não está a correr ou está noutro PC")
            logger.warning("")
            logger.warning("  3. Testa no próprio PC do servidor:")
            logger.warning("     → bluetoothctl")
            logger.warning("     → scan on")
            logger.warning("     → Deve aparecer 'IoT-Node'")

    logger.info("")
    return 0


if __name__ == '__main__':
    sys.exit(main())
