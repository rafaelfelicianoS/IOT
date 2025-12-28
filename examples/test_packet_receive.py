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

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_server import Application, Service
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
    print("\n\n⚠️  A terminar...")
    running = False


def main():
    print("=" * 70)
    print("  TEST PACKET RECEIVE - Receber pacotes no servidor")
    print("=" * 70)
    print()

    # Registar signal handler
    signal.signal(signal.SIGINT, signal_handler)

    # Criar NID e PacketManager
    print("1️⃣  A criar PacketManager...")
    local_nid = NID.generate()
    packet_manager = PacketManager(local_nid, TEST_SHARED_KEY)
    print(f"   ✅ PacketManager criado")
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
        print(f"📬 PACOTE RECEBIDO #{packets_received}")
        print("-" * 70)
        print(f"   Raw bytes: {len(packet_bytes)} bytes")
        print()

        try:
            # Desserializar pacote
            packet = Packet.from_bytes(packet_bytes)
            print(f"   ✅ Pacote desserializado:")
            print(f"      Source: {packet.source}")
            print(f"      Destination: {packet.destination}")
            print(f"      Type: {MessageType.to_string(packet.msg_type)}")
            print(f"      TTL: {packet.ttl}")
            print(f"      Sequence: {packet.sequence}")
            print(f"      Payload size: {len(packet.payload)} bytes")
            print()

            # Validar pacote
            if packet_manager.validate_packet(packet):
                packets_valid += 1
                print(f"   ✅ PACOTE VÁLIDO (MAC verificado)")
                print()

                # Mostrar payload se for DATA
                if packet.msg_type == MessageType.DATA:
                    try:
                        payload_str = packet.payload.decode('utf-8')
                        print(f"   📄 Payload (texto):")
                        print(f"      {payload_str}")
                    except:
                        print(f"   📄 Payload (hex):")
                        print(f"      {packet.payload.hex()}")
                    print()

                # Processar com packet manager
                packet_manager.handle_received_packet(packet)

            else:
                print(f"   ❌ PACOTE INVÁLIDO (MAC ou TTL)")
                print()

        except Exception as e:
            print(f"   ❌ Erro ao processar pacote: {e}")
            import traceback
            traceback.print_exc()
            print()

        print("-" * 70)
        print()

    # Registar handler para DATA packets
    def on_data_packet(packet: Packet):
        """Handler específico para pacotes DATA."""
        print(f"   🎯 Handler DATA chamado para seq={packet.sequence}")

    packet_manager.register_handler(MessageType.DATA, on_data_packet)

    # Criar servidor GATT
    print("2️⃣  A criar servidor GATT...")
    try:
        import dbus
        import dbus.mainloop.glib
        from gi.repository import GLib

        # Setup D-Bus
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()

        # Criar application
        app = Application(bus)

        # Criar IoT Network Service
        service = IoTNetworkService(
            bus=bus,
            path="/org/bluez/iot",
            index=0,
            device_nid=local_nid,
            device_type="node"
        )

        # Configurar callback para pacotes recebidos
        packet_char = service.get_characteristic(0)  # NetworkPacketCharacteristic
        if isinstance(packet_char, NetworkPacketCharacteristic):
            packet_char.set_packet_callback(on_packet_received)
            print(f"   ✅ Callback de pacotes configurado")

        # Adicionar service
        app.add_service(service)

        # Registar application
        app.register()
        print(f"   ✅ Servidor GATT registado")
        print()

        print("=" * 70)
        print("  🎧 AGUARDANDO PACOTES...")
        print("  Pressione Ctrl+C para terminar")
        print("=" * 70)
        print()

        # Loop principal
        mainloop = GLib.MainLoop()

        # Run mainloop em thread separada para permitir Ctrl+C
        import threading

        def run_mainloop():
            try:
                mainloop.run()
            except Exception as e:
                logger.error(f"Erro no mainloop: {e}")

        mainloop_thread = threading.Thread(target=run_mainloop, daemon=True)
        mainloop_thread.start()

        # Aguardar até Ctrl+C
        try:
            while running:
                time.sleep(1)
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
        app.unregister()

        return 0

    except Exception as e:
        print(f"❌ Erro ao criar servidor: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
