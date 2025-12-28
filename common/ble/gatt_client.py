"""
BLE Client implementation using SimpleBLE.

Permite a um dispositivo:
- Fazer scan de dispositivos BLE nearby
- Conectar a outros dispositivos BLE
- Ler/Escrever em características GATT
- Subscrever a notificações
"""

import time
from typing import List, Optional, Callable, Dict, Any
from dataclasses import dataclass

try:
    import simplepyble as simpleble
    SIMPLEBLE_AVAILABLE = True
except ImportError:
    SIMPLEBLE_AVAILABLE = False
    print("⚠️  SimpleBLE não está disponível. Instalar com: pip install simplepyble")

from common.utils.logger import get_logger
from common.utils.ble_logger import get_ble_logger
from common.utils.constants import IOT_NETWORK_SERVICE_UUID
from common.ble.dbus_gatt_helper import DBusGATTHelper

logger = get_logger("gatt_client")


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ScannedDevice:
    """
    Representa um dispositivo encontrado durante o scan.
    """
    address: str
    identifier: str
    rssi: int
    name: Optional[str] = None
    service_uuids: List[str] = None
    manufacturer_data: Dict[int, bytes] = None

    def __post_init__(self):
        if self.service_uuids is None:
            self.service_uuids = []
        if self.manufacturer_data is None:
            self.manufacturer_data = {}

    def __str__(self):
        return f"{self.name or 'Unknown'} ({self.address}) RSSI: {self.rssi} dBm"

    def has_iot_service(self) -> bool:
        """
        Verifica se o dispositivo anuncia o serviço IoT Network.

        SimpleBLE não expõe Service UUIDs do advertising packet, então verificamos:
        1. Manufacturer Data (método principal - sempre funciona)
        2. Service UUIDs (fallback - só funciona se SimpleBLE os expuser)
        """
        from common.utils.constants import (
            IOT_NETWORK_SERVICE_UUID,
            IOT_MANUFACTURER_ID,
            IOT_MANUFACTURER_DATA_MAGIC
        )

        # 1. Verificar manufacturer data (MÉTODO PRINCIPAL)
        if self.manufacturer_data and IOT_MANUFACTURER_ID in self.manufacturer_data:
            data = self.manufacturer_data[IOT_MANUFACTURER_ID]
            if data == IOT_MANUFACTURER_DATA_MAGIC:
                return True

        # 2. Verificar service UUIDs (FALLBACK - pode não funcionar com SimpleBLE)
        if not self.service_uuids:
            return False

        # Normalizar UUIDs do dispositivo (remover hífens e lowercase)
        device_uuids = [uuid.lower().replace('-', '') for uuid in self.service_uuids]

        # UUID completo normalizado
        full_uuid_norm = IOT_NETWORK_SERVICE_UUID.lower().replace('-', '')

        # Primeiros 8 caracteres hex (32 bits)
        short_32 = full_uuid_norm[:8]  # "12340000"

        for uuid in device_uuids:
            # Verificar match exato com UUID completo
            if uuid == full_uuid_norm:
                return True
            # Verificar se começa com os primeiros 32 bits
            if uuid.startswith(short_32):
                return True
            # Verificar apenas os primeiros 8 chars
            if uuid == short_32:
                return True

        return False


@dataclass
class GATTService:
    """Representa um GATT Service."""
    uuid: str
    characteristics: List['GATTCharacteristic']

    def get_characteristic(self, uuid: str) -> Optional['GATTCharacteristic']:
        """Retorna uma característica pelo UUID."""
        for char in self.characteristics:
            if char.uuid.lower() == uuid.lower():
                return char
        return None


@dataclass
class GATTCharacteristic:
    """Representa uma GATT Characteristic."""
    uuid: str
    capabilities: List[str]  # ['read', 'write', 'notify', 'indicate']


# ============================================================================
# BLE Scanner
# ============================================================================

class BLEScanner:
    """
    Scanner BLE para descobrir dispositivos nearby.
    """

    def __init__(self, adapter_index: int = 0):
        """
        Inicializa o scanner BLE.

        Args:
            adapter_index: Índice do adaptador BLE (0 = hci0, 1 = hci1, etc.)
        """
        if not SIMPLEBLE_AVAILABLE:
            raise RuntimeError("SimpleBLE não está disponível")

        adapters = simpleble.Adapter.get_adapters()
        if not adapters:
            raise RuntimeError("Nenhum adaptador BLE encontrado")

        if adapter_index >= len(adapters):
            raise RuntimeError(f"Adaptador {adapter_index} não existe")

        self.adapter = adapters[adapter_index]
        self.ble_log = get_ble_logger(self.adapter.address())
        logger.info(f"Scanner BLE iniciado: {self.adapter.identifier()} ({self.adapter.address()})")

    def clear_cache(self):
        """
        Limpa o cache de scan do adaptador BLE.

        SimpleBLE pode manter resultados antigos em cache.
        Este método faz um scan curto para forçar refresh.
        """
        logger.debug("A limpar cache de scan BLE...")
        # Scan curto (100ms) para refresh
        self.adapter.scan_for(100)
        # Descartar resultados
        _ = self.adapter.scan_get_results()
        logger.debug("Cache de scan limpo")

    def scan(self, duration_ms: int = 5000, filter_iot: bool = False) -> List[ScannedDevice]:
        """
        Faz scan de dispositivos BLE.

        Args:
            duration_ms: Duração do scan em milissegundos
            filter_iot: Se True, retorna apenas dispositivos com IoT Network Service

        Returns:
            Lista de dispositivos encontrados
        """
        logger.info(f"A fazer scan BLE durante {duration_ms}ms...")
        self.ble_log.log_scan_start(duration_ms, filter_iot)

        self.adapter.scan_for(duration_ms)
        peripherals = self.adapter.scan_get_results()

        devices = []
        for peripheral in peripherals:
            # Extrair service UUIDs
            service_uuids = []
            manufacturer_data = {}

            try:
                # Tentar obter service UUIDs (nem todos os dispositivos anunciam)
                if hasattr(peripheral, 'services'):
                    service_uuids = [str(service.uuid()) for service in peripheral.services()]

                # Tentar obter manufacturer data
                if hasattr(peripheral, 'manufacturer_data'):
                    for mfr_id, data in peripheral.manufacturer_data().items():
                        manufacturer_data[mfr_id] = bytes(data)
            except Exception as e:
                logger.debug(f"Erro ao obter dados do periférico {peripheral.address()}: {e}")

            device = ScannedDevice(
                address=peripheral.address(),
                identifier=peripheral.identifier(),
                rssi=peripheral.rssi(),
                name=peripheral.identifier() if peripheral.identifier() else None,
                service_uuids=service_uuids,
                manufacturer_data=manufacturer_data,
            )

            # Filtrar por IoT Network Service se pedido
            if filter_iot and not device.has_iot_service():
                continue

            devices.append(device)
            logger.debug(f"  Encontrado: {device}")

        logger.info(f"Scan concluído: {len(devices)} dispositivos encontrados")
        self.ble_log.log_scan_result(len(devices), devices)
        return devices


# ============================================================================
# BLE Connection
# ============================================================================

class BLEConnection:
    """
    Representa uma conexão BLE a um dispositivo remoto.
    """

    def __init__(self, peripheral, adapter_name: str = "hci0"):
        """
        Inicializa a conexão BLE.

        Args:
            peripheral: SimpleBLE Peripheral object
            adapter_name: Nome do adaptador BLE (para D-Bus helper)
        """
        self.peripheral = peripheral
        self.address = peripheral.address()
        self.is_connected = False
        self._notification_callbacks: Dict[str, Callable] = {}
        self.ble_log = get_ble_logger()
        self.dbus_helper = DBusGATTHelper(adapter_name)  # Helper para quando SimpleBLE falhar

        logger.debug(f"BLEConnection criada para {self.address}")

    def connect(self, timeout_ms: int = 5000) -> bool:
        """
        Conecta ao dispositivo remoto.

        Args:
            timeout_ms: Timeout em milissegundos

        Returns:
            True se conectado com sucesso
        """
        import time

        try:
            logger.info(f"A conectar a {self.address}...")
            self.ble_log.log_connection_attempt(self.address)

            start_time = time.time()
            self.peripheral.connect()
            connection_time_ms = (time.time() - start_time) * 1000

            self.is_connected = self.peripheral.is_connected()

            if self.is_connected:
                logger.info(f"✅ Conectado a {self.address}")
                self.ble_log.log_connection_success(self.address, connection_time_ms)

                # IMPORTANTE: Descobrir serviços GATT após conexão
                # SimpleBLE requer esta chamada para popular a lista de serviços
                # Aguardar e tentar múltiplas vezes se necessário
                logger.debug("A aguardar descoberta de serviços GATT...")

                services = []
                max_retries = 5  # Aumentar para 5 tentativas
                has_characteristics = False

                for attempt in range(max_retries):
                    time.sleep(2.0)  # Aguardar 2 segundos entre tentativas

                    try:
                        services = self.peripheral.services()

                        # Verificar se algum serviço tem características
                        total_chars = sum(len(svc.characteristics()) for svc in services)
                        has_characteristics = total_chars > 0

                        logger.debug(f"Tentativa {attempt + 1}/{max_retries}: {len(services)} serviços, {total_chars} características")

                        if len(services) > 0:
                            # Serviços encontrados, mostrar detalhes
                            for svc in services:
                                num_chars = len(svc.characteristics())
                                logger.debug(f"  - {svc.uuid()} ({num_chars} características)")

                            # Se temos serviços E características, terminar
                            if has_characteristics:
                                logger.debug("✅ Serviços e características descobertos com sucesso!")
                                break
                            elif attempt < max_retries - 1:
                                logger.debug("  Serviços encontrados mas sem características, a tentar novamente...")
                        elif attempt < max_retries - 1:
                            logger.debug("  Nenhum serviço ainda, a tentar novamente...")
                    except Exception as e:
                        logger.warning(f"Aviso ao descobrir serviços (tentativa {attempt + 1}): {e}")

                if len(services) == 0:
                    logger.warning("⚠️  Nenhum serviço GATT descoberto após múltiplas tentativas")
                elif not has_characteristics:
                    logger.warning("⚠️  Serviços descobertos mas sem características - SimpleBLE pode ter limitações")

                return True
            else:
                logger.error(f"❌ Falha ao conectar a {self.address}")
                self.ble_log.log_connection_failed(self.address, "Connection failed")
                return False

        except Exception as e:
            logger.error(f"Erro ao conectar a {self.address}: {e}")
            self.ble_log.log_connection_failed(self.address, str(e))
            return False

    def disconnect(self):
        """Desconecta do dispositivo."""
        if self.is_connected:
            try:
                self.peripheral.disconnect()
                self.is_connected = False
                logger.info(f"Desconectado de {self.address}")
                self.ble_log.log_disconnection(self.address, "normal")
            except Exception as e:
                logger.error(f"Erro ao desconectar de {self.address}: {e}")
                self.ble_log.log_disconnection(self.address, f"error: {e}")

    def get_services(self) -> List[GATTService]:
        """
        Retorna todos os serviços GATT do dispositivo.

        Returns:
            Lista de serviços GATT
        """
        if not self.is_connected:
            logger.error("Não conectado - não é possível obter serviços")
            return []

        services = []
        for service in self.peripheral.services():
            characteristics = []
            for char in service.characteristics():
                # Converter capabilities para lista de strings
                caps = []
                if char.can_read():
                    caps.append('read')
                if char.can_write_request() or char.can_write_command():
                    caps.append('write')
                if char.can_notify():
                    caps.append('notify')
                if char.can_indicate():
                    caps.append('indicate')

                characteristics.append(GATTCharacteristic(
                    uuid=str(char.uuid()),
                    capabilities=caps,
                ))

            services.append(GATTService(
                uuid=str(service.uuid()),
                characteristics=characteristics,
            ))

        return services

    def read_characteristic(self, service_uuid: str, char_uuid: str) -> Optional[bytes]:
        """
        Lê o valor de uma característica.

        Args:
            service_uuid: UUID do serviço
            char_uuid: UUID da característica

        Returns:
            Valor lido (bytes) ou None se erro
        """
        if not self.is_connected:
            logger.error("Não conectado - não é possível ler")
            return None

        try:
            self.ble_log.log_read_request(self.address, service_uuid, char_uuid)
            data = self.peripheral.read(service_uuid, char_uuid)
            data_bytes = bytes(data)
            logger.debug(f"Read {char_uuid}: {len(data_bytes)} bytes")
            self.ble_log.log_read_response(self.address, service_uuid, char_uuid, data_bytes, success=True)
            return data_bytes
        except Exception as e:
            logger.error(f"Erro ao ler {char_uuid}: {e}")
            self.ble_log.log_read_response(self.address, service_uuid, char_uuid, b"", success=False)
            return None

    def write_characteristic(
        self,
        service_uuid: str,
        char_uuid: str,
        data: bytes,
        with_response: bool = True
    ) -> bool:
        """
        Escreve um valor numa característica.

        Args:
            service_uuid: UUID do serviço
            char_uuid: UUID da característica
            data: Dados a escrever
            with_response: Se True, usa write request (com resposta)

        Returns:
            True se escrita bem-sucedida
        """
        if not self.is_connected:
            logger.error("Não conectado - não é possível escrever")
            return False

        try:
            self.ble_log.log_write_request(self.address, service_uuid, char_uuid, data, with_response)

            # Tentar SimpleBLE primeiro
            try:
                if with_response:
                    self.peripheral.write_request(service_uuid, char_uuid, data)
                else:
                    self.peripheral.write_command(service_uuid, char_uuid, data)

                logger.debug(f"✅ Write via SimpleBLE: {char_uuid} ({len(data)} bytes)")
                self.ble_log.log_write_response(self.address, char_uuid, success=True)
                return True

            except Exception as simpleble_error:
                # SimpleBLE falhou - tentar D-Bus
                logger.warning(f"SimpleBLE falhou ({simpleble_error}), a tentar via D-Bus...")

                success = self.dbus_helper.write_characteristic(
                    self.address,
                    service_uuid,
                    char_uuid,
                    data
                )

                if success:
                    logger.debug(f"✅ Write via D-Bus: {char_uuid} ({len(data)} bytes)")
                    self.ble_log.log_write_response(self.address, char_uuid, success=True)
                    return True
                else:
                    raise Exception("Falha tanto em SimpleBLE quanto em D-Bus")

        except Exception as e:
            logger.error(f"Erro ao escrever em {char_uuid}: {e}")
            self.ble_log.log_write_response(self.address, char_uuid, success=False, error=str(e))
            return False

    def subscribe_notifications(
        self,
        service_uuid: str,
        char_uuid: str,
        callback: Callable[[bytes], None]
    ) -> bool:
        """
        Subscreve a notificações de uma característica.

        Args:
            service_uuid: UUID do serviço
            char_uuid: UUID da característica
            callback: Função chamada quando recebe notificação (recebe bytes)

        Returns:
            True se subscrição bem-sucedida
        """
        if not self.is_connected:
            logger.error("Não conectado - não é possível subscrever")
            return False

        try:
            # Wrapper para converter SimpleBLE bytearray para bytes E fazer logging
            def notification_wrapper(data):
                data_bytes = bytes(data)
                self.ble_log.log_notification(self.address, char_uuid, data_bytes)
                callback(data_bytes)

            self.peripheral.notify(service_uuid, char_uuid, notification_wrapper)
            self._notification_callbacks[char_uuid] = callback
            logger.info(f"✅ Subscrito a notificações: {char_uuid}")
            self.ble_log.log_subscribe(self.address, char_uuid, success=True)
            return True

        except Exception as e:
            logger.error(f"Erro ao subscrever {char_uuid}: {e}")
            self.ble_log.log_subscribe(self.address, char_uuid, success=False)
            return False

    def unsubscribe_notifications(self, service_uuid: str, char_uuid: str) -> bool:
        """
        Remove subscrição de notificações.

        Args:
            service_uuid: UUID do serviço
            char_uuid: UUID da característica

        Returns:
            True se remoção bem-sucedida
        """
        if not self.is_connected:
            return False

        try:
            self.peripheral.unsubscribe(service_uuid, char_uuid)
            if char_uuid in self._notification_callbacks:
                del self._notification_callbacks[char_uuid]
            logger.info(f"Cancelada subscrição: {char_uuid}")
            return True
        except Exception as e:
            logger.error(f"Erro ao cancelar subscrição {char_uuid}: {e}")
            return False


# ============================================================================
# BLE Client (High-Level)
# ============================================================================

class BLEClient:
    """
    Cliente BLE de alto nível para interagir com dispositivos IoT.
    """

    def __init__(self, adapter_index: int = 0):
        """
        Inicializa o cliente BLE.

        Args:
            adapter_index: Índice do adaptador BLE
        """
        if not SIMPLEBLE_AVAILABLE:
            raise RuntimeError("SimpleBLE não está disponível")

        self.scanner = BLEScanner(adapter_index)
        self.connections: Dict[str, BLEConnection] = {}
        self.adapter_name = f"hci{adapter_index}"  # Para D-Bus helper

        logger.info("BLE Client iniciado")

    def scan_iot_devices(self, duration_ms: int = 5000) -> List[ScannedDevice]:
        """
        Faz scan de dispositivos IoT Network.

        Args:
            duration_ms: Duração do scan

        Returns:
            Lista de dispositivos IoT encontrados
        """
        return self.scanner.scan(duration_ms=duration_ms, filter_iot=True)

    def connect_to_device(self, device: ScannedDevice) -> Optional[BLEConnection]:
        """
        Conecta a um dispositivo.

        Args:
            device: Dispositivo a conectar

        Returns:
            BLEConnection se sucesso, None se falha
        """
        # Se já estamos conectados, retornar conexão existente
        if device.address in self.connections:
            conn = self.connections[device.address]
            if conn.is_connected:
                logger.info(f"Já conectado a {device.address}")
                return conn

        # Obter peripheral do scanner (usar o mesmo adapter que fez o scan)
        peripherals = self.scanner.adapter.scan_get_results()

        peripheral = None
        for p in peripherals:
            if p.address() == device.address:
                peripheral = p
                break

        if not peripheral:
            logger.error(f"Dispositivo {device.address} não encontrado")
            return None

        # Criar e conectar
        conn = BLEConnection(peripheral, adapter_name=self.adapter_name)
        if conn.connect():
            self.connections[device.address] = conn
            return conn
        else:
            return None

    def disconnect_from_device(self, address: str):
        """
        Desconecta de um dispositivo.

        Args:
            address: Endereço BLE do dispositivo
        """
        if address in self.connections:
            self.connections[address].disconnect()
            del self.connections[address]

    def disconnect_all(self):
        """Desconecta de todos os dispositivos."""
        for address in list(self.connections.keys()):
            self.disconnect_from_device(address)

    def get_connection(self, address: str) -> Optional[BLEConnection]:
        """
        Retorna a conexão para um dispositivo.

        Args:
            address: Endereço BLE

        Returns:
            BLEConnection ou None
        """
        return self.connections.get(address)


# ============================================================================
# Exemplo de Uso
# ============================================================================

if __name__ == '__main__':
    logger.info("BLE Client - Module")
    logger.info("Este módulo fornece funcionalidade de BLE client.")
    logger.info("")
    logger.info("Exemplo:")
    logger.info("  from common.ble.gatt_client import BLEClient")
    logger.info("")
    logger.info("  client = BLEClient()")
    logger.info("  devices = client.scan_iot_devices()")
    logger.info("  conn = client.connect_to_device(devices[0])")
