#!/usr/bin/env python3
"""
Router Daemon - Serviço de routing interno para dispositivos IoT.

Conforme Secção 5.7 da especificação:
- Fornece funcionalidades básicas de rede para comunicação bidirectional com o Sink
- Escuta todas as conexões BLE locais (1 uplink + N downlinks)
- Forward packets se necessário
- Adiciona/remove MACs per-link (mas não lida com DTLS)

Características:
- Learning switch behavior (forwarding table dinâmica)
- Per-link MAC validation
- TTL management
- Separation of concerns: routing separado da aplicação
"""

import threading
import time
from typing import Dict, Optional, Callable, Set
from loguru import logger

from common.network.packet import Packet, MessageType
from common.network.forwarding_table import ForwardingTable
from common.utils.nid import NID
from common.security.crypto import calculate_hmac, verify_hmac, DEFAULT_HMAC_KEY
from common.security.replay_protection import ReplayProtection


def _get_msg_type_name(msg_type) -> str:
    """Helper para obter nome do MessageType (handle int ou enum)."""
    return msg_type.name if hasattr(msg_type, 'name') else f"MessageType({msg_type})"


class RouterDaemon:
    """
    Router Daemon - Serviço de routing para dispositivos IoT.

    Este daemon implementa a camada de rede conforme Secção 5.7:
    - Routing de pacotes entre uplink e downlinks
    - Forwarding table (learning switch)
    - Per-link MAC handling
    - TTL decrementation
    - Separation from DTLS (end-to-end encryption)
    """

    def __init__(self, my_nid: NID):
        """
        Inicializa o Router Daemon.

        Args:
            my_nid: Network Identifier deste dispositivo
        """
        self.my_nid = my_nid

        # Forwarding table (NID → port_id)
        self.forwarding_table = ForwardingTable()

        # Replay protection (verificar duplicados)
        self.replay_protection = ReplayProtection(window_size=100)

        # Session keys por porta (port_id → session_key)
        # Port IDs: "uplink" ou BLE address do downlink
        self.session_keys: Dict[str, bytes] = {}
        self.session_keys_lock = threading.Lock()

        # Callbacks para entregar pacotes localmente
        # msg_type → callback(packet)
        self.local_handlers: Dict[MessageType, Callable[[Packet], None]] = {}
        self.local_handlers_lock = threading.Lock()

        # Callback para enviar pacote por uma porta específica
        # Será configurado externamente pelo Node/Sink
        self.send_callback: Optional[Callable[[str, bytes], bool]] = None

        # Estatísticas
        self.packets_routed = 0
        self.packets_delivered_locally = 0
        self.packets_dropped = 0
        self.stats_lock = threading.Lock()

        # Running state
        self.running = False

        logger.info(f" Router Daemon inicializado para NID={str(my_nid)[:8]}...")

    def set_send_callback(self, callback: Callable[[str, bytes], bool]):
        """
        Configura callback para enviar pacotes via BLE.

        Args:
            callback: Função(port_id, packet_bytes) → bool
                     port_id: "uplink" ou BLE address
        """
        self.send_callback = callback
        logger.debug(" Send callback configurado")

    def register_local_handler(self, msg_type: MessageType, handler: Callable[[Packet], None]):
        """
        Regista handler para processar pacotes destinados a este dispositivo.

        Args:
            msg_type: Tipo de mensagem (DATA, HEARTBEAT, etc)
            handler: Função que processa o pacote
        """
        with self.local_handlers_lock:
            self.local_handlers[msg_type] = handler

        # MessageType pode ser int ou enum, handle both
        type_name = _get_msg_type_name(msg_type)
        logger.debug(f" Handler registado para {type_name}")

    def set_session_key(self, port_id: str, session_key: bytes):
        """
        Configura session key para uma porta específica.

        Args:
            port_id: "uplink" ou BLE address do downlink
            session_key: Session key de 32 bytes (derivada via ECDH)
        """
        with self.session_keys_lock:
            self.session_keys[port_id] = session_key
        logger.debug(f" Session key configurada para porta {port_id}")

    def remove_session_key(self, port_id: str):
        """Remove session key quando porta desconecta."""
        with self.session_keys_lock:
            if port_id in self.session_keys:
                del self.session_keys[port_id]
        logger.debug(f" Session key removida para porta {port_id}")

    def receive_packet(self, port_id: str, packet_bytes: bytes):
        """
        Recebe pacote de uma porta BLE (uplink ou downlink).

        Este é o ponto de entrada principal do daemon.

        Args:
            port_id: "uplink" ou BLE address do downlink
            packet_bytes: Pacote em formato bytes
        """
        try:
            # Parsear pacote
            packet = Packet.from_bytes(packet_bytes)

            logger.debug(
                f" Pacote recebido de {port_id}: "
                f"{packet.source} → {packet.destination} "
                f"(type={_get_msg_type_name(packet.msg_type)}, ttl={packet.ttl})"
            )

            # 1. Verificar replay protection
            if not self.replay_protection.check_and_update(packet.source, packet.sequence):
                logger.warning(
                    f"  REPLAY ATTACK detectado! "
                    f"Source={packet.source}, Seq={packet.sequence}"
                )
                with self.stats_lock:
                    self.packets_dropped += 1
                return

            # 2. Verificar MAC da porta de entrada
            if not self._verify_packet_mac(packet, port_id):
                logger.error(f" MAC inválido no pacote de {port_id}")
                with self.stats_lock:
                    self.packets_dropped += 1
                return

            # 3. Aprender rota (learning switch)
            # Pacote veio de port_id, então para chegar a packet.source
            # devemos enviar para port_id
            self.forwarding_table.learn(packet.source, port_id)
            logger.debug(f" Aprendido: {str(packet.source)[:8]}... → {port_id}")

            # 4. Decidir: forward ou entregar localmente?
            # HEARTBEAT packets são broadcast - sempre entregar localmente E forward
            if packet.msg_type == MessageType.HEARTBEAT:
                # Broadcast: entregar localmente sempre
                self._deliver_locally(packet)
                # Se TTL > 1, também fazer forward para downlinks
                if packet.ttl > 1:
                    self._forward_packet(packet, incoming_port=port_id)
            elif packet.destination == self.my_nid:
                # Para nós - entregar localmente
                self._deliver_locally(packet)
            else:
                # Para outro dispositivo - forward
                self._forward_packet(packet, incoming_port=port_id)

        except Exception as e:
            logger.error(f"Erro ao processar pacote de {port_id}: {e}", exc_info=True)
            with self.stats_lock:
                self.packets_dropped += 1

    def _verify_packet_mac(self, packet: Packet, port_id: str) -> bool:
        """
        Verifica MAC do pacote usando session key da porta.

        HEARTBEAT packets usam DEFAULT_HMAC_KEY (autenticidade garantida por ECDSA signature).
        DATA packets usam session key ECDH negociada durante autenticação.

        Args:
            packet: Pacote recebido
            port_id: Porta de entrada

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

        # HEARTBEAT packets usam DEFAULT_HMAC_KEY
        # (autenticidade garantida por ECDSA P-521 signature dentro do payload)
        if packet.msg_type == MessageType.HEARTBEAT:
            is_valid = verify_hmac(mac_data, packet.mac, DEFAULT_HMAC_KEY)

            if not is_valid:
                logger.error(
                    f" HEARTBEAT MAC verification failed (DEFAULT_HMAC_KEY)\n"
                    f"   Source: {packet.source}\n"
                    f"   Dest: {packet.destination}\n"
                    f"   Seq: {packet.sequence}"
                )

            return is_valid

        # DATA e outros packets usam session key negociada
        with self.session_keys_lock:
            session_key = self.session_keys.get(port_id)

        if not session_key:
            logger.warning(f"  Sem session key para porta {port_id}")
            return False

        is_valid = verify_hmac(mac_data, packet.mac, session_key)

        if not is_valid:
            logger.error(
                f" MAC verification failed for packet from {port_id}\n"
                f"   Source: {packet.source}\n"
                f"   Dest: {packet.destination}\n"
                f"   Type: {_get_msg_type_name(packet.msg_type)}\n"
                f"   Seq: {packet.sequence}"
            )

        return is_valid

    def _deliver_locally(self, packet: Packet):
        """
        Entrega pacote à aplicação local.

        Args:
            packet: Pacote destinado a este dispositivo
        """
        logger.info(
            f" Entregando localmente: {packet.source} → {packet.destination} "
            f"(type={_get_msg_type_name(packet.msg_type)}, {len(packet.payload)} bytes)"
        )

        # Encontrar handler para este tipo de mensagem
        with self.local_handlers_lock:
            handler = self.local_handlers.get(packet.msg_type)

        if handler:
            try:
                handler(packet)
                with self.stats_lock:
                    self.packets_delivered_locally += 1
            except Exception as e:
                logger.error(f"Erro ao processar pacote localmente: {e}", exc_info=True)
        else:
            logger.warning(f"  Sem handler para tipo {_get_msg_type_name(packet.msg_type)}")

    def _forward_packet(self, packet: Packet, incoming_port: str):
        """
        Forward pacote para próximo hop.

        Args:
            packet: Pacote a forwarded
            incoming_port: Porta de onde veio (não reenviar para lá)
        """
        # 1. Verificar TTL
        if packet.ttl <= 1:
            logger.warning(f"  Pacote descartado - TTL expirou")
            with self.stats_lock:
                self.packets_dropped += 1
            return

        # 2. Decrementar TTL
        packet.ttl -= 1

        # 3. Consultar forwarding table
        next_port = self.forwarding_table.lookup(packet.destination)

        if not next_port:
            logger.warning(
                f"  Rota desconhecida para {str(packet.destination)[:8]}... - descartando"
            )
            with self.stats_lock:
                self.packets_dropped += 1
            return

        # 4. Não enviar de volta pela porta de entrada
        if next_port == incoming_port:
            logger.warning(
                f"  Loop detectado - next_port == incoming_port ({next_port})"
            )
            with self.stats_lock:
                self.packets_dropped += 1
            return

        # 5. Recalcular MAC para a porta de saída
        # Construir dados para novo MAC
        mac_data = (
            packet.source.to_bytes() +
            packet.destination.to_bytes() +
            bytes([packet.msg_type, packet.ttl]) +
            packet.sequence.to_bytes(4, 'big') +
            packet.payload
        )

        # HEARTBEAT packets usam DEFAULT_HMAC_KEY, outros usam session key
        if packet.msg_type == MessageType.HEARTBEAT:
            packet.mac = calculate_hmac(mac_data, DEFAULT_HMAC_KEY)
        else:
            # DATA e outros packets usam session key negociada
            with self.session_keys_lock:
                next_session_key = self.session_keys.get(next_port)

            if not next_session_key:
                logger.error(f" Sem session key para porta {next_port}")
                with self.stats_lock:
                    self.packets_dropped += 1
                return

            packet.mac = calculate_hmac(mac_data, next_session_key)

        # 6. Enviar via callback
        if not self.send_callback:
            logger.error(" Send callback não configurado!")
            return

        success = self.send_callback(next_port, packet.to_bytes())

        if success:
            logger.info(
                f" Forwarded: {str(packet.source)[:8]}... → "
                f"{str(packet.destination)[:8]}... via {next_port} "
                f"(ttl={packet.ttl})"
            )
            with self.stats_lock:
                self.packets_routed += 1
        else:
            logger.error(f" Falha ao enviar pacote para {next_port}")
            with self.stats_lock:
                self.packets_dropped += 1

    def send_packet(
        self,
        destination: NID,
        msg_type: MessageType,
        payload: bytes,
        sequence: int
    ) -> bool:
        """
        Envia pacote originado localmente.

        Esta função é usada pela aplicação local (Node/Sink) para enviar dados.

        Args:
            destination: NID de destino
            msg_type: Tipo de mensagem
            payload: Dados a enviar
            sequence: Sequence number

        Returns:
            True se enviou com sucesso
        """
        packet = Packet.create(
            source=self.my_nid,
            destination=destination,
            msg_type=msg_type,
            payload=payload,
            sequence=sequence
        )

        # Consultar forwarding table para saber por onde enviar
        next_port = self.forwarding_table.lookup(destination)

        if not next_port:
            logger.error(f" Rota desconhecida para {str(destination)[:8]}...")
            return False

        # Calcular MAC para porta de saída
        with self.session_keys_lock:
            session_key = self.session_keys.get(next_port)

        if not session_key:
            logger.error(f" Sem session key para porta {next_port}")
            return False

        # Construir dados para MAC
        mac_data = (
            packet.source.to_bytes() +
            packet.destination.to_bytes() +
            bytes([packet.msg_type, packet.ttl]) +
            packet.sequence.to_bytes(4, 'big') +
            packet.payload
        )

        packet.mac = calculate_hmac(mac_data, session_key)

        if not self.send_callback:
            logger.error(" Send callback não configurado!")
            return False

        success = self.send_callback(next_port, packet.to_bytes())

        if success:
            logger.info(
                f" Enviado: {str(destination)[:8]}... via {next_port} "
                f"(type={_get_msg_type_name(msg_type)})"
            )

        return success

    def get_stats(self) -> Dict[str, int]:
        """
        Retorna estatísticas do daemon.

        Returns:
            Dict com contadores
        """
        with self.stats_lock:
            return {
                "routed": self.packets_routed,
                "delivered": self.packets_delivered_locally,
                "dropped": self.packets_dropped,
                "total": self.packets_routed + self.packets_delivered_locally + self.packets_dropped
            }

    def get_forwarding_table_snapshot(self) -> Dict[str, str]:
        """
        Retorna snapshot da forwarding table.

        Returns:
            Dict {nid_str: port_id}
        """
        entries = self.forwarding_table.get_all_entries()
        return {str(nid): port for nid, port in entries.items()}

    def start(self):
        """Inicia o daemon."""
        self.running = True
        logger.info(" Router Daemon iniciado")

    def stop(self):
        """Para o daemon."""
        self.running = False
        logger.info(" Router Daemon parado")
