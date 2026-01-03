#!/usr/bin/env python3
"""
Teste de encriptação end-to-end em mensagens reais.

Este teste verifica que:
1. Node encripta mensagens antes de enviar
2. Sink desencripta mensagens ao receber
3. Mensagens corrompidas são rejeitadas
"""

import sys
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent))

from common.security import DTLSChannel
from common.utils.nid import NID
from common.network.packet import Packet
from common.utils.constants import MessageType
import os


def test_end_to_end_message_encryption():
    """Testa encriptação/desencriptação de mensagens end-to-end."""
    print("\n" + "=" * 70)
    print("TESTE: Encriptação End-to-End em Mensagens")
    print("=" * 70)

    try:
        # Certificados de teste
        certs_dir = Path(__file__).parent / "certs"
        ca_cert = certs_dir / "ca_certificate.pem"
        node_certs = list(certs_dir.glob("node_*_cert.pem"))

        if not node_certs:
            print("\n⚠️  Nenhum certificado encontrado")
            print("   Execute: cd support && ./create_certificates.sh\n")
            return False

        node_cert = node_certs[0]
        node_key = node_cert.parent / node_cert.name.replace("_cert.pem", "_key.pem")

        # Criar NIDs
        node_nid = NID.generate()
        sink_nid = NID.generate()

        print(f"\n📝 Node NID: {str(node_nid)[:16]}...")
        print(f"📝 Sink NID: {str(sink_nid)[:16]}...")

        # Criar canais DTLS (simular Node e Sink)
        print("\n1️⃣  Criando canais DTLS...")
        node_channel = DTLSChannel(
            cert_path=node_cert,
            key_path=node_key,
            ca_cert_path=ca_cert,
            is_server=False,
            peer_nid=sink_nid
        )

        sink_channel = DTLSChannel(
            cert_path=node_cert,  # Usando mesmo cert só para teste
            key_path=node_key,
            ca_cert_path=ca_cert,
            is_server=True,
            peer_nid=node_nid
        )

        # Estabelecer canais
        print("\n2️⃣  Estabelecendo canais...")
        if not node_channel.establish():
            print("❌ Falha ao estabelecer canal do Node")
            return False

        if not sink_channel.establish():
            print("❌ Falha ao estabelecer canal do Sink")
            return False

        print("✅ Canais estabelecidos")

        # Derivar chaves (mesma session key para ambos)
        print("\n3️⃣  Derivando chaves de encriptação...")
        session_key = os.urandom(32)
        node_channel.derive_encryption_key(session_key)
        sink_channel.derive_encryption_key(session_key)
        print("✅ Chaves derivadas")

        # Simular envio de mensagem do Node
        print("\n4️⃣  Node: Enviando mensagem encriptada...")
        original_message = b"Hello Sink! This is a test message from IoT Node."
        print(f"   Mensagem original: {original_message.decode()}")
        print(f"   Tamanho: {len(original_message)} bytes")

        # Encriptar (wrap)
        encrypted_payload = node_channel.wrap(original_message)
        print(f"\n   🔐 Encriptado: {len(encrypted_payload)} bytes")
        print(f"   Overhead: +{len(encrypted_payload) - len(original_message)} bytes (nonce + tag)")

        # Verificar que está diferente
        if encrypted_payload == original_message:
            print("❌ FALHA: Payload não foi encriptado!")
            return False
        print("   ✅ Payload foi encriptado (diferente do original)")

        # Simular recepção no Sink
        print("\n5️⃣  Sink: Recebendo e desencriptando...")

        # Desencriptar (unwrap)
        decrypted_payload = sink_channel.unwrap(encrypted_payload)

        if decrypted_payload is None:
            print("❌ FALHA: Não foi possível desencriptar")
            return False

        print(f"   🔓 Desencriptado: {len(decrypted_payload)} bytes")
        print(f"   Mensagem: {decrypted_payload.decode()}")

        # Verificar que é igual ao original
        if decrypted_payload != original_message:
            print("❌ FALHA: Mensagem desencriptada diferente da original!")
            print(f"   Original:      {original_message}")
            print(f"   Desencriptado: {decrypted_payload}")
            return False

        print("   ✅ Mensagem desencriptada corretamente")

        # Testar rejeição de mensagem corrompida
        print("\n6️⃣  Testando proteção de integridade...")
        corrupted = bytearray(encrypted_payload)
        corrupted[-5] ^= 0xFF  # Modificar byte no meio do ciphertext

        decrypted_corrupted = sink_channel.unwrap(bytes(corrupted))
        if decrypted_corrupted is None:
            print("   ✅ Mensagem corrompida rejeitada (tag inválida)")
        else:
            print("   ❌ FALHA: Mensagem corrompida aceita!")
            return False

        print("\n" + "=" * 70)
        print("✅ TESTE PASSOU - Encriptação end-to-end funcional!")
        print("=" * 70)
        print("\n📊 Resumo:")
        print(f"   • Mensagem original: {len(original_message)} bytes")
        print(f"   • Mensagem encriptada: {len(encrypted_payload)} bytes")
        print(f"   • Overhead: {len(encrypted_payload) - len(original_message)} bytes")
        print(f"   • Integridade: Protegida (GCM tag)")
        print(f"   • Confidencialidade: AES-256")
        print()

        return True

    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_end_to_end_message_encryption()
    sys.exit(0 if success else 1)
