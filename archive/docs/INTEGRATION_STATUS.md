# Feature Integration Branch

**Branch**: `feature/integration`  
**Created**: 2025-12-29  
**Purpose**: Branch de integração que combina todas as features implementadas até agora

---

##  O que este branch contém

Este branch integra código dos seguintes branches:

-  **feature/network-packets** - Transmissão de pacotes BLE (SimpleBLE + Bleak hybrid)
-  **feature/network-controls** - Network CLI + Neighbor Discovery
-  **feature/heartbeat-protocol** - Heartbeat protocol com notificações

---

##  Componentes Disponíveis

### BLE Layer (`common/ble/`)
-  **gatt_server.py** - GATT Server (D-Bus + BlueZ)
-  **gatt_services.py** - IoT Network Service customizado
-  **gatt_client.py** - BLE Client (SimpleBLE + Bleak hybrid)
-  **bleak_helper.py** - Helper para write operations via Bleak
-  **advertising.py** - BLE Advertising
-  **dbus_gatt_helper.py** - D-Bus GATT helper

### Network Layer (`common/network/`)
-  **packet.py** - Formato de pacotes (source, dest, type, payload, MAC)
-  **packet_manager.py** - PacketManager para send/receive
-  **forwarding_table.py** - Forwarding tables (switch learning)
-  **link_manager.py** - Gestão de uplink/downlinks
-  **neighbor_discovery.py** - Descoberta automática de vizinhos

### Protocol Layer (`common/protocol/`)
-  **heartbeat.py** - Heartbeat protocol (88 bytes: NID + Timestamp + Signature)

### Examples (`examples/`)
-  **network_cli.py** - CLI interativa (scan, connect, disconnect, status)
-  **test_gatt_server.py** - GATT Server test (com heartbeat timer)
-  **test_packet_send_bleak.py** - Teste de envio de pacotes via Bleak
-  **test_heartbeat_notifications.py** - Teste de heartbeat notifications
-  **test_neighbor_notifications.py** - Teste de neighbor table notifications
-  **test_ble_client.py** - Cliente BLE básico
-  **configure_ble_only.sh** - Script para configurar adaptador BLE (LE-only)
-  **clear_bluez_cache.sh** - Script para limpar cache BlueZ

### Utilities (`common/utils/`)
-  **constants.py** - Constantes (UUIDs, message types)
-  **config.py** - Gestão de configuração
-  **logger.py** - Sistema de logging
-  **nid.py** - Network Identifier (wrapper UUID)

---

##  Features Testadas End-to-End

1. **BLE Connection** - Conexão entre 2 PCs via BLE 
2. **BLE Write** - Envio de 126 bytes via Bleak 
3. **Neighbor Table Notifications** - 8 notificações em 80s 
4. **Heartbeat Notifications** - Heartbeats a cada 5s 

---

##  Como Testar

### 1. GATT Server (PC Server)
```bash
sudo python3 examples/test_gatt_server.py hci0
```

### 2. Network CLI (PC Client)
```bash
python3 examples/network_cli.py
```

Comandos disponíveis:
- `scan` - Descobrir vizinhos
- `neighbors` - Listar vizinhos conhecidos
- `connect <address>` - Conectar a vizinho
- `disconnect <address>` - Desconectar
- `status` - Ver status da rede (uplink, downlinks)

### 3. Testar Packet Send
```bash
python3 examples/test_packet_send_bleak.py
```

### 4. Testar Heartbeat
```bash
python3 examples/test_heartbeat_notifications.py
```

---

##  Próximas Implementações

Conforme [PROJECT_STATUS.md](PROJECT_STATUS.md), as próximas fases são:

### Fase 3: Certificates & Session Keys (50% da nota!)
- [ ] CA (Certification Authority)
- [ ] Geração de certificados X.509 com P-521
- [ ] Mutual authentication
- [ ] ECDH session keys

### Fase 4: Basic Message Routing
- [ ] HMAC-SHA256 para MACs
- [ ] Replay protection
- [ ] Router daemon

### Fase 5: Heartbeat Broadcast (completar)
- [ ] ECDSA signature (real, não placeholder)
- [ ] Signature verification
- [ ] Multi-unicast flooding

---

##  Known Issues

### SimpleBLE Write Limitation
**Problema**: SimpleBLE não consegue escrever em características GATT no Linux.

**Solução**: Sistema híbrido SimpleBLE + Bleak
- SimpleBLE: scan + notifications
- Bleak: write operations (fallback automático)

### BLE Advertising Intermitente
**Causas**: RSSI fraco, interferência WiFi, advertising intervals

**Mitigação**: Scan timeout maior, aproximar dispositivos

---

##  Estatísticas

- **Ficheiros Python**: ~35
- **Linhas de código**: ~4500
- **Fases completas**: 1/8 (BLE + parcial Network Controls + parcial Heartbeat)
- **Progresso**: ~25%

**Breakdown por avaliação**:
- Network (20%): ~60% completo
- **Security (50%)**: ~5% completo ️
- Documentation (30%): ~40% completo

---

##  Documentação

- [PROJECT_STATUS.md](PROJECT_STATUS.md) - Status detalhado e roadmap
- [README.md](README.md) - Documentação principal
- [docs/project.txt](docs/project.txt) - Especificação oficial do projeto
