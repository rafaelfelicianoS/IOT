#!/usr/bin/env python3
"""
Teste de Notificações de Heartbeat.

Este script testa se as notificações de heartbeat funcionam quando o Sink
envia heartbeats periódicos via NetworkPacketCharacteristic.

Uso:
    Terminal 1 (Server): sudo python3 examples/test_gatt_server.py hci0
    Terminal 2 (Client): python3 examples/test_heartbeat_notifications.py
"""

import sys
import time
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient, SIMPLEBLE_AVAILABLE
from common.utils.constants import IOT_NETWORK_SERVICE_UUID, CHAR_NETWORK_PACKET_UUID
from common.utils.logger import setup_logger
from common.protocol.heartbeat import parse_heartbeat_packet, HeartbeatMonitor
from common.network.packet import Packet
from common.security import ReplayProtection

# Setup logger
logger = setup_logger("test_heartbeat_notifications")


def main():
    """Main function."""

    logger.info("=" * 70)
    logger.info("  Test: Heartbeat Notifications")
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

    # Criar heartbeat monitor
    monitor = HeartbeatMonitor(timeout_count=3)
    logger.info("💓 Heartbeat Monitor iniciado")
    logger.info("")

    # Criar protetor de replay
    replay_protector = ReplayProtection(window_size=100)
    logger.info("🛡️  Replay Protection iniciado")
    logger.info("")

    # Contador de notificações recebidas
    notification_count = 0
    heartbeat_count = 0
    replay_count = 0
    last_sequence = None

    def notification_handler(data: bytes):
        """Handler para notificações de pacotes."""
        nonlocal notification_count, heartbeat_count, replay_count, last_sequence

        notification_count += 1

        logger.info("")
        logger.info(f"🔔 NOTIFICAÇÃO #{notification_count} RECEBIDA!")
        logger.info(f"   📊 Dados completos ({len(data)} bytes): {data[:32].hex()}...")

        try:
            # Parsear pacote
            packet = Packet.from_bytes(data)
            logger.info(f"   📦 Pacote parseado:")
            logger.info(f"      Source: {packet.source}")
            logger.info(f"      Destination: {packet.destination}")
            logger.info(f"      Type: {packet.msg_type} (0x{packet.msg_type:02x})")
            logger.info(f"      TTL: {packet.ttl}")
            logger.info(f"      Sequence: {packet.sequence}")
            logger.info(f"      Payload size: {len(packet.payload)} bytes")

            # Verificar MAC do pacote
            mac_valid = packet.verify_mac()
            if mac_valid:
                logger.info(f"      ✅ MAC válido")
            else:
                logger.warning(f"      ❌ MAC INVÁLIDO - Pacote pode ter sido modificado!")
                return  # Ignorar pacote com MAC inválido

            # Verificar replay attack
            is_not_replay = replay_protector.check_and_update(packet.source, packet.sequence)
            if not is_not_replay:
                replay_count += 1
                logger.warning(f"      🚨 REPLAY ATTACK DETECTADO! (total: {replay_count})")
                return  # Ignorar pacote replay

            logger.info(f"      ✅ Não é replay")

            # Verificar se é heartbeat
            heartbeat = parse_heartbeat_packet(packet)
            if heartbeat:
                heartbeat_count += 1
                monitor.on_heartbeat_received(heartbeat)

                logger.info(f"   💓 HEARTBEAT DETECTADO!")
                logger.info(f"      Sink NID: {heartbeat.sink_nid}")
                logger.info(f"      Timestamp: {heartbeat.timestamp:.2f}")
                logger.info(f"      Age: {heartbeat.age():.2f}s")
                logger.info(f"      Signature: {'<placeholder>' if heartbeat.signature == b'\\x00' * 64 else '<signed>'}")

                # Verificar sequência
                if last_sequence is not None:
                    expected = last_sequence + 1
                    if packet.sequence != expected:
                        logger.warning(f"      ⚠️  Sequência inesperada! Esperado: {expected}, Recebido: {packet.sequence}")
                    else:
                        logger.info(f"      ✅ Sequência correta ({packet.sequence})")

                last_sequence = packet.sequence

                # Mostrar estatísticas do monitor
                stats = monitor.get_stats()
                logger.info(f"   📊 Monitor Stats:")
                logger.info(f"      Total heartbeats: {stats['total_received']}")
                logger.info(f"      Time since last: {stats['time_since_last']:.2f}s")
                logger.info(f"      Missed count: {stats['missed_count']}")

            else:
                logger.info(f"   ℹ️  Pacote não é heartbeat (tipo: 0x{packet.msg_type:02x})")

        except Exception as e:
            logger.error(f"   ❌ Erro ao parsear pacote: {e}")

        logger.info("")

    # Subscrever notificações
    logger.info("=" * 70)
    logger.info("📡 A subscrever notificações de NetworkPacket...")
    logger.info("=" * 70)
    logger.info("")

    success = conn.subscribe_notifications(
        IOT_NETWORK_SERVICE_UUID,
        CHAR_NETWORK_PACKET_UUID,
        notification_handler
    )

    if not success:
        logger.error("❌ Falha ao subscrever notificações")
        return 1

    logger.info("✅ Subscrição bem-sucedida!")
    logger.info("")
    logger.info("=" * 70)
    logger.info("📝 AGUARDANDO HEARTBEATS:")
    logger.info("=" * 70)
    logger.info("")
    logger.info("O servidor deve enviar heartbeats a cada 5 segundos.")
    logger.info("Este cliente irá:")
    logger.info("  1. Receber notificações via NetworkPacketCharacteristic")
    logger.info("  2. Parsear os pacotes")
    logger.info("  3. Identificar heartbeats")
    logger.info("  4. Monitorizar timeouts")
    logger.info("")
    logger.info("=" * 70)
    logger.info("⏳ A aguardar heartbeats (pressiona Ctrl+C para terminar)...")
    logger.info("=" * 70)
    logger.info("")

    # Aguardar por notificações (mantém conexão ativa)
    try:
        while True:
            time.sleep(1)

            # A cada 15 segundos, mostra status e verifica timeout
            if int(time.time()) % 15 == 0:
                logger.info(f"⏱️  Status: {notification_count} notificações, {heartbeat_count} heartbeats")

                # Verificar timeout
                if monitor.check_timeout():
                    logger.error("💔 TIMEOUT! Não recebemos heartbeats há muito tempo!")
                    logger.error("   O servidor pode ter crashado ou perdemos conexão.")

    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 70)
        logger.info("👋 A terminar...")
        logger.info("=" * 70)
        logger.info("")
        logger.info(f"📊 RESUMO:")
        logger.info(f"   Total de notificações: {notification_count}")
        logger.info(f"   Total de heartbeats: {heartbeat_count}")
        logger.info(f"   Replays detectados: {replay_count}")

        # Estatísticas finais do monitor
        stats = monitor.get_stats()
        if stats['last_heartbeat'] is not None:
            logger.info(f"   Último heartbeat: {stats['time_since_last']:.2f}s atrás")
            logger.info(f"   Sink NID: {stats['sink_nid']}")

        # Estatísticas do protetor de replay
        replay_stats = replay_protector.get_stats()
        logger.info(f"   Sources tracked: {replay_stats['tracked_sources']}")

        logger.info("")

    # Desconectar
    conn.disconnect()
    logger.info("✅ Desconectado")
    logger.info("")

    return 0


if __name__ == '__main__':
    sys.exit(main())
