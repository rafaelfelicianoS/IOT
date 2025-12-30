#!/usr/bin/env python3
"""
IoT Node - Dispositivo cliente da rede IoT.

O Node é responsável por:
- Descobrir o Sink via BLE scan
- Conectar ao Sink via GATT Client
- Autenticar-se com certificados X.509
- Receber heartbeats do Sink
- Enviar mensagens ao Sink
- Manter session key para comunicação segura
"""

import sys
import argparse
import signal
import time
from pathlib import Path
from typing import Optional, Dict
import threading

from common.utils.logger import get_logger
from common.utils.nid import NID
from common.ble.gatt_client import BLEClient, ScannedDevice, BLEConnection
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

        # BLE Client
        self.ble_client = BLEClient(adapter_index=adapter_index)

        # Conexão ao Sink
        self.sink_connection: Optional[BLEConnection] = None
        self.sink_nid: Optional[NID] = None
        self.sink_device: Optional[ScannedDevice] = None

        # Session key com o Sink
        self.session_key: Optional[bytes] = None
        self.session_key_lock = threading.Lock()

        # Estado
        self.authenticated = False
        self.last_heartbeat_time = 0
        self.heartbeat_sequence = 0

        logger.info(f"IoT Node inicializado (adapter=hci{adapter_index})")

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
        self.sink_connection = self.ble_client.connect_to_device(self.sink_device)

        if not self.sink_connection:
            logger.error("❌ Falha ao conectar ao Sink")
            return False

        if not self.sink_connection.is_connected:
            logger.error("❌ Conexão não está ativa")
            return False

        logger.info("✅ Conectado ao Sink via GATT")

        # Descobrir serviços
        success = self.sink_connection.discover_services()
        if not success:
            logger.error("❌ Falha ao descobrir serviços")
            return False

        # Verificar se tem o serviço IoT
        if not self.sink_connection.has_service(IOT_NETWORK_SERVICE_UUID):
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
            self.sink_connection.subscribe(
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
            if not self.sink_nid:
                self.sink_nid = heartbeat.sink_nid
                logger.info(f"Sink NID identificado: {self.sink_nid}")

            # Verificar replay
            if not self.replay_protection.check_and_update(heartbeat.sink_nid, packet.sequence):
                logger.warning(f"⚠️  REPLAY ATTACK detectado em heartbeat!")
                return

            # Verificar MAC se temos session key
            with self.session_key_lock:
                if self.session_key:
                    if not self._verify_packet_mac(packet, self.session_key):
                        logger.error("❌ MAC inválido em heartbeat!")
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
        with self.session_key_lock:
            if self.session_key:
                if not self._verify_packet_mac(packet, self.session_key):
                    logger.error("❌ MAC inválido!")
                    return

        # Processar payload
        logger.info(f"✅ Mensagem recebida: {packet.payload!r}")

    def authenticate_with_sink(self) -> bool:
        """
        Realiza autenticação mútua com o Sink.

        Returns:
            True se autenticação bem-sucedida
        """
        logger.info("🔐 A iniciar autenticação com Sink...")

        # TODO: Implementar protocolo de autenticação
        # Por agora, apenas marcar como autenticado
        logger.warning("⚠️  Autenticação não totalmente implementada - usando placeholder")

        self.authenticated = True
        logger.info("✅ Autenticação completada (placeholder)")

        return True

    def send_message(self, message: bytes, destination: Optional[NID] = None) -> bool:
        """
        Envia uma mensagem através do Sink.

        Args:
            message: Mensagem a enviar
            destination: NID de destino (None = Sink)

        Returns:
            True se enviou com sucesso
        """
        if not self.sink_connection or not self.sink_connection.is_connected:
            logger.error("Não conectado ao Sink")
            return False

        if destination is None:
            destination = self.sink_nid

        # Criar pacote
        packet = Packet.create(
            source=self.my_nid,
            destination=destination,
            msg_type=MessageType.DATA,
            payload=message,
        )

        # Calcular MAC se temos session key
        with self.session_key_lock:
            if self.session_key:
                # Construir dados para MAC
                mac_data = (
                    packet.source.to_bytes() +
                    packet.destination.to_bytes() +
                    bytes([packet.msg_type, packet.ttl]) +
                    packet.sequence.to_bytes(4, 'big') +
                    packet.payload
                )
                packet.mac = calculate_hmac(mac_data, self.session_key)
            else:
                packet.calculate_and_set_mac()

        # Enviar via NETWORK_PACKET characteristic
        try:
            self.sink_connection.write(
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

    def run(self):
        """Loop principal do Node."""
        logger.info("=" * 60)
        logger.info("  A iniciar IoT Node")
        logger.info("=" * 60)

        self.running = True

        try:
            # 1. Descobrir Sink
            self.sink_device = self.discover_sink(timeout_s=30)
            if not self.sink_device:
                logger.error("❌ Falha ao descobrir Sink")
                return

            # 2. Conectar ao Sink
            if not self.connect_to_sink():
                logger.error("❌ Falha ao conectar ao Sink")
                return

            # 3. Autenticar
            if not self.authenticate_with_sink():
                logger.error("❌ Falha na autenticação")
                return

            logger.info("=" * 60)
            logger.info("✅ Node pronto e conectado ao Sink!")
            logger.info("=" * 60)

            # Loop principal - monitorizar conexão
            while self.running:
                time.sleep(1)

                # Verificar se ainda está conectado
                if not self.sink_connection.is_connected:
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

        # Desconectar do Sink
        if self.sink_connection:
            self.sink_connection.disconnect()

        # Desconectar todos
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
