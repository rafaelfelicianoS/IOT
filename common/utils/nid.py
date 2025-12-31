"""
Gestão de Network Identifiers (NIDs).

NIDs são UUIDs de 128 bits usados para identificar dispositivos na rede.
"""

import uuid
from typing import Union


class NID:
    """
    Network Identifier - identificador único de 128 bits para dispositivos.

    Wrapper sobre UUID para facilitar conversões e validações.
    """

    def __init__(self, value: Union[str, bytes, uuid.UUID]):
        """
        Inicializa um NID.

        Args:
            value: UUID como string, bytes ou objeto UUID

        Raises:
            ValueError: Se o valor não for um UUID válido
        """
        if isinstance(value, uuid.UUID):
            self._uuid = value
        elif isinstance(value, str):
            self._uuid = uuid.UUID(value)
        elif isinstance(value, bytes):
            if len(value) != 16:
                raise ValueError(f"NID bytes deve ter 16 bytes, recebeu {len(value)}")
            self._uuid = uuid.UUID(bytes=value)
        else:
            raise ValueError(f"Tipo inválido para NID: {type(value)}")

    @classmethod
    def generate(cls) -> 'NID':
        """
        Gera um novo NID aleatório (UUID v4).

        Returns:
            Novo NID
        """
        return cls(uuid.uuid4())

    @classmethod
    def from_hex(cls, hex_string: str) -> 'NID':
        """
        Cria NID a partir de string hexadecimal.

        Args:
            hex_string: String hexadecimal (com ou sem hífens)

        Returns:
            NID criado
        """
        return cls(uuid.UUID(hex=hex_string))

    @classmethod
    def from_bytes(cls, data: bytes) -> 'NID':
        """
        Cria NID a partir de bytes.

        Args:
            data: 16 bytes

        Returns:
            NID criado
        """
        return cls(uuid.UUID(bytes=data))

    def to_bytes(self) -> bytes:
        """
        Converte NID para bytes (16 bytes).

        Returns:
            Representação em bytes
        """
        return self._uuid.bytes

    def to_hex(self) -> str:
        """
        Converte NID para string hexadecimal (sem hífens).

        Returns:
            String hexadecimal
        """
        return self._uuid.hex

    def to_string(self) -> str:
        """
        Converte NID para string UUID formatada (com hífens).

        Returns:
            String UUID (formato: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)
        """
        return str(self._uuid)

    def to_short_string(self) -> str:
        """
        Converte NID para string curta (primeiros 8 hex chars).

        Usado para nomes de ficheiros e identificação curta.

        Returns:
            String hexadecimal curta (ex: 'af04ea89')
        """
        return self.to_hex()[:8]

    def __str__(self) -> str:
        """String representation (formato curto para display)."""
        # Mostrar apenas os primeiros 8 caracteres para brevidade
        return self.to_hex()[:8] + "..."

    def __repr__(self) -> str:
        """Representação completa."""
        return f"NID({self.to_string()})"

    def __eq__(self, other) -> bool:
        """Igualdade entre NIDs."""
        if isinstance(other, NID):
            return self._uuid == other._uuid
        return False

    def __hash__(self) -> int:
        """Hash do NID (para usar em dicts/sets)."""
        return hash(self._uuid)

    def __bytes__(self) -> bytes:
        """Converte para bytes."""
        return self.to_bytes()


def is_valid_nid(value: Union[str, bytes]) -> bool:
    """
    Verifica se um valor é um NID válido.

    Args:
        value: Valor a verificar

    Returns:
        True se for um NID válido
    """
    try:
        NID(value)
        return True
    except (ValueError, TypeError):
        return False
