#!/usr/bin/env python3
"""
Teste do sistema de fragmentação.

Verifica se mensagens são corretamente fragmentadas e reassembladas.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.fragmentation import fragment_message, FragmentReassembler
from common.utils.logger import setup_logger

logger = setup_logger("test_fragmentation")


def test_small_message():
    """Testa mensagem pequena (sem fragmentação)."""
    logger.info("\n=== Teste 1: Mensagem Pequena ===")

    message = b"Hello, this is a small message!"
    logger.info(f"Mensagem original: {len(message)} bytes")

    # Fragmentar
    fragments = fragment_message(message)
    logger.info(f"Fragmentos criados: {len(fragments)}")

    # Reassemblar
    reassembler = FragmentReassembler()

    for i, fragment in enumerate(fragments):
        logger.info(f"  Processando fragmento {i+1}/{len(fragments)}: {len(fragment)} bytes")
        is_complete, reassembled = reassembler.add_fragment(fragment)

        if is_complete:
            logger.info(f" Mensagem reassemblada: {len(reassembled)} bytes")

            if reassembled == message:
                logger.info(" Mensagem correta!")
                return True
            else:
                logger.error(" Mensagem diferente!")
                logger.error(f"   Original: {message}")
                logger.error(f"   Reassemblada: {reassembled}")
                return False

    logger.error(" Mensagem não foi reassemblada")
    return False


def test_large_message():
    """Testa mensagem grande (com fragmentação)."""
    logger.info("\n=== Teste 2: Mensagem Grande ===")

    message = b"X" * 911
    logger.info(f"Mensagem original: {len(message)} bytes")

    # Fragmentar
    fragments = fragment_message(message)
    logger.info(f"Fragmentos criados: {len(fragments)}")

    for i, frag in enumerate(fragments):
        logger.info(f"  Fragmento {i+1}: {len(frag)} bytes")

    # Reassemblar
    reassembler = FragmentReassembler()

    for i, fragment in enumerate(fragments):
        logger.info(f"  Processando fragmento {i+1}/{len(fragments)}")
        is_complete, reassembled = reassembler.add_fragment(fragment)

        if is_complete:
            logger.info(f" Mensagem reassemblada: {len(reassembled)} bytes")

            if reassembled == message:
                logger.info(" Mensagem correta!")
                return True
            else:
                logger.error(" Mensagem diferente!")
                logger.error(f"   Original length: {len(message)}")
                logger.error(f"   Reassembled length: {len(reassembled)}")
                return False
        else:
            logger.info(f"  → Aguardando mais fragmentos...")

    logger.error(" Mensagem não foi reassemblada")
    return False


def test_certificate():
    """Testa com certificado real."""
    logger.info("\n=== Teste 3: Certificado Real ===")

    from common.utils.nid import NID
    from common.security.certificate_manager import CertificateManager
    from common.security.authentication import AuthenticationProtocol

    # Carregar certificado
    client_nid = NID("69f0365f-0b47-4449-8c75-558f4537cf85")
    cert_manager = CertificateManager(client_nid)

    if not cert_manager.initialize():
        logger.error(" Erro ao carregar certificados")
        return False

    auth_protocol = AuthenticationProtocol(cert_manager)
    cert_offer = auth_protocol.start_authentication()

    logger.info(f"CERT_OFFER: {len(cert_offer)} bytes")

    # Fragmentar
    fragments = fragment_message(cert_offer)
    logger.info(f"Fragmentos criados: {len(fragments)}")

    for i, frag in enumerate(fragments):
        logger.info(f"  Fragmento {i+1}: {len(frag)} bytes")

    # Reassemblar
    reassembler = FragmentReassembler()

    for i, fragment in enumerate(fragments):
        logger.info(f"  Processando fragmento {i+1}/{len(fragments)}")
        is_complete, reassembled = reassembler.add_fragment(fragment)

        if is_complete:
            logger.info(f" CERT_OFFER reassemblado: {len(reassembled)} bytes")

            if reassembled == cert_offer:
                logger.info(" CERT_OFFER correto!")
                return True
            else:
                logger.error(" CERT_OFFER diferente!")
                logger.error(f"   Original length: {len(cert_offer)}")
                logger.error(f"   Reassembled length: {len(reassembled)}")
                logger.error(f"   Original first 50 bytes: {cert_offer[:50].hex()}")
                logger.error(f"   Reassembled first 50 bytes: {reassembled[:50].hex()}")
                return False
        else:
            logger.info(f"  → Aguardando mais fragmentos...")

    logger.error(" CERT_OFFER não foi reassemblado")
    return False


def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("  Teste do Sistema de Fragmentação BLE")
    logger.info("=" * 60)

    results = []

    # Teste 1: Mensagem pequena
    results.append(("Mensagem pequena", test_small_message()))

    # Teste 2: Mensagem grande
    results.append(("Mensagem grande", test_large_message()))

    # Teste 3: Certificado real
    results.append(("Certificado real", test_certificate()))

    # Resumo
    logger.info("\n" + "=" * 60)
    logger.info("  Resumo dos Testes")
    logger.info("=" * 60)

    for name, result in results:
        status = " PASS" if result else " FAIL"
        logger.info(f"{status} - {name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        logger.info("\n Todos os testes passaram!")
        return 0
    else:
        logger.error("\n Alguns testes falharam!")
        return 1


if __name__ == '__main__':
    sys.exit(main())
