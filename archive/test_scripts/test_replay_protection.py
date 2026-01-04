#!/usr/bin/env python3
"""
Teste de Proteção contra Replay Attacks.

Este script testa se a proteção contra replay funciona corretamente:
1. Aceita pacotes com sequence numbers novos
2. Rejeita pacotes duplicados (mesmo sequence number)
3. Rejeita pacotes muito antigos (fora da janela)
4. Aceita reordenamento dentro da janela
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.nid import NID
from common.security.replay_protection import ReplayProtection


def test_basic_replay_detection():
    """Testa detecção básica de replay."""
    print("=" * 60)
    print("1. Teste de Detecção Básica de Replay")
    print("=" * 60)

    protector = ReplayProtection(window_size=10)
    source_nid = NID.generate()

    # Primeiro pacote: deve ser aceite
    is_valid = protector.check_and_update(source_nid, sequence=1)
    print(f"✅ Sequence 1 (primeiro): {is_valid}")
    assert is_valid, "Primeiro pacote deveria ser aceite"

    # Segundo pacote: deve ser aceite
    is_valid = protector.check_and_update(source_nid, sequence=2)
    print(f"✅ Sequence 2 (novo): {is_valid}")
    assert is_valid, "Pacote com sequence novo deveria ser aceite"

    # Replay do primeiro pacote: deve ser rejeitado
    is_valid = protector.check_and_update(source_nid, sequence=1)
    print(f"✅ Sequence 1 (replay): {is_valid}")
    assert not is_valid, "Replay deveria ser rejeitado"

    # Replay do segundo pacote: deve ser rejeitado
    is_valid = protector.check_and_update(source_nid, sequence=2)
    print(f"✅ Sequence 2 (replay): {is_valid}")
    assert not is_valid, "Replay deveria ser rejeitado"

    print()


def test_reordering_within_window():
    """Testa aceitação de reordenamento dentro da janela."""
    print("=" * 60)
    print("2. Teste de Reordenamento Dentro da Janela")
    print("=" * 60)

    protector = ReplayProtection(window_size=10)
    source_nid = NID.generate()

    # Enviar pacotes: 1, 2, 3, 5, 4 (4 chega atrasado mas dentro da janela)
    sequences = [1, 2, 3, 5, 4]

    for seq in sequences:
        is_valid = protector.check_and_update(source_nid, sequence=seq)
        print(f"  Sequence {seq}: {'✅ aceite' if is_valid else '❌ rejeitado'}")
        assert is_valid, f"Sequence {seq} deveria ser aceite (dentro da janela)"

    print(f"✅ Reordenamento dentro da janela funcionou")
    print()


def test_window_expiration():
    """Testa rejeição de pacotes fora da janela."""
    print("=" * 60)
    print("3. Teste de Expiração da Janela")
    print("=" * 60)

    protector = ReplayProtection(window_size=10)
    source_nid = NID.generate()

    # Enviar pacote com sequence 1
    is_valid = protector.check_and_update(source_nid, sequence=1)
    print(f"✅ Sequence 1: aceite")
    assert is_valid

    # Avançar muito no tempo (sequence 20)
    is_valid = protector.check_and_update(source_nid, sequence=20)
    print(f"✅ Sequence 20: aceite (novo highest)")
    assert is_valid

    # Tentar enviar sequence 1 novamente (fora da janela: 20 - 10 = 10)
    is_valid = protector.check_and_update(source_nid, sequence=1)
    print(f"✅ Sequence 1 (fora da janela): rejeitado={not is_valid}")
    assert not is_valid, "Sequence fora da janela deveria ser rejeitado"

    # Sequence 11 ainda está dentro da janela (20 - 10 = 10, então 11 é válido)
    is_valid = protector.check_and_update(source_nid, sequence=11)
    print(f"✅ Sequence 11 (dentro da janela): aceite={is_valid}")
    assert is_valid, "Sequence dentro da janela deveria ser aceite"

    # Sequence 9 está fora da janela
    is_valid = protector.check_and_update(source_nid, sequence=9)
    print(f"✅ Sequence 9 (fora da janela): rejeitado={not is_valid}")
    assert not is_valid, "Sequence fora da janela deveria ser rejeitado"

    print()


def test_multiple_sources():
    """Testa tracking de múltiplos sources independentes."""
    print("=" * 60)
    print("4. Teste de Múltiplos Sources")
    print("=" * 60)

    protector = ReplayProtection(window_size=10)

    source_a = NID.generate()
    source_b = NID.generate()

    # Source A: sequence 1
    is_valid = protector.check_and_update(source_a, sequence=1)
    print(f"✅ Source A, seq 1: {is_valid}")
    assert is_valid

    # Source B: sequence 1 (independente de A)
    is_valid = protector.check_and_update(source_b, sequence=1)
    print(f"✅ Source B, seq 1: {is_valid}")
    assert is_valid, "Sources diferentes devem ter tracking independente"

    # Source A: sequence 1 novamente (replay)
    is_valid = protector.check_and_update(source_a, sequence=1)
    print(f"✅ Source A, seq 1 (replay): {is_valid}")
    assert not is_valid, "Replay de A deveria ser rejeitado"

    # Source B: sequence 2 (válido)
    is_valid = protector.check_and_update(source_b, sequence=2)
    print(f"✅ Source B, seq 2: {is_valid}")
    assert is_valid

    # Verificar stats
    stats = protector.get_stats()
    print(f"\n📊 Estatísticas:")
    print(f"   Tracked sources: {stats['tracked_sources']}")
    print(f"   Window size: {stats['window_size']}")
    assert stats['tracked_sources'] == 2, "Deveria ter 2 sources tracked"

    print()


def test_reset_source():
    """Testa reset de tracking de um source."""
    print("=" * 60)
    print("5. Teste de Reset de Source")
    print("=" * 60)

    protector = ReplayProtection(window_size=10)
    source_nid = NID.generate()

    # Enviar alguns pacotes
    protector.check_and_update(source_nid, sequence=1)
    protector.check_and_update(source_nid, sequence=2)
    protector.check_and_update(source_nid, sequence=3)

    print(f"✅ Enviados sequences 1, 2, 3")

    # Sequence 1 é replay (rejeitado)
    is_valid = protector.check_and_update(source_nid, sequence=1)
    print(f"✅ Sequence 1 antes do reset: rejeitado={not is_valid}")
    assert not is_valid

    # Reset tracking
    protector.reset_source(source_nid)
    print(f"✅ Tracking resetado para source")

    # Sequence 1 agora é aceite (como se fosse novo)
    is_valid = protector.check_and_update(source_nid, sequence=1)
    print(f"✅ Sequence 1 após reset: aceite={is_valid}")
    assert is_valid, "Após reset, sequence 1 deveria ser aceite novamente"

    print()


def main():
    """Main function."""
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     Teste de Proteção contra Replay Attacks               ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print()

    try:
        test_basic_replay_detection()
        test_reordering_within_window()
        test_window_expiration()
        test_multiple_sources()
        test_reset_source()

        print("=" * 60)
        print("✅ TODOS OS TESTES PASSARAM!")
        print("=" * 60)
        print()
        print("Conclusão:")
        print("  - Replay detection está a funcionar corretamente")
        print("  - Pacotes duplicados são rejeitados")
        print("  - Reordenamento dentro da janela é aceite")
        print("  - Pacotes fora da janela são rejeitados")
        print("  - Múltiplos sources são tracked independentemente")
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
