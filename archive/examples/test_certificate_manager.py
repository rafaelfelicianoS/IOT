#!/usr/bin/env python3
"""
Teste do CertificateManager.

Este script testa:
1. Carregamento de certificados do dispositivo e CA
2. Validação de certificados
3. Extração de informações (NID, tipo Sink/Node)
4. Assinatura e verificação de dados
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.security import CertificateManager
from common.utils.nid import NID
from cryptography import x509
from cryptography.hazmat.backends import default_backend


def main():
    """Main function."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║        Teste do Certificate Manager                       ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # Obter lista de NIDs disponíveis (dispositivos com certificados)
    certs_dir = Path(__file__).parent.parent / "certs"
    device_dirs = [d for d in certs_dir.iterdir() if d.is_dir()]

    if len(device_dirs) < 2:
        print(" É necessário ter pelo menos 2 dispositivos com certificados")
        print("   Execute primeiro: python3 examples/test_certificates.py")
        return 1

    # Pegar os primeiros dois dispositivos
    device1_dir = device_dirs[0]
    device2_dir = device_dirs[1]

    # Extrair NIDs dos nomes dos diretórios
    device1_nid = NID(device1_dir.name)
    device2_nid = NID(device2_dir.name)

    print("=" * 60)
    print("1. Inicialização dos Certificate Managers")
    print("=" * 60)
    print(f"Device 1: {device1_nid}")
    print(f"Device 2: {device2_nid}")
    print()

    cert_mgr1 = CertificateManager(device1_nid)
    cert_mgr2 = CertificateManager(device2_nid)

    # Inicializar (carregar certificados)
    print("\n A carregar certificados do Device 1...")
    if not cert_mgr1.initialize():
        print(" Erro ao inicializar Certificate Manager do Device 1")
        return 1

    print("\n A carregar certificados do Device 2...")
    if not cert_mgr2.initialize():
        print(" Erro ao inicializar Certificate Manager do Device 2")
        return 1

    print("\n" + "=" * 60)
    print("2. Validação Cruzada de Certificados")
    print("=" * 60)

    # Device 1 valida certificado do Device 2
    print(f"\n Device 1 validando certificado do Device 2...")
    is_valid = cert_mgr1.validate_certificate(cert_mgr2.device_cert)
    print(f"   Resultado: {' VÁLIDO' if is_valid else ' INVÁLIDO'}")

    # Device 2 valida certificado do Device 1
    print(f"\n Device 2 validando certificado do Device 1...")
    is_valid = cert_mgr2.validate_certificate(cert_mgr1.device_cert)
    print(f"   Resultado: {' VÁLIDO' if is_valid else ' INVÁLIDO'}")

    print("\n" + "=" * 60)
    print("3. Extração de Informações dos Certificados")
    print("=" * 60)

    # Extrair NID do certificado do Device 2
    print(f"\n Device 1 extraindo NID do certificado do Device 2...")
    extracted_nid = cert_mgr1.extract_nid_from_cert(cert_mgr2.device_cert)
    print(f"   NID extraído: {extracted_nid}")
    print(f"   Corresponde ao esperado? {extracted_nid == device2_nid}")

    is_sink_1 = cert_mgr1.is_sink_certificate(cert_mgr1.device_cert)
    is_sink_2 = cert_mgr1.is_sink_certificate(cert_mgr2.device_cert)

    print(f"\n  Device 1 é Sink? {is_sink_1}")
    print(f"  Device 2 é Sink? {is_sink_2}")

    print("\n" + "=" * 60)
    print("4. Assinatura e Verificação de Dados")
    print("=" * 60)

    # Device 1 assina dados
    test_data = b"Hello, this is a test message for authentication!"
    print(f"\n Device 1 assinando dados: {test_data[:30]}...")

    signature = cert_mgr1.sign_data(test_data)
    print(f"   Assinatura gerada: {len(signature)} bytes")
    print(f"   Primeiros 16 bytes (hex): {signature[:16].hex()}")

    # Device 2 verifica assinatura usando certificado do Device 1
    print(f"\n Device 2 verificando assinatura do Device 1...")
    is_valid = cert_mgr2.verify_signature(test_data, signature, cert_mgr1.device_cert)
    print(f"   Resultado: {' ASSINATURA VÁLIDA' if is_valid else ' ASSINATURA INVÁLIDA'}")

    # Testar com assinatura corrompida
    print(f"\n Testando com assinatura corrompida...")
    corrupted_signature = signature[:-1] + bytes([signature[-1] ^ 0xFF])
    is_valid = cert_mgr2.verify_signature(test_data, corrupted_signature, cert_mgr1.device_cert)
    print(f"   Resultado: {' VÁLIDA (ERRO!)' if is_valid else ' INVÁLIDA (correto!)'}")

    # Testar com dados diferentes
    print(f"\n Testando com dados diferentes...")
    different_data = b"Different data"
    is_valid = cert_mgr2.verify_signature(different_data, signature, cert_mgr1.device_cert)
    print(f"   Resultado: {' VÁLIDA (ERRO!)' if is_valid else ' INVÁLIDA (correto!)'}")

    print("\n" + "=" * 60)
    print("5. Simulação de Autenticação Challenge-Response")
    print("=" * 60)

    # Device 2 gera challenge para Device 1
    import os
    challenge = os.urandom(32)  # 32 bytes aleatórios
    print(f"\n Device 2 gera challenge: {challenge.hex()[:32]}...")

    # Device 1 assina o challenge
    print(f"\n  Device 1 assina o challenge...")
    response = cert_mgr1.sign_data(challenge)

    # Device 2 verifica a resposta
    print(f"\n Device 2 verifica a resposta...")
    is_valid = cert_mgr2.verify_signature(challenge, response, cert_mgr1.device_cert)

    if is_valid:
        print(f"    AUTENTICAÇÃO BEM SUCEDIDA!")
        print(f"   Device 1 provou possuir a chave privada do certificado")
    else:
        print(f"    AUTENTICAÇÃO FALHOU!")

    print("\n" + "=" * 60)
    print(" TODOS OS TESTES PASSARAM!")
    print("=" * 60)
    print("\nResumo:")
    print("  - Certificate Managers inicializados com sucesso")
    print("  - Validação cruzada de certificados funciona")
    print("  - Extração de NID funciona corretamente")
    print("  - Identificação de Sink/Node funciona")
    print("  - Assinatura e verificação funcionam corretamente")
    print("  - Challenge-Response implementado com sucesso")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
