# CLI Interativo - IoT Network

## Visão Geral

O CLI Interativo permite controlar e debugar o Sink e Node em tempo real, sem precisar reiniciar os dispositivos. É perfeito para:

-  **Debug**: Testar conexões, enviar mensagens, verificar status
-  **Testes**: Simular cenários rapidamente
-  **Monitorização**: Ver status em tempo real
-  **Aprendizagem**: Entender como a rede funciona

## Como Usar

### Sink Interativo

```bash
./iot-sink interactive hci0
```

Comandos disponíveis:

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `status` | Status geral do Sink | `status` |
| `downlinks` | Lista Nodes conectados | `downlinks` |
| `heartbeat_stats` | Stats de heartbeats | `heartbeat_stats` |
| `inbox [limit]` | Mostra mensagens recebidas | `inbox` ou `inbox 50` |
| `send <nid> <msg>` | Envia mensagem para um Node | `send 53a84 Hello Node!` |
| `broadcast <msg>` | Broadcast para todos os Nodes | `broadcast Attention!` |
| `session_keys` | Lista session keys | `session_keys` |
| `my_nid` | Mostra NID do Sink | `my_nid` |
| `clear` | Limpa a tela | `clear` |
| `help` | Ajuda | `help` |
| `exit` | Sai e para o Sink | `exit` |

### Node Interativo

```bash
./iot-node interactive
```

Comandos disponíveis:

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `scan [timeout]` | Procura Sinks/Nodes | `scan 10` |
| `connect [num\|addr]` | Conecta ao dispositivo escolhido | `connect 1` ou `connect E0:D3:62:D6:EE:A0` |
| `disconnect` | Desconecta do uplink | `disconnect` |
| `reconnect` | Reconecta ao uplink | `reconnect` |
| `status` | Status completo | `status` |
| `uplink` | Detalhes do uplink | `uplink` |
| `downlinks` | Lista downlinks | `downlinks` |
| `send <msg>` | Envia mensagem ao Sink | `send Hello Sink!` |
| `ping [count]` | Pinga o Sink | `ping 5` |
| `my_nid` | Mostra NID do Node | `my_nid` |
| `clear` | Limpa a tela | `clear` |
| `help` | Ajuda | `help` |
| `exit` | Sai e para o Node | `exit` |

## Exemplos Práticos

### Exemplo 1: Testar Conexão Básica

#### Terminal 1 - Sink
```bash
$ ./iot-sink interactive hci0
============================================================
  Iniciando IoT Sink Device (Interactive Mode)
============================================================

 Certificados encontrados:
   Cert: sink_af04ea89_cert.pem
   Key:  sink_af04ea89_key.pem
   CA:   ca_certificate.pem

╔═══════════════════════════════════════════════════════════════╗
║              IoT Sink - Interactive CLI                      ║
╚═══════════════════════════════════════════════════════════════╝

Digite 'help' para ver comandos disponíveis.
Digite 'exit' ou Ctrl+D para sair.

sink> status

 STATUS DO SINK

️  UPTIME: 15s

 DOWNLINKS: 0 node(s) conectado(s)

 HEARTBEATS:
   Sequência atual: 3

 REDE:
   Sink NID: 53a84472...
   Adapter: hci0
   GATT Server:  Ativo
   Advertisement:  Ativo

sink>
```

#### Terminal 2 - Node
```bash
$ ./iot-node interactive
============================================================
  Iniciando IoT Node Device (Interactive Mode)
============================================================

 Certificados encontrados:
   Cert: node_9d4df1cf_cert.pem
   Key:  node_9d4df1cf_key.pem
   CA:   ca_certificate.pem

╔═══════════════════════════════════════════════════════════════╗
║              IoT Node - Interactive CLI                      ║
╚═══════════════════════════════════════════════════════════════╝

Digite 'help' para ver comandos disponíveis.
Digite 'exit' ou Ctrl+D para sair.

Comandos principais:
  scan          - Procurar Sinks/Nodes disponíveis
  connect       - Conectar a um uplink
  disconnect    - Desconectar do uplink
  send          - Enviar mensagem ao Sink
  status        - Ver status da conexão

node> scan

 A fazer scan por 10s...

 Encontrados 2 dispositivo(s):

  1. E0:D3:62:D6:EE:A0  | Type: Sink | Hop: -1  | RSSI: -45 dBm
  2. A1:B2:C3:D4:E5:F6  | Type: Node | Hop: 0   | RSSI: -52 dBm

 Use 'connect <número>' ou 'connect <endereço>' para conectar

node> connect 1

 A conectar a E0:D3:62:D6:EE:A0...

 Conectado via GATT

 A autenticar...

 Autenticado com sucesso!

 Hop count: 0

node> status

╔═══════════════════════════════════════════════════════════════╗
║              IoT Node - Status (hop=0)                        ║
╚═══════════════════════════════════════════════════════════════╝

️  UPTIME: 1m 23s

 UPLINK:
   Status:  Conectado
   NID: 53a84472-db22-...
   Address: E0:D3:62:D6:EE:A0
   Authenticated: 
   Meu hop: 0

 DOWNLINKS: 0 node(s)

 AUTENTICAÇÃO:
   Uplink:  Autenticado
   Session Key:  Estabelecida

 HEARTBEATS:
   Último recebido: 1.2s atrás
   Sequência: 17

 REDE:
   Meu NID: 9d4df1cf-0b47-...
   Adapter: hci0
   GATT Server:  Ativo
   GATT Client:  Ativo

node> send Olá Sink!

 Enviando mensagem ao Sink...
   Mensagem: Olá Sink!

 Mensagem enviada com sucesso!

node> ping 3

 Enviando 3 pings ao Sink...

  1.  12.3ms
  2.  11.8ms
  3.  13.1ms

node>
```

### Exemplo 2: Monitorar Heartbeats

```bash
sink> heartbeat_stats

 HEARTBEAT STATS

   Sequência atual: 42
   Intervalo: 5.0s
   Total enviados: ~42

sink> downlinks

 DOWNLINKS CONECTADOS

┌─────────────────────┬────────────────────┬──────────────┐
│ Address             │ NID                │ Has Session  │
├─────────────────────┼────────────────────┼──────────────┤
│ A0:B1:C2:D3:E4:F5   │ 9d4df1cf-0b47-...  │            │
└─────────────────────┴────────────────────┴──────────────┘

 Total: 1 downlink(s)
```

### Exemplo 3: Debug de Problemas de Conexão

```bash
node> status
# Mostra: Uplink desconectado

node> scan 15
# Procura por 15 segundos

️  Nenhum Sink/Node encontrado

 Certifique-se que há um Sink ou Node a fazer advertising

# Verificar:
# 1. Sink está running?
# 2. Adapter BLE correto?
# 3. Permissões BLE OK?
```

### Exemplo 4: Testar Broadcast

```bash
# Terminal 1 - Sink
sink> downlinks
# Ver quantos Nodes conectados

sink> broadcast Mensagem para todos!

 Broadcasting para 3 Node(s)...
   Mensagem: Mensagem para todos!

️  Funcionalidade de broadcast ainda não totalmente implementada

# Cada Node conectado vai receber a mensagem
```

### Exemplo 5: Ver Mensagens Recebidas (Inbox)

```bash
# Terminal 1 - Sink
sink> inbox

 INBOX - MENSAGENS RECEBIDAS

┌──────────────────────┬──────────────────────┬─────────────────────────────────┐
│ Timestamp            │ Source NID           │ Message                         │
├──────────────────────┼──────────────────────┼─────────────────────────────────┤
│ 2026-01-02 14:32:15  │ 9d4df1cf-0b47-...    │ Hello Sink!                     │
│ 2026-01-02 14:32:20  │ 9d4df1cf-0b47-...    │ Temperature: 23.5C              │
│ 2026-01-02 14:32:45  │ a1b2c3d4-5e6f-...    │ Sensor data update              │
└──────────────────────┴──────────────────────┴─────────────────────────────────┘

 Total no inbox: 3 mensagem(ns)

# Ver mais mensagens
sink> inbox 50

# Mensagens são enviadas pelos Nodes usando o comando 'send'
```

## Dicas e Tricks

### 1. Auto-complete
Use Tab para auto-completar comandos (depende do terminal).

### 2. Histórico de Comandos
Use ↑ e ↓ para navegar pelo histórico de comandos.

### 3. Limpar Tela
Use `clear` ou Ctrl+L para limpar a tela.

### 4. Sair Rapidamente
- `exit` ou `quit`
- Ctrl+D
- Ctrl+C (interrompe e para o dispositivo)

### 5. Ver Ajuda de um Comando
```bash
sink> help status
sink> help send
```

### 6. Monitorar Logs em Paralelo
```bash
# Terminal 1 - Sink interactive
./iot-sink interactive hci0

# Terminal 2 - Logs
./iot-sink logs --follow

# Terminal 3 - Node interactive
./iot-node interactive
```

## Troubleshooting

### Problema: "Nenhum certificado encontrado"
**Solução**: Verifique que os certificados estão em `certs/`:
```bash
ls -la certs/ | grep -E "(sink|node|ca)"
```

### Problema: Node não conecta ao Sink
**Verificar**:
1. Sink está running? (`sink> status`)
2. Adapter BLE correto?
3. Fazer `node> scan` para verificar se vê o Sink

### Problema: "Falha na autenticação"
**Verificar**:
1. Certificados são válidos?
2. CA certificate é o mesmo para Sink e Node?
3. Ver logs: `./iot-sink logs --grep auth`

### Problema: Heartbeats não recebidos
**Verificar**:
1. `node> uplink` - está conectado?
2. `sink> heartbeat_stats` - Sink está enviando?
3. Ver tempo desde último: `node> status`

## Comparação: Normal vs Interactive

| Aspecto | Modo Normal | Modo Interativo |
|---------|-------------|-----------------|
| **Uso** | Produção, automático | Debug, testes |
| **Controle** | Automático | Manual |
| **Visibilidade** | Logs | Status em tempo real |
| **Flexibilidade** | Fixo | Comandos dinâmicos |
| **Performance** | Otimizado | Overhead do CLI |

## Comandos Implementados vs Planejados

### Sink

| Comando | Status | Notas |
|---------|--------|-------|
| `status` |  Implementado | Mostra tudo |
| `downlinks` |  Implementado | Lista nodes |
| `heartbeat_stats` |  Implementado | Stats de HB |
| `inbox` |  Implementado | Mostra mensagens recebidas |
| `send` | ️ Parcial | Base pronta, falta envio real |
| `broadcast` | ️ Parcial | Base pronta, falta envio real |
| `session_keys` |  Implementado | Lista keys |
| `my_nid` |  Implementado | Mostra NID |

### Node

| Comando | Status | Notas |
|---------|--------|-------|
| `scan` |  Implementado | Procura uplinks |
| `connect` |  Implementado | Conecta + auth |
| `disconnect` |  Implementado | Desconecta |
| `reconnect` |  Implementado | Força reconexão |
| `status` |  Implementado | Status completo |
| `uplink` |  Implementado | Detalhes uplink |
| `downlinks` |  Implementado | Lista downlinks |
| `send` |  Implementado | Envia mensagens |
| `ping` |  Implementado | Pinga o Sink |
| `my_nid` |  Implementado | Mostra NID |

## Próximos Passos

- [ ] Implementar envio real de mensagens no Sink
- [ ] Adicionar comando `routes` para ver forwarding table
- [ ] Adicionar comando `neighbors` no Node
- [ ] Melhorar output com cores (termcolor)
- [ ] Adicionar comando `inspect <nid>` para debug profundo
- [ ] Tab completion para NIDs
- [ ] Histórico persistente
