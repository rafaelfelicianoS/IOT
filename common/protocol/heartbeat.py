"""
Protocolo de Heartbeat.

O Sink envia heartbeats periódicos (broadcast) para todos os dispositivos
conectados. Os nodes usam estes heartbeats para:
- Verificar conectividade com o Sink
- Detetar timeouts (3 heartbeats perdidos = desconexão)
- Sincronizar informação de rede

Formato do payload do heartbeat:
┌───────────────┬──────────────┬────────────┐
│  Sink NID     │  Timestamp   │  Signature │
│   16 bytes    │   8 bytes    │  64 bytes  │
└───────────────┴──────────────┴────────────┘
Total: 88 bytes

Signature: ECDSA (P-521) do (Sink NID + Timestamp)
"""

import struct
import time
from typing import Optional
from dataclasses import dataclass

from common.utils.nid import NID
from common.utils.constants import MessageType, HEARTBEAT_INTERVAL
from common.network.packet import Packet
from common.utils.logger import get_logger

logger = get_logger("heartbeat")

# Tamanhos dos campos (bytes)
HEARTBEAT_NID_SIZE = 16
HEARTBEAT_TIMESTAMP_SIZE = 8
HEARTBEAT_SIGNATURE_SIZE = 64
HEARTBEAT_PAYLOAD_SIZE = HEARTBEAT_NID_SIZE + HEARTBEAT_TIMESTAMP_SIZE + HEARTBEAT_SIGNATURE_SIZE


@dataclass
class HeartbeatPayload:
    """
    Payload de um heartbeat.

    Attributes:
        sink_nid: NID do Sink que enviou o heartbeat
        timestamp: Timestamp UNIX (segundos desde epoch)
        signature: Assinatura digital ECDSA (placeholder por agora)
    """
    sink_nid: NID
    timestamp: float
    signature: bytes

    def __post_init__(self):
        """Validação após inicialização."""
        if not isinstance(self.sink_nid, NID):
            raise TypeError("sink_nid deve ser um NID")

        if len(self.signature) != HEARTBEAT_SIGNATURE_SIZE:
            raise ValueError(
                f"Signature deve ter {HEARTBEAT_SIGNATURE_SIZE} bytes, "
                f"recebeu {len(self.signature)}"
            )

    @classmethod
    def create(
        cls,
        sink_nid: NID,
        timestamp: Optional[float] = None,
        signature: Optional[bytes] = None,
    ) -> 'HeartbeatPayload':
        """
        Cria um novo heartbeat payload.

        Args:
            sink_nid: NID do Sink
            timestamp: Timestamp (usa time.time() se None)
            signature: Assinatura digital (placeholder se None)

        Returns:
            Novo HeartbeatPayload
        """
        if timestamp is None:
            timestamp = time.time()

        if signature is None:
            # Placeholder: zeros
            # TODO: Implementar assinatura digital ECDSA
            signature = b'\x00' * HEARTBEAT_SIGNATURE_SIZE

        return cls(
            sink_nid=sink_nid,
            timestamp=timestamp,
            signature=signature,
        )

    def to_bytes(self) -> bytes:
        """
        Serializa o heartbeat payload para bytes.

        Returns:
            Representação binária (88 bytes)
        """
        # Format: sink_nid(16) + timestamp(8 double) + signature(64)
        return struct.pack(
            f"!{HEARTBEAT_NID_SIZE}sd{HEARTBEAT_SIGNATURE_SIZE}s",
            self.sink_nid.to_bytes(),
            self.timestamp,
            self.signature,
        )

    @classmethod
    def from_bytes(cls, data: bytes) -> 'HeartbeatPayload':
        """
        Desserializa um heartbeat payload a partir de bytes.

        Args:
            data: Dados binários do payload

        Returns:
            HeartbeatPayload desserializado

        Raises:
            ValueError: Se os dados forem inválidos
        """
        if len(data) != HEARTBEAT_PAYLOAD_SIZE:
            raise ValueError(
                f"Heartbeat payload deve ter {HEARTBEAT_PAYLOAD_SIZE} bytes, "
                f"recebeu {len(data)}"
            )

        # Unpack
        format_str = f"!{HEARTBEAT_NID_SIZE}sd{HEARTBEAT_SIGNATURE_SIZE}s"
        (
            sink_nid_bytes,
            timestamp,
            signature,
        ) = struct.unpack(format_str, data)

        sink_nid = NID.from_bytes(sink_nid_bytes)

        return cls(
            sink_nid=sink_nid,
            timestamp=timestamp,
            signature=signature,
        )

    def verify_signature(self) -> bool:
        """
        Verifica a assinatura digital do heartbeat.

        Returns:
            True se assinatura válida, False caso contrário

        Note:
            Por agora retorna sempre True (placeholder).
            TODO: Implementar verificação ECDSA real.
        """
        # TODO: Implementar verificação ECDSA
        logger.debug("Verificação de assinatura (placeholder)")
        return True

    def age(self) -> float:
        """
        Calcula a idade do heartbeat (tempo desde que foi criado).

        Returns:
            Tempo em segundos desde o timestamp
        """
        return time.time() - self.timestamp

    def __str__(self) -> str:
        """String representation para debugging."""
        return (
            f"HeartbeatPayload(\n"
            f"  sink={self.sink_nid},\n"
            f"  timestamp={self.timestamp:.2f} (age: {self.age():.2f}s),\n"
            f"  signature={'<placeholder>' if self.signature == b'\\x00' * 64 else '<signed>'}\n"
            f")"
        )


def create_heartbeat_packet(
    sink_nid: NID,
    broadcast_nid: Optional[NID] = None,
    sequence: int = 0,
) -> Packet:
    """
    Cria um pacote de heartbeat.

    Args:
        sink_nid: NID do Sink que envia o heartbeat
        broadcast_nid: NID de broadcast (None = usa sink_nid)
        sequence: Número de sequência

    Returns:
        Pacote de heartbeat pronto a enviar
    """
    # Criar payload
    heartbeat_payload = HeartbeatPayload.create(sink_nid)

    # Broadcast: destination = sink_nid (todos os nodes aceitam)
    if broadcast_nid is None:
        broadcast_nid = sink_nid

    # Criar pacote
    packet = Packet.create(
        source=sink_nid,
        destination=broadcast_nid,
        msg_type=MessageType.HEARTBEAT,
        payload=heartbeat_payload.to_bytes(),
        sequence=sequence,
        ttl=1,  # Heartbeats não fazem forwarding
    )

    logger.debug(f"Heartbeat packet criado: seq={sequence}, size={packet.size()} bytes")

    return packet


def parse_heartbeat_packet(packet: Packet) -> Optional[HeartbeatPayload]:
    """
    Extrai o payload de heartbeat de um pacote.

    Args:
        packet: Pacote a parsear

    Returns:
        HeartbeatPayload se válido, None caso contrário
    """
    # Verificar tipo
    if packet.msg_type != MessageType.HEARTBEAT:
        logger.warning(
            f"Pacote não é heartbeat: type={MessageType.to_string(packet.msg_type)}"
        )
        return None

    # Parsear payload
    try:
        heartbeat = HeartbeatPayload.from_bytes(packet.payload)

        # Verificar assinatura
        if not heartbeat.verify_signature():
            logger.warning("Assinatura de heartbeat inválida")
            return None

        return heartbeat

    except Exception as e:
        logger.error(f"Erro ao parsear heartbeat: {e}")
        return None


class HeartbeatMonitor:
    """
    Monitor de heartbeats para nodes IoT.

    Mantém registo dos últimos heartbeats recebidos e deteta timeouts.
    """

    def __init__(self, timeout_count: int = 3):
        """
        Inicializa o monitor.

        Args:
            timeout_count: Número de heartbeats perdidos antes de timeout
        """
        self.timeout_count = timeout_count
        self.last_heartbeat: Optional[HeartbeatPayload] = None
        self.heartbeat_history: list[float] = []
        self.missed_count = 0

        logger.info(f"HeartbeatMonitor iniciado (timeout após {timeout_count} heartbeats)")

    def on_heartbeat_received(self, heartbeat: HeartbeatPayload):
        """
        Processa um heartbeat recebido.

        Args:
            heartbeat: Heartbeat payload recebido
        """
        self.last_heartbeat = heartbeat
        self.heartbeat_history.append(heartbeat.timestamp)
        self.missed_count = 0

        # Manter apenas últimos 10 heartbeats
        if len(self.heartbeat_history) > 10:
            self.heartbeat_history.pop(0)

        logger.debug(f"Heartbeat recebido: {heartbeat.sink_nid} (age: {heartbeat.age():.2f}s)")

    def check_timeout(self) -> bool:
        """
        Verifica se houve timeout (muitos heartbeats perdidos).

        Returns:
            True se timeout detetado, False caso contrário
        """
        if self.last_heartbeat is None:
            return False

        # Calcular tempo desde último heartbeat
        time_since_last = self.last_heartbeat.age()

        # Timeout = HEARTBEAT_INTERVAL * (timeout_count + 1)
        timeout_threshold = HEARTBEAT_INTERVAL * (self.timeout_count + 1)

        if time_since_last > timeout_threshold:
            logger.warning(
                f"Heartbeat timeout! Último há {time_since_last:.1f}s "
                f"(threshold: {timeout_threshold}s)"
            )
            return True

        return False

    def get_stats(self) -> dict:
        """
        Obtém estatísticas do monitor.

        Returns:
            Dicionário com estatísticas
        """
        if self.last_heartbeat is None:
            return {
                'last_heartbeat': None,
                'time_since_last': None,
                'total_received': 0,
                'missed_count': self.missed_count,
            }

        return {
            'last_heartbeat': self.last_heartbeat.timestamp,
            'time_since_last': self.last_heartbeat.age(),
            'total_received': len(self.heartbeat_history),
            'missed_count': self.missed_count,
            'sink_nid': str(self.last_heartbeat.sink_nid),
        }
