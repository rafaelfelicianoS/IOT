#!/bin/bash
# Script para testar GATT operations com gatttool diretamente

TARGET_MAC="E0:D3:62:D6:EE:A0"
ADAPTER="hci0"

echo "============================================"
echo "  Teste GATT via gatttool"
echo "============================================"
echo ""

echo "1️⃣  Conectando a $TARGET_MAC via $ADAPTER..."
gatttool -i $ADAPTER -b $TARGET_MAC --interactive <<EOF
connect
char-desc
exit
EOF

echo ""
echo "============================================"
echo "  Teste concluído"
echo "============================================"
