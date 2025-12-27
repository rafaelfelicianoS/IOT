# Quick Start Guide

Guia rápido para começar a desenvolver o projeto IoT Bluetooth Network.

---

## 📦 Setup Inicial

### 1. Instalar Dependências do Sistema (Ubuntu)

```bash
# BlueZ stack
sudo apt-get update
sudo apt-get install -y bluez bluez-tools libbluetooth-dev

# D-Bus e GLib
sudo apt-get install -y python3-dbus python3-gi libglib2.0-dev

# Python development
sudo apt-get install -y python3-dev python3-pip python3-venv

# SimpleBLE dependencies
sudo apt-get install -y cmake build-essential libdbus-1-dev

# OpenSSL
sudo apt-get install -y libssl-dev

# Ferramentas úteis
sudo apt-get install -y bluetooth hcitool bluetoothctl
```

### 2. Criar Virtual Environment

```bash
# Criar venv
python3 -m venv venv

# Ativar
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Instalar Dependências Python

```bash
pip install -r requirements.txt
```

**Nota**: Se tiver problemas com `simpleble` ou `pyDTLS`, podemos instalar individualmente depois.

### 4. Configurar Ambiente

```bash
# Copiar configuração
cp .env.example .env

# Editar conforme necessário
nano .env
```

### 5. Verificar Bluetooth

```bash
# Listar adaptadores
hciconfig

# Deve mostrar algo como:
# hci0:	Type: Primary  Bus: USB
#	BD Address: XX:XX:XX:XX:XX:XX  ACL MTU: 1021:8  SCO MTU: 64:1
#	UP RUNNING
```

Se não estiver UP:

```bash
sudo hciconfig hci0 up
```

---

## 🔍 Verificar Setup

Execute o helper script:

```bash
python3 dev_helper.py
```

Deve mostrar:
- ✅ Todos os diretórios criados
- Estatísticas do projeto
- Próximos passos

---

## 📚 Estrutura do Projeto

```
iot-bluetooth-network/
│
├── sink/              # Código do Sink (gateway)
├── node/              # Código dos IoT Nodes
├── common/            # Código partilhado
│   ├── ble/          # Camada BLE (GATT)
│   ├── network/      # Camada de rede (packets, routing)
│   ├── security/     # Segurança (X.509, ECDH, DTLS)
│   ├── protocol/     # Protocolos (heartbeat, inbox)
│   └── utils/        # Utilidades
├── support/           # Ferramentas (CA, provisioning)
└── tests/             # Testes
```

---

## 🎯 Roadmap de Implementação

### ✅ Fase 0: Preparação (CONCLUÍDA)

- [x] Estrutura de diretórios
- [x] Configuração e constantes
- [x] Classes base (Packet, ForwardingTable, NID)
- [x] Sistema de logging

### 🚧 Fase 1: BLE Básico (PRÓXIMO)

**Ficheiros a criar**:

1. **[common/ble/gatt_server.py](common/ble/gatt_server.py)** - Servidor GATT (D-Bus)
   - Adaptar [docs/src-exploring-bluetooth/gatt_server.py](docs/src-exploring-bluetooth/gatt_server.py)
   - Classes genéricas: `Application`, `Service`, `Characteristic`, `Descriptor`

2. **[common/ble/gatt_services.py](common/ble/gatt_services.py)** - Serviços GATT customizados
   - `IoTNetworkService` + Characteristics

3. **[common/ble/gatt_client.py](common/ble/gatt_client.py)** - Cliente BLE (SimpleBLE)
   - Scan, connect, read/write

4. **[common/network/link_manager.py](common/network/link_manager.py)** - Gestão de links
   - Uplink/downlinks management

**Como começar**:

```bash
# Começar pelo GATT Server
# Abrir o exemplo e adaptar
code docs/src-exploring-bluetooth/gatt_server.py
code common/ble/gatt_server.py
```

### 📋 Fases Seguintes

Ver [PROJECT_STATUS.md](PROJECT_STATUS.md) para roadmap completo.

---

## 🧪 Testar BLE

### Verificar Dispositivos BLE Nearby

```bash
# Scan (Ctrl+C para parar)
sudo hcitool lescan

# Ou usar bluetoothctl
bluetoothctl
> scan on
> list
> exit
```

### Testar Exemplo Chat Server

```bash
# Terminal 1: Executar servidor
sudo python3 docs/src-exploring-bluetooth/gatt_server.py hci0

# Terminal 2: Conectar e testar com bluetoothctl
bluetoothctl
> scan on
> connect [MAC_ADDRESS]
```

---

## 📖 Documentação Importante

### Ficheiros de Referência

- [README.md](README.md) - Visão geral do projeto
- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Status e roadmap detalhado
- [docs/project.pdf](docs/project.pdf) - Especificação completa do projeto
- [docs/Ex08.pdf](docs/Ex08.pdf) - Guia de laboratório BLE

### Código de Referência

- [docs/src-exploring-bluetooth/gatt_server.py](docs/src-exploring-bluetooth/gatt_server.py) - Exemplo GATT Server

### Módulos Já Implementados

- [common/utils/constants.py](common/utils/constants.py) - Constantes (UUIDs, tipos de mensagens)
- [common/utils/config.py](common/utils/config.py) - Configuração
- [common/utils/nid.py](common/utils/nid.py) - Network Identifiers
- [common/network/packet.py](common/network/packet.py) - Formato de pacotes
- [common/network/forwarding_table.py](common/network/forwarding_table.py) - Tabela de forwarding

---

## 🛠️ Comandos Úteis

### Desenvolvimento

```bash
# Ver status do projeto
python3 dev_helper.py

# Executar testes
pytest

# Executar com coverage
pytest --cov=common --cov=sink --cov=node

# Formatar código
black .

# Lint
flake8 .
```

### Bluetooth

```bash
# Ver adaptadores
hciconfig

# Reset adaptador
sudo hciconfig hci0 down
sudo hciconfig hci0 up

# Scan BLE
sudo hcitool lescan

# Interface interativa
bluetoothctl
```

### Logs

```bash
# Ver logs
tail -f logs/*.log

# Limpar logs
rm -rf logs/*.log
```

---

## ❓ Troubleshooting

### SimpleBLE não instala

Se tiver problemas com `simpleble`:

```bash
# Instalar dependências build
sudo apt-get install -y cmake build-essential libdbus-1-dev

# Tentar instalar novamente
pip install simpleble
```

Se continuar a falhar, podemos usar alternativas (Bleak ou PyBluez).

### pyDTLS não instala

```bash
# Instalar OpenSSL dev
sudo apt-get install -y libssl-dev

# Tentar novamente
pip install pyDTLS
```

Alternativa: implementar DTLS manualmente com `cryptography`.

### Bluetooth não funciona

```bash
# Verificar serviço
sudo systemctl status bluetooth

# Reiniciar serviço
sudo systemctl restart bluetooth

# Verificar adaptador
hciconfig
```

### Permissões

Alguns comandos BLE requerem `sudo` ou adicionar user ao grupo `bluetooth`:

```bash
sudo usermod -a -G bluetooth $USER
# Logout/login para aplicar
```

---

## 🚀 Começar a Programar

### Criar primeiro módulo: GATT Server

```bash
# Abrir editor
code common/ble/gatt_server.py

# Começar com template baseado no exemplo
# Ver docs/src-exploring-bluetooth/gatt_server.py
```

### Estrutura sugerida:

```python
"""
GATT Server implementation using D-Bus and BlueZ.

Based on the example from docs/src-exploring-bluetooth/gatt_server.py
"""

import dbus
import dbus.service
from gi.repository import GLib
from common.utils.constants import *
from common.utils.logger import get_logger

logger = get_logger("gatt_server")

# ... classes Application, Service, Characteristic, Descriptor
```

---

## 📞 Ajuda

- Consultar [PROJECT_STATUS.md](PROJECT_STATUS.md) para ver o que fazer a seguir
- Ver exemplos em [docs/src-exploring-bluetooth/](docs/src-exploring-bluetooth/)
- Ler especificação em [docs/project.pdf](docs/project.pdf)

---

**Boa sorte com o desenvolvimento! 🚀**
