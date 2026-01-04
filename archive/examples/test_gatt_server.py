#!/usr/bin/env python3
"""
Exemplo de teste do GATT Server.

Este script cria um serviço GATT IoT simples e regista-o com o BlueZ.
Pode ser usado para testar a implementação base do GATT Server.

Uso:
    sudo python3 examples/test_gatt_server.py hci0
"""

import sys
import signal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_server import Application, register_application
from common.ble.gatt_services import IoTNetworkService
from common.ble.advertising import Advertisement, register_advertisement
from common.utils.nid import NID
from common.utils.logger import setup_logger
from common.protocol.heartbeat import create_heartbeat_packet
from common.utils.constants import HEARTBEAT_INTERVAL

# Setup logger
logger = setup_logger("test_gatt_server")

# Global mainloop
mainloop = None


def signal_handler(sig, frame):
    """Handler para Ctrl+C."""
    logger.info("\nA terminar...")
    if mainloop:
        mainloop.quit()
    sys.exit(0)


def packet_received_callback(packet_bytes: bytes):
    """
    Callback chamado quando um pacote é recebido.

    Args:
        packet_bytes: Bytes do pacote
    """
    logger.info(f" Pacote recebido: {len(packet_bytes)} bytes")
    logger.info(f"   Dados (hex): {packet_bytes.hex()}")


def auth_callback(auth_data: bytes, sender: str) -> bytes:
    """
    Callback para autenticação.

    Args:
        auth_data: Dados de autenticação
        sender: ID do sender

    Returns:
        Resposta de autenticação
    """
    logger.info(f" Auth request de {sender}: {len(auth_data)} bytes")

    # Resposta simples (em produção, processar certificado X.509)
    response = b"AUTH_OK"
    return response


def main(argv):
    """Main function."""
    global mainloop

    if len(argv) < 2:
        logger.error("Uso: sudo python3 test_gatt_server.py <hci_interface>")
        logger.error("Exemplo: sudo python3 test_gatt_server.py hci0")
        return 1

    adapter_name = argv[1]

    logger.info("=" * 60)
    logger.info("  GATT Server Test - IoT Network Service")
    logger.info("=" * 60)

    # Gerar NID para este dispositivo
    device_nid = NID.generate()
    logger.info(f"\n Device NID: {device_nid.to_string()}")
    logger.info(f"   Short: {device_nid}")

    import dbus
    import dbus.mainloop.glib
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    app = Application(bus)

    logger.info("\n A criar IoTNetworkService...")
    service = IoTNetworkService(
        bus,
        '/org/bluez/iot/service',
        0,
        device_nid,
        device_type="node",
    )

    # Configurar callbacks
    service.get_packet_characteristic().set_packet_callback(packet_received_callback)
    service.get_auth_characteristic().set_auth_callback(auth_callback)

    # Atualizar hop count (simulando dispositivo conectado)
    service.get_device_info_characteristic().update_hop_count(1)

    # Simular vizinhos
    neighbors = [
        {'nid': NID.generate(), 'hop_count': 0},
        {'nid': NID.generate(), 'hop_count': 1},
    ]
    service.get_neighbor_characteristic().update_neighbors(neighbors)

    app.add_service(service)

    logger.info("\n Application criada com sucesso!")
    logger.info(f"   Service UUID: {service.uuid}")
    logger.info(f"   Characteristics: {len(service.get_characteristics())}")

    # Registar application
    logger.info(f"\n A registar application no adaptador {adapter_name}...")

    try:
        mainloop = register_application(app, adapter_name)
    except Exception as e:
        logger.error(f" Erro ao registar application: {e}")
        logger.error("\nVerifique:")
        logger.error(f"  1. Adaptador {adapter_name} existe? (hciconfig)")
        logger.error("  2. Bluetooth está ativo? (sudo systemctl status bluetooth)")
        logger.error("  3. A correr com sudo?")
        return 1

    logger.info(f"\n A criar BLE Advertisement...")

    import dbus
    bus = dbus.SystemBus()

    adv = Advertisement(bus, 0, Advertisement.TYPE_PERIPHERAL)
    adv.add_service_uuid(service.uuid)  # Anunciar o IoT Network Service
    adv.set_local_name("IoT-Node")
    adv.include_tx_power = True
    adv.discoverable = True

    logger.info(f"   Service UUID: {service.uuid}")
    logger.info(f"   Local Name: IoT-Node")

    # Registar advertisement
    logger.info(f" A registar advertisement...")
    register_advertisement(adv, adapter_name)

    # Timers para simular mudanças periódicas
    from gi.repository import GLib

    neighbor_update_count = 0
    heartbeat_sequence = 0
    last_heartbeat_packet = None  # Para testes de replay
    heartbeat_enabled = True  # Flag para controlar heartbeats

    # Arquivo de controlo para heartbeats
    heartbeat_control_file = Path(__file__).parent.parent / "logs" / "heartbeat_control"

    # Resetar controlo de heartbeat no arranque (começar sempre com heartbeats ativos)
    try:
        heartbeat_control_file.parent.mkdir(parents=True, exist_ok=True)
        with open(heartbeat_control_file, 'w') as f:
            f.write("start")
        logger.info(" Controlo de heartbeat resetado: heartbeats ATIVOS por padrão")
    except Exception as e:
        logger.warning(f"Erro ao resetar controlo de heartbeat: {e}")

    def check_heartbeat_control():
        """Verifica arquivo de controlo para ligar/desligar heartbeats."""
        nonlocal heartbeat_enabled
        try:
            if heartbeat_control_file.exists():
                with open(heartbeat_control_file, 'r') as f:
                    command = f.read().strip().lower()
                    if command == "stop":
                        if heartbeat_enabled:
                            heartbeat_enabled = False
                            logger.info(" Heartbeats DESABILITADOS (comando: stop)")
                    elif command == "start":
                        if not heartbeat_enabled:
                            heartbeat_enabled = True
                            logger.info("▶  Heartbeats HABILITADOS (comando: start)")
        except Exception as e:
            logger.debug(f"Erro ao ler heartbeat_control: {e}")
        return True  # Continuar timer

    def simulate_neighbor_change():
        """Simula mudanças periódicas na neighbor table."""
        nonlocal neighbor_update_count
        neighbor_update_count += 1

        # Alternar entre diferentes números de vizinhos
        num_neighbors = (neighbor_update_count % 4) + 1  # 1, 2, 3, 4, 1, 2, ...

        new_neighbors = [
            {'nid': NID.generate(), 'hop_count': i}
            for i in range(num_neighbors)
        ]

        service.get_neighbor_characteristic().update_neighbors(new_neighbors)
        logger.info(f" Neighbor table atualizada: {num_neighbors} vizinhos (update #{neighbor_update_count})")

        return True  # Continuar timer

    def send_heartbeat():
        """Envia heartbeat periódico via NetworkPacketCharacteristic."""
        nonlocal heartbeat_sequence, last_heartbeat_packet, heartbeat_enabled

        if not heartbeat_enabled:
            return True  # Continuar timer mas não enviar

        heartbeat_sequence += 1

        heartbeat_packet = create_heartbeat_packet(
            sink_nid=device_nid,
            sequence=heartbeat_sequence,
        )

        # TESTE: Reenviar alguns pacotes para testar replay detection
        if heartbeat_sequence in [15, 16, 25]:
            # Reenviar pacote anterior (replay attack)
            if last_heartbeat_packet is not None:
                logger.warning(f"  TESTE: Reenviando heartbeat anterior (REPLAY ATTACK)")
                packet_bytes = last_heartbeat_packet
                service.get_packet_characteristic().notify_packet(packet_bytes)

        packet_bytes = heartbeat_packet.to_bytes()
        service.get_packet_characteristic().notify_packet(packet_bytes)
        last_heartbeat_packet = packet_bytes

        logger.info(f" Heartbeat enviado: seq={heartbeat_sequence}")

        return True  # Continuar timer

    # Agendar mudanças a cada 10 segundos (neighbor table)
    GLib.timeout_add_seconds(10, simulate_neighbor_change)
    logger.info("  Timer configurado: neighbor table será atualizada a cada 10 segundos")

    # Agendar heartbeats a cada HEARTBEAT_INTERVAL segundos
    GLib.timeout_add_seconds(HEARTBEAT_INTERVAL, send_heartbeat)
    logger.info(f" Timer configurado: heartbeats serão enviados a cada {HEARTBEAT_INTERVAL} segundos")

    GLib.timeout_add_seconds(1, check_heartbeat_control)
    logger.info(" Timer de controlo de heartbeat configurado (verifica a cada 1s)")

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("\n" + "=" * 60)
    logger.info("   GATT Server a correr com Advertising!")
    logger.info("=" * 60)
    logger.info("\nDispositivo visível e disponível para conexões BLE.")
    logger.info("Pressione Ctrl+C para terminar.\n")

    logger.info(" Para testar com bluetoothctl:")
    logger.info("   1. bluetoothctl")
    logger.info("   2. scan on  → deve aparecer 'IoT-Node'")
    logger.info("   3. connect <MAC_ADDRESS>")
    logger.info("   4. list-attributes")
    logger.info("")

    # Run mainloop
    try:
        mainloop.run()
    except KeyboardInterrupt:
        logger.info("\nA terminar...")

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
