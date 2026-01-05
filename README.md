# IoT Bluetooth Network

Rede ad-hoc segura baseada em Bluetooth Low Energy.

Projeto académico para Segurança Informática e nas Comunicações (SIC).

---

## Sobre

Implementação de rede IoT privada com comunicação exclusiva via BLE, seguindo especificação em `docs/specs/project.txt`.

Topologia em árvore com Sink central e nós IoT como sensores/routers.

### Características

- Topologia em árvore com lazy uplink selection
- Heartbeat protocol (5s intervals) com assinaturas ECDSA
- Heartbeat forwarding para downlinks
- RouterDaemon com forwarding table (learning switch)
- Endereçamento NID (128 bits UUID)
- Certificados X.509 (P-521)
- Autenticação mútua challenge-response
- Session keys por link (ECDH)
- MACs (HMAC-SHA256) em todos os pacotes
- Replay protection (sequence numbers + window 100)
- Encriptação end-to-end (AES-256-GCM)
- Fragmentação automática de mensagens grandes (180 bytes por fragmento)
- Serviço Inbox no Sink
- Chain reaction disconnect
- Deteção de timeout (3 heartbeats perdidos = 15s)

---

## Instalação

### Requisitos
- Linux com Bluetooth LE
- Python 3.8+
- BlueZ

### Setup em PC Novo

**1. Instalar dependências**
```bash
sudo ./install_deps.sh
```

**2. Configurar adaptador Bluetooth (importante!)**
```bash
# Configurar adaptador em modo LE-only e limpar cache
sudo ./setup_bluetooth.sh hci0
```

**3. Gerar certificados**

Se és o **primeiro PC (Sink)**:
```bash
# Criar CA e certificado do Sink
./support/setup_sink.sh
```

Se és um **Node** e a CA já existe noutro PC:
```bash
# 1. Copiar certificados CA do PC que tem o Sink:
#    certs/ca_certificate.pem
#    certs/ca_private_key.pem

# 2. Criar certificado do Node
./support/setup_node.sh
```

### Setup Rede Multi-PC

Para testar com múltiplos PCs:

**PC 1 (Sink):**
```bash
./support/setup_sink.sh
# Copiar certs/ca_*.pem para os outros PCs
```

**PC 2, 3, ... (Nodes):**
```bash
# Copiar ca_certificate.pem e ca_private_key.pem para certs/
./support/setup_node.sh
```

---

## Execução

### Sink
```bash
# Modo interativo
sudo ./iot-sink interactive hci0

# Comandos disponíveis
sink> status       # Ver estado do Sink
sink> downlinks    # Listar Nodes conectados
sink> inbox        # Ver mensagens recebidas
```

### Node
```bash
# Modo interativo
./iot-node interactive

# Comandos no CLI
node> scan         # Procurar Sink/Nodes
node> connect 1    # Conectar ao dispositivo #1
node> status       # Ver estado (hop count, uplink, downlinks)
node> send Hello!  # Enviar mensagem ao Sink
```

### Teste Multi-Hop (2 máquinas com 2 adaptadores BLE)

**Máquina 1 (Sink + Node intermediário):**
```bash
# Terminal 1: Sink
sudo ./iot-sink interactive hci0

# Terminal 2: Node intermediário
./iot-node interactive --adapter 1
node> scan
node> connect <sink>
```

**Máquina 2 (Node final):**
```bash
./iot-node interactive
node> scan
node> connect <node_intermediario>
node> send teste multihop
```

**Verificar:**
- Node intermediário verá `hop=0`, Node final verá `hop=1`
- Heartbeats são forwarded (ver logs: "Flooding heartbeat para X downlink(s)")
- Mensagem do Node final chega ao Sink via Node intermediário

---

## Arquitetura

### Topologia

```
         Sink (hop=-1)
           /   |   \
          /    |    \
    Node A   Node B   Node C
    (h=0)    (h=0)    (h=0)
               |
             /   \
        Node D   Node E
        (h=1)    (h=1)
```

### Estrutura

```
iot/
├── sync/           # Sink (gateway)
│   ├── sink_device.py
│   ├── interactive_sink.py
│   └── sink_cli.py
├── node/           # Nodes IoT
│   ├── iot_node.py
│   ├── interactive_node.py
│   └── node_cli.py
├── common/         # Código partilhado
│   ├── ble/        # GATT Server/Client, Advertising
│   ├── network/    # Routing, Forwarding, Packets
│   ├── security/   # X.509, Auth, HMAC, Replay, DTLS
│   ├── protocol/   # Heartbeat
│   └── utils/      # NID, Logger, Constants
├── support/        # CA e provisioning
│   ├── ca.py                 
│   ├── provision_device.py   
│   ├── setup_sink.sh         
│   └── setup_node.sh         
├── certs/          # Certificados gerados
├── logs/           # Logs de execução
└── docs/           # Documentação
    └── specs/      # Especificação do projeto
```

---

## Segurança

### Certificados X.509
- CA própria
- Curva P-521
- ECDSA + ECDH

### Autenticação
- Mútua automática
- Challenge-response
- Validação de certificados

### Session Keys
- ECDH por link
- 32 bytes
- Nova a cada autenticação

### Integridade
- HMAC-SHA256 em todos os pacotes
- Sequence numbers
- Replay protection (window 100)
- Fragmentação automática para mensagens BLE grandes

### Encriptação End-to-End
- DTLS com AES-256-GCM
- Mensagens DATA encriptadas
- Inbox recebe mensagens desencriptadas automaticamente

---

## Limitações

- Autenticação de downlinks: Placeholder (aceita sem validação real)
- Teste em larga escala (10+ dispositivos) não realizado

---

## Autores

**SIC 2025/2026**

- 118655 - Pedro Laredo
- 119638 - Rafael Soares
- 119401 - Tomás Cruz
- 119867 - Guilherme Tavares
- 119806 - João Abrunhosa

