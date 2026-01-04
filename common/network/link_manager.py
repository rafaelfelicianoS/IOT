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
from common.network.heartbeat_monitor import HeartbeatMonitor
from common.network.packet import Packet, MessageType
from common.utils.constants import IOT_NETWORK_SERVICE_UUID, CHAR_NETWORK_PACKET_UUID

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

    def send_packet(self, packet_data: bytes) -> bool:
        """
        Envia um pacote através do link usando a característica NETWORK_PACKET.

        Args:
            packet_data: Pacote serializado (bytes)

        Returns:
            True se enviado com sucesso
        """
        from common.utils.constants import IOT_NETWORK_SERVICE_UUID, CHAR_NETWORK_PACKET_UUID

        if not self.connection.is_connected:
            logger.warning(f"Link {self.address} não está conectado")
            return False

        success = self.connection.write_characteristic(
            IOT_NETWORK_SERVICE_UUID,
            CHAR_NETWORK_PACKET_UUID,
            packet_data
        )

        if success:
            self.last_activity = datetime.now()
            logger.debug(f"Pacote enviado via {self}: {len(packet_data)} bytes")
        else:
            logger.error(f"Falha ao enviar pacote via {self}")

        return success

    def enable_packet_notifications(self, callback: Callable[[bytes], None]) -> bool:
        """
        Ativa notificações para a característica NETWORK_PACKET.

        Args:
            callback: Função chamada quando um pacote é recebido

        Returns:
            True se ativado com sucesso
        """
        from common.utils.constants import IOT_NETWORK_SERVICE_UUID, CHAR_NETWORK_PACKET_UUID

        # Guardar callback
        self._data_callback = callback

        # Tentar ativar notificações (se a conexão suportar)
        # Nota: SimpleBLE pode não suportar notificações diretamente
        # Isto é um placeholder para quando implementarmos notificações
        logger.info(f"Notificações de pacotes ativadas para {self}")
        return True

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

    def __init__(self, client: 'BLEClient', my_nid: Optional[NID] = None):
        """
        Inicializa o Link Manager.

        Args:
            client: BLE Client para operações de conexão
            my_nid: NID do dispositivo local (se None, gera um novo)
        """
        from common.ble.gatt_client import BLEClient

        self.client: BLEClient = client
        self.my_nid: NID = my_nid if my_nid else NID.generate()
        self.uplink: Optional[Link] = None
        self.downlinks: Dict[str, Link] = {}  # address -> Link

        # Forwarding Table: NID -> Link (para routing)
        # Aprende de onde vieram os pacotes para saber para onde enviar respostas
        self.forwarding_table: Dict[NID, Link] = {}  # NID -> Link

        # Heartbeat monitoring
        self.heartbeat_monitor: Optional[HeartbeatMonitor] = None

        # Callbacks
        self._new_downlink_callbacks: List[Callable[[Link], None]] = []
        self._lost_link_callbacks: List[Callable[[Link], None]] = []

        # Lock para thread safety (RLock permite re-entrada na mesma thread)
        self._lock = threading.RLock()

        logger.info(f"Link Manager iniciado (my_nid={self.my_nid})")

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

            # Parar monitor anterior se existir
            if self.heartbeat_monitor:
                self.heartbeat_monitor.stop()

            link = Link(connection, device_info, is_uplink=True)
            link.set_disconnected_callback(self._on_uplink_disconnected)

            self.uplink = link
            logger.info(f" Uplink definido: {link}")

            # Iniciar monitoramento de heartbeat
            self._start_heartbeat_monitoring(link)

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
        logger.warning("  Uplink desconectado!")
        with self._lock:
            old_link = self.uplink
            self.uplink = None

            # Parar monitor de heartbeat
            if self.heartbeat_monitor:
                self.heartbeat_monitor.stop()
                self.heartbeat_monitor = None

        # Notificar callbacks
        if old_link:
            self._notify_lost_link(old_link)

    # ========================================================================
    # Heartbeat Monitoring
    # ========================================================================

    def _start_heartbeat_monitoring(self, link: Link):
        """
        Inicia monitoramento de heartbeats para o uplink.

        Args:
            link: Link do uplink para monitorar
        """
        self.heartbeat_monitor = HeartbeatMonitor(
            heartbeat_interval=5.0,
            max_missed=3,
            on_timeout=self._on_heartbeat_timeout
        )

        # Subscrever notificações de pacotes
        def on_packet_received(data: bytes):
            """Callback quando recebe um pacote via notify."""
            try:
                # Deserializar pacote
                packet = Packet.from_bytes(data)

                logger.debug(
                    f" Pacote recebido via {link.address}: "
                    f"{packet.source} → {packet.destination} "
                    f"(type={MessageType.to_string(packet.msg_type)}, seq={packet.sequence})"
                )

                # Se é heartbeat, notificar monitor
                if packet.msg_type == MessageType.HEARTBEAT:
                    logger.debug(f" Heartbeat recebido: seq={packet.sequence}")
                    self.heartbeat_monitor.on_heartbeat_received(packet.sequence)

                # Se é DATA, rotear o pacote
                elif packet.msg_type == MessageType.DATA:
                    logger.info(
                        f" DATA recebido: {packet.source} → {packet.destination} "
                        f"({len(packet.payload)} bytes)"
                    )
                    # Rotear packet (aprende rota + forward se necessário)
                    self.route_packet(packet, from_link=link)

            except Exception as e:
                logger.error(f"Erro ao processar pacote recebido: {e}")

        # Subscribe a notificações
        success = link.connection.subscribe_notifications(
            IOT_NETWORK_SERVICE_UUID,
            CHAR_NETWORK_PACKET_UUID,
            on_packet_received
        )

        if not success:
            logger.error(" Falha ao subscrever notificações de heartbeat")
            return

        # Iniciar monitor
        self.heartbeat_monitor.start()
        logger.info(" Monitoramento de heartbeat iniciado")

    def _on_heartbeat_timeout(self):
        """
        Callback quando timeout de heartbeat é detetado.

        Ações:
        1. Desconectar uplink
        2. Desconectar todos os downlinks
        3. Marcar hop_count como negativo (TODO)
        4. Procurar novo uplink (TODO)
        """
        logger.error(" TIMEOUT DE HEARTBEAT DETETADO!")
        logger.error("   Ações: desconectar uplink + todos os downlinks")

        with self._lock:
            # Desconectar uplink
            if self.uplink:
                logger.info(f"   A desconectar uplink: {self.uplink.address}")
                self.uplink.disconnect()
                self.uplink = None

            # Desconectar todos os downlinks
            downlink_addrs = list(self.downlinks.keys())
            for address in downlink_addrs:
                logger.info(f"   A desconectar downlink: {address}")
                self.disconnect_downlink(address)

        logger.warning("  Todos os links desconectados devido a timeout de heartbeat")

    def get_heartbeat_status(self) -> dict:
        """
        Retorna informações sobre o estado do monitoramento de heartbeat.

        Returns:
            Dict com status do heartbeat monitor
        """
        if not self.heartbeat_monitor:
            return {
                'monitoring': False,
                'missed_count': 0,
                'time_since_last': None
            }

        return {
            'monitoring': self.heartbeat_monitor.is_monitoring(),
            'missed_count': self.heartbeat_monitor.get_missed_count(),
            'time_since_last': self.heartbeat_monitor.get_time_since_last()
        }

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

            device_info = DeviceInfo(
                nid=neighbor_info.nid,
                hop_count=neighbor_info.hop_count,
                device_type=neighbor_info.device_type,
            )

            link = self.set_uplink(connection, device_info)
            logger.info(f" Conectado a {address} e uplink estabelecido")

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

            link = Link(connection, device_info, is_uplink=False)
            link.set_disconnected_callback(lambda: self._on_downlink_disconnected(address))

            self.downlinks[address] = link
            logger.info(f" Downlink adicionado: {link}")

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
        logger.warning(f"  Downlink desconectado: {address}")
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
        if self.uplink and self.uplink.address == address:
            logger.info(f"A desconectar do uplink {address}")
            self.clear_uplink()
            return

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

    # ========================================================================
    # Packet Routing
    # ========================================================================

    def send_packet_to_uplink(self, packet_data: bytes) -> bool:
        """
        Envia um pacote para o uplink (em direção ao Sink).

        Args:
            packet_data: Pacote serializado

        Returns:
            True se enviado com sucesso
        """
        if not self.has_uplink():
            logger.warning("Sem uplink disponível para enviar pacote")
            return False

        return self.uplink.send_packet(packet_data)

    def send_packet_to_downlink(self, address: str, packet_data: bytes) -> bool:
        """
        Envia um pacote para um downlink específico.

        Args:
            address: Endereço do downlink
            packet_data: Pacote serializado

        Returns:
            True se enviado com sucesso
        """
        link = self.downlinks.get(address)
        if not link:
            logger.warning(f"Downlink {address} não encontrado")
            return False

        return link.send_packet(packet_data)

    def broadcast_packet_to_downlinks(self, packet_data: bytes, exclude: Optional[str] = None) -> int:
        """
        Envia um pacote para todos os downlinks (broadcast).

        Args:
            packet_data: Pacote serializado
            exclude: Endereço a excluir do broadcast (ex: origem do pacote)

        Returns:
            Número de downlinks que receberam com sucesso
        """
        count = 0
        for address, link in self.downlinks.items():
            if exclude and address == exclude:
                continue

            if link.send_packet(packet_data):
                count += 1

        logger.debug(f"Pacote broadcast para {count}/{len(self.downlinks)} downlinks")
        return count

    def route_packet(self, packet: 'Packet', received_from: Optional[str] = None) -> bool:
        """
        Roteia um pacote recebido.

        Lógica de routing:
        1. Se destino é este node -> processar localmente
        2. Se destino está nos downlinks -> enviar para esse downlink
        3. Caso contrário -> enviar para uplink (em direção ao Sink)

        Args:
            packet: Pacote a rotear
            received_from: Endereço de quem recebeu o pacote (para evitar loop)

        Returns:
            True se roteado com sucesso
        """
        from common.network.packet import Packet

        # Decrementar TTL
        if not packet.decrement_ttl():
            logger.warning(f"Pacote expirou (TTL=0), descartando (seq={packet.sequence})")
            return False

        # TODO: Verificar se o destino é este node (comparar com local NID)
        # Se for, processar localmente ao invés de rotear

        for address, link in self.downlinks.items():
            if address == received_from:
                continue  # Não enviar de volta para quem enviou

            if link.device_info.nid == packet.destination:
                logger.info(f"Roteando pacote para downlink {address}")
                return self.send_packet_to_downlink(address, packet.to_bytes())

        # Se não está nos downlinks, enviar para uplink
        if self.has_uplink():
            if received_from != self.uplink.address:  # Evitar loop
                logger.info("Roteando pacote para uplink")
                return self.send_packet_to_uplink(packet.to_bytes())
            else:
                logger.warning("Pacote veio do uplink mas destino não encontrado, descartando")
                return False
        else:
            logger.warning("Sem uplink para rotear pacote, descartando")
            return False

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
    # ========================================================================
    # Packet Routing (Seção 3.1 do projeto)
    # ========================================================================

    def learn_route(self, source_nid: NID, from_link: Link):
        """
        Aprende a rota para um NID (adiciona à forwarding table).

        Quando recebemos um pacote de source_nid via from_link,
        memorizamos que para enviar pacotes para source_nid devemos
        usar from_link.

        Args:
            source_nid: NID de origem do pacote
            from_link: Link de onde veio o pacote
        """
        with self._lock:
            if source_nid not in self.forwarding_table:
                self.forwarding_table[source_nid] = from_link
                logger.info(f" Rota aprendida: {source_nid} → Link[{from_link.address}]")
            elif self.forwarding_table[source_nid] != from_link:
                # Rota mudou (pode acontecer se topologia mudar)
                old_link = self.forwarding_table[source_nid]
                self.forwarding_table[source_nid] = from_link
                logger.info(
                    f" Rota atualizada: {source_nid} "
                    f"Link[{old_link.address}] → Link[{from_link.address}]"
                )

    def route_packet(self, packet: Packet, from_link: Optional[Link] = None) -> bool:
        """
        Roteia um pacote recebido.

        Lógica de routing:
        1. Se destino == meu_nid → processar localmente (não implementado aqui)
        2. Se veio de downlink → forward uplink (em direção ao Sink)
        3. Se veio de uplink e temos rota → forward downlink
        4. Se veio de uplink e não temos rota → drop (não sabemos onde está)

        Args:
            packet: Pacote a rotear
            from_link: Link de onde veio o pacote (None se gerado localmente)

        Returns:
            True se roteado com sucesso
        """
        with self._lock:
            # Aprender rota de retorno (se não for heartbeat)
            if from_link and packet.msg_type != MessageType.HEARTBEAT:
                self.learn_route(packet.source, from_link)

            # Caso 1: Pacote veio de downlink (ou gerado localmente)
            # → Encaminhar uplink em direção ao Sink
            if from_link is None or (from_link in self.downlinks.values()):
                if self.uplink:
                    logger.debug(
                        f" Forwarding uplink: {packet.source} → {packet.destination} "
                        f"(type={MessageType.to_string(packet.msg_type)})"
                    )
                    return self._send_packet_via_link(packet, self.uplink)
                else:
                    logger.warning(f"  Não tenho uplink para forward {packet}")
                    return False

            # Caso 2: Pacote veio de uplink
            # → Procurar rota na forwarding table e encaminhar downlink
            elif from_link == self.uplink:
                dest_nid = packet.destination

                if dest_nid in self.forwarding_table:
                    target_link = self.forwarding_table[dest_nid]
                    logger.debug(
                        f" Forwarding downlink: {packet.source} → {packet.destination} "
                        f"via Link[{target_link.address}] (type={MessageType.to_string(packet.msg_type)})"
                    )
                    return self._send_packet_via_link(packet, target_link)
                else:
                    logger.warning(
                        f"  Sem rota para {dest_nid} na forwarding table. "
                        f"Dropping packet."
                    )
                    return False

            else:
                logger.error(f" Link desconhecido: {from_link}")
                return False

    def _send_packet_via_link(self, packet: Packet, link: Link) -> bool:
        """
        Envia um pacote através de um link específico.

        Args:
            packet: Pacote a enviar
            link: Link para enviar

        Returns:
            True se enviado com sucesso
        """
        try:
            packet_bytes = packet.to_bytes()
            success = link.connection.write_characteristic(
                IOT_NETWORK_SERVICE_UUID,
                CHAR_NETWORK_PACKET_UUID,
                packet_bytes
            )

            if success:
                logger.debug(f" Pacote enviado via Link[{link.address}]: {len(packet_bytes)} bytes")
            else:
                logger.error(f" Falha ao enviar pacote via Link[{link.address}]")

            return success

        except Exception as e:
            logger.error(f" Erro ao enviar pacote via Link[{link.address}]: {e}")
            return False

    def get_forwarding_table(self) -> Dict[NID, str]:
        """
        Retorna a forwarding table (NID -> endereço do link).

        Returns:
            Dict com NIDs e endereços dos links
        """
        with self._lock:
            return {nid: link.address for nid, link in self.forwarding_table.items()}

    def clear_forwarding_table(self):
        """Limpa a forwarding table."""
        with self._lock:
            self.forwarding_table.clear()
            logger.info("  Forwarding table limpa")


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
