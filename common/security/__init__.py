"""Security module for IoT network."""

from common.security.certificate_manager import CertificateManager
from common.security.authentication import AuthenticationProtocol, AuthMessage, AuthMessageType, AuthState

try:
    from common.security.mac import compute_packet_mac, verify_packet_mac
    _has_mac = True
except ImportError:
    _has_mac = False

try:
    from common.security.replay_protection import ReplayProtection
    _has_replay = True
except ImportError:
    _has_replay = False

__all__ = ['CertificateManager', 'AuthenticationProtocol', 'AuthMessage', 'AuthMessageType', 'AuthState']

if _has_mac:
    __all__.extend(['compute_packet_mac', 'verify_packet_mac'])

if _has_replay:
    __all__.append('ReplayProtection')
