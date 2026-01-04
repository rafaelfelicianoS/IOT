"""
BLE Advertising implementation using D-Bus and BlueZ.

Permite que o dispositivo BLE seja descoberto por outros dispositivos
através de LE Advertising.
"""

import dbus
import dbus.service
from typing import List, Optional

from common.utils.constants import (
    BLUEZ_SERVICE_NAME,
    LE_ADVERTISING_MANAGER_IFACE,
    DBUS_PROP_IFACE,
)
from common.utils.logger import get_logger

logger = get_logger("advertising")


# ============================================================================
# Exceções
# ============================================================================

class InvalidArgsException(dbus.exceptions.DBusException):
    """Exceção para argumentos inválidos."""
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'


class NotPermittedException(dbus.exceptions.DBusException):
    """Exceção para operações não permitidas."""
    _dbus_error_name = 'org.bluez.Error.NotPermitted'


class NotSupportedException(dbus.exceptions.DBusException):
    """Exceção para operações não suportadas."""
    _dbus_error_name = 'org.bluez.Error.NotSupported'


class FailedException(dbus.exceptions.DBusException):
    """Exceção genérica para falhas."""
    _dbus_error_name = 'org.bluez.Error.Failed'


# ============================================================================
# Advertisement - org.bluez.LEAdvertisement1
# ============================================================================

class Advertisement(dbus.service.Object):
    """
    BLE LE Advertisement.

    Permite que o dispositivo seja descoberto por outros dispositivos BLE.
    """

    # Tipos de advertising
    TYPE_BROADCAST = 'broadcast'
    TYPE_PERIPHERAL = 'peripheral'

    def __init__(
        self,
        bus: dbus.SystemBus,
        index: int,
        advertising_type: str = TYPE_PERIPHERAL,
    ):
        """
        Inicializa um Advertisement.

        Args:
            bus: D-Bus system bus
            index: Índice do advertisement
            advertising_type: Tipo de advertising ('broadcast' ou 'peripheral')
        """
        self.path = f'/org/bluez/iot/advertisement{index}'
        self.bus = bus
        self.ad_type = advertising_type
        self.service_uuids: List[str] = []
        self.manufacturer_data: Optional[dict] = None
        self.solicit_uuids: List[str] = []
        self.service_data: Optional[dict] = None
        self.local_name: Optional[str] = None
        self.include_tx_power = False
        self.discoverable = True

        # Configuração para manter advertising durante conexões ativas
        # Valores baixos de intervalo = mais visível mesmo com conexões
        self.min_interval = None  # Em milliseconds (None = usar default do BlueZ)
        self.max_interval = None  # Em milliseconds (None = usar default do BlueZ)
        self.duration = 0  # 0 = advertising contínuo (não para)

        dbus.service.Object.__init__(self, bus, self.path)
        logger.info(f"Advertisement criado: {self.path} (type: {advertising_type})")

    def get_path(self) -> dbus.ObjectPath:
        """Retorna o D-Bus path do advertisement."""
        return dbus.ObjectPath(self.path)

    def add_service_uuid(self, uuid: str):
        """
        Adiciona um Service UUID ao advertisement.

        Args:
            uuid: Service UUID (formato: 12340000-0000-1000-8000-00805f9b34fb)
        """
        if uuid not in self.service_uuids:
            self.service_uuids.append(uuid)
            logger.info(f" Service UUID adicionado ao advertising: {uuid}")
            logger.info(f"   Lista atual de UUIDs: {self.service_uuids}")

    def add_manufacturer_data(self, manufacturer_id: int, data: bytes):
        """
        Adiciona manufacturer data ao advertisement.

        Args:
            manufacturer_id: ID do manufacturer
            data: Dados do manufacturer
        """
        if self.manufacturer_data is None:
            self.manufacturer_data = {}

        self.manufacturer_data[manufacturer_id] = dbus.Array(
            list(data),
            signature='y'
        )
        logger.debug(f"Manufacturer data adicionado: ID={manufacturer_id}")

    def add_service_data(self, uuid: str, data: bytes):
        """
        Adiciona service data ao advertisement.

        Args:
            uuid: Service UUID
            data: Dados do service
        """
        if self.service_data is None:
            self.service_data = {}

        self.service_data[uuid] = dbus.Array(
            list(data),
            signature='y'
        )
        logger.debug(f"Service data adicionado: {uuid}")

    def set_local_name(self, name: str):
        """
        Define o nome local do dispositivo.

        Args:
            name: Nome do dispositivo
        """
        self.local_name = name
        logger.debug(f"Local name definido: {name}")

    def get_properties(self):
        """Retorna as propriedades do advertisement."""
        properties = {
            'Type': self.ad_type,
        }

        if self.service_uuids:
            logger.info(f" Advertising com ServiceUUIDs: {self.service_uuids}")
            properties['ServiceUUIDs'] = dbus.Array(
                self.service_uuids,
                signature='s'
            )
        else:
            logger.warning(f"  Advertising SEM ServiceUUIDs! Lista vazia: {self.service_uuids}")

        if self.solicit_uuids:
            properties['SolicitUUIDs'] = dbus.Array(
                self.solicit_uuids,
                signature='s'
            )

        if self.manufacturer_data:
            properties['ManufacturerData'] = dbus.Dictionary(
                self.manufacturer_data,
                signature='qv'
            )

        if self.service_data:
            properties['ServiceData'] = dbus.Dictionary(
                self.service_data,
                signature='sv'
            )

        if self.local_name:
            properties['LocalName'] = dbus.String(self.local_name)

        if self.include_tx_power:
            properties['IncludeTxPower'] = dbus.Boolean(self.include_tx_power)

        # Discoverable - importante para aparecer no scan!
        properties['Discoverable'] = dbus.Boolean(self.discoverable)

        # Duration: 0 = advertising contínuo (mesmo durante conexões)
        if self.duration is not None:
            properties['Duration'] = dbus.UInt16(self.duration)

        # MinInterval e MaxInterval para controlar frequência do advertising
        if self.min_interval is not None:
            properties['MinInterval'] = dbus.UInt16(self.min_interval)

        if self.max_interval is not None:
            properties['MaxInterval'] = dbus.UInt16(self.max_interval)

        return {
            'org.bluez.LEAdvertisement1': properties
        }

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        """D-Bus method: GetAll properties."""
        logger.debug(f"GetAll called on {self.path}")

        if interface != 'org.bluez.LEAdvertisement1':
            raise InvalidArgsException()

        return self.get_properties()['org.bluez.LEAdvertisement1']

    @dbus.service.method('org.bluez.LEAdvertisement1', in_signature='', out_signature='')
    def Release(self):
        """
        D-Bus method: Release.

        Chamado quando o advertisement é libertado pelo BlueZ.
        """
        logger.info(f"Advertisement released: {self.path}")


# ============================================================================
# Funções de Utilidade
# ============================================================================

def register_advertisement(
    advertisement: Advertisement,
    adapter_name: str = 'hci0',
) -> bool:
    """
    Regista um advertisement com o BlueZ.

    Args:
        advertisement: Advertisement a registar
        adapter_name: Nome do adaptador BLE (ex: 'hci0')

    Returns:
        True se registado com sucesso, False caso contrário
    """
    bus = advertisement.bus
    adapter_path = f"/org/bluez/{adapter_name}"

    logger.info(f"A registar advertisement no adaptador: {adapter_path}")

    try:
        adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, adapter_path)
        ad_manager = dbus.Interface(adapter_obj, LE_ADVERTISING_MANAGER_IFACE)

        # Registar advertisement
        ad_manager.RegisterAdvertisement(
            advertisement.get_path(),
            {},
            reply_handler=lambda: logger.info(" Advertisement registado com sucesso!"),
            error_handler=lambda e: logger.error(f" Falha ao registar advertisement: {e}"),
        )

        return True

    except dbus.exceptions.DBusException as e:
        logger.error(f"Erro ao registar advertisement: {e}")
        return False


def unregister_advertisement(
    advertisement: Advertisement,
    adapter_name: str = 'hci0',
) -> bool:
    """
    Remove o registo de um advertisement.

    Args:
        advertisement: Advertisement a remover
        adapter_name: Nome do adaptador BLE

    Returns:
        True se removido com sucesso, False caso contrário
    """
    bus = advertisement.bus
    adapter_path = f"/org/bluez/{adapter_name}"

    logger.info(f"A remover advertisement do adaptador: {adapter_path}")

    try:
        adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, adapter_path)
        ad_manager = dbus.Interface(adapter_obj, LE_ADVERTISING_MANAGER_IFACE)

        ad_manager.UnregisterAdvertisement(advertisement.get_path())
        logger.info("Advertisement removido com sucesso")
        return True

    except dbus.exceptions.DBusException as e:
        logger.error(f"Erro ao remover advertisement: {e}")
        return False


# ============================================================================
# Exemplo de Uso
# ============================================================================

if __name__ == '__main__':
    logger.info("BLE Advertising - Module")
    logger.info("Este módulo fornece funcionalidade de BLE advertising.")
    logger.info("")
    logger.info("Exemplo:")
    logger.info("  from common.ble.advertising import Advertisement, register_advertisement")
