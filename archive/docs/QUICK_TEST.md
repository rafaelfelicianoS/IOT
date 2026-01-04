#  TESTE RÁPIDO - Sink + Node

## Preparação (uma vez):

```bash
cd /home/rafael/repos/iot

# Verificar certificados existem
ls certs/sink_* certs/node_*

# Se não existirem:
./support/setup_sink.sh      # Gera certificados do Sink
./support/setup_node.sh      # Gera certificados do Node
```

##  Executar Teste:

### TERMINAL 1: Sink
```bash
cd /home/rafael/repos/iot
sudo ./run_sink.sh hci0
```

### TERMINAL 2: Node  
```bash
cd /home/rafael/repos/iot
./run_node_9d4df1cf.sh
```

### TERMINAL 3: Logs (opcional)
```bash
cd /home/rafael/repos/iot
./watch_logs.sh
```

##  O que deve acontecer:

**Sink (Terminal 1):**
```
 Certificados carregados com sucesso
Sink NID: af04ea89...
 GATT Server configurado
 GATT application registada!
 Advertisement registado!
 Heartbeat enviado (cada 5s)
```

**Node (Terminal 2):**
```
 Certificados carregados com sucesso
Node NID: 9d4df1cf...
 GATT Server ativo - aguardando downlinks
 A procurar uplink...
 Sink encontrado: IoT-Sink-af04ea89
 Conectado ao uplink via GATT
 Conectado ao Sink - hop_count=0
 Advertisement atualizado: hop_count=0
 Node pronto! Uplink conectado (hop=0)
 Heartbeat recebido (seq=X, age=0.0Xs)
 Heartbeat recebido (seq=X+1, age=0.0Xs)
...
```

##  Sucesso se:

- [ ] Sink envia heartbeats a cada 5s
- [ ] Node encontra Sink em < 10s
- [ ] Node conecta em < 5s
- [ ] Node hop_count = 0
- [ ] Node recebe heartbeats a cada 5s
- [ ] Latência < 0.1s
- [ ] Sem erros nos logs

##  Se der erro:

```bash
# Reiniciar Bluetooth
sudo systemctl restart bluetooth

# Tentar novamente
sudo ./run_sink.sh hci0     # Terminal 1
./run_node_9d4df1cf.sh      # Terminal 2
```

##  Verificar Advertisement:

```bash
# Terminal 4
sudo hcitool lescan

# Deve aparecer:
# IoT-Sink-af04ea89
# IoT-Node-9d4df1cf
```

##  Ver manufacturer data:

```bash
sudo btmon

# Procurar por:
# Sink: manufacturer data 0xFFFF = [00 FF]
# Node: manufacturer data 0xFFFF = [01 00]
```

---

**Pressione Ctrl+C em cada terminal para parar.**
