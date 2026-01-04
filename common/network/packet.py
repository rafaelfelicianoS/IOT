"""
Formato e manipulação de pacotes da rede IoT.

Estrutura do pacote:
┌────────────┬────────────┬──────────┬─────┬──────────┬─────────┬─────────┐
│ Source NID │ Dest NID   │   Type   │ TTL │ Sequence │   MAC   │ Payload │
│  16 bytes  │  16 bytes  │  1 byte  │ 1 B │ 4 bytes  │ 32 bytes│ N bytes │
└────────────┴────────────┴──────────┴─────┴──────────┴─────────┴─────────┘
"""

import struct
from typing import Optional
from dataclasses import dataclass

from common.utils.nid import NID
from common.utils.constants import (
    MessageType,
    NID_SIZE,
    TYPE_SIZE,
    TTL_SIZE,
    SEQUENCE_SIZE,
    MAC_SIZE,
    PACKET_HEADER_SIZE,
    DEFAULT_TTL,
)
from common.security.crypto import calculate_hmac, verify_hmac


@dataclass
class Packet:
    """
    Representa um pacote da rede IoT.

    Attributes:
        source: NID do dispositivo de origem
        destination: NID do dispositivo de destino
        msg_type: Tipo de mensagem (ver MessageType)
        ttl: Time-to-live (decrementado a cada hop)
        sequence: Número de sequência (para prevenção de replay)
        mac: Message Authentication Code (HMAC-SHA256)
        payload: Dados da mensagem
    """

    source: NID
    destination: NID
    msg_type: int
    ttl: int
    sequence: int
    mac: bytes
    payload: bytes

    def __post_init__(self):
        """Validação após inicialização."""
        if not isinstance(self.source, NID):
            raise TypeError("source deve ser um NID")
        if not isinstance(self.destination, NID):
            raise TypeError("destination deve ser um NID")

        if not (0 <= self.ttl <= 255):
            raise ValueError(f"TTL deve estar entre 0 e 255, recebeu {self.ttl}")

        if len(self.mac) != MAC_SIZE:
            raise ValueError(f"MAC deve ter {MAC_SIZE} bytes, recebeu {len(self.mac)}")

    @classmethod
    def create(
        cls,
        source: NID,
        destination: NID,
        msg_type: int,
        payload: bytes,
        sequence: int = 0,
        ttl: int = DEFAULT_TTL,
        mac: bytes = b'\x00' * MAC_SIZE,
    ) -> 'Packet':
        """
        Cria um novo pacote.

        Args:
            source: NID de origem
            destination: NID de destino
            msg_type: Tipo de mensagem
            payload: Dados da mensagem
            sequence: Número de sequência
            ttl: Time-to-live
            mac: MAC (será calculado depois, placeholder por agora)

        Returns:
            Novo pacote
        """
        return cls(
            source=source,
            destination=destination,
            msg_type=msg_type,
            ttl=ttl,
            sequence=sequence,
            mac=mac,
            payload=payload,
        )

    def to_bytes(self) -> bytes:
        """
        Serializa o pacote para bytes.

        Returns:
            Representação binária do pacote
        """
        # Header format: source(16) + dest(16) + type(1) + ttl(1) + seq(4) + mac(32)
        header = struct.pack(
            f"!{NID_SIZE}s{NID_SIZE}sBBI{MAC_SIZE}s",
            self.source.to_bytes(),
            self.destination.to_bytes(),
            self.msg_type,
            self.ttl,
            self.sequence,
            self.mac,
        )

        return header + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Packet':
        """
        Desserializa um pacote a partir de bytes.

        Args:
            data: Dados binários do pacote

        Returns:
            Pacote desserializado

        Raises:
            ValueError: Se os dados forem inválidos
        """
        if len(data) < PACKET_HEADER_SIZE:
            raise ValueError(
                f"Dados insuficientes para header. "
                f"Esperado mínimo {PACKET_HEADER_SIZE}, recebeu {len(data)}"
            )

        # Unpack header
        header_format = f"!{NID_SIZE}s{NID_SIZE}sBBI{MAC_SIZE}s"
        header_data = data[:PACKET_HEADER_SIZE]
        payload_data = data[PACKET_HEADER_SIZE:]

        (
            source_bytes,
            dest_bytes,
            msg_type,
            ttl,
            sequence,
            mac,
        ) = struct.unpack(header_format, header_data)

        source = NID.from_bytes(source_bytes)
        destination = NID.from_bytes(dest_bytes)

        return cls(
            source=source,
            destination=destination,
            msg_type=msg_type,
            ttl=ttl,
            sequence=sequence,
            mac=mac,
            payload=payload_data,
        )

    def decrement_ttl(self) -> bool:
        """
        Decrementa o TTL do pacote.

        Returns:
            True se TTL ainda é válido (> 0), False se expirou

        Raises:
            ValueError: Se TTL já está em 0
        """
        if self.ttl == 0:
            return False

        self.ttl -= 1
        return self.ttl > 0

    def get_header_for_mac(self) -> bytes:
        """
        Obtém o header sem o MAC para cálculo do MAC.

        Returns:
            Header sem o campo MAC
        """
        return struct.pack(
            f"!{NID_SIZE}s{NID_SIZE}sBBI",
            self.source.to_bytes(),
            self.destination.to_bytes(),
            self.msg_type,
            self.ttl,
            self.sequence,
        )

    def update_mac(self, new_mac: bytes):
        """
        Atualiza o MAC do pacote.

        Args:
            new_mac: Novo MAC

        Raises:
            ValueError: Se o MAC não tiver o tamanho correto
        """
        if len(new_mac) != MAC_SIZE:
            raise ValueError(f"MAC deve ter {MAC_SIZE} bytes")
        self.mac = new_mac

    def calculate_and_set_mac(self, key: Optional[bytes] = None):
        """
        Calcula e define o MAC do pacote.

        O MAC é calculado sobre o header (sem o campo MAC) + payload.

        Args:
            key: Chave HMAC (32 bytes). Se None, usa a chave padrão.

        Raises:
            ValueError: Se a chave não tiver 32 bytes
        """
        # Dados para calcular MAC: header sem MAC + payload
        data = self.get_header_for_mac() + self.payload

        # Calcular MAC
        mac = calculate_hmac(data, key)

        # Atualizar MAC do pacote
        self.mac = mac

    def verify_mac(self, key: Optional[bytes] = None) -> bool:
        """
        Verifica se o MAC do pacote é válido.

        Args:
            key: Chave HMAC (32 bytes). Se None, usa a chave padrão.

        Returns:
            True se o MAC é válido, False caso contrário

        Raises:
            ValueError: Se a chave não tiver 32 bytes
        """
        # Dados para verificar MAC: header sem MAC + payload
        data = self.get_header_for_mac() + self.payload

        return verify_hmac(data, self.mac, key)

    def size(self) -> int:
        """
        Retorna o tamanho total do pacote em bytes.

        Returns:
            Tamanho total
        """
        return PACKET_HEADER_SIZE + len(self.payload)

    def __str__(self) -> str:
        """String representation para debugging."""
        return (
            f"Packet(\n"
            f"  src={self.source},\n"
            f"  dst={self.destination},\n"
            f"  type={MessageType.to_string(self.msg_type)},\n"
            f"  ttl={self.ttl},\n"
            f"  seq={self.sequence},\n"
            f"  payload_size={len(self.payload)} bytes\n"
            f")"
        )

    def __repr__(self) -> str:
        return self.__str__()
