#!/usr/bin/env python3
"""
Teste do AuthenticationHandler.

Este script simula o uso do AuthenticationHandler com múltiplos clientes,
como aconteceria num servidor GATT real.
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.security import CertificateManager, AuthenticationProtocol
from common.security.auth_handler import AuthenticationHandler
from common.utils.nid import NID


def main():
    """Main function."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     Teste do Authentication Handler (GATT Server)         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    # Obter dispositivos com certificados
    certs_dir = Path(__file__).parent.parent / "certs"
    device_dirs = [d for d in certs_dir.iterdir() if d.is_dir()]

    if len(device_dirs) < 3:
        print("❌ É necessário ter pelo menos 3 dispositivos com certificados")
        print("   Execute primeiro: python3 examples/test_certificates.py")
        return 1

    # Dispositivo servidor (Device A)
    server_nid = NID(device_dirs[0].name)

    # Clientes (Devices B e C)
    client1_nid = NID(device_dirs[1].name)
    client2_nid = NID(device_dirs[2].name)

    print("=" * 60)
    print("1. Configuração")
    print("=" * 60)
    print(f"Servidor: {server_nid}")
    print(f"Cliente 1: {client1_nid}")
    print(f"Cliente 2: {client2_nid}")
    print()

    # Criar Certificate Managers
    server_cert_mgr = CertificateManager(server_nid)
    client1_cert_mgr = CertificateManager(client1_nid)
    client2_cert_mgr = CertificateManager(client2_nid)

    # Inicializar
    print("📁 Carregando certificados...")
    server_cert_mgr.initialize()
    client1_cert_mgr.initialize()
    client2_cert_mgr.initialize()

    # Criar AuthenticationHandler no servidor
    print("\n🔐 Criando AuthenticationHandler no servidor...")
    auth_handler = AuthenticationHandler(server_cert_mgr)

    # Callbacks
    authenticated_clients = []
    failed_clients = []

    def on_authenticated(client_id: str, peer_info: dict):
        print(f"\n🎉 Callback: Cliente {client_id} autenticado!")
        print(f"   Peer NID: {peer_info['nid']}")
        print(f"   Peer tipo: {'SINK' if peer_info['is_sink'] else 'NODE'}")
        authenticated_clients.append(client_id)

    def on_auth_failed(client_id: str):
        print(f"\n❌ Callback: Autenticação falhou para {client_id}")
        failed_clients.append(client_id)

    auth_handler.set_authenticated_callback(on_authenticated)
    auth_handler.set_auth_failed_callback(on_auth_failed)

    # Criar protocolos de autenticação para os clientes
    print("\n🔐 Criando protocolos de autenticação nos clientes...")
    client1_auth = AuthenticationProtocol(client1_cert_mgr)
    client2_auth = AuthenticationProtocol(client2_cert_mgr)

    print("\n" + "=" * 60)
    print("2. Autenticação do Cliente 1")
    print("=" * 60)

    # Cliente 1 conecta e inicia autenticação
    print("\n--- Cliente 1 inicia autenticação ---")
    client1_id = "client1:00:11:22:33:44:55"
    msg1 = client1_auth.start_authentication()

    # Servidor processa mensagem do Cliente 1
    print(f"\n--- Servidor processa mensagem do Cliente 1 ---")
    response1 = auth_handler.handle_auth_message(msg1, client1_id)

    # Simular troca completa de mensagens
    while response1:
        # Cliente 1 processa resposta do servidor
        print(f"\n--- Cliente 1 processa resposta ---")
        continue_auth, client_response = client1_auth.process_message(response1)

        if not continue_auth:
            break

        if client_response:
            # Servidor processa resposta do Cliente 1
            print(f"\n--- Servidor processa resposta do Cliente 1 ---")
            response1 = auth_handler.handle_auth_message(client_response, client1_id)
        else:
            break

    # Verificar se Cliente 1 está autenticado
    if auth_handler.is_authenticated(client1_id):
        print(f"\n✅ Cliente 1 está AUTENTICADO no servidor")
    else:
        print(f"\n❌ Cliente 1 NÃO está autenticado")

    print("\n" + "=" * 60)
    print("3. Autenticação do Cliente 2")
    print("=" * 60)

    # Cliente 2 conecta e inicia autenticação
    print("\n--- Cliente 2 inicia autenticação ---")
    client2_id = "client2:00:11:22:33:44:66"
    msg2 = client2_auth.start_authentication()

    # Servidor processa mensagem do Cliente 2
    print(f"\n--- Servidor processa mensagem do Cliente 2 ---")
    response2 = auth_handler.handle_auth_message(msg2, client2_id)

    # Simular troca completa de mensagens
    while response2:
        # Cliente 2 processa resposta do servidor
        print(f"\n--- Cliente 2 processa resposta ---")
        continue_auth, client_response = client2_auth.process_message(response2)

        if not continue_auth:
            break

        if client_response:
            # Servidor processa resposta do Cliente 2
            print(f"\n--- Servidor processa resposta do Cliente 2 ---")
            response2 = auth_handler.handle_auth_message(client_response, client2_id)
        else:
            break

    # Verificar se Cliente 2 está autenticado
    if auth_handler.is_authenticated(client2_id):
        print(f"\n✅ Cliente 2 está AUTENTICADO no servidor")
    else:
        print(f"\n❌ Cliente 2 NÃO está autenticado")

    print("\n" + "=" * 60)
    print("4. Resumo")
    print("=" * 60)

    auth_clients = auth_handler.get_authenticated_clients()
    print(f"\nClientes autenticados: {len(auth_clients)}")
    for client_id in auth_clients:
        peer_info = auth_handler.get_peer_info(client_id)
        print(f"  - {client_id}: {peer_info['nid']} ({'SINK' if peer_info['is_sink'] else 'NODE'})")

    print(f"\nCallbacks de sucesso chamados: {len(authenticated_clients)}")
    print(f"Callbacks de falha chamados: {len(failed_clients)}")

    if len(auth_clients) == 2 and len(failed_clients) == 0:
        print("\n" + "=" * 60)
        print("✅ TESTE PASSOU COM SUCESSO!")
        print("=" * 60)
        print("\nResumo:")
        print("  - AuthenticationHandler criado com sucesso")
        print("  - Múltiplas sessões geridas corretamente")
        print("  - 2 clientes autenticados com sucesso")
        print("  - Callbacks funcionam corretamente")
        return 0
    else:
        print("\n❌ TESTE FALHOU!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
