#!/bin/bash
# Auto-generated script to run Sink with certificates

ADAPTER=${1:-hci0}

# Detectar Python do venv se existir
if [ -n "$VIRTUAL_ENV" ]; then
    PYTHON="$VIRTUAL_ENV/bin/python3"
else
    PYTHON="python3"
fi

# Adicionar diretório do projeto ao PYTHONPATH
export PYTHONPATH="/home/rafael/repos/iot:$PYTHONPATH"

echo "A iniciar Sink no adaptador $ADAPTER..."
sudo -E PYTHONPATH="$PYTHONPATH" "$PYTHON" "/home/rafael/repos/iot/sink/sink_device.py" "$ADAPTER" \
    --cert "/home/rafael/repos/iot/certs/sink_c5c55ab2_cert.pem" \
    --key "/home/rafael/repos/iot/certs/sink_c5c55ab2_key.pem" \
    --ca-cert "/home/rafael/repos/iot/certs/ca_certificate.pem"
