"""
Constantes globais do projeto IoT Bluetooth Network.

Define UUIDs, message types, configurações default, etc.
"""

# ============================================================================
# GATT Service UUIDs
# ============================================================================

# Base UUID (Bluetooth SIG base)
BASE_UUID = "00000000-0000-1000-8000-00805f9b34fb"

# IoT Network Service UUID (128-bit full form)
IOT_NETWORK_SERVICE_UUID = "12340000-0000-1000-8000-00805f9b34fb"

# Short forms (para advertising - BlueZ pode usar versões curtas)
IOT_NETWORK_SERVICE_UUID_SHORT_32 = "0000000012340000"  # 32-bit form
IOT_NETWORK_SERVICE_UUID_SHORT_16 = "1234"  # 16-bit form (se couber)

# Characteristics UUIDs
CHAR_NETWORK_PACKET_UUID = "12340001-0000-1000-8000-00805f9b34fb"
CHAR_DEVICE_INFO_UUID = "12340002-0000-1000-8000-00805f9b34fb"
CHAR_NEIGHBOR_TABLE_UUID = "12340003-0000-1000-8000-00805f9b34fb"
CHAR_AUTHENTICATION_UUID = "12340004-0000-1000-8000-00805f9b34fb"

# ============================================================================
# D-Bus Interfaces (BlueZ)
# ============================================================================

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHARACTERISTIC_IFACE = 'org.bluez.GattCharacteristic1'
GATT_DESCRIPTOR_IFACE = 'org.bluez.GattDescriptor1'

DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'

# ============================================================================
# Message Types
# ============================================================================

class MessageType:
    """Tipos de mensagens na rede IoT."""
    DATA = 0x01          # Dados de sensores para Sink
    HEARTBEAT = 0x02     # Heartbeat do Sink
    CONTROL = 0x03       # Comandos de controlo
    AUTH_REQUEST = 0x04  # Pedido de autenticação
    AUTH_RESPONSE = 0x05 # Resposta de autenticação
    ROUTE_LEARN = 0x06   # Mensagem para aprendizagem de rota

    @staticmethod
    def to_string(msg_type: int) -> str:
        """Converte tipo de mensagem para string."""
        mapping = {
            0x01: "DATA",
            0x02: "HEARTBEAT",
            0x03: "CONTROL",
            0x04: "AUTH_REQUEST",
            0x05: "AUTH_RESPONSE",
            0x06: "ROUTE_LEARN",
        }
        return mapping.get(msg_type, f"UNKNOWN(0x{msg_type:02x})")

# ============================================================================
# Packet Format Constants
# ============================================================================

# Tamanhos dos campos do pacote (em bytes)
NID_SIZE = 16           # Network Identifier (UUID = 128 bits = 16 bytes)
TYPE_SIZE = 1           # Message type
TTL_SIZE = 1            # Time-to-live
SEQUENCE_SIZE = 4       # Sequence number
MAC_SIZE = 32           # HMAC-SHA256

# Header total = Source NID + Dest NID + Type + TTL + Seq + MAC
PACKET_HEADER_SIZE = (NID_SIZE * 2) + TYPE_SIZE + TTL_SIZE + SEQUENCE_SIZE + MAC_SIZE

# Valores default
DEFAULT_TTL = 10
MAX_TTL = 255

# ============================================================================
# Network Configuration
# ============================================================================

# Heartbeat
HEARTBEAT_INTERVAL = 5      # segundos
HEARTBEAT_TIMEOUT_COUNT = 3 # número de heartbeats perdidos antes de timeout

# Hop count especial
HOP_COUNT_DISCONNECTED = -1  # Dispositivo sem uplink
HOP_COUNT_SINK = -1          # Sink não tem hop count positivo (é a raiz)

# ============================================================================
# Security Configuration
# ============================================================================

# Elliptic Curve
ELLIPTIC_CURVE_NAME = "secp521r1"  # P-521

# Certificate validity
CERT_VALIDITY_DAYS = 365

# Distinguished Name fields para certificados
DN_COUNTRY = "PT"
DN_STATE = "Aveiro"
DN_LOCALITY = "Aveiro"
DN_ORGANIZATION = "SIC IoT Network"
DN_ORGANIZATIONAL_UNIT = "IoT Devices"

# Subject field para identificar Sink
SINK_SUBJECT_FIELD = "Sink"

# ============================================================================
# Service Names (End-to-End)
# ============================================================================

SERVICE_INBOX = "inbox"  # Serviço Inbox no Sink

# ============================================================================
# BLE Configuration
# ============================================================================

# Advertising
ADVERTISING_TIMEOUT = 0  # 0 = indefinido

# Scan
SCAN_TIMEOUT_DEFAULT = 10  # segundos

# Connection
CONNECTION_TIMEOUT = 30  # segundos

# MTU
BLE_MTU_DEFAULT = 512  # Maximum Transmission Unit

# ============================================================================
# Paths
# ============================================================================

# Diretórios
DEFAULT_CERTS_DIR = "./certs"
DEFAULT_KEYS_DIR = "./keys"
DEFAULT_LOGS_DIR = "./logs"

# Ficheiros CA
CA_CERT_FILENAME = "ca_cert.pem"
CA_KEY_FILENAME = "ca_key.pem"

# ============================================================================
# Logging
# ============================================================================

# Níveis de log
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

# ============================================================================
# UI Configuration
# ============================================================================

UI_REFRESH_RATE = 1  # segundos

# ============================================================================
# Misc
# ============================================================================

# Encoding
DEFAULT_ENCODING = "utf-8"

# Timeout padrão
DEFAULT_TIMEOUT = 30  # segundos
