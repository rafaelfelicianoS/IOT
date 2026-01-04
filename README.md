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

### Setup

```bash
# Instalar dependências
sudo bash install_deps.sh

# Gerar certificados
python3 support/provision_device.py --type sink --nid $(uuidgen)
python3 support/provision_device.py --type node --nid $(uuidgen)
```

---

## Execução

### Sink
```bash
./iot-sink interactive hci0
```

### Node
```bash
./iot-node interactive

node> scan
node> connect 1
node> send Hello!
```

### Verificar mensagem
```bash
sink> inbox
```

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
│   └── provision_device.py
├── certs/          # Certificados gerados
├── keys/           # Chaves (vazia)
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

- DATA multi-hop: Node→Sink direto funcional, forwarding intermediário básico implementado
- Heartbeat forwarding: Totalmente funcional
- RouterDaemon: Implementado com forwarding table

---

## Autores

Grupo X - SIC 2025/2026

