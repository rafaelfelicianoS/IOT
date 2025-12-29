"""
Módulo de segurança para a rede IoT.

Fornece funcionalidades criptográficas como HMAC, verificação de integridade,
proteção contra replay attacks, e futuramente autenticação via certificados X.509.
"""

from common.security.crypto import calculate_hmac, verify_hmac
from common.security.replay_protection import ReplayProtection

__all__ = ['calculate_hmac', 'verify_hmac', 'ReplayProtection']
