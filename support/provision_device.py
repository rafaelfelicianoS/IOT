#!/usr/bin/env python3
"""
Script para provisionar dispositivos IoT com certificados X.509.

Uso:
    python3 support/provision_device.py --type sink --nid <UUID>
    python3 support/provision_device.py --type node --nid <UUID>
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend

from common.utils.nid import NID
from common.utils.logger import setup_logger
from support.ca import CertificationAuthority, CERTS_DIR

logger = setup_logger("provision")


def provision_device(device_type: str, nid: NID):
    """
    Provisiona um dispositivo IoT com certificado X.509.

    Args:
        device_type: 'sink' ou 'node'
        nid: NID do dispositivo
    """
    logger.info("=" * 60)
    logger.info(f"  Provisionando dispositivo: {device_type.upper()}")
    logger.info("=" * 60)
    logger.info(f"NID: {nid}")
    logger.info("")

    # Carregar CA
    ca = CertificationAuthority()
    try:
        ca.load_ca_files()
        logger.info(" CA carregada")
    except FileNotFoundError:
        logger.error(" CA não encontrada! Execute primeiro:")
        logger.error("   python3 support/ca.py")
        return False

    # Gerar par de chaves para o dispositivo
    logger.info("A gerar par de chaves ECDSA P-521 para dispositivo...")
    device_private_key = ec.generate_private_key(
        ec.SECP521R1(),
        backend=default_backend()
    )
    device_public_key = device_private_key.public_key()
    logger.info(" Par de chaves gerado")

    # Emitir certificado
    is_sink = (device_type == 'sink')
    cert = ca.issue_device_certificate(nid, device_public_key, is_sink=is_sink)

    # Guardar chave privada e certificado
    nid_str = str(nid)[:8]  # Primeiros 8 caracteres do NID
    device_key_path = CERTS_DIR / f"{device_type}_{nid_str}_key.pem"
    device_cert_path = CERTS_DIR / f"{device_type}_{nid_str}_cert.pem"

    # Guardar chave privada
    with open(device_key_path, "wb") as f:
        f.write(
            device_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    logger.info(f" Chave privada guardada: {device_key_path}")

    # Guardar certificado
    with open(device_cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    logger.info(f" Certificado guardado: {device_cert_path}")

    logger.info("")
    logger.info("=" * 60)
    logger.info(" Dispositivo provisionado com sucesso!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Para executar o dispositivo, use:")
    if device_type == 'sink':
        logger.info(f"  sudo ./iot-sink hci0 \\")
        logger.info(f"    --cert {device_cert_path} \\")
        logger.info(f"    --key {device_key_path} \\")
        logger.info(f"    --ca-cert {CERTS_DIR / 'ca_certificate.pem'}")
    else:
        logger.info(f"  ./iot-node \\")
        logger.info(f"    --cert {device_cert_path} \\")
        logger.info(f"    --key {device_key_path} \\")
        logger.info(f"    --ca-cert {CERTS_DIR / 'ca_certificate.pem'}")

    return True


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Provisiona dispositivo IoT com certificado X.509"
    )
    parser.add_argument(
        '--type',
        required=True,
        choices=['sink', 'node'],
        help="Tipo de dispositivo (sink ou node)"
    )
    parser.add_argument(
        '--nid',
        type=str,
        help="NID do dispositivo (UUID). Se omitido, gera um novo"
    )

    args = parser.parse_args()

    # Parse ou gerar NID
    if args.nid:
        try:
            nid = NID(args.nid)
        except Exception as e:
            logger.error(f"NID inválido: {e}")
            return 1
    else:
        nid = NID.generate()
        logger.info(f"NID gerado automaticamente: {nid}")

    # Provisionar
    success = provision_device(args.type, nid)
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
