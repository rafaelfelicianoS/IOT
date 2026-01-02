# Guia de Utilização - IoT Network

## Auto-Detecção de Certificados

Os scripts CLI agora detectam automaticamente os certificados no diretório `certs/`.

### Estrutura Esperada

```
certs/
├── ca_certificate.pem          # Certificado da CA (obrigatório)
├── sink_*_cert.pem             # Certificados do Sink
├── sink_*_key.pem              # Chaves privadas do Sink
├── node_*_cert.pem             # Certificados dos Nodes
└── node_*_key.pem              # Chaves privadas dos Nodes
```

## Iniciar o Sink

### Modo Normal (sem CLI interativo)

**Uso básico (detecta certificados automaticamente):**
```bash
./iot-sink start hci0
```

### Modo Interativo (com CLI de debug)

**Inicia o Sink com um CLI interativo:**
```bash
./iot-sink interactive hci0
```

Neste modo, você pode:
- `status` - Ver status do Sink (downlinks, heartbeats)
- `downlinks` - Listar Nodes conectados
- `send <nid_prefix> <msg>` - Enviar mensagem para um Node
- `broadcast <msg>` - Enviar mensagem para todos os Nodes
- `session_keys` - Ver session keys estabelecidas
- `my_nid` - Ver o NID do Sink
- `help` - Ver todos os comandos
- `exit` - Sair e parar o Sink

**Com múltiplos certificados:**
```bash
# Lista os certificados disponíveis e usa o primeiro
./iot-sink start hci0

# Usa um certificado específico (índice começa em 1)
./iot-sink start hci0 --cert-index 2
```

**O que acontece:**
1. Procura certificados `sink_*_cert.pem` e `sink_*_key.pem` em `certs/`
2. Procura `ca_certificate.pem` em `certs/`
3. Se encontrar múltiplos certificados, mostra a lista
4. Usa o primeiro certificado (ou o especificado com `--cert-index`)
5. Inicia o Sink no adaptador especificado

## Iniciar um Node

### Modo Normal (automático)

**Uso básico (detecta certificados automaticamente):**
```bash
./iot-node start
```

### Modo Interativo (com CLI de debug)

**Inicia o Node com um CLI interativo:**
```bash
./iot-node interactive
```

Neste modo, você pode:
- `scan [timeout]` - Procurar Sinks/Nodes disponíveis
- `connect` - Conectar ao uplink descoberto
- `disconnect` - Desconectar do uplink
- `reconnect` - Reconectar ao uplink
- `send <msg>` - Enviar mensagem ao Sink
- `ping [count]` - Pingar o Sink e medir latência
- `status` - Ver status completo (uplink, downlinks, hop count)
- `uplink` - Ver detalhes do uplink
- `downlinks` - Listar Nodes conectados abaixo
- `my_nid` - Ver o NID do Node
- `help` - Ver todos os comandos
- `exit` - Sair e parar o Node

**Com adaptador específico:**
```bash
# Usa hci1 em vez de hci0
./iot-node start --adapter 1
```

**Com múltiplos certificados:**
```bash
# Usa um certificado específico
./iot-node start --cert-index 2
```

**O que acontece:**
1. Procura certificados `node_*_cert.pem` e `node_*_key.pem` em `certs/`
2. Procura `ca_certificate.pem` em `certs/`
3. Se encontrar múltiplos certificados, mostra a lista
4. Usa o primeiro certificado (ou o especificado com `--cert-index`)
5. Inicia o Node no adaptador especificado (padrão: hci0)

## Outros Comandos

### Ver Logs
```bash
# Sink
./iot-sink logs                  # Últimas 50 linhas
./iot-sink logs --tail 100       # Últimas 100 linhas
./iot-sink logs --follow         # Seguir em tempo real
./iot-sink logs --grep heartbeat # Filtrar por padrão

# Node
./iot-node logs                  # Últimas 50 linhas
./iot-node logs --follow         # Seguir em tempo real
```

### Verificar Status
```bash
./iot-sink status
./iot-node status
```

## Exemplos Completos

### Cenário 1: Um Sink e um Node (Modo Normal)
```bash
# Terminal 1 - Sink
./iot-sink start hci0

# Terminal 2 - Node
./iot-node start
```

### Cenário 2: Um Sink e um Node (Modo Interativo para Debug)
```bash
# Terminal 1 - Sink interativo
./iot-sink interactive hci0
# Depois de iniciar:
sink> status           # Ver status
sink> downlinks        # Ver nodes conectados

# Terminal 2 - Node interativo
./iot-node interactive
# Depois de iniciar:
node> scan             # Procurar Sink
node> connect          # Conectar ao Sink
node> status           # Ver status da conexão
node> send Hello!      # Enviar mensagem
node> ping 5           # Pingar o Sink 5 vezes
```

### Cenário 3: Múltiplos Sinks (diferentes adaptadores)
```bash
# Terminal 1 - Sink 1 em hci0
./iot-sink start hci0 --cert-index 1

# Terminal 2 - Sink 2 em hci1
./iot-sink start hci1 --cert-index 2
```

### Cenário 4: Monitorização de Logs
```bash
# Terminal 1 - Iniciar Sink
./iot-sink start hci0

# Terminal 2 - Seguir logs
./iot-sink logs --follow
```

## Resolução de Problemas

### Erro: "Nenhum certificado encontrado"
- Verifique que os certificados existem em `certs/`
- Certifique-se que seguem o padrão de nomenclatura:
  - Sink: `sink_*_cert.pem` e `sink_*_key.pem`
  - Node: `node_*_cert.pem` e `node_*_key.pem`
  - CA: `ca_certificate.pem`

### Erro: "Certificado CA não encontrado"
- Verifique que existe `certs/ca_certificate.pem`

### Múltiplos certificados - qual usar?
- Execute o comando sem `--cert-index` para ver a lista
- Use `--cert-index N` para escolher (N começa em 1)

## Vantagens

### Auto-Detecção de Certificados
✅ **Simplicidade**: Apenas especifique o adaptador BLE
✅ **Flexibilidade**: Suporta múltiplos certificados
✅ **Segurança**: Certificados organizados em um único diretório
✅ **Sem erros**: Não é preciso lembrar os caminhos completos

### CLI Interativo
✅ **Debug fácil**: Controle manual completo
✅ **Teste rápido**: Scan, connect, send sem restartar
✅ **Visibilidade**: Status em tempo real
✅ **Comandos simples**: Interface amigável tipo shell

## Migração do Método Antigo

**Antes (especificando todos os caminhos):**
```bash
python3 sink/sink_device.py hci0 \
  --cert certs/sink_af04ea89_cert.pem \
  --key certs/sink_af04ea89_key.pem \
  --ca-cert certs/ca_certificate.pem
```

**Agora (auto-detecção):**
```bash
./iot-sink start hci0
```
