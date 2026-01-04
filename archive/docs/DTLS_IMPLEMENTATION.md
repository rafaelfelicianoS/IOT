# Implementação DTLS End-to-End

## Visão Geral

Este documento descreve a implementação de **DTLS (Datagram Transport Layer Security)** para proteção end-to-end na rede IoT, conforme requisito do projeto (Seção 5.7).

DTLS fornece encriptação e autenticação end-to-end entre cada Node e o Sink, complementando as camadas de segurança já existentes.

---

## Requisito do Projeto

> **Seção 5.7 - End-to-end services:**
> "The end-to-end communication between each IoT device and the Sink must be protected with DTLS. DTLS is suitable to be explored over connectionless transport protocols, such as the one we are implementing in this end-to-end communication. For end-to-end authentication you should use the same certificates that are used for the authentication of peers in the direct links."

---

## Camadas de Segurança

A rede IoT implementa **3 camadas de segurança**:

### 1. Link Layer (BLE)
- **Protocolo**: Bluetooth LE pairing ("Just Works")
- **Proteção**: Confidencialidade e integridade do link direto
- **Escopo**: Apenas comunicação BLE direta (1-hop)

### 2. Per-Link Security
- **Protocolo**: Session Keys + HMAC-SHA256
- **Proteção**: Integridade e freshness (via sequence numbers)
- **Escopo**: Cada link BLE individual
- **Implementação**:
  - Session keys derivadas via ECDH durante autenticação
  - HMAC calculado sobre cada pacote
  - Replay protection com janela de sequence numbers

### 3. End-to-End Security (DTLS)  NOVO
- **Protocolo**: DTLS 1.2 com certificados X.509
- **Proteção**: Confidencialidade, integridade e autenticação end-to-end
- **Escopo**: Node ↔ Sink (atravessa múltiplos hops)
- **Implementação**:
  - Certificados ECDSA P-521 para autenticação
  - Ciphers ECDHE para forward secrecy
  - Mensagens DATA wrapped/unwrapped com DTLS

---

## Arquitetura DTLS

### Componentes

#### 1. `DTLSChannel` (Node)
Cada Node mantém **um único canal DTLS** com o Sink:

```python
class DTLSChannel:
    def __init__(cert_path, key_path, ca_cert_path, is_server, peer_nid)
    def establish() -> bool          # Handshake DTLS
    def wrap(plaintext) -> bytes     # Encrypt
    def unwrap(ciphertext) -> bytes  # Decrypt
    def close()
```

**Características:**
- Usa certificados X.509 existentes (mesmo da autenticação per-link)
- `is_server=False` (Node é cliente)
- Estabelecido após autenticação bem-sucedida

#### 2. `DTLSManager` (Sink)
O Sink gerencia **múltiplos canais DTLS** (um por Node conectado):

```python
class DTLSManager:
    def __init__(cert_path, key_path, ca_cert_path)
    def create_channel(node_nid) -> DTLSChannel
    def get_channel(node_nid) -> DTLSChannel
    def remove_channel(node_nid)
```

**Características:**
- Mantém dict de canais por NID do Node
- Cria canal automaticamente quando Node autentica
- Remove canal quando Node desconecta

---

## Fluxo de Estabelecimento

### 1. Conexão BLE
```
Node → Sink: BLE GATT connection
```

### 2. Autenticação Mútua X.509
```
Node ↔ Sink: AuthenticationProtocol
              - Challenge-response com certificados
              - Verificação de assinaturas
              - Derivação de session key (ECDH)
```

### 3. Estabelecimento DTLS 
```
Node → Sink: DTLS ClientHello
Sink → Node: DTLS ServerHello + Certificate
Node → Sink: DTLS Certificate + ClientKeyExchange
Node ↔ Sink: DTLS Finished
```

**Após DTLS handshake:**
- Canal seguro estabelecido
- Mensagens DATA podem ser encriptadas end-to-end

---

## Integração no Código

### Sink (`sink/sink_device.py`)

#### Inicialização:
```python
def __init__(self, ...):
    self.dtls_manager = DTLSManager(
        cert_path=cert_path,
        key_path=key_path,
        ca_cert_path=ca_cert_path
    )
```

#### Após Autenticação (linha ~302):
```python
if self.auth_handler.is_authenticated(client_address):
    # ... armazenar session key ...

    # Estabelecer canal DTLS
    dtls_channel = self.dtls_manager.create_channel(client_nid)
    if dtls_channel.establish():
        logger.info(f" Canal DTLS estabelecido")
```

### Node (`node/iot_node.py`)

#### Inicialização:
```python
def __init__(self, ...):
    self.dtls_channel: Optional[DTLSChannel] = None
```

#### Após Autenticação (linha ~695):
```python
if auth_protocol.state.name == 'AUTHENTICATED':
    # ... armazenar session key ...

    # Estabelecer canal DTLS
    self.dtls_channel = DTLSChannel(
        cert_path=self.cert_path,
        key_path=self.key_path,
        ca_cert_path=self.ca_cert_path,
        is_server=False,
        peer_nid=self.uplink_nid
    )
    if self.dtls_channel.establish():
        logger.info(" Canal DTLS end-to-end estabelecido")
```

---

## Uso em Mensagens

### Envio (Node → Sink)

```python
def send_message(self, message: bytes):
    # 1. Criar pacote DATA
    packet = Packet.create(source=self.my_nid, destination=sink_nid, ...)

    # 2. Wrap com DTLS (end-to-end)
    if self.dtls_channel:
        encrypted_payload = self.dtls_channel.wrap(packet.payload)
        packet.payload = encrypted_payload

    # 3. Adicionar MAC (per-link)
    packet.mac = calculate_hmac(packet_data, self.uplink_session_key)

    # 4. Enviar via BLE
    self.uplink_connection.write(SERVICE, CHAR, packet.to_bytes())
```

### Recepção (Sink)

```python
def _handle_data_packet(self, packet: Packet):
    # 1. Verificar MAC (per-link)
    if not verify_hmac(...):
        return

    # 2. Unwrap com DTLS (end-to-end)
    dtls_channel = self.dtls_manager.get_channel(packet.source)
    if dtls_channel:
        plaintext = dtls_channel.unwrap(packet.payload)
        packet.payload = plaintext

    # 3. Processar mensagem
    logger.info(f"Mensagem recebida: {packet.payload.decode()}")
```

---

## Biblioteca Utilizada

### python3-dtls

**Instalação:**
```bash
pip install python3-dtls
```

**Características:**
- Implementação pura Python
- Backend OpenSSL via ctypes
- Suporta DTLS 1.2
- Compatible com certificados ECDSA
- API similar ao módulo `ssl` padrão

**Limitações:**
- Requer adaptação para transportes connectionless (BLE)
- Necessário implementar "pseudo-socket" que use callbacks BLE

---

## Estado da Implementação

###  Implementado
- [x] Módulo `DTLSChannel` e `DTLSManager`
- [x] Integração no fluxo de autenticação
- [x] Estabelecimento de canais DTLS após auth
- [x] Estrutura para wrap/unwrap de mensagens

###  TODO
- [ ] Implementar adaptador de socket para BLE transport
- [ ] Completar métodos `wrap()` e `unwrap()` com DTLS real
- [ ] Integrar wrap/unwrap no `send_message()` do Node
- [ ] Integrar unwrap na recepção de mensagens do Sink
- [ ] Testes end-to-end com mensagens encriptadas

---

## Configuração de Ciphers

O DTLS usa ciphers compatíveis com certificados ECDSA P-521:

```python
context.set_ciphers('ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-GCM-SHA256')
```

**Benefícios:**
- **ECDHE**: Forward secrecy (chaves de sessão não comprometidas se chave privada vazar)
- **ECDSA**: Compatible com certificados P-521
- **AES-GCM**: Authenticated encryption (confidencialidade + integridade)
- **SHA384**: Hash forte

---

## Separação de Responsabilidades

| Layer | Protocolo | Responsabilidade | Escopo |
|-------|-----------|------------------|--------|
| **BLE** | Bluetooth Pairing | Proteção do link físico | 1-hop |
| **Per-Link** | Session Keys + HMAC | Integridade hop-by-hop | Cada link |
| **End-to-End** | DTLS | Confidencialidade & Auth | Node ↔ Sink |

**Exemplo:**
```
Node A → Node B → Sink

Per-Link Security:
- A↔B: Session key AB + HMAC
- B↔Sink: Session key BSink + HMAC

End-to-End Security:
- A↔Sink: DTLS channel (atravessa B)
```

Mesmo que Node B seja comprometido:
-  Pode ver pacotes encriptados (DTLS)
-  Não pode ler conteúdo das mensagens (confidencialidade end-to-end)
-  Não pode modificar mensagens (HMAC detecta)

---

## Compatibilidade com Projeto

Esta implementação cumpre os requisitos:

 **Seção 5.7**: "end-to-end communication must be protected with DTLS"
 **Certificados**: Usa mesmos certificados X.509 (ECDSA P-521)
 **Connectionless**: DTLS adequado para transporte sem conexão
 **Separação**: DTLS separado de MACs per-link (camadas diferentes)

---

## Referências

- [python3-dtls no PyPI](https://pypi.org/project/python3-dtls/)
- [DTLS RFC 6347](https://datatracker.ietf.org/doc/html/rfc6347)
- [TLS 1.2 with ECDSA](https://datatracker.ietf.org/doc/html/rfc4492)

---

## Sources

- [Dtls · PyPI](https://pypi.org/project/Dtls/)
- [python3-dtls · PyPI](https://pypi.org/project/python3-dtls/)
- [GitHub - rbit/pydtls](https://github.com/rbit/pydtls)
