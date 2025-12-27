#!/bin/bash
#
# Script para executar o BLE Client de teste
# Uso: ./run_test_client.sh
#

# Mudar para o diretório do projeto
cd "$(dirname "$0")"

# Criar diretório de logs se não existir
mkdir -p logs

# Nome do ficheiro de log com timestamp
LOGFILE="logs/ble_client_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 A iniciar BLE Client..."
echo "📝 Log a ser guardado em: $LOGFILE"
echo ""

# Executar com o python3 do sistema e guardar output
# Usa 'tee' para mostrar no ecrã E guardar no ficheiro
python3 examples/test_ble_client.py 2>&1 | tee "$LOGFILE"
