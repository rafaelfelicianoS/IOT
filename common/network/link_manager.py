"""
Link Manager - Gestão de links BLE (uplink e downlinks).

Cada dispositivo IoT tem:
- 1 uplink: conexão ao parent (em direção ao Sink)
- N downlinks: conexões a children (dispositivos que se conectaram a nós)
"""

import threading
from typing import Optional, List, Callable, Dict
from dataclasses import dataclass
from datetime import datetime

from common.ble.gatt_client import BLEConnection, ScannedDevice
from common.utils.nid import NID
from common.utils.logger import get_logger

logger = get_logger("link_manager")


# ============================================================================
# Link - Representa uma conexão BLE
# ============================================================================

@dataclass
class DeviceInfo:
    """
    Informação de um dispositivo remoto.
    """
    nid: NID
    hop_count: int
    device_type: str  # 'sink', 'node'

    def __str__(self):
        return f"{self.device_type.upper()} NID={self.nid} hop={self.hop_count}"

    @classmethod
    def from_bytes(cls, data: bytes) -> 'DeviceInfo':
        """
        Deserializa DeviceInfo a partir de bytes.
        
        Formato: NID (16 bytes) + hop_count (1 byte) + device_type (1 byte)
        
        Args:
            data: Bytes lidos da característica DeviceInfo
            
        Returns:
            DeviceInfo deserializado
            
        Raises:
            ValueError: Se os dados estiverem em formato inválido
        """
        if len(data) < 18:
            raise ValueError(f"DeviceInfo precisa de pelo menos 18 bytes, recebido {len(data)}")
        
        # Parse dos campos
        nid_bytes = data[:16]
        hop_count = data[16]
        device_type_byte = data[17]
        
        # Criar NID
        nid = NID(nid_bytes)
        
        # Mapear device_type
        device_type = 'sink' if device_type_byte == 0 else 'node'
        
        return cls(nid=nid, hop_count=hop_count, device_type=device_type)


class Link:
    """
    Representa uma conexão BLE (uplink ou downlink).

    Um Link é um wrapper sobre BLEConnection que adiciona:
    - Informação do dispositivo remoto (NID, hop count)
    - Callbacks para eventos (data received, disconnected)
    - Timestamp da última atividade
    """

    def __init__(
        self,
        connection: BLEConnection,
        device_info: DeviceInfo,
        is_uplink: bool = False,
    ):
        """
        Inicializa um Link.

        Args:
            connection: BLEConnection ao dispositivo remoto
            device_info: Informação do dispositivo remoto
            is_uplink: True se é uplink (parent), False se é downlink (child)
        """
        self.connection = connection
        self.device_info = device_info
        self.is_uplink = is_uplink
        self.address = connection.address

        # Timestamps
        self.created_at = datetime.now()
        self.last_activity = datetime.now()

        # Callbacks
        self._data_callback: Optional[Callable[[bytes], None]] = None
        self._disconnected_callback: Optional[Callable, None] = None

        logger.info(f"Link criado: {self} ({'UPLINK' if is_uplink else 'DOWNLINK'})")

    def __str__(self):
        return f"Link[{self.address}] -> {self.device_info}"

    def set_data_callback(self, callback: Callable[[bytes], None]):
        """
        Define callback para quando dados são recebidos.

        Args:
            callback: Função que recebe bytes
        """
        self._data_callback = callback

    def set_disconnected_callback(self, callback: Callable):
        """
        Define callback para quando a conexão é perdida.

        Args:
            callback: Função chamada quando desconecta
        """
        self._disconnected_callback = callback

    def send(self, data: bytes, service_uuid: str, char_uuid: str) -> bool:
        """
        Envia dados através do link.

        Args:
            data: Dados a enviar
            service_uuid: UUID do serviço GATT
            char_uuid: UUID da característica GATT

        Returns:
            True se enviado com sucesso
        """
        if not self.connection.is_connected:
            logger.warning(f"Link {self.address} não está conectado")
            return False

        success = self.connection.write_characteristic(service_uuid, char_uuid, data)
        if success:
            self.last_activity = datetime.now()
            logger.debug(f"Dados enviados via {self}: {len(data)} bytes")
        return success

    def disconnect(self):
        """Desconecta o link."""
        self.connection.disconnect()
        if self._disconnected_callback:
            self._disconnected_callback()


# ============================================================================
# Link Manager
# ============================================================================

class LinkManager:
    """
    Gestor de links BLE.

    Responsável por:
    - Gerir o uplink (conexão ao parent)
    - Gerir downlinks (conexões de children)
    - Conectar/desconectar de vizinhos
    - Notificar eventos (novo link, link perdido)
    """

    def __init__(self, client: 'BLEClient'):
        """
        Inicializa o Link Manager.

        Args:
            client: BLE Client para operações de conexão
        """
        from common.ble.gatt_client import BLEClient

        self.client: BLEClient = client
        self.uplink: Optional[Link] = None
        self.downlinks: Dict[str, Link] = {}  # address -> Link

        # Callbacks
        self._new_downlink_callbacks: List[Callable[[Link], None]] = []
        self._lost_link_callbacks: List[Callable[[Link], None]] = []

        # Lock para thread safety
        self._lock = threading.Lock()

        logger.info("Link Manager iniciado")

    # ========================================================================
    # Uplink Management
    # ========================================================================

    def set_uplink(self, connection: BLEConnection, device_info: DeviceInfo) -> Link:
        """
        Define o uplink (conexão ao parent).

        Args:
            connection: BLEConnection ao parent
            device_info: Informação do parent

        Returns:
            Link criado
        """
        with self._lock:
            # Se já existe uplink, desconectar
            if self.uplink:
                logger.warning("Uplink já existe - a substituir")
                self.uplink.disconnect()

            # Criar novo uplink
            link = Link(connection, device_info, is_uplink=True)
            link.set_disconnected_callback(self._on_uplink_disconnected)

            self.uplink = link
            logger.info(f"✅ Uplink definido: {link}")

            return link

    def clear_uplink(self):
        """Remove o uplink."""
        with self._lock:
            if self.uplink:
                self.uplink.disconnect()
                self.uplink = None
                logger.info("Uplink removido")

    def get_uplink(self) -> Optional[Link]:
        """Retorna o uplink atual."""
        return self.uplink

    def has_uplink(self) -> bool:
        """Verifica se tem uplink."""
        return self.uplink is not None and self.uplink.connection.is_connected

    def _on_uplink_disconnected(self):
        """Callback quando uplink é desconectado."""
        logger.warning("⚠️  Uplink desconectado!")
        with self._lock:
            old_link = self.uplink
            self.uplink = None

        # Notificar callbacks
        if old_link:
            self._notify_lost_link(old_link)

    # ========================================================================
    # Connection Management
    # ========================================================================

    def connect_to_neighbor(self, address: str, neighbor_info) -> Optional[Link]:
        """
        Conecta a um vizinho e cria um uplink.

        Args:
            address: Endereço BLE do vizinho
            neighbor_info: NeighborInfo do vizinho

        Returns:
            Link criado ou None se falhar
        """
        logger.info(f"A conectar a vizinho {address}...")

        try:
            # Criar ScannedDevice
            device = ScannedDevice(
                address=address,
                identifier=address,
                rssi=neighbor_info.rssi,
                name=None,
                service_uuids=[],
                manufacturer_data={},
            )

            # Conectar via BLE Client
            connection = self.client.connect_to_device(device)
            if not connection:
                logger.error(f"Falha ao conectar a {address}")
                return None

            # Criar DeviceInfo
            device_info = DeviceInfo(
                nid=neighbor_info.nid,
                hop_count=neighbor_info.hop_count,
                device_type=neighbor_info.device_type,
            )

            # Adicionar como uplink
            link = self.set_uplink(connection, device_info)
            logger.info(f"✅ Conectado a {address} e uplink estabelecido")

            return link

        except Exception as e:
            logger.error(f"Erro ao conectar a {address}: {e}")
            return None

    # ========================================================================
    # Downlink Management
    # ========================================================================

    def add_downlink(self, connection: BLEConnection, device_info: DeviceInfo) -> Link:
        """
        Adiciona um downlink (child conectou-se a nós).

        Args:
            connection: BLEConnection ao child
            device_info: Informação do child

        Returns:
            Link criado
        """
        with self._lock:
            address = connection.address

            # Se já existe, substituir
            if address in self.downlinks:
                logger.warning(f"Downlink {address} já existe - a substituir")
                self.downlinks[address].disconnect()

            # Criar novo downlink
            link = Link(connection, device_info, is_uplink=False)
            link.set_disconnected_callback(lambda: self._on_downlink_disconnected(address))

            self.downlinks[address] = link
            logger.info(f"✅ Downlink adicionado: {link}")

        # Notificar callbacks (fora do lock)
        self._notify_new_downlink(link)
        return link

    def remove_downlink(self, address: str):
        """
        Remove um downlink.

        Args:
            address: Endereço BLE do child
        """
        with self._lock:
            if address in self.downlinks:
                link = self.downlinks[address]
                link.disconnect()
                del self.downlinks[address]
                logger.info(f"Downlink removido: {address}")

                # Notificar callbacks
                self._notify_lost_link(link)

    def get_downlink(self, address: str) -> Optional[Link]:
        """
        Retorna um downlink pelo endereço.

        Args:
            address: Endereço BLE

        Returns:
            Link ou None
        """
        return self.downlinks.get(address)

    def get_all_downlinks(self) -> List[Link]:
        """Retorna todos os downlinks."""
        return list(self.downlinks.values())

    def has_downlinks(self) -> bool:
        """Verifica se tem downlinks."""
        return len(self.downlinks) > 0

    def _on_downlink_disconnected(self, address: str):
        """
        Callback quando um downlink é desconectado.

        Args:
            address: Endereço do downlink
        """
        logger.warning(f"⚠️  Downlink desconectado: {address}")
        self.remove_downlink(address)

    # ========================================================================
    # Broadcast & Routing
    # ========================================================================

    def send_to_uplink(self, data: bytes, service_uuid: str, char_uuid: str) -> bool:
        """
        Envia dados para o uplink.

        Args:
            data: Dados a enviar
            service_uuid: UUID do serviço
            char_uuid: UUID da característica

        Returns:
            True se enviado com sucesso
        """
        if not self.has_uplink():
            logger.warning("Sem uplink - não é possível enviar")
            return False

        return self.uplink.send(data, service_uuid, char_uuid)

    def send_to_downlink(
        self,
        address: str,
        data: bytes,
        service_uuid: str,
        char_uuid: str
    ) -> bool:
        """
        Envia dados para um downlink específico.

        Args:
            address: Endereço do downlink
            data: Dados a enviar
            service_uuid: UUID do serviço
            char_uuid: UUID da característica

        Returns:
            True se enviado com sucesso
        """
        link = self.get_downlink(address)
        if not link:
            logger.warning(f"Downlink {address} não existe")
            return False

        return link.send(data, service_uuid, char_uuid)

    def broadcast_to_downlinks(
        self,
        data: bytes,
        service_uuid: str,
        char_uuid: str,
        exclude: Optional[str] = None
    ) -> int:
        """
        Envia dados para todos os downlinks.

        Args:
            data: Dados a enviar
            service_uuid: UUID do serviço
            char_uuid: UUID da característica
            exclude: Endereço de downlink a excluir (opcional)

        Returns:
            Número de downlinks que receberam com sucesso
        """
        count = 0
        for address, link in self.downlinks.items():
            if exclude and address == exclude:
                continue

            if link.send(data, service_uuid, char_uuid):
                count += 1

        logger.debug(f"Broadcast para {count}/{len(self.downlinks)} downlinks")
        return count

    # ========================================================================
    # Callbacks & Events
    # ========================================================================

    def on_new_downlink(self, callback: Callable[[Link], None]):
        """
        Regista callback para quando um novo downlink é adicionado.

        Args:
            callback: Função que recebe Link
        """
        self._new_downlink_callbacks.append(callback)

    def on_lost_link(self, callback: Callable[[Link], None]):
        """
        Regista callback para quando um link é perdido.

        Args:
            callback: Função que recebe Link
        """
        self._lost_link_callbacks.append(callback)

    def _notify_new_downlink(self, link: Link):
        """Notifica callbacks de novo downlink."""
        for callback in self._new_downlink_callbacks:
            try:
                callback(link)
            except Exception as e:
                logger.error(f"Erro em callback new_downlink: {e}")

    def _notify_lost_link(self, link: Link):
        """Notifica callbacks de link perdido."""
        for callback in self._lost_link_callbacks:
            try:
                callback(link)
            except Exception as e:
                logger.error(f"Erro em callback lost_link: {e}")

    # ========================================================================
    # Status & Info
    # ========================================================================

    def get_status(self) -> dict:
        """
        Retorna o estado atual do Link Manager.

        Returns:
            Dicionário com informação de estado
        """
        return {
            'has_uplink': self.has_uplink(),
            'uplink': str(self.uplink) if self.uplink else None,
            'num_downlinks': len(self.downlinks),
            'downlinks': [str(link) for link in self.downlinks.values()],
        }

    def disconnect_neighbor(self, address: str):
        """
        Desconecta de um vizinho específico por endereço.

        Args:
            address: Endereço BLE do vizinho
        """
        # Verificar se é o uplink
        if self.uplink and self.uplink.address == address:
            logger.info(f"A desconectar do uplink {address}")
            self.clear_uplink()
            return

        # Verificar se é um downlink
        if address in self.downlinks:
            logger.info(f"A desconectar do downlink {address}")
            self.remove_downlink(address)
            return

        logger.warning(f"Vizinho {address} não está conectado")

    def get_uplink(self) -> Optional[Link]:
        """
        Retorna o uplink atual.

        Returns:
            Link do uplink ou None
        """
        return self.uplink

    def get_downlinks(self) -> List[Link]:
        """
        Retorna lista de downlinks.

        Returns:
            Lista de Links
        """
        return self.get_all_downlinks()

    def disconnect_all(self):
        """Desconecta todos os links."""
        logger.info("A desconectar todos os links...")

        # Desconectar uplink
        self.clear_uplink()

        # Desconectar downlinks
        with self._lock:
            for address in list(self.downlinks.keys()):
                self.remove_downlink(address)

        logger.info("Todos os links desconectados")


# ============================================================================
# Exemplo de Uso
# ============================================================================

if __name__ == '__main__':
    logger.info("Link Manager - Module")
    logger.info("Este módulo gere uplink e downlinks BLE.")
    logger.info("")
    logger.info("Exemplo:")
    logger.info("  from common.network.link_manager import LinkManager")
    logger.info("")
    logger.info("  lm = LinkManager()")
    logger.info("  lm.set_uplink(connection, device_info)")
    logger.info("  lm.add_downlink(connection, device_info)")
