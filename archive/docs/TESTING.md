# Guia de Testes da Rede IoT

##  Quick Start

### Modo Interativo (Recomendado)
```bash
python3 test_network.py
```

Depois escolhe uma opção do menu:
- `1` - Iniciar Sink
- `2` - Iniciar Node  
- `3` - Monitorar logs em tempo real
- `7` - Ver status de autenticação
- `8` - Ver heartbeats
- `9` - Ver assinaturas digitais

### Modo Direto (Command Line)
```bash
# Iniciar componentes
python3 test_network.py --sink     # Iniciar Sink
python3 test_network.py --node     # Iniciar Node

# Monitorar logs
python3 test_network.py --logs            # Tempo real
python3 test_network.py --tail 100        # Últimas 100 linhas
python3 test_network.py --grep heartbeat  # Buscar padrão
```

##  Cenários de Teste

### 1. Teste Básico de Conectividade
```bash
# Terminal 1: Iniciar Sink
python3 test_network.py --sink

# Terminal 2: Iniciar Node
python3 test_network.py --node

# Terminal 3: Monitorar
python3 test_network.py --logs
```

**Resultado esperado:**
-  Node descobre Sink via BLE scan
-  Conexão GATT estabelecida
-  Autenticação X.509 completa
-  Session key derivada via ECDH
-  Heartbeats recebidos e verificados a cada 5s

### 2. Teste de Autenticação
```bash
python3 test_network.py --grep "autenticação|Session key|certificado"
```

**Verificar:**
- ` Certificado do peer recebido`
- ` Certificado validado com sucesso`
- `️ Response gerada: 139 bytes`
- ` Autenticação bem-sucedida!`
- ` Session key estabelecida`

### 3. Teste de Assinaturas Digitais
```bash
python3 test_network.py --grep "assinado|assinatura"
```

**Verificar:**
- Sink: `️ Heartbeat assinado: 139 bytes (padded para 142)`
- Node: ` Assinatura de heartbeat válida` (se DEBUG ativo)
- **Sem erros**: ` MAC inválido` ou ` Assinatura inválida`

### 4. Teste de Heartbeats
```bash
python3 test_network.py --grep "heartbeat|"
```

**Verificar:**
- Heartbeats a cada ~5 segundos
- Sequence numbers incrementais (7, 8, 9, 10...)
- Tamanho do pacote: 236 bytes (70 header + 166 payload)

##  Troubleshooting

### Sink não encontrado
```bash
# Verificar Bluetooth
sudo systemctl status bluetooth
hciconfig hci0 up

# Verificar advertising
python3 test_network.py --grep "Advertisement"
```

### Autenticação falhando
```bash
# Ver detalhes da autenticação
python3 test_network.py --grep "AUTH|certificado|challenge"

# Verificar certificados
ls -lh certs/
```

### Assinaturas inválidas
```bash
# Ver erros de assinatura
python3 test_network.py --grep "Assinatura.*grande|MAC inválido|truncada"

# Verificar tamanho das assinaturas
python3 test_network.py --grep "assinado.*bytes"
```

##  Métricas de Sucesso

### Sistema Funcionando Corretamente 
```
 Autenticação bem-sucedida!
 Session key estabelecida
 Heartbeat recebido (seq=X, age=Y.Ys)
(Sem erros de MAC ou assinatura)
```

### Problemas Conhecidos 
```
 MAC inválido em heartbeat!
 Assinatura de heartbeat inválida!
️ Certificado do Sink não disponível
ERROR | Assinatura muito grande: X bytes (máx Y)
```

## ️ Scripts Auxiliares

### Limpar Logs
```bash
> logs/iot-network.log
```

### Ver Estatísticas de Heartbeats
```bash
grep "Heartbeat recebido" logs/iot-network.log | wc -l
```

### Ver Taxa de Sucesso de Autenticação
```bash
grep -c "Autenticação bem-sucedida" logs/iot-network.log
```

##  Estrutura de Logs

- `logs/iot-network.log` - Log principal (Sink + Node)
- `logs/ble_operations_*.log` - Logs detalhados de operações BLE

##  Checklist de Segurança

- [x] Autenticação X.509 com certificados
- [x] Challenge-response com assinaturas ECDSA
- [x] Session keys derivadas via ECDH
- [x] MACs (HMAC-SHA256) em todos os pacotes
- [x] Assinaturas digitais em heartbeats broadcast
- [x] Replay protection com sequence numbers
- [ ] Key rotation (não implementado)
- [ ] Certificate revocation (não implementado)
