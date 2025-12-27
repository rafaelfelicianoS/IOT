# Guia de Teste - GATT Server

Este guia explica como testar o GATT Server que implementámos.

---

## 📋 Pré-requisitos

### Verificar Bluetooth

```bash
# Ver adaptadores Bluetooth disponíveis
hciconfig

# Deve mostrar algo como:
# hci0:	Type: Primary  Bus: USB
#	BD Address: XX:XX:XX:XX:XX:XX  ACL MTU: 1021:8  SCO MTU: 64:1
#	UP RUNNING
```

Se o adaptador não estiver UP:
```bash
sudo hciconfig hci0 up
```

---

## 🔧 Instalação

### Opção 1: Script Automático (Recomendado)

```bash
# Executar script de instalação
sudo bash install_deps.sh
```

### Opção 2: Manual

```bash
# 1. Instalar dependências do sistema
sudo apt-get update
sudo apt-get install -y bluez bluez-tools libbluetooth-dev \
    python3-dbus python3-gi libglib2.0-dev \
    python3-dev python3-pip python3-venv \
    bluetooth hcitool

# 2. Verificar serviço Bluetooth
sudo systemctl status bluetooth

# 3. Criar virtual environment
python3 -m venv venv
source venv/bin/activate

# 4. Instalar dependências Python
pip install --upgrade pip
pip install loguru python-dotenv typer rich
```

---

## 🧪 Teste 1: Executar GATT Server

### Terminal 1: Servidor

```bash
# Ativar venv (se ainda não estiver)
source venv/bin/activate

# Executar servidor GATT (REQUER SUDO!)
sudo python3 examples/test_gatt_server.py hci0
```

**Saída esperada**:
```
============================================================
  GATT Server Test - IoT Network Service
============================================================

📱 Device NID: 12345678-1234-5678-1234-567890abcdef
   Short: 12345678...

🔧 A criar IoTNetworkService...
✅ Application criada com sucesso!
   Service UUID: 12340000-0000-1000-8000-00805f9b34fb
   Characteristics: 4

📡 A registar application no adaptador hci0...
✅ GATT application registada com sucesso!

============================================================
  ✅ GATT Server a correr!
============================================================

Serviço disponível para clientes BLE.
Pressione Ctrl+C para terminar.
```

### Terminal 2: Cliente (bluetoothctl)

```bash
# Abrir bluetoothctl
bluetoothctl

# Comandos dentro do bluetoothctl:
[bluetooth]# power on
[bluetooth]# scan on

# Aguardar alguns segundos até ver o dispositivo
# (pode aparecer como "Unknown" ou com um nome genérico)

# Anotar o MAC address do dispositivo
# Conectar (substituir XX:XX:XX:XX:XX:XX pelo MAC address)
[bluetooth]# connect XX:XX:XX:XX:XX:XX

# Se conectar com sucesso, listar serviços
[bluetooth]# list-attributes

# Deves ver o serviço IoT Network com UUID 12340000-...
# E as 4 características

# Sair
[bluetooth]# exit
```

---

## 🧪 Teste 2: Verificar Características GATT

Depois de conectar com `bluetoothctl`, podes explorar as características:

### Ver todas as características

```bash
[bluetooth]# list-attributes
```

Deves ver:

```
Service /org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX/service0XXX
	12340000-0000-1000-8000-00805f9b34fb
	IoT Network Service
Characteristic /org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX/service0XXX/char0XXX
	12340001-0000-1000-8000-00805f9b34fb
	NetworkPacket
Characteristic /org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX/service0XXX/char0XXX
	12340002-0000-1000-8000-00805f9b34fb
	DeviceInfo
Characteristic /org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX/service0XXX/char0XXX
	12340003-0000-1000-8000-00805f9b34fb
	NeighborTable
Characteristic /org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX/service0XXX/char0XXX
	12340004-0000-1000-8000-00805f9b34fb
	Auth
```

### Ler Device Info

```bash
# Selecionar a characteristic DeviceInfo (UUID 12340002-...)
[bluetooth]# select-attribute /org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX/service0XXX/char0XXX

# Ler valor
[bluetooth]# read
```

Deves ver os bytes do NID + hop count + device type.

---

## 🧪 Teste 3: Scan BLE

Verificar se o dispositivo aparece no scan:

```bash
# Scan simples
sudo hcitool lescan

# Scan com informação detalhada
sudo bluetoothctl
[bluetooth]# scan on
```

---

## 🐛 Troubleshooting

### Erro: "Dependency glib-2.0 not found"

```bash
sudo apt-get install libglib2.0-dev python3-gi
```

### Erro: "Bluetooth stack error"

```bash
# Reiniciar serviço Bluetooth
sudo systemctl restart bluetooth

# Verificar status
sudo systemctl status bluetooth
```

### Erro: "Permission denied"

O servidor GATT **requer sudo** porque interage diretamente com o BlueZ via D-Bus:

```bash
sudo python3 examples/test_gatt_server.py hci0
```

### Adaptador não aparece (hci0)

```bash
# Listar adaptadores
hciconfig

# Se não mostrar nada:
sudo hciconfig hci0 up

# Verificar no sistema
lsusb | grep -i bluetooth
```

### "Application already registered"

Se já tens uma aplicação GATT registada:

```bash
# Parar o servidor anterior (Ctrl+C)
# Aguardar alguns segundos
# Tentar novamente
sudo python3 examples/test_gatt_server.py hci0
```

---

## 📊 Logs

Os logs são guardados em `logs/test_gatt_server.log`:

```bash
# Ver logs em tempo real
tail -f logs/test_gatt_server.log

# Ver últimas 50 linhas
tail -50 logs/test_gatt_server.log
```

---

## ✅ Checklist de Teste

- [ ] Servidor GATT inicia sem erros
- [ ] Servidor regista com BlueZ (mensagem "✅ GATT application registada")
- [ ] Dispositivo aparece em scan BLE
- [ ] Consegues conectar via `bluetoothctl`
- [ ] Serviço IoT Network (12340000-...) é visível
- [ ] 4 Características são visíveis
- [ ] Consegues ler DeviceInfo characteristic
- [ ] Logs são criados em `logs/`

---

## 🎯 Teste 4: BLE Client (Scanner e Conexão)

### Pré-requisito: SimpleBLE

```bash
# Instalar SimpleBLE
pip install simplepyble

# Ou via apt (se disponível)
sudo apt install python3-simplepyble
```

### Executar teste do BLE Client

**Terminal 1**: Manter o GATT Server a correr (test_gatt_server.py)

**Terminal 2**: Executar BLE Client

```bash
# Executar cliente BLE
python3 examples/test_ble_client.py
```

**Saída esperada**:
```
============================================================
  BLE Client Test - IoT Network Scanner
============================================================

🔍 A fazer scan de dispositivos IoT...
   (aguarda 5 segundos)

✅ Encontrados 1 dispositivos IoT:

  1. IoT-Node (E0:D3:62:D6:EE:A0)
     Address: E0:D3:62:D6:EE:A0
     RSSI: -45 dBm
     Services: 1

============================================================
🔗 A conectar ao primeiro dispositivo: E0:D3:62:D6:EE:A0
============================================================

✅ Conectado com sucesso!

🔍 A explorar serviços GATT...
   Encontrados X serviços:

   📦 Service: 12340000-0000-1000-8000-00805f9b34fb
      - Characteristic: 12340001-...
        Capabilities: write, notify
      - Characteristic: 12340002-...
        Capabilities: read
      (...)

============================================================
📖 A ler DeviceInfo Characteristic...
============================================================

✅ DeviceInfo lida: 18 bytes

   📱 NID: d18371c1-884c-4265-957d-ce1f01c3a59d
      Short: d18371c1...
   🔢 Hop Count: 1
   🏷️  Device Type: node

============================================================
📖 A ler NeighborTable Characteristic...
============================================================

✅ NeighborTable lida: X bytes

   👥 Número de vizinhos: 2

   1. NID: 12345678...
      Hop Count: 0
   2. NID: 87654321...
      Hop Count: 1

============================================================
👋 A desconectar...
============================================================
✅ Desconectado
```

---

## 🎯 Próximos Testes

Depois de confirmar que o BLE Client funciona:

1. **Testar callbacks**: Escrever dados na NetworkPacket characteristic
2. **Testar notificações**: Subscrever e receber notificações
3. **Múltiplos clientes**: Conectar 2+ dispositivos simultaneamente
4. **Neighbor Discovery**: Scan periódico automático
5. **CLI Interface**: Comandos interativos (scan, connect, status)

---

## 📞 Ajuda

Se tiveres problemas:

1. Verifica os logs: `tail -f logs/test_gatt_server.log`
2. Verifica Bluetooth: `sudo systemctl status bluetooth`
3. Verifica adaptador: `hciconfig`
4. Consulta [QUICKSTART.md](QUICKSTART.md) para mais detalhes

---

**Boa sorte com os testes! 🚀**
