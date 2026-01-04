#!/usr/bin/env python3
"""
Teste direto do SimpleBLE para ver o que recebemos nos scans.
"""
import sys
import simplepyble

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 test_simpleble_scan.py <adapter_index>")
        return 1

    adapter_index = int(sys.argv[1])

    adapters = simplepyble.Adapter.get_adapters()
    if adapter_index >= len(adapters):
        print(f"Adaptador {adapter_index} não encontrado!")
        return 1

    adapter = adapters[adapter_index]
    print(f"Usando adaptador: {adapter.identifier()} ({adapter.address()})")
    print()

    print("A fazer scan durante 10 segundos...")
    adapter.scan_for(10000)
    peripherals = adapter.scan_get_results()

    print(f"Encontrados {len(peripherals)} dispositivos:")
    print()

    for i, p in enumerate(peripherals, 1):
        print(f"{i}. {p.identifier()} ({p.address()})")
        print(f"   RSSI: {p.rssi()} dBm")

        try:
            services = p.services()
            print(f"   services() retornou: {len(services)} serviços")
            for s in services:
                print(f"      - UUID: {s.uuid()}")
                print(f"        Data: {s.data()}")
        except Exception as e:
            print(f"   services() erro: {e}")

        try:
            mfr_data = p.manufacturer_data()
            print(f"   manufacturer_data() retornou: {len(mfr_data)} entradas")
            for mfr_id, data in mfr_data.items():
                print(f"      - ID: {mfr_id}, Data: {bytes(data).hex()}")
        except Exception as e:
            print(f"   manufacturer_data() erro: {e}")

        print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
