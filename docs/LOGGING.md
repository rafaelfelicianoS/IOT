# Sistema de Logging BLE

Este documento explica o sistema de logging detalhado para operações BLE.

---

## Visão Geral

O projeto tem dois sistemas de logging complementares:

1. **Logger Geral** (`common/utils/logger.py`): Logs de aplicação (INFO, DEBUG, WARNING, ERROR)
2. **BLE Operation Logger** (`common/utils/ble_logger.py`): Logs detalhados de todas as operações BLE

---

## BLE Operation Logger

### Localização dos Logs

Os logs BLE são guardados em:
```
logs/ble_operations_<DEVICE_ADDRESS>_<SESSION_ID>.log
```

Exemplo:
```
logs/ble_operations_E0D362D6EEA0_20251227_183045.log
```

### Formato dos Logs

Cada linha de log tem o formato:
```
<TIMESTAMP> | <LEVEL> | [<OPERATION_ID>] <EVENT> | <DETAILS>
```

Exemplo:
```
2025-12-27 18:30:45.123 | INFO | [OP-20251227_183045-0001] SCAN_START | Duration: 5000ms | Filter_IoT: True
2025-12-27 18:30:50.456 | INFO | [OP-20251227_183045-0002] SCAN_RESULT | Devices_Found: 3
2025-12-27 18:30:50.457 | DEBUG | [OP-20251227_183045-0002]   Device_1: Name: IoT-Node | Address: AA:BB:CC:DD:EE:FF | RSSI: -45 dBm
```

---

## Tipos de Eventos Registados

### 1. Scan Operations

**SCAN_START**
```
[OP-XXXX] SCAN_START | Duration: 5000ms | Filter_IoT: True
```

**SCAN_RESULT**
```
[OP-XXXX] SCAN_RESULT | Devices_Found: 3
[OP-XXXX]   Device_1: Name: IoT-Node | Address: AA:BB:CC:DD:EE:FF | RSSI: -45 dBm | Services: 1
```

### 2. Connection Operations

**CONNECT_ATTEMPT**
```
[OP-XXXX] CONNECT_ATTEMPT | Local: E0:D3:62:D6:EE:A0 | Remote: AA:BB:CC:DD:EE:FF
```

**CONNECT_SUCCESS**
```
[OP-XXXX] CONNECT_SUCCESS | Remote: AA:BB:CC:DD:EE:FF | Time: 124.50ms
```

**CONNECT_FAILED**
```
[OP-XXXX] CONNECT_FAILED | Remote: AA:BB:CC:DD:EE:FF | Error: Connection timeout
```

**DISCONNECT**
```
[OP-XXXX] DISCONNECT | Remote: AA:BB:CC:DD:EE:FF | Reason: normal
```

### 3. Read Operations

**READ_REQUEST**
```
[OP-XXXX] READ_REQUEST | Remote: AA:BB:CC:DD:EE:FF | Service: 12340000-... | Char: 12340002-...
```

**READ_RESPONSE**
```
[OP-XXXX] READ_RESPONSE | Remote: AA:BB:CC:DD:EE:FF | Char: 12340002-... | Data: 18 bytes | Hex: 010203... | ASCII: ...
```

**READ_FAILED**
```
[OP-XXXX] READ_FAILED | Remote: AA:BB:CC:DD:EE:FF | Char: 12340002-...
```

### 4. Write Operations

**WRITE_REQUEST** (ou WRITE_COMMAND)
```
[OP-XXXX] WRITE_REQUEST | Remote: AA:BB:CC:DD:EE:FF | Char: 12340001-... | Data: 32 bytes | Hex: ...
```

**WRITE_SUCCESS**
```
[OP-XXXX] WRITE_SUCCESS | Remote: AA:BB:CC:DD:EE:FF | Char: 12340001-...
```

**WRITE_FAILED**
```
[OP-XXXX] WRITE_FAILED | Remote: AA:BB:CC:DD:EE:FF | Char: 12340001-... | Error: Not writable
```

### 5. Notification Operations

**SUBSCRIBE_SUCCESS**
```
[OP-XXXX] SUBSCRIBE_SUCCESS | Remote: AA:BB:CC:DD:EE:FF | Char: 12340001-...
```

**NOTIFICATION** (recebida)
```
[OP-XXXX] NOTIFICATION | Remote: AA:BB:CC:DD:EE:FF | Char: 12340001-... | Data: 10 bytes | Hex: ...
```

### 6. Packet Operations (IoT Network)

**PACKET_SEND**
```
[OP-XXXX] PACKET_SEND | Remote: AA:BB:CC:DD:EE:FF | Type: DATA | Size: 64 | Data: ...
```

**PACKET_RECEIVE**
```
[OP-XXXX] PACKET_RECEIVE | Remote: AA:BB:CC:DD:EE:FF | Type: HEARTBEAT | Size: 32 | Data: ...
```

---

## Como Usar

### No Código

```python
from common.utils.ble_logger import get_ble_logger

# Obter logger (singleton global)
ble_log = get_ble_logger("E0:D3:62:D6:EE:A0")

# Exemplos de uso
ble_log.log_scan_start(5000, filter_iot=True)
ble_log.log_connection_attempt("AA:BB:CC:DD:EE:FF")
ble_log.log_connection_success("AA:BB:CC:DD:EE:FF", 124.5)
ble_log.log_read_request("AA:BB:CC:DD:EE:FF", service_uuid, char_uuid)
ble_log.log_read_response("AA:BB:CC:DD:EE:FF", service_uuid, char_uuid, data, success=True)
```

### Visualizar Logs

```bash
# Ver log em tempo real
tail -f logs/ble_operations_*.log

# Filtrar por tipo de evento
grep "CONNECT" logs/ble_operations_*.log

# Filtrar por dispositivo remoto
grep "AA:BB:CC:DD:EE:FF" logs/ble_operations_*.log

# Ver apenas erros
grep "FAILED\|ERROR" logs/ble_operations_*.log
```

---

## Debugging com Logs

### Problema: Dispositivo não aparece no scan

1. Verificar se scan foi iniciado:
```bash
grep "SCAN_START" logs/ble_operations_*.log
```

2. Ver quantos dispositivos foram encontrados:
```bash
grep "SCAN_RESULT" logs/ble_operations_*.log
```

3. Ver lista completa de dispositivos:
```bash
grep "Device_" logs/ble_operations_*.log
```

### Problema: Falha ao conectar

1. Ver tentativas de conexão:
```bash
grep "CONNECT_ATTEMPT" logs/ble_operations_*.log
```

2. Ver falhas:
```bash
grep "CONNECT_FAILED" logs/ble_operations_*.log
```

3. Ver tempo de conexões bem-sucedidas:
```bash
grep "CONNECT_SUCCESS" logs/ble_operations_*.log
```

### Problema: Erro ao ler característica

1. Ver pedidos de leitura:
```bash
grep "READ_REQUEST" logs/ble_operations_*.log
```

2. Ver respostas:
```bash
grep "READ_RESPONSE\|READ_FAILED" logs/ble_operations_*.log
```

3. Ver dados lidos:
```bash
grep "READ_RESPONSE" logs/ble_operations_*.log | grep "Data:"
```

---

## Configuração

### Rotação de Logs

Os logs BLE têm:
- **Rotação**: 10 MB
- **Retenção**: 30 dias
- **Thread-safe**: Sim (enqueue=True)

### Nível de Log

Por padrão, todos os eventos são registados (DEBUG level).

Para alterar, modificar em `common/utils/ble_logger.py`:
```python
logger.add(
    self.log_file,
    level="INFO",  # ou "DEBUG", "WARNING", "ERROR"
    ...
)
```

---

## Performance

O BLE Operation Logger está otimizado para:
- **Baixo overhead**: Logging assíncrono (enqueue=True)
- **Formato eficiente**: Dados truncados após 64 bytes por defeito
- **Sem bloqueio**: Não afeta performance das operações BLE

---

## Notas Importantes

1. **Logs contêm dados sensíveis**: NIDs, endereços BLE, dados de pacotes
2. **Não fazer commit dos logs**: Estão em .gitignore
3. **Limpar logs antigos**: Usar `find logs/ -name "*.log" -mtime +30 -delete`
4. **Permissões**: Logs criados pelo user que executa o processo

---

**Última atualização**: 2025-12-27
