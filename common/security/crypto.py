"""
Funções criptográficas para a rede IoT.

Implementa HMAC-SHA256 para garantir integridade e autenticidade dos pacotes.
"""

import hmac
import hashlib
from typing import Optional

# Chave compartilhada para HMAC (32 bytes)
# Em produção, isto seria derivado de certificados X.509 ou um protocolo de troca de chaves
# Por agora, usamos uma chave hardcoded para testes
DEFAULT_HMAC_KEY = b'IoT_Network_Shared_Secret_Key_32'  # 32 bytes


def calculate_hmac(data: bytes, key: Optional[bytes] = None) -> bytes:
    """
    Calcula HMAC-SHA256 dos dados fornecidos.

    Args:
        data: Dados para calcular o MAC
        key: Chave HMAC (32 bytes). Se None, usa a chave padrão.

    Returns:
        MAC de 32 bytes (HMAC-SHA256)

    Raises:
        ValueError: Se a chave não tiver 32 bytes
    """
    if key is None:
        key = DEFAULT_HMAC_KEY

    if len(key) != 32:
        raise ValueError(f"Chave HMAC deve ter 32 bytes, recebeu {len(key)}")

    # Calcular HMAC-SHA256
    mac = hmac.new(key, data, hashlib.sha256).digest()

    return mac


def verify_hmac(data: bytes, mac: bytes, key: Optional[bytes] = None) -> bool:
    """
    Verifica se o MAC fornecido corresponde aos dados.

    Args:
        data: Dados originais
        mac: MAC a verificar (32 bytes)
        key: Chave HMAC (32 bytes). Se None, usa a chave padrão.

    Returns:
        True se o MAC é válido, False caso contrário

    Raises:
        ValueError: Se o MAC não tiver 32 bytes ou chave não tiver 32 bytes
    """
    if len(mac) != 32:
        raise ValueError(f"MAC deve ter 32 bytes, recebeu {len(mac)}")

    if key is None:
        key = DEFAULT_HMAC_KEY

    if len(key) != 32:
        raise ValueError(f"Chave HMAC deve ter 32 bytes, recebeu {len(key)}")

    # Calcular MAC esperado
    expected_mac = calculate_hmac(data, key)

    # Comparação segura contra timing attacks
    return hmac.compare_digest(mac, expected_mac)


def set_hmac_key(key: bytes):
    """
    Define uma nova chave HMAC global.

    ATENÇÃO: Esta função é para testes. Em produção, a chave
    deve ser derivada de certificados X.509.

    Args:
        key: Nova chave HMAC (32 bytes)

    Raises:
        ValueError: Se a chave não tiver 32 bytes
    """
    global DEFAULT_HMAC_KEY

    if len(key) != 32:
        raise ValueError(f"Chave HMAC deve ter 32 bytes, recebeu {len(key)}")

    DEFAULT_HMAC_KEY = key
