# Interface de Linha de Comando (CLI)

## 📌 Visão Geral

O projeto fornece CLIs dedicados para controlar o Sink e o Node de forma independente.

```
./iot-sink     # CLI para o Sink Device
./iot-node     # CLI para o Node Device
```

## 🚀 CLI do Sink (`./iot-sink`)

### Comandos Disponíveis

#### `start` - Iniciar o Sink
```bash
./iot-sink start
```
Inicia o Sink Device e aguarda conexões de Nodes.

**O que faz:**
- Inicializa certificados X.509
- Configura GATT Server BLE
- Inicia advertising
- Envia heartbeats a cada 5 segundos
- Aceita autenticações de Nodes

---

#### `logs` - Visualizar Logs

**Ver últimos logs (padrão: 50 linhas)**
```bash
./iot-sink logs
```

**Ver últimas N linhas**
```bash
./iot-sink logs --tail 100
```

**Seguir logs em tempo real**
```bash
./iot-sink logs --follow
./iot-sink logs -f
```

**Filtrar logs por padrão**
```bash
./iot-sink logs --grep heartbeat
./iot-sink logs --grep "autenticação"
./iot-sink logs --grep "Session key"
```

---

#### `status` - Verificar Status
```bash
./iot-sink status
```

Mostra:
- Status do serviço
- Últimas atividades (conexões, autenticações)
- Heartbeats enviados

---

## 🌐 CLI do Node (`./iot-node`)

### Comandos Disponíveis

#### `start` - Iniciar o Node
```bash
./iot-node start
```
Inicia o Node Device em modo dual (client + server).

**O que faz:**
- Procura Sink via BLE scan
- Conecta ao Sink via GATT
- Autentica com certificados X.509
- Deriva session key via ECDH
- Recebe e verifica heartbeats
- Funciona como gateway (aceita downlinks)

---

#### `logs` - Visualizar Logs

**Ver últimos logs (padrão: 50 linhas)**
```bash
./iot-node logs
```

**Ver últimas N linhas**
```bash
./iot-node logs --tail 200
```

**Seguir logs em tempo real**
```bash
./iot-node logs --follow
./iot-node logs -f
```

**Filtrar logs por padrão**
```bash
./iot-node logs --grep "Sink encontrado"
./iot-node logs --grep authentication
./iot-node logs --grep "💓"
```

---

#### `status` - Verificar Status
```bash
./iot-node status
```

Mostra:
- Status da conexão com Sink
- Estado de autenticação
- Últimos heartbeats recebidos
- Session key ativa

---

#### `send` - Enviar Mensagem ⚠️ (Futuro)
```bash
./iot-node send "Hello Sink"
```

**Nota:** Funcionalidade planejada para envio de mensagens DATA.

---

## 📖 Exemplos de Uso

### Cenário 1: Teste Básico
```bash
# Terminal 1: Iniciar Sink
./iot-sink start

# Terminal 2: Iniciar Node
./iot-node start

# Terminal 3: Monitorar logs
./iot-sink logs -f
```

### Cenário 2: Debug de Autenticação
```bash
# Ver processo de autenticação no Node
./iot-node logs --grep "autenticação|certificado|Session key"

# Ver no Sink
./iot-sink logs --grep "AUTH|challenge|response"
```

### Cenário 3: Monitorar Heartbeats
```bash
# Ver heartbeats enviados (Sink)
./iot-sink logs --grep "Heartbeat enviado"

# Ver heartbeats recebidos (Node)
./iot-node logs --grep "Heartbeat recebido"
```

### Cenário 4: Verificar Assinaturas Digitais
```bash
# Ver assinaturas no Sink
./iot-sink logs --grep "assinado"

# Ver verificações no Node
./iot-node logs --grep "assinatura"
```

---

## 🔍 Dicas de Troubleshooting

### Sink não inicia
```bash
# Verificar certificados
ls -lh certs/

# Ver logs de erro
./iot-sink logs --tail 50
```

### Node não conecta ao Sink
```bash
# Verificar se Sink está ativo
./iot-sink status

# Ver se Node encontrou o Sink
./iot-node logs --grep "Sink encontrado"

# Verificar Bluetooth
sudo systemctl status bluetooth
hciconfig hci0 up
```

### Autenticação falhando
```bash
# Ver detalhes no Node
./iot-node logs --grep "AUTH|certificado" --tail 100

# Ver detalhes no Sink
./iot-sink logs --grep "AUTH|certificado" --tail 100
```

### Heartbeats não chegam
```bash
# Verificar envio (Sink)
./iot-sink logs --grep "Heartbeat enviado" --tail 10

# Verificar recepção (Node)
./iot-node logs --grep "Heartbeat\|MAC\|assinatura" --tail 20
```

---

## 🎯 Atalhos Úteis

### Limpar logs
```bash
> logs/iot-network.log
```

### Ver apenas erros
```bash
./iot-sink logs --grep "ERROR\|❌"
./iot-node logs --grep "ERROR\|❌"
```

### Ver métricas de sucesso
```bash
# Contar autenticações bem-sucedidas
./iot-node logs | grep -c "Autenticação bem-sucedida"

# Contar heartbeats recebidos
./iot-node logs | grep -c "Heartbeat recebido"
```

---

## 📝 Notas

- Os CLIs usam o mesmo arquivo de log: `logs/iot-network.log`
- Use `Ctrl+C` para parar qualquer comando
- Logs em tempo real (`--follow`) podem ser parados com `Ctrl+C`
- Filtros (`--grep`) são case-insensitive
- Use aspas para padrões com espaços: `--grep "Session key"`
