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

sys.path.insert(0, str(Path(__file__).parent.parent))

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
    DTLSChannel,
    calculate_hmac,
    verify_hmac,
)
from common.network.packet import Packet, MessageType
from common.network.router_daemon import RouterDaemon
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
        peripheral_only: bool = False,
    ):
        """
        Inicializa o IoT Node.

        Args:
            cert_path: Caminho para certificado do Node
            key_path: Caminho para chave privada do Node
            ca_cert_path: Caminho para certificado da CA
            adapter_index: Índice do adaptador BLE (0 = hci0, 1 = hci1, etc.)
            peripheral_only: Se True, não procura uplink (apenas aceita conexões downlink)
        """
        self.adapter_index = adapter_index
        self.peripheral_only = peripheral_only
        self.running = False

        # Armazenar paths dos certificados (necessário para DTLS)
        from pathlib import Path as PathLib
        self.cert_path = PathLib(cert_path) if isinstance(cert_path, str) else cert_path
        self.key_path = PathLib(key_path) if isinstance(key_path, str) else key_path
        self.ca_cert_path = PathLib(ca_cert_path) if isinstance(ca_cert_path, str) else ca_cert_path

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

        self.cert_manager = CertificateManager(device_nid=extracted_nid)
        self.cert_manager.device_cert = device_cert
        self.cert_manager.device_private_key = device_key
        self.cert_manager.ca_cert = ca_cert

        logger.info(" Certificados carregados com sucesso")

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

        # Canal DTLS end-to-end com o Sink
        self.dtls_channel: Optional[DTLSChannel] = None

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
        self.data_packet_sequence = 0  # Contador de sequence para pacotes DATA
        self.data_packet_sequence_lock = threading.Lock()

        # Buffer para respostas de autenticação recebidas via indication
        self.auth_response_buffer: List[bytes] = []
        self.auth_response_lock = threading.Lock()

        # Reassembler para fragmentos AUTH
        from common.ble.fragmentation import FragmentReassembler
        self.auth_reassembler = FragmentReassembler()

        # Router Daemon (Secção 5.7 - serviço de routing separado)
        self.router = RouterDaemon(my_nid=self.my_nid)
        self.router.set_send_callback(self._router_send_callback)

        # Registar handlers locais no router
        self.router.register_local_handler(MessageType.DATA, self._handle_data_packet_local)
        self.router.register_local_handler(MessageType.HEARTBEAT, self._handle_heartbeat_packet_local)

        # Contador de mensagens roteadas via uplink (para UI - Secção 6)
        self.uplink_messages_sent = 0
        self.uplink_messages_lock = threading.Lock()

        logger.info(f"IoT Node inicializado (adapter=hci{adapter_index})")
        logger.info(" Router Daemon integrado")

    def setup_gatt_server(self):
        """Configura o GATT Server para aceitar downlinks."""
        logger.info("A configurar GATT Server...")

        import dbus
        import dbus.mainloop.glib

        # Configurar GLib main loop para D-Bus
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SystemBus()

        self.app = Application(self.bus)

        self.service = IoTNetworkService(
            bus=self.bus,
            path=self.app.path,
            index=0,
            device_nid=self.my_nid,
            device_type='node'
        )

        self.app.add_service(self.service)

        # Configurar callbacks do serviço
        packet_char = self.service.get_packet_characteristic()
        auth_char = self.service.get_auth_characteristic()

        packet_char.set_packet_callback(self._on_downlink_packet_received)
        auth_char.set_auth_callback(self._on_downlink_auth_message)

        self.advertisement = Advertisement(self.bus, 0, 'peripheral')
        self.advertisement.add_service_uuid(self.service.uuid)
        self.advertisement.set_local_name(f"IoT-Node-{str(self.my_nid)[:8]}")

        # Manufacturer data: tipo=1 (Node), hop_count (atualizado dinamicamente)
        with self.hop_count_lock:
            hop_byte = self.hop_count if self.hop_count >= 0 else 255
        manufacturer_data = bytes([1, hop_byte])  # type=1 (Node)
        self.advertisement.add_manufacturer_data(0xFFFF, manufacturer_data)

        # IMPORTANTE: Configurar advertising contínuo para suportar múltiplas conexões
        # Duration=0 significa que o advertising NÃO para quando aceita conexões
        # Isto permite que múltiplos Nodes descubram e conectem a este Node simultaneamente
        self.advertisement.duration = 0  # Advertising contínuo (não para com conexões)
        logger.info(" Advertising contínuo configurado (duration=0)")

        logger.info(" GATT Server configurado")

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
            reply_handler=lambda: logger.info(" GATT application registada!"),
            error_handler=lambda e: logger.error(f" Falha ao registar GATT: {e}")
        )

        # Registar advertisement
        ad_manager = dbus.Interface(adapter_obj, 'org.bluez.LEAdvertisingManager1')

        # Tentar desregistar primeiro (caso exista de execução anterior)
        try:
            ad_manager.UnregisterAdvertisement(self.advertisement.get_path())
            logger.debug(" Advertisement anterior desregistado")
        except Exception:
            pass  # Ignorar se não existir

        ad_manager.RegisterAdvertisement(
            self.advertisement.get_path(), {},
            reply_handler=lambda: logger.info(" Advertisement registado!"),
            error_handler=lambda e: logger.error(f" Falha ao registar advertisement: {e}")
        )

        self.mainloop = GLib.MainLoop()
        self.mainloop_thread = threading.Thread(target=self.mainloop.run, daemon=True)
        self.mainloop_thread.start()

        logger.info(" GATT Server iniciado em thread separada")

    def stop_gatt_server(self):
        """Para o GATT Server."""
        logger.info("A parar GATT Server...")

        if self.mainloop and self.mainloop.is_running():
            self.mainloop.quit()

        if self.mainloop_thread:
            self.mainloop_thread.join(timeout=2.0)

        logger.info(" GATT Server parado")

    def disconnect_all_downlinks(self):
        """
        Desconecta todos os downlinks (Chain Reaction Disconnect).

        Chamado quando este Node perde uplink (desconexão ou heartbeat timeout).
        Força todos os Nodes conectados abaixo a desconectarem em cascata.
        """
        with self.downlinks_lock:
            if not self.downlinks:
                logger.debug("Nenhum downlink para desconectar")
                return

            downlink_count = len(self.downlinks)
            logger.warning(f" Chain Reaction Disconnect: desconectando {downlink_count} downlink(s)")

            # Listar downlinks para log
            for addr, nid in self.downlinks.items():
                logger.info(f"   Desconectando downlink: {addr} (NID: {nid.to_bytes().hex()[:8]}...)")

            # Limpar downlinks
            # NOTA: A desconexão física acontece quando o GATT Server para ou
            # quando os downlinks detectam que perdemos uplink (hop_count = -1 no advertisement)
            self.downlinks.clear()

        # Limpar session keys dos downlinks
        with self.downlink_session_keys_lock:
            self.downlink_session_keys.clear()

        # Atualizar advertisement para hop_count = -1 (desconectado)
        # Isso fará os downlinks saberem que perdemos uplink
        with self.hop_count_lock:
            self.hop_count = -1
        self.update_advertisement_hop_count()

        logger.info(" Todos os downlinks desconectados (chain reaction completada)")

    # ========================================================================
    # ROUTER DAEMON - Callbacks e Handlers
    # ========================================================================

    def _router_send_callback(self, port_id: str, packet_bytes: bytes) -> bool:
        """
        Callback para o Router Daemon enviar pacotes via BLE.

        Args:
            port_id: "uplink" ou BLE address do downlink
            packet_bytes: Pacote em formato bytes

        Returns:
            True se enviou com sucesso
        """
        try:
            if port_id == "uplink":
                if not self.uplink_connection or not self.uplink_connection.is_connected:
                    logger.error(" Uplink não conectado")
                    return False

                self.uplink_connection.write(
                    IOT_NETWORK_SERVICE_UUID,
                    CHAR_NETWORK_PACKET_UUID,
                    packet_bytes
                )

                # Incrementar contador de mensagens enviadas
                with self.uplink_messages_lock:
                    self.uplink_messages_sent += 1

                logger.debug(f" Pacote enviado para uplink ({len(packet_bytes)} bytes)")
                return True

            else:
                if not self.service:
                    logger.error(" GATT Service não inicializado")
                    return False

                packet_char = self.service.get_packet_characteristic()
                packet_char.notify_packet(packet_bytes)

                logger.debug(f" Pacote enviado para downlink {port_id} ({len(packet_bytes)} bytes)")
                return True

        except Exception as e:
            logger.error(f"Erro ao enviar pacote via {port_id}: {e}")
            return False

    def _handle_data_packet_local(self, packet: Packet):
        """
        Handler local para pacotes DATA destinados a este Node.

        Chamado pelo Router Daemon quando packet.destination == my_nid.

        Args:
            packet: Pacote DATA recebido
        """
        logger.info(
            f" DATA recebido (local): {packet.source} → {packet.destination} "
            f"({len(packet.payload)} bytes)"
        )

        # DTLS End-to-End: Desencriptar payload se houver canal estabelecido
        decrypted_payload = packet.payload
        if self.dtls_channel and self.dtls_channel.established and self.dtls_channel.aesgcm:
            try:
                decrypted_payload = self.dtls_channel.unwrap(packet.payload)
                logger.info(f" Payload desencriptado end-to-end: {len(packet.payload)} → {len(decrypted_payload)} bytes")
            except Exception as e:
                logger.error(f" Erro ao desencriptar payload: {e}")
                return

        # Processar mensagem
        try:
            message = decrypted_payload.decode('utf-8', errors='replace')
            logger.info(f" Mensagem recebida de {str(packet.source)[:8]}...: {message!r}")
        except Exception as e:
            logger.warning(f"  Payload não é texto UTF-8: {e}")
            logger.info(f" Dados binários recebidos: {len(decrypted_payload)} bytes")

    def _handle_heartbeat_packet_local(self, packet: Packet):
        """
        Handler local para pacotes HEARTBEAT.

        Chamado pelo Router Daemon.

        Args:
            packet: Pacote HEARTBEAT recebido
        """
        # Reusa lógica existente
        self._handle_heartbeat(packet)

    # ========================================================================
    # FIM - ROUTER DAEMON
    # ========================================================================

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
            # Determinar port_id do downlink
            # NOTA: Idealmente precisaríamos do BLE address do client,
            # mas por agora usamos "downlink" genérico
            # TODO: Melhorar para obter address específico
            port_id = "downlink"

            # Delegar ao Router Daemon
            self.router.receive_packet(port_id, data)

        except Exception as e:
            logger.error(f"Erro ao processar pacote de downlink: {e}")

    def _on_downlink_auth_message(self, data: bytes, sender: str):
        """
        Callback quando recebe mensagem de autenticação de um downlink.

        Args:
            data: Dados da mensagem de autenticação
            sender: D-Bus sender ID do cliente que enviou a mensagem
        """
        import dbus

        logger.info(f" Mensagem de autenticação recebida de downlink (sender: {sender})")
        logger.warning("  Autenticação de downlinks não totalmente implementada - usando placeholder")
        # TODO: Implementar autenticação mutual com downlinks

        # WORKAROUND: BlueZ para advertising após conexão mesmo com duration=0
        # Re-registar advertising para manter visibilidade para outros Nodes
        try:
            adv_manager = dbus.Interface(
                self.bus.get_object('org.bluez', f'/org/bluez/{self.adapter_name}'),
                'org.bluez.LEAdvertisingManager1'
            )
            adv_manager.UnregisterAdvertisement(self.advertisement.get_path())
            adv_manager.RegisterAdvertisement(
                self.advertisement.get_path(),
                {},
                reply_handler=lambda: logger.info(" Advertising re-registado após conexão downlink"),
                error_handler=lambda e: logger.warning(f"  Falha ao re-registar advertising: {e}")
            )
        except Exception as e:
            logger.warning(f"  Erro ao re-registar advertising: {e}")

        # PLACEHOLDER: Retornar mensagem AUTH_SUCCESS vazia
        # Formato AuthMessage: type(1) + payload_length(2) + payload(N)
        # type=0x04 (AUTH_SUCCESS), payload_length=0x0000, payload=vazio
        # Isto permite que a conexão seja estabelecida sem autenticação real
        logger.info(" Enviando resposta AUTH_SUCCESS placeholder (autenticação aceite sem validação)")
        return b"\x04\x00\x00"  # AUTH_SUCCESS com payload vazio

    def _restart_advertising_after_uplink_connection(self):
        """
        Re-registar advertising após conectar ao Sink como cliente.

        WORKAROUND: Alguns adaptadores BLE param de fazer advertising quando atuam
        como cliente. Isto garante que permanecemos visíveis para outros Nodes.
        """
        import dbus
        import time

        try:
            logger.debug(" Re-registando advertising após conexão uplink...")
            adv_manager = dbus.Interface(
                self.bus.get_object('org.bluez', f'/org/bluez/{self.adapter_name}'),
                'org.bluez.LEAdvertisingManager1'
            )

            # Tentar desregistar (pode já não estar registado)
            try:
                adv_manager.UnregisterAdvertisement(self.advertisement.get_path())
                logger.debug(" Advertisement desregistado")
            except Exception as e:
                logger.debug(f"Advertisement já não estava registado: {e}")

            # Alguns adaptadores precisam de mais tempo - tentar com delays crescentes
            # NOTA: Alguns adaptadores BLE (especialmente adaptadores integrados sem dongle)
            # podem ter dificuldade em advertising simultâneo com conexão client.
            # Aumentamos delays e tentativas para dar mais hipóteses.
            delays = [0.3, 0.8, 1.5, 2.5]  # segundos - delays maiores para adaptadores problemáticos
            success = False

            for attempt in range(1, len(delays) + 1):
                time.sleep(delays[attempt - 1])

                # Event para aguardar resultado assíncrono
                result_event = threading.Event()
                error_msg = [None]  # Lista para permitir modificação em callback

                # Definir callbacks que sinalizam o event
                def make_reply_handler(attempt_num):
                    def handler():
                        logger.info(f"✅ Advertising re-registado após conexão uplink (tentativa {attempt_num})")
                        result_event.set()
                    return handler

                def make_error_handler(attempt_num):
                    def handler(e):
                        error_msg[0] = str(e)
                        logger.debug(f"❌ Tentativa {attempt_num} falhou: {e}")
                        result_event.set()
                    return handler

                try:
                    adv_manager.RegisterAdvertisement(
                        self.advertisement.get_path(),
                        {},
                        reply_handler=make_reply_handler(attempt),
                        error_handler=make_error_handler(attempt)
                    )
                    logger.debug(f"RegisterAdvertisement chamado (tentativa {attempt}, delay {delays[attempt-1]}s)")

                    # Aguardar resultado (timeout 3s) - CRÍTICO: esperar antes de retry!
                    if result_event.wait(timeout=3.0):
                        if error_msg[0] is None:
                            # Sucesso!
                            success = True
                            break
                        # Erro reportado via callback - continuar para próxima tentativa
                    else:
                        logger.debug(f"⏱️ Tentativa {attempt} timeout (sem resposta em 3s)")

                except Exception as e:
                    logger.debug(f"❌ Tentativa {attempt} com delay {delays[attempt-1]}s falhou imediatamente: {e}")

            if not success:
                logger.warning(f"  Falha ao re-registar advertising após {len(delays)} tentativas")

        except Exception as e:
            logger.warning(f"  Erro ao re-registar advertising após uplink: {e}")

    def discover_sink(self, timeout_s: int = 10) -> Optional[ScannedDevice]:
        """
        Descobre o Sink fazendo scan BLE.

        Args:
            timeout_s: Timeout para descoberta

        Returns:
            ScannedDevice do Sink ou None se não encontrado
        """
        logger.info(" A procurar Sink...")

        end_time = time.time() + timeout_s
        while time.time() < end_time and self.running:
            # Scan durante 5 segundos
            devices = self.ble_client.scan_iot_devices(duration_ms=5000)

            logger.info(f"Encontrados {len(devices)} dispositivos IoT")

            # Procurar pelo Sink (manufacturer data tipo=0, hop_count=255)
            for device in devices:
                logger.debug(f"  Device: {device}")

                if device.manufacturer_data and 0xFFFF in device.manufacturer_data:
                    data = device.manufacturer_data[0xFFFF]
                    if len(data) >= 2:
                        device_type = data[0]
                        hop_count = data[1]

                        logger.debug(f"    Type={device_type}, HopCount={hop_count}")

                        # Sink tem type=0 e hop_count=255 (representação de -1)
                        if device_type == 0 and hop_count == 255:
                            logger.info(f" Sink encontrado: {device}")
                            return device

            if devices:
                logger.debug("Nenhum Sink encontrado neste scan, tentando novamente...")

        logger.warning("  Sink não encontrado após timeout")
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
            logger.error(" Falha ao conectar ao Sink")
            return False

        if not self.uplink_connection.is_connected:
            logger.error(" Conexão não está ativa")
            return False

        logger.info(" Conectado ao Sink via GATT")

        # Descobrir serviços
        success = self.uplink_connection.discover_services()
        if not success:
            logger.error(" Falha ao descobrir serviços")
            return False

        if not self.uplink_connection.has_service(IOT_NETWORK_SERVICE_UUID):
            logger.error(f" Sink não tem o serviço IoT ({IOT_NETWORK_SERVICE_UUID})")
            return False

        logger.info(" Serviço IoT Network encontrado")

        # Resetar timestamp de heartbeat (nova conexão)
        self.last_heartbeat_time = 0
        logger.debug(" Timestamp de heartbeat resetado para nova conexão")

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
            logger.info(" Subscrito a NETWORK_PACKET")
        except Exception as e:
            logger.error(f"Erro ao subscrever NETWORK_PACKET: {e}")

    def _on_packet_notification(self, data: bytes):
        """
        Callback quando recebe notificação de pacote (ex: heartbeat).

        Args:
            data: Dados do pacote
        """
        try:
            # Delegar ao Router Daemon
            # Pacotes do uplink vêm da porta "uplink"
            self.router.receive_packet("uplink", data)

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

            if not self.replay_protection.check_and_update(heartbeat.sink_nid, packet.sequence):
                logger.warning(f"  REPLAY ATTACK detectado em heartbeat!")
                return

            # Heartbeats usam a chave padrão, não session keys (são broadcast)
            if not packet.verify_mac():
                logger.error(" MAC inválido em heartbeat!")
                return

            if not heartbeat.verify_signature(self.cert_manager):
                logger.error(" Assinatura de heartbeat inválida!")
                return

            # Atualizar timestamp
            self.last_heartbeat_time = time.time()
            self.heartbeat_sequence = packet.sequence

            age = heartbeat.age()
            logger.debug(f" Heartbeat recebido (seq={packet.sequence}, age={age:.2f}s)")

            # Heartbeat Flooding: forward para todos os downlinks
            self._forward_heartbeat_to_downlinks(packet)

        except Exception as e:
            logger.error(f"Erro ao processar heartbeat: {e}", exc_info=True)

    def _forward_heartbeat_to_downlinks(self, packet: Packet):
        """
        Forward heartbeat recebido para todos os downlinks (Heartbeat Flooding).

        O heartbeat original do Sink é propagado por toda a árvore de Nodes,
        permitindo que todos os dispositivos detectem perda de conectividade.

        Args:
            packet: Pacote de heartbeat original recebido do uplink
        """
        with self.downlinks_lock:
            if not self.downlinks:
                # Sem downlinks - nada a fazer
                return

            downlink_count = len(self.downlinks)
            logger.debug(f" Flooding heartbeat para {downlink_count} downlink(s)")

        # Forward o heartbeat para cada downlink via GATT Server
        # NOTA: O heartbeat é enviado como notificação através do NETWORK_PACKET characteristic
        if self.service:
            try:
                # Obter a characteristic de NETWORK_PACKET do GATT Server
                packet_char = self.service.get_characteristic(CHAR_NETWORK_PACKET_UUID)
                if packet_char:
                    packet_char.notify_packet(packet.to_bytes())
                    logger.debug(f" Heartbeat forwarded para {downlink_count} downlink(s)")
                else:
                    logger.warning("  NETWORK_PACKET characteristic não encontrada no GATT Server")
            except Exception as e:
                logger.error(f"Erro ao forward heartbeat: {e}", exc_info=True)

    def _handle_data_packet(self, packet: Packet):
        """
        Processa pacote DATA recebido.

        Args:
            packet: Pacote recebido
        """
        logger.info(
            f" DATA recebido: {packet.source} → {packet.destination} "
            f"({len(packet.payload)} bytes)"
        )

        if packet.destination != self.my_nid:
            logger.debug(f"Pacote não é para este node (dest={packet.destination})")
            return

        if not self.replay_protection.check_and_update(packet.source, packet.sequence):
            logger.warning(f"  REPLAY ATTACK detectado!")
            return

        with self.uplink_session_key_lock:
            if self.uplink_session_key:
                if not self._verify_packet_mac(packet, self.uplink_session_key):
                    logger.error(" MAC inválido!")
                    return

        # Processar payload
        logger.info(f" Mensagem recebida: {packet.payload!r}")

    def _on_auth_indication(self, data: bytes):
        """
        Callback para receber indicações de autenticação do Sink.

        Args:
            data: Dados recebidos via indication (pode ser fragmentado)
        """
        logger.debug(f" AUTH indication recebida: {len(data)} bytes")

        # Defragmentar mensagem
        is_complete, auth_data = self.auth_reassembler.add_fragment(data)

        if is_complete:
            logger.debug(f" AUTH mensagem completa: {len(auth_data)} bytes")
            with self.auth_response_lock:
                self.auth_response_buffer.append(auth_data)
        else:
            logger.debug(f" Aguardando mais fragmentos AUTH...")

    def authenticate_with_sink(self) -> bool:
        """
        Realiza autenticação mútua com o Sink.

        Returns:
            True se autenticação bem-sucedida
        """
        logger.info(" A iniciar autenticação com Sink...")

        if not self.uplink_connection or not self.uplink_connection.is_connected:
            logger.error("Não conectado ao Sink")
            return False

        try:
            # Limpar buffer de respostas de autenticações anteriores
            with self.auth_response_lock:
                self.auth_response_buffer.clear()

            # Subscrever a AUTH characteristic para receber indicações
            logger.debug(" A subscrever a AUTH characteristic...")
            success = self.uplink_connection.subscribe(
                IOT_NETWORK_SERVICE_UUID,
                CHAR_AUTHENTICATION_UUID,
                self._on_auth_indication
            )

            if not success:
                logger.error(" Falha ao subscrever AUTH characteristic")
                return False

            logger.debug(" Subscrito a AUTH indications")

            from common.security.authentication import AuthenticationProtocol

            auth_protocol = AuthenticationProtocol(self.cert_manager)

            # 1. Iniciar autenticação enviando nosso certificado
            logger.info(" Enviando certificado...")
            initial_msg = auth_protocol.start_authentication()

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
                    logger.debug(f" Enviando resposta ({len(reply)} bytes)")
                    self._send_auth_message(reply)

                if not continue_auth:
                    # Autenticação completou
                    if auth_protocol.state.name == 'AUTHENTICATED':
                        logger.info(" Autenticação bem-sucedida!")

                        # Obter session key
                        session_key = auth_protocol.derive_session_key()
                        if session_key:
                            with self.uplink_session_key_lock:
                                self.uplink_session_key = session_key
                            logger.info(" Session key estabelecida")

                            # Configurar session key no Router Daemon
                            self.router.set_session_key("uplink", session_key)
                            logger.info(" Session key configurada no Router Daemon")

                        # Obter NID do Sink
                        self.uplink_nid = auth_protocol.peer_nid

                        # Armazenar certificado do Sink para verificação de assinaturas
                        if auth_protocol.peer_cert:
                            self.cert_manager._sink_cert = auth_protocol.peer_cert
                            logger.info(" Certificado do Sink armazenado para verificação de heartbeats")

                        # Estabelecer canal DTLS end-to-end com o Sink
                        self.dtls_channel = DTLSChannel(
                            cert_path=self.cert_path,
                            key_path=self.key_path,
                            ca_cert_path=self.ca_cert_path,
                            is_server=False,
                            peer_nid=self.uplink_nid
                        )
                        if self.dtls_channel.establish():
                            logger.info(" Canal DTLS end-to-end estabelecido com Sink")

                            # Derivar chave de encriptação a partir da session key
                            if session_key:
                                self.dtls_channel.derive_encryption_key(session_key)
                                logger.info(" Chave de encriptação end-to-end derivada")

                        # WORKAROUND: Re-registar advertising após conectar ao Sink como cliente
                        # Alguns adaptadores BLE param de fazer advertising quando atuam como cliente
                        # Precisamos manter visibilidade para permitir que outros Nodes se conectem a nós
                        self._restart_advertising_after_uplink_connection()

                        self.authenticated = True
                        return True
                    else:
                        logger.error(f" Autenticação falhou: {auth_protocol.state.name}")
                        return False

            logger.error(" Autenticação expirou (timeout)")
            return False

        except Exception as e:
            logger.error(f" Erro durante autenticação: {e}", exc_info=True)
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

        # Obter e incrementar sequence number
        with self.data_packet_sequence_lock:
            seq = self.data_packet_sequence
            self.data_packet_sequence += 1

        # DTLS End-to-End: Encriptar payload antes de criar pacote
        encrypted_payload = message
        if self.dtls_channel and self.dtls_channel.established and self.dtls_channel.aesgcm:
            encrypted_payload = self.dtls_channel.wrap(message)
            logger.info(f" Payload encriptado end-to-end: {len(message)} → {len(encrypted_payload)} bytes")

        packet = Packet.create(
            source=self.my_nid,
            destination=destination,
            msg_type=MessageType.DATA,
            payload=encrypted_payload,
            sequence=seq,
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

        try:
            self.uplink_connection.write(
                IOT_NETWORK_SERVICE_UUID,
                CHAR_NETWORK_PACKET_UUID,
                packet.to_bytes()
            )
            logger.info(f" Mensagem enviada para {destination}")
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
                logger.warning("  Não conseguiu ler DeviceInfo do uplink")
                with self.hop_count_lock:
                    self.hop_count = 0  # Assumir conexão direta ao Sink
                return

            # Parsear DeviceInfo: 16 bytes NID + 1 byte hop_count + 1 byte device_type
            uplink_hop = device_info_data[16]  # hop_count do uplink

            # Se uplink é Sink (hop=255/-1), nosso hop = 0
            # Senão, nosso hop = uplink_hop + 1
            if uplink_hop == 255:
                new_hop = 0
                logger.info(f" Conectado ao Sink - hop_count=0")
            else:
                new_hop = uplink_hop + 1
                logger.info(f" Conectado a Node (hop={uplink_hop}) - nosso hop_count={new_hop}")

            with self.hop_count_lock:
                self.hop_count = new_hop

        except Exception as e:
            logger.error(f"Erro ao atualizar hop_count: {e}")
            with self.hop_count_lock:
                self.hop_count = 0  # Default: assumir hop 0

    def run(self):
        """Loop principal do Node."""
        logger.info("=" * 60)
        if self.peripheral_only:
            logger.info("  A iniciar IoT Node (PERIPHERAL-ONLY mode)")
            logger.info("  Modo: Apenas aceita conexões, não procura uplink")
        else:
            logger.info("  A iniciar IoT Node (dual-mode)")
        logger.info("=" * 60)

        self.running = True

        try:
            # 0. Configurar e iniciar GATT Server (para aceitar downlinks)
            self.setup_gatt_server()
            self.start_gatt_server()
            logger.info(" GATT Server ativo - aguardando downlinks")

            # Se modo peripheral-only, não procurar uplink
            if self.peripheral_only:
                logger.info(" Modo peripheral-only ativo")
                logger.info(" Advertising ativo - aguardando conexões de outros nodes")

                # Loop apenas como server
                while self.running:
                    time.sleep(1)
                return

            # 1. Descobrir uplink (Sink ou outro Node)
            self.sink_device = self.discover_sink(timeout_s=30)
            if not self.sink_device:
                logger.error(" Falha ao descobrir uplink")
                # Continuar mesmo sem uplink - podemos receber downlinks
                logger.warning("  Sem uplink - operando apenas como server")

                # Loop apenas como server
                while self.running:
                    time.sleep(1)
                return

            # 2. Conectar ao uplink
            if not self.connect_to_sink():
                logger.error(" Falha ao conectar ao uplink")
                return

            # 3. Atualizar hop_count baseado no uplink
            self._update_hop_count_from_uplink()

            # 4. Atualizar advertisement com novo hop_count
            self.update_advertisement_hop_count()

            # 5. Autenticar
            if not self.authenticate_with_sink():
                logger.error(" Falha na autenticação")
                return

            logger.info("=" * 60)
            logger.info(f" Node pronto! Uplink conectado (hop={self.hop_count})")
            logger.info("=" * 60)

            # Loop principal - monitorizar conexão
            while self.running:
                time.sleep(1)

                if not self.uplink_connection.is_connected:
                    logger.warning("  Conexão perdida com Sink")
                    # Chain Reaction Disconnect: desconectar todos os downlinks
                    self.disconnect_all_downlinks()
                    break

                # Heartbeats são enviados a cada 5s, então 15s = 3x o intervalo
                if self.last_heartbeat_time > 0:
                    time_since_heartbeat = time.time() - self.last_heartbeat_time
                    if time_since_heartbeat > 15:
                        logger.error(
                            f" Timeout de heartbeat! Sem heartbeat há {time_since_heartbeat:.1f}s "
                            f"(último seq={self.heartbeat_sequence})"
                        )
                        logger.warning("  Desconectando do uplink devido a timeout de heartbeat...")
                        # Chain Reaction Disconnect: desconectar todos os downlinks
                        self.disconnect_all_downlinks()
                        break
                    elif time_since_heartbeat > 10:
                        logger.warning(
                            f"  Sem heartbeat há {time_since_heartbeat:.1f}s "
                            f"(último seq={self.heartbeat_sequence})"
                        )

        except KeyboardInterrupt:
            logger.info("\n  Keyboard interrupt recebido")
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

        logger.info(" Node parado")


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
    parser.add_argument(
        '--peripheral-only',
        action='store_true',
        help='Modo peripheral-only: não procura uplink, apenas aceita conexões downlink'
    )

    args = parser.parse_args()

    try:
        node = IoTNode(
            cert_path=args.cert,
            key_path=args.key,
            ca_cert_path=args.ca_cert,
            adapter_index=args.adapter,
            peripheral_only=args.peripheral_only,
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
