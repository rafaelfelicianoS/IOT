# Guia de Testes - Feature Integration

**Branch**: `feature/integration`

Este guia mostra como testar todas as funcionalidades implementadas.

---

## 📋 Pré-requisitos

### Hardware
- 2 PCs com Bluetooth BLE (ou dongles BLE)
- Distância: < 10 metros (idealmente lado a lado)

### Software
```bash
# Verificar que estás no branch correto
git branch --show-current  # deve mostrar: feature/integration

# Ativar venv
source venv/bin/activate

# Verificar dependências
pip list | grep -E "(bleak|simpleble|dbus|loguru)"
```

---

## 🧪 Testes Disponíveis

### 1. GATT Server Básico
**O que testa**: GATT Server inicia, advertising funciona, características GATT disponíveis

**PC Server**:
```bash
sudo python3 examples/test_gatt_server.py hci0
```

**Resultado esperado**:
```
✅ GATT Server registado com sucesso
✅ Advertisement registado com sucesso
✅ Heartbeat timer iniciado (5s intervals)
✅ Neighbor update timer iniciado (10s intervals)
📡 A aguardar conexões...
```

**Verificar noutro terminal**:
```bash
# Ver se dispositivo está visível
sudo hcitool lescan

# Ou usar bluetoothctl
bluetoothctl
> scan on
# Deve aparecer: IoT-Network-XXXX
```

---

### 2. BLE Client - Conexão e Leitura
**O que testa**: Scan, conexão, leitura de características

**PC Client** (com server a correr):
```bash
python3 examples/test_ble_client.py
```

**Resultado esperado**:
```
🔍 A fazer scan...
✅ Encontrado: E0:D3:62:D6:EE:A0
🔗 A conectar...
✅ Conectado!
📡 Services: 13 services encontrados
📖 A ler DeviceInfo...
✅ DeviceInfo lido com sucesso
```

---

### 3. Packet Send via Bleak
**O que testa**: Envio de pacotes via BLE (write operation)

**PC Client**:
```bash
python3 examples/test_packet_send_bleak.py
```

**Resultado esperado**:
```
🔍 A fazer scan de dispositivos BLE...
✅ Encontrado: IoT-Network (E0:D3:62:D6:EE:A0)
🔌 A conectar ao dispositivo...
✅ Conectado: True
📡 A descobrir serviços...
✅ IoT Network Service encontrado
📦 A criar pacote de teste...
   Total Packet Size: 126 bytes
✍️  A enviar pacote via Bleak...
✅ SUCESSO! Pacote enviado com sucesso!
```

**No server** (terminal onde corre test_gatt_server.py):
```
📨 Pacote recebido via WriteNetworkPacket
   Source: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
   Size: 126 bytes
```

---

### 4. Heartbeat Notifications
**O que testa**: Receção de heartbeats via notificações BLE

**PC Client**:
```bash
python3 examples/test_heartbeat_notifications.py
```

**Resultado esperado**:
```
🔍 Scanning for BLE devices...
✅ Found target: E0:D3:62:D6:EE:A0
🔗 Connecting...
✅ Connected!
📡 Subscribing to heartbeat notifications...
✅ Subscribed to NetworkPacket notifications!

⏳ Listening for 30 seconds...

📨 Heartbeat #1 received!
   Sink NID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
   Sequence: 123
   Timestamp: 1735500000.123

📨 Heartbeat #2 received!
   ...
```

**Frequência**: 1 heartbeat a cada ~5 segundos (deve receber 6 heartbeats em 30s)

---

### 5. Neighbor Table Notifications
**O que testa**: Receção de updates da neighbor table

**PC Client**:
```bash
python3 examples/test_neighbor_notifications.py
```

**Resultado esperado**:
```
🔍 Scanning for device...
✅ Found: E0:D3:62:D6:EE:A0
🔗 Connecting...
✅ Connected!
📡 Subscribing to neighbor table notifications...
✅ Subscribed!

⏳ Listening for 90 seconds...

📊 Neighbor Table Update #1 (8 bytes)
   Format: 00 00 00 00 00 00 00 00
   (2 neighbors found)

📊 Neighbor Table Update #2 (8 bytes)
   ...
```

**Frequência**: 1 update a cada ~10 segundos

---

### 6. Network CLI (Interface Completa)
**O que testa**: Scan, connect, disconnect, status - tudo num interface interativa

**PC Client**:
```bash
python3 examples/network_cli.py
```

**Comandos para experimentar**:

```
╔═══════════════════════════════════════════════════════════════╗
║                  IoT Network - CLI Interface                  ║
╚═══════════════════════════════════════════════════════════════╝

# 1. Ver comandos disponíveis
iot-network> help

# 2. Fazer scan de vizinhos
iot-network> scan

# Output esperado:
🔍 A fazer scan de vizinhos...

✅ Encontrados 1 vizinho(s):

┌─────────────────────┬──────────────┬─────┬────────┬─────────┐
│ Address             │ NID          │ Hop │ Type   │ RSSI    │
├─────────────────────┼──────────────┼─────┼────────┼─────────┤
│ E0:D3:62:D6:EE:A0   │ 12345678...  │  -1 │ sink   │  -60dBm │
└─────────────────────┴──────────────┴─────┴────────┴─────────┘

🏆 Melhor rota: E0:D3:62:D6:EE:A0 (hop=-1, rssi=-60dBm)

# 3. Ver vizinhos conhecidos (cache)
iot-network> neighbors

# 4. Conectar a um vizinho
iot-network> connect E0:D3:62:D6:EE:A0

# Output esperado:
🔗 A conectar a E0:D3:62:D6:EE:A0...
   NID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
   Hop count: -1
   RSSI: -60dBm

✅ Conectado com sucesso a E0:D3:62:D6:EE:A0!

# 5. Ver status da rede
iot-network> status

# Output esperado:
📊 STATUS DA REDE

🔼 UPLINK:
   Address: E0:D3:62:D6:EE:A0
   NID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
   Hop count: -1
   Type: sink
   Estado: 🟢 Conectado

🔽 DOWNLINKS: Nenhum

📈 ESTATÍSTICAS:
   Vizinhos conhecidos: 1
   Vizinhos conectados: 1
   Melhor hop count: -1
   Último scan: 10s atrás

# 6. Enviar pacote de dados
iot-network> send E0:D3:62:D6:EE:A0 Hello from CLI!

# Output esperado:
📤 A enviar mensagem para E0:D3:62:D6:EE:A0...
   Mensagem: Hello from CLI!
   Tamanho: 15 caracteres

✅ Pacote enviado com sucesso!
   Tamanho total: 85 bytes
   Destino NID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX

# No servidor deve aparecer:
📨 Pacote recebido via WriteNetworkPacket
   Source: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
   Payload: Hello from CLI!
   Size: 85 bytes

# 7. Desconectar
iot-network> disconnect E0:D3:62:D6:EE:A0

# 8. Limpar tela
iot-network> clear

# 9. Sair
iot-network> exit
```

---

## 🔧 Configuração BLE (se necessário)

### Se tiveres erro "br-connection-unknown"

**PC Server**:
```bash
# Configurar adaptador para LE-only (disable BR/EDR)
./examples/configure_ble_only.sh hci0
```

### Se dispositivo não aparecer no scan

**PC Client**:
```bash
# Limpar cache BlueZ
./examples/clear_bluez_cache.sh -y

# Aproximar dispositivos fisicamente
# Reduzir interferência WiFi
```

---

## 📊 Checklist de Testes

Marca o que já testaste:

- [ ] **Test 1**: GATT Server inicia sem erros
- [ ] **Test 2**: BLE Client conecta e lê DeviceInfo
- [ ] **Test 3**: Packet Send via Bleak (126 bytes)
- [ ] **Test 4**: Heartbeat notifications (6 heartbeats em 30s)
- [ ] **Test 5**: Neighbor notifications (8 updates em 90s)
- [ ] **Test 6**: Network CLI - scan funciona
- [ ] **Test 7**: Network CLI - connect funciona
- [ ] **Test 8**: Network CLI - status mostra uplink
- [ ] **Test 9**: Network CLI - send envia pacote
- [ ] **Test 10**: Network CLI - disconnect funciona

---

## 🐛 Troubleshooting

### Erro: "SimpleBLE não está instalado"
```bash
pip install simpleble
```

### Erro: "Device not found"
1. Verificar que server está a correr: `sudo python3 examples/test_gatt_server.py hci0`
2. Verificar scan manual: `sudo hcitool lescan`
3. Aproximar dispositivos
4. Limpar cache: `./examples/clear_bluez_cache.sh -y`

### Erro: "br-connection-unknown"
```bash
./examples/configure_ble_only.sh hci0
```

### Server não inicia
```bash
# Parar outros processos bluetooth
sudo systemctl restart bluetooth

# Verificar permissões
sudo usermod -aG bluetooth $USER
```

---

## 📝 Logs

Todos os testes geram logs em `logs/`:
- `logs/iot-network.log` - Log geral
- `logs/test_gatt_server.log` - Server logs
- `logs/ble_operations_*.log` - Operações BLE detalhadas

Para ver logs em real-time:
```bash
tail -f logs/iot-network.log
```

---

## ✅ Próximos Passos

Depois de testares tudo:
1. Reportar resultados (o que funcionou / não funcionou)
2. Decidir próxima implementação (sugestão: Fase 3 - Security)

