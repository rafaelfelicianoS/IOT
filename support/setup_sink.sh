#!/bin/bash
# Setup completo do Sink: CA + Certificado

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================================"
echo "  Setup do Sink - IoT Network"
echo "========================================================"
echo ""

# 1. Criar CA (se não existir)
if [ ! -f "$PROJECT_DIR/certs/ca_certificate.pem" ]; then
    echo "CA não existe, a criar..."
    python3 "$SCRIPT_DIR/ca.py"
    echo ""
else
    echo " CA já existe"
    echo ""
fi

# 2. Gerar certificado para o Sink
echo "A gerar certificado para o Sink..."
python3 "$SCRIPT_DIR/provision_device.py" --type sink "$@"

# 3. Criar script para executar o Sink
SINK_CERT=$(ls -t "$PROJECT_DIR/certs/sink_"*"_cert.pem" 2>/dev/null | head -1)
SINK_KEY=$(ls -t "$PROJECT_DIR/certs/sink_"*"_key.pem" 2>/dev/null | head -1)
CA_CERT="$PROJECT_DIR/certs/ca_certificate.pem"

if [ -n "$SINK_CERT" ] && [ -n "$SINK_KEY" ]; then
    cat > "$PROJECT_DIR/run_sink.sh" << EOF
#!/bin/bash
# Auto-generated script to run Sink with certificates

ADAPTER=\${1:-hci0}

# Detectar Python do venv se existir
if [ -n "\$VIRTUAL_ENV" ]; then
    PYTHON="\$VIRTUAL_ENV/bin/python3"
else
    PYTHON="python3"
fi

# Adicionar diretório do projeto ao PYTHONPATH
export PYTHONPATH="$PROJECT_DIR:\$PYTHONPATH"

echo "A iniciar Sink no adaptador \$ADAPTER..."
sudo -E PYTHONPATH="\$PYTHONPATH" "\$PYTHON" "$PROJECT_DIR/sync/sink_device.py" "\$ADAPTER" \\
    --cert "$SINK_CERT" \\
    --key "$SINK_KEY" \\
    --ca-cert "$CA_CERT"
EOF
    chmod +x "$PROJECT_DIR/run_sink.sh"

    echo ""
    echo "========================================================"
    echo " Setup do Sink concluído!"
    echo "========================================================"
    echo ""
    echo "Para executar o Sink:"
    echo "  ./run_sink.sh [adapter]"
    echo ""
    echo "Exemplo:"
    echo "  ./run_sink.sh hci0"
else
    echo ""
    echo "========================================================"
    echo " Setup do Sink concluído!"
    echo "========================================================"
fi
