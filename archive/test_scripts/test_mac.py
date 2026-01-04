#!/usr/bin/env python3
"""
Teste de implementação do MAC (HMAC-SHA256) para pacotes.

Este script testa:
1. Cálculo de MAC em pacotes
2. Verificação de MAC válido
3. Detecção de MAC inválido (pacote modificado)
4. Integração com heartbeats
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.nid import NID
from common.network.packet import Packet
from common.utils.constants import MessageType
from common.protocol.heartbeat import create_heartbeat_packet
from common.security.crypto import calculate_hmac, verify_hmac

def test_basic_hmac():
    """Testa funções básicas de HMAC."""
    print("=" * 60)
    print("1. Teste de HMAC Básico")
    print("=" * 60)

    # Dados de teste
    data = b"Hello, IoT Network!"

    # Calcular MAC
    mac = calculate_hmac(data)
    print(f"✅ MAC calculado: {mac.hex()[:32]}...")
    print(f"   Tamanho: {len(mac)} bytes")

    # Verificar MAC válido
    is_valid = verify_hmac(data, mac)
    print(f"✅ Verificação de MAC válido: {is_valid}")
    assert is_valid, "MAC válido deveria ser aceite"

    # Verificar MAC inválido (dados modificados)
    modified_data = b"Hello, IoT Network?"  # Mudou ! para ?
    is_valid = verify_hmac(modified_data, mac)
    print(f"✅ Verificação de dados modificados: {is_valid}")
    assert not is_valid, "MAC inválido deveria ser rejeitado"

    print()

def test_packet_mac():
    """Testa MAC em pacotes."""
    print("=" * 60)
    print("2. Teste de MAC em Pacotes")
    print("=" * 60)

    # Criar NIDs
    source_nid = NID.generate()
    dest_nid = NID.generate()

    # Criar pacote
    packet = Packet.create(
        source=source_nid,
        destination=dest_nid,
        msg_type=MessageType.DATA,
        payload=b"Test data payload",
        sequence=1,
    )

    print(f"📦 Pacote criado: src={source_nid}, dst={dest_nid}")
    print(f"   Tipo: {MessageType.to_string(packet.msg_type)}")
    print(f"   Sequence: {packet.sequence}")
    print(f"   MAC inicial: {packet.mac.hex()[:32]}... (placeholder)")

    # Calcular MAC
    packet.calculate_and_set_mac()
    print(f"✅ MAC calculado: {packet.mac.hex()[:32]}...")

    # Verificar MAC
    is_valid = packet.verify_mac()
    print(f"✅ Verificação de MAC: {is_valid}")
    assert is_valid, "MAC do pacote deveria ser válido"

    # Serializar e desserializar
    packet_bytes = packet.to_bytes()
    print(f"✅ Pacote serializado: {len(packet_bytes)} bytes")

    packet_restored = Packet.from_bytes(packet_bytes)
    print(f"✅ Pacote desserializado")

    # Verificar MAC do pacote restaurado
    is_valid = packet_restored.verify_mac()
    print(f"✅ MAC após serialização: {is_valid}")
    assert is_valid, "MAC deveria permanecer válido após serialização"

    # Tentar modificar o payload e verificar que MAC falha
    packet_restored.payload = b"Modified payload!"
    is_valid = packet_restored.verify_mac()
    print(f"✅ MAC com payload modificado: {is_valid}")
    assert not is_valid, "MAC deveria falhar com payload modificado"

    print()

def test_heartbeat_mac():
    """Testa MAC em heartbeats."""
    print("=" * 60)
    print("3. Teste de MAC em Heartbeats")
    print("=" * 60)

    # Criar heartbeat
    sink_nid = NID.generate()
    heartbeat = create_heartbeat_packet(sink_nid, sequence=42)

    print(f"💓 Heartbeat criado: sink={sink_nid}")
    print(f"   Sequence: {heartbeat.sequence}")
    print(f"   Tamanho: {heartbeat.size()} bytes")
    print(f"   MAC: {heartbeat.mac.hex()[:32]}...")

    # Verificar que heartbeat tem MAC válido
    is_valid = heartbeat.verify_mac()
    print(f"✅ MAC do heartbeat: {is_valid}")
    assert is_valid, "Heartbeat deveria ter MAC válido"

    # Serializar e verificar
    heartbeat_bytes = heartbeat.to_bytes()
    heartbeat_restored = Packet.from_bytes(heartbeat_bytes)

    is_valid = heartbeat_restored.verify_mac()
    print(f"✅ MAC após serialização: {is_valid}")
    assert is_valid, "MAC deveria permanecer válido"

    print()

def test_mac_tampering():
    """Testa detecção de tampering em diferentes campos."""
    print("=" * 60)
    print("4. Teste de Detecção de Tampering")
    print("=" * 60)

    # Criar pacote
    source_nid = NID.generate()
    dest_nid = NID.generate()

    packet = Packet.create(
        source=source_nid,
        destination=dest_nid,
        msg_type=MessageType.DATA,
        payload=b"Original data",
        sequence=100,
        ttl=10,
    )
    packet.calculate_and_set_mac()

    print("📦 Pacote original criado com MAC válido")

    # Teste 1: Modificar TTL
    original_ttl = packet.ttl
    packet.ttl = 5
    is_valid = packet.verify_mac()
    print(f"✅ MAC com TTL modificado ({original_ttl}→{packet.ttl}): {is_valid}")
    assert not is_valid, "MAC deveria falhar com TTL modificado"
    packet.ttl = original_ttl  # Restaurar

    # Teste 2: Modificar sequence
    original_seq = packet.sequence
    packet.sequence = 999
    is_valid = packet.verify_mac()
    print(f"✅ MAC com sequence modificado ({original_seq}→{packet.sequence}): {is_valid}")
    assert not is_valid, "MAC deveria falhar com sequence modificado"
    packet.sequence = original_seq  # Restaurar

    # Teste 3: Modificar msg_type
    original_type = packet.msg_type
    packet.msg_type = MessageType.HEARTBEAT
    is_valid = packet.verify_mac()
    print(f"✅ MAC com tipo modificado (DATA→HEARTBEAT): {is_valid}")
    assert not is_valid, "MAC deveria falhar com tipo modificado"
    packet.msg_type = original_type  # Restaurar

    # Verificar que pacote restaurado tem MAC válido
    is_valid = packet.verify_mac()
    print(f"✅ MAC após restaurar valores originais: {is_valid}")
    assert is_valid, "MAC deveria ser válido novamente"

    print()

def main():
    """Main function."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║       Teste de Implementação de MAC (HMAC-SHA256)         ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    try:
        test_basic_hmac()
        test_packet_mac()
        test_heartbeat_mac()
        test_mac_tampering()

        print("=" * 60)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("=" * 60)
        print()
        print("Conclusão:")
        print("  - HMAC-SHA256 está a funcionar corretamente")
        print("  - Pacotes podem calcular e verificar MACs")
        print("  - Heartbeats são criados com MAC válido")
        print("  - Tampering é detetado em todos os campos")
        print()

        return 0

    except AssertionError as e:
        print()
        print("=" * 60)
        print(f"❌ TESTE FALHOU: {e}")
        print("=" * 60)
        return 1
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ ERRO: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
