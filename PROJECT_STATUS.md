# Project Status & Roadmap

**Última atualização**: 2025-12-29

**Baseado em**: [docs/project.txt](docs/project.txt) (especificação oficial do projeto)

---

## 🎉 Novidades Recentes

### 2025-12-29 - SimpleBLE + Bleak Hybrid Solution

**✅ BLE Write Operations Working (testado end-to-end)**:
- Solução híbrida SimpleBLE + Bleak implementada
- SimpleBLE: usado para scan e notificações ✅
- Bleak: usado para write operations ✅
- Fallback automático em `BLEConnection.write_characteristic()`
- Teste bem-sucedido: 126 bytes enviados via Bleak

**✅ Network Packet Transmission**:
- Pacotes podem ser enviados via BLE (client → server)
- Created [examples/test_packet_send_bleak.py](examples/test_packet_send_bleak.py)
- Scripts de configuração BLE criados (clear cache, LE-only mode)

### 2025-12-27 - Heartbeat Protocol Implementado

**✅ Heartbeat Protocol (implementado)**:
- Criado [common/protocol/heartbeat.py](common/protocol/heartbeat.py) com protocolo completo
- HeartbeatPayload: 88 bytes (Sink NID + Timestamp + ECDSA Signature)
- Servidor envia heartbeats a cada 5 segundos via NetworkPacketCharacteristic
- Cliente detecta e parseia heartbeats automaticamente
- HeartbeatMonitor com timeout detection (3 heartbeats perdidos)

**✅ Neighbor Table Notifications**:
- Sistema de notificações BLE a funcionar perfeitamente
- 8 notificações recebidas em 80 segundos (10s intervals)
- Parsing correto de neighbor table data
- Detecção de mudanças automática

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

## 📋 Roadmap (Baseado na Especificação Oficial)

**Fonte**: [docs/project.txt](docs/project.txt) - Secção 7 "Implementation strategy"

A especificação recomenda implementação faseada, camada por camada:

### ✅ Fase 1: Bluetooth Connections (CONCLUÍDA)

> "Develop the fundamental mechanisms to create and destroy Bluetooth connections between IoT devices"

- [x] GATT Server (D-Bus + BlueZ)
- [x] GATT Client (SimpleBLE + Bleak hybrid)
- [x] BLE Advertising
- [x] Service discovery
- [x] Connection management
- [x] **EXTRA**: Solução híbrida para contornar limitações do SimpleBLE

**Status**: ✅ Completo e testado end-to-end

---

### ⏳ Fase 2: Network Controls (EM PROGRESSO)

> "Develop the network controls"

Controlos de rede para debug e testes (secção 4 do projeto):

- [ ] **Scan nearby devices** - mostrar hop count até Sink
- [ ] **Manual connect** - conectar manualmente a um dispositivo
- [ ] **Stop heartbeat** - simular link quebrado

**Implementação necessária**:
- [ ] [common/network/neighbor_discovery.py](common/network/neighbor_discovery.py) - Scan e filtragem
- [ ] CLI interface (node/sink) com comandos `scan`, `connect`, `disconnect`

**Prioridade**: Média (útil para testes, mas não é core functionality)

---

### 🔐 Fase 3: Certificates & Session Keys (PRÓXIMA PRIORIDADE)

> "Develop the mechanisms to create public key certificates to IoT devices and to use them to negotiate session keys for Bluetooth links"

**⚠️ PESO NA AVALIAÇÃO: 50% da nota!**

Requisitos de segurança (secções 5.1 - 5.7):

**Certificados X.509**:
- [ ] [support/ca.py](support/ca.py) - Certification Authority (CA)
- [ ] [support/cert_generator.py](support/cert_generator.py) - Gerar certificados X.509
- [ ] [support/provision_device.py](support/provision_device.py) - Provisioning de dispositivos
- [ ] [common/security/certificates.py](common/security/certificates.py) - Gestão de certificados
  - Curva elíptica: **P-521 (SECP521R1)**
  - Bind NID ↔ Public Key
  - Sink: certificado especial (campo Subject identifica-o)

**Autenticação & Session Keys**:
- [ ] [common/security/authentication.py](common/security/authentication.py) - Mutual authentication
  - Protocolo de autenticação mútua após conexão BLE
  - Validar certificados emitidos por CA comum
- [ ] [common/security/session_keys.py](common/security/session_keys.py) - ECDH key agreement
  - Cada autenticação produz nova session key
  - Mesmo com misbehaving participant

**Prioridade**: 🔴 **ALTA** - Vale 50% da nota!

---

### 📦 Fase 4: Basic Message Routing (PRÓXIMA)

> "Develop a basic message routing mechanism for sending data from an IoT device to the Sink, using a header with NIDs for device addressing, and names/numbers to identify services/clients and a MAC to check the authenticity and freshness of messages received by the devices"

**Packet Format** (já implementado em [common/network/packet.py](common/network/packet.py)):
- ✅ Source NID (16 bytes)
- ✅ Dest NID (16 bytes)
- ✅ Type (1 byte)
- ✅ TTL (1 byte)
- ✅ Sequence (4 bytes)
- ✅ MAC (32 bytes) - **placeholder, falta implementar cálculo real**
- ✅ Payload (N bytes)

**Implementação necessária**:
- [ ] [common/security/mac_handler.py](common/security/mac_handler.py) - HMAC-SHA256
  - Cálculo de MAC usando session key
  - Verificação de MAC
- [ ] [common/security/replay_protection.py](common/security/replay_protection.py)
  - Detecção de sequence numbers duplicados
  - Window-based ou counter-based
- [ ] [common/network/router_daemon.py](common/network/router_daemon.py)
  - Recebe pacotes de todos os links (uplink + downlinks)
  - Verifica MAC de entrada
  - Forwarding baseado em forwarding table
  - Adiciona novo MAC ao reenviar

**Prioridade**: 🟠 Média-Alta

---

### 📡 Fase 5: Heartbeat Broadcast (PARCIALMENTE CONCLUÍDA)

> "Develop the downlink broadcast mechanism that will help to implement the heartbeat protocol"

**Já implementado**:
- [x] HeartbeatPayload structure (88 bytes)
- [x] Envio periódico (5s intervals)
- [x] Notificações via BLE
- [x] Parsing de heartbeats
- [x] HeartbeatMonitor (timeout detection)

**Falta implementar**:
- [ ] **Assinatura digital ECDSA real** (atualmente placeholder)
- [ ] **Verificação de assinatura** antes de usar/forward heartbeat
- [ ] **Multi-unicast flooding** (broadcast recursivo pelos downlinks)
- [ ] [sink/heartbeat_service.py](sink/heartbeat_service.py) - Serviço dedicado no Sink

**Prioridade**: 🟠 Média

---

### ⏱️ Fase 6: Heartbeat Timeout & Link Failure

> "Implement the timeout mechanism in the heartbeat to detect link failures"

Requisitos (secção 3.2):
- [ ] Deteção de 3 heartbeats perdidos consecutivos
- [ ] Disconnect de uplink ao detetar falha
- [ ] Disconnect de TODOS os downlinks (chain reaction)
- [ ] Procura de novo uplink
- [ ] Hop count negativo quando sem uplink

**Prioridade**: 🟢 Média-Baixa (depende de Fase 5 completa)

---

### 📨 Fase 7: Inbox Service

> "Implement the Inbox service, both in the Sink and in the IoT devices"

Requisitos (secção 5.7):
- [ ] [common/protocol/service_base.py](common/protocol/service_base.py) - Base para serviços
- [ ] [common/protocol/inbox_protocol.py](common/protocol/inbox_protocol.py)
  - Service name: "Inbox"
  - Random client port
- [ ] [sink/inbox_service.py](sink/inbox_service.py) - Servidor Inbox no Sink
- [ ] Cliente Inbox nos IoT nodes

**Prioridade**: 🟢 Baixa

---

### 🔒 Fase 8: DTLS End-to-End (OPCIONAL)

> "Add DTLS to the message routing service"

**⚠️ Nota**: Segundo o README, DTLS não foi implementado (Fase 4 marcada como "❌ DTLS end-to-end (não implementado)")

Requisitos (secção 5.7):
- [ ] [common/security/dtls_handler.py](common/security/dtls_handler.py)
- [ ] Integração com router daemon
- [ ] Secure channel agreement (IoT ↔ Sink)
- [ ] Wrapper/unwrapper de tráfego

**Prioridade**: 🔵 Muito Baixa / Opcional

---

## 🎯 Próximo Passo Imediato

### 🔐 Fase 3: Certificates & Session Keys

**Justificação**:
- **50% da nota** vem de security features
- É pré-requisito para Fase 4 (routing com MACs)
- Network controls (Fase 2) são úteis mas não bloqueantes

**Ordem de implementação sugerida**:

1. **CA & Certificate Generation** ([support/ca.py](support/ca.py), [support/cert_generator.py](support/cert_generator.py))
   - Criar CA root certificate
   - Implementar geração de certificados X.509 com P-521
   - Special handling para certificado do Sink

2. **Certificate Management** ([common/security/certificates.py](common/security/certificates.py))
   - Load/verify certificates
   - Extract NID from certificate
   - Validate certificate chain

3. **Mutual Authentication** ([common/security/authentication.py](common/security/authentication.py))
   - Challenge-response protocol
   - Certificate exchange & validation
   - Integration com AuthCharacteristic (já existe no GATT)

4. **ECDH Session Keys** ([common/security/session_keys.py](common/security/session_keys.py))
   - ECDH key agreement com P-521
   - Session key derivation (KDF)
   - Key storage per link

**Próxima ação**: Implementar CA e geração de certificados

---

## 📊 Estatísticas

- **Ficheiros criados**: ~35
- **Linhas de código**: ~4500
- **Fases concluídas**: 1/8 (BLE completo) + parcial Fase 2 (Network Controls) + parcial Fase 5 (Heartbeat)
- **Progresso estimado**: 25% (1 fase completa de 8)
- **Features testadas end-to-end**: 4 (BLE connection, BLE write, NeighborTable notifications, Heartbeat notifications)

**Breakdown por peso de avaliação**:
- **Network management (20%)**: ~60% completo (BLE + packet format + forwarding tables)
- **Security (50%)**: ~5% completo (apenas estrutura base, falta X.509, ECDH, MACs, DTLS)
- **Documentation (30%)**: ~40% completo (README, PROJECT_STATUS, project.txt)

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
