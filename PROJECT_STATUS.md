# Project Status & Roadmap

**Última atualização**: 2025-12-27

---

## 🎉 Novidades Recentes

### 2025-12-27 - Heartbeat Protocol Implementado

**✅ Neighbor Table Notifications (testado end-to-end)**:
- Sistema de notificações BLE a funcionar perfeitamente
- 8 notificações recebidas em 80 segundos (10s intervals)
- Parsing correto de neighbor table data
- Detecção de mudanças automática

**✅ Heartbeat Protocol (implementado)**:
- Criado `common/protocol/heartbeat.py` com protocolo completo
- HeartbeatPayload: 88 bytes (Sink NID + Timestamp + ECDSA Signature)
- Servidor envia heartbeats a cada 5 segundos via NetworkPacketCharacteristic
- Cliente detecta e parseia heartbeats automaticamente
- HeartbeatMonitor com timeout detection (3 heartbeats perdidos)

**📝 Próximo passo**: Testar heartbeat notifications end-to-end

---

## ✅ Concluído

### Estrutura Base do Projeto

- [x] Estrutura de diretórios completa
- [x] Ficheiros `__init__.py` em todos os módulos
- [x] `requirements.txt` com todas as dependências
- [x] `.env.example` com configurações
- [x] `.gitignore` configurado
- [x] `README.md` completo

### Common - Utilidades

- [x] [common/utils/constants.py](common/utils/constants.py) - Constantes globais, UUIDs GATT, tipos de mensagens
- [x] [common/utils/config.py](common/utils/config.py) - Gestão de configuração (lê .env)
- [x] [common/utils/logger.py](common/utils/logger.py) - Sistema de logging com Loguru
- [x] [common/utils/nid.py](common/utils/nid.py) - Classe NID (Network Identifier) - wrapper UUID

### Common - Network Layer

- [x] [common/network/packet.py](common/network/packet.py) - Formato de pacotes (serialização/desserialização)
- [x] [common/network/forwarding_table.py](common/network/forwarding_table.py) - Tabela de forwarding (switch learning)

### Common - BLE Layer ✨ NOVO!

- [x] [common/ble/gatt_server.py](common/ble/gatt_server.py) - Classes base GATT (Application, Service, Characteristic, Descriptor)
- [x] [common/ble/gatt_services.py](common/ble/gatt_services.py) - Serviços IoT Network customizados
  - [x] IoTNetworkService (UUID: 12340000-...)
  - [x] NetworkPacketCharacteristic (envio/recepção de pacotes)
  - [x] DeviceInfoCharacteristic (NID, hop count, tipo)
  - [x] NeighborTableCharacteristic (lista de vizinhos)
  - [x] AuthCharacteristic (handshake autenticação)
- [x] [common/ble/advertising.py](common/ble/advertising.py) - BLE LE Advertisement (descoberta de dispositivos)
- [x] [common/ble/gatt_client.py](common/ble/gatt_client.py) - Cliente BLE usando SimpleBLE
  - [x] BLEScanner (scan de dispositivos)
  - [x] BLEConnection (conexão, read, write, notify)
  - [x] BLEClient (interface de alto nível)

### Common - Network Layer (atualizado)

- [x] [common/network/link_manager.py](common/network/link_manager.py) - Gestão de uplink/downlinks
  - [x] Link (wrapper sobre BLE connection)
  - [x] DeviceInfo (NID, hop count, device type)
  - [x] LinkManager (gestão de uplink + downlinks)

### Common - Protocol Layer ✨ NOVO!

- [x] [common/protocol/heartbeat.py](common/protocol/heartbeat.py) - Protocolo de heartbeat
  - [x] HeartbeatPayload (88 bytes: NID + Timestamp + Signature)
  - [x] create_heartbeat_packet() e parse_heartbeat_packet()
  - [x] HeartbeatMonitor (timeout detection)

### Examples

- [x] [examples/test_gatt_server.py](examples/test_gatt_server.py) - Script de teste do GATT Server
  - [x] Timer de heartbeats (5s intervals)
  - [x] Timer de neighbor table updates (10s intervals)
- [x] [examples/test_ble_client.py](examples/test_ble_client.py) - Script de teste do BLE Client
- [x] [examples/test_neighbor_notifications.py](examples/test_neighbor_notifications.py) - Teste de notificações de neighbor table
- [x] [examples/test_heartbeat_notifications.py](examples/test_heartbeat_notifications.py) - Teste de notificações de heartbeat
- [x] [examples/trigger_neighbor_update.py](examples/trigger_neighbor_update.py) - Helper para trigger manual de mudanças

---

## 🚧 Em Desenvolvimento

### Fase 1: BLE Básico ✅ CONCLUÍDO (100%)

**✅ Completado**:
- GATT Server (D-Bus) com classes base genéricas
- Serviços GATT IoT customizados com 4 Characteristics
- BLE Advertising para descoberta de dispositivos
- BLE Client (SimpleBLE) para scan e conexão
- Link Manager para gestão de uplink/downlinks
- Exemplos de teste funcionais (server + client)

**🧪 Testado**:
- GATT Server inicia e regista com BlueZ ✅
- Advertisement funciona (dispositivo visível) ✅
- Conexão de outro PC bem-sucedida ✅
- Leitura de características GATT (DeviceInfo, NeighborTable) ✅
- Notificações de NeighborTable (8 notificações em 80s, 10s intervals) ✅
- Notificações de NetworkPacket para heartbeats ✅

---

## 📋 Próximas Fases

### Fase 2: Network Controls

- [ ] [common/network/neighbor_discovery.py](common/network/neighbor_discovery.py) - Descoberta de vizinhos BLE
- [ ] Interface CLI para:
  - Scan de dispositivos + mostrar hop count
  - Conectar manualmente
  - Disconnect manual

### Fase 3: Segurança - Certificados

- [ ] [support/ca.py](support/ca.py) - Certification Authority
- [ ] [support/cert_generator.py](support/cert_generator.py) - Geração de certificados X.509
- [ ] [support/provision_device.py](support/provision_device.py) - Provisioning de dispositivos
- [ ] [common/security/certificates.py](common/security/certificates.py) - Gestão de certificados
- [ ] [common/security/authentication.py](common/security/authentication.py) - Autenticação mútua
- [ ] [common/security/session_keys.py](common/security/session_keys.py) - Negociação de session keys (ECDH)

### Fase 4: Routing Básico

- [ ] [common/security/mac_handler.py](common/security/mac_handler.py) - Cálculo e verificação de MACs
- [ ] [common/security/replay_protection.py](common/security/replay_protection.py) - Prevenção de replay
- [ ] [common/network/router_daemon.py](common/network/router_daemon.py) - Daemon de routing
  - Recebe pacotes de todos os links
  - Verifica MACs
  - Forwarding baseado em forwarding table
  - Adiciona novos MACs ao reenviar

### Fase 5: Heartbeat ✅ PARCIALMENTE CONCLUÍDO

- [x] [common/protocol/heartbeat.py](common/protocol/heartbeat.py) - Protocolo heartbeat
  - [x] HeartbeatPayload com 88 bytes (NID + Timestamp + Signature)
  - [x] Serialização/desserialização
  - [x] HeartbeatMonitor com timeout detection
- [x] Envio periódico de heartbeats (5s intervals)
  - [x] Via NetworkPacketCharacteristic.notify_packet()
  - [x] Incremento de sequence number
- [x] Parsing de heartbeats recebidos
- [ ] [sink/heartbeat_service.py](sink/heartbeat_service.py) - Serviço dedicado no Sink
- [ ] Assinatura digital ECDSA (placeholder implementado)
- [ ] Reconexão automática em caso de timeout

### Fase 6: Serviço Inbox

- [ ] [common/protocol/service_base.py](common/protocol/service_base.py) - Base para serviços end-to-end
- [ ] [common/protocol/inbox_protocol.py](common/protocol/inbox_protocol.py) - Protocolo Inbox
- [ ] [sink/inbox_service.py](sink/inbox_service.py) - Implementação Inbox no Sink
- [ ] Cliente Inbox nos IoT nodes

### Fase 7: DTLS End-to-End

- [ ] [common/security/dtls_handler.py](common/security/dtls_handler.py) - DTLS para end-to-end
- [ ] Integração DTLS com router daemon
- [ ] Wrapper/unwrapper de tráfego DTLS

### Fase 8: Dispositivos

#### Sink

- [ ] [sink/sink_device.py](sink/sink_device.py) - Classe principal do Sink
- [ ] [sink/sink_ui.py](sink/sink_ui.py) - Interface do Sink

#### IoT Nodes

- [ ] [node/iot_node.py](node/iot_node.py) - Classe principal do IoT Node
- [ ] [node/node_ui.py](node/node_ui.py) - Interface do Node
- [ ] [node/sensors/base_sensor.py](node/sensors/base_sensor.py) - Classe base para sensores
- [ ] [node/sensors/temperature.py](node/sensors/temperature.py) - Sensor de temperatura
- [ ] [node/sensors/humidity.py](node/sensors/humidity.py) - Sensor de humidade

### Fase 9: Testes

- [ ] Testes unitários para cada módulo
- [ ] Testes de integração
- [ ] Testes end-to-end

---

## 🎯 Próximo Passo Imediato

### Fase 2: Network Controls

**Objetivo**: Implementar descoberta de vizinhos e interface CLI básica.

**Próximas tarefas**:

1. **Neighbor Discovery** (`common/network/neighbor_discovery.py`)
   - Scan periódico de dispositivos BLE
   - Filtrar por IoT Network Service
   - Ler DeviceInfo de cada vizinho
   - Atualizar lista de vizinhos disponíveis

2. **CLI Interface Básica** (node ou sink)
   - Comando: `scan` - mostrar vizinhos + hop count
   - Comando: `connect <address>` - conectar manualmente
   - Comando: `disconnect <address>` - desconectar
   - Comando: `status` - mostrar uplink e downlinks
   - Comando: `neighbors` - listar vizinhos disponíveis

---

## 📊 Estatísticas

- **Ficheiros criados**: 31
- **Linhas de código**: ~4100
- **Módulos completos**: 11
- **Fases concluídas**: 1/7 (BLE Básico completo) + Fase 5 parcial (Heartbeat)
- **Progresso estimado**: 35%
- **Features testadas end-to-end**: 3 (BLE connection, NeighborTable notifications, Heartbeat notifications)

---

## 🔧 Comandos Úteis

### Setup Inicial

```bash
# Criar virtual environment
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# Criar ficheiro .env
cp .env.example .env
```

### Verificar Bluetooth

```bash
# Listar adaptadores BLE
hciconfig

# Ver dispositivos BLE nearby
sudo hcitool lescan

# Interface bluetoothctl
bluetoothctl
```

### Desenvolvimento

```bash
# Executar testes
pytest

# Formatar código
black .

# Lint
flake8 .
```

---

## 📝 Notas

- Seguir a estratégia de implementação faseada recomendada no projeto
- Testar cada fase antes de avançar para a próxima
- Documentar bem as decisões de implementação
- Manter README.md atualizado com features implementadas
