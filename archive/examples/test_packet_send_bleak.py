#!/usr/bin/env python3
"""
Teste de envio de pacotes encriptados usando Bleak.

Bleak é usado para operações de WRITE (client → server)
porque SimpleBLE não suporta write em Linux.

Uso:
    Terminal 1 (Server): sudo python3 examples/test_gatt_server.py hci0
    Terminal 2 (Client): python3 examples/test_packet_send_bleak.py
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from bleak import BleakClient, BleakScanner
from common.utils.constants import IOT_NETWORK_SERVICE_UUID, CHAR_NETWORK_PACKET_UUID
from common.utils.logger import setup_logger
from common.utils.nid import NID
from common.network.packet import Packet
from common.utils.constants import MessageType

# Setup logger
logger = setup_logger("test_packet_send_bleak")

TARGET_ADDRESS = "E0:D3:62:D6:EE:A0"


async def main():
    """Main function."""

    logger.info("=" * 70)
    logger.info("  Test: Packet Send with Bleak")
    logger.info("=" * 70)
    logger.info("")

    # Fazer scan de dispositivos BLE
    logger.info(" A fazer scan de dispositivos BLE...")
    devices = await BleakScanner.discover(timeout=5.0, return_adv=True)

    target = None
    target_rssi = None
    for device, adv_data in devices.values():
        if device.address.upper() == TARGET_ADDRESS.upper():
            target = device
            target_rssi = adv_data.rssi
            logger.info(f" Encontrado: {device.name or 'Unknown'} ({device.address})")
            logger.info(f"   RSSI: {adv_data.rssi}")
            break

    if not target:
        logger.error(f" Dispositivo {TARGET_ADDRESS} não encontrado!")
        logger.info("\nDispositivos encontrados:")
        for device, adv_data in devices.values():
            logger.info(f"   - {device.address} ({device.name or 'Unknown'}) RSSI: {adv_data.rssi}")
        logger.info("\nCertifica-te que o GATT Server está a correr:")
        logger.info("  sudo python3 examples/test_gatt_server.py hci0")
        return 1

    # Conectar ao dispositivo
    logger.info(f"\n A conectar ao dispositivo com timeout de 30s...")
    logger.info(f"   A usar BLEDevice object em vez de endereço string")
    logger.info(f"   (Isto preserva o address type correto do scanner)")
    try:
        # Usar o BLEDevice object em vez da string do endereço
        # Isto preserva o address type (public vs random) do scanner
        async with BleakClient(target, timeout=30.0) as client:
            logger.info(f" Conectado: {client.is_connected}")

            # Descobrir serviços
            logger.info(f"\n A descobrir serviços...")
            services_found = False
            for service in client.services:
                if service.uuid.lower() == IOT_NETWORK_SERVICE_UUID.lower():
                    logger.info(f" IoT Network Service encontrado: {service.uuid}")
                    services_found = True

                    # Procurar característica NETWORK_PACKET
                    for char in service.characteristics:
                        if char.uuid.lower() == CHAR_NETWORK_PACKET_UUID.lower():
                            logger.info(f" NETWORK_PACKET Characteristic encontrada: {char.uuid}")
                            logger.info(f"   Properties: {char.properties}")
                            break

            if not services_found:
                logger.error(" IoT Network Service não encontrado!")
                return 1

            logger.info("\n A criar pacote de teste...")

            # NIDs de teste
            source_nid = NID.generate()
            dest_nid = NID.generate()

            logger.info(f"   Source NID: {source_nid}")
            logger.info(f"   Dest NID: {dest_nid}")

            test_payload = b"Hello from Bleak! Testing encrypted packet transmission."
            packet = Packet.create(
                source=source_nid,
                destination=dest_nid,
                msg_type=MessageType.DATA,
                payload=test_payload,
                sequence=1,
                ttl=5,
            )

            logger.info(f"   Packet Type: DATA (0x{MessageType.DATA:02x})")
            logger.info(f"   Payload: {len(test_payload)} bytes")
            logger.info(f"   Total Packet Size: {packet.size()} bytes")

            # Serializar pacote
            packet_bytes = packet.to_bytes()
            logger.info(f"   Serialized: {packet_bytes[:32].hex()}...")

            logger.info(f"\n  A enviar pacote via Bleak...")
            logger.info(f"   Service: {IOT_NETWORK_SERVICE_UUID}")
            logger.info(f"   Characteristic: {CHAR_NETWORK_PACKET_UUID}")
            logger.info(f"   Data: {len(packet_bytes)} bytes")

            try:
                # Write com resposta (write request)
                await client.write_gatt_char(CHAR_NETWORK_PACKET_UUID, packet_bytes, response=True)
                logger.info(f" SUCESSO! Pacote enviado com sucesso!")
                logger.info(f"   {len(packet_bytes)} bytes escritos na característica")

            except Exception as write_error:
                logger.error(f" Erro ao escrever: {write_error}")
                import traceback
                traceback.print_exc()
                return 1

            # Aguardar um pouco antes de desconectar
            logger.info("\n A aguardar 2 segundos antes de desconectar...")
            await asyncio.sleep(2)

            logger.info("\n Teste concluído com sucesso!")

    except Exception as e:
        logger.error(f" Erro durante conexão: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1

    logger.info("")
    logger.info("=" * 70)
    logger.info(" Teste terminado")
    logger.info("=" * 70)
    logger.info("")

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
