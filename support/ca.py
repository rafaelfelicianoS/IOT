#!/usr/bin/env python3
"""
Certification Authority (CA) para a rede IoT.

Esta CA é responsável por:
- Gerar o par de chaves da CA (ECDSA P-521)
- Emitir certificados X.509 para dispositivos IoT
- Emitir certificados X.509 para o Sink
- Assinar certificados com a chave privada da CA

O certificado da CA é auto-assinado e deve ser distribuído
para todos os dispositivos da rede para verificação.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from cryptography import x509
from cryptography.x509.oid import NameOID, ExtensionOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

from common.utils.nid import NID
from common.utils.logger import setup_logger

logger = setup_logger("ca")

# Diretório para armazenar certificados e chaves
CERTS_DIR = Path(__file__).parent.parent / "certs"
CERTS_DIR.mkdir(exist_ok=True)


class CertificationAuthority:
    """
    Autoridade de Certificação para a rede IoT.

    Usa ECDSA com curva P-521 conforme especificação do projeto.
    """

    def __init__(
        self,
        ca_name: str = "IoT Network CA",
        validity_days: int = 365 * 10,  # 10 anos
    ):
        """
        Inicializa a CA.

        Args:
            ca_name: Nome da CA
            validity_days: Validade dos certificados em dias
        """
        self.ca_name = ca_name
        self.validity_days = validity_days
        self.ca_private_key: Optional[ec.EllipticCurvePrivateKey] = None
        self.ca_cert: Optional[x509.Certificate] = None

        logger.info(f"CA inicializada: {ca_name}")

    def generate_ca_keypair(self) -> ec.EllipticCurvePrivateKey:
        """
        Gera par de chaves ECDSA P-521 para a CA.

        Returns:
            Chave privada da CA
        """
        logger.info("A gerar par de chaves ECDSA P-521 para CA...")

        private_key = ec.generate_private_key(
            ec.SECP521R1(),  # Curva P-521
            backend=default_backend()
        )

        logger.info(" Par de chaves gerado")
        return private_key

    def create_ca_certificate(self) -> x509.Certificate:
        """
        Cria certificado auto-assinado da CA.

        Returns:
            Certificado X.509 da CA
        """
        if self.ca_private_key is None:
            self.ca_private_key = self.generate_ca_keypair()

        logger.info("A criar certificado auto-assinado da CA...")

        # Subject e Issuer são iguais (auto-assinado)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "PT"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Aveiro"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IoT Network"),
            x509.NameAttribute(NameOID.COMMON_NAME, self.ca_name),
        ])

        # Certificado
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self.ca_private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=self.validity_days))
            # Extensões para CA
            .add_extension(
                x509.BasicConstraints(ca=True, path_length=0),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_cert_sign=True,
                    crl_sign=True,
                    key_encipherment=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(self.ca_private_key, hashes.SHA256(), backend=default_backend())
        )

        logger.info(" Certificado CA criado")
        logger.info(f"   Serial: {cert.serial_number}")
        logger.info(f"   Válido até: {cert.not_valid_after}")

        return cert

    def issue_device_certificate(
        self,
        device_nid: NID,
        device_public_key: ec.EllipticCurvePublicKey,
        is_sink: bool = False,
    ) -> x509.Certificate:
        """
        Emite certificado X.509 para um dispositivo IoT.

        Args:
            device_nid: NID do dispositivo
            device_public_key: Chave pública do dispositivo (ECDSA P-521)
            is_sink: True se for o Sink, False se for node normal

        Returns:
            Certificado X.509 assinado pela CA
        """
        if self.ca_private_key is None or self.ca_cert is None:
            raise RuntimeError("CA não foi inicializada. Execute initialize() primeiro.")

        logger.info(f"A emitir certificado para dispositivo: {device_nid}")
        logger.info(f"   Tipo: {'SINK' if is_sink else 'NODE'}")

        # Subject do dispositivo
        subject_attrs = [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "PT"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "IoT Network"),
            x509.NameAttribute(NameOID.COMMON_NAME, device_nid.to_string()),
        ]

        # Se for Sink, adicionar atributo especial
        if is_sink:
            subject_attrs.append(
                x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Sink")
            )

        subject = x509.Name(subject_attrs)

        # Issuer é a CA
        issuer = self.ca_cert.subject

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(device_public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.utcnow())
            .not_valid_after(datetime.utcnow() + timedelta(days=self.validity_days))
            # Extensões para dispositivo final
            .add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    key_cert_sign=False,
                    crl_sign=False,
                    content_commitment=False,
                    data_encipherment=False,
                    key_agreement=True,  # Para ECDH
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            # Subject Alternative Name com o NID
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName(str(device_nid))
                ]),
                critical=False,
            )
            .sign(self.ca_private_key, hashes.SHA256(), backend=default_backend())
        )

        logger.info(" Certificado emitido")
        logger.info(f"   Serial: {cert.serial_number}")
        logger.info(f"   Válido até: {cert.not_valid_after}")

        return cert

    def initialize(self):
        """
        Inicializa a CA: gera chaves e certificado auto-assinado.
        """
        logger.info("=" * 60)
        logger.info("Inicializando Certification Authority")
        logger.info("=" * 60)

        # Gerar chave privada
        self.ca_private_key = self.generate_ca_keypair()

        self.ca_cert = self.create_ca_certificate()

        logger.info("=" * 60)
        logger.info(" CA inicializada com sucesso!")
        logger.info("=" * 60)

    def save_ca_files(self):
        """
        Guarda chave privada e certificado da CA em ficheiros.
        """
        if self.ca_private_key is None or self.ca_cert is None:
            raise RuntimeError("CA não foi inicializada")

        # Guardar chave privada (PEM format, sem password por simplicidade)
        ca_key_path = CERTS_DIR / "ca_private_key.pem"
        with open(ca_key_path, "wb") as f:
            f.write(
                self.ca_private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
        logger.info(f" Chave privada CA guardada: {ca_key_path}")

        # Guardar certificado CA
        ca_cert_path = CERTS_DIR / "ca_certificate.pem"
        with open(ca_cert_path, "wb") as f:
            f.write(self.ca_cert.public_bytes(serialization.Encoding.PEM))
        logger.info(f" Certificado CA guardado: {ca_cert_path}")

    def load_ca_files(self):
        """
        Carrega chave privada e certificado da CA a partir de ficheiros.
        """
        ca_key_path = CERTS_DIR / "ca_private_key.pem"
        ca_cert_path = CERTS_DIR / "ca_certificate.pem"

        if not ca_key_path.exists() or not ca_cert_path.exists():
            raise FileNotFoundError("Ficheiros da CA não encontrados. Execute initialize() primeiro.")

        # Carregar chave privada
        with open(ca_key_path, "rb") as f:
            self.ca_private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        logger.info(f" Chave privada CA carregada: {ca_key_path}")

        # Carregar certificado
        with open(ca_cert_path, "rb") as f:
            self.ca_cert = x509.load_pem_x509_certificate(
                f.read(),
                backend=default_backend()
            )
        logger.info(f" Certificado CA carregado: {ca_cert_path}")


def main():
    """Função principal para testar a CA."""
    print("\n")
    print("=" * 60)
    print("  Certification Authority - IoT Network")
    print("=" * 60)
    print()

    ca = CertificationAuthority()

    try:
        ca.load_ca_files()
        print(" CA já existe, certificados carregados")
    except FileNotFoundError:
        print("  CA não existe, a criar nova CA...")
        ca.initialize()
        ca.save_ca_files()

    # Mostrar informações da CA
    print()
    print("=" * 60)
    print("Informações da CA:")
    print("=" * 60)
    print(f"Nome: {ca.ca_cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value}")
    print(f"Serial: {ca.ca_cert.serial_number}")
    print(f"Válido de: {ca.ca_cert.not_valid_before}")
    print(f"Válido até: {ca.ca_cert.not_valid_after}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
