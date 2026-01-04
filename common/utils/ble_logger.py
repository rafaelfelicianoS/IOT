"""
BLE Operation Logger - Sistema de logging detalhado para operações BLE.

Regista todas as operações BLE (scan, connect, read, write, notify) com
timestamps, dados trocados, e erros para facilitar debugging.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from loguru import logger

from common.utils.config import config


class BLEOperationLogger:
    """
    Logger especializado para operações BLE.

    Regista todas as operações com detalhes completos incluindo:
    - Timestamps precisos
    - Endereços BLE
    - Dados trocados (hex dump)
    - Erros e exceções
    - Duração de operações
    """

    def __init__(self, device_address: Optional[str] = None):
        """
        Inicializa o BLE Operation Logger.

        Args:
            device_address: Endereço BLE do dispositivo local (opcional)
        """
        self.device_address = device_address or "unknown"
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        log_filename = f"ble_operations_{self.device_address.replace(':', '')}_{self.session_id}.log"
        self.log_file = config.logs_dir / log_filename

        # Configurar logger
        self._setup_logger()

        # Contador de operações
        self.operation_counter = 0

        logger.info(f"BLE Operation Logger iniciado: {log_filename}")

    def _setup_logger(self):
        """Configura o logger específico para operações BLE."""
        try:
            # Garantir que o diretório existe
            config.ensure_directories_exist()

            logger.add(
                self.log_file,
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message}",
                level="DEBUG",
                rotation="10 MB",
                retention="30 days",
                enqueue=True,
            )

        except (PermissionError, OSError) as e:
            logger.warning(f"Não foi possível criar ficheiro de log BLE: {e}")

    def _get_operation_id(self) -> str:
        """Retorna um ID único para a operação."""
        self.operation_counter += 1
        return f"OP-{self.session_id}-{self.operation_counter:04d}"

    def _format_bytes(self, data: bytes, max_length: int = 64) -> str:
        """
        Formata bytes para visualização.

        Args:
            data: Dados em bytes
            max_length: Número máximo de bytes a mostrar

        Returns:
            String formatada com hex e ASCII
        """
        if not data:
            return "<empty>"

        hex_str = data[:max_length].hex()
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[:max_length])

        truncated = " [TRUNCATED]" if len(data) > max_length else ""

        return f"{len(data)} bytes | Hex: {hex_str} | ASCII: {ascii_str}{truncated}"

    def log_scan_start(self, duration_ms: int, filter_iot: bool = False):
        """
        Regista início de scan BLE.

        Args:
            duration_ms: Duração do scan em milissegundos
            filter_iot: Se está a filtrar apenas dispositivos IoT
        """
        op_id = self._get_operation_id()
        logger.info(
            f"[{op_id}] SCAN_START | "
            f"Duration: {duration_ms}ms | "
            f"Filter_IoT: {filter_iot}"
        )

    def log_scan_result(self, devices_found: int, devices: list):
        """
        Regista resultado de scan BLE.

        Args:
            devices_found: Número de dispositivos encontrados
            devices: Lista de dispositivos (ScannedDevice)
        """
        op_id = self._get_operation_id()
        logger.info(
            f"[{op_id}] SCAN_RESULT | "
            f"Devices_Found: {devices_found}"
        )

        for i, device in enumerate(devices, 1):
            logger.debug(
                f"[{op_id}]   Device_{i}: "
                f"Name: {device.name or 'Unknown'} | "
                f"Address: {device.address} | "
                f"RSSI: {device.rssi} dBm | "
                f"Services: {len(device.service_uuids)}"
            )

    def log_connection_attempt(self, remote_address: str):
        """
        Regista tentativa de conexão.

        Args:
            remote_address: Endereço BLE do dispositivo remoto
        """
        op_id = self._get_operation_id()
        logger.info(
            f"[{op_id}] CONNECT_ATTEMPT | "
            f"Local: {self.device_address} | "
            f"Remote: {remote_address}"
        )

    def log_connection_success(self, remote_address: str, connection_time_ms: float):
        """
        Regista conexão bem-sucedida.

        Args:
            remote_address: Endereço BLE do dispositivo remoto
            connection_time_ms: Tempo que demorou a conectar (ms)
        """
        op_id = self._get_operation_id()
        logger.info(
            f"[{op_id}] CONNECT_SUCCESS | "
            f"Remote: {remote_address} | "
            f"Time: {connection_time_ms:.2f}ms"
        )

    def log_connection_failed(self, remote_address: str, error: str):
        """
        Regista falha de conexão.

        Args:
            remote_address: Endereço BLE do dispositivo remoto
            error: Mensagem de erro
        """
        op_id = self._get_operation_id()
        logger.error(
            f"[{op_id}] CONNECT_FAILED | "
            f"Remote: {remote_address} | "
            f"Error: {error}"
        )

    def log_disconnection(self, remote_address: str, reason: str = "normal"):
        """
        Regista desconexão.

        Args:
            remote_address: Endereço BLE do dispositivo remoto
            reason: Razão da desconexão
        """
        op_id = self._get_operation_id()
        logger.info(
            f"[{op_id}] DISCONNECT | "
            f"Remote: {remote_address} | "
            f"Reason: {reason}"
        )

    def log_read_request(
        self,
        remote_address: str,
        service_uuid: str,
        char_uuid: str
    ):
        """
        Regista pedido de leitura GATT.

        Args:
            remote_address: Endereço do dispositivo remoto
            service_uuid: UUID do serviço
            char_uuid: UUID da característica
        """
        op_id = self._get_operation_id()
        logger.debug(
            f"[{op_id}] READ_REQUEST | "
            f"Remote: {remote_address} | "
            f"Service: {service_uuid} | "
            f"Char: {char_uuid}"
        )

    def log_read_response(
        self,
        remote_address: str,
        service_uuid: str,
        char_uuid: str,
        data: bytes,
        success: bool = True
    ):
        """
        Regista resposta de leitura GATT.

        Args:
            remote_address: Endereço do dispositivo remoto
            service_uuid: UUID do serviço
            char_uuid: UUID da característica
            data: Dados lidos
            success: Se a leitura foi bem-sucedida
        """
        op_id = self._get_operation_id()

        if success:
            logger.info(
                f"[{op_id}] READ_RESPONSE | "
                f"Remote: {remote_address} | "
                f"Char: {char_uuid} | "
                f"Data: {self._format_bytes(data)}"
            )
        else:
            logger.error(
                f"[{op_id}] READ_FAILED | "
                f"Remote: {remote_address} | "
                f"Char: {char_uuid}"
            )

    def log_write_request(
        self,
        remote_address: str,
        service_uuid: str,
        char_uuid: str,
        data: bytes,
        with_response: bool = True
    ):
        """
        Regista pedido de escrita GATT.

        Args:
            remote_address: Endereço do dispositivo remoto
            service_uuid: UUID do serviço
            char_uuid: UUID da característica
            data: Dados a escrever
            with_response: Se é write request (True) ou write command (False)
        """
        op_id = self._get_operation_id()
        write_type = "REQUEST" if with_response else "COMMAND"

        logger.info(
            f"[{op_id}] WRITE_{write_type} | "
            f"Remote: {remote_address} | "
            f"Char: {char_uuid} | "
            f"Data: {self._format_bytes(data)}"
        )

    def log_write_response(
        self,
        remote_address: str,
        char_uuid: str,
        success: bool = True,
        error: Optional[str] = None
    ):
        """
        Regista resposta de escrita GATT.

        Args:
            remote_address: Endereço do dispositivo remoto
            char_uuid: UUID da característica
            success: Se a escrita foi bem-sucedida
            error: Mensagem de erro (se houver)
        """
        op_id = self._get_operation_id()

        if success:
            logger.info(
                f"[{op_id}] WRITE_SUCCESS | "
                f"Remote: {remote_address} | "
                f"Char: {char_uuid}"
            )
        else:
            logger.error(
                f"[{op_id}] WRITE_FAILED | "
                f"Remote: {remote_address} | "
                f"Char: {char_uuid} | "
                f"Error: {error}"
            )

    def log_notification(
        self,
        remote_address: str,
        char_uuid: str,
        data: bytes
    ):
        """
        Regista notificação GATT recebida.

        Args:
            remote_address: Endereço do dispositivo remoto
            char_uuid: UUID da característica
            data: Dados da notificação
        """
        op_id = self._get_operation_id()
        logger.info(
            f"[{op_id}] NOTIFICATION | "
            f"Remote: {remote_address} | "
            f"Char: {char_uuid} | "
            f"Data: {self._format_bytes(data)}"
        )

    def log_subscribe(
        self,
        remote_address: str,
        char_uuid: str,
        success: bool = True
    ):
        """
        Regista subscrição a notificações.

        Args:
            remote_address: Endereço do dispositivo remoto
            char_uuid: UUID da característica
            success: Se a subscrição foi bem-sucedida
        """
        op_id = self._get_operation_id()

        if success:
            logger.info(
                f"[{op_id}] SUBSCRIBE_SUCCESS | "
                f"Remote: {remote_address} | "
                f"Char: {char_uuid}"
            )
        else:
            logger.error(
                f"[{op_id}] SUBSCRIBE_FAILED | "
                f"Remote: {remote_address} | "
                f"Char: {char_uuid}"
            )

    def log_error(self, operation: str, error: Exception, context: Dict[str, Any] = None):
        """
        Regista um erro genérico.

        Args:
            operation: Nome da operação que falhou
            error: Exceção capturada
            context: Contexto adicional (dicionário)
        """
        op_id = self._get_operation_id()

        context_str = json.dumps(context) if context else "{}"

        logger.error(
            f"[{op_id}] ERROR | "
            f"Operation: {operation} | "
            f"Error: {type(error).__name__}: {str(error)} | "
            f"Context: {context_str}"
        )

    def log_packet_send(
        self,
        remote_address: str,
        packet_type: str,
        packet_size: int,
        packet_data: bytes
    ):
        """
        Regista envio de pacote da rede IoT.

        Args:
            remote_address: Endereço do dispositivo remoto
            packet_type: Tipo de pacote (DATA, HEARTBEAT, etc.)
            packet_size: Tamanho do pacote
            packet_data: Dados do pacote
        """
        op_id = self._get_operation_id()
        logger.info(
            f"[{op_id}] PACKET_SEND | "
            f"Remote: {remote_address} | "
            f"Type: {packet_type} | "
            f"Size: {packet_size} | "
            f"Data: {self._format_bytes(packet_data, max_length=32)}"
        )

    def log_packet_receive(
        self,
        remote_address: str,
        packet_type: str,
        packet_size: int,
        packet_data: bytes
    ):
        """
        Regista recepção de pacote da rede IoT.

        Args:
            remote_address: Endereço do dispositivo remoto
            packet_type: Tipo de pacote (DATA, HEARTBEAT, etc.)
            packet_size: Tamanho do pacote
            packet_data: Dados do pacote
        """
        op_id = self._get_operation_id()
        logger.info(
            f"[{op_id}] PACKET_RECEIVE | "
            f"Remote: {remote_address} | "
            f"Type: {packet_type} | "
            f"Size: {packet_size} | "
            f"Data: {self._format_bytes(packet_data, max_length=32)}"
        )

    def log_custom(self, event: str, **kwargs):
        """
        Regista evento customizado.

        Args:
            event: Nome do evento
            **kwargs: Dados adicionais
        """
        op_id = self._get_operation_id()

        data_str = " | ".join(f"{k}: {v}" for k, v in kwargs.items())

        logger.info(
            f"[{op_id}] {event.upper()} | {data_str}"
        )


# ============================================================================
# Singleton global para facilitar uso
# ============================================================================

_global_ble_logger: Optional[BLEOperationLogger] = None


def get_ble_logger(device_address: Optional[str] = None) -> BLEOperationLogger:
    """
    Obtém ou cria o BLE Operation Logger global.

    Args:
        device_address: Endereço BLE do dispositivo local

    Returns:
        Instância do BLEOperationLogger
    """
    global _global_ble_logger

    if _global_ble_logger is None:
        _global_ble_logger = BLEOperationLogger(device_address)

    return _global_ble_logger


# ============================================================================
# Exemplo de Uso
# ============================================================================

if __name__ == '__main__':
    ble_log = BLEOperationLogger("E0:D3:62:D6:EE:A0")

    # Exemplos de logging
    ble_log.log_scan_start(5000, filter_iot=True)
    ble_log.log_connection_attempt("AA:BB:CC:DD:EE:FF")
    ble_log.log_connection_success("AA:BB:CC:DD:EE:FF", 124.5)
    ble_log.log_read_request("AA:BB:CC:DD:EE:FF", "12340000-...", "12340002-...")
    ble_log.log_read_response(
        "AA:BB:CC:DD:EE:FF",
        "12340000-...",
        "12340002-...",
        b"\x01\x02\x03\x04",
        success=True
    )

    print(f"Logs guardados em: {ble_log.log_file}")
