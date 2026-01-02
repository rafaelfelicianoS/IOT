#!/usr/bin/env python3
"""
IoT Node - Dispositivo dual-mode da rede IoT.

O Node é responsável por:
- Descobrir o Sink (ou outro Node) via BLE scan
- Conectar ao uplink via GATT Client
- Aceitar conexões de outros Nodes via GATT Server (downlinks)
- Autenticar-se com certificados X.509
- Receber heartbeats do uplink
- Forwardar heartbeats para downlinks
- Rotear mensagens entre uplink e downlinks
- Manter session keys para comunicação segura
"""

import sys
import argparse
import signal
import time
from pathlib import Path
from typing import Optional, Dict, List
import threading

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent))

# GLib para mainloop D-Bus (GATT Server)
from gi.repository import GLib

from common.utils.logger import get_logger
from common.utils.nid import NID
from common.ble.gatt_client import BLEClient, ScannedDevice, BLEConnection
from common.ble.gatt_server import Application
from common.ble.gatt_services import IoTNetworkService
from common.ble.advertising import Advertisement
from common.security import (
    CertificateManager,
    AuthenticationHandler,
    ReplayProtection,
    calculate_hmac,
    verify_hmac,
)
from common.network.packet import Packet, MessageType
from common.protocol.heartbeat import HeartbeatPayload
from common.utils.constants import (
    IOT_NETWORK_SERVICE_UUID,
    CHAR_NETWORK_PACKET_UUID,
    CHAR_DEVICE_INFO_UUID,
    CHAR_NEIGHBOR_TABLE_UUID,
    CHAR_AUTHENTICATION_UUID,
)

logger = get_logger("iot_node")


class IoTNode:
    """
    IoT Node - Cliente BLE que conecta ao Sink.
    """

    def __init__(
        self,
        cert_path: str,
        key_path: str,
        ca_cert_path: str,
        adapter_index: int = 0,
    ):
        """
        Inicializa o IoT Node.

        Args:
            cert_path: Caminho para certificado do Node
            key_path: Caminho para chave privada do Node
            ca_cert_path: Caminho para certificado da CA
            adapter_index: Índice do adaptador BLE (0 = hci0, 1 = hci1, etc.)
        """
        self.adapter_index = adapter_index
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

        # Verificar se NÃO é certificado de Sink
        if self.cert_manager.is_sink_certificate(device_cert):
            raise ValueError("Certificado fornecido é de um Sink, não de um Node!")

        # Usar NID do certificado
        self.my_nid = extracted_nid
        logger.info(f"Node NID: {self.my_nid}")

        # Componentes de segurança
        self.auth_handler = AuthenticationHandler(self.cert_manager)
        self.replay_protection = ReplayProtection(window_size=100)

        # BLE Client (para uplink)
        self.ble_client = BLEClient(adapter_index=adapter_index)

        # Uplink (conexão ao Sink ou outro Node)
        self.uplink_connection: Optional[BLEConnection] = None
        self.uplink_nid: Optional[NID] = None
        self.uplink_device: Optional[ScannedDevice] = None

        # Session key com o uplink
        self.uplink_session_key: Optional[bytes] = None
        self.uplink_session_key_lock = threading.Lock()

        # GATT Server (para downlinks)
        self.adapter_name = f"hci{adapter_index}"
        self.bus = None
        self.app: Optional[Application] = None
        self.service: Optional[IoTNetworkService] = None
        self.advertisement: Optional[Advertisement] = None
        self.mainloop: Optional[GLib.MainLoop] = None
        self.mainloop_thread: Optional[threading.Thread] = None

        # Downlinks (outros Nodes conectados a nós)
        self.downlinks: Dict[str, NID] = {}  # address -> client_nid
        self.downlinks_lock = threading.Lock()

        # Session keys por downlink (client_nid -> session_key)
        self.downlink_session_keys: Dict[NID, bytes] = {}
        self.downlink_session_keys_lock = threading.Lock()

        # Hop count (distância ao Sink)
        self.hop_count = -1  # -1 = desconectado
        self.hop_count_lock = threading.Lock()

        # Estado
        self.authenticated = False  # Autenticado com uplink
        self.last_heartbeat_time = 0
        self.heartbeat_sequence = 0

        # Buffer para respostas de autenticação recebidas via indication
        self.auth_response_buffer: List[bytes] = []
        self.auth_response_lock = threading.Lock()

        # Reassembler para fragmentos AUTH
        from common.ble.fragmentation import FragmentReassembler
        self.auth_reassembler = FragmentReassembler()

        logger.info(f"IoT Node inicializado (adapter=hci{adapter_index})")

    def setup_gatt_server(self):
        """Configura o GATT Server para aceitar downlinks."""
        logger.info("A configurar GATT Server...")

        # Criar conexão D-Bus com GLib main loop
        import dbus
        import dbus.mainloop.glib

        # Configurar GLib main loop para D-Bus
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()

        # Criar aplicação GATT
        self.app = Application(self.bus)

        # Criar serviço IoT Network
        self.service = IoTNetworkService(
            bus=self.bus,
            path=self.app.path,
            index=0,
            device_nid=self.my_nid,
            device_type='node'
        )

        # Adicionar serviço à aplicação
        self.app.add_service(self.service)

        # Configurar callbacks do serviço
        packet_char = self.service.get_packet_characteristic()
        auth_char = self.service.get_auth_characteristic()

        packet_char.set_packet_callback(self._on_downlink_packet_received)
        auth_char.set_auth_callback(self._on_downlink_auth_message)

        # Criar advertisement
        self.advertisement = Advertisement(self.bus, 0, 'peripheral')
        self.advertisement.add_service_uuid(self.service.uuid)
        self.advertisement.set_local_name(f"IoT-Node-{str(self.my_nid)[:8]}")

        # Manufacturer data: tipo=1 (Node), hop_count (atualizado dinamicamente)
        with self.hop_count_lock:
            hop_byte = self.hop_count if self.hop_count >= 0 else 255
        manufacturer_data = bytes([1, hop_byte])  # type=1 (Node)
        self.advertisement.add_manufacturer_data(0xFFFF, manufacturer_data)

        logger.info("✅ GATT Server configurado")

    def start_gatt_server(self):
        """Inicia o GATT Server em thread separada."""
        logger.info("A iniciar GATT Server...")

        import dbus

        # Obter adaptador BLE via D-Bus
        adapter_path = f"/org/bluez/{self.adapter_name}"
        adapter_obj = self.bus.get_object('org.bluez', adapter_path)

        # Registar aplicação GATT
        gatt_manager = dbus.Interface(adapter_obj, 'org.bluez.GattManager1')
        gatt_manager.RegisterApplication(
            self.app.get_path(), {},
            reply_handler=lambda: logger.info("✅ GATT application registada!"),
            error_handler=lambda e: logger.error(f"❌ Falha ao registar GATT: {e}")
        )

        # Registar advertisement
        ad_manager = dbus.Interface(adapter_obj, 'org.bluez.LEAdvertisingManager1')
        ad_manager.RegisterAdvertisement(
            self.advertisement.get_path(), {},
            reply_handler=lambda: logger.info("✅ Advertisement registado!"),
            error_handler=lambda e: logger.error(f"❌ Falha ao registar advertisement: {e}")
        )

        # Criar e iniciar mainloop em thread separada
        self.mainloop = GLib.MainLoop()
        self.mainloop_thread = threading.Thread(target=self.mainloop.run, daemon=True)
        self.mainloop_thread.start()

        logger.info("✅ GATT Server iniciado em thread separada")

    def stop_gatt_server(self):
        """Para o GATT Server."""
        logger.info("A parar GATT Server...")

        if self.mainloop and self.mainloop.is_running():
            self.mainloop.quit()

        if self.mainloop_thread:
            self.mainloop_thread.join(timeout=2.0)

        logger.info("✅ GATT Server parado")

    def update_advertisement_hop_count(self):
        """Atualiza o hop_count no advertisement."""
        if not self.advertisement:
            return

        with self.hop_count_lock:
            hop_byte = self.hop_count if self.hop_count >= 0 else 255

        manufacturer_data = bytes([1, hop_byte])  # type=1 (Node)
        self.advertisement.add_manufacturer_data(0xFFFF, manufacturer_data)

        logger.debug(f"Advertisement atualizado: hop_count={self.hop_count}")

    def _on_downlink_packet_received(self, data: bytes):
        """
        Callback quando recebe pacote de um downlink (outro Node conectado a nós).

        Args:
            data: Dados do pacote recebido
        """
        try:
            packet = Packet.from_bytes(data)
            logger.info(f"📥 Pacote recebido de downlink: {packet.source} (type={MessageType(packet.msg_type).name})")

            # TODO: Implementar routing - se destino não somos nós, forwardar para uplink
            if packet.destination != self.my_nid:
                logger.info(f"🔀 Forwarding pacote para uplink (destino: {packet.destination})")
                # Forwardar para uplink
                return

            # Processar pacote destinado a nós
            if packet.msg_type == MessageType.DATA:
                logger.info(f"📨 Mensagem recebida de {packet.source}: {packet.payload.decode('utf-8', errors='replace')}")

        except Exception as e:
            logger.error(f"Erro ao processar pacote de downlink: {e}")

    def _on_downlink_auth_message(self, data: bytes):
        """
        Callback quando recebe mensagem de autenticação de um downlink.

        Args:
            data: Dados da mensagem de autenticação
        """
        logger.info("🔐 Mensagem de autenticação recebida de downlink")
        logger.warning("⚠️  Autenticação de downlinks não totalmente implementada - usando placeholder")
        # TODO: Implementar autenticação mutual com downlinks

    def discover_sink(self, timeout_s: int = 10) -> Optional[ScannedDevice]:
        """
        Descobre o Sink fazendo scan BLE.

        Args:
            timeout_s: Timeout para descoberta

        Returns:
            ScannedDevice do Sink ou None se não encontrado
        """
        logger.info("🔍 A procurar Sink...")

        end_time = time.time() + timeout_s
        while time.time() < end_time and self.running:
            # Scan durante 5 segundos
            devices = self.ble_client.scan_iot_devices(duration_ms=5000)

            logger.info(f"Encontrados {len(devices)} dispositivos IoT")

            # Procurar pelo Sink (manufacturer data tipo=0, hop_count=255)
            for device in devices:
                logger.debug(f"  Device: {device}")

                # Verificar manufacturer data
                if device.manufacturer_data and 0xFFFF in device.manufacturer_data:
                    data = device.manufacturer_data[0xFFFF]
                    if len(data) >= 2:
                        device_type = data[0]
                        hop_count = data[1]

                        logger.debug(f"    Type={device_type}, HopCount={hop_count}")

                        # Sink tem type=0 e hop_count=255 (representação de -1)
                        if device_type == 0 and hop_count == 255:
                            logger.info(f"✅ Sink encontrado: {device}")
                            return device

            if devices:
                logger.debug("Nenhum Sink encontrado neste scan, tentando novamente...")

        logger.warning("⚠️  Sink não encontrado após timeout")
        return None

    def connect_to_sink(self) -> bool:
        """
        Conecta ao Sink via GATT.

        Returns:
            True se conectou com sucesso
        """
        if not self.sink_device:
            logger.error("Sink device não está definido!")
            return False

        logger.info(f"A conectar ao Sink {self.sink_device.address}...")

        # Conectar
        self.uplink_connection = self.ble_client.connect_to_device(self.sink_device)

        if not self.uplink_connection:
            logger.error("❌ Falha ao conectar ao Sink")
            return False

        if not self.uplink_connection.is_connected:
            logger.error("❌ Conexão não está ativa")
            return False

        logger.info("✅ Conectado ao Sink via GATT")

        # Descobrir serviços
        success = self.uplink_connection.discover_services()
        if not success:
            logger.error("❌ Falha ao descobrir serviços")
            return False

        # Verificar se tem o serviço IoT
        if not self.uplink_connection.has_service(IOT_NETWORK_SERVICE_UUID):
            logger.error(f"❌ Sink não tem o serviço IoT ({IOT_NETWORK_SERVICE_UUID})")
            return False

        logger.info("✅ Serviço IoT Network encontrado")

        # Subscrever a notificações de pacotes (heartbeats)
        self._subscribe_to_notifications()

        return True

    def _subscribe_to_notifications(self):
        """Subscreve a notificações de características."""
        logger.info("A subscrever a notificações...")

        # Subscrever NETWORK_PACKET (para receber heartbeats)
        try:
            self.uplink_connection.subscribe(
                IOT_NETWORK_SERVICE_UUID,
                CHAR_NETWORK_PACKET_UUID,
                self._on_packet_notification
            )
            logger.info("✅ Subscrito a NETWORK_PACKET")
        except Exception as e:
            logger.error(f"Erro ao subscrever NETWORK_PACKET: {e}")

    def _on_packet_notification(self, data: bytes):
        """
        Callback quando recebe notificação de pacote (ex: heartbeat).

        Args:
            data: Dados do pacote
        """
        try:
            # Deserializar pacote
            packet = Packet.from_bytes(data)

            # Verificar tipo
            if packet.msg_type == MessageType.HEARTBEAT:
                self._handle_heartbeat(packet)
            elif packet.msg_type == MessageType.DATA:
                self._handle_data_packet(packet)
            else:
                logger.debug(f"Pacote tipo {MessageType.to_string(packet.msg_type)} recebido")

        except Exception as e:
            logger.error(f"Erro ao processar notificação: {e}", exc_info=True)

    def _handle_heartbeat(self, packet: Packet):
        """
        Processa heartbeat recebido do Sink.

        Args:
            packet: Pacote de heartbeat
        """
        try:
            # Deserializar payload
            heartbeat = HeartbeatPayload.from_bytes(packet.payload)

            # Atualizar sink_nid se ainda não temos
            if not self.uplink_nid:
                self.uplink_nid = heartbeat.sink_nid
                logger.info(f"Sink NID identificado: {self.uplink_nid}")

            # Verificar replay
            if not self.replay_protection.check_and_update(heartbeat.sink_nid, packet.sequence):
                logger.warning(f"⚠️  REPLAY ATTACK detectado em heartbeat!")
                return

            # Verificar MAC com chave padrão (heartbeats são broadcast)
            # Heartbeats usam a chave padrão, não session keys (são broadcast)
            if not packet.verify_mac():
                logger.error("❌ MAC inválido em heartbeat!")
                return

            # Verificar assinatura digital do heartbeat
            if not heartbeat.verify_signature(self.cert_manager):
                logger.error("❌ Assinatura de heartbeat inválida!")
                return

            # Atualizar timestamp
            self.last_heartbeat_time = time.time()
            self.heartbeat_sequence = packet.sequence

            age = heartbeat.age()
            logger.debug(f"💓 Heartbeat recebido (seq={packet.sequence}, age={age:.2f}s)")

        except Exception as e:
            logger.error(f"Erro ao processar heartbeat: {e}", exc_info=True)

    def _handle_data_packet(self, packet: Packet):
        """
        Processa pacote DATA recebido.

        Args:
            packet: Pacote recebido
        """
        logger.info(
            f"📨 DATA recebido: {packet.source} → {packet.destination} "
            f"({len(packet.payload)} bytes)"
        )

        # Verificar se é para nós
        if packet.destination != self.my_nid:
            logger.debug(f"Pacote não é para este node (dest={packet.destination})")
            return

        # Verificar replay
        if not self.replay_protection.check_and_update(packet.source, packet.sequence):
            logger.warning(f"⚠️  REPLAY ATTACK detectado!")
            return

        # Verificar MAC
        with self.uplink_session_key_lock:
            if self.uplink_session_key:
                if not self._verify_packet_mac(packet, self.uplink_session_key):
                    logger.error("❌ MAC inválido!")
                    return

        # Processar payload
        logger.info(f"✅ Mensagem recebida: {packet.payload!r}")

    def _on_auth_indication(self, data: bytes):
        """
        Callback para receber indicações de autenticação do Sink.

        Args:
            data: Dados recebidos via indication (pode ser fragmentado)
        """
        logger.debug(f"🔐 AUTH indication recebida: {len(data)} bytes")

        # Defragmentar mensagem
        is_complete, auth_data = self.auth_reassembler.add_fragment(data)

        if is_complete:
            logger.debug(f"🔐 AUTH mensagem completa: {len(auth_data)} bytes")
            with self.auth_response_lock:
                self.auth_response_buffer.append(auth_data)
        else:
            logger.debug(f"🔐 Aguardando mais fragmentos AUTH...")

    def authenticate_with_sink(self) -> bool:
        """
        Realiza autenticação mútua com o Sink.

        Returns:
            True se autenticação bem-sucedida
        """
        logger.info("🔐 A iniciar autenticação com Sink...")

        if not self.uplink_connection or not self.uplink_connection.is_connected:
            logger.error("Não conectado ao Sink")
            return False

        try:
            # Limpar buffer de respostas de autenticações anteriores
            with self.auth_response_lock:
                self.auth_response_buffer.clear()

            # Subscrever a AUTH characteristic para receber indicações
            logger.debug("📡 A subscrever a AUTH characteristic...")
            success = self.uplink_connection.subscribe(
                IOT_NETWORK_SERVICE_UUID,
                CHAR_AUTHENTICATION_UUID,
                self._on_auth_indication
            )

            if not success:
                logger.error("❌ Falha ao subscrever AUTH characteristic")
                return False

            logger.debug("✅ Subscrito a AUTH indications")

            # Criar protocolo de autenticação
            from common.security.authentication import AuthenticationProtocol

            auth_protocol = AuthenticationProtocol(self.cert_manager)

            # 1. Iniciar autenticação enviando nosso certificado
            logger.info("📤 Enviando certificado...")
            initial_msg = auth_protocol.start_authentication()

            # Enviar via AUTH characteristic com fragmentação se necessário
            self._send_auth_message(initial_msg)

            # 2. Esperar resposta do Sink e processar protocolo
            max_rounds = 10  # Máximo de trocas de mensagens
            for round_num in range(max_rounds):
                logger.debug(f"Autenticação round {round_num + 1}/{max_rounds}")

                # Esperar resposta (timeout 5s)
                time.sleep(0.5)

                # Ler resposta do Sink via AUTH characteristic
                response = self._read_auth_response()

                if not response:
                    logger.debug("Sem resposta ainda, continuando...")
                    continue

                # Processar mensagem recebida
                continue_auth, reply = auth_protocol.process_message(response)

                if reply:
                    # Enviar resposta
                    logger.debug(f"📤 Enviando resposta ({len(reply)} bytes)")
                    self._send_auth_message(reply)

                if not continue_auth:
                    # Autenticação completou
                    if auth_protocol.state.name == 'AUTHENTICATED':
                        logger.info("✅ Autenticação bem-sucedida!")

                        # Obter session key
                        session_key = auth_protocol.derive_session_key()
                        if session_key:
                            with self.uplink_session_key_lock:
                                self.uplink_session_key = session_key
                            logger.info("🔑 Session key estabelecida")

                        # Obter NID do Sink
                        self.uplink_nid = auth_protocol.peer_nid

                        # Armazenar certificado do Sink para verificação de assinaturas
                        if auth_protocol.peer_cert:
                            self.cert_manager._sink_cert = auth_protocol.peer_cert
                            logger.debug("✅ Certificado do Sink armazenado")

                        self.authenticated = True
                        return True
                    else:
                        logger.error(f"❌ Autenticação falhou: {auth_protocol.state.name}")
                        return False

            logger.error("❌ Autenticação expirou (timeout)")
            return False

        except Exception as e:
            logger.error(f"❌ Erro durante autenticação: {e}", exc_info=True)
            return False

    def _send_auth_message(self, data: bytes):
        """
        Envia mensagem de autenticação via AUTH characteristic.

        Usa fragmentação se necessário.

        Args:
            data: Dados a enviar
        """
        from common.ble.fragmentation import fragment_message

        # Fragmentar se necessário
        fragments = fragment_message(data)

        logger.debug(f"Enviando mensagem auth: {len(data)} bytes em {len(fragments)} fragmento(s)")

        for i, fragment in enumerate(fragments):
            self.uplink_connection.write(
                IOT_NETWORK_SERVICE_UUID,
                CHAR_AUTHENTICATION_UUID,
                fragment
            )
            logger.debug(f"  Fragmento {i+1}/{len(fragments)} enviado")

            # Pequeno delay entre fragmentos
            if len(fragments) > 1:
                time.sleep(0.1)

    def _read_auth_response(self) -> Optional[bytes]:
        """
        Lê resposta de autenticação do buffer (recebida via indication).

        Returns:
            Dados recebidos ou None
        """
        with self.auth_response_lock:
            if self.auth_response_buffer:
                # Pegar e remover primeira resposta do buffer
                data = self.auth_response_buffer.pop(0)
                logger.debug(f"Resposta auth lida do buffer: {len(data)} bytes")
                return data

        return None

    def send_message(self, message: bytes, destination: Optional[NID] = None) -> bool:
        """
        Envia uma mensagem através do Sink.

        Args:
            message: Mensagem a enviar
            destination: NID de destino (None = Sink)

        Returns:
            True se enviou com sucesso
        """
        if not self.uplink_connection or not self.uplink_connection.is_connected:
            logger.error("Não conectado ao Sink")
            return False

        if destination is None:
            destination = self.uplink_nid

        # Criar pacote
        packet = Packet.create(
            source=self.my_nid,
            destination=destination,
            msg_type=MessageType.DATA,
            payload=message,
        )

        # Calcular MAC se temos session key
        with self.uplink_session_key_lock:
            if self.uplink_session_key:
                # Construir dados para MAC
                mac_data = (
                    packet.source.to_bytes() +
                    packet.destination.to_bytes() +
                    bytes([packet.msg_type, packet.ttl]) +
                    packet.sequence.to_bytes(4, 'big') +
                    packet.payload
                )
                packet.mac = calculate_hmac(mac_data, self.uplink_session_key)
            else:
                packet.calculate_and_set_mac()

        # Enviar via NETWORK_PACKET characteristic
        try:
            self.uplink_connection.write(
                IOT_NETWORK_SERVICE_UUID,
                CHAR_NETWORK_PACKET_UUID,
                packet.to_bytes()
            )
            logger.info(f"✅ Mensagem enviada para {destination}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            return False

    def _verify_packet_mac(self, packet: Packet, session_key: bytes) -> bool:
        """
        Verifica o MAC de um pacote.

        Args:
            packet: Pacote a verificar
            session_key: Session key

        Returns:
            True se MAC válido
        """
        # Construir dados para verificação MAC
        mac_data = (
            packet.source.to_bytes() +
            packet.destination.to_bytes() +
            bytes([packet.msg_type, packet.ttl]) +
            packet.sequence.to_bytes(4, 'big') +
            packet.payload
        )

        # Verificar MAC
        return verify_hmac(mac_data, packet.mac, session_key)

    def _update_hop_count_from_uplink(self):
        """Atualiza o hop_count baseado no uplink conectado."""
        try:
            # Ler DeviceInfo do uplink para obter seu hop_count
            device_info_data = self.uplink_connection.read(
                IOT_NETWORK_SERVICE_UUID,
                CHAR_DEVICE_INFO_UUID
            )

            if not device_info_data or len(device_info_data) < 18:
                logger.warning("⚠️  Não conseguiu ler DeviceInfo do uplink")
                with self.hop_count_lock:
                    self.hop_count = 0  # Assumir conexão direta ao Sink
                return

            # Parsear DeviceInfo: 16 bytes NID + 1 byte hop_count + 1 byte device_type
            uplink_hop = device_info_data[16]  # hop_count do uplink

            # Se uplink é Sink (hop=255/-1), nosso hop = 0
            # Senão, nosso hop = uplink_hop + 1
            if uplink_hop == 255:
                new_hop = 0
                logger.info(f"✅ Conectado ao Sink - hop_count=0")
            else:
                new_hop = uplink_hop + 1
                logger.info(f"✅ Conectado a Node (hop={uplink_hop}) - nosso hop_count={new_hop}")

            with self.hop_count_lock:
                self.hop_count = new_hop

        except Exception as e:
            logger.error(f"Erro ao atualizar hop_count: {e}")
            with self.hop_count_lock:
                self.hop_count = 0  # Default: assumir hop 0

    def run(self):
        """Loop principal do Node."""
        logger.info("=" * 60)
        logger.info("  A iniciar IoT Node (dual-mode)")
        logger.info("=" * 60)

        self.running = True

        try:
            # 0. Configurar e iniciar GATT Server (para aceitar downlinks)
            self.setup_gatt_server()
            self.start_gatt_server()
            logger.info("✅ GATT Server ativo - aguardando downlinks")

            # 1. Descobrir uplink (Sink ou outro Node)
            self.sink_device = self.discover_sink(timeout_s=30)
            if not self.sink_device:
                logger.error("❌ Falha ao descobrir uplink")
                # Continuar mesmo sem uplink - podemos receber downlinks
                logger.warning("⚠️  Sem uplink - operando apenas como server")

                # Loop apenas como server
                while self.running:
                    time.sleep(1)
                return

            # 2. Conectar ao uplink
            if not self.connect_to_sink():
                logger.error("❌ Falha ao conectar ao uplink")
                return

            # 3. Atualizar hop_count baseado no uplink
            self._update_hop_count_from_uplink()

            # 4. Atualizar advertisement com novo hop_count
            self.update_advertisement_hop_count()

            # 5. Autenticar
            if not self.authenticate_with_sink():
                logger.error("❌ Falha na autenticação")
                return

            logger.info("=" * 60)
            logger.info(f"✅ Node pronto! Uplink conectado (hop={self.hop_count})")
            logger.info("=" * 60)

            # Loop principal - monitorizar conexão
            while self.running:
                time.sleep(1)

                # Verificar se ainda está conectado
                if not self.uplink_connection.is_connected:
                    logger.warning("⚠️  Conexão perdida com Sink")
                    break

                # Verificar se recebemos heartbeat recentemente (último 10s)
                if self.last_heartbeat_time > 0:
                    time_since_heartbeat = time.time() - self.last_heartbeat_time
                    if time_since_heartbeat > 10:
                        logger.warning(
                            f"⚠️  Sem heartbeat há {time_since_heartbeat:.1f}s "
                            f"(último seq={self.heartbeat_sequence})"
                        )

        except KeyboardInterrupt:
            logger.info("\n⚠️  Keyboard interrupt recebido")
        finally:
            self.stop()

    def stop(self):
        """Para o Node."""
        logger.info("A parar Node...")
        self.running = False

        # Parar GATT Server
        self.stop_gatt_server()

        # Desconectar do uplink
        if self.uplink_connection:
            self.uplink_connection.disconnect()

        # Desconectar todos os clients
        self.ble_client.disconnect_all()

        logger.info("✅ Node parado")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="IoT Node - BLE Client Device")
    parser.add_argument(
        '--cert',
        required=True,
        help='Caminho para o certificado do Node'
    )
    parser.add_argument(
        '--key',
        required=True,
        help='Caminho para a chave privada do Node'
    )
    parser.add_argument(
        '--ca-cert',
        required=True,
        help='Caminho para o certificado da CA'
    )
    parser.add_argument(
        '--adapter',
        type=int,
        default=0,
        help='Índice do adaptador BLE (default: 0 = hci0)'
    )

    args = parser.parse_args()

    # Criar Node
    try:
        node = IoTNode(
            cert_path=args.cert,
            key_path=args.key,
            ca_cert_path=args.ca_cert,
            adapter_index=args.adapter,
        )

        # Signal handlers
        def signal_handler(signum, frame):
            logger.info(f"\nSinal {signum} recebido, a parar...")
            node.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Executar
        node.run()

    except Exception as e:
        logger.error(f"Erro ao iniciar IoT Node: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
