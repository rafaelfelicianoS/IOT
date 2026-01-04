#!/usr/bin/env python3
"""
Teste do Protocolo de Autenticação.

Este script simula o handshake completo de autenticação entre dois dispositivos:
1. Device A envia certificado
2. Device B valida certificado de A e envia certificado + challenge
3. Device A valida certificado de B, responde ao challenge e envia challenge
4. Device B responde ao challenge
5. Ambos confirmam autenticação
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.security import CertificateManager
from common.security.authentication import AuthenticationProtocol, AuthMessage, AuthMessageType
from common.utils.nid import NID


def main():
    """Main function."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     Teste do Protocolo de Autenticação Mútua              ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # Obter dispositivos com certificados
    certs_dir = Path(__file__).parent.parent / "certs"
    device_dirs = [d for d in certs_dir.iterdir() if d.is_dir()]

    if len(device_dirs) < 2:
        print(" É necessário ter pelo menos 2 dispositivos com certificados")
        print("   Execute primeiro: python3 examples/test_certificates.py")
        return 1

    # Dispositivos
    device_a_nid = NID(device_dirs[0].name)
    device_b_nid = NID(device_dirs[1].name)

    print("=" * 60)
    print("1. Configuração dos Dispositivos")
    print("=" * 60)
    print(f"Device A: {device_a_nid}")
    print(f"Device B: {device_b_nid}")
    print()

    cert_mgr_a = CertificateManager(device_a_nid)
    cert_mgr_b = CertificateManager(device_b_nid)

    # Inicializar
    print(" Carregando certificados do Device A...")
    if not cert_mgr_a.initialize():
        print(" Erro ao inicializar Certificate Manager do Device A")
        return 1

    print(" Carregando certificados do Device B...")
    if not cert_mgr_b.initialize():
        print(" Erro ao inicializar Certificate Manager do Device B")
        return 1

    print("\n Criando protocolos de autenticação...")
    auth_a = AuthenticationProtocol(cert_mgr_a)
    auth_b = AuthenticationProtocol(cert_mgr_b)

    print(f"   Device A - Estado inicial: {auth_a.state.name}")
    print(f"   Device B - Estado inicial: {auth_b.state.name}")

    # Simulação do handshake
    print("\n" + "=" * 60)
    print("2. Handshake de Autenticação")
    print("=" * 60)

    # Passo 1: Device A inicia e envia certificado
    print("\n--- Passo 1: Device A → Device B (CERT_OFFER) ---")
    msg1_bytes = auth_a.start_authentication()
    print(f"Device A envia: {len(msg1_bytes)} bytes")
    print(f"Device A estado: {auth_a.state.name}")

    # Device B recebe certificado de A
    print("\n--- Device B processa certificado de A ---")
    continue_b, response_b = auth_b.process_message(msg1_bytes)
    print(f"Device B estado: {auth_b.state.name}")
    print(f"Device B continua: {continue_b}")
    if response_b:
        print(f"Device B responde: {len(response_b)} bytes")

    # Passo 2: Device B envia certificado + challenge
    print("\n--- Passo 2: Device B → Device A (CERT_OFFER) ---")
    msg2_bytes = auth_b.start_authentication()
    print(f"Device B envia certificado: {len(msg2_bytes)} bytes")

    # Device A recebe certificado de B
    print("\n--- Device A processa certificado de B ---")
    continue_a, response_a = auth_a.process_message(msg2_bytes)
    print(f"Device A estado: {auth_a.state.name}")
    print(f"Device A continua: {continue_a}")
    if response_a:
        msg_parsed = AuthMessage.from_bytes(response_a)
        print(f"Device A responde: {msg_parsed}")

    # Passo 3: Device A responde ao challenge de B
    print("\n--- Passo 3: Device A → Device B (RESPONSE ao challenge) ---")
    if response_b:
        continue_a2, response_a2 = auth_a.process_message(response_b)
        print(f"Device A estado: {auth_a.state.name}")
        if response_a2:
            msg_parsed = AuthMessage.from_bytes(response_a2)
            print(f"Device A envia: {msg_parsed}")

            # Device B verifica response de A
            print("\n--- Device B verifica response de A ---")
            continue_b2, response_b2 = auth_b.process_message(response_a2)
            print(f"Device B estado: {auth_b.state.name}")
            if response_b2:
                msg_parsed = AuthMessage.from_bytes(response_b2)
                print(f"Device B envia: {msg_parsed}")

                # Device A recebe confirmação de B
                if msg_parsed.msg_type == AuthMessageType.AUTH_SUCCESS:
                    print("\n--- Device A recebe confirmação de B ---")
                    auth_a.process_message(response_b2)
                    print(f"Device A estado: {auth_a.state.name}")

    # Passo 4: Device B responde ao challenge de A
    print("\n--- Passo 4: Device B → Device A (RESPONSE ao challenge) ---")
    if response_a:
        continue_b3, response_b3 = auth_b.process_message(response_a)
        print(f"Device B estado: {auth_b.state.name}")
        if response_b3:
            msg_parsed = AuthMessage.from_bytes(response_b3)
            print(f"Device B envia: {msg_parsed}")

            # Device A verifica response de B
            print("\n--- Device A verifica response de B ---")
            continue_a3, response_a3 = auth_a.process_message(response_b3)
            print(f"Device A estado: {auth_a.state.name}")
            if response_a3:
                msg_parsed = AuthMessage.from_bytes(response_a3)
                print(f"Device A envia: {msg_parsed}")

                # Device B recebe confirmação de A
                if msg_parsed.msg_type == AuthMessageType.AUTH_SUCCESS:
                    print("\n--- Device B recebe confirmação de A ---")
                    auth_b.process_message(response_a3)
                    print(f"Device B estado: {auth_b.state.name}")

    print("\n" + "=" * 60)
    print("3. Resultado da Autenticação")
    print("=" * 60)

    auth_a_success = auth_a.is_authenticated()
    auth_b_success = auth_b.is_authenticated()

    print(f"\nDevice A autenticado? {' SIM' if auth_a_success else ' NÃO'}")
    print(f"Device B autenticado? {' SIM' if auth_b_success else ' NÃO'}")

    if auth_a_success and auth_b_success:
        print("\n AUTENTICAÇÃO MÚTUA BEM SUCEDIDA! ")

        # Mostrar informações do peer
        peer_a_info = auth_a.get_peer_info()
        peer_b_info = auth_b.get_peer_info()

        print("\n--- Informações do Peer (Device A) ---")
        print(f"Peer NID: {peer_a_info['nid']}")
        print(f"Peer tipo: {'SINK' if peer_a_info['is_sink'] else 'NODE'}")

        print("\n--- Informações do Peer (Device B) ---")
        print(f"Peer NID: {peer_b_info['nid']}")
        print(f"Peer tipo: {'SINK' if peer_b_info['is_sink'] else 'NODE'}")

        print("\n" + "=" * 60)
        print(" TESTE PASSOU COM SUCESSO!")
        print("=" * 60)
        return 0
    else:
        print("\n AUTENTICAÇÃO FALHOU!")
        print("\n" + "=" * 60)
        print(" TESTE FALHOU!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
