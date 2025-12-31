#!/usr/bin/env python3
"""
Protocolo de Autenticação Mútua com Certificados X.509.

Este módulo implementa o handshake de autenticação entre dois dispositivos:
1. Troca de certificados
2. Validação dos certificados
3. Challenge-Response (prova de posse da chave privada)
4. Estabelecimento de sessão autenticada

Formato dos pacotes de autenticação:
┌──────────┬─────────────────────┬──────────────┐
│  Type    │  Payload            │  Length      │
│  1 byte  │  Variable           │  Variable    │
└──────────┴─────────────────────┴──────────────┘

Tipos de pacotes:
- 0x01: CERT_OFFER   - Enviar certificado
- 0x02: CHALLENGE    - Enviar challenge (32 bytes random)
- 0x03: RESPONSE     - Resposta ao challenge (assinatura)
- 0x04: AUTH_SUCCESS - Autenticação bem sucedida
- 0x05: AUTH_FAILED  - Autenticação falhou
"""

import os
import struct
from enum import IntEnum
from typing import Optional, Tuple
from dataclasses import dataclass

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from common.utils.nid import NID
from common.utils.logger import get_logger
from common.security.certificate_manager import CertificateManager

logger = get_logger("auth")

# Tamanho do challenge (bytes)
CHALLENGE_SIZE = 32


class AuthMessageType(IntEnum):
    """Tipos de mensagens do protocolo de autenticação."""
    CERT_OFFER = 0x01
    CHALLENGE = 0x02
    RESPONSE = 0x03
    AUTH_SUCCESS = 0x04
    AUTH_FAILED = 0x05


class AuthState(IntEnum):
    """Estados do processo de autenticação."""
    IDLE = 0                    # Ainda não iniciou
    CERT_SENT = 1               # Certificado enviado, aguardando certificado do peer
    CERT_RECEIVED = 2           # Certificado do peer recebido e validado
    CHALLENGE_SENT = 3          # Challenge enviado, aguardando response
    CHALLENGE_RECEIVED = 4      # Challenge recebido, response enviada
    AUTHENTICATED = 5           # Autenticação completa e bem sucedida
    FAILED = 6                  # Autenticação falhou


@dataclass
class AuthMessage:
    """Mensagem do protocolo de autenticação."""
    msg_type: AuthMessageType
    payload: bytes

    def to_bytes(self) -> bytes:
        """Serializa a mensagem para bytes."""
        # Format: type(1) + payload_length(2) + payload(N)
        return struct.pack("!BH", self.msg_type, len(self.payload)) + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> 'AuthMessage':
        """Desserializa mensagem a partir de bytes."""
        if len(data) < 3:
            raise ValueError(f"Dados insuficientes para AuthMessage: {len(data)} bytes")

        msg_type, payload_length = struct.unpack("!BH", data[:3])
        payload = data[3:3 + payload_length]

        if len(payload) != payload_length:
            raise ValueError(
                f"Payload incompleto: esperado {payload_length}, "
                f"recebido {len(payload)}"
            )

        return cls(AuthMessageType(msg_type), payload)

    def __str__(self) -> str:
        """String representation."""
        return (
            f"AuthMessage(type={AuthMessageType(self.msg_type).name}, "
            f"payload={len(self.payload)} bytes)"
        )


class AuthenticationProtocol:
    """
    Protocolo de autenticação mútua com certificados X.509.

    Implementa o handshake completo entre dois dispositivos.
    """

    def __init__(self, cert_manager: CertificateManager):
        """
        Inicializa o protocolo de autenticação.

        Args:
            cert_manager: Certificate Manager inicializado
        """
        self.cert_manager = cert_manager
        self.state = AuthState.IDLE

        # Dados do peer
        self.peer_cert: Optional[x509.Certificate] = None
        self.peer_nid: Optional[NID] = None
        self.peer_is_sink: bool = False

        # Challenge-Response
        self.outgoing_challenge: Optional[bytes] = None  # Challenge que enviámos
        self.incoming_challenge: Optional[bytes] = None  # Challenge que recebemos

        logger.info(f"AuthenticationProtocol inicializado para {cert_manager.device_nid}")

    def start_authentication(self) -> bytes:
        """
        Inicia o processo de autenticação enviando o certificado.

        Returns:
            Mensagem CERT_OFFER serializada para enviar ao peer
        """
        logger.info("🔐 Iniciando autenticação - enviando certificado...")

        # Obter certificado em formato PEM
        cert_bytes = self.cert_manager.get_device_certificate_bytes()

        # Criar mensagem
        msg = AuthMessage(AuthMessageType.CERT_OFFER, cert_bytes)

        # Atualizar estado
        self.state = AuthState.CERT_SENT

        logger.info(f"   Certificado: {len(cert_bytes)} bytes")
        logger.debug(f"   Estado: IDLE → CERT_SENT")

        return msg.to_bytes()

    def handle_cert_offer(self, cert_pem: bytes) -> Tuple[bool, Optional[bytes]]:
        """
        Processa certificado recebido do peer.

        Args:
            cert_pem: Certificado em formato PEM

        Returns:
            (success, response_message)
            - success: True se certificado é válido
            - response_message: Próxima mensagem a enviar (CHALLENGE ou AUTH_FAILED)
        """
        logger.info("📜 Certificado do peer recebido - validando...")

        try:
            # Parsear certificado
            peer_cert = x509.load_pem_x509_certificate(cert_pem, backend=default_backend())

            # Validar certificado
            if not self.cert_manager.validate_certificate(peer_cert):
                logger.error("❌ Certificado do peer é inválido!")
                self.state = AuthState.FAILED
                msg = AuthMessage(AuthMessageType.AUTH_FAILED, b"Invalid certificate")
                return False, msg.to_bytes()

            # Extrair informações
            self.peer_cert = peer_cert
            self.peer_nid = self.cert_manager.extract_nid_from_cert(peer_cert)
            self.peer_is_sink = self.cert_manager.is_sink_certificate(peer_cert)

            logger.info(f"✅ Certificado válido!")
            logger.info(f"   Peer NID: {self.peer_nid}")
            logger.info(f"   Peer tipo: {'SINK' if self.peer_is_sink else 'NODE'}")

            # Atualizar estado
            self.state = AuthState.CERT_RECEIVED

            # Gerar e enviar challenge
            self.outgoing_challenge = os.urandom(CHALLENGE_SIZE)
            msg = AuthMessage(AuthMessageType.CHALLENGE, self.outgoing_challenge)

            logger.info(f"🎲 Enviando challenge: {self.outgoing_challenge.hex()[:32]}...")
            logger.debug(f"   Estado: CERT_RECEIVED → CHALLENGE_SENT")
            self.state = AuthState.CHALLENGE_SENT

            return True, msg.to_bytes()

        except Exception as e:
            logger.error(f"❌ Erro ao processar certificado: {e}")
            self.state = AuthState.FAILED
            msg = AuthMessage(AuthMessageType.AUTH_FAILED, str(e).encode())
            return False, msg.to_bytes()

    def handle_challenge(self, challenge: bytes) -> bytes:
        """
        Processa challenge recebido e envia response (assinatura).

        Args:
            challenge: Challenge recebido (32 bytes)

        Returns:
            Mensagem RESPONSE serializada
        """
        logger.info("🎲 Challenge recebido - gerando response...")

        if len(challenge) != CHALLENGE_SIZE:
            logger.error(f"❌ Challenge com tamanho inválido: {len(challenge)} bytes")
            raise ValueError(f"Challenge deve ter {CHALLENGE_SIZE} bytes")

        # Guardar challenge
        self.incoming_challenge = challenge
        logger.debug(f"   Challenge: {challenge.hex()[:32]}...")

        # Assinar challenge com chave privada
        signature = self.cert_manager.sign_data(challenge)

        # Criar mensagem de response
        msg = AuthMessage(AuthMessageType.RESPONSE, signature)

        logger.info(f"✍️  Response gerada: {len(signature)} bytes")
        logger.debug(f"   Estado: CHALLENGE_RECEIVED")
        self.state = AuthState.CHALLENGE_RECEIVED

        return msg.to_bytes()

    def handle_response(self, signature: bytes) -> Tuple[bool, bytes]:
        """
        Processa response ao challenge e verifica assinatura.

        Args:
            signature: Assinatura do challenge

        Returns:
            (authenticated, response_message)
            - authenticated: True se assinatura é válida
            - response_message: AUTH_SUCCESS ou AUTH_FAILED
        """
        logger.info("🔍 Response recebida - verificando assinatura...")

        if self.outgoing_challenge is None:
            logger.error("❌ Nenhum challenge foi enviado!")
            self.state = AuthState.FAILED
            msg = AuthMessage(AuthMessageType.AUTH_FAILED, b"No challenge sent")
            return False, msg.to_bytes()

        if self.peer_cert is None:
            logger.error("❌ Certificado do peer não está carregado!")
            self.state = AuthState.FAILED
            msg = AuthMessage(AuthMessageType.AUTH_FAILED, b"No peer certificate")
            return False, msg.to_bytes()

        # Verificar assinatura
        is_valid = self.cert_manager.verify_signature(
            self.outgoing_challenge,
            signature,
            self.peer_cert
        )

        if is_valid:
            logger.info("✅ Assinatura válida - AUTENTICAÇÃO BEM SUCEDIDA!")
            logger.info(f"   Peer {self.peer_nid} autenticado com sucesso")
            self.state = AuthState.AUTHENTICATED

            msg = AuthMessage(AuthMessageType.AUTH_SUCCESS, b"")
            return True, msg.to_bytes()
        else:
            logger.error("❌ Assinatura inválida - AUTENTICAÇÃO FALHOU!")
            self.state = AuthState.FAILED

            msg = AuthMessage(AuthMessageType.AUTH_FAILED, b"Invalid signature")
            return False, msg.to_bytes()

    def handle_auth_success(self) -> bool:
        """
        Processa mensagem de sucesso do peer.

        Returns:
            True (autenticação completa)
        """
        logger.info("✅ Peer confirmou autenticação bem sucedida!")
        self.state = AuthState.AUTHENTICATED
        return True

    def handle_auth_failed(self, reason: bytes) -> bool:
        """
        Processa mensagem de falha do peer.

        Args:
            reason: Motivo da falha

        Returns:
            False (autenticação falhou)
        """
        reason_str = reason.decode('utf-8', errors='replace')
        logger.error(f"❌ Peer rejeitou autenticação: {reason_str}")
        self.state = AuthState.FAILED
        return False

    def process_message(self, data: bytes) -> Tuple[bool, Optional[bytes]]:
        """
        Processa uma mensagem recebida do protocolo de autenticação.

        Args:
            data: Dados recebidos

        Returns:
            (continue_auth, response_message)
            - continue_auth: True se deve continuar, False se terminou (sucesso ou falha)
            - response_message: Mensagem a enviar como resposta (None se não há resposta)
        """
        try:
            # Parsear mensagem
            msg = AuthMessage.from_bytes(data)
            logger.debug(f"📨 Recebido: {msg}")

            # Processar de acordo com o tipo
            if msg.msg_type == AuthMessageType.CERT_OFFER:
                success, response = self.handle_cert_offer(msg.payload)
                return success, response

            elif msg.msg_type == AuthMessageType.CHALLENGE:
                response = self.handle_challenge(msg.payload)
                return True, response

            elif msg.msg_type == AuthMessageType.RESPONSE:
                authenticated, response = self.handle_response(msg.payload)
                return not authenticated, response  # continuar se falhou

            elif msg.msg_type == AuthMessageType.AUTH_SUCCESS:
                self.handle_auth_success()
                return False, None  # Terminado com sucesso

            elif msg.msg_type == AuthMessageType.AUTH_FAILED:
                self.handle_auth_failed(msg.payload)
                return False, None  # Terminado com falha

            else:
                logger.error(f"❌ Tipo de mensagem desconhecido: {msg.msg_type}")
                return False, None

        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {e}")
            self.state = AuthState.FAILED
            return False, None

    def is_authenticated(self) -> bool:
        """
        Verifica se a autenticação foi bem sucedida.

        Returns:
            True se autenticado, False caso contrário
        """
        return self.state == AuthState.AUTHENTICATED

    def get_peer_info(self) -> Optional[dict]:
        """
        Obtém informações do peer autenticado.

        Returns:
            Dicionário com informações do peer, ou None se não autenticado
        """
        if not self.is_authenticated():
            return None

        # Incluir session key se disponível
        info = {
            'nid': self.peer_nid,
            'is_sink': self.peer_is_sink,
            'certificate': self.peer_cert,
        }

        # Derivar session key
        session_key = self.derive_session_key()
        if session_key:
            info['session_key'] = session_key

        return info

    def derive_session_key(self) -> Optional[bytes]:
        """
        Deriva uma session key a partir do handshake de autenticação.

        Usa ECDH (Elliptic Curve Diffie-Hellman) para derivar uma chave
        compartilhada a partir das chaves públicas dos dois peers.

        Returns:
            Session key de 32 bytes ou None se não disponível
        """
        if not self.is_authenticated():
            logger.warning("Tentativa de derivar session key sem estar autenticado")
            return None

        if not self.peer_cert or not self.cert_manager.device_private_key:
            logger.error("Certificados não disponíveis para derivar session key")
            return None

        try:
            from cryptography.hazmat.primitives import hashes
            from cryptography.hazmat.primitives.kdf.hkdf import HKDF
            from cryptography.hazmat.primitives.asymmetric import ec

            # Obter chave pública do peer
            peer_public_key = self.peer_cert.public_key()

            # Realizar ECDH
            shared_secret = self.cert_manager.device_private_key.exchange(
                ec.ECDH(),
                peer_public_key
            )

            # Derivar session key usando HKDF
            kdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,
                salt=None,
                info=b'IoT Network Session Key'
            )

            session_key = kdf.derive(shared_secret)

            logger.debug(f"🔑 Session key derivada: {len(session_key)} bytes")
            return session_key

        except Exception as e:
            logger.error(f"Erro ao derivar session key: {e}")
            return None

    def reset(self):
        """Reset do protocolo para nova autenticação."""
        self.state = AuthState.IDLE
        self.peer_cert = None
        self.peer_nid = None
        self.peer_is_sink = False
        self.outgoing_challenge = None
        self.incoming_challenge = None

        logger.debug("🔄 Protocolo de autenticação resetado")
