#!/bin/bash
# Auto-generated script to run Node with certificates

# Adicionar diretório do projeto ao PYTHONPATH
export PYTHONPATH="/home/rafael/repos/iot:$PYTHONPATH"

echo "A iniciar Node 9d4df1cf..."
python3 "/home/rafael/repos/iot/node/iot_node.py" \
    --cert "/home/rafael/repos/iot/certs/node_9d4df1cf_cert.pem" \
    --key "/home/rafael/repos/iot/certs/node_9d4df1cf_key.pem" \
    --ca-cert "/home/rafael/repos/iot/certs/ca_certificate.pem" \
    "$@"
