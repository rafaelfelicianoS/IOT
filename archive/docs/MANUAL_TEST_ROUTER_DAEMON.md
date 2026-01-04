#  Manual Testing Guide - Router Daemon Multi-Hop

## Guia Completo de Teste Manual do Router Daemon

Este guia fornece instruções passo-a-passo para testar manualmente o Router Daemon com topologia multi-hop real.

---

##  Pré-Requisitos

### Hardware Necessário

**Cenário Mínimo (2-Hop):**
- 3 PCs com Bluetooth LE (ou 1 PC com 3 adaptadores BLE USB)
- Adaptadores: hci0, hci1, hci2

**Cenário Completo (3-Hop):**
- 4 PCs com Bluetooth LE
- Adaptadores: hci0, hci1, hci2, hci3

### Software

```bash
# Em cada PC, verificar:
python3 --version  # >= 3.8
bluetoothctl --version  # BlueZ 5.50+

# Verificar adaptadores BLE disponíveis
hciconfig
```

### Preparação do Branch

```bash
# Em cada PC, clonar e fazer checkout
git clone <repo-url>
cd iot
git checkout feature/router-daemon

# Instalar dependências
./install_deps.sh

# OU manualmente:
pip install -r requirements.txt
```

---

##  Teste 1: Multi-Hop 2-Hop (Node A → Node B → Sink)

### Topologia

```
    PC3 (Node A)
         │
         │ BLE
         ↓
    PC2 (Node B)
         │
         │ BLE
         ↓
    PC1 (Sink)
```

### Passo 1: Iniciar Sink (PC1)

```bash
# Terminal 1 - PC1
cd iot
./iot-sink interactive hci0
```

**Verificar output:**
```
╔═══════════════════════════════════════════════════════════════╗
║              IoT Sink - Interactive CLI                      ║
╚═══════════════════════════════════════════════════════════════╝

[INFO] Sink NID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
[INFO]  GATT Server registado
[INFO]  Advertisement ativo
[INFO]  Heartbeat service iniciado
[INFO]  Router Daemon integrado

sink> _
```

 **Checkpoint**: Sink está ativo e broadcasting

### Passo 2: Iniciar Node B (PC2) - Intermediário

```bash
# Terminal 1 - PC2
cd iot
./iot-node interactive hci1
```

**Aguardar inicialização:**
```
[INFO] Node NID: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
[INFO]  GATT Server ativo
[INFO]  Router Daemon integrado
```

**Conectar ao Sink:**
```bash
node> scan 10
```

**Verificar output:**
```
 Encontrados 1 dispositivo(s):

  1. XX:XX:XX:XX:XX:XX    | Type: Sink | Hop: 0   | RSSI: -XX dBm

 Use 'connect <número>' para conectar
```

**Conectar:**
```bash
node> connect 1
```

**Aguardar autenticação:**
```
 A conectar a XX:XX:XX:XX:XX:XX...
 Conectado via GATT
 A autenticar...
[INFO]  Session key estabelecida
[INFO]  Session key configurada no Router Daemon
[INFO]  Certificado do Sink verificado
 Autenticado com sucesso!
 Hop count: 0
```

 **Checkpoint**: Node B conectado ao Sink (hop=0)

### Passo 3: Verificar Router Daemon no Node B

```bash
# Em PC2
node> status
```

**Verificar secção:**
```
 UPLINK:
   Status:  Conectado
   NID: <Sink_NID>
   Address: XX:XX:XX:XX:XX:XX
   Authenticated: 
   Meu hop: 0

 ROUTER DAEMON:
   Packets routed: 0
   Packets delivered: 0
   Messages via uplink: 0
```

 **Checkpoint**: Router Daemon ativo no Node B

### Passo 4: Iniciar Node A (PC3) - Cliente Final

```bash
# Terminal 1 - PC3
cd iot
./iot-node interactive hci2
```

**Scan para dispositivos:**
```bash
node> scan 10
```

**IMPORTANTE**: Deves ver **Node B** (não o Sink):
```
 Encontrados 1 dispositivo(s):

  1. YY:YY:YY:YY:YY:YY    | Type: Node | Hop: 0   | RSSI: -XX dBm
```

**Conectar ao Node B:**
```bash
node> connect 1
```

**Aguardar autenticação:**
```
 Conectado via GATT
 Autenticado com sucesso!
 Hop count: 1  ← Node A está a 1 hop do Sink (via Node B)
```

 **Checkpoint**: Node A conectado ao Node B (hop=1)

### Passo 5: TESTE CRÍTICO - Enviar Mensagem Multi-Hop

**Em Node A (PC3):**
```bash
node> send Hello from Node A! This goes through Node B to reach Sink.
```

**Verificar output em Node A:**
```
[INFO]  Payload encriptado end-to-end: 63 → 91 bytes
[INFO]  Mensagem enviada
```

**Verificar logs em Node B (PC2):**
```
[INFO]  Pacote recebido de downlink: <NodeA_NID> → <Sink_NID>
[INFO]  Forwarded: <NodeA_NID> → <Sink_NID> via uplink (ttl=7)
```

**Verificar no Sink (PC1):**
```bash
sink> inbox
```

**Deve aparecer:**
```
 INBOX - MENSAGENS RECEBIDAS

┌─────────────────────┬────────────────────┬──────────────────────────────────┐
│ Timestamp           │ From               │ Message                          │
├─────────────────────┼────────────────────┼──────────────────────────────────┤
│ 2026-01-03 18:XX:XX │ <NodeA_NID>        │ Hello from Node A! This goes...  │
└─────────────────────┴────────────────────┴──────────────────────────────────┘
```

 **SUCESSO**: Mensagem atravessou 2 hops!
- Node A → Node B (forwarded pelo router daemon)
- Node B → Sink (entregue localmente)

---

##  Teste 2: Multi-Hop 3-Hop (Node A → Node B → Node C → Sink)

### Topologia

```
    PC4 (Node A)
         │
         ↓
    PC3 (Node B)
         │
         ↓
    PC2 (Node C)
         │
         ↓
    PC1 (Sink)
```

### Passos

1. **Sink** (PC1): `./iot-sink interactive hci0`
2. **Node C** (PC2): Conectar ao Sink (hop=0)
3. **Node B** (PC3): Conectar ao Node C (hop=1)
4. **Node A** (PC4): Conectar ao Node B (hop=2)

### Teste

**Em Node A:**
```bash
node> send 3-hop test message!
```

**Verificar forwarding:**
- **Node B logs**: ` Forwarded: NodeA → Sink via uplink`
- **Node C logs**: ` Forwarded: NodeA → Sink via uplink`
- **Sink inbox**: Mensagem aparece!

 **SUCESSO**: Mensagem atravessou 3 hops!

---

##  Teste 3: Heartbeat Forwarding Multi-Hop

### Objetivo

Verificar que heartbeats do Sink são propagados por toda a árvore.

### Procedimento

**Topologia: Node A → Node B → Sink**

**Monitorizar logs em Node A:**
```bash
# Em terminal separado (PC3)
tail -f logs/iot-network.log | grep -i heartbeat
```

**Deve ver (a cada ~5s):**
```
[INFO]  Heartbeat recebido (seq=X, age=Y.YYs)
[INFO]  Assinatura de heartbeat válida
```

**Verificar em Node B:**
```bash
node> status
```

**Ver:**
```
 HEARTBEATS:
   Último recebido: 2.3s atrás
   Sequência: 42
```

 **SUCESSO**: Heartbeats propagam por toda a árvore

---

##  Teste 4: Forwarding Table Learning

### Objetivo

Verificar que router daemon aprende rotas dinamicamente.

### Procedimento

**No Node B (intermediário):**

1. **Antes** de Node A enviar mensagem:
```bash
node> status
# Forwarding table vazia ou só com Sink
```

2. **Node A envia mensagem**
3. **Depois** em Node B:
```bash
node> status
```

**Deve mostrar:**
```
 FORWARDING TABLE:
   <Sink_NID>... → uplink
   <NodeA_NID>... → downlink
```

 **SUCESSO**: Router aprendeu rota de retorno para Node A!

---

##  Teste 5: TTL Decrementation

### Objetivo

Verificar que TTL é decrementado a cada hop.

### Procedimento

**Modificar código temporariamente** (apenas para teste):

```python
# Em common/network/packet.py, linha ~80
TTL_DEFAULT = 2  # APENAS PARA TESTE (original é 8)
```

**Topologia: Node A → Node B → Node C → Sink**

**Enviar de Node A:**
```bash
node> send TTL test
```

**Resultado esperado:**
- TTL inicial: 2
- Após Node B: TTL=1 (forwarded)
- Após Node C: TTL=0 (**DESCARTADO**)
- **Sink NÃO recebe a mensagem**

**Verificar logs em Node C:**
```
[WARN] ️  Pacote descartado - TTL expirou
```

 **SUCESSO**: TTL gerido corretamente

**IMPORTANTE**: Reverter mudança após teste!

---

##  Teste 6: Chain Reaction Disconnect

### Objetivo

Verificar que ao perder uplink, downlinks são desconectados em cascata.

### Procedimento

**Topologia: Node A → Node B → Sink**

**No Sink:**
```bash
sink> downlinks
# Ver Node B conectado

sink> stop_heartbeat <NodeB_NID>
# Simula falha de link com Node B
```

**Aguardar ~15s (3 × 5s heartbeat interval)**

**Verificar Node B:**
```
[ERROR]  Timeout de heartbeat! Sem heartbeat há 15.Xs
[WARN] ️  Desconectando do uplink devido a timeout
[WARN]  Chain Reaction Disconnect: desconectando 1 downlink(s)
```

**Verificar Node A:**
```
[WARN] ️  Conexão perdida com uplink
[WARN]  Chain Reaction Disconnect
```

 **SUCESSO**: Chain reaction funcionou!

---

##  Teste 7: End-to-End Encryption Multi-Hop

### Objetivo

Verificar que payload permanece encriptado durante forwarding.

### Procedimento

**Monitorizar logs em Node B:**
```bash
tail -f logs/iot-network.log | grep -E "encript|desencript|wrap|unwrap"
```

**Node A envia:**
```bash
node> send Secret message!
```

**Logs de Node A:**
```
[INFO]  Payload encriptado end-to-end: 15 → 43 bytes
```

**Logs de Node B (ROUTER):**
```
[INFO]  Pacote recebido de downlink
[INFO]  Forwarded: NodeA → Sink via uplink
```

**IMPORTANTE**: Node B **NÃO** deve mostrar "desencriptado" ou payload em claro!

**Logs do Sink:**
```
[INFO]  DATA recebido (local): NodeA → Sink
[INFO]  Payload desencriptado end-to-end: 43 → 15 bytes
[INFO]  Mensagem: "Secret message!"
```

 **SUCESSO**: End-to-end encryption preservado!

---

##  Checklist de Testes

Use esta checklist para garantir que todos os testes passaram:

- [ ] **Teste 1**: Multi-hop 2-hop funciona
- [ ] **Teste 2**: Multi-hop 3-hop funciona
- [ ] **Teste 3**: Heartbeats propagam
- [ ] **Teste 4**: Forwarding table aprende rotas
- [ ] **Teste 5**: TTL decrementation funciona
- [ ] **Teste 6**: Chain reaction disconnect funciona
- [ ] **Teste 7**: End-to-end encryption preservado

---

##  Troubleshooting

### Problema: Node não vê dispositivos no scan

**Causa**: Adaptadores BLE desconfigurados

**Solução**:
```bash
sudo btmgmt -i hci0 power off
sudo btmgmt -i hci0 bredr off
sudo btmgmt -i hci0 le on
sudo btmgmt -i hci0 power on
```

### Problema: "MAC inválido" nos logs

**Causa**: Session keys não configuradas corretamente

**Verificar**:
1. Autenticação completou?
2. ` Session key configurada no Router Daemon` apareceu nos logs?

**Solução**: Reconectar dispositivo

### Problema: Packets não são forwarded

**Causa**: Send callback não configurado ou forwarding table vazia

**Verificar logs**:
```bash
grep -i "send callback\|forwarding table" logs/iot-network.log
```

**Solução**: Reiniciar Node intermediário

### Problema: Mensagem não chega ao Sink

**Debug passo-a-passo**:

1. **Em Node A**: Mensagem foi enviada?
   ```
   grep "Mensagem enviada" logs/iot-network.log
   ```

2. **Em Node B**: Packet foi recebido e forwarded?
   ```
   grep "Forwarded.*NodeA" logs/iot-network.log
   ```

3. **No Sink**: DATA recebido?
   ```
   grep "DATA recebido.*NodeA" logs/iot-network.log
   ```

Se falhar em qualquer passo, verificar logs desse dispositivo.

---

##  Screenshots Recomendados

Para documentação/apresentação, capturar:

1. **Topologia**: Diagrama mostrando Sink → Node B → Node A
2. **Node A**: Comando `send` e confirmação
3. **Node B**: Logs mostrando ` Forwarded`
4. **Sink**: `inbox` mostrando mensagem recebida
5. **Forwarding Table**: `status` em Node B mostrando rotas aprendidas

---

##  Demonstração para Professor

### Script Recomendado (5 minutos)

```bash
# 1. Mostrar topologia (30s)
echo "Topologia: Node A (hop=1) → Node B (hop=0) → Sink"

# 2. Mostrar status de cada dispositivo (1 min)
# Em cada terminal, executar: node> status (ou sink> status)

# 3. Enviar mensagem multi-hop (1 min)
# Node A: node> send Demo message via multi-hop!

# 4. Mostrar forwarding em Node B (1 min)
# Mostrar logs: tail logs/iot-network.log | grep Forwarded

# 5. Mostrar inbox no Sink (1 min)
# sink> inbox

# 6. Explicar Router Daemon (1.5 min)
# - Serviço separado (Secção 5.7 )
# - Forwarding tables (learning switch)
# - Per-link MACs
# - TTL management
```

---

##  Critérios de Sucesso

**O teste manual é considerado bem-sucedido se:**

1.  Mensagem enviada de Node A chega ao Sink
2.  Logs mostram forwarding explícito em nós intermediários
3.  Forwarding table aprende rotas dinamicamente
4.  Heartbeats propagam por toda a árvore
5.  End-to-end encryption preservado (payload em claro só no Sink)
6.  Chain reaction disconnect funciona
7.  Sem erros "MAC inválido" ou "Replay attack"

---

##  Relatório de Testes

Após completar os testes, preencher:

```markdown
# Relatório de Testes Manuais - Router Daemon

**Data**: ___/___/______
**Testador**: _______________
**Branch**: feature/router-daemon
**Commit**: 9b9d3e5

## Resultados

| Teste | Status | Observações |
|-------|--------|-------------|
| Multi-hop 2-hop |  /  | |
| Multi-hop 3-hop |  /  | |
| Heartbeat forwarding |  /  | |
| Forwarding table |  /  | |
| TTL decrementation |  /  | |
| Chain reaction |  /  | |
| E2E encryption |  /  | |

## Bugs Encontrados

1.
2.
3.

## Conclusão

[ ]  Aprovado para merge
[ ]  Requer correções
```

---

**Boa sorte com os testes!** 

Se encontrarem problemas, consultar:
- [ROUTER_DAEMON_IMPLEMENTATION.md](ROUTER_DAEMON_IMPLEMENTATION.md) - Documentação técnica
- [Logs do projeto](logs/iot-network.log) - Debug detalhado
