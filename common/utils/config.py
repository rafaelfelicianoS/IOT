"""
Gestão de configuração do projeto.

Lê variáveis de ambiente do ficheiro .env e fornece acesso centralizado
às configurações.
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from common.utils.constants import (
    HEARTBEAT_INTERVAL,
    HEARTBEAT_TIMEOUT_COUNT,
    DEFAULT_TTL,
    ELLIPTIC_CURVE_NAME,
    CERT_VALIDITY_DAYS,
    DEFAULT_CERTS_DIR,
    DEFAULT_KEYS_DIR,
    DEFAULT_LOGS_DIR,
    LOG_LEVEL_INFO,
    UI_REFRESH_RATE,
    SCAN_TIMEOUT_DEFAULT,
    CA_CERT_FILENAME,
    CA_KEY_FILENAME,
)


class Config:
    """
    Classe de configuração singleton.

    Carrega configurações do .env e fornece acesso através de propriedades.
    """

    _instance: Optional['Config'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # Carregar .env
        load_dotenv()

        # Bluetooth
        self.ble_interface: str = os.getenv("BLE_INTERFACE", "hci0")
        self.ble_scan_timeout: int = int(os.getenv("BLE_SCAN_TIMEOUT", SCAN_TIMEOUT_DEFAULT))

        # Network
        self.heartbeat_interval: int = int(os.getenv("HEARTBEAT_INTERVAL", HEARTBEAT_INTERVAL))
        self.heartbeat_timeout: int = int(os.getenv("HEARTBEAT_TIMEOUT", HEARTBEAT_TIMEOUT_COUNT))
        self.max_ttl: int = int(os.getenv("MAX_TTL", DEFAULT_TTL))

        # Security
        self.elliptic_curve: str = os.getenv("ELLIPTIC_CURVE", ELLIPTIC_CURVE_NAME)
        self.cert_validity_days: int = int(os.getenv("CERT_VALIDITY_DAYS", CERT_VALIDITY_DAYS))

        # Paths
        self.certs_dir: Path = Path(os.getenv("CERTS_DIR", DEFAULT_CERTS_DIR))
        self.keys_dir: Path = Path(os.getenv("KEYS_DIR", DEFAULT_KEYS_DIR))
        self.logs_dir: Path = Path(os.getenv("LOGS_DIR", DEFAULT_LOGS_DIR))

        # CA files
        ca_cert_file = os.getenv("CA_CERT_FILE")
        ca_key_file = os.getenv("CA_KEY_FILE")

        self.ca_cert_path: Path = Path(ca_cert_file) if ca_cert_file else self.certs_dir / CA_CERT_FILENAME
        self.ca_key_path: Path = Path(ca_key_file) if ca_key_file else self.keys_dir / CA_KEY_FILENAME

        # Logging
        self.log_level: str = os.getenv("LOG_LEVEL", LOG_LEVEL_INFO)

        # Device
        self.device_type: str = os.getenv("DEVICE_TYPE", "node")  # "sink" ou "node"
        self.device_nid: Optional[str] = os.getenv("DEVICE_NID")
        self.device_cert: Optional[Path] = Path(os.getenv("DEVICE_CERT")) if os.getenv("DEVICE_CERT") else None
        self.device_key: Optional[Path] = Path(os.getenv("DEVICE_KEY")) if os.getenv("DEVICE_KEY") else None

        # Sink
        self.sink_nid: Optional[str] = os.getenv("SINK_NID")

        # UI
        self.ui_refresh_rate: int = int(os.getenv("UI_REFRESH_RATE", UI_REFRESH_RATE))

        # Debug
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"
        self.disable_cert_verification: bool = os.getenv("DISABLE_CERT_VERIFICATION", "false").lower() == "true"

        self._initialized = True

    def ensure_directories_exist(self):
        """Cria os diretórios necessários se não existirem."""
        self.certs_dir.mkdir(parents=True, exist_ok=True)
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def is_sink(self) -> bool:
        """Verifica se este dispositivo é o Sink."""
        return self.device_type.lower() == "sink"

    def is_node(self) -> bool:
        """Verifica se este dispositivo é um nó IoT."""
        return self.device_type.lower() == "node"

    def __repr__(self) -> str:
        return (
            f"Config(\n"
            f"  device_type={self.device_type},\n"
            f"  ble_interface={self.ble_interface},\n"
            f"  heartbeat_interval={self.heartbeat_interval}s,\n"
            f"  log_level={self.log_level}\n"
            f")"
        )


# Instância global de configuração
config = Config()
