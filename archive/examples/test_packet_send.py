#!/usr/bin/env python3
"""
Testa envio de pacotes pela rede IoT.

Este script:
1. Conecta ao servidor GATT
2. Cria um pacote de teste
3. Envia o pacote via característica NETWORK_PACKET
4. Verifica se foi enviado com sucesso
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient
from common.network.packet import Packet
from common.network.packet_manager import PacketManager
from common.utils.nid import NID
from common.utils.constants import MessageType, IOT_NETWORK_SERVICE_UUID, CHAR_NETWORK_PACKET_UUID
from common.utils.logger import setup_logger

logger = setup_logger("test_packet_send")

TARGET_SERVER = "E0:D3:62:D6:EE:A0"

# Chave partilhada de teste (32 bytes)
# Em produção, esta seria derivada do certificado
TEST_SHARED_KEY = b'test_key_1234567890_32bytes!!!'


def main():
    if len(sys.argv) < 2:
        print("Uso: python3 test_packet_send.py <hci_interface>")
        print("Exemplo: python3 test_packet_send.py hci0")
        print("         python3 test_packet_send.py hci1")
        return 1

    adapter_name = sys.argv[1]
    # Converter hciX para índice (hci0 -> 0, hci1 -> 1, etc.)
    adapter_index = int(adapter_name.replace('hci', ''))

    print("=" * 70)
    print("  TEST PACKET SEND - Enviar pacote para o servidor")
    print("=" * 70)
    print(f"  Adaptador: {adapter_name} (índice {adapter_index})")
    print("=" * 70)
    print()

    print("1⃣  A criar cliente BLE...")
    client = BLEClient(adapter_index=adapter_index)
    print(f"    Cliente criado: {client.scanner.adapter.identifier()}")
    print()

    # Fazer scan
    print(f"2⃣  A fazer scan para encontrar servidores IoT...")
    devices = client.scanner.scan(duration_ms=5000, filter_iot=True)
    print(f"    Scan concluído: {len(devices)} dispositivos encontrados")
    print()

    if len(devices) == 0:
        print(" Nenhum servidor IoT encontrado!")
        print()
        print("Certifica-te que:")
        print("  1. O servidor está a correr (sudo python3 test_packet_receive.py hci0)")
        print("  2. O servidor está noutra máquina (não podes conectar a ti próprio)")
        print("  3. Os dispositivos estão próximos")
        return 1

    # Mostrar dispositivos encontrados
    print(" Servidores IoT encontrados:")
    print()
    for i, dev in enumerate(devices):
        print(f"  [{i}] {dev.address}")
        if dev.name:
            print(f"      Nome: {dev.name}")
        print(f"      RSSI: {dev.rssi} dBm")
        print(f"      Serviços: {len(dev.service_uuids)}")
        print()

    # Procurar o servidor TARGET ou usar o primeiro
    target = None
    for dev in devices:
        if dev.address.upper() == TARGET_SERVER.upper():
            target = dev
            print(f" Servidor alvo {TARGET_SERVER} encontrado!")
            break

    if not target:
        print(f"  Servidor alvo {TARGET_SERVER} não encontrado")
        print(f"   A usar o primeiro servidor disponível: {devices[0].address}")
        target = devices[0]

    print()
    print(f" A conectar a: {target.address}")
    print()

    # Conectar
    print("3⃣  A conectar ao servidor...")
    conn = client.connect_to_device(target)

    if not conn:
        print(" Falha ao conectar!")
        return 1

    print(f"    Conectado com sucesso!")
    print()

    print("4⃣  A criar PacketManager...")
    local_nid = NID.generate()
    packet_manager = PacketManager(local_nid, TEST_SHARED_KEY)
    print(f"    PacketManager criado")
    print(f"      Local NID: {local_nid}")
    print()

    print("5⃣  A criar pacote de teste...")
    dest_nid = NID.generate()  # NID de destino fictício
    test_payload = b"Hello from test_packet_send! This is a test message."

    packet = packet_manager.create_data_packet(
        destination=dest_nid,
        data=test_payload
    )

    print(f"    Pacote criado:")
    print(f"      Source: {packet.source}")
    print(f"      Destination: {packet.destination}")
    print(f"      Type: {MessageType.to_string(packet.msg_type)}")
    print(f"      TTL: {packet.ttl}")
    print(f"      Sequence: {packet.sequence}")
    print(f"      Payload size: {len(packet.payload)} bytes")
    print(f"      Total size: {packet.size()} bytes")
    print()

    # Serializar pacote
    packet_bytes = packet.to_bytes()
    print(f"    Pacote serializado: {len(packet_bytes)} bytes")
    print()

    print("6⃣  A enviar pacote via NETWORK_PACKET characteristic...")
    try:
        success = conn.write_characteristic(
            IOT_NETWORK_SERVICE_UUID,
            CHAR_NETWORK_PACKET_UUID,
            packet_bytes
        )

        if success:
            print(f"    Pacote enviado com sucesso!")
        else:
            print(f"    Falha ao enviar pacote")
            success = False

    except Exception as e:
        print(f"    Erro ao enviar pacote: {e}")
        import traceback
        traceback.print_exc()
        success = False

    print()

    # Desconectar
    print("7⃣  A desconectar...")
    client.disconnect_from_device(target.address)
    print("    Desconectado")
    print()

    print("=" * 70)
    if success:
        print("   SUCESSO - Pacote enviado com sucesso!")
    else:
        print("   FALHA - Não foi possível enviar o pacote")
    print("=" * 70)
    print()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
