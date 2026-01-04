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

            # Debug: mostrar todos os paths do dispositivo
            device_paths = [p for p in objects.keys() if p.startswith(device_path)]
            logger.debug(f"Paths D-Bus encontrados para {device_path}: {len(device_paths)}")
            for p in device_paths[:10]:  # Mostrar primeiros 10
                logger.debug(f"  {p}")

            # Procurar características do dispositivo
            char_uuid_lower = char_uuid.lower()
            characteristics_found = []

            for path, interfaces in objects.items():
                if not path.startswith(device_path):
                    continue

                if self.GATT_CHARACTERISTIC_IFACE in interfaces:
                    props = interfaces[self.GATT_CHARACTERISTIC_IFACE]
                    uuid = props.get('UUID', '').lower()
                    characteristics_found.append((path, uuid))

                    if uuid == char_uuid_lower:
                        logger.debug(f" Característica encontrada: {path}")
                        return path

            # Debug: mostrar características encontradas
            logger.warning(f"Característica {char_uuid} não encontrada em {device_path}")
            logger.debug(f"Características disponíveis ({len(characteristics_found)}):")
            for path, uuid in characteristics_found[:10]:
                logger.debug(f"  {uuid} -> {path}")

            return None

        except dbus.exceptions.DBusException as e:
            logger.error(f"Erro D-Bus ao procurar característica: {e}")
            return None

    def _trigger_service_discovery(self, device_address: str) -> bool:
        """
        Força o BlueZ a descobrir serviços GATT do dispositivo.

        Args:
            device_address: Endereço MAC do dispositivo

        Returns:
            True se descoberta foi iniciada
        """
        try:
            device_path = self._get_device_path(device_address)
            device_obj = self.bus.get_object(self.BLUEZ_SERVICE, device_path)
            device_props = dbus.Interface(device_obj, "org.freedesktop.DBus.Properties")

            services_resolved = device_props.Get(self.DEVICE_IFACE, "ServicesResolved")
            logger.debug(f"ServicesResolved antes: {services_resolved}")

            if not services_resolved:
                logger.debug("A forçar descoberta de serviços GATT via D-Bus...")
                # O BlueZ descobre automaticamente após connect, mas podemos verificar UUIDs
                uuids = device_props.Get(self.DEVICE_IFACE, "UUIDs")
                logger.debug(f"UUIDs anunciados: {len(uuids) if uuids else 0}")

                # Aguardar um pouco para o BlueZ resolver serviços
                import time
                for i in range(5):
                    time.sleep(1)
                    services_resolved = device_props.Get(self.DEVICE_IFACE, "ServicesResolved")
                    logger.debug(f"ServicesResolved tentativa {i+1}: {services_resolved}")
                    if services_resolved:
                        break

            return services_resolved

        except dbus.exceptions.DBusException as e:
            logger.warning(f"Erro ao verificar ServicesResolved: {e}")
            return False

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

            # Forçar descoberta de serviços se necessário
            self._trigger_service_discovery(device_address)

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

            logger.debug(f" Escrita bem-sucedida via D-Bus!")
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

            logger.debug(f" Leitura bem-sucedida via D-Bus: {len(data)} bytes")
            return data

        except dbus.exceptions.DBusException as e:
            logger.error(f"Erro D-Bus ao ler: {e}")
            return None
        except Exception as e:
            logger.error(f"Erro ao ler via D-Bus: {e}")
            return None
