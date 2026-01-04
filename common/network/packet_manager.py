"""
Packet Manager - Gestão de envio e receção de pacotes com validação HMAC.

Responsável por:
- Criar pacotes com MAC válido
- Validar MAC de pacotes recebidos
- Gerir sequence numbers
- Routing de pacotes
"""

import hmac
import hashlib
import threading
from typing import Optional, Callable, Dict
from dataclasses import dataclass

from common.network.packet import Packet
from common.utils.nid import NID
from common.utils.constants import MessageType, MAC_SIZE
from common.utils.logger import get_logger

logger = get_logger("packet_manager")


class PacketManager:
    """
    Gestor de pacotes da rede IoT.

    Responsável por criar, validar e rotear pacotes.
    """

    def __init__(self, local_nid: NID, shared_key: bytes):
        """
        Inicializa o Packet Manager.

        Args:
            local_nid: NID do dispositivo local
            shared_key: Chave partilhada para HMAC (deve ser derivada do certificado)
        """
        self.local_nid = local_nid
        self.shared_key = shared_key

        # Sequence number para pacotes enviados
        self._sequence_counter = 0
        self._sequence_lock = threading.Lock()

        # Callbacks para pacotes recebidos (por tipo de mensagem)
        self._packet_handlers: Dict[int, Callable[[Packet], None]] = {}

        logger.info(f"PacketManager iniciado para NID {local_nid}")

    # ========================================================================
    # Sequence Number Management
    # ========================================================================

    def _get_next_sequence(self) -> int:
        """
        Obtém o próximo sequence number.

        Returns:
            Próximo sequence number
        """
        with self._sequence_lock:
            seq = self._sequence_counter
            self._sequence_counter = (self._sequence_counter + 1) % (2**32)  # 4 bytes = 32 bits
            return seq

    # ========================================================================
    # HMAC Calculation and Validation
    # ========================================================================

    def _calculate_mac(self, packet: Packet) -> bytes:
        """
        Calcula o MAC (HMAC-SHA256) para um pacote.

        O MAC é calculado sobre: header (sem MAC) + payload

        Args:
            packet: Pacote para calcular MAC

        Returns:
            MAC calculado (32 bytes)
        """
        # Obter header sem MAC
        header_without_mac = packet.get_header_for_mac()

        # Dados para MAC = header + payload
        data_for_mac = header_without_mac + packet.payload

        # Calcular HMAC-SHA256
        mac = hmac.new(self.shared_key, data_for_mac, hashlib.sha256).digest()

        return mac

    def _validate_mac(self, packet: Packet) -> bool:
        """
        Valida o MAC de um pacote recebido.

        Args:
            packet: Pacote para validar

        Returns:
            True se MAC válido, False caso contrário
        """
        # Calcular MAC esperado
        expected_mac = self._calculate_mac(packet)

        # Comparação constant-time para prevenir timing attacks
        return hmac.compare_digest(packet.mac, expected_mac)

    # ========================================================================
    # Packet Creation
    # ========================================================================

    def create_packet(
        self,
        destination: NID,
        msg_type: int,
        payload: bytes,
        ttl: Optional[int] = None,
    ) -> Packet:
        """
        Cria um pacote completo com MAC válido.

        Args:
            destination: NID de destino
            msg_type: Tipo de mensagem
            payload: Dados a enviar
            ttl: Time-to-live (None = default)

        Returns:
            Pacote criado e assinado
        """
        from common.utils.constants import DEFAULT_TTL

        # Obter próximo sequence number
        sequence = self._get_next_sequence()

        packet = Packet.create(
            source=self.local_nid,
            destination=destination,
            msg_type=msg_type,
            payload=payload,
            sequence=sequence,
            ttl=ttl if ttl is not None else DEFAULT_TTL,
            mac=b'\x00' * MAC_SIZE,
        )

        # Calcular e atualizar MAC
        mac = self._calculate_mac(packet)
        packet.update_mac(mac)

        logger.debug(f"Pacote criado: {MessageType.to_string(msg_type)} -> {destination} (seq={sequence})")

        return packet

    # ========================================================================
    # Packet Validation
    # ========================================================================

    def validate_packet(self, packet: Packet) -> bool:
        """
        Valida um pacote recebido.

        Verifica:
        - MAC válido
        - TTL > 0

        Args:
            packet: Pacote para validar

        Returns:
            True se pacote válido, False caso contrário
        """
        if packet.ttl == 0:
            logger.warning(f"Pacote com TTL=0 descartado (seq={packet.sequence})")
            return False

        if not self._validate_mac(packet):
            logger.warning(f"Pacote com MAC inválido descartado (seq={packet.sequence})")
            return False

        return True

    # ========================================================================
    # Packet Handlers
    # ========================================================================

    def register_handler(self, msg_type: int, handler: Callable[[Packet], None]):
        """
        Regista um handler para um tipo de mensagem.

        Args:
            msg_type: Tipo de mensagem
            handler: Função callback que recebe o pacote
        """
        self._packet_handlers[msg_type] = handler
        logger.debug(f"Handler registado para {MessageType.to_string(msg_type)}")

    def handle_received_packet(self, packet: Packet) -> bool:
        """
        Processa um pacote recebido.

        1. Valida o pacote
        2. Chama o handler apropriado se registado

        Args:
            packet: Pacote recebido

        Returns:
            True se pacote foi processado, False se foi descartado
        """
        if not self.validate_packet(packet):
            return False

        logger.info(
            f"Pacote recebido: {MessageType.to_string(packet.msg_type)} "
            f"de {packet.source} (seq={packet.sequence}, ttl={packet.ttl})"
        )

        # Chamar handler se registado
        handler = self._packet_handlers.get(packet.msg_type)
        if handler:
            try:
                handler(packet)
            except Exception as e:
                logger.error(f"Erro ao processar pacote: {e}", exc_info=True)
                return False
        else:
            logger.warning(f"Nenhum handler registado para {MessageType.to_string(packet.msg_type)}")

        return True

    # ========================================================================
    # Utility
    # ========================================================================

    def create_data_packet(self, destination: NID, data: bytes) -> Packet:
        """Helper para criar pacote de dados."""
        return self.create_packet(destination, MessageType.DATA, data)

    def create_heartbeat_packet(self, destination: NID) -> Packet:
        """Helper para criar pacote de heartbeat."""
        return self.create_packet(destination, MessageType.HEARTBEAT, b'')

    def create_control_packet(self, destination: NID, command: bytes) -> Packet:
        """Helper para criar pacote de controlo."""
        return self.create_packet(destination, MessageType.CONTROL, command)
