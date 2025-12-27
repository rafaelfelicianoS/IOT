#!/usr/bin/env python3
"""
Development Helper Script

Script de utilidades para ajudar no desenvolvimento do projeto.
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple


def count_lines_of_code() -> Tuple[int, int]:
    """
    Conta linhas de código Python no projeto.

    Returns:
        (total_lines, code_lines) - linhas totais e linhas de código (sem comentários/vazias)
    """
    total = 0
    code = 0

    for root, dirs, files in os.walk('.'):
        # Ignorar diretórios
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'venv', '.git', 'docs']]

        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        total += len(lines)

                        for line in lines:
                            stripped = line.strip()
                            # Contar se não for vazia nem comentário
                            if stripped and not stripped.startswith('#'):
                                code += 1
                except Exception as e:
                    print(f"Erro ao ler {filepath}: {e}")

    return total, code


def list_python_files() -> List[Path]:
    """
    Lista todos os ficheiros Python do projeto.

    Returns:
        Lista de Paths
    """
    files = []

    for root, dirs, filenames in os.walk('.'):
        # Ignorar diretórios
        dirs[:] = [d for d in dirs if d not in ['__pycache__', 'venv', '.git']]

        for filename in filenames:
            if filename.endswith('.py'):
                filepath = Path(root) / filename
                files.append(filepath)

    return sorted(files)


def check_structure():
    """Verifica se a estrutura de diretórios está correta."""
    required_dirs = [
        'sink',
        'node',
        'node/sensors',
        'common',
        'common/ble',
        'common/network',
        'common/security',
        'common/protocol',
        'common/utils',
        'support',
        'tests',
    ]

    print("📁 Verificando estrutura de diretórios...\n")

    all_ok = True
    for dir_path in required_dirs:
        exists = Path(dir_path).is_dir()
        status = "✅" if exists else "❌"
        print(f"  {status} {dir_path}")
        if not exists:
            all_ok = False

    return all_ok


def show_stats():
    """Mostra estatísticas do projeto."""
    print("\n📊 Estatísticas do Projeto\n")
    print("=" * 60)

    # Linhas de código
    total_lines, code_lines = count_lines_of_code()
    print(f"\n📝 Linhas de Código:")
    print(f"  Total:  {total_lines:,}")
    print(f"  Código: {code_lines:,}")

    # Ficheiros
    py_files = list_python_files()
    print(f"\n📄 Ficheiros Python: {len(py_files)}")

    # Módulos por diretório
    print(f"\n📦 Módulos por Diretório:")
    dirs_count = {}
    for f in py_files:
        dir_name = str(f.parent)
        if dir_name not in dirs_count:
            dirs_count[dir_name] = 0
        dirs_count[dir_name] += 1

    for dir_name, count in sorted(dirs_count.items()):
        if dir_name != '.':
            print(f"  {dir_name}: {count} ficheiros")

    print("\n" + "=" * 60)


def show_next_steps():
    """Mostra os próximos passos do desenvolvimento."""
    print("\n🎯 Próximos Passos\n")
    print("=" * 60)
    print("\n📌 Fase 1: BLE Básico (PRIORITÁRIO)\n")
    print("  1. Criar common/ble/gatt_server.py")
    print("     - Adaptar exemplo docs/src-exploring-bluetooth/gatt_server.py")
    print("     - Classes: Application, Service, Characteristic, Descriptor")
    print()
    print("  2. Criar common/ble/gatt_services.py")
    print("     - IoTNetworkService")
    print("     - NetworkPacketCharacteristic")
    print("     - DeviceInfoCharacteristic")
    print("     - NeighborTableCharacteristic")
    print("     - AuthCharacteristic")
    print()
    print("  3. Criar common/ble/gatt_client.py")
    print("     - BLEScanner")
    print("     - BLEConnection")
    print("     - BLEClient")
    print()
    print("  4. Criar common/network/link_manager.py")
    print("     - Link (wrapper sobre BLE connection)")
    print("     - LinkManager (uplink + downlinks)")
    print()
    print("📖 Consultar PROJECT_STATUS.md para roadmap completo")
    print("=" * 60)


def main():
    """Main function."""
    print("\n" + "=" * 60)
    print("  IoT Bluetooth Network - Development Helper")
    print("=" * 60)

    # Verificar estrutura
    check_structure()

    # Mostrar estatísticas
    show_stats()

    # Mostrar próximos passos
    show_next_steps()

    print()


if __name__ == "__main__":
    main()
