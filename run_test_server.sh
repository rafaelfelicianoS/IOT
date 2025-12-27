#!/bin/bash
#
# Script para executar o GATT Server de teste
# Uso: sudo ./run_test_server.sh
#

# Mudar para o diretório do projeto
cd "$(dirname "$0")"

# Criar diretório de logs se não existir
mkdir -p logs

# Nome do ficheiro de log com timestamp
LOGFILE="logs/gatt_server_$(date +%Y%m%d_%H%M%S).log"

echo "🚀 A iniciar GATT Server..."
echo "📝 Log a ser guardado em: $LOGFILE"
echo ""

# Executar com o python3 do sistema e guardar output
# Usa 'tee' para mostrar no ecrã E guardar no ficheiro
python3 examples/test_gatt_server.py hci0 2>&1 | tee "$LOGFILE"
