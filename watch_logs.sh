#!/bin/bash
# Script para monitorar logs em tempo real

LOG_FILE="logs/iot-network.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "⚠️  Arquivo de log não encontrado: $LOG_FILE"
    echo "   Os logs serão criados quando Sink ou Node iniciarem."
    exit 1
fi

echo "📋 Monitorando logs em tempo real..."
echo "   Arquivo: $LOG_FILE"
echo "   Pressione Ctrl+C para parar"
echo ""

tail -f "$LOG_FILE" | grep --line-buffered -E "(✅|❌|⚠️|💓|🔍|🔗|📥|📤|INFO|ERROR|WARNING)"
