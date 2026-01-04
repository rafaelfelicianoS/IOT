#!/usr/bin/env python3
"""
Teste de Neighbor Discovery.

Este script testa a descoberta automática de vizinhos BLE.
Faz scan periódico, conecta aos dispositivos, lê DeviceInfo,
e mantém lista atualizada de vizinhos.

Uso:
    python3 examples/test_neighbor_discovery.py
"""

import sys
import time
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient, SIMPLEBLE_AVAILABLE
from common.network.neighbor_discovery import NeighborDiscovery, NeighborInfo
from common.utils.logger import setup_logger

# Setup logger
logger = setup_logger("test_neighbor_discovery")


def main():
    """Main function."""

    logger.info("=" * 70)
    logger.info("  Test: Neighbor Discovery")
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

    logger.info("✅ BLE Client criado")
    logger.info("")

    # Criar NeighborDiscovery
    discovery = NeighborDiscovery(
        client=client,
        scan_interval=30,      # Scan a cada 30 segundos
        scan_duration=5000,    # Cada scan dura 5 segundos
        neighbor_timeout=120,  # Remove vizinhos não vistos há 2 minutos
    )

    logger.info("✅ NeighborDiscovery criado")
    logger.info(f"   Scan interval: {discovery.scan_interval}s")
    logger.info(f"   Scan duration: {discovery.scan_duration}ms")
    logger.info(f"   Neighbor timeout: {discovery.neighbor_timeout}s")
    logger.info("")

    # Configurar callbacks
    def on_neighbor_discovered(neighbor: NeighborInfo):
        """Callback quando um novo vizinho é descoberto."""
        logger.info("")
        logger.info("🆕 NOVO VIZINHO DESCOBERTO!")
        logger.info(f"   Address: {neighbor.address}")
        logger.info(f"   NID: {neighbor.nid}")
        logger.info(f"   Hop Count: {neighbor.hop_count}")
        logger.info(f"   Device Type: {neighbor.device_type}")
        logger.info(f"   RSSI: {neighbor.rssi} dBm")
        logger.info("")

    def on_neighbor_updated(neighbor: NeighborInfo):
        """Callback quando um vizinho é atualizado."""
        logger.debug(f"🔄 Vizinho atualizado: {neighbor.address}")

    def on_neighbor_lost(neighbor: NeighborInfo):
        """Callback quando um vizinho é perdido (timeout)."""
        logger.info("")
        logger.info("💔 VIZINHO PERDIDO (TIMEOUT)!")
        logger.info(f"   Address: {neighbor.address}")
        logger.info(f"   NID: {neighbor.nid}")
        logger.info(f"   Último visto: {neighbor.age():.1f}s atrás")
        logger.info("")

    discovery.on_neighbor_discovered = on_neighbor_discovered
    discovery.on_neighbor_updated = on_neighbor_updated
    discovery.on_neighbor_lost = on_neighbor_lost

    # Fazer primeiro scan
    logger.info("=" * 70)
    logger.info("🔍 A fazer primeiro scan...")
    logger.info("=" * 70)
    logger.info("")

    try:
        discovered = discovery.scan_once()

        logger.info("")
        logger.info("=" * 70)
        logger.info(f"📊 RESULTADO DO SCAN")
        logger.info("=" * 70)
        logger.info(f"Total de vizinhos descobertos: {len(discovered)}")
        logger.info("")

        if discovered:
            logger.info("Lista de vizinhos:")
            for i, neighbor in enumerate(discovered, 1):
                logger.info(f"  {i}. {neighbor}")

            logger.info("")

            # Mostrar melhor vizinho
            best = discovery.get_best_neighbor()
            if best:
                logger.info(f"🏆 Melhor vizinho (menor hop count):")
                logger.info(f"   {best}")
                logger.info("")

        # Mostrar estatísticas
        stats = discovery.get_stats()
        logger.info("📊 Estatísticas:")
        logger.info(f"   Total de vizinhos: {stats['total_neighbors']}")
        logger.info(f"   Vizinhos conectados: {stats['connected_neighbors']}")
        logger.info(f"   Melhor hop count: {stats['best_hop_count']}")
        logger.info(f"   Última scan: {stats['last_scan_age']:.1f}s atrás")

        if stats['neighbors_by_hop']:
            logger.info(f"   Vizinhos por hop count:")
            for hop, count in sorted(stats['neighbors_by_hop'].items()):
                logger.info(f"      hop={hop}: {count} vizinhos")

        logger.info("")

        # Loop de scans periódicos
        logger.info("=" * 70)
        logger.info("🔄 MODO CONTÍNUO")
        logger.info("=" * 70)
        logger.info("")
        logger.info(f"Vou fazer scan a cada {discovery.scan_interval}s.")
        logger.info("Pressiona Ctrl+C para terminar.")
        logger.info("")

        scan_count = 1

        while True:
            # Aguardar até próximo scan
            time.sleep(discovery.scan_interval)

            scan_count += 1
            logger.info("=" * 70)
            logger.info(f"🔍 Scan #{scan_count}")
            logger.info("=" * 70)
            logger.info("")

            # Fazer scan
            discovered = discovery.scan_once()

            logger.info(f"Scan concluído: {len(discovered)} vizinhos encontrados")

            # Mostrar estatísticas atualizadas
            stats = discovery.get_stats()
            logger.info(f"Total de vizinhos conhecidos: {stats['total_neighbors']}")

            best = discovery.get_best_neighbor()
            if best:
                logger.info(f"Melhor rota: {best.address} (hop={best.hop_count})")

            logger.info("")

    except KeyboardInterrupt:
        logger.info("")
        logger.info("=" * 70)
        logger.info("👋 A terminar...")
        logger.info("=" * 70)
        logger.info("")

        # Estatísticas finais
        stats = discovery.get_stats()
        logger.info("📊 RESUMO FINAL:")
        logger.info(f"   Total de vizinhos descobertos: {stats['total_neighbors']}")

        if stats['total_neighbors'] > 0:
            logger.info("")
            logger.info("   Lista final de vizinhos:")
            for neighbor in discovery.get_neighbors():
                logger.info(f"      {neighbor}")

            logger.info("")
            best = discovery.get_best_neighbor()
            if best:
                logger.info(f"   Melhor rota: {best.address} (hop={best.hop_count})")

        logger.info("")

    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
