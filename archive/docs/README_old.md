# IoT Bluetooth Network

**Bluetooth-based, secure ad-hoc network for IoT devices**

Projeto académico para a disciplina de Segurança Informática e nas Comunicações (SIC).

---

##  Descrição

Este projeto implementa uma rede ad-hoc privada de dispositivos IoT que comunicam exclusivamente via **Bluetooth Low Energy (BLE)**. A rede utiliza uma topologia em árvore, com um dispositivo **Sink** (gateway) e múltiplos **nós IoT** que funcionam simultaneamente como sensores e routers.

### Características Principais

-  **Topologia em árvore** (tree-based, não mesh)
-  **Routing multi-hop** com forwarding tables (tipo switch learning)
-  **Endereçamento baseado em NID** (Network Identifier de 128 bits)
-  **Heartbeat protocol** para deteção de falhas de link
-  **Segurança robusta**:
  - Certificados X.509 com curva elíptica P-521
  - Autenticação mútua entre dispositivos
  - Session keys por link (ECDH)
  - MACs para integridade e prevenção de replay
  - DTLS para comunicação end-to-end (IoT ↔ Sink)
-  **Serviço Inbox** para envio de mensagens ao Sink

---

## ️ Arquitetura

### Topologia de Rede

```
                    ┌──────────────┐
                    │  Sink Device │
                    │  (hops = -1) │
                    └───────┬──────┘
                            │
           ┌────────────────┼────────────────┐
           │                │                │
      ┌────▼────┐      ┌────▼────┐     ┌────▼────┐
      │ IoT (A) │      │ IoT (B) │     │ IoT (C) │
      │ hops=0  │      │ hops=0  │     │ hops=0  │
      └─────────┘      └────┬────┘     └─────────┘
                            │
                   ┌────────┴────────┐
                   │                 │
              ┌────▼────┐       ┌────▼────┐
              │ IoT (D) │       │ IoT (E) │
              │ hops=1  │       │ hops=1  │
              └─────────┘       └─────────┘
```

- **Uplink**: Ligação em direção ao Sink (1 por dispositivo)
- **Downlink**: Ligações de dispositivos "filhos" (0 ou mais por dispositivo)
- **Forwarding tables**: Cada nó aprende rotas dinamicamente (como switches)

### Estrutura do Projeto

```
iot-bluetooth-network/
├── sink/                   # Código exclusivo do Sink
│   ├── sink_device.py
│   ├── heartbeat_service.py
│   ├── inbox_service.py
│   └── sink_ui.py
│
├── node/                   # Código exclusivo dos IoT Nodes
│   ├── iot_node.py
│   ├── node_ui.py
│   └── sensors/
│       ├── base_sensor.py
│       ├── temperature.py
│       └── humidity.py
│
├── common/                 # Código partilhado
│   ├── ble/               # Camada BLE (GATT Server/Client)
│   ├── network/           # Camada de rede (packets, routing)
│   ├── security/          # Segurança (X.509, ECDH, MACs, DTLS)
│   ├── protocol/          # Protocolos (heartbeat, inbox)
│   └── utils/             # Utilidades (config, logging, NIDs)
│
├── support/                # Ferramentas de suporte
│   ├── ca.py              # Certification Authority
│   ├── provision_device.py
│   └── cert_generator.py
│
├── tests/                  # Testes unitários
├── docs/                   # Documentação do projeto
└── examples/               # Exemplos (chat server/client)
```

---

##  Instalação

### Requisitos do Sistema (Ubuntu)

```bash
# BlueZ stack
sudo apt-get update
sudo apt-get install -y bluez bluez-tools libbluetooth-dev

# D-Bus e GLib (para GATT Server)
sudo apt-get install -y python3-dbus python3-gi libglib2.0-dev

# Python development
sudo apt-get install -y python3-dev python3-pip

# SimpleBLE dependencies (se necessário compilar)
sudo apt-get install -y cmake build-essential libdbus-1-dev

# OpenSSL (para DTLS)
sudo apt-get install -y libssl-dev

# Ferramentas de debug BLE
sudo apt-get install -y bluetooth hcitool bluetoothctl
```

### Instalação Python

```bash
# Criar virtual environment (recomendado)
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt
```

### Configuração

```bash
# Copiar ficheiro de configuração
cp .env.example .env

# Editar configuração conforme necessário
nano .env
```

---

##  Tecnologias Utilizadas

### BLE (Bluetooth Low Energy)

- **SimpleBLE**: Cliente BLE (scanning, connecting, read/write characteristics)
- **BlueZ + D-Bus**: Servidor GATT (advertising, services, characteristics)
- **PyGObject**: GLib mainloop para eventos D-Bus

### Segurança

- **cryptography**: Biblioteca Python para:
  - Certificados X.509
  - Curva elíptica P-521 (ECDSA, ECDH)
  - HMAC para MACs
  - DTLS (end-to-end)
- **PyDTLS**: DTLS sobre sockets customizados

### Networking

- **Formato de pacotes customizado** (struct)
- **Forwarding tables** (dict-based learning)
- **UUID** para NIDs (128 bits)

---

##  Segurança

### Camadas de Segurança

1. **Bluetooth Link Layer**
   - Pairing mode: Just Works
   - Confidencialidade e integridade na camada BLE

2. **Autenticação de Dispositivos**
   - Certificados X.509 emitidos por CA comum
   - Curva elíptica P-521 (SECP521R1)
   - Mutual authentication após conexão BLE

3. **Session Keys por Link**
   - ECDH key agreement
   - Nova session key por autenticação
   - Usado para MACs de mensagens

4. **Integridade e Freshness**
   - HMAC em todas as mensagens
   - Sequence numbers para prevenir replay
   - Validação em cada hop

5. **End-to-End (IoT ↔ Sink)**
   - DTLS para proteção end-to-end
   - Router daemon: adiciona/remove MACs per-link
   - DTLS apenas nos endpoints

### Certificados

- **CA**: Certification Authority emite todos os certificados
- **IoT Nodes**: Certificado liga NID ↔ Public Key
- **Sink**: Certificado especial (campo Subject identifica-o)

---

##  Funcionalidades

### Sink

- [ ] Heartbeat broadcasting (5s intervals, assinado digitalmente)
- [ ] Serviço Inbox (recebe mensagens dos IoT nodes)
- [ ] DTLS endpoint
- [ ] Forwarding tables para routing
- [ ] UI: mostrar mensagens recebidas + estatísticas

### IoT Nodes

- [ ] Sensores simulados (temperatura, humidade, etc.)
- [ ] Router daemon (forwarding multi-hop)
- [ ] DTLS endpoint
- [ ] Gestão de uplink/downlinks
- [ ] Deteção de falha de link (3 heartbeats perdidos)
- [ ] Reconexão automática
- [ ] UI: mostrar NID, uplink, downlinks, forwarding table, estatísticas

### Network Controls (Debug)

- [ ] Scan de dispositivos nearby + mostrar hop count
- [ ] Conectar manualmente a um dispositivo
- [ ] Simular link quebrado (parar heartbeat)

---

##  Formato de Pacotes

```
┌────────────┬────────────┬──────────┬─────┬──────────┬─────────┬─────────┐
│ Source NID │ Dest NID   │   Type   │ TTL │ Sequence │   MAC   │ Payload │
│  16 bytes  │  16 bytes  │  1 byte  │ 1 B │ 4 bytes  │ 32 bytes│ N bytes │
└────────────┴────────────┴──────────┴─────┴──────────┴─────────┴─────────┘

Tipos de Mensagem:
- 0x01: DATA          (dados de sensores)
- 0x02: HEARTBEAT     (heartbeat do Sink)
- 0x03: CONTROL       (comandos de controlo)
- 0x04: AUTH_REQUEST  (autenticação)
- 0x05: AUTH_RESPONSE (resposta autenticação)
```

---

##  Testes

```bash
# Executar todos os testes
pytest

# Testes específicos
pytest tests/test_packet.py
pytest tests/test_security.py

# Com verbose
pytest -v

# Com coverage
pytest --cov=common --cov=sink --cov=node
```

---

##  Execução

### 1. Provisioning (criar certificados)

```bash
# Criar CA
python -m support.ca --init

# Criar certificado para Sink
python -m support.provision_device --type sink --nid <SINK_NID>

# Criar certificados para IoT Nodes
python -m support.provision_device --type node --nid <NODE_NID>
```

### 2. Executar Sink

```bash
python -m sink.sink_device --cert ./certs/sink_cert.pem --key ./keys/sink_key.pem
```

### 3. Executar IoT Nodes

```bash
python -m node.iot_node --cert ./certs/node1_cert.pem --key ./keys/node1_key.pem
```

---

##  Estratégia de Implementação

Implementação faseada conforme recomendado no enunciado:

###  Fase 1: BLE Básico (CONCLUÍDA)
-  Criar/destruir conexões Bluetooth
-  GATT Server (D-Bus + BlueZ)
-  BLE Client (SimpleBLE + Bleak híbrido)
  - SimpleBLE: scan e notificações
  - Bleak: write operations (fallback automático)
-  Advertising com manufacturer data
-  Service discovery e characteristic enumeration

###  Fase 2: Network Layer (CONCLUÍDA)
-  Formato de pacotes (Packet class)
-  Serialização/desserialização binária
-  PacketManager (send/receive/validation)
-  LinkManager (uplink/downlink management)
-  Neighbor Discovery protocol
-  Forwarding tables (learning switch style)
-  Scan de dispositivos IoT
-  Network controls (CLI)

###  Fase 3: Heartbeat Protocol (CONCLUÍDA)
-  Broadcast de heartbeats (5s intervals)
-  HeartbeatPayload structure
-  HeartbeatMonitor (timeout detection)
-  Notification-based delivery
-  Assinatura digital (placeholder - falta ECDSA real)

###  Fase 4: Segurança - Certificados (EM PROGRESSO)
-  CA para emitir certificados X.509
-  Provisioning de dispositivos
-  Autenticação mútua
-  Negociação de session keys (ECDH)
-  HMAC-SHA256 para packet integrity
-  DTLS end-to-end (não implementado)

###  Fase 5: Serviço Inbox (PENDENTE)
-  Implementar Inbox no Sink
-  Cliente Inbox nos nodes

###  Fase 6: Sink & Node Implementation (PENDENTE)
-  Sink device completo
-  IoT Node completo com sensores
-  Router daemon
-  UIs (sink_ui.py, node_ui.py)

---

##  Autores

- **[Adicionar nome e número dos membros do grupo]**

### Contribuições

- Membro 1: [percentagem]% - [descrição das tarefas]
- Membro 2: [percentagem]% - [descrição das tarefas]
- Membro 3: [percentagem]% - [descrição das tarefas]
- Membro 4: [percentagem]% - [descrição das tarefas]

---

##  Licença

Projeto académico para a disciplina de SIC.

---

##  Issues Conhecidos & Soluções

### SimpleBLE Write Limitation no Linux
**Problema**: SimpleBLE não consegue escrever em características GATT no Linux devido a limitações da biblioteca.

**Solução Implementada**: Sistema híbrido SimpleBLE + Bleak
- SimpleBLE: Usado para scan e notificações (funciona perfeitamente)
- Bleak: Usado automaticamente como fallback para operações de write
- A transição é transparente - `BLEConnection.write_characteristic()` tenta SimpleBLE primeiro e usa Bleak se falhar

**Configuração necessária no servidor**:
```bash
# Configurar adaptador BLE em modo LE-only (evita erro br-connection-unknown)
./examples/configure_ble_only.sh hci0
```

### Advertising Intermitente
**Problema**: Dispositivo aparece/desaparece no scan BLE de forma intermitente.

**Causas**:
- Advertising intervals (100ms-1000ms)
- RSSI fraco (-60 a -70 dBm)
- Interferência WiFi (ambos usam 2.4 GHz)
- Scan window vs scan interval do BlueZ

**Mitigação**:
- Aumentar scan timeout (5s→10s)
- Aproximar dispositivos fisicamente
- Reduzir interferência WiFi

---

##  Exemplos e Testes

### Testar GATT Server
```bash
# PC Servidor
sudo python3 examples/test_gatt_server.py hci0
```

### Testar Packet Send (BLE Write)
```bash
# PC Cliente (requer GATT server a correr)
python3 examples/test_packet_send_bleak.py
```

### Testar Heartbeat Notifications
```bash
# PC Cliente (requer GATT server a correr)
python3 examples/test_heartbeat_notifications.py
```

### Network CLI
```bash
# Scan de dispositivos e gestão de links
python3 examples/network_cli.py
```

---

##  Referências

- [BlueZ - Official Bluetooth Stack for Linux](http://www.bluez.org/)
- [SimpleBLE Documentation](https://github.com/OpenBluetoothToolbox/SimpleBLE)
- [PyDTLS](https://github.com/rbit-sr/Protego)
- [Cryptography.io](https://cryptography.io/)
- [GATT Specification](https://www.bluetooth.com/specifications/specs/gatt/)
