# HEARTBEAT MAC Verification Fix

## 🔴 Problema Identificado

Após implementação do Router Daemon, os heartbeats do Sink **não eram recebidos** pelos Nodes.

### Root Cause

**Incompatibilidade de chaves MAC**:

1. **Sink** envia heartbeats usando `create_heartbeat_packet()` → MAC calculado com `DEFAULT_HMAC_KEY`
2. **Router Daemon** do Node recebe → Espera MAC calculado com **session key ECDH** (negociada durante autenticação)
3. **Resultado**: Verificação MAC **SEMPRE FALHA** ❌

### Evidência nos Logs

```
2026-01-03 18:19:33.537 | INFO | 🔀 Session key configurada no Router Daemon
2026-01-03 18:19:36.620 | ERROR | ❌ MAC verification failed for packet from uplink
   Source: 54c225f2... (Sink)
   Dest: 54c225f2... (Broadcast)
   Type: MessageType(2) (HEARTBEAT)
   Seq: 29
```

### Fluxo do Bug

```
SINK (sink_device.py:447-474)
  ↓
  create_heartbeat_packet()
  ↓
  packet.calculate_and_set_mac()  ← Usa DEFAULT_HMAC_KEY
  ↓
  notify_packet(heartbeat_packet.to_bytes())

NODE Router Daemon (router_daemon.py:200-227)
  ↓
  receive_packet("uplink", packet_bytes)
  ↓
  _verify_packet_mac(packet, "uplink")
  ↓
  session_key = self.session_keys.get("uplink")  ← ECDH session key
  ↓
  verify_hmac(mac_data, packet.mac, session_key)  ← FALHA! ❌
```

---

## ✅ Solução Implementada (Opção B)

### Abordagem

**HEARTBEAT packets usam DEFAULT_HMAC_KEY (broadcast)**
- Autenticidade garantida por **ECDSA P-521 signature** dentro do payload
- DEFAULT_HMAC_KEY protege contra corrupção de rede

**DATA packets usam session key ECDH (unicast)**
- Segurança end-to-end com chave negociada
- Confidencialidade e autenticidade

### Mudanças em `router_daemon.py`

#### 1. Import DEFAULT_HMAC_KEY
```python
from common.security.crypto import calculate_hmac, verify_hmac, DEFAULT_HMAC_KEY
```

#### 2. `_verify_packet_mac()` - Lógica Dual
```python
def _verify_packet_mac(self, packet: Packet, port_id: str) -> bool:
    """
    HEARTBEAT packets usam DEFAULT_HMAC_KEY (autenticidade garantida por ECDSA signature).
    DATA packets usam session key ECDH negociada durante autenticação.
    """
    mac_data = (...)

    # HEARTBEAT = DEFAULT_HMAC_KEY
    if packet.msg_type == MessageType.HEARTBEAT:
        is_valid = verify_hmac(mac_data, packet.mac, DEFAULT_HMAC_KEY)
        return is_valid

    # DATA = session key
    session_key = self.session_keys.get(port_id)
    if not session_key:
        return False

    is_valid = verify_hmac(mac_data, packet.mac, session_key)
    return is_valid
```

#### 3. `_forward_packet()` - Recalcula MAC Corretamente
```python
def _forward_packet(self, packet: Packet, incoming_port: str):
    """Forward packet with correct MAC for outgoing port."""

    mac_data = (...)

    # HEARTBEAT = DEFAULT_HMAC_KEY
    if packet.msg_type == MessageType.HEARTBEAT:
        packet.mac = calculate_hmac(mac_data, DEFAULT_HMAC_KEY)
    else:
        # DATA = session key
        next_session_key = self.session_keys.get(next_port)
        packet.mac = calculate_hmac(mac_data, next_session_key)

    self.send_callback(next_port, packet.to_bytes())
```

#### 4. `receive_packet()` - Broadcast Behavior
```python
# HEARTBEAT packets são broadcast - sempre entregar localmente E forward
if packet.msg_type == MessageType.HEARTBEAT:
    # Broadcast: entregar localmente sempre
    self._deliver_locally(packet)
    # Se TTL > 1, também fazer forward para downlinks
    if packet.ttl > 1:
        self._forward_packet(packet, incoming_port=port_id)
elif packet.destination == self.my_nid:
    # Para nós - entregar localmente
    self._deliver_locally(packet)
else:
    # Para outro dispositivo - forward
    self._forward_packet(packet, incoming_port=port_id)
```

---

## 🧪 Testes

### Novo Teste Adicionado

**`test_heartbeat_with_default_hmac_key()`** - Valida:
1. HEARTBEAT criado com `create_heartbeat_packet()` (DEFAULT_HMAC_KEY)
2. Router Daemon tem session key ECDH configurada
3. HEARTBEAT é recebido e verificado com DEFAULT_HMAC_KEY
4. HEARTBEAT é entregue localmente (broadcast)

### Resultados

```
======================================================================
TEST 8: HEARTBEAT packets with DEFAULT_HMAC_KEY
======================================================================
📤 Created heartbeat packet:
   Source: fdb98575...
   Dest: fdb98575... (broadcast)
   Seq: 42
   MAC uses: DEFAULT_HMAC_KEY
✅ Heartbeat received and verified with DEFAULT_HMAC_KEY
   (despite having ECDH session key configured)
✅ PASS - HEARTBEAT packets correctly use DEFAULT_HMAC_KEY

======================================================================
 SUMMARY
======================================================================
✅ Passed: 8/8
======================================================================

🎉 ALL TESTS PASSED! Router Daemon is functional.
```

---

## 🔒 Segurança

### HEARTBEAT Packets

**Camadas de Proteção**:
1. **MAC (DEFAULT_HMAC_KEY)**: Protege contra corrupção de rede
2. **ECDSA P-521 Signature**: Garante autenticidade do Sink (dentro do payload)
3. **Replay Protection**: Sliding window (size 100) previne replay attacks

**Justificação**:
- HEARTBEATs são **broadcast** (todos os nodes devem receber)
- Usar session key individual impossibilitaria broadcast eficiente
- ECDSA signature garante que apenas o Sink pode criar heartbeats válidos

### DATA Packets

**Camadas de Proteção**:
1. **MAC (Session Key ECDH)**: Autenticidade e integridade per-link
2. **DTLS Payload**: Confidencialidade end-to-end (AES-256-GCM)
3. **Replay Protection**: Sliding window previne replay attacks

---

## 📊 Impacto

### Antes da Fix
- ❌ Heartbeats bloqueados por MAC verification failure
- ❌ Nodes nunca recebem heartbeats
- ❌ Timeout de heartbeat dispara

### Depois da Fix
- ✅ Heartbeats verificados corretamente com DEFAULT_HMAC_KEY
- ✅ Nodes recebem heartbeats do Sink
- ✅ ECDSA signature garante autenticidade
- ✅ Broadcast multi-hop funciona (TTL > 1)

---

## 🎯 Alternativas Consideradas

### Opção A: Sink usa Router Daemon
**Rejeita** - Complexidade excessiva, Sink teria que enviar heartbeat individualmente para cada cliente

### Opção C: Heartbeats ignoram verificação MAC
**Rejeita** - Quebra princípio de defesa em profundidade, expõe a ruído de rede

### ✅ Opção B: HEARTBEAT = DEFAULT_HMAC_KEY (Escolhida)
**Aceita** - Balança simplicidade, segurança e compatibilidade

---

## 📝 Commit

```
fix: Router Daemon HEARTBEAT MAC verification with DEFAULT_HMAC_KEY

- HEARTBEATs usam DEFAULT_HMAC_KEY (broadcast)
- DATA packets usam session key ECDH
- Broadcast behavior: entrega local + forward
- 8/8 testes passam (100%)
```

**Commit Hash**: `e2024cd`

---

## 🔗 Referências

- [router_daemon.py:188-246](common/network/router_daemon.py#L188-L246) - `_verify_packet_mac()`
- [router_daemon.py:312-336](common/network/router_daemon.py#L312-L336) - `_forward_packet()` MAC recalculation
- [router_daemon.py:175-188](common/network/router_daemon.py#L175-L188) - Broadcast delivery logic
- [test_router_daemon.py:371-432](test_router_daemon.py#L371-L432) - `test_heartbeat_with_default_hmac_key()`
- [heartbeat.py:262-302](common/protocol/heartbeat.py#L262-L302) - `create_heartbeat_packet()`
