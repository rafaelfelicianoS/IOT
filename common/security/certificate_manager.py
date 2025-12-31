#!/usr/bin/env python3
"""
Certificate Manager para dispositivos IoT.

Responsável por:
- Carregar certificado e chave privada do dispositivo
- Carregar certificado da CA
- Validar certificados recebidos de outros dispositivos
- Extrair informações de certificados (NID, tipo Sink/Node)
"""

from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime, timezone

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

from common.utils.nid import NID
from common.utils.logger import get_logger

logger = get_logger("cert_manager")


class CertificateManager:
    """
    Gestor de certificados para um dispositivo IoT.

    Carrega e valida certificados X.509 usando ECDSA P-521.
    """

    def __init__(self, device_nid: NID, certs_dir: Optional[Path] = None):
        """
        Inicializa o Certificate Manager.

        Args:
            device_nid: NID deste dispositivo
            certs_dir: Diretório raiz dos certificados (default: ./certs)
        """
        self.device_nid = device_nid

        if certs_dir is None:
            # Assumir que certs está na raiz do projeto
            self.certs_dir = Path(__file__).parent.parent.parent / "certs"
        else:
            self.certs_dir = certs_dir

        # Certificados e chaves
        self.device_cert: Optional[x509.Certificate] = None
        self.device_private_key: Optional[ec.EllipticCurvePrivateKey] = None
        self.ca_cert: Optional[x509.Certificate] = None

        logger.info(f"CertificateManager inicializado para {device_nid}")
        logger.info(f"   Diretório de certificados: {self.certs_dir}")

    def load_device_certificate(self, device_type: str = None) -> bool:
        """
        Carrega o certificado e chave privada do dispositivo.

        Suporta dois formatos:
        1. Estrutura de diretórios: certs/<full-uuid>/certificate.pem
        2. Formato flat: certs/{sink|node}_<short-nid>_{cert|key}.pem

        Args:
            device_type: Tipo do dispositivo ('sink' ou 'node') para formato flat

        Returns:
            True se carregado com sucesso, False caso contrário
        """
        # Tentar formato de diretório primeiro
        device_dir = self.certs_dir / self.device_nid.to_string()
        cert_path = device_dir / "certificate.pem"
        key_path = device_dir / "private_key.pem"

        # Se não existir, tentar formato flat
        if not cert_path.exists() and device_type:
            short_nid = self.device_nid.to_short_string()
            cert_path = self.certs_dir / f"{device_type}_{short_nid}_cert.pem"
            key_path = self.certs_dir / f"{device_type}_{short_nid}_key.pem"
            logger.debug(f"Tentando formato flat: {cert_path}")

        # Verificar se ficheiros existem
        if not cert_path.exists():
            logger.error(f"Certificado não encontrado: {cert_path}")
            # Tentar auto-detectar tipo se não foi fornecido
            if not device_type:
                for dtype in ['sink', 'node']:
                    short_nid = self.device_nid.to_short_string()
                    alt_cert_path = self.certs_dir / f"{dtype}_{short_nid}_cert.pem"
                    if alt_cert_path.exists():
                        cert_path = alt_cert_path
                        key_path = self.certs_dir / f"{dtype}_{short_nid}_key.pem"
                        logger.info(f"Auto-detectado tipo: {dtype}")
                        break
                else:
                    return False
            else:
                return False

        if not key_path.exists():
            logger.error(f"Chave privada não encontrada: {key_path}")
            return False

        try:
            # Carregar certificado
            with open(cert_path, "rb") as f:
                self.device_cert = x509.load_pem_x509_certificate(
                    f.read(),
                    backend=default_backend()
                )

            # Carregar chave privada
            with open(key_path, "rb") as f:
                self.device_private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                    backend=default_backend()
                )

            logger.info(f"✅ Certificado do dispositivo carregado: {cert_path}")
            logger.info(f"   Serial: {self.device_cert.serial_number}")

            # Validar que o NID do certificado corresponde ao esperado
            cert_nid = self.extract_nid_from_cert(self.device_cert)
            if cert_nid != self.device_nid:
                logger.error(
                    f"NID do certificado ({cert_nid}) não corresponde "
                    f"ao NID do dispositivo ({self.device_nid})"
                )
                return False

            return True

        except Exception as e:
            logger.error(f"Erro ao carregar certificado do dispositivo: {e}")
            return False

    def load_ca_certificate(self) -> bool:
        """
        Carrega o certificado da CA.

        Returns:
            True se carregado com sucesso, False caso contrário
        """
        ca_cert_path = self.certs_dir / "ca_certificate.pem"

        if not ca_cert_path.exists():
            logger.error(f"Certificado da CA não encontrado: {ca_cert_path}")
            return False

        try:
            with open(ca_cert_path, "rb") as f:
                self.ca_cert = x509.load_pem_x509_certificate(
                    f.read(),
                    backend=default_backend()
                )

            logger.info(f"✅ Certificado da CA carregado: {ca_cert_path}")
            logger.info(f"   Serial: {self.ca_cert.serial_number}")

            return True

        except Exception as e:
            logger.error(f"Erro ao carregar certificado da CA: {e}")
            return False

    def initialize(self) -> bool:
        """
        Inicializa o Certificate Manager carregando todos os certificados necessários.

        Returns:
            True se tudo foi carregado com sucesso, False caso contrário
        """
        logger.info("=" * 60)
        logger.info("A carregar certificados...")
        logger.info("=" * 60)

        # Carregar CA
        if not self.load_ca_certificate():
            return False

        # Carregar certificado do dispositivo
        if not self.load_device_certificate():
            return False

        logger.info("=" * 60)
        logger.info("✅ Todos os certificados carregados com sucesso!")
        logger.info("=" * 60)

        return True

    def validate_certificate(self, cert: x509.Certificate) -> bool:
        """
        Valida um certificado recebido de outro dispositivo.

        Verifica:
        1. Assinatura da CA
        2. Validade temporal
        3. Extensões corretas

        Args:
            cert: Certificado a validar

        Returns:
            True se válido, False caso contrário
        """
        if self.ca_cert is None:
            logger.error("CA não está carregada, não é possível validar certificado")
            return False

        try:
            # 1. Verificar assinatura da CA
            ca_public_key = self.ca_cert.public_key()
            ca_public_key.verify(
                cert.signature,
                cert.tbs_certificate_bytes,
                ec.ECDSA(cert.signature_hash_algorithm)
            )
            logger.debug("✅ Assinatura da CA válida")

        except InvalidSignature:
            logger.warning("❌ Assinatura da CA inválida!")
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar assinatura: {e}")
            return False

        # 2. Verificar validade temporal
        now = datetime.now(timezone.utc)

        # Converter para timezone-aware se necessário
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc

        if now < not_before:
            logger.warning(f"❌ Certificado ainda não é válido (válido a partir de {not_before})")
            return False

        if now > not_after:
            logger.warning(f"❌ Certificado expirado (expirou em {not_after})")
            return False

        logger.debug(f"✅ Certificado válido temporalmente (expira em {not_after})")

        # 3. Verificar que não é um certificado CA (BasicConstraints ca=False)
        try:
            basic_constraints = cert.extensions.get_extension_for_oid(
                x509.oid.ExtensionOID.BASIC_CONSTRAINTS
            ).value

            if basic_constraints.ca:
                logger.warning("❌ Certificado é uma CA (não deveria ser)")
                return False

        except x509.ExtensionNotFound:
            logger.warning("⚠️  BasicConstraints não encontrado no certificado")

        logger.info("✅ Certificado validado com sucesso")
        return True

    def extract_nid_from_cert(self, cert: x509.Certificate) -> NID:
        """
        Extrai o NID do Common Name do certificado.

        Args:
            cert: Certificado

        Returns:
            NID extraído

        Raises:
            ValueError: Se não conseguir extrair o NID
        """
        try:
            cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
            return NID(cn)
        except Exception as e:
            raise ValueError(f"Erro ao extrair NID do certificado: {e}")

    def is_sink_certificate(self, cert: x509.Certificate) -> bool:
        """
        Verifica se um certificado é de um Sink.

        Args:
            cert: Certificado

        Returns:
            True se for Sink, False se for Node
        """
        try:
            ou_attrs = cert.subject.get_attributes_for_oid(NameOID.ORGANIZATIONAL_UNIT_NAME)
            return len(ou_attrs) > 0 and ou_attrs[0].value == "Sink"
        except:
            return False

    def get_device_certificate_bytes(self) -> bytes:
        """
        Obtém o certificado do dispositivo em formato PEM (bytes).

        Returns:
            Certificado em formato PEM

        Raises:
            RuntimeError: Se certificado não está carregado
        """
        if self.device_cert is None:
            raise RuntimeError("Certificado do dispositivo não está carregado")

        return self.device_cert.public_bytes(serialization.Encoding.PEM)

    def get_device_public_key(self) -> ec.EllipticCurvePublicKey:
        """
        Obtém a chave pública do certificado do dispositivo.

        Returns:
            Chave pública ECDSA

        Raises:
            RuntimeError: Se certificado não está carregado
        """
        if self.device_cert is None:
            raise RuntimeError("Certificado do dispositivo não está carregado")

        return self.device_cert.public_key()

    def sign_data(self, data: bytes) -> bytes:
        """
        Assina dados com a chave privada do dispositivo.

        Args:
            data: Dados a assinar

        Returns:
            Assinatura ECDSA (bytes)

        Raises:
            RuntimeError: Se chave privada não está carregada
        """
        if self.device_private_key is None:
            raise RuntimeError("Chave privada do dispositivo não está carregada")

        from cryptography.hazmat.primitives import hashes

        signature = self.device_private_key.sign(
            data,
            ec.ECDSA(hashes.SHA256())
        )

        return signature

    def verify_signature(
        self,
        data: bytes,
        signature: bytes,
        cert: x509.Certificate
    ) -> bool:
        """
        Verifica uma assinatura usando a chave pública de um certificado.

        Args:
            data: Dados originais
            signature: Assinatura a verificar
            cert: Certificado com a chave pública

        Returns:
            True se assinatura válida, False caso contrário
        """
        try:
            from cryptography.hazmat.primitives import hashes

            public_key = cert.public_key()
            public_key.verify(
                signature,
                data,
                ec.ECDSA(hashes.SHA256())
            )
            return True

        except InvalidSignature:
            logger.warning("❌ Assinatura inválida")
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar assinatura: {e}")
            return False
