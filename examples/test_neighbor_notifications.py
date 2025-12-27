#!/usr/bin/env python3
"""
Teste de Notificações de Neighbor Table.

Este script testa se as notificações funcionam quando a neighbor table é atualizada.

Uso:
    Terminal 1 (Server): sudo python3 examples/test_gatt_server.py hci0
    Terminal 2 (Client): python3 examples/test_neighbor_notifications.py
"""

import sys
import time
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient, SIMPLEBLE_AVAILABLE
from common.utils.constants import IOT_NETWORK_SERVICE_UUID, CHAR_NEIGHBOR_TABLE_UUID
from common.utils.nid import NID
from common.utils.logger import setup_logger

# Setup logger
logger = setup_logger("test_neighbor_notifications")


def main():
    """Main function."""

    logger.info("=" * 70)
    logger.info("  Test: Neighbor Table Notifications")
    logger.info("=" * 70)
    logger.info("")

    # Verificar se SimpleBLE está disponível
    if not SIMPLEBLE_AVAILABLE:
        logger.error("❌ SimpleBLE não está instalado!")
        return 1

    # Criar cliente BLE
    try:
        client = BLEClient(adapter_index=0)
    except Exception as e:
        logger.error(f"❌ Erro ao criar BLE Client: {e}")
        return 1

    # Fazer scan de dispositivos IoT
    logger.info("🔍 A fazer scan de dispositivos IoT...")
    devices = client.scan_iot_devices(duration_ms=5000)

    if not devices:
        logger.warning("⚠️  Nenhum dispositivo IoT encontrado")
        logger.info("Certifica-te que o GATT Server está a correr:")
        logger.info("  sudo python3 examples/test_gatt_server.py hci0")
        return 0

    logger.info(f"✅ Encontrados {len(devices)} dispositivos IoT")
    logger.info(f"   Conectando ao primeiro: {devices[0].address}")
    logger.info("")

    # Conectar ao primeiro dispositivo
    conn = client.connect_to_device(devices[0])
    if not conn:
        logger.error("❌ Falha ao conectar")
        return 1

    logger.info("✅ Conectado com sucesso!")
    logger.info("")

    # Ler neighbor table inicial
    logger.info("📖 A ler Neighbor Table inicial...")
    initial_data = conn.read_characteristic(
        IOT_NETWORK_SERVICE_UUID,
        CHAR_NEIGHBOR_TABLE_UUID
    )

    if initial_data:
        num_neighbors = initial_data[0]
        logger.info(f"   👥 Vizinhos iniciais: {num_neighbors}")
        logger.info(f"   Dados (hex): {initial_data.hex()}")
    else:
        logger.error("❌ Falha ao ler Neighbor Table")
        return 1

    logger.info("")

    # Contador de notificações recebidas
    notification_count = 0
    last_neighbors_count = None

    def notification_handler(data: bytes):
        """Handler para notificações."""
        nonlocal notification_count, last_neighbors_count

        notification_count += 1
        num_neighbors = data[0]

        logger.info("")
        logger.info(f"🔔 NOTIFICAÇÃO #{notification_count} RECEBIDA!")
        logger.info(f"   👥 Número de vizinhos: {num_neighbors}")
        logger.info(f"   📊 Dados completos ({len(data)} bytes): {data.hex()}")

        # Parse dos vizinhos
        if num_neighbors > 0:
            logger.info(f"   📋 Lista de vizinhos:")
            offset = 1
            for i in range(num_neighbors):
                if offset + 18 <= len(data):
                    nid_bytes = data[offset:offset+16]
                    hop_count = data[offset+16]
                    reserved = data[offset+17]

                    # Converter signed byte se necessário
                    if hop_count > 127:
                        hop_count = hop_count - 256

                    nid = NID(nid_bytes)
                    logger.info(f"      {i+1}. NID: {nid}")
                    logger.info(f"         Hop Count: {hop_count}")

                    offset += 18

        # Verificar se mudou
        if last_neighbors_count is not None and last_neighbors_count != num_neighbors:
            logger.info(f"   ⚠️  MUDANÇA DETECTADA: {last_neighbors_count} → {num_neighbors} vizinhos")

        last_neighbors_count = num_neighbors
        logger.info("")

    # Subscrever notificações
    logger.info("=" * 70)
    logger.info("📡 A subscrever notificações de Neighbor Table...")
    logger.info("=" * 70)
    logger.info("")

    success = conn.subscribe_notifications(
        IOT_NETWORK_SERVICE_UUID,
        CHAR_NEIGHBOR_TABLE_UUID,
        notification_handler
    )

    if not success:
        logger.error("❌ Falha ao subscrever notificações")
        return 1

    logger.info("✅ Subscrição bem-sucedida!")
    logger.info("")
    logger.info("=" * 70)
    logger.info("📝 INSTRUÇÕES:")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Agora, no servidor (Terminal 1), simula uma mudança na neighbor table:")
    logger.info("")
    logger.info("  1. Abre uma shell Python interativa no servidor:")
    logger.info("     → Ctrl+C no servidor (se estiver a correr)")
    logger.info("")
    logger.info("  2. No código do server, adiciona um timer que atualiza neighbors")
    logger.info("     → Ou usa D-Bus para injetar mudanças")
    logger.info("")
    logger.info("Alternativamente, vou criar um script helper para testar...")
    logger.info("")
    logger.info("=" * 70)
    logger.info("⏳ A aguardar notificações (pressiona Ctrl+C para terminar)...")
    logger.info("=" * 70)
    logger.info("")

    # Aguardar por notificações (mantém conexão ativa)
    try:
        while True:
            time.sleep(1)

            # A cada 10 segundos, mostra status
            if int(time.time()) % 10 == 0:
                logger.info(f"⏱️  Ainda a aguardar... ({notification_count} notificações recebidas até agora)")

    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 70)
        logger.info("👋 A terminar...")
        logger.info("=" * 70)
        logger.info("")
        logger.info(f"📊 RESUMO:")
        logger.info(f"   Total de notificações recebidas: {notification_count}")
        logger.info("")

    # Desconectar
    conn.disconnect()
    logger.info("✅ Desconectado")
    logger.info("")

    return 0


if __name__ == '__main__':
    sys.exit(main())
