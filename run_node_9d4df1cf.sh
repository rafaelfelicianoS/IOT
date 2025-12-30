#!/bin/bash
# Auto-generated script to run Node with certificates

# Diretório do projeto (usa o diretório onde o script está localizado)
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Adicionar diretório do projeto e venv ao PYTHONPATH
export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"

# Usar venv/lib do ambiente virtual para ter acesso aos pacotes instalados via pip
if [ -d "$PROJECT_DIR/venv/lib/python3.12/site-packages" ]; then
    export PYTHONPATH="$PROJECT_DIR/venv/lib/python3.12/site-packages:$PYTHONPATH"
fi

# NID do dispositivo (pode ser alterado)
NID="53a84472-db22-4eac-b5b3-3ef55b8630a6"

echo "A iniciar Node com NID: $NID..."

# Usar python3 do sistema (tem acesso a PyGObject/dbus-python)
# mas com PYTHONPATH configurado para ter acesso aos pacotes do venv
/usr/bin/python3 "$PROJECT_DIR/node/iot_node.py" \
    --cert "$PROJECT_DIR/certs/$NID/certificate.pem" \
    --key "$PROJECT_DIR/certs/$NID/private_key.pem" \
    --ca-cert "$PROJECT_DIR/certs/ca_certificate.pem" \
    "$@"
