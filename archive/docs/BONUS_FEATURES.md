#  Features Bónus - 10% Extra

**Especificação**: "A maximum of 10% bonus will be granted to projects that implement some interesting, non-mandatory features."

---

##  **CRITÉRIOS DE SELEÇÃO**

Para obter o bónus máximo (10% = +2 valores), as features devem:

 **Ser interessantes academicamente** (não triviais)  
 **Agregar valor real ao projeto** (aplicabilidade prática)  
 **Demonstrar compreensão profunda** dos conceitos de rede/segurança  
 **Não quebrar funcionalidades existentes**  
 **Ser implementáveis em 2-4 dias** de trabalho

---

##  **RECOMENDAÇÕES TOP 3** (Ordem de Prioridade)

###  **1. Multiple Sinks com Failover Automático**

**Complexidade**:  Alta  
**Impacto Académico**: ⭐⭐⭐⭐⭐ Máximo  
**Tempo Estimado**: 3-4 dias  
**Pontos Bónus**: +2 valores (exemplo explícito da especificação)

#### Por que escolher:
-  **Exemplo explícito** na especificação
-  Demonstra arquitetura distribuída avançada
-  Testa conhecimento profundo de DTLS e routing
-  Feature real-world crítica (fault tolerance)

#### O que implementar:

```
Cenário:
┌─────────┐          ┌─────────┐
│ Sink A  │          │ Sink B  │
│ (Main)  │          │ (Backup)│
└────┬────┘          └────┬────┘
     │                    │
     ├─────────┬──────────┤
     │         │          │
  ┌──┴──┐   ┌─┴───┐   ┌──┴──┐
  │Node1│   │Node2│   │Node3│
  └─────┘   └─────┘   └─────┘
```

**Features**:
1. **Sink Discovery Protocol**
   - Nodes descobrem múltiplos Sinks via advertising
   - Cada Sink anuncia prioridade (main/backup)
   
2. **Failover Automático**
   - Se Sink Main cai → Nodes conectam ao Backup
   - Detecção via heartbeat timeout (já implementado)
   
3. **DTLS Channel Management**
   - Quando Sink muda: invalidar canal DTLS antigo
   - Estabelecer novo canal com novo Sink
   - Session key renegotiation
   
4. **Sink Coordination**
   - Sinks partilham estado via message queue
   - Inbox replicado entre Sinks (opcional)

#### Ficheiros a criar/modificar:

```python
# common/network/sink_discovery.py
class SinkDiscoveryProtocol:
    """Protocolo para descobrir múltiplos Sinks."""
    def discover_sinks(self, timeout: int) -> List[SinkInfo]
    def select_best_sink(self, sinks: List[SinkInfo]) -> SinkInfo

# common/network/multi_sink_manager.py
class MultiSinkManager:
    """Gere conexões a múltiplos Sinks com failover."""
    def connect_to_sink(self, sink_info: SinkInfo)
    def handle_sink_failover(self, old_sink: NID, new_sink: NID)
    def invalidate_dtls_channel(self, sink_nid: NID)

# node/iot_node.py - MODIFICAR
def handle_sink_change(self):
    # Detectar mudança de Sink
    # Limpar canal DTLS antigo
    # Reconectar ao novo Sink
```

#### Demo para Professor:

```bash
# Terminal 1 - Sink A (Main)
./iot-sink interactive hci0 --priority=main

# Terminal 2 - Sink B (Backup)
./iot-sink interactive hci1 --priority=backup

# Terminal 3 - Node
./iot-node interactive hci2
node> scan
# → Mostra Sink A (main, priority=1) e Sink B (backup, priority=2)
node> connect 1  # Conecta ao Main

# Simular falha do Sink A
# Terminal 1: Ctrl+C (mata Sink A)

# Terminal 3 - Node deteta e reconecta automaticamente
[INFO]  Sink Main timeout - iniciando failover
[INFO]  Conectando ao Sink Backup...
[INFO]  Novo canal DTLS estabelecido
[INFO]  Failover completo!
```

**Complexidade vs Reward**: ⭐⭐⭐⭐⭐ Máximo impacto

---

###  **2. Sensor Data Aggregation com Timestamps**

**Complexidade**:  Média  
**Impacto Académico**: ⭐⭐⭐⭐ Alto  
**Tempo Estimado**: 1-2 dias  
**Pontos Bónus**: +1.5 valores

#### Por que escolher:
-  IoT devices reais sempre têm sensores
-  Demonstra aplicação prática de IoT
-  Integra com arquitetura existente sem quebrar nada
-  Impressiona visualmente (dados reais + visualização)

#### O que implementar:

**Features**:
1. **Virtual Sensors**
   - Temperatura (simulated ou lm-sensors real)
   - CPU usage (psutil)
   - Memory usage
   - Battery level (se laptop)
   
2. **Periodic Sampling**
   - Configurable interval (ex: 10s)
   - Timestamps em UTC
   
3. **Data Aggregation no Sink**
   - Armazenar séries temporais
   - Calcular estatísticas (avg, min, max)
   
4. **Query Interface**
   - `sink> sensors` - listar todos sensores
   - `sink> data <node_nid> temperature last 10` - últimas 10 leituras
   - `sink> stats <node_nid> temperature` - estatísticas

#### Ficheiros a criar:

```python
# node/sensors/sensor_manager.py
class SensorManager:
    """Gere múltiplos sensores num Node."""
    def __init__(self):
        self.sensors = {
            'temperature': VirtualTemperatureSensor(),
            'cpu': CPUSensor(),
            'memory': MemorySensor(),
        }
    
    def sample_all(self) -> Dict[str, SensorReading]:
        """Amostra todos os sensores."""
        return {name: sensor.read() for name, sensor in self.sensors.items()}

# node/sensors/base.py
class Sensor:
    """Classe base para sensores."""
    def read(self) -> SensorReading
    
class SensorReading:
    timestamp: float  # Unix timestamp
    value: float
    unit: str
    sensor_id: str

# sink/data_aggregator.py
class DataAggregator:
    """Agrega dados de sensores de todos os Nodes."""
    def store_reading(self, node_nid: NID, reading: SensorReading)
    def get_recent(self, node_nid: NID, sensor: str, limit: int)
    def get_stats(self, node_nid: NID, sensor: str)
```

#### Demo:

```bash
# Node - Sampling automático
[INFO] ️  Temperature: 23.5°C
[INFO]  CPU: 45%
[INFO]  Memory: 2.1GB / 8GB

# Sink - Ver dados
sink> sensors
 SENSORES ATIVOS:

Node: 9d4df1cf-...
  • temperature (última: 23.5°C há 5s)
  • cpu (última: 45% há 5s)
  • memory (última: 2.1GB há 5s)

sink> data 9d4df1cf temperature last 5
┌─────────────────────┬─────────────┐
│ Timestamp           │ Temperatura │
├─────────────────────┼─────────────┤
│ 2026-01-03 18:30:00 │ 23.5°C      │
│ 2026-01-03 18:30:10 │ 23.6°C      │
│ 2026-01-03 18:30:20 │ 23.4°C      │
│ 2026-01-03 18:30:30 │ 23.7°C      │
│ 2026-01-03 18:30:40 │ 23.5°C      │
└─────────────────────┴─────────────┘

sink> stats 9d4df1cf temperature
 ESTATÍSTICAS - Temperature (últimas 100 leituras)

   Média: 23.54°C
   Min:   22.8°C
   Max:   24.2°C
   StdDev: 0.35°C
```

**Bonus**: Exportar para CSV/JSON para análise externa

---

###  **3. Adaptive Heartbeat com Power Management**

**Complexidade**:  Baixa-Média  
**Impacto Académico**: ⭐⭐⭐ Médio-Alto  
**Tempo Estimado**: 1 dia  
**Pontos Bónus**: +1 valor

#### Por que escolher:
-  Relevante para IoT real (battery-powered devices)
-  Demonstra otimização de rede
-  Fácil de implementar (modificar heartbeat existente)
-  Impressiona com métricas de eficiência

#### O que implementar:

**Features**:
1. **Adaptive Heartbeat Interval**
   - Normal: 5s (como está)
   - Low Power: 15s (quando bateria < 20%)
   - Sleep Mode: 60s (quando inativo)
   
2. **Battery Level Monitoring**
   - Ler battery level (se disponível)
   - Simular se não houver (degrada com tempo)
   
3. **Dynamic Timeout Adjustment**
   - Sink ajusta timeout baseado no modo do Node
   - Low Power Node: 3 × 15s = 45s timeout
   
4. **Power Statistics**
   - Calcular energia poupada
   - Mostrar no status

#### Ficheiros a modificar:

```python
# common/protocol/heartbeat.py - ADICIONAR
class PowerMode(IntEnum):
    NORMAL = 0      # 5s interval
    LOW_POWER = 1   # 15s interval
    SLEEP = 2       # 60s interval

# node/iot_node.py - MODIFICAR
class IoTNode:
    def __init__(self):
        self.power_mode = PowerMode.NORMAL
        self.battery_level = 100  # %
    
    def update_power_mode(self):
        if self.battery_level < 20:
            self.power_mode = PowerMode.LOW_POWER
        elif self.battery_level < 10:
            self.power_mode = PowerMode.SLEEP
    
    def get_heartbeat_interval(self) -> float:
        intervals = {
            PowerMode.NORMAL: 5.0,
            PowerMode.LOW_POWER: 15.0,
            PowerMode.SLEEP: 60.0,
        }
        return intervals[self.power_mode]
```

#### Demo:

```bash
node> status
...
 POWER MANAGEMENT:
   Mode:  NORMAL (5s heartbeats)
   Battery: 100%
   Energia poupada: 0 kJ

# Simular bateria baixa
node> set battery 15
[INFO] ️  Bateria baixa - mudando para LOW_POWER mode
[INFO]  Heartbeat interval: 5s → 15s

node> status
 POWER MANAGEMENT:
   Mode:  LOW_POWER (15s heartbeats)
   Battery: 15%
   Energia poupada: 12.3 kJ (desde início)
   Packets saved: ~2400 (em 2h)
```

---

##  **OUTRAS IDEAS INTERESSANTES**

### 4. **Network Topology Visualizer (Web Interface)**

**Tempo**: 2-3 dias | **Bónus**: +1.5

- Web dashboard mostrando topologia em tempo real
- Visualização de hop counts, RSSI, packet flow
- D3.js ou vis.js para gráfico interativo
- WebSocket para updates em tempo real

```
http://localhost:8080
┌─────────────────────────────────┐
│   IoT Network Dashboard         │
├─────────────────────────────────┤
│  [Sink]                         │
│    └─ Node A (hop=0, RSSI=-45)  │
│       └─ Node B (hop=1, RSSI=-55)│
│    └─ Node C (hop=0, RSSI=-50)  │
│                                  │
│   Packets: 1234 (98% success) │
│   Avg Latency: 45ms           │
└─────────────────────────────────┘
```

### 5. **Message Priority Queue (QoS)**

**Tempo**: 1 dia | **Bónus**: +0.8

```python
class MessagePriority(IntEnum):
    LOW = 0      # Sensor data
    NORMAL = 1   # Regular messages
    HIGH = 2     # Alerts
    CRITICAL = 3 # Emergency (bypass queue)

# Router Daemon mantém 4 filas separadas
# Processa CRITICAL primeiro, depois HIGH, etc.
```

### 6. **Secure Firmware Update Over-the-Air**

**Tempo**: 3-4 dias | **Bónus**: +1.8

- Sink distribui firmware updates
- Signature verification (ECDSA)
- Incremental updates (delta patches)
- Rollback mechanism

### 7. **Network Intrusion Detection System**

**Tempo**: 2 dias | **Bónus**: +1.5

- Detetar padrões anómalos (excessive packets, replay attacks)
- Rate limiting por Node
- Blacklist automático de Nodes maliciosos
- Alert system

### 8. **Dynamic Route Optimization (RSSI-based)**

**Tempo**: 1-2 dias | **Bónus**: +1.2

- Escolher uplink baseado em RSSI (não só hop count)
- Re-routing automático se link degrada
- Path quality metrics

### 9. **Message Acknowledgment & Retransmission**

**Tempo**: 1 dia | **Bónus**: +0.8

- ACK packets para DATA messages
- Timeout & retransmission automática
- Sequence number tracking

### 10. **Energy Harvesting Simulation**

**Tempo**: 1 dia | **Bónus**: +0.7

- Simular solar panels a recarregar bateria
- Duty cycling baseado em energia disponível
- Predictive power management

---

##  **MATRIZ DE DECISÃO**

| Feature | Complexidade | Tempo | Bónus | Impressão | Quebra? | **SCORE** |
|---------|--------------|-------|-------|-----------|---------|-----------|
| **Multiple Sinks** | Alta | 3-4d | +2.0 | ⭐⭐⭐⭐⭐ | Não | **10/10** |
| **Sensor Aggregation** | Média | 1-2d | +1.5 | ⭐⭐⭐⭐ | Não | **9/10** |
| **Adaptive Heartbeat** | Baixa | 1d | +1.0 | ⭐⭐⭐ | Não | **8/10** |
| **Web Dashboard** | Média | 2-3d | +1.5 | ⭐⭐⭐⭐ | Não | **8/10** |
| **QoS Priority** | Baixa | 1d | +0.8 | ⭐⭐⭐ | Não | **7/10** |
| **Firmware Update** | Alta | 3-4d | +1.8 | ⭐⭐⭐⭐⭐ | Possível | **7/10** |
| **IDS** | Média | 2d | +1.5 | ⭐⭐⭐⭐ | Não | **8/10** |
| **RSSI Routing** | Média | 1-2d | +1.2 | ⭐⭐⭐ | Não | **7/10** |

---

##  **RECOMENDAÇÃO FINAL**

### Cenário 1: **Máximo Impacto (10% completo)**
**Escolher**: Multiple Sinks + Sensor Aggregation  
**Tempo**: 4-6 dias  
**Bónus Esperado**: +2.0 valores ⭐⭐⭐⭐⭐

### Cenário 2: **Rápido e Eficiente (5-7% bónus)**
**Escolher**: Sensor Aggregation + Adaptive Heartbeat  
**Tempo**: 2-3 dias  
**Bónus Esperado**: +1.2-1.5 valores ⭐⭐⭐⭐

### Cenário 3: **Quick Win (3-5% bónus)**
**Escolher**: Adaptive Heartbeat + QoS  
**Tempo**: 1-2 dias  
**Bónus Esperado**: +0.8-1.0 valores ⭐⭐⭐

---

##  **COMO MAXIMIZAR BÓNUS**

### Estratégia Apresentação:

1. **Documentar Bem**
   - Criar `BONUS_IMPLEMENTATION.md`
   - Explicar decisões de design
   - Comparar com literatura académica

2. **Demo Impressionante**
   - Script de demo de 2-3 minutos
   - Mostrar cenários realistas
   - Métricas visuais

3. **Justificar Academicamente**
   - Citar papers (IEEE, ACM)
   - Explicar relevância para IoT real
   - Mostrar complexidade técnica

4. **README Atualizado**
   - Secção "Bonus Features" destacada
   - Comparação com sistemas comerciais
   - Screenshots/diagramas

---

##  **REFERÊNCIAS ÚTEIS**

### Papers Relevantes:
- "Energy-Efficient Data Aggregation in Wireless Sensor Networks" (IEEE)
- "Fault-Tolerant IoT Gateway Architecture" (ACM)
- "Adaptive Heartbeat for Low-Power IoT" (Springer)

### Sistemas Comerciais com Features Similares:
- AWS IoT Core (Multiple endpoints, failover)
- Azure IoT Hub (Sensor aggregation, telemetry)
- Zigbee (Adaptive heartbeat, power management)

---

**NOTA**: Com o projeto já em **19.6-20.0** valores, implementar Multiple Sinks garante **20+ valores** (cap em 20, mas impressiona). ⭐
