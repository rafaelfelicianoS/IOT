#!/bin/bash
# Script para copiar certificados para outra máquina

# Uso: ./scripts/copy_certs.sh user@hostname:/path/to/IOT

if [ -z "$1" ]; then
    echo "Uso: ./scripts/copy_certs.sh user@hostname:/path/to/IOT"
    echo "Exemplo: ./scripts/copy_certs.sh rafa@laptop:/home/rafa/IOT/IOT"
    exit 1
fi

DEST=$1

echo "📦 A copiar certificados para $DEST..."

# Copiar toda a pasta certs
rsync -avz --progress certs/ "$DEST/certs/"

echo "✅ Certificados copiados!"
echo ""
echo "Estrutura copiada:"
echo "  - certs/ca_certificate.pem"
echo "  - certs/ca_private_key.pem"
echo "  - certs/<device-nid>/certificate.pem"
echo "  - certs/<device-nid>/private_key.pem"
