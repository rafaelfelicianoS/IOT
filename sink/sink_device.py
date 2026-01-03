#!/usr/bin/env python3
"""
Sink Device - Gateway central da rede IoT.

O Sink é responsável por:
- Aceitar conexões de IoT Nodes via BLE (GATT Server)
- Enviar heartbeats assinados a cada 5 segundos
- Autenticar nodes com certificados X.509
- Validar MACs e prevenir replay attacks
- Receber mensagens via Inbox service
"""

import sys
import argparse
import signal
from pathlib import Path
from typing import Optional, Dict, List
import threading
import time

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# GLib para mainloop D-Bus
from gi.repository import GLib

from common.utils.logger import get_logger
from common.utils.nid import NID
from common.ble.gatt_server import Application
from common.ble.gatt_services import (
    IoTNetworkService,
    NetworkPacketCharacteristic,
    DeviceInfoCharacteristic,
    NeighborTableCharacteristic,
    AuthCharacteristic,
)
from common.ble.advertising import Advertisement
from common.security import (
    CertificateManager,
    AuthenticationHandler,
    ReplayProtection,
    DTLSManager,
    calculate_hmac,
    verify_hmac,
)
from common.network.packet import Packet, MessageType
from common.protocol.heartbeat import create_heartbeat_packet

logger = get_logger("sink_device")


class SinkDevice:
    """
    Sink Device - Gateway central da rede IoT.

    Funcionalidades:
    - GATT Server para aceitar conexões de nodes
    - Heartbeat broadcasting (5s intervals)
    - Autenticação X.509 de nodes
    - Validação de MACs e replay protection
    - Inbox service (TODO)
    """

    def __init__(
        self,
        adapter: str,
        cert_path: Path,
        key_path: Path,
        ca_cert_path: Path,
        my_nid: Optional[NID] = None,
    ):
        """
        Inicializa o Sink Device.

        Args:
            adapter: Adaptador BLE (ex: 'hci0')
            cert_path: Caminho para certificado do Sink
            key_path: Caminho para chave privada do Sink
            ca_cert_path: Caminho para certificado da CA
            my_nid: NID do Sink (se None, extrai do certificado)
        """
        self.adapter = adapter
        self.running = False

        # Carregar certificados manualmente
        logger.info("A carregar certificados...")

        from cryptography import x509
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.backends import default_backend

        # Carregar certificado do dispositivo
        with open(cert_path, 'rb') as f:
            device_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        # Carregar chave privada do dispositivo
        with open(key_path, 'rb') as f:
            device_key = serialization.load_pem_private_key(
                f.read(), password=None, backend=default_backend()
            )

        # Carregar certificado da CA
        with open(ca_cert_path, 'rb') as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), default_backend())

        # Extrair NID do certificado
        from common.security.certificate_manager import CertificateManager as CM
        extracted_nid = CM.extract_nid_from_cert(CM, device_cert)

        # Criar CertificateManager com NID extraído
        self.cert_manager = CertificateManager(device_nid=extracted_nid)
        self.cert_manager.device_cert = device_cert
        self.cert_manager.device_private_key = device_key
        self.cert_manager.ca_cert = ca_cert

        logger.info("✅ Certificados carregados com sucesso")

        # Verificar se é certificado de Sink
        if not self.cert_manager.is_sink_certificate(device_cert):
            raise ValueError("Certificado fornecido não é de um Sink (OU != 'Sink')")

        # Usar NID do certificado
        self.my_nid = extracted_nid
        logger.info(f"Sink NID: {self.my_nid}")

        # Componentes de segurança
        self.auth_handler = AuthenticationHandler(self.cert_manager)
        self.replay_protection = ReplayProtection(window_size=100)
        self.dtls_manager = DTLSManager(
            cert_path=cert_path,
            key_path=key_path,
            ca_cert_path=ca_cert_path
        )

        # Downlinks conectados (address -> client_nid)
        self.downlinks: Dict[str, NID] = {}
        self.downlinks_lock = threading.Lock()

        # Session keys por link (client_nid -> session_key)
        self.session_keys: Dict[NID, bytes] = {}
        self.session_keys_lock = threading.Lock()

        # Inbox: mensagens recebidas dos Nodes
        # Estrutura: List[Dict] com {timestamp, source_nid, message, client_address}
        self.inbox: List[Dict] = []
        self.inbox_lock = threading.Lock()

        # Heartbeat blocking: NIDs de nodes que não devem receber heartbeats
        # Usado para simular link failures
        self.heartbeat_blocked_nodes: set = set()
        self.heartbeat_blocked_lock = threading.Lock()

        # GATT Application
        self.app = None
        self.advertisement = None
        self.mainloop = None

        # Heartbeat
        self.heartbeat_sequence = 0
        self.heartbeat_timer = None

        logger.info(f"Sink Device inicializado (adapter={adapter})")

    def setup_gatt_server(self):
        """Configura o GATT Server."""
        logger.info("A configurar GATT Server...")

        # Criar conexão D-Bus com GLib main loop
        import dbus
        import dbus.mainloop.glib

        # Configurar GLib main loop para D-Bus
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        self.bus = dbus.SystemBus()

        # Criar aplicação GATT
        self.app = Application(self.bus)

        # Criar serviço IoT Network (cria todas as características automaticamente)
        service = IoTNetworkService(
            bus=self.bus,
            path=self.app.path,
            index=0,
            device_nid=self.my_nid,
            device_type='sink'
        )

        # Guardar referência ao service
        self.service = service

        # Obter referências às características
        self.packet_char = service.get_packet_characteristic()
        self.neighbor_char = service.get_neighbor_characteristic()
        self.auth_char = service.get_auth_characteristic()

        # Configurar callbacks
        self.packet_char.set_packet_callback(self._on_packet_received)
        self.auth_char.set_auth_callback(self._on_auth_message)

        # Adicionar serviço
        self.app.add_service(service)

        logger.info("✅ GATT Server configurado")

    def setup_advertising(self):
        """Configura BLE Advertising."""
        logger.info("A configurar BLE Advertising...")

        # Criar advertisement
        self.advertisement = Advertisement(self.bus, 0, 'peripheral')  # bus, index, type
        self.advertisement.add_service_uuid(self.service.uuid)
        self.advertisement.set_local_name(f"IoT-Sink-{str(self.my_nid)[:8]}")

        # Manufacturer data: tipo=0 (Sink), hop_count=255 (-1 em unsigned)
        manufacturer_data = bytes([0, 255])
        self.advertisement.add_manufacturer_data(0xFFFF, manufacturer_data)

        logger.info("✅ BLE Advertising configurado")

    def _on_packet_received(self, data: bytes, client_address: Optional[str] = None):
        """
        Callback quando recebe um pacote via NETWORK_PACKET characteristic.

        Args:
            data: Dados do pacote (bytes)
            client_address: Endereço BLE do cliente (se disponível)
        """
        try:
            # Deserializar pacote
            packet = Packet.from_bytes(data)

            logger.info(
                f"📦 Pacote recebido de {client_address or 'unknown'}: "
                f"{packet.source} → {packet.destination} "
                f"(type={MessageType.to_string(packet.msg_type)}, seq={packet.sequence})"
            )

            # 1. Verificar replay attack
            if not self.replay_protection.check_and_update(packet.source, packet.sequence):
                logger.warning(
                    f"⚠️  REPLAY ATTACK detectado! "
                    f"Source={packet.source}, seq={packet.sequence}"
                )
                return

            # 2. Verificar MAC
            session_key = self._get_session_key(packet.source)
            if session_key:
                if not self._verify_packet_mac(packet, session_key):
                    logger.error(f"❌ MAC inválido! Pacote rejeitado.")
                    return
            else:
                logger.warning(
                    f"⚠️  Sem session key para {packet.source} - "
                    f"autenticação pendente?"
                )
                # Aceitar pacotes sem MAC verificado se não temos session key
                # (pode ser mensagem de autenticação)

            # 3. Processar pacote baseado no tipo
            if packet.msg_type == MessageType.DATA:
                self._handle_data_packet(packet, client_address)
            elif packet.msg_type == MessageType.AUTH_REQUEST:
                logger.debug("AUTH_REQUEST recebido via pacote (usar AuthCharacteristic)")
            else:
                logger.warning(f"Tipo de pacote desconhecido: {packet.msg_type}")

        except Exception as e:
            logger.error(f"Erro ao processar pacote: {e}", exc_info=True)

    def _on_auth_message(self, data: bytes, client_address: Optional[str] = None):
        """
        Callback quando recebe mensagem de autenticação via AUTH characteristic.

        Args:
            data: Mensagem de autenticação (bytes)
            client_address: Endereço BLE do cliente
        """
        logger.info(f"🔐 Mensagem de autenticação recebida de {client_address}: {len(data)} bytes")

        try:
            # Processar autenticação (usa AuthenticationHandler)
            response = self.auth_handler.handle_auth_message(data, client_address)

            # Verificar se autenticação completou
            if self.auth_handler.is_authenticated(client_address):
                logger.info(f"✅ Cliente {client_address} autenticado com sucesso!")

                # Obter session key
                peer_info = self.auth_handler.get_peer_info(client_address)

                if peer_info and 'session_key' in peer_info:
                    session_key = peer_info['session_key']
                    client_nid = peer_info['nid']

                    # Guardar session key
                    self._store_session_key(client_nid, session_key)

                    # Adicionar a lista de downlinks
                    with self.downlinks_lock:
                        self.downlinks[client_address] = client_nid

                    logger.info(f"🔑 Session key armazenada para {client_nid}")

                    # Estabelecer canal DTLS end-to-end
                    dtls_channel = self.dtls_manager.create_channel(client_nid)
                    if dtls_channel.establish():
                        logger.info(f"🔐 Canal DTLS estabelecido com {str(client_nid)[:8]}...")

                        # Derivar chave de encriptação a partir da session key
                        dtls_channel.derive_encryption_key(session_key)
                        logger.info(f"🔑 Chave de encriptação end-to-end derivada para {str(client_nid)[:8]}...")

            # Retornar resposta (fragmentação/envio é feito pela AuthCharacteristic)
            return response if response else b''

        except Exception as e:
            logger.error(f"Erro ao processar autenticação: {e}", exc_info=True)
            return b''

    def _handle_data_packet(self, packet: Packet, client_address: Optional[str]):
        """
        Processa pacote DATA recebido.

        Args:
            packet: Pacote recebido
            client_address: Endereço do cliente
        """
        logger.info(
            f"📨 DATA recebido: {packet.source} → {packet.destination} "
            f"({len(packet.payload)} bytes)"
        )

        # Se destino é o Sink, processar localmente
        if packet.destination == self.my_nid:
            # DTLS End-to-End: Desencriptar payload
            decrypted_payload = packet.payload
            dtls_channel = self.dtls_manager.get_channel(packet.source)
            if dtls_channel and dtls_channel.established and dtls_channel.aesgcm:
                decrypted_payload = dtls_channel.unwrap(packet.payload)
                if decrypted_payload is None:
                    logger.error("❌ Falha ao desencriptar payload end-to-end - descartando pacote")
                    return
                logger.info(f"🔓 Payload desencriptado end-to-end: {len(packet.payload)} → {len(decrypted_payload)} bytes")

            logger.info(f"✅ Pacote destinado ao Sink - payload: {decrypted_payload!r}")

            # Inbox Service: armazenar mensagem recebida
            try:
                # Decodificar mensagem
                message = decrypted_payload.decode('utf-8', errors='replace')

                # Preparar entrada do inbox
                inbox_entry = {
                    'timestamp': time.time(),
                    'source_nid': packet.source.to_bytes().hex()[:16] + '...',  # Primeiros 8 bytes
                    'message': message,
                    'client_address': client_address,
                    'sequence': packet.sequence
                }

                # Adicionar ao inbox com lock
                with self.inbox_lock:
                    self.inbox.append(inbox_entry)

                    # Limitar tamanho do inbox (máximo 100 mensagens)
                    if len(self.inbox) > 100:
                        self.inbox.pop(0)  # Remover mensagem mais antiga

                logger.info(f"📥 Mensagem armazenada no inbox: '{message}' (de {inbox_entry['source_nid']})")
            except Exception as e:
                logger.error(f"Erro ao armazenar mensagem no inbox: {e}", exc_info=True)
        else:
            # Forward para outro node (se tivermos rota)
            logger.warning(
                f"⚠️  Pacote destinado a {packet.destination} mas Sink não faz forward "
                f"(nodes devem enviar diretamente ao destino ou via uplink)"
            )

    def _verify_packet_mac(self, packet: Packet, session_key: bytes) -> bool:
        """
        Verifica o MAC de um pacote.

        Args:
            packet: Pacote a verificar
            session_key: Session key do link

        Returns:
            True se MAC válido
        """
        # Construir dados para verificação MAC
        # MAC cobre: source + dest + type + ttl + sequence + payload
        mac_data = (
            packet.source.to_bytes() +
            packet.destination.to_bytes() +
            bytes([packet.msg_type, packet.ttl]) +
            packet.sequence.to_bytes(4, 'big') +
            packet.payload
        )

        # Verificar MAC
        return verify_hmac(mac_data, packet.mac, session_key)

    def _get_session_key(self, nid: NID) -> Optional[bytes]:
        """Obtém session key para um NID."""
        with self.session_keys_lock:
            return self.session_keys.get(nid)

    def _store_session_key(self, nid: NID, session_key: bytes):
        """Armazena session key para um NID."""
        with self.session_keys_lock:
            self.session_keys[nid] = session_key

    def block_heartbeat(self, nid: NID):
        """
        Bloqueia envio de heartbeats para um node específico.
        Usado para simular link failures.

        Args:
            nid: NID do node a bloquear
        """
        with self.heartbeat_blocked_lock:
            self.heartbeat_blocked_nodes.add(nid)
        logger.info(f"🚫 Heartbeats bloqueados para {nid}")

    def unblock_heartbeat(self, nid: NID):
        """
        Desbloqueia envio de heartbeats para um node.

        Args:
            nid: NID do node a desbloquear
        """
        with self.heartbeat_blocked_lock:
            self.heartbeat_blocked_nodes.discard(nid)
        logger.info(f"✅ Heartbeats desbloqueados para {nid}")

    def get_blocked_heartbeat_nodes(self) -> set:
        """Retorna lista de nodes com heartbeat bloqueado."""
        with self.heartbeat_blocked_lock:
            return self.heartbeat_blocked_nodes.copy()

    def start_heartbeat_service(self):
        """Inicia o serviço de heartbeat (5s intervals)."""
        logger.info("💓 A iniciar serviço de heartbeat...")

        def send_heartbeat():
            """Envia heartbeat assinado."""
            if not self.running:
                return False  # Para o timer

            try:
                # Incrementar sequence
                self.heartbeat_sequence += 1

                # Criar pacote de heartbeat com assinatura
                heartbeat_packet = create_heartbeat_packet(
                    sink_nid=self.my_nid,
                    cert_manager=self.cert_manager,
                    sequence=self.heartbeat_sequence,
                )

                # Determinar clientes a excluir (NIDs bloqueados -> endereços)
                exclude_clients = set()
                with self.heartbeat_blocked_lock:
                    if self.heartbeat_blocked_nodes:
                        # Converter NIDs bloqueados em endereços de clientes
                        with self.downlinks_lock:
                            for client_addr, client_nid in self.downlinks.items():
                                if client_nid in self.heartbeat_blocked_nodes:
                                    exclude_clients.add(client_addr)

                # Enviar via notificação NETWORK_PACKET (excluindo clientes bloqueados)
                self.packet_char.notify_packet(heartbeat_packet.to_bytes(), exclude_clients=exclude_clients)

                if exclude_clients:
                    logger.debug(f"💓 Heartbeat enviado (seq={self.heartbeat_sequence}, {len(exclude_clients)} bloqueados)")
                else:
                    logger.debug(f"💓 Heartbeat enviado (seq={self.heartbeat_sequence})")

            except Exception as e:
                logger.error(f"Erro ao enviar heartbeat: {e}", exc_info=True)

            # Reagendar (retorna True para continuar)
            return True

        # Timer inicial (5s depois)
        self.heartbeat_timer = GLib.timeout_add_seconds(5, send_heartbeat)
        logger.info("✅ Serviço de heartbeat iniciado")

    def start(self):
        """Inicia o Sink Device."""
        logger.info("=" * 60)
        logger.info("  A iniciar Sink Device")
        logger.info("=" * 60)

        # Setup GATT Server
        self.setup_gatt_server()

        # Registar GATT application com BlueZ
        import dbus
        logger.info(f"A registar GATT application no adaptador {self.adapter}...")
        adapter_path = f"/org/bluez/{self.adapter}"
        adapter_obj = self.bus.get_object('org.bluez', adapter_path)
        gatt_manager = dbus.Interface(adapter_obj, 'org.bluez.GattManager1')

        gatt_manager.RegisterApplication(
            self.app.get_path(),
            {},
            reply_handler=lambda: logger.info("✅ GATT application registada!"),
            error_handler=lambda e: logger.error(f"❌ Falha ao registar: {e}")
        )

        # Setup Advertising
        self.setup_advertising()

        # Registar advertisement com BlueZ
        logger.info(f"A registar advertisement no adaptador {self.adapter}...")
        ad_manager = dbus.Interface(adapter_obj, 'org.bluez.LEAdvertisingManager1')

        ad_manager.RegisterAdvertisement(
            self.advertisement.get_path(),
            {},
            reply_handler=lambda: logger.info("✅ Advertisement registado!"),
            error_handler=lambda e: logger.error(f"❌ Falha ao registar advertisement: {e}")
        )

        # Iniciar heartbeat service
        self.start_heartbeat_service()

        # Marcar como running
        self.running = True

        # GLib mainloop
        logger.info("✅ Sink Device iniciado - a aguardar conexões...")
        self.mainloop = GLib.MainLoop()

        try:
            self.mainloop.run()
        except KeyboardInterrupt:
            logger.info("\n⚠️  Keyboard interrupt recebido")
        finally:
            self.stop()

    def stop(self):
        """Para o Sink Device."""
        logger.info("A parar Sink Device...")
        self.running = False

        # Parar heartbeat timer
        if self.heartbeat_timer:
            GLib.source_remove(self.heartbeat_timer)
            self.heartbeat_timer = None

        # Parar mainloop
        if self.mainloop and self.mainloop.is_running():
            self.mainloop.quit()

        logger.info("✅ Sink Device parado")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Sink Device - IoT Network Gateway")
    parser.add_argument(
        'adapter',
        help="BLE adapter (ex: hci0)"
    )
    parser.add_argument(
        '--cert',
        type=Path,
        required=True,
        help="Caminho para certificado do Sink (.pem)"
    )
    parser.add_argument(
        '--key',
        type=Path,
        required=True,
        help="Caminho para chave privada do Sink (.pem)"
    )
    parser.add_argument(
        '--ca-cert',
        type=Path,
        required=True,
        help="Caminho para certificado da CA (.pem)"
    )
    parser.add_argument(
        '--nid',
        type=str,
        help="NID do Sink (UUID). Se omitido, extrai do certificado"
    )

    args = parser.parse_args()

    # Validar paths
    if not args.cert.exists():
        logger.error(f"Certificado não encontrado: {args.cert}")
        return 1

    if not args.key.exists():
        logger.error(f"Chave privada não encontrada: {args.key}")
        return 1

    if not args.ca_cert.exists():
        logger.error(f"Certificado CA não encontrado: {args.ca_cert}")
        return 1

    # Parse NID (se fornecido)
    my_nid = None
    if args.nid:
        try:
            my_nid = NID(args.nid)
        except Exception as e:
            logger.error(f"NID inválido: {e}")
            return 1

    # Criar Sink Device
    try:
        sink = SinkDevice(
            adapter=args.adapter,
            cert_path=args.cert,
            key_path=args.key,
            ca_cert_path=args.ca_cert,
            my_nid=my_nid,
        )

        # Signal handlers
        def signal_handler(sig, frame):
            logger.info(f"\nSinal {sig} recebido, a parar...")
            sink.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Iniciar
        sink.start()

        return 0

    except Exception as e:
        logger.error(f"Erro ao iniciar Sink Device: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
