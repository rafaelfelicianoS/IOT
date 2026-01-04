#!/usr/bin/env python3
"""
Exemplo de GATT Server com Autenticação X.509.

Este servidor GATT:
1. Carrega certificado do dispositivo
2. Aceita conexões BLE
3. Requer autenticação via AuthCharacteristic antes de aceitar pacotes
4. Envia heartbeats após autenticação

Uso:
    sudo python3 examples/test_gatt_server_with_auth.py hci0 <device_nid>

Exemplo:
    sudo python3 examples/test_gatt_server_with_auth.py hci0 323b6aad-08bc-4ab7-86c8-e94f6a141fcd
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
from common.security import CertificateManager
from common.security.auth_handler import AuthenticationHandler

# Setup logger
logger = setup_logger("gatt_server_auth")

# Global mainloop
mainloop = None

# Authenticated clients
authenticated_clients = set()


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
    # TODO: Verificar se cliente está autenticado antes de aceitar pacote
    logger.info(f" Pacote recebido: {len(packet_bytes)} bytes")
    logger.info(f"   Dados (hex): {packet_bytes.hex()}")


def on_client_authenticated(client_id: str, peer_info: dict):
    """
    Callback chamado quando um cliente é autenticado com sucesso.

    Args:
        client_id: ID do cliente
        peer_info: Informações do peer autenticado
    """
    logger.info("=" * 60)
    logger.info(f" CLIENTE AUTENTICADO!")
    logger.info("=" * 60)
    logger.info(f"Cliente: {client_id}")
    logger.info(f"Peer NID: {peer_info['nid']}")
    logger.info(f"Peer tipo: {'SINK' if peer_info['is_sink'] else 'NODE'}")
    logger.info("=" * 60)

    authenticated_clients.add(client_id)


def on_auth_failed(client_id: str):
    """
    Callback chamado quando autenticação falha.

    Args:
        client_id: ID do cliente
    """
    logger.error("=" * 60)
    logger.error(f" AUTENTICAÇÃO FALHOU!")
    logger.error("=" * 60)
    logger.error(f"Cliente: {client_id}")
    logger.error("=" * 60)


def main(argv):
    """Main function."""
    global mainloop

    if len(argv) < 3:
        logger.error("Uso: sudo python3 test_gatt_server_with_auth.py <hci_interface> <device_nid>")
        logger.error("Exemplo: sudo python3 test_gatt_server_with_auth.py hci0 323b6aad-08bc-4ab7-86c8-e94f6a141fcd")
        return 1

    adapter_name = argv[1]
    device_nid_str = argv[2]

    try:
        device_nid = NID(device_nid_str)
    except ValueError as e:
        logger.error(f" NID inválido: {e}")
        return 1

    logger.info("=" * 60)
    logger.info("  GATT Server com Autenticação X.509")
    logger.info("=" * 60)
    logger.info(f"\n Device NID: {device_nid}")

    # Carregar certificados
    logger.info("\n Carregando certificados...")
    cert_manager = CertificateManager(device_nid)

    if not cert_manager.initialize():
        logger.error(" Erro ao carregar certificados")
        logger.error(f"\nVerifique se existem certificados para este dispositivo:")
        logger.error(f"  certs/{device_nid.to_string()}/certificate.pem")
        logger.error(f"  certs/{device_nid.to_string()}/private_key.pem")
        logger.error(f"  certs/ca_certificate.pem")
        return 1

    logger.info("\n Criando Authentication Handler...")
    auth_handler = AuthenticationHandler(cert_manager)
    auth_handler.set_authenticated_callback(on_client_authenticated)
    auth_handler.set_auth_failed_callback(on_auth_failed)

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
        device_type="sink" if cert_manager.is_sink_certificate(cert_manager.device_cert) else "node",
    )

    # Configurar callbacks
    service.get_packet_characteristic().set_packet_callback(packet_received_callback)

    # Configurar auth callback para usar o AuthenticationHandler
    def auth_callback(auth_data: bytes, sender: str) -> bytes:
        """Callback de autenticação que usa o AuthenticationHandler."""
        response = auth_handler.handle_auth_message(auth_data, sender)
        return response if response else b''

    service.get_auth_characteristic().set_auth_callback(auth_callback)

    # Atualizar hop count (simulando dispositivo conectado)
    service.get_device_info_characteristic().update_hop_count(0)

    # Simular vizinhos
    neighbors = [
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
    adv.set_local_name("IoT-Auth-Server")
    adv.include_tx_power = True
    adv.discoverable = True

    logger.info(f"   Service UUID: {service.uuid}")
    logger.info(f"   Local Name: IoT-Auth-Server")

    # Registar advertisement
    logger.info(f" A registar advertisement...")
    register_advertisement(adv, adapter_name)

    # Timer para heartbeats
    from gi.repository import GLib

    heartbeat_sequence = 0

    def send_heartbeat():
        """Envia heartbeat periódico via NetworkPacketCharacteristic."""
        nonlocal heartbeat_sequence
        heartbeat_sequence += 1

        heartbeat_packet = create_heartbeat_packet(
            sink_nid=device_nid,
            sequence=heartbeat_sequence,
        )

        # Serializar e enviar via notify
        packet_bytes = heartbeat_packet.to_bytes()
        service.get_packet_characteristic().notify_packet(packet_bytes)

        logger.info(f" Heartbeat enviado: seq={heartbeat_sequence}, size={len(packet_bytes)} bytes")
        logger.info(f"   Clientes autenticados: {len(authenticated_clients)}")

        return True  # Continuar timer

    # Agendar heartbeats a cada HEARTBEAT_INTERVAL segundos
    GLib.timeout_add_seconds(HEARTBEAT_INTERVAL, send_heartbeat)
    logger.info(f" Timer configurado: heartbeats serão enviados a cada {HEARTBEAT_INTERVAL} segundos")

    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("\n" + "=" * 60)
    logger.info("   GATT Server com Autenticação a correr!")
    logger.info("=" * 60)
    logger.info("\nDispositivo visível e disponível para conexões BLE.")
    logger.info("Clientes devem autenticar-se antes de trocar pacotes.")
    logger.info("\nPressione Ctrl+C para terminar.\n")

    logger.info(" Para testar:")
    logger.info("   1. Usar outro script Python com cliente BLE autenticado")
    logger.info("   2. Ou usar bluetoothctl para conectar e ver características")
    logger.info("")

    # Run mainloop
    try:
        mainloop.run()
    except KeyboardInterrupt:
        logger.info("\nA terminar...")

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
