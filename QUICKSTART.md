# Quick Start Guide

Guia rápido para executar o projeto IoT Bluetooth Network.

---

## 📋 Requisitos

- Linux com Bluetooth LE
- Python 3.8+
- BlueZ stack
- 2+ dispositivos BLE (ou máquinas virtuais)

---

## 🚀 Instalação

### 1. Instalar Dependências

```bash
sudo bash install_deps.sh
```

Isso instala:
- BlueZ e ferramentas Bluetooth
- Python dependencies (requirements.txt)
- SimpleBLE para GATT Client
- Dependências de desenvolvimento

### 2. Gerar Certificados

```bash
# Certificados do Sink
python3 support/provision_device.py --type sink --nid $(uuidgen)

# Certificados de Nodes (um para cada node)
python3 support/provision_device.py --type node --nid $(uuidgen)
python3 support/provision_device.py --type node --nid $(uuidgen)
```

Os certificados são salvos em `certs/`.

### 3. Verificar Bluetooth

```bash
# Listar adaptadores
hciconfig

# Se não estiver UP:
sudo hciconfig hci0 up

# Testar scan
sudo hcitool lescan
```

---

## 🎯 Execução

### Iniciar Sink (Gateway)

```bash
# Modo interativo com interface hci0
./iot-sink interactive hci0
```

Comandos disponíveis no Sink:
```
sink> status          # Ver status do Sink
sink> connections     # Listar nodes conectados
sink> inbox          # Ver mensagens recebidas
sink> heartbeat      # Info sobre heartbeats
sink> help           # Ajuda
sink> quit           # Sair
```

### Iniciar Node (IoT Device)

```bash
# Em outro terminal/máquina
./iot-node interactive
```

Comandos disponíveis no Node:
```
node> scan           # Procurar Sink/Nodes
node> connect 1      # Conectar ao device #1
node> send Hello!    # Enviar mensagem ao Sink
node> status         # Ver status do node
node> disconnect     # Desconectar uplink
node> help          # Ajuda
node> quit          # Sair
```

---

## 📝 Exemplo de Uso

### Cenário: Node envia mensagem para Sink

**Terminal 1 - Sink:**
```bash
./iot-sink interactive hci0

# Aguardar node conectar
# Verificar conexões
sink> connections

# Ver mensagens recebidas
sink> inbox
```

**Terminal 2 - Node:**
```bash
./iot-node interactive

# Procurar Sink
node> scan

# Conectar ao Sink (assumindo que aparece como #1)
node> connect 1

# Aguardar autenticação...

# Enviar mensagem
node> send Hello from Node!

# Verificar status
node> status
```

**Terminal 1 - Sink (verificar):**
```bash
sink> inbox
# Deve mostrar a mensagem "Hello from Node!"
```

---

## 🏗️ Estrutura do Projeto

```
iot/
├── sync/              # Sink (gateway)
│   ├── sink_device.py        # Lógica principal do Sink
│   ├── interactive_sink.py   # CLI interativa
│   └── sink_cli.py           # Parser de comandos
├── node/              # IoT Nodes
│   ├── iot_node.py           # Lógica principal do Node
│   ├── interactive_node.py   # CLI interativa
│   └── node_cli.py           # Parser de comandos
├── common/            # Código partilhado
│   ├── ble/          # GATT Server/Client, Advertising, Fragmentação
│   ├── network/      # RouterDaemon, Packets, ForwardingTable, HeartbeatMonitor
│   ├── security/     # X.509, Authentication, DTLS, Replay Protection
│   ├── protocol/     # Heartbeat Protocol
│   └── utils/        # NID, Logger, Constants
├── support/           # CA e provisioning
│   ├── ca.py                 # Certificate Authority
│   └── provision_device.py   # Geração de certificados
├── certs/             # Certificados X.509 (P-521)
├── keys/              # Diretório para chaves (vazio)
├── logs/              # Logs de execução
└── docs/              # Documentação
    └── specs/         # Especificação do projeto
```

---

## 🔐 Segurança

O projeto implementa:

- **X.509 Certificates**: P-521 curve, ECDSA + ECDH
- **Autenticação Mútua**: Challenge-response automático
- **Session Keys**: ECDH por link (32 bytes)
- **HMAC-SHA256**: Integridade em todos os pacotes
- **Replay Protection**: Sequence numbers + window 100
- **DTLS**: Encriptação end-to-end com AES-256-GCM
- **Heartbeat Signatures**: ECDSA para autenticidade

---

## 🌐 Topologia

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

- Sink é o gateway central
- Nodes selecionam uplink automaticamente (lazy selection)
- Heartbeats a cada 5 segundos
- Timeout após 3 heartbeats perdidos (15s)
- Chain reaction disconnect quando uplink falha

---

## 🛠️ Comandos Úteis

### Bluetooth

```bash
# Reset adaptador
sudo hciconfig hci0 down && sudo hciconfig hci0 up

# Scan BLE
sudo hcitool lescan

# Interface interativa
bluetoothctl
```

### Logs

```bash
# Ver logs em tempo real
tail -f logs/iot-network.log

# Limpar logs
rm -f logs/*.log
```

### Certificados

```bash
# Ver certificados gerados
ls -lh certs/

# Verificar certificado
openssl x509 -in certs/ca_certificate.pem -text -noout
```

---

## 🐛 Troubleshooting

### Bluetooth não funciona

```bash
# Verificar serviço
sudo systemctl status bluetooth

# Reiniciar
sudo systemctl restart bluetooth

# Verificar adaptador
hciconfig
```

### Erro de permissões

```bash
# Adicionar user ao grupo bluetooth
sudo usermod -a -G bluetooth $USER

# Logout/login para aplicar
```

### SimpleBLE não instala

```bash
# Instalar dependências
sudo apt-get install -y cmake build-essential libdbus-1-dev

# Tentar novamente
pip3 install simpleble
```

### Node não encontra Sink

1. Verificar se Sink está em modo advertising:
   ```bash
   sink> status
   ```

2. Verificar se Bluetooth está UP:
   ```bash
   hciconfig
   ```

3. Aumentar potência de sinal:
   ```bash
   sudo hciconfig hci0 leadv 0
   ```

### Autenticação falha

1. Verificar certificados em `certs/`
2. Gerar novos certificados se necessário
3. Verificar logs: `tail -f logs/*.log`

---

## 📚 Documentação

- **README.md**: Visão geral e arquitetura
- **docs/specs/project.txt**: Especificação completa (texto)
- **docs/specs/project.pdf**: Especificação completa (PDF)
- **docs/specs/Ex08.pdf**: Guia de laboratório BLE
- **docs/LOGGING.md**: Sistema de logging detalhado

---

## ✨ Características Implementadas

- ✅ Topologia em árvore com lazy uplink selection
- ✅ Heartbeat protocol (5s) com ECDSA
- ✅ Heartbeat forwarding para downlinks
- ✅ RouterDaemon com forwarding table
- ✅ NID (128 bits UUID)
- ✅ X.509 (P-521)
- ✅ Autenticação mútua
- ✅ ECDH session keys
- ✅ HMAC-SHA256
- ✅ Replay protection
- ✅ AES-256-GCM (DTLS)
- ✅ Fragmentação automática (180 bytes)
- ✅ Serviço Inbox no Sink
- ✅ Chain reaction disconnect
- ✅ Timeout detection (15s)

---

## 📞 Comandos Avançados

### Sink CLI

```bash
# Ver downlinks ativos
sink> connections

# Bloquear heartbeats para um node
sink> block_heartbeat <NID>

# Desbloquear heartbeats
sink> unblock_heartbeat <NID>

# Ver lista de nodes com heartbeat bloqueado
sink> blocked_nodes

# Estatísticas
sink> stats
```

### Node CLI

```bash
# Informação de uplink
node> uplink

# Ver downlinks (se for router)
node> downlinks

# Forçar desconexão do uplink
node> disconnect

# Reconectar
node> scan
node> connect <ID>

# Ver hop count
node> status
```

---

**Projeto pronto para execução e testes! 🚀**
