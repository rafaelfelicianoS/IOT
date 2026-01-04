#!/usr/bin/env python3
"""
Debug SimpleBLE - Ver exatamente o que o SimpleBLE retorna durante scan.
"""

import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import simplepyble
    SIMPLEBLE_AVAILABLE = True
except ImportError:
    print("❌ SimpleBLE não está disponível!")
    sys.exit(1)

def main():
    print("=" * 70)
    print("  DEBUG SimpleBLE - Ver o que está a ser retornado")
    print("=" * 70)
    print()

    # Obter adaptador
    adapters = simplepyble.Adapter.get_adapters()
    if not adapters:
        print("❌ Nenhum adaptador BLE encontrado!")
        return 1

    adapter = adapters[0]
    print(f"Adaptador: {adapter.identifier()}")
    print(f"Address: {adapter.address()}")
    print()

    # Fazer scan
    print("A fazer scan durante 5 segundos...")
    adapter.scan_for(5000)
    peripherals = adapter.scan_get_results()

    print(f"\n✅ SimpleBLE retornou {len(peripherals)} periféricos\n")

    if len(peripherals) == 0:
        print("⚠️  NENHUM periférico encontrado pelo SimpleBLE!")
        print()
        print("Isto pode significar:")
        print("  1. Não há dispositivos BLE a fazer advertising")
        print("  2. O adaptador BLE não tem permissões")
        print("  3. SimpleBLE tem problemas de compatibilidade")
        print()
        return 1

    for i, peripheral in enumerate(peripherals, 1):
        print(f"\n{'='*70}")
        print(f"PERIFÉRICO {i}:")
        print(f"{'='*70}")

        # Informação básica
        print(f"  Address: {peripheral.address()}")
        print(f"  Identifier: {peripheral.identifier()}")
        print(f"  RSSI: {peripheral.rssi()} dBm")
        print(f"  Connectable: {peripheral.is_connectable()}")
        print()

        # Métodos disponíveis
        print(f"  Métodos disponíveis no Peripheral:")
        methods = [m for m in dir(peripheral) if not m.startswith('_')]
        for method in methods:
            print(f"    - {method}")
        print()

        # Tentar obter manufacturer data
        print(f"  Manufacturer Data:")
        try:
            if hasattr(peripheral, 'manufacturer_data'):
                mfr_data = peripheral.manufacturer_data()
                if mfr_data:
                    for mfr_id, data in mfr_data.items():
                        print(f"    Manufacturer ID {mfr_id}: {bytes(data).hex()}")
                else:
                    print(f"    (vazio)")
            else:
                print(f"    (método não disponível)")
        except Exception as e:
            print(f"    ❌ Erro: {e}")
        print()

        # Tentar obter service data
        print(f"  Service Data:")
        try:
            if hasattr(peripheral, 'service_data'):
                svc_data = peripheral.service_data()
                if svc_data:
                    for uuid, data in svc_data.items():
                        print(f"    Service {uuid}: {bytes(data).hex()}")
                else:
                    print(f"    (vazio)")
            else:
                print(f"    (método não disponível)")
        except Exception as e:
            print(f"    ❌ Erro: {e}")
        print()

        # Tentar obter services (provavelmente só após conexão)
        print(f"  Services:")
        try:
            if hasattr(peripheral, 'services'):
                services = peripheral.services()
                if services:
                    for service in services:
                        print(f"    Service UUID: {service.uuid()}")
                else:
                    print(f"    (vazio)")
            else:
                print(f"    (método não disponível)")
        except Exception as e:
            print(f"    ❌ Erro (esperado - services só após conexão): {e}")
        print()

    print()
    print("=" * 70)
    return 0

if __name__ == '__main__':
    sys.exit(main())
