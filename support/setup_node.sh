#!/bin/bash
# Setup de um IoT Node: Gera certificado

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================================"
echo "  Setup de IoT Node - IoT Network"
echo "========================================================"
echo ""

# Verificar se CA existe
if [ ! -f "$PROJECT_DIR/certs/ca_certificate.pem" ]; then
    echo " CA não existe! Execute primeiro:"
    echo "   ./support/setup_sink.sh"
    exit 1
fi

echo " CA encontrada"
echo ""

# Gerar certificado para o Node
echo "A gerar certificado para o Node..."
python3 "$SCRIPT_DIR/provision_device.py" --type node "$@"

# Criar script para executar o Node
NODE_CERT=$(ls -t "$PROJECT_DIR/certs/node_"*"_cert.pem" 2>/dev/null | head -1)
NODE_KEY=$(ls -t "$PROJECT_DIR/certs/node_"*"_key.pem" 2>/dev/null | head -1)
CA_CERT="$PROJECT_DIR/certs/ca_certificate.pem"

if [ -n "$NODE_CERT" ] && [ -n "$NODE_KEY" ]; then
    # Extrair NID do nome do ficheiro para criar script único
    NODE_ID=$(basename "$NODE_CERT" | sed 's/node_\(.*\)_cert.pem/\1/')

    cat > "$PROJECT_DIR/run_node_$NODE_ID.sh" << EOF
#!/bin/bash
# Auto-generated script to run Node with certificates

# Adicionar diretório do projeto ao PYTHONPATH
export PYTHONPATH="$PROJECT_DIR:\$PYTHONPATH"

echo "A iniciar Node $NODE_ID..."
python3 "$PROJECT_DIR/node/iot_node.py" \\
    --cert "$NODE_CERT" \\
    --key "$NODE_KEY" \\
    --ca-cert "$CA_CERT" \\
    "\$@"
EOF
    chmod +x "$PROJECT_DIR/run_node_$NODE_ID.sh"

    echo ""
    echo "========================================================"
    echo " Setup do Node concluído!"
    echo "========================================================"
    echo ""
    echo "Para executar o Node:"
    echo "  ./run_node_$NODE_ID.sh"
else
    echo ""
    echo "========================================================"
    echo " Setup do Node concluído!"
    echo "========================================================"
fi
