#!/bin/bash
#
# Script para limpar logs com permissões de root
# Uso: sudo ./clean_logs.sh
#

echo "🧹 A limpar diretório de logs..."

# Remover todo o diretório logs
rm -rf logs/

# Recriar o diretório
mkdir -p logs/

# Mudar dono para o utilizador atual (não root)
chown -R $SUDO_USER:$SUDO_USER logs/

echo "✅ Logs limpos! Agora podes fazer git pull"
echo ""
echo "Executar: git pull"
