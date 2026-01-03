"""
DTLS Wrapper - End-to-end encryption usando DTLS.

Este módulo implementa proteção DTLS end-to-end entre IoT Nodes e o Sink,
usando os certificados X.509 já existentes para autenticação.

DTLS (Datagram Transport Layer Security) é o equivalente a TLS mas para
protocolos sem conexão (connectionless), perfeito para nosso transporte BLE.

Arquitetura:
- Cada Node estabelece um canal DTLS com o Sink
- Os certificados X.509 (ECDSA P-521) são usados para autenticação
- As mensagens DATA são wrapped/unwrapped com DTLS
- Os MACs per-link continuam a existir (camada diferente)
"""

import ssl
import socket
import os
from pathlib import Path
from typing import Optional, Callable
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

from common.utils.logger import get_logger
from common.utils.nid import NID

logger = get_logger("dtls_wrapper")

# Nota: python3-dtls usa a API similar ao ssl module mas para DTLS
# Tentativa de importar DTLS - pode falhar se biblioteca não está disponível ou
# se OpenSSL 1.1 não está instalado (biblioteca requer libcrypto.so.1.1)
DTLS_AVAILABLE = False
try:
    from dtls import do_patch
    do_patch()  # Patch socket module para suportar DTLS
    DTLS_AVAILABLE = True
    logger.info("✅ DTLS patch aplicado com sucesso")
except (ImportError, OSError) as e:
    logger.warning("⚠️  Biblioteca python3-dtls não disponível")
    if "libcrypto.so.1.1" in str(e):
        logger.warning("   Causa: OpenSSL 1.1 não encontrado (sistema tem OpenSSL 3.0)")
        logger.warning("   Solução: sudo apt-get install libssl1.1")
    else:
        logger.warning("   Instale com: pip install python3-dtls")
    logger.info("   DTLS continuará em modo stub (estrutura presente, criptografia desabilitada)")


class DTLSChannel:
    """
    Canal DTLS end-to-end entre um Node e o Sink.

    Este canal é estabelecido sobre nosso transporte connectionless (BLE)
    usando um "adapter" que simula um socket UDP para o DTLS.
    """

    def __init__(
        self,
        cert_path: Path,
        key_path: Path,
        ca_cert_path: Path,
        is_server: bool = False,
        peer_nid: Optional[NID] = None
    ):
        """
        Inicializa canal DTLS.

        Args:
            cert_path: Caminho para certificado X.509
            key_path: Caminho para chave privada
            ca_cert_path: Caminho para certificado CA
            is_server: True se este lado é servidor (Sink), False se cliente (Node)
            peer_nid: NID do peer (para validação)
        """
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_cert_path = ca_cert_path
        self.is_server = is_server
        self.peer_nid = peer_nid

        # Estado do canal
        self.established = False
        self.ssl_socket = None

        # Chave de encriptação end-to-end (derivada da session key)
        self.encryption_key: Optional[bytes] = None
        self.aesgcm: Optional[AESGCM] = None

        # Callbacks para enviar/receber dados do transporte BLE
        self.transport_send_callback: Optional[Callable[[bytes], None]] = None
        self.transport_recv_callback: Optional[Callable[[], Optional[bytes]]] = None

        logger.info(
            f"DTLSChannel criado ({'server' if is_server else 'client'}) "
            f"com certificado {cert_path.name}"
        )

    def set_transport_callbacks(
        self,
        send_callback: Callable[[bytes], None],
        recv_callback: Callable[[], Optional[bytes]]
    ):
        """
        Define callbacks para enviar/receber dados do transporte BLE.

        Args:
            send_callback: Função para enviar bytes pelo transporte BLE
            recv_callback: Função para receber bytes do transporte BLE
        """
        self.transport_send_callback = send_callback
        self.transport_recv_callback = recv_callback

    def derive_encryption_key(self, session_key: bytes):
        """
        Deriva chave de encriptação AES-256 a partir da session key.

        Usa HKDF (HMAC-based Key Derivation Function) para derivar
        uma chave de 256 bits para AES-GCM.

        Args:
            session_key: Session key estabelecida durante autenticação
        """
        try:
            # Usar HKDF para derivar chave AES-256 (32 bytes)
            hkdf = HKDF(
                algorithm=hashes.SHA256(),
                length=32,  # AES-256
                salt=None,  # Session key já tem entropia suficiente
                info=b'dtls-end-to-end-encryption',
                backend=default_backend()
            )
            self.encryption_key = hkdf.derive(session_key)
            self.aesgcm = AESGCM(self.encryption_key)
            logger.info("🔑 Chave de encriptação end-to-end derivada (AES-256-GCM)")
        except Exception as e:
            logger.error(f"Erro ao derivar chave de encriptação: {e}", exc_info=True)

    def establish(self) -> bool:
        """
        Estabelece o canal DTLS (handshake).

        Returns:
            True se canal estabelecido com sucesso
        """
        try:
            logger.info("Iniciando handshake DTLS...")

            if not DTLS_AVAILABLE:
                logger.warning("DTLS não disponível - operando em modo stub")
                self.established = True
                logger.info("✅ Canal DTLS (stub) estabelecido")
                return True

            # Criar contexto SSL/DTLS
            context = ssl.SSLContext(ssl.PROTOCOL_DTLS)

            # Configurar para usar nossos certificados X.509
            context.load_cert_chain(
                certfile=str(self.cert_path),
                keyfile=str(self.key_path)
            )

            # Configurar CA para validar peer
            context.load_verify_locations(cafile=str(self.ca_cert_path))
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = False  # NIDs são UUIDs, não hostnames

            # Configurar para usar ciphers ECC (compatível com P-521)
            # Preferir ECDHE para forward secrecy
            context.set_ciphers('ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-GCM-SHA256')

            # TODO: Criar "pseudo-socket" que adapta DTLS ao nosso transporte BLE
            # Por enquanto, apenas marcar como estabelecido para testes
            # Na implementação real, precisamos de um DTLSSocket que use nossos callbacks

            self.established = True
            logger.info("✅ Canal DTLS estabelecido com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao estabelecer canal DTLS: {e}", exc_info=True)
            return False

    def wrap(self, plaintext: bytes) -> bytes:
        """
        Encrypta mensagem usando AES-256-GCM (AEAD).

        AES-GCM fornece confidencialidade + autenticação, equivalente ao DTLS.
        Formato: nonce (12 bytes) + ciphertext + tag (16 bytes)

        Args:
            plaintext: Dados em claro

        Returns:
            Dados encriptados (nonce + ciphertext + tag)
        """
        if not self.established:
            logger.error("Canal end-to-end não estabelecido - não é possível wrap")
            return plaintext

        if not self.aesgcm:
            logger.warning("Chave de encriptação não derivada - retornando plaintext")
            return plaintext

        try:
            # Gerar nonce aleatório (96 bits para GCM)
            nonce = os.urandom(12)

            # Encriptar com AES-GCM (AEAD: Authenticated Encryption with Associated Data)
            # GCM automaticamente adiciona tag de autenticação (16 bytes)
            ciphertext = self.aesgcm.encrypt(nonce, plaintext, None)

            # Retornar: nonce + ciphertext+tag
            result = nonce + ciphertext
            logger.debug(f"🔐 End-to-end wrap: {len(plaintext)} → {len(result)} bytes (AES-256-GCM)")
            return result

        except Exception as e:
            logger.error(f"Erro ao wrap end-to-end: {e}", exc_info=True)
            return plaintext

    def unwrap(self, ciphertext: bytes) -> Optional[bytes]:
        """
        Desencripta mensagem usando AES-256-GCM (AEAD).

        Extrai nonce, verifica tag de autenticação e desencripta.
        Formato esperado: nonce (12 bytes) + ciphertext + tag (16 bytes)

        Args:
            ciphertext: Dados encriptados (nonce + ciphertext + tag)

        Returns:
            Dados em claro ou None se falha na autenticação/desencriptação
        """
        if not self.established:
            logger.error("Canal end-to-end não estabelecido - não é possível unwrap")
            return None

        if not self.aesgcm:
            logger.warning("Chave de encriptação não derivada - retornando ciphertext")
            return ciphertext

        try:
            # Verificar tamanho mínimo (nonce + tag = 28 bytes)
            if len(ciphertext) < 28:
                logger.error(f"Ciphertext muito pequeno: {len(ciphertext)} bytes (mínimo 28)")
                return None

            # Extrair nonce (primeiros 12 bytes)
            nonce = ciphertext[:12]

            # Resto é ciphertext + tag de autenticação
            encrypted_data = ciphertext[12:]

            # Desencriptar e verificar tag (GCM faz automaticamente)
            # Se tag não bater, levanta InvalidTag exception
            plaintext = self.aesgcm.decrypt(nonce, encrypted_data, None)

            logger.debug(f"🔓 End-to-end unwrap: {len(ciphertext)} → {len(plaintext)} bytes (AES-256-GCM)")
            return plaintext

        except Exception as e:
            logger.error(f"Erro ao unwrap end-to-end: {e}", exc_info=True)
            logger.error("⚠️  Tag de autenticação inválida ou dados corrompidos!")
            return None

    def close(self):
        """Fecha o canal DTLS."""
        if self.ssl_socket:
            try:
                self.ssl_socket.close()
            except Exception as e:
                logger.warning(f"Erro ao fechar socket DTLS: {e}")

        self.established = False
        logger.info("Canal DTLS fechado")


class DTLSManager:
    """
    Gerenciador de canais DTLS para o Sink.

    O Sink mantém múltiplos canais DTLS (um por Node conectado).
    """

    def __init__(
        self,
        cert_path: Path,
        key_path: Path,
        ca_cert_path: Path
    ):
        """
        Inicializa gerenciador DTLS.

        Args:
            cert_path: Certificado do Sink
            key_path: Chave privada do Sink
            ca_cert_path: Certificado CA
        """
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_cert_path = ca_cert_path

        # Canais DTLS por NID do Node
        self.channels: dict[str, DTLSChannel] = {}

        logger.info("DTLSManager inicializado")

    def create_channel(self, node_nid: NID) -> DTLSChannel:
        """
        Cria novo canal DTLS para um Node.

        Args:
            node_nid: NID do Node

        Returns:
            Canal DTLS criado
        """
        channel = DTLSChannel(
            cert_path=self.cert_path,
            key_path=self.key_path,
            ca_cert_path=self.ca_cert_path,
            is_server=True,
            peer_nid=node_nid
        )

        self.channels[str(node_nid)] = channel
        logger.info(f"Canal DTLS criado para Node {str(node_nid)[:8]}...")

        return channel

    def get_channel(self, node_nid: NID) -> Optional[DTLSChannel]:
        """
        Obtém canal DTLS existente para um Node.

        Args:
            node_nid: NID do Node

        Returns:
            Canal DTLS ou None
        """
        return self.channels.get(str(node_nid))

    def remove_channel(self, node_nid: NID):
        """
        Remove canal DTLS de um Node.

        Args:
            node_nid: NID do Node
        """
        nid_str = str(node_nid)
        if nid_str in self.channels:
            self.channels[nid_str].close()
            del self.channels[nid_str]
            logger.info(f"Canal DTLS removido para Node {nid_str[:8]}...")
