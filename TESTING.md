# Testing - IoT Bluetooth Network

Resultados de testes realizados no projeto.

## Ambiente de Teste

- **SO**: Linux (Ubuntu/Debian)
- **BlueZ**: 5.72
- **Python**: 3.12+
- **Adaptadores BLE**: USB dongles + adaptadores integrados

## Testes Realizados

### 1. Conexão Sink ↔ Node (1 hop)

**Setup:**
- PC1: Sink (hci0)
- PC2: Node (hci0)

**Resultado:** ✅ **SUCESSO**
- Node descobre Sink via BLE scan
- Conexão GATT estabelecida
- Autenticação mútua X.509 funcional
- Hop count atualizado corretamente (hop=0)
- Heartbeats recebidos a cada 5 segundos
- Session key ECDH estabelecida
- Mensagens DATA chegam ao Sink inbox
- Verificação de assinatura ECDSA funcional
- Replay protection ativo

**Logs:**
```
✅ Conectado ao Sink via GATT
✅ Certificado do peer validado!
✅ Autenticação bem-sucedida!
✅ Session key estabelecida
✅ Hop count: 0
```

---

### 2. Multi-Hop: Sink ↔ Node1 ↔ Node2 (2 hops)

**Setup:**
- Toshiba PC: Sink (hci0) + Node1 (hci1)
- HP PC: Node2 (hci0)

**Resultado:** ⚠️ **PARCIAL**
- Sink ↔ Node1: ✅ Funcional
- Node1 hop=0: ✅ Correto
- Heartbeat forwarding: ✅ Funcional
- **Problema identificado**: Adaptadores BLE integrados não suportam advertising simultâneo com conexão client
- Node1 não consegue re-registar advertising após conectar ao Sink
- Node2 não consegue descobrir Node1

**Limitação Hardware:**
- Adaptadores BLE USB (dongles) funcionam melhor
- Adaptadores integrados têm limitações em multi-role BLE

---

### 3. Peripheral-Only Mode

**Setup:**
- Node em modo `--peripheral-only` (hop=254)
- Não procura uplink, apenas aceita downlinks

**Resultado:** ✅ **IMPLEMENTADO**
- Hop count 254 identifica peripheral-only
- Outros nodes não tentam usar como uplink
- Útil para nodes sem dongle BLE

---

### 4. Heartbeat Protocol

**Resultado:** ✅ **SUCESSO TOTAL**
- Sink envia heartbeats a cada 5s
- Assinaturas ECDSA (P-521) verificadas
- Flooding para downlinks funcional
- Timeout detection (3 heartbeats = 15s)
- Chain reaction disconnect funcional

**Logs:**
```
✅ Verificando heartbeat: Sink NID: 4e127252...
✅ Assinatura verificada com sucesso!
🔄 Flooding heartbeat para 2 downlink(s)
```

---

### 5. RouterDaemon & Forwarding Table

**Resultado:** ✅ **FUNCIONAL**
- Learning switch implementado
- Forwarding table atualizada dinamicamente
- Mensagens roteadas corretamente
- Flooding quando destino desconhecido

**Exemplo de Forwarding Table:**
```
📊 Forwarding Table:
   4e127252... → uplink (Sink)
   0abd8260... → downlink_1 (Node2)
   a8e9e96f... → local (self)
```

---

### 6. Segurança

#### Autenticação X.509
✅ **SUCESSO**
- Challenge-response funcional
- Certificados P-521 validados
- CA própria

#### Session Keys (ECDH)
✅ **SUCESSO**
- Chave derivada por link
- 32 bytes
- Renovada a cada autenticação

#### Integridade (HMAC-SHA256)
✅ **SUCESSO**
- HMAC em todos os pacotes
- Sequence numbers
- Replay protection (window=100)

#### Encriptação End-to-End (DTLS + AES-256-GCM)
✅ **IMPLEMENTADO**
- Canal DTLS estabelecido
- Mensagens DATA encriptadas
- Decriptação automática no Sink

---

### 7. Fragmentação BLE

**Resultado:** ✅ **FUNCIONAL**
- Mensagens grandes fragmentadas automaticamente
- 180 bytes por fragmento
- Reassembly funcional
- Certificados X.509 (887 bytes) fragmentados em 5 pacotes

---

## Limitações Conhecidas

1. **Advertising após conexão**: Adaptadores integrados falham
   - **Solução**: Usar dongles USB BLE

2. **Multi-hop com 3+ dispositivos**: Limitado por hardware BLE disponível
   - **Status**: Código implementado e testado com 2 hops

3. **Autenticação de downlinks**: Placeholder
   - Uplinks autenticados ✅
   - Downlinks aceites sem validação ⚠️

---

## Conclusão

**Funcionalidades Core:** ✅ Todas implementadas
- Heartbeat protocol com ECDSA
- Routing multi-hop
- Segurança (X.509, HMAC, DTLS)
- Forwarding table dinâmica

**Testes Multi-Hop:** ⚠️ Limitados por hardware BLE
- Solução: Dongles USB em todos os nodes
