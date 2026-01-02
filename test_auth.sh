#!/bin/bash
# Script para testar autenticação X.509 entre Sink e Node

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     Teste de Autenticação X.509 - Sink + Node                ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Este teste vai:"
echo "  1. Iniciar o Sink (GATT Server + Advertisement)"
echo "  2. Iniciar o Node (conecta ao Sink)"
echo "  3. Monitorar logs de autenticação X.509"
echo ""
echo "📋 Logs a procurar:"
echo "  • 📤 Enviando certificado..."
echo "  • 🔐 Mensagem de autenticação recebida..."
echo "  • ✅ Cliente autenticado com sucesso!"
echo "  • 🔑 Session key estabelecida"
echo "  • 🔑 Session key armazenada para NID..."
echo ""
echo "Pressione Ctrl+C para parar todos os processos."
echo ""

# Criar diretório de logs se não existir
mkdir -p logs

# Limpar log anterior
> logs/iot-network.log

echo "─────────────────────────────────────────────────────────────────"
echo "🚀 A iniciar Sink..."
echo "─────────────────────────────────────────────────────────────────"

# Terminal 1: Sink
sudo ./run_sink.sh hci0 &
SINK_PID=$!

echo "✅ Sink iniciado (PID: $SINK_PID)"
echo ""
echo "⏳ A aguardar 8 segundos para Sink ficar pronto..."
sleep 8

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo "🚀 A iniciar Node..."
echo "─────────────────────────────────────────────────────────────────"

# Terminal 2: Node
./run_node_9d4df1cf.sh &
NODE_PID=$!

echo "✅ Node iniciado (PID: $NODE_PID)"
echo ""
echo "⏳ A aguardar 15 segundos para autenticação completar..."
sleep 15

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo "📋 LOGS DE AUTENTICAÇÃO:"
echo "─────────────────────────────────────────────────────────────────"

# Mostrar logs relevantes de autenticação
grep -E "(🔐|📤|🔑|autenticação|certificado|Session key)" logs/iot-network.log | tail -n 30

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo "✅ TESTE COMPLETO"
echo "─────────────────────────────────────────────────────────────────"
echo ""
echo "Para ver logs em tempo real:"
echo "  tail -f logs/iot-network.log"
echo ""
echo "Para parar os processos:"
echo "  sudo kill $SINK_PID $NODE_PID"
echo ""
echo "Os processos continuam a correr em background."
echo "Pressione Ctrl+C para manter os processos ou aguarde..."

# Dar tempo para ver os logs
sleep 5

echo ""
echo "📊 Mantendo processos ativos. Verifique os logs continuamente."
echo "   Use: ./watch_logs.sh"
echo ""

# Manter script vivo para capturar Ctrl+C
trap "echo ''; echo '🛑 A parar processos...'; sudo kill $SINK_PID $NODE_PID 2>/dev/null; echo '✅ Processos parados.'; exit 0" INT

wait
