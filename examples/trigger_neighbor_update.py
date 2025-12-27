#!/usr/bin/env python3
"""
Helper: Trigger Neighbor Table Update

Este script injeta mudanças na neighbor table do servidor via um ficheiro de trigger.
O servidor monitoriza este ficheiro e quando deteta mudanças, atualiza a neighbor table.

Uso:
    python3 examples/trigger_neighbor_update.py <num_neighbors>

Exemplos:
    python3 examples/trigger_neighbor_update.py 1  # Adiciona 1 vizinho
    python3 examples/trigger_neighbor_update.py 3  # Adiciona 3 vizinhos
    python3 examples/trigger_neighbor_update.py 0  # Remove todos
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.nid import NID


def main(argv):
    """Main function."""

    if len(argv) < 2:
        print("Uso: python3 trigger_neighbor_update.py <num_neighbors>")
        print("")
        print("Exemplos:")
        print("  python3 trigger_neighbor_update.py 1")
        print("  python3 trigger_neighbor_update.py 3")
        print("  python3 trigger_neighbor_update.py 0")
        return 1

    try:
        num_neighbors = int(argv[1])
    except ValueError:
        print(f"❌ Erro: '{argv[1]}' não é um número válido")
        return 1

    if num_neighbors < 0 or num_neighbors > 10:
        print(f"❌ Erro: Número de vizinhos deve estar entre 0 e 10")
        return 1

    print(f"🔧 A preparar trigger para {num_neighbors} vizinhos...")
    print("")

    # Gerar vizinhos aleatórios
    neighbors = []
    for i in range(num_neighbors):
        nid = NID.generate()
        hop_count = i  # Hop count incrementa
        neighbors.append({'nid': nid, 'hop_count': hop_count})
        print(f"  Vizinho {i+1}:")
        print(f"    NID: {nid}")
        print(f"    Hop Count: {hop_count}")

    # Criar ficheiro trigger
    trigger_file = Path("trigger_neighbor_update.txt")

    with open(trigger_file, 'w') as f:
        f.write(f"{num_neighbors}\n")
        for neighbor in neighbors:
            f.write(f"{neighbor['nid'].to_string()},{neighbor['hop_count']}\n")

    print("")
    print(f"✅ Ficheiro trigger criado: {trigger_file}")
    print("")
    print("📝 PRÓXIMO PASSO:")
    print("   O servidor precisa monitorizar este ficheiro e aplicar as mudanças.")
    print("   Atualmente isto é manual - vais precisar modificar test_gatt_server.py")
    print("   para incluir um FileSystemWatcher ou atualizar manualmente.")
    print("")
    print("💡 SOLUÇÃO RÁPIDA:")
    print("   1. Para no servidor (Ctrl+C)")
    print("   2. Modifica o código para ler este ficheiro no início")
    print("   3. Reinicia o servidor")
    print("")

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
