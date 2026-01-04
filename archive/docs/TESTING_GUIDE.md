# Guia de Teste - Sistema IoT BLE Mesh Network

##  Teste Rápido: Sink + Node

### Terminal 1: Sink
```bash
cd /home/rafael/repos/iot
sudo ./run_sink.sh hci0
```

**Saída esperada:**
-  Certificados carregados
-  GATT Server configurado  
-  Advertisement registado
-  Heartbeats a cada 5s

### Terminal 2: Node
```bash
cd /home/rafael/repos/iot
./run_node_9d4df1cf.sh
```

**Saída esperada:**
-  GATT Server ativo
-  Sink encontrado
-  Conectado ao Sink - hop_count=0
-  Heartbeats recebidos a cada 5s

##  Checklist:
- [ ] Sink heartbeats a cada 5s
- [ ] Node descobre e conecta ao Sink
- [ ] Node hop=0
- [ ] Node recebe heartbeats
- [ ] Sem erros nos logs
