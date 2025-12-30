"""
Módulo de segurança para a rede IoT.

Fornece funcionalidades criptográficas:
- HMAC-SHA256 para integridade de pacotes
- Proteção contra replay attacks
- Certificados X.509 e autenticação mútua
"""

# Crypto (HMAC)
from common.security.crypto import calculate_hmac, verify_hmac

# Replay Protection
from common.security.replay_protection import ReplayProtection

# X.509 Certificates & Authentication
from common.security.certificate_manager import CertificateManager
from common.security.authentication import (
    AuthenticationProtocol,
    AuthMessage,
    AuthMessageType,
    AuthState
)
from common.security.auth_handler import AuthenticationHandler

__all__ = [
    # Crypto
    'calculate_hmac',
    'verify_hmac',
    # Replay Protection
    'ReplayProtection',
    # X.509 & Authentication
    'CertificateManager',
    'AuthenticationProtocol',
    'AuthMessage',
    'AuthMessageType',
    'AuthState',
    'AuthenticationHandler',
]
