"""
Network layer do projeto IoT Bluetooth Network.

Módulos:
- packet: Formato e manipulação de pacotes
- forwarding_table: Tabela de forwarding (switch learning)
- link_manager: Gestão de uplink/downlinks BLE
- neighbor_discovery: Descoberta automática de vizinhos
"""

from common.network.packet import Packet
from common.network.forwarding_table import ForwardingTable
from common.network.link_manager import Link, DeviceInfo, LinkManager
from common.network.neighbor_discovery import NeighborInfo, NeighborDiscovery

__all__ = [
    'Packet',
    'ForwardingTable',
    'Link',
    'DeviceInfo',
    'LinkManager',
    'NeighborInfo',
    'NeighborDiscovery',
]
