# Certificados IoT Network

**Data de criação**: 2026-01-02  
**Validade**: 10 anos (até 2035-12-31)

---

##  Certificados Criados

###  CA (Certification Authority)
- **Certificado**: `certs/ca_certificate.pem`
- **Chave Privada**: `certs/ca_private_key.pem`
- **Algoritmo**: ECDSA P-521

###  Sink Device
- **NID**: `54c225f2...`
- **Certificado**: `certs/sink_54c225f2_cert.pem`
- **Chave Privada**: `certs/sink_54c225f2_key.pem`
- **Tipo**: Sink (OU=Sink no certificado)

###  Node 1
- **NID**: `74383752...`
- **Certificado**: `certs/node_74383752_cert.pem`
- **Chave Privada**: `certs/node_74383752_key.pem`
- **Tipo**: Node

###  Node 2
- **NID**: `03c606c8...`
- **Certificado**: `certs/node_03c606c8_cert.pem`
- **Chave Privada**: `certs/node_03c606c8_key.pem`
- **Tipo**: Node

---

##  Como Usar

### Iniciar Sink
```bash
sudo python3 sink/sink_device.py \
  --cert certs/sink_54c225f2_cert.pem \
  --key certs/sink_54c225f2_key.pem \
  --ca-cert certs/ca_certificate.pem \
  hci0
```

Ou usar o CLI:
```bash
./iot-sink start
```

### Iniciar Node 1
```bash
python3 node/iot_node.py \
  --cert certs/node_74383752_cert.pem \
  --key certs/node_74383752_key.pem \
  --ca-cert certs/ca_certificate.pem \
  hci0
```

Ou usar o CLI:
```bash
./iot-node start
```

### Iniciar Node 2
```bash
python3 node/iot_node.py \
  --cert certs/node_03c606c8_cert.pem \
  --key certs/node_03c606c8_key.pem \
  --ca-cert certs/ca_certificate.pem \
  hci1
```

---

##  Recriar Certificados

Para eliminar e recriar todos os certificados:

```bash
# 1. Eliminar certificados antigos
rm -rf certs/*

# 2. Criar nova CA
python3 support/ca.py

# 3. Criar certificado Sink
python3 support/provision_device.py --type sink

# 4. Criar certificados Nodes
python3 support/provision_device.py --type node
python3 support/provision_device.py --type node
```

---

##  Detalhes Técnicos

- **Curva Elíptica**: P-521 (SECP521R1)
- **Assinatura**: ECDSA-SHA256
- **Formato**: X.509 PEM
- **Key Usage**: 
  - CA: digital_signature, key_cert_sign, crl_sign
  - Devices: digital_signature, key_encipherment, key_agreement (para ECDH)
- **Autenticação**: Mutual authentication com challenge-response
- **Session Keys**: ECDH + HKDF-SHA256 (32 bytes)
