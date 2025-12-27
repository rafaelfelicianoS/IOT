"""
GATT Server implementation using D-Bus and BlueZ.

Fornece classes base para criar serviços GATT customizados que podem ser
registados com o BlueZ stack do Linux via D-Bus.

Baseado no exemplo: docs/src-exploring-bluetooth/gatt_server.py

Arquitetura:
    Application (D-Bus ObjectManager)
    └── Service (org.bluez.GattService1)
        └── Characteristic (org.bluez.GattCharacteristic1)
            └── Descriptor (org.bluez.GattDescriptor1)
"""

import sys
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GLib
from typing import List, Optional, Dict, Any

from common.utils.constants import (
    BLUEZ_SERVICE_NAME,
    GATT_MANAGER_IFACE,
    GATT_SERVICE_IFACE,
    GATT_CHARACTERISTIC_IFACE,
    GATT_DESCRIPTOR_IFACE,
    DBUS_PROP_IFACE,
    DBUS_OM_IFACE,
)
from common.utils.logger import get_logger

logger = get_logger("gatt_server")


# ============================================================================
# Exceções
# ============================================================================

class InvalidArgsException(dbus.exceptions.DBusException):
    """Exceção para argumentos inválidos."""
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'


class NotSupportedException(dbus.exceptions.DBusException):
    """Exceção para operações não suportadas."""
    _dbus_error_name = 'org.bluez.Error.NotSupported'


class NotPermittedException(dbus.exceptions.DBusException):
    """Exceção para operações não permitidas."""
    _dbus_error_name = 'org.bluez.Error.NotPermitted'


class FailedException(dbus.exceptions.DBusException):
    """Exceção genérica para falhas."""
    _dbus_error_name = 'org.bluez.Error.Failed'


# ============================================================================
# Descriptor - org.bluez.GattDescriptor1
# ============================================================================

class Descriptor(dbus.service.Object):
    """
    Classe base para GATT Descriptors.

    Descriptors fornecem metadados sobre Characteristics (ex: descrição, formato).
    """

    def __init__(
        self,
        bus: dbus.SystemBus,
        index: int,
        uuid: str,
        flags: List[str],
        characteristic: 'Characteristic',
    ):
        """
        Inicializa um Descriptor.

        Args:
            bus: D-Bus system bus
            index: Índice do descriptor (usado no path)
            uuid: UUID do descriptor (128 bits)
            flags: Flags (ex: ['read', 'write'])
            characteristic: Characteristic parent
        """
        self.path = characteristic.path + '/desc' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.flags = flags
        self.chrc = characteristic

        dbus.service.Object.__init__(self, bus, self.path)
        logger.debug(f"Descriptor criado: {self.path} (UUID: {uuid})")

    def get_properties(self) -> Dict[str, Dict[str, Any]]:
        """Retorna as propriedades do descriptor."""
        return {
            GATT_DESCRIPTOR_IFACE: {
                'Characteristic': self.chrc.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
            }
        }

    def get_path(self) -> dbus.ObjectPath:
        """Retorna o D-Bus path do descriptor."""
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface: str):
        """D-Bus method: GetAll properties."""
        logger.debug(f"GetAll called on {self.path}")

        if interface != GATT_DESCRIPTOR_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_DESCRIPTOR_IFACE]

    @dbus.service.method(GATT_DESCRIPTOR_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options: Dict[str, Any]):
        """
        D-Bus method: ReadValue.

        Deve ser sobrescrito por subclasses.
        """
        logger.warning(f"ReadValue not implemented for {self.path}")
        raise NotSupportedException()

    @dbus.service.method(GATT_DESCRIPTOR_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value: List[int], options: Dict[str, Any]):
        """
        D-Bus method: WriteValue.

        Deve ser sobrescrito por subclasses.
        """
        logger.warning(f"WriteValue not implemented for {self.path}")
        raise NotSupportedException()


# ============================================================================
# Characteristic - org.bluez.GattCharacteristic1
# ============================================================================

class Characteristic(dbus.service.Object):
    """
    Classe base para GATT Characteristics.

    Characteristics são os valores principais num serviço GATT.
    Podem ser lidos, escritos, e podem notificar clientes de mudanças.
    """

    def __init__(
        self,
        bus: dbus.SystemBus,
        index: int,
        uuid: str,
        flags: List[str],
        service: 'Service',
    ):
        """
        Inicializa uma Characteristic.

        Args:
            bus: D-Bus system bus
            index: Índice da characteristic (usado no path)
            uuid: UUID da characteristic (128 bits)
            flags: Flags (ex: ['read', 'write', 'notify'])
            service: Service parent
        """
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors: List[Descriptor] = []
        self.notifying = False

        dbus.service.Object.__init__(self, bus, self.path)
        logger.debug(f"Characteristic criada: {self.path} (UUID: {uuid}, flags: {flags})")

    def get_properties(self) -> Dict[str, Dict[str, Any]]:
        """Retorna as propriedades da characteristic."""
        return {
            GATT_CHARACTERISTIC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Descriptors': dbus.Array(self.get_descriptor_paths(), signature='o'),
            }
        }

    def get_path(self) -> dbus.ObjectPath:
        """Retorna o D-Bus path da characteristic."""
        return dbus.ObjectPath(self.path)

    def add_descriptor(self, descriptor: Descriptor):
        """Adiciona um descriptor a esta characteristic."""
        self.descriptors.append(descriptor)
        logger.debug(f"Descriptor adicionado a {self.path}: {descriptor.path}")

    def get_descriptor_paths(self) -> List[dbus.ObjectPath]:
        """Retorna os paths de todos os descriptors."""
        return [desc.get_path() for desc in self.descriptors]

    def get_descriptors(self) -> List[Descriptor]:
        """Retorna todos os descriptors."""
        return self.descriptors

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface: str):
        """D-Bus method: GetAll properties."""
        logger.debug(f"GetAll called on {self.path}")

        if interface != GATT_CHARACTERISTIC_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_CHARACTERISTIC_IFACE]

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options: Dict[str, Any]):
        """
        D-Bus method: ReadValue.

        Deve ser sobrescrito por subclasses que suportam leitura.
        """
        logger.warning(f"ReadValue not implemented for {self.path}")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value: List[int], options: Dict[str, Any]):
        """
        D-Bus method: WriteValue.

        Deve ser sobrescrito por subclasses que suportam escrita.
        """
        logger.warning(f"WriteValue not implemented for {self.path}")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE)
    def StartNotify(self):
        """
        D-Bus method: StartNotify.

        Deve ser sobrescrito por subclasses que suportam notificações.
        """
        logger.warning(f"StartNotify not implemented for {self.path}")
        raise NotSupportedException()

    @dbus.service.method(GATT_CHARACTERISTIC_IFACE)
    def StopNotify(self):
        """
        D-Bus method: StopNotify.

        Deve ser sobrescrito por subclasses que suportam notificações.
        """
        logger.warning(f"StopNotify not implemented for {self.path}")
        raise NotSupportedException()

    @dbus.service.signal(DBUS_PROP_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface: str, changed: Dict[str, Any], invalidated: List[str]):
        """
        D-Bus signal: PropertiesChanged.

        Usado para notificar clientes de mudanças em propriedades.
        """
        pass


# ============================================================================
# Service - org.bluez.GattService1
# ============================================================================

class Service(dbus.service.Object):
    """
    Classe base para GATT Services.

    Um Service agrupa um conjunto de Characteristics relacionadas.
    """

    def __init__(
        self,
        bus: dbus.SystemBus,
        path: str,
        index: int,
        uuid: str,
        primary: bool = True,
    ):
        """
        Inicializa um Service.

        Args:
            bus: D-Bus system bus
            path: Base path (ex: '/org/bluez/example/service')
            index: Índice do service (usado no path)
            uuid: UUID do service (128 bits)
            primary: Se é um primary service
        """
        self.path = path + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics: List[Characteristic] = []

        dbus.service.Object.__init__(self, bus, self.path)
        logger.info(f"Service criado: {self.path} (UUID: {uuid}, primary: {primary})")

    def get_properties(self) -> Dict[str, Dict[str, Any]]:
        """Retorna as propriedades do service."""
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(self.get_characteristic_paths(), signature='o'),
            }
        }

    def get_path(self) -> dbus.ObjectPath:
        """Retorna o D-Bus path do service."""
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, characteristic: Characteristic):
        """Adiciona uma characteristic a este service."""
        self.characteristics.append(characteristic)
        logger.debug(f"Characteristic adicionada a {self.path}: {characteristic.path}")

    def get_characteristic_paths(self) -> List[dbus.ObjectPath]:
        """Retorna os paths de todas as characteristics."""
        return [chrc.get_path() for chrc in self.characteristics]

    def get_characteristics(self) -> List[Characteristic]:
        """Retorna todas as characteristics."""
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface: str):
        """D-Bus method: GetAll properties."""
        logger.debug(f"GetAll called on {self.path}")

        if interface != GATT_SERVICE_IFACE:
            raise InvalidArgsException()

        return self.get_properties()[GATT_SERVICE_IFACE]


# ============================================================================
# Application - org.freedesktop.DBus.ObjectManager
# ============================================================================

class Application(dbus.service.Object):
    """
    GATT Application - implementa D-Bus ObjectManager.

    Agrega todos os Services, Characteristics e Descriptors da aplicação.
    """

    def __init__(self, bus: dbus.SystemBus, path: str = '/'):
        """
        Inicializa uma Application.

        Args:
            bus: D-Bus system bus
            path: D-Bus path da aplicação (default: '/')
        """
        self.path = path
        self.services: List[Service] = []

        dbus.service.Object.__init__(self, bus, self.path)
        logger.info(f"Application criada: {self.path}")

    def get_path(self) -> dbus.ObjectPath:
        """Retorna o D-Bus path da aplicação."""
        return dbus.ObjectPath(self.path)

    def add_service(self, service: Service):
        """Adiciona um service à aplicação."""
        self.services.append(service)
        logger.info(f"Service adicionado à aplicação: {service.path}")

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        """
        D-Bus method: GetManagedObjects.

        Retorna todos os objetos geridos pela aplicação (services, characteristics, descriptors).
        Chamado pelo BlueZ quando a aplicação é registada.
        """
        logger.debug("GetManagedObjects called")

        response = {}

        # Adicionar todos os services
        for service in self.services:
            response[service.get_path()] = service.get_properties()

            # Adicionar características do service
            for chrc in service.get_characteristics():
                response[chrc.get_path()] = chrc.get_properties()

                # Adicionar descriptors da characteristic
                for desc in chrc.get_descriptors():
                    response[desc.get_path()] = desc.get_properties()

        logger.debug(f"GetManagedObjects returning {len(response)} objects")
        return response


# ============================================================================
# Funções de Utilidade
# ============================================================================

def register_application(
    application: Application,
    adapter_name: str = 'hci0',
) -> GLib.MainLoop:
    """
    Regista uma GATT application com o BlueZ e inicia o mainloop.

    Args:
        application: Application a registar
        adapter_name: Nome do adaptador BLE (ex: 'hci0')

    Returns:
        GLib.MainLoop (já a correr)

    Raises:
        Exception: Se falhar o registo
    """
    # Setup D-Bus mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    # Get system bus
    bus = dbus.SystemBus()

    # Get adapter
    adapter_path = f"/org/bluez/{adapter_name}"
    logger.info(f"A usar adaptador: {adapter_path}")

    try:
        adapter_obj = bus.get_object(BLUEZ_SERVICE_NAME, adapter_path)
        gatt_manager = dbus.Interface(adapter_obj, GATT_MANAGER_IFACE)
    except dbus.exceptions.DBusException as e:
        logger.error(f"Erro ao aceder ao adaptador {adapter_name}: {e}")
        raise

    # Create mainloop
    mainloop = GLib.MainLoop()

    # Register application
    logger.info("A registar GATT application...")
    gatt_manager.RegisterApplication(
        application.get_path(),
        {},
        reply_handler=lambda: logger.info("✅ GATT application registada com sucesso!"),
        error_handler=lambda e: logger.error(f"❌ Falha ao registar application: {e}"),
    )

    return mainloop


# ============================================================================
# Exemplo de Uso (se executado diretamente)
# ============================================================================

if __name__ == '__main__':
    logger.info("GATT Server - Base Classes")
    logger.info("Este módulo fornece classes base para criar serviços GATT.")
    logger.info("Use-o importando as classes em outros módulos.")
    logger.info("")
    logger.info("Exemplo:")
    logger.info("  from common.ble.gatt_server import Application, Service, Characteristic")
