#!/usr/bin/env python3
"""
Testa receção de pacotes no servidor GATT.

Este script:
1. Inicia um servidor GATT
2. Regista callback para pacotes recebidos
3. Aguarda por pacotes
4. Valida e processa pacotes recebidos
"""

import sys
import time
from pathlib import Path
import signal

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_server import Application, Service, register_application
from common.ble.advertising import Advertisement, register_advertisement
from common.ble.gatt_services import (
    IoTNetworkService,
    NetworkPacketCharacteristic,
)
from common.network.packet import Packet
from common.network.packet_manager import PacketManager
from common.utils.nid import NID
from common.utils.constants import MessageType
from common.utils.logger import setup_logger

logger = setup_logger("test_packet_receive")

# Chave partilhada de teste (32 bytes) - DEVE ser a mesma que no sender
TEST_SHARED_KEY = b'test_key_1234567890_32bytes!!!'

running = True


def signal_handler(sig, frame):
    """Handler para Ctrl+C."""
    global running
    print("\n\n  A terminar...")
    running = False


def main():
    if len(sys.argv) < 2:
        print("Uso: sudo python3 test_packet_receive.py <hci_interface>")
        print("Exemplo: sudo python3 test_packet_receive.py hci0")
        print("         sudo python3 test_packet_receive.py hci1")
        return 1

    adapter_name = sys.argv[1]

    print("=" * 70)
    print("  TEST PACKET RECEIVE - Receber pacotes no servidor")
    print("=" * 70)
    print(f"  Adaptador: {adapter_name}")
    print("=" * 70)
    print()

    # Registar signal handler
    signal.signal(signal.SIGINT, signal_handler)

    print("1⃣  A criar PacketManager...")
    local_nid = NID.generate()
    packet_manager = PacketManager(local_nid, TEST_SHARED_KEY)
    print(f"    PacketManager criado")
    print(f"      Local NID: {local_nid}")
    print()

    # Contador de pacotes
    packets_received = 0
    packets_valid = 0

    # Callback para quando um pacote é recebido
    def on_packet_received(packet_bytes: bytes):
        """Processa um pacote recebido."""
        nonlocal packets_received, packets_valid

        packets_received += 1

        print()
        print("-" * 70)
        print(f" PACOTE RECEBIDO #{packets_received}")
        print("-" * 70)
        print(f"   Raw bytes: {len(packet_bytes)} bytes")
        print()

        try:
            # Desserializar pacote
            packet = Packet.from_bytes(packet_bytes)
            print(f"    Pacote desserializado:")
            print(f"      Source: {packet.source}")
            print(f"      Destination: {packet.destination}")
            print(f"      Type: {MessageType.to_string(packet.msg_type)}")
            print(f"      TTL: {packet.ttl}")
            print(f"      Sequence: {packet.sequence}")
            print(f"      Payload size: {len(packet.payload)} bytes")
            print()

            if packet_manager.validate_packet(packet):
                packets_valid += 1
                print(f"    PACOTE VÁLIDO (MAC verificado)")
                print()

                # Mostrar payload se for DATA
                if packet.msg_type == MessageType.DATA:
                    try:
                        payload_str = packet.payload.decode('utf-8')
                        print(f"    Payload (texto):")
                        print(f"      {payload_str}")
                    except:
                        print(f"    Payload (hex):")
                        print(f"      {packet.payload.hex()}")
                    print()

                # Processar com packet manager
                packet_manager.handle_received_packet(packet)

            else:
                print(f"    PACOTE INVÁLIDO (MAC ou TTL)")
                print()

        except Exception as e:
            print(f"    Erro ao processar pacote: {e}")
            import traceback
            traceback.print_exc()
            print()

        print("-" * 70)
        print()

    # Registar handler para DATA packets
    def on_data_packet(packet: Packet):
        """Handler específico para pacotes DATA."""
        print(f"    Handler DATA chamado para seq={packet.sequence}")

    packet_manager.register_handler(MessageType.DATA, on_data_packet)

    print("2⃣  A criar servidor GATT...")
    try:
        import dbus
        import dbus.mainloop.glib

        # Setup D-Bus mainloop ANTES de criar objetos D-Bus
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

        # Get system bus
        bus = dbus.SystemBus()

        app = Application(bus)

        service = IoTNetworkService(
            bus=bus,
            path="/org/bluez/iot",
            index=0,
            device_nid=local_nid,
            device_type="node"
        )

        # Configurar callback para pacotes recebidos
        characteristics = service.get_characteristics()
        packet_char = characteristics[0]  # NetworkPacketCharacteristic é a primeira
        if isinstance(packet_char, NetworkPacketCharacteristic):
            packet_char.set_packet_callback(on_packet_received)
            print(f"    Callback de pacotes configurado")

        app.add_service(service)
        print()

        print("=" * 70)
        print("   A REGISTAR SERVIDOR E AGUARDAR PACOTES...")
        print("  Pressione Ctrl+C para terminar")
        print("=" * 70)
        print()

        # Configurar adaptador como discoverable
        print("3⃣  A configurar adaptador BLE...")
        try:
            adapter_path = f"/org/bluez/{adapter_name}"
            adapter_obj = bus.get_object('org.bluez', adapter_path)
            adapter_props = dbus.Interface(adapter_obj, 'org.freedesktop.DBus.Properties')

            # Ativar Discoverable e Pairable
            adapter_props.Set('org.bluez.Adapter1', 'Discoverable', dbus.Boolean(True))
            adapter_props.Set('org.bluez.Adapter1', 'Pairable', dbus.Boolean(True))
            print(f"    Adaptador configurado como discoverable e pairable")
        except Exception as e:
            print(f"     Aviso: Não foi possível configurar discoverable: {e}")
        print()

        # Registar application e obter mainloop
        print("4⃣  A registar GATT application...")
        mainloop = register_application(app, adapter_name=adapter_name)
        print(f"    GATT Application registada")
        print()

        print("5⃣  A criar BLE Advertisement...")
        adv = Advertisement(bus, 0, Advertisement.TYPE_PERIPHERAL)
        adv.add_service_uuid(service.uuid)

        from common.utils.constants import IOT_MANUFACTURER_ID, IOT_MANUFACTURER_DATA_MAGIC
        adv.add_manufacturer_data(IOT_MANUFACTURER_ID, IOT_MANUFACTURER_DATA_MAGIC)

        print(f"    Advertisement criado com serviço {service.uuid}")
        print(f"    Manufacturer data adicionado: ID={hex(IOT_MANUFACTURER_ID)}, data={IOT_MANUFACTURER_DATA_MAGIC}")
        print()

        print("6⃣  A registar Advertisement...")
        register_advertisement(adv, adapter_name)
        print(f"    Advertisement registado - dispositivo agora é visível!")
        print()

        # Aguardar até Ctrl+C
        try:
            mainloop.run()
        except KeyboardInterrupt:
            pass

        print()
        print("=" * 70)
        print("  ESTATÍSTICAS:")
        print(f"    Pacotes recebidos: {packets_received}")
        print(f"    Pacotes válidos: {packets_valid}")
        print(f"    Pacotes inválidos: {packets_received - packets_valid}")
        print("=" * 70)
        print()

        # Cleanup
        mainloop.quit()

        return 0

    except Exception as e:
        print(f" Erro ao criar servidor: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
