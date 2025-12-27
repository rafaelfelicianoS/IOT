"""
GATT Services específicos para a rede IoT.

Define o IoTNetworkService com as suas Characteristics:
- NetworkPacketCharacteristic: Envio/recepção de pacotes
- DeviceInfoCharacteristic: Informação do dispositivo (NID, hop count)
- NeighborTableCharacteristic: Lista de vizinhos BLE
- AuthCharacteristic: Handshake de autenticação

UUIDs definidos em common/utils/constants.py
"""

import dbus
from typing import Optional, Callable, List, Dict, Any

from common.ble.gatt_server import (
    Service,
    Characteristic,
    Descriptor,
    NotSupportedException,
)
from common.utils.constants import (
    IOT_NETWORK_SERVICE_UUID,
    CHAR_NETWORK_PACKET_UUID,
    CHAR_DEVICE_INFO_UUID,
    CHAR_NEIGHBOR_TABLE_UUID,
    CHAR_AUTHENTICATION_UUID,
    GATT_CHARACTERISTIC_IFACE,
    DBUS_PROP_IFACE,
)
from common.utils.logger import get_logger
from common.utils.nid import NID

logger = get_logger("gatt_services")


# ============================================================================
# NetworkPacketCharacteristic
# ============================================================================

class NetworkPacketCharacteristic(Characteristic):
    """
    Characteristic para envio/recepção de pacotes de rede.

    Flags: ['write', 'notify']
    - Write: Clientes escrevem pacotes para enviar
    - Notify: Servidor notifica clientes de pacotes recebidos

    Este é o canal principal de comunicação entre dispositivos.
    """

    def __init__(self, bus: dbus.SystemBus, index: int, service: Service):
        """
        Inicializa a NetworkPacketCharacteristic.

        Args:
            bus: D-Bus system bus
            index: Índice da characteristic
            service: Service parent
        """
        Characteristic.__init__(
            self,
            bus,
            index,
            CHAR_NETWORK_PACKET_UUID,
            ['write', 'notify'],
            service,
        )

        self.notifying = False
        self.subscribed_clients = set()
        self.packet_callback: Optional[Callable[[bytes], None]] = None

        logger.info("NetworkPacketCharacteristic criada")

    def set_packet_callback(self, callback: Callable[[bytes], None]):
        """
        Define callback chamado quando um pacote é recebido (via Write).

        Args:
            callback: Função que recebe bytes do pacote
        """
        self.packet_callback = callback
        logger.debug("Packet callback definido")

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, in_signature='aya{sv}', sender_keyword='sender')
    def WriteValue(self, value: List[int], options: Dict[str, Any], sender=None):
        """
        Recebe um pacote escrito por um cliente.

        Args:
            value: Array de bytes do pacote
            options: Opções D-Bus
            sender: ID do sender D-Bus
        """
        packet_bytes = bytes(value)
        logger.debug(f"Pacote recebido de {sender}: {len(packet_bytes)} bytes")

        # Chamar callback se definido
        if self.packet_callback:
            try:
                self.packet_callback(packet_bytes)
            except Exception as e:
                logger.error(f"Erro no packet callback: {e}")

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, sender_keyword='sender')
    def StartNotify(self, sender=None):
        """
        Cliente subscreve notificações de pacotes.

        Args:
            sender: ID do sender D-Bus
        """
        if sender is None:
            return

        self.notifying = True
        self.subscribed_clients.add(sender)
        logger.info(f"Cliente {sender} subscreveu notificações de pacotes")

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, sender_keyword='sender')
    def StopNotify(self, sender=None):
        """
        Cliente cancela subscrição de notificações.

        Args:
            sender: ID do sender D-Bus
        """
        if sender is None:
            return

        self.subscribed_clients.discard(sender)
        if not self.subscribed_clients:
            self.notifying = False

        logger.info(f"Cliente {sender} cancelou subscrição de pacotes")

    def notify_packet(self, packet_bytes: bytes):
        """
        Envia notificação de um pacote a todos os clientes subscritos.

        Args:
            packet_bytes: Bytes do pacote a notificar
        """
        if not self.notifying:
            logger.debug("Nenhum cliente subscrito, pacote não enviado")
            return

        try:
            # Converter bytes para dbus.Array
            value = dbus.Array(list(packet_bytes), signature='y')

            # Emitir signal PropertiesChanged
            self.PropertiesChanged(
                GATT_CHARACTERISTIC_IFACE,
                {'Value': value},
                []
            )

            logger.debug(f"Pacote notificado a {len(self.subscribed_clients)} clientes")
        except Exception as e:
            logger.error(f"Erro ao notificar pacote: {e}")


# ============================================================================
# DeviceInfoCharacteristic
# ============================================================================

class DeviceInfoCharacteristic(Characteristic):
    """
    Characteristic com informação do dispositivo.

    Flags: ['read']
    - Read: Clientes podem ler informação do dispositivo

    Formato do valor (bytes):
    - 16 bytes: NID (UUID)
    - 1 byte: Hop count (signed int, -1 = sem uplink)
    - 1 byte: Device type (0 = node, 1 = sink)
    """

    def __init__(
        self,
        bus: dbus.SystemBus,
        index: int,
        service: Service,
        device_nid: NID,
        device_type: str = "node",
    ):
        """
        Inicializa a DeviceInfoCharacteristic.

        Args:
            bus: D-Bus system bus
            index: Índice da characteristic
            service: Service parent
            device_nid: NID deste dispositivo
            device_type: Tipo do dispositivo ("node" ou "sink")
        """
        Characteristic.__init__(
            self,
            bus,
            index,
            CHAR_DEVICE_INFO_UUID,
            ['read'],
            service,
        )

        self.device_nid = device_nid
        self.device_type = device_type
        self.hop_count = -1  # -1 = sem uplink

        logger.info(f"DeviceInfoCharacteristic criada: NID={device_nid}, type={device_type}")

    def update_hop_count(self, hop_count: int):
        """
        Atualiza o hop count.

        Args:
            hop_count: Novo hop count (-1 = sem uplink)
        """
        self.hop_count = hop_count
        logger.debug(f"Hop count atualizado: {hop_count}")

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options: Dict[str, Any]):
        """
        Retorna informação do dispositivo.

        Returns:
            18 bytes: NID (16) + hop_count (1) + device_type (1)
        """
        # Formato: NID (16 bytes) + hop_count (1 byte signed) + device_type (1 byte)
        device_type_byte = 1 if self.device_type == "sink" else 0

        # Hop count como signed byte (-128 a 127)
        hop_count_byte = self.hop_count if self.hop_count >= 0 else 256 + self.hop_count

        value = self.device_nid.to_bytes() + bytes([hop_count_byte, device_type_byte])

        logger.debug(f"DeviceInfo lida: NID={self.device_nid}, hops={self.hop_count}, type={device_type_byte}")
        return dbus.Array(list(value), signature='y')


# ============================================================================
# NeighborTableCharacteristic
# ============================================================================

class NeighborTableCharacteristic(Characteristic):
    """
    Characteristic com lista de vizinhos BLE descobertos.

    Flags: ['read', 'notify']
    - Read: Clientes podem ler a lista atual
    - Notify: Notifica quando a lista muda

    Formato do valor (bytes):
    - 1 byte: Número de vizinhos (N)
    - Para cada vizinho (18 bytes):
      - 16 bytes: NID
      - 1 byte: Hop count do vizinho
      - 1 byte: Reserved (futuro uso)
    """

    def __init__(self, bus: dbus.SystemBus, index: int, service: Service):
        """
        Inicializa a NeighborTableCharacteristic.

        Args:
            bus: D-Bus system bus
            index: Índice da characteristic
            service: Service parent
        """
        Characteristic.__init__(
            self,
            bus,
            index,
            CHAR_NEIGHBOR_TABLE_UUID,
            ['read', 'notify'],
            service,
        )

        self.neighbors: List[Dict[str, Any]] = []  # [{'nid': NID, 'hop_count': int}, ...]
        self.notifying = False
        self.subscribed_clients = set()

        logger.info("NeighborTableCharacteristic criada")

    def update_neighbors(self, neighbors: List[Dict[str, Any]]):
        """
        Atualiza a lista de vizinhos e notifica clientes.

        Args:
            neighbors: Lista de dicts com 'nid' e 'hop_count'
        """
        self.neighbors = neighbors
        logger.debug(f"Neighbor table atualizada: {len(neighbors)} vizinhos")

        # Notificar clientes se houver subscrições
        if self.notifying:
            self._notify_neighbors()

    def _serialize_neighbors(self) -> bytes:
        """
        Serializa a lista de vizinhos para bytes.

        Returns:
            Bytes serializados
        """
        # 1 byte: número de vizinhos
        data = bytes([len(self.neighbors)])

        # Para cada vizinho: NID (16) + hop_count (1) + reserved (1)
        for neighbor in self.neighbors:
            nid: NID = neighbor['nid']
            hop_count: int = neighbor.get('hop_count', -1)

            # Hop count como signed byte
            hop_count_byte = hop_count if hop_count >= 0 else 256 + hop_count

            data += nid.to_bytes() + bytes([hop_count_byte, 0])  # 0 = reserved

        return data

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options: Dict[str, Any]):
        """
        Retorna a lista de vizinhos.

        Returns:
            Bytes serializados da tabela de vizinhos
        """
        value = self._serialize_neighbors()
        logger.debug(f"Neighbor table lida: {len(self.neighbors)} vizinhos")
        return dbus.Array(list(value), signature='y')

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, sender_keyword='sender')
    def StartNotify(self, sender=None):
        """Cliente subscreve notificações."""
        if sender is None:
            return

        self.notifying = True
        self.subscribed_clients.add(sender)
        logger.info(f"Cliente {sender} subscreveu neighbor table")

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, sender_keyword='sender')
    def StopNotify(self, sender=None):
        """Cliente cancela subscrição."""
        if sender is None:
            return

        self.subscribed_clients.discard(sender)
        if not self.subscribed_clients:
            self.notifying = False

        logger.info(f"Cliente {sender} cancelou subscrição de neighbor table")

    def _notify_neighbors(self):
        """Notifica clientes da lista atualizada de vizinhos."""
        try:
            value = dbus.Array(list(self._serialize_neighbors()), signature='y')

            self.PropertiesChanged(
                GATT_CHARACTERISTIC_IFACE,
                {'Value': value},
                []
            )

            logger.debug(f"Neighbor table notificada a {len(self.subscribed_clients)} clientes")
        except Exception as e:
            logger.error(f"Erro ao notificar neighbor table: {e}")


# ============================================================================
# AuthCharacteristic
# ============================================================================

class AuthCharacteristic(Characteristic):
    """
    Characteristic para handshake de autenticação.

    Flags: ['write', 'indicate']
    - Write: Cliente envia mensagens de autenticação
    - Indicate: Servidor responde com acknowledgment

    Usado para autenticação mútua via certificados X.509.
    """

    def __init__(self, bus: dbus.SystemBus, index: int, service: Service):
        """
        Inicializa a AuthCharacteristic.

        Args:
            bus: D-Bus system bus
            index: Índice da characteristic
            service: Service parent
        """
        Characteristic.__init__(
            self,
            bus,
            index,
            CHAR_AUTHENTICATION_UUID,
            ['write', 'indicate'],
            service,
        )

        self.auth_callback: Optional[Callable[[bytes, str], bytes]] = None
        self.indicating = False
        self.subscribed_clients = set()

        logger.info("AuthCharacteristic criada")

    def set_auth_callback(self, callback: Callable[[bytes, str], bytes]):
        """
        Define callback para processar mensagens de autenticação.

        Args:
            callback: Função que recebe (auth_data, sender) e retorna resposta
        """
        self.auth_callback = callback
        logger.debug("Auth callback definido")

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, in_signature='aya{sv}', sender_keyword='sender')
    def WriteValue(self, value: List[int], options: Dict[str, Any], sender=None):
        """
        Recebe mensagem de autenticação de um cliente.

        Args:
            value: Dados de autenticação
            options: Opções D-Bus
            sender: ID do sender
        """
        auth_data = bytes(value)
        logger.debug(f"Auth data recebida de {sender}: {len(auth_data)} bytes")

        # Processar autenticação
        if self.auth_callback:
            try:
                response = self.auth_callback(auth_data, sender)
                # Enviar resposta via Indicate
                self._indicate_response(response)
            except Exception as e:
                logger.error(f"Erro no auth callback: {e}")

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, sender_keyword='sender')
    def StartNotify(self, sender=None):
        """Cliente subscreve indications."""
        if sender is None:
            return

        self.indicating = True
        self.subscribed_clients.add(sender)
        logger.info(f"Cliente {sender} subscreveu auth indications")

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, sender_keyword='sender')
    def StopNotify(self, sender=None):
        """Cliente cancela subscrição."""
        if sender is None:
            return

        self.subscribed_clients.discard(sender)
        if not self.subscribed_clients:
            self.indicating = False

        logger.info(f"Cliente {sender} cancelou subscrição de auth")

    def _indicate_response(self, response_bytes: bytes):
        """
        Envia resposta de autenticação via Indicate.

        Args:
            response_bytes: Resposta a enviar
        """
        if not self.indicating:
            logger.debug("Nenhum cliente subscrito, resposta não enviada")
            return

        try:
            value = dbus.Array(list(response_bytes), signature='y')

            self.PropertiesChanged(
                GATT_CHARACTERISTIC_IFACE,
                {'Value': value},
                []
            )

            logger.debug("Auth response indicada")
        except Exception as e:
            logger.error(f"Erro ao indicar auth response: {e}")


# ============================================================================
# IoTNetworkService
# ============================================================================

class IoTNetworkService(Service):
    """
    GATT Service principal para a rede IoT.

    Agrega todas as Characteristics necessárias para comunicação na rede.
    """

    def __init__(
        self,
        bus: dbus.SystemBus,
        path: str,
        index: int,
        device_nid: NID,
        device_type: str = "node",
    ):
        """
        Inicializa o IoTNetworkService.

        Args:
            bus: D-Bus system bus
            path: Base path
            index: Índice do service
            device_nid: NID deste dispositivo
            device_type: Tipo ("node" ou "sink")
        """
        Service.__init__(self, bus, path, index, IOT_NETWORK_SERVICE_UUID, primary=True)

        logger.info("A criar IoTNetworkService...")

        # Características
        self.packet_char = NetworkPacketCharacteristic(bus, 0, self)
        self.device_info_char = DeviceInfoCharacteristic(bus, 1, self, device_nid, device_type)
        self.neighbor_char = NeighborTableCharacteristic(bus, 2, self)
        self.auth_char = AuthCharacteristic(bus, 3, self)

        # Adicionar ao service
        self.add_characteristic(self.packet_char)
        self.add_characteristic(self.device_info_char)
        self.add_characteristic(self.neighbor_char)
        self.add_characteristic(self.auth_char)

        logger.info("✅ IoTNetworkService criado com sucesso!")

    def get_packet_characteristic(self) -> NetworkPacketCharacteristic:
        """Retorna a NetworkPacketCharacteristic."""
        return self.packet_char

    def get_device_info_characteristic(self) -> DeviceInfoCharacteristic:
        """Retorna a DeviceInfoCharacteristic."""
        return self.device_info_char

    def get_neighbor_characteristic(self) -> NeighborTableCharacteristic:
        """Retorna a NeighborTableCharacteristic."""
        return self.neighbor_char

    def get_auth_characteristic(self) -> AuthCharacteristic:
        """Retorna a AuthCharacteristic."""
        return self.auth_char
