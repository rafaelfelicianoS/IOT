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

# Adicionar o diretório raiz ao path
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
    print("=" * 70)
    print("  TEST PACKET SEND - Enviar pacote para o servidor")
    print("=" * 70)
    print()

    # Criar cliente
    print("1️⃣  A criar cliente BLE...")
    client = BLEClient()
    print(f"   ✅ Cliente criado: {client.scanner.adapter.identifier()}")
    print()

    # Fazer scan
    print(f"2️⃣  A fazer scan para encontrar {TARGET_SERVER}...")
    devices = client.scanner.scan(duration_ms=5000, filter_iot=False)
    print(f"   ✅ Scan concluído: {len(devices)} dispositivos encontrados")
    print()

    # Procurar o servidor
    target = None
    for dev in devices:
        if dev.address.upper() == TARGET_SERVER.upper():
            target = dev
            break

    if not target:
        print(f"❌ Servidor {TARGET_SERVER} NÃO encontrado no scan!")
        return 1

    print(f"✅ Servidor encontrado: {target.address}")
    print()

    # Conectar
    print("3️⃣  A conectar ao servidor...")
    conn = client.connect_to_device(target)

    if not conn:
        print("❌ Falha ao conectar!")
        return 1

    print(f"   ✅ Conectado com sucesso!")
    print()

    # Criar PacketManager
    print("4️⃣  A criar PacketManager...")
    local_nid = NID.generate()
    packet_manager = PacketManager(local_nid, TEST_SHARED_KEY)
    print(f"   ✅ PacketManager criado")
    print(f"      Local NID: {local_nid}")
    print()

    # Criar pacote de teste
    print("5️⃣  A criar pacote de teste...")
    dest_nid = NID.generate()  # NID de destino fictício
    test_payload = b"Hello from test_packet_send! This is a test message."

    packet = packet_manager.create_data_packet(
        destination=dest_nid,
        data=test_payload
    )

    print(f"   ✅ Pacote criado:")
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
    print(f"   📦 Pacote serializado: {len(packet_bytes)} bytes")
    print()

    # Enviar pacote
    print("6️⃣  A enviar pacote via NETWORK_PACKET characteristic...")
    try:
        success = conn.write_characteristic(
            IOT_NETWORK_SERVICE_UUID,
            CHAR_NETWORK_PACKET_UUID,
            packet_bytes
        )

        if success:
            print(f"   ✅ Pacote enviado com sucesso!")
        else:
            print(f"   ❌ Falha ao enviar pacote")
            success = False

    except Exception as e:
        print(f"   ❌ Erro ao enviar pacote: {e}")
        import traceback
        traceback.print_exc()
        success = False

    print()

    # Desconectar
    print("7️⃣  A desconectar...")
    client.disconnect_from_device(target.address)
    print("   ✅ Desconectado")
    print()

    print("=" * 70)
    if success:
        print("  ✅ SUCESSO - Pacote enviado com sucesso!")
    else:
        print("  ❌ FALHA - Não foi possível enviar o pacote")
    print("=" * 70)
    print()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
