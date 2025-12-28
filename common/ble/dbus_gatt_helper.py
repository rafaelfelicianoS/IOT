#!/usr/bin/env python3
"""
Helper para operações GATT via D-Bus direto.

SimpleBLE no Linux tem limitações ao descobrir características.
Este módulo usa D-Bus (BlueZ) diretamente para operações GATT
quando o SimpleBLE falha.
"""
import dbus
from typing import Optional, List
from loguru import logger

class DBusGATTHelper:
    """Helper para operações GATT via D-Bus do BlueZ."""

    BLUEZ_SERVICE = "org.bluez"
    GATT_CHARACTERISTIC_IFACE = "org.bluez.GattCharacteristic1"
    GATT_SERVICE_IFACE = "org.bluez.GattService1"
    DEVICE_IFACE = "org.bluez.Device1"

    def __init__(self, adapter_name: str = "hci0"):
        """
        Inicializa o helper D-Bus.

        Args:
            adapter_name: Nome do adaptador (ex: hci0, hci1)
        """
        self.adapter_name = adapter_name
        self.bus = dbus.SystemBus()

    def _get_device_path(self, device_address: str) -> Optional[str]:
        """
        Obtém o caminho D-Bus do dispositivo.

        Args:
            device_address: Endereço MAC (ex: E0:D3:62:D6:EE:A0)

        Returns:
            Caminho D-Bus ou None se não encontrado
        """
        # Formato: /org/bluez/hci0/dev_E0_D3_62_D6_EE_A0
        formatted_addr = device_address.replace(":", "_")
        return f"/org/bluez/{self.adapter_name}/dev_{formatted_addr}"

    def _find_characteristic(self, device_path: str, char_uuid: str) -> Optional[str]:
        """
        Procura uma característica pelo UUID no dispositivo.

        Args:
            device_path: Caminho D-Bus do dispositivo
            char_uuid: UUID da característica

        Returns:
            Caminho D-Bus da característica ou None
        """
        try:
            obj_manager = dbus.Interface(
                self.bus.get_object(self.BLUEZ_SERVICE, "/"),
                "org.freedesktop.DBus.ObjectManager"
            )

            objects = obj_manager.GetManagedObjects()

            # Procurar características do dispositivo
            char_uuid_lower = char_uuid.lower()
            for path, interfaces in objects.items():
                if not path.startswith(device_path):
                    continue

                if self.GATT_CHARACTERISTIC_IFACE in interfaces:
                    props = interfaces[self.GATT_CHARACTERISTIC_IFACE]
                    if props.get('UUID', '').lower() == char_uuid_lower:
                        logger.debug(f"Característica encontrada: {path}")
                        return path

            logger.warning(f"Característica {char_uuid} não encontrada em {device_path}")
            return None

        except dbus.exceptions.DBusException as e:
            logger.error(f"Erro D-Bus ao procurar característica: {e}")
            return None

    def write_characteristic(
        self,
        device_address: str,
        service_uuid: str,
        char_uuid: str,
        data: bytes
    ) -> bool:
        """
        Escreve dados numa característica via D-Bus.

        Args:
            device_address: Endereço MAC do dispositivo
            service_uuid: UUID do serviço (não usado, mas mantido para compatibilidade)
            char_uuid: UUID da característica
            data: Dados a escrever

        Returns:
            True se escrita bem-sucedida
        """
        try:
            device_path = self._get_device_path(device_address)
            logger.debug(f"Device path: {device_path}")

            # Procurar característica
            char_path = self._find_characteristic(device_path, char_uuid)
            if not char_path:
                logger.error(f"Característica {char_uuid} não encontrada")
                return False

            # Obter interface da característica
            char_obj = self.bus.get_object(self.BLUEZ_SERVICE, char_path)
            char_iface = dbus.Interface(char_obj, self.GATT_CHARACTERISTIC_IFACE)

            # Escrever dados
            logger.debug(f"A escrever {len(data)} bytes em {char_uuid}...")
            char_iface.WriteValue(list(data), {})

            logger.debug(f"✅ Escrita bem-sucedida via D-Bus!")
            return True

        except dbus.exceptions.DBusException as e:
            logger.error(f"Erro D-Bus ao escrever: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro ao escrever via D-Bus: {e}")
            return False

    def read_characteristic(
        self,
        device_address: str,
        service_uuid: str,
        char_uuid: str
    ) -> Optional[bytes]:
        """
        Lê dados de uma característica via D-Bus.

        Args:
            device_address: Endereço MAC do dispositivo
            service_uuid: UUID do serviço (não usado, mas mantido para compatibilidade)
            char_uuid: UUID da característica

        Returns:
            Dados lidos ou None se erro
        """
        try:
            device_path = self._get_device_path(device_address)

            # Procurar característica
            char_path = self._find_characteristic(device_path, char_uuid)
            if not char_path:
                logger.error(f"Característica {char_uuid} não encontrada")
                return None

            # Obter interface da característica
            char_obj = self.bus.get_object(self.BLUEZ_SERVICE, char_path)
            char_iface = dbus.Interface(char_obj, self.GATT_CHARACTERISTIC_IFACE)

            # Ler dados
            logger.debug(f"A ler de {char_uuid}...")
            value = char_iface.ReadValue({})
            data = bytes(value)

            logger.debug(f"✅ Leitura bem-sucedida via D-Bus: {len(data)} bytes")
            return data

        except dbus.exceptions.DBusException as e:
            logger.error(f"Erro D-Bus ao ler: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao ler via D-Bus: {e}")
            return None
