#!/usr/bin/env python3
"""
Sistema de fragmentação para mensagens BLE grandes.

Divide mensagens grandes em chunks que cabem no MTU do BLE
e reconstrói no lado receptor.

Formato do fragmento:
┌──────────┬──────────┬──────────┬─────────────────┐
│  Flags   │  Seq #   │  Total   │  Payload        │
│  1 byte  │  1 byte  │  1 byte  │  N bytes        │
└──────────┴──────────┴──────────┴─────────────────┘

Flags:
- Bit 0: FIRST fragment (1 = primeiro fragmento)
- Bit 1: LAST fragment (1 = último fragmento)
- Bits 2-7: Reservados

Seq #: Número do fragmento (0-255)
Total: Total de fragmentos esperados (1-255)
"""

import struct
from typing import List, Optional, Tuple
from dataclasses import dataclass

from common.utils.logger import get_logger

logger = get_logger("fragmentation")

# Tamanho máximo do payload de cada fragmento (bytes)
# Conservador para garantir que cabe no MTU mínimo do BLE (23 bytes - headers)
FRAGMENT_PAYLOAD_SIZE = 180  # 180 bytes de payload + 3 bytes de header = 183 bytes total

# Flags
FLAG_FIRST = 0x01
FLAG_LAST = 0x02


@dataclass
class Fragment:
    """Representa um fragmento de uma mensagem."""
    flags: int
    sequence: int
    total: int
    payload: bytes

    def is_first(self) -> bool:
        """Verifica se é o primeiro fragmento."""
        return (self.flags & FLAG_FIRST) != 0

    def is_last(self) -> bool:
        """Verifica se é o último fragmento."""
        return (self.flags & FLAG_LAST) != 0

    def to_bytes(self) -> bytes:
        """Serializa o fragmento para bytes."""
        return struct.pack("!BBB", self.flags, self.sequence, self.total) + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> 'Fragment':
        """Desserializa fragmento a partir de bytes."""
        if len(data) < 3:
            raise ValueError(f"Fragmento inválido: mínimo 3 bytes, recebeu {len(data)}")

        flags, sequence, total = struct.unpack("!BBB", data[:3])
        payload = data[3:]

        return cls(flags, sequence, total, payload)


def fragment_message(data: bytes) -> List[bytes]:
    """
    Divide uma mensagem em fragmentos.

    Args:
        data: Dados a fragmentar

    Returns:
        Lista de fragmentos (bytes) prontos para enviar
    """
    if len(data) <= FRAGMENT_PAYLOAD_SIZE:
        # Mensagem pequena, não precisa fragmentar
        # Enviar como fragmento único (FIRST | LAST)
        fragment = Fragment(
            flags=FLAG_FIRST | FLAG_LAST,
            sequence=0,
            total=1,
            payload=data
        )
        logger.debug(f"Mensagem pequena ({len(data)} bytes), 1 fragmento")
        return [fragment.to_bytes()]

    # Mensagem grande, fragmentar
    num_fragments = (len(data) + FRAGMENT_PAYLOAD_SIZE - 1) // FRAGMENT_PAYLOAD_SIZE
    fragments = []

    logger.info(f"Fragmentando mensagem de {len(data)} bytes em {num_fragments} fragmentos")

    for i in range(num_fragments):
        start = i * FRAGMENT_PAYLOAD_SIZE
        end = min(start + FRAGMENT_PAYLOAD_SIZE, len(data))
        payload = data[start:end]

        # Definir flags
        flags = 0
        if i == 0:
            flags |= FLAG_FIRST
        if i == num_fragments - 1:
            flags |= FLAG_LAST

        fragment = Fragment(
            flags=flags,
            sequence=i,
            total=num_fragments,
            payload=payload
        )

        fragments.append(fragment.to_bytes())
        logger.debug(f"  Fragmento {i+1}/{num_fragments}: {len(payload)} bytes, flags=0x{flags:02x}")

    return fragments


class FragmentReassembler:
    """
    Reconstrói mensagens a partir de fragmentos recebidos.

    Mantém estado dos fragmentos recebidos e reconstrói quando completo.
    """

    def __init__(self):
        """Inicializa o reassembler."""
        self.fragments: List[Optional[bytes]] = []
        self.total_fragments: Optional[int] = None
        self.received_count = 0

        logger.debug("FragmentReassembler inicializado")

    def add_fragment(self, fragment_data: bytes) -> Tuple[bool, Optional[bytes]]:
        """
        Adiciona um fragmento e tenta reconstruir a mensagem.

        Args:
            fragment_data: Dados do fragmento

        Returns:
            (is_complete, reassembled_message)
            - is_complete: True se a mensagem está completa
            - reassembled_message: Mensagem reconstruída (None se incompleta)
        """
        try:
            fragment = Fragment.from_bytes(fragment_data)
        except Exception as e:
            logger.error(f"Erro ao parsear fragmento: {e}")
            return False, None

        logger.debug(
            f"Fragmento recebido: seq={fragment.sequence}, total={fragment.total}, "
            f"payload={len(fragment.payload)} bytes, flags=0x{fragment.flags:02x}"
        )

        # Primeiro fragmento - inicializar
        if fragment.is_first():
            logger.info(f"Iniciando recepção de {fragment.total} fragmentos")
            self.fragments = [None] * fragment.total
            self.total_fragments = fragment.total
            self.received_count = 0

        # Verificar se total bate
        if self.total_fragments is None:
            logger.warning("Recebido fragmento mas não foi inicializado (falta FIRST)")
            return False, None

        if fragment.total != self.total_fragments:
            logger.error(
                f"Total de fragmentos inconsistente: esperado {self.total_fragments}, "
                f"recebido {fragment.total}"
            )
            self.reset()
            return False, None

        # Verificar sequência
        if fragment.sequence >= self.total_fragments:
            logger.error(
                f"Sequência inválida: {fragment.sequence} >= {self.total_fragments}"
            )
            return False, None

        # Armazenar fragmento
        if self.fragments[fragment.sequence] is None:
            self.fragments[fragment.sequence] = fragment.payload
            self.received_count += 1
            logger.debug(
                f"Fragmento {fragment.sequence + 1}/{self.total_fragments} armazenado "
                f"({self.received_count} de {self.total_fragments} recebidos)"
            )

        # Verificar se está completo
        if self.received_count == self.total_fragments:
            # Reconstruir mensagem
            reassembled = b''.join(self.fragments)
            logger.info(
                f"✅ Mensagem reconstruída: {len(reassembled)} bytes "
                f"({self.total_fragments} fragmentos)"
            )

            self.reset()
            return True, reassembled

        return False, None

    def reset(self):
        """Reset do reassembler."""
        self.fragments = []
        self.total_fragments = None
        self.received_count = 0
        logger.debug("FragmentReassembler resetado")
