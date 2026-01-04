#!/usr/bin/env python3
"""
Lista adaptadores Bluetooth disponíveis no sistema.

Este script ajuda a identificar qual adaptador BLE usar nos testes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import simplepyble as simpleble
except ImportError:
    print(" SimpleBLE não está disponível!")
    print("   Instalar com: pip install simplepyble")
    sys.exit(1)


def main():
    print("=" * 70)
    print("  ADAPTADORES BLUETOOTH DISPONÍVEIS")
    print("=" * 70)
    print()

    adapters = simpleble.Adapter.get_adapters()

    if not adapters:
        print(" Nenhum adaptador Bluetooth encontrado!")
        print()
        print("Verifique:")
        print("  1. Bluetooth está ativado?")
        print("  2. hciconfig -a")
        print("  3. systemctl status bluetooth")
        return 1

    print(f"Encontrados {len(adapters)} adaptador(es):")
    print()

    for i, adapter in enumerate(adapters):
        identifier = adapter.identifier()
        print(f"  [{i}] {identifier}")
        try:
            address = adapter.address()
            print(f"      Endereço: {address}")
        except RuntimeError:
            print(f"      (Adaptador virtual/inválido)")
        print()

    print("=" * 70)
    print("Para usar um adaptador específico:")
    print()
    print("  # Usar hci0 (adaptador 0)")
    print("  python3 test_packet_send.py hci0")
    print("  sudo python3 test_packet_receive.py hci0")
    print()
    print("  # Usar hci1 (adaptador 1)")
    print("  python3 test_packet_send.py hci1")
    print("  sudo python3 test_packet_receive.py hci1")
    print("=" * 70)
    print()

    return 0


if __name__ == '__main__':
    sys.exit(main())
