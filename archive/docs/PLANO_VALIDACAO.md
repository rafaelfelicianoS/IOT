#  PLANO DE VALIDAÇÃO - Testes Incrementais

**Objetivo**: Validar o que está implementado antes de adicionar features novas  
**Data**: 2025-12-31

---

##  O QUE JÁ ESTÁ PRONTO (Confirmado)

### 1. Certificados e CA
```bash
 certs/ca_certificate.pem       - CA root
 certs/ca_private_key.pem        - CA private key
 certs/sink_af04ea89_cert.pem    - Sink certificate
 certs/sink_af04ea89_key.pem     - Sink private key
 certs/node_9d4df1cf_cert.pem    - Node certificate  
 certs/node_9d4df1cf_key.pem     - Node private key
```

### 2. Security Implementation
```python
 common/security/certificate_manager.py  - Load/validate certificates
 common/security/authentication.py       - X.509 mutual auth protocol
 common/security/auth_handler.py         - GATT integration
 common/security/crypto.py               - HMAC-SHA256
 common/security/replay_protection.py    - Sequence numbers
 support/ca.py                           - CA implementation
```

### 3. Integration Points
```python
 sink/sink_device.py:
   - AuthenticationHandler initialized (line 123)
   - auth_handler.handle_message() (line 265)
   - auth_handler.is_authenticated() (line 273)
   - auth_handler.get_session_key() (line 277)

 node/iot_node.py:
   - AuthenticationHandler initialized (line 119)
```

---

##  TESTES INCREMENTAIS

### TESTE 1: Carregar Certificados 
**Objetivo**: Verificar que os certificados são carregados corretamente

```bash
cd /home/rafael/repos/iot

# Teste simples
python3 -c "
from pathlib import Path
from common.security.certificate_manager import CertificateManager
from common.utils.nid import NID

# Sink
sink_nid = NID.from_string('af04ea89-e9b3-4f42-a4e1-32d8b5e21c8f')
sink_cm = CertificateManager(sink_nid)
success = sink_cm.load_device_certificate()
print(f'Sink cert loaded: {success}')

# Node  
node_nid = NID.from_string('9d4df1cf-2b1a-4e5d-8c3f-1a2b3c4d5e6f')
node_cm = CertificateManager(node_nid)
success = node_cm.load_device_certificate()
print(f'Node cert loaded: {success}')
"
```

**Esperado**: 
```
Sink cert loaded: True
Node cert loaded: True
```

---

### TESTE 2: Validar Authentication Protocol 
**Objetivo**: Testar handshake de autenticação localmente

```bash
cd /home/rafael/repos/iot

python3 examples/test_authentication_protocol.py
```

**Esperado**:
- Troca de certificados
- Challenge-response
- Autenticação bem-sucedida
- Session key derivada

**Se não existir**, criar `examples/test_authentication_protocol.py`

---

### TESTE 3: Sink Standalone 
**Objetivo**: Verificar que Sink inicia com certificados

```bash
sudo ./run_sink.sh hci0
```

**Verificar logs**:
```
 Certificados carregados com sucesso
 GATT Server configurado
 GATT application registada!
 Advertisement registado!
 Heartbeat enviado
```

**Se der erro**: Analisar stack trace

---

### TESTE 4: Node Standalone 
**Objetivo**: Node inicia sem conectar

```bash
./run_node_9d4df1cf.sh
```

**Verificar logs**:
```
 Certificados carregados com sucesso
 GATT Server ativo
 A procurar uplink...
```

---

### TESTE 5: Sink + Node (Connection Only) 
**Objetivo**: Conexão BLE básica (sem autenticação por agora)

```bash
# Terminal 1
sudo ./run_sink.sh hci0

# Terminal 2  
./run_node_9d4df1cf.sh
```

**Verificar**:
- [ ] Node encontra Sink
- [ ] Node conecta ao Sink via GATT
- [ ] Conexão BLE estabelecida
- [ ] Sem crash

---

### TESTE 6: Authentication Handshake 
**Objetivo**: Validar que autenticação funciona end-to-end

**Verificar nos logs**:

**Sink**:
```
 Mensagem de autenticação recebida
 Certificado do peer validado
 Challenge-response verificado
 Cliente autenticado: [node_nid]
 Session key estabelecida
```

**Node**:
```
 Iniciando autenticação com uplink
 Certificado enviado
 Certificado do Sink validado  
 Challenge enviado/recebido
 Autenticado com Sink
 Session key estabelecida
```

---

### TESTE 7: Heartbeat com Signature Real 
**Objetivo**: Verificar que heartbeats são assinados com certificado

**Modificar**: `common/protocol/heartbeat.py`
- Trocar placeholder signature por assinatura ECDSA real
- Usar private key do Sink

**Verificar**:
- [ ] Heartbeat assinado
- [ ] Node verifica assinatura
- [ ] Signature válida

---

### TESTE 8: Message MAC 
**Objetivo**: Pacotes são protegidos com HMAC

**Verificar**:
- [ ] Packet.mac é calculado com session key
- [ ] MAC é verificado no receptor
- [ ] Pacotes com MAC inválido são rejeitados

---

### TESTE 9: Replay Protection 
**Objetivo**: Pacotes repetidos são detectados

**Verificar**:
- [ ] Sequence numbers incrementam
- [ ] Pacotes com seq old são rejeitados

---

##  CHECKLIST RÁPIDA

Execute os testes nesta ordem:

```bash
# 1. Teste de certificados
[ ] python3 -c "from common.security.certificate_manager import CertificateManager; ..."

# 2. Teste de authentication protocol  
[ ] python3 examples/test_authentication_protocol.py

# 3. Sink standalone
[ ] sudo ./run_sink.sh hci0

# 4. Node standalone (outro terminal)
[ ] ./run_node_9d4df1cf.sh

# 5. Verificar conexão + autenticação (logs)
[ ] Ver Terminal 1 (Sink)
[ ] Ver Terminal 2 (Node)

# 6. Testar heartbeats
[ ] Ver " Heartbeat" em ambos terminais

# 7. Testar envio de pacotes
[ ] python3 examples/test_packet_send_bleak.py
```

---

##  PROBLEMAS ESPERADOS

### 1. Certificados não encontrados
**Solução**: Regenerar com `./support/setup_sink.sh` e `./support/setup_node.sh`

### 2. Authentication não inicia
**Causa**: AuthCharacteristic não está a trigger o handler
**Debug**: Adicionar logs em `gatt_services.py` → `AuthCharacteristic.WriteValue()`

### 3. Session key não é usada
**Causa**: Packet MAC ainda usa chave hardcoded
**Fix**: Modificar `Packet.calculate_mac()` para aceitar session key

### 4. Heartbeat signature é placeholder
**Status**: Esperado! Falta implementar assinatura real
**Fix**: Usar `cert_manager.sign_data()` em `heartbeat.py`

---

##  PRIORIDADES

**Agora (hoje)**:
1.  Teste 1: Certificados
2.  Teste 3: Sink standalone
3.  Teste 4: Node standalone  
4.  Teste 5: Conexão Sink + Node

**Depois (próxima sessão)**:
5. Teste 6: Authentication handshake
6. Teste 7: Heartbeat signatures
7. Teste 8-9: MACs + Replay protection

---

**Próximo**: Executar Teste 1 → Certificados
