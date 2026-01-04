"""
Neighbor Discovery - Descoberta automática de vizinhos BLE.

Este módulo implementa a descoberta periódica de vizinhos na rede IoT.
Faz scan de dispositivos BLE, lê as suas DeviceInfo characteristics,
e mantém uma lista atualizada de vizinhos disponíveis.

A descoberta é usada para:
- Encontrar novos vizinhos
- Atualizar hop counts
- Decidir a melhor rota para o Sink
- Manter neighbor table atualizada
"""

import time
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime

from common.ble.gatt_client import BLEClient, BLEConnection, SIMPLEBLE_AVAILABLE
from common.utils.nid import NID
from common.utils.constants import (
    IOT_NETWORK_SERVICE_UUID,
    CHAR_DEVICE_INFO_UUID,
    HOP_COUNT_DISCONNECTED,
)
from common.utils.logger import get_logger

logger = get_logger("neighbor_discovery")


@dataclass
class NeighborInfo:
    """
    Informação sobre um vizinho descoberto.

    Attributes:
        address: Endereço BLE do vizinho
        nid: Network Identifier do vizinho
        hop_count: Número de hops até ao Sink
        device_type: Tipo do dispositivo ("node" ou "sink")
        rssi: RSSI (Received Signal Strength Indicator) em dBm
        last_seen: Timestamp da última vez que foi visto
        is_connected: Se estamos conectados a este vizinho
    """
    address: str
    nid: NID
    hop_count: int
    device_type: str
    rssi: int
    last_seen: float = field(default_factory=time.time)
    is_connected: bool = False

    def age(self) -> float:
        """
        Calcula há quanto tempo este vizinho foi visto.

        Returns:
            Tempo em segundos desde last_seen
        """
        return time.time() - self.last_seen

    def is_better_than(self, other: 'NeighborInfo') -> bool:
        """
        Verifica se este vizinho é melhor que outro para routing.

        Um vizinho é melhor se:
        1. Tem hop count menor (mais perto do Sink)
        2. Se hop count igual, tem RSSI melhor (sinal mais forte)

        Args:
            other: Outro vizinho para comparar

        Returns:
            True se este vizinho é melhor
        """
        if self.hop_count != other.hop_count:
            return self.hop_count < other.hop_count
        return self.rssi > other.rssi

    def __str__(self) -> str:
        """String representation."""
        age_str = f"{self.age():.1f}s ago"
        conn_str = "connected" if self.is_connected else "disconnected"
        return (
            f"{self.address} ({self.nid}) "
            f"hop={self.hop_count} rssi={self.rssi}dBm "
            f"type={self.device_type} {conn_str} seen={age_str}"
        )


class NeighborDiscovery:
    """
    Serviço de descoberta automática de vizinhos.

    Faz scan periódico de dispositivos BLE IoT, conecta para ler DeviceInfo,
    e mantém uma lista atualizada de vizinhos.
    """

    def __init__(
        self,
        client: BLEClient,
        scan_interval: int = 30,
        scan_duration: int = 5000,
        neighbor_timeout: int = 120,
    ):
        """
        Inicializa o serviço de descoberta.

        Args:
            client: BLE Client para fazer scans
            scan_interval: Intervalo entre scans (segundos)
            scan_duration: Duração de cada scan (ms)
            neighbor_timeout: Tempo antes de remover vizinho (segundos)
        """
        self.client = client
        self.scan_interval = scan_interval
        self.scan_duration = scan_duration
        self.neighbor_timeout = neighbor_timeout

        # Dicionário de vizinhos: address -> NeighborInfo
        self.neighbors: Dict[str, NeighborInfo] = {}

        # Callbacks
        self.on_neighbor_discovered: Optional[Callable[[NeighborInfo], None]] = None
        self.on_neighbor_updated: Optional[Callable[[NeighborInfo], None]] = None
        self.on_neighbor_lost: Optional[Callable[[NeighborInfo], None]] = None

        self._running = False
        self._last_scan = 0

        logger.info(
            f"NeighborDiscovery inicializado: "
            f"scan_interval={scan_interval}s, "
            f"scan_duration={scan_duration}ms, "
            f"timeout={neighbor_timeout}s"
        )

    def scan_once(self) -> List[NeighborInfo]:
        """
        Faz um scan único e descobre vizinhos.

        Returns:
            Lista de vizinhos descobertos neste scan
        """
        logger.info("A iniciar scan de vizinhos...")

        # Pequeno delay entre scans para limpar cache BLE
        import time
        if self._last_scan > 0:
            time_since_last = time.time() - self._last_scan
            if time_since_last < 2.0:
                delay = 2.0 - time_since_last
                logger.debug(f"Aguardando {delay:.1f}s para limpar cache BLE...")
                time.sleep(delay)

        # Limpar cache do scanner antes de novo scan
        try:
            self.client.scanner.clear_cache()
        except Exception as e:
            logger.debug(f"Erro ao limpar cache (ignorado): {e}")

        # Scan de dispositivos IoT
        devices = self.client.scan_iot_devices(duration_ms=self.scan_duration)
        logger.info(f"Scan concluído: {len(devices)} dispositivos IoT encontrados")

        discovered = []

        for device in devices:
            try:
                # Conectar ao dispositivo
                logger.debug(f"A conectar a {device.address} para ler DeviceInfo...")
                conn = self.client.connect_to_device(device)

                if not conn:
                    logger.warning(f"Falha ao conectar a {device.address}")
                    continue

                # Ler DeviceInfo
                device_info = conn.read_characteristic(
                    IOT_NETWORK_SERVICE_UUID,
                    CHAR_DEVICE_INFO_UUID,
                )

                if not device_info or len(device_info) < 18:
                    logger.warning(f"DeviceInfo inválido de {device.address}")
                    conn.disconnect()
                    continue

                # Parsear DeviceInfo
                nid_bytes = device_info[0:16]
                hop_count = int.from_bytes(device_info[16:17], 'big', signed=True)
                device_type = "sink" if device_info[17] == 1 else "node"

                nid = NID.from_bytes(nid_bytes)

                neighbor = NeighborInfo(
                    address=device.address,
                    nid=nid,
                    hop_count=hop_count,
                    device_type=device_type,
                    rssi=device.rssi,
                    last_seen=time.time(),
                    is_connected=False,  # Vamos desconectar após ler
                )

                discovered.append(neighbor)

                logger.info(f"Vizinho descoberto: {neighbor}")

                # Desconectar
                conn.disconnect()

                # Atualizar dicionário de vizinhos
                if device.address in self.neighbors:
                    # Vizinho já conhecido - atualizar
                    old_neighbor = self.neighbors[device.address]
                    self.neighbors[device.address] = neighbor

                    # Callback de update
                    if self.on_neighbor_updated:
                        self.on_neighbor_updated(neighbor)

                    # Log se hop count mudou
                    if old_neighbor.hop_count != neighbor.hop_count:
                        logger.info(
                            f"Hop count de {device.address} mudou: "
                            f"{old_neighbor.hop_count} → {neighbor.hop_count}"
                        )

                else:
                    # Novo vizinho
                    self.neighbors[device.address] = neighbor

                    # Callback de descoberta
                    if self.on_neighbor_discovered:
                        self.on_neighbor_discovered(neighbor)

                    logger.info(f"Novo vizinho adicionado: {device.address}")

            except Exception as e:
                logger.error(f"Erro ao processar {device.address}: {e}")
                continue

        # Remover vizinhos antigos (timeout)
        self._remove_stale_neighbors()

        self._last_scan = time.time()

        return discovered

    def _remove_stale_neighbors(self):
        """Remove vizinhos que não foram vistos há muito tempo."""
        current_time = time.time()
        to_remove = []

        for address, neighbor in self.neighbors.items():
            if current_time - neighbor.last_seen > self.neighbor_timeout:
                to_remove.append(address)

        for address in to_remove:
            neighbor = self.neighbors.pop(address)
            logger.info(f"Vizinho removido (timeout): {address}")

            # Callback de perda
            if self.on_neighbor_lost:
                self.on_neighbor_lost(neighbor)

    def get_neighbors(self) -> List[NeighborInfo]:
        """
        Obtém lista de todos os vizinhos conhecidos.

        Returns:
            Lista de vizinhos
        """
        return list(self.neighbors.values())

    def get_neighbor(self, address: str) -> Optional[NeighborInfo]:
        """
        Obtém informação de um vizinho específico.

        Args:
            address: Endereço BLE do vizinho

        Returns:
            NeighborInfo se encontrado, None caso contrário
        """
        return self.neighbors.get(address)

    def get_best_neighbor(self) -> Optional[NeighborInfo]:
        """
        Encontra o melhor vizinho para routing (menor hop count).

        Returns:
            Melhor vizinho, ou None se nenhum disponível
        """
        if not self.neighbors:
            return None

        # Filtrar vizinhos válidos (hop_count >= 0)
        valid_neighbors = [
            n for n in self.neighbors.values()
            if n.hop_count >= 0
        ]

        if not valid_neighbors:
            return None

        # Ordenar por hop count, depois RSSI
        sorted_neighbors = sorted(
            valid_neighbors,
            key=lambda n: (n.hop_count, -n.rssi)
        )

        return sorted_neighbors[0]

    def get_neighbors_by_hop_count(self, hop_count: int) -> List[NeighborInfo]:
        """
        Obtém todos os vizinhos com um hop count específico.

        Args:
            hop_count: Hop count para filtrar

        Returns:
            Lista de vizinhos com esse hop count
        """
        return [
            n for n in self.neighbors.values()
            if n.hop_count == hop_count
        ]

    def mark_connected(self, address: str, connected: bool = True):
        """
        Marca um vizinho como conectado/desconectado.

        Args:
            address: Endereço do vizinho
            connected: True se conectado, False se desconectado
        """
        if address in self.neighbors:
            self.neighbors[address].is_connected = connected
            logger.debug(f"Vizinho {address} marcado como {'conectado' if connected else 'desconectado'}")

    def get_stats(self) -> Dict:
        """
        Obtém estatísticas do neighbor discovery.

        Returns:
            Dicionário com estatísticas
        """
        if not self.neighbors:
            return {
                'total_neighbors': 0,
                'connected_neighbors': 0,
                'best_hop_count': None,
                'last_scan_age': time.time() - self._last_scan if self._last_scan > 0 else None,
            }

        connected = sum(1 for n in self.neighbors.values() if n.is_connected)
        best = self.get_best_neighbor()

        return {
            'total_neighbors': len(self.neighbors),
            'connected_neighbors': connected,
            'best_hop_count': best.hop_count if best else None,
            'last_scan_age': time.time() - self._last_scan if self._last_scan > 0 else None,
            'neighbors_by_hop': {
                hop: len(self.get_neighbors_by_hop_count(hop))
                for hop in set(n.hop_count for n in self.neighbors.values())
            }
        }

    def __str__(self) -> str:
        """String representation."""
        stats = self.get_stats()
        return (
            f"NeighborDiscovery("
            f"total={stats['total_neighbors']}, "
            f"connected={stats['connected_neighbors']}, "
            f"best_hop={stats['best_hop_count']})"
        )
