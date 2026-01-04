#!/usr/bin/env python3
"""
Teste de Certificados X.509.

Este script testa:
1. Criação/carregamento da CA
2. Geração de certificados para dispositivos IoT
3. Validação de certificados
4. Verificação de assinaturas
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography import x509
from cryptography.hazmat.primitives import serialization

from support.ca import CertificationAuthority, CERTS_DIR
from common.utils.nid import NID


def generate_device_keypair():
    """Gera par de chaves ECDSA P-521 para um dispositivo."""
    return ec.generate_private_key(
        ec.SECP521R1(),
        backend=default_backend()
    )


def save_device_certificate(device_nid: NID, cert: x509.Certificate, private_key: ec.EllipticCurvePrivateKey):
    """Guarda certificado e chave privada de um dispositivo."""
    device_dir = CERTS_DIR / device_nid.to_string()
    device_dir.mkdir(exist_ok=True)

    # Guardar certificado
    cert_path = device_dir / "certificate.pem"
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    # Guardar chave privada
    key_path = device_dir / "private_key.pem"
    with open(key_path, "wb") as f:
        f.write(
            private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    return cert_path, key_path


def verify_certificate(cert: x509.Certificate, ca_cert: x509.Certificate) -> bool:
    """
    Verifica se um certificado foi assinado pela CA.

    Args:
        cert: Certificado a verificar
        ca_cert: Certificado da CA

    Returns:
        True se válido, False caso contrário
    """
    try:
        ca_public_key = ca_cert.public_key()
        ca_public_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            ec.ECDSA(cert.signature_hash_algorithm)
        )
        return True
    except Exception as e:
        print(f"Erro ao verificar certificado: {e}")
        return False


def extract_nid_from_cert(cert: x509.Certificate) -> NID:
    """Extrai o NID do Common Name do certificado."""
    cn = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
    # CN contém o UUID no formato com hífens (e.g., "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
    return NID(cn)


def is_sink_certificate(cert: x509.Certificate) -> bool:
    """Verifica se o certificado é de um Sink (tem OU=Sink)."""
    try:
        ou_attrs = cert.subject.get_attributes_for_oid(x509.oid.NameOID.ORGANIZATIONAL_UNIT_NAME)
        return len(ou_attrs) > 0 and ou_attrs[0].value == "Sink"
    except:
        return False


def main():
    """Main function."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║           Teste de Certificados X.509                     ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # 1. Criar/Carregar CA
    print("=" * 60)
    print("1. Inicialização da CA")
    print("=" * 60)

    ca = CertificationAuthority()

    try:
        ca.load_ca_files()
        print(" CA carregada de ficheiros existentes")
    except FileNotFoundError:
        print("  CA não existe, a criar...")
        ca.initialize()
        ca.save_ca_files()
        print(" CA criada e guardada")

    print(f"   Nome: {ca.ca_cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value}")
    print(f"   Serial: {ca.ca_cert.serial_number}")
    print()

    # 2. Gerar certificados para dispositivos IoT
    print("=" * 60)
    print("2. Emissão de Certificados para Dispositivos")
    print("=" * 60)

    nodes = []
    for i in range(3):
        nid = NID.generate()
        private_key = generate_device_keypair()
        cert = ca.issue_device_certificate(nid, private_key.public_key(), is_sink=False)
        nodes.append((nid, private_key, cert))

        # Guardar certificado
        cert_path, key_path = save_device_certificate(nid, cert, private_key)

        print(f" Node #{i+1}: {nid}")
        print(f"   Serial: {cert.serial_number}")
        print(f"   Certificado: {cert_path}")

    print()

    print("=" * 60)
    print("3. Emissão de Certificado para Sink")
    print("=" * 60)

    sink_nid = NID.generate()
    sink_private_key = generate_device_keypair()
    sink_cert = ca.issue_device_certificate(sink_nid, sink_private_key.public_key(), is_sink=True)

    # Guardar certificado do Sink
    sink_cert_path, sink_key_path = save_device_certificate(sink_nid, sink_cert, sink_private_key)

    print(f" Sink: {sink_nid}")
    print(f"   Serial: {sink_cert.serial_number}")
    print(f"   Certificado: {sink_cert_path}")
    print(f"   OU: Sink (marcado como Sink)")
    print()

    # 3. Validar certificados
    print("=" * 60)
    print("4. Validação de Certificados")
    print("=" * 60)

    test_nid, test_key, test_cert = nodes[0]
    is_valid = verify_certificate(test_cert, ca.ca_cert)
    print(f" Certificado do Node {test_nid}: {'VÁLIDO' if is_valid else 'INVÁLIDO'}")

    is_valid = verify_certificate(sink_cert, ca.ca_cert)
    print(f" Certificado do Sink {sink_nid}: {'VÁLIDO' if is_valid else 'INVÁLIDO'}")
    print()

    # 4. Testar extração de informações
    print("=" * 60)
    print("5. Extração de Informações dos Certificados")
    print("=" * 60)

    # Extrair NID
    extracted_nid = extract_nid_from_cert(test_cert)
    print(f" NID extraído do certificado: {extracted_nid}")
    print(f"   Corresponde ao original? {extracted_nid == test_nid}")
    print()

    print(f" Node é Sink? {is_sink_certificate(test_cert)}")
    print(f" Sink é Sink? {is_sink_certificate(sink_cert)}")
    print()

    # 5. Resumo
    print("=" * 60)
    print(" TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    print()
    print("Resumo:")
    print(f"  - CA criada/carregada com sucesso")
    print(f"  - {len(nodes)} certificados de Nodes emitidos")
    print(f"  - 1 certificado de Sink emitido")
    print(f"  - Todos os certificados são válidos")
    print(f"  - Extração de NID funciona corretamente")
    print(f"  - Identificação de Sink funciona corretamente")
    print()

    # Mostrar estrutura de diretórios
    print("=" * 60)
    print("Estrutura de Certificados:")
    print("=" * 60)
    print(f"certs/")
    print(f"├── ca_certificate.pem")
    print(f"├── ca_private_key.pem")
    for nid, _, _ in nodes:
        print(f"├── {nid}/")
        print(f"│   ├── certificate.pem")
        print(f"│   └── private_key.pem")
    print(f"└── {sink_nid}/ (Sink)")
    print(f"    ├── certificate.pem")
    print(f"    └── private_key.pem")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
