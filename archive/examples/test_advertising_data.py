#!/usr/bin/env python3
"""
Test: Ver se SimpleBLE expõe service UUIDs do advertising packet.
"""
import simplepyble

def main():
    adapters = simplepyble.Adapter.get_adapters()

    if not adapters:
        print("Nenhum adaptador BLE encontrado!")
        return 1

    # Usar o primeiro adaptador
    adapter = adapters[0]
    print(f"Adaptador: {adapter.identifier()}")
    print(f"Endereço: {adapter.address()}")
    print()

    print("A fazer scan de 5s...")
    adapter.scan_for(5000)
    peripherals = adapter.scan_get_results()

    print(f"Encontrados {len(peripherals)} dispositivos")
    print()

    for p in peripherals:
        print(f"Device: {p.identifier()} ({p.address()})")
        print(f"  RSSI: {p.rssi()}")
        print(f"  Connectable: {p.is_connectable()}")

        # Testar manufacturer_data() - isto funciona sem conectar
        try:
            mfr_data = p.manufacturer_data()
            print(f"  Manufacturer Data: {len(mfr_data)} entries")
            for mfr_id, data in mfr_data.items():
                print(f"    - ID {mfr_id}: {data.hex()}")
        except Exception as e:
            print(f"  Manufacturer Data: Erro - {e}")

        # Testar services() - SERÁ QUE ISTO FUNCIONA SEM CONECTAR?
        try:
            services = p.services()
            print(f"  Services (SEM conexão): {len(services)} serviços")
            for s in services:
                print(f"    - UUID: {s.uuid()}")
        except Exception as e:
            print(f"  Services (SEM conexão): Erro - {e}")

        print()

    return 0

if __name__ == '__main__':
    exit(main())
