#!/bin/bash
# Auto-generated script to run Node with certificates

# Diretório do projeto (usa o diretório onde o script está localizado)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Adicionar diretório do projeto ao PYTHONPATH
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# NID do dispositivo (pode ser alterado)
NID="53a84472-db22-4eac-b5b3-3ef55b8630a6"

echo "A iniciar Node com NID: $NID..."
python3 "$PROJECT_DIR/node/iot_node.py" \
    --cert "$PROJECT_DIR/certs/$NID/certificate.pem" \
    --key "$PROJECT_DIR/certs/$NID/private_key.pem" \
    --ca-cert "$PROJECT_DIR/certs/ca_certificate.pem" \
    "$@"
