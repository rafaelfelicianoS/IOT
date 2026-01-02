#!/usr/bin/env python3
"""
Script CLI interativo para testar a rede IoT.

Permite iniciar Sink e Node, monitorar logs em tempo real,
e executar comandos de teste.
"""

import subprocess
import sys
import time
import argparse
from pathlib import Path

def print_header(text):
    """Imprime cabeçalho formatado."""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def run_sink():
    """Inicia o Sink em foreground."""
    print_header("Iniciando Sink Device")
    try:
        subprocess.run([sys.executable, "sink/sink_device.py"], cwd="/home/rafael/repos/iot")
    except KeyboardInterrupt:
        print("\n✅ Sink parado")

def run_node():
    """Inicia o Node em foreground."""
    print_header("Iniciando IoT Node")
    try:
        subprocess.run([sys.executable, "node/iot_node.py"], cwd="/home/rafael/repos/iot")
    except KeyboardInterrupt:
        print("\n✅ Node parado")

def tail_logs():
    """Mostra logs em tempo real."""
    print_header("Monitorando logs (Ctrl+C para parar)")
    try:
        subprocess.run(
            ["tail", "-f", "/home/rafael/repos/iot/logs/iot-network.log"],
            cwd="/home/rafael/repos/iot"
        )
    except KeyboardInterrupt:
        print("\n✅ Monitoramento parado")

def show_recent_logs(lines=50):
    """Mostra logs recentes."""
    print_header(f"Últimos {lines} logs")
    subprocess.run(
        ["tail", "-n", str(lines), "/home/rafael/repos/iot/logs/iot-network.log"],
        cwd="/home/rafael/repos/iot"
    )

def grep_logs(pattern):
    """Pesquisa padrão nos logs."""
    print_header(f"Buscando: {pattern}")
    subprocess.run(
        ["grep", "-i", "--color=auto", pattern, "/home/rafael/repos/iot/logs/iot-network.log"],
        cwd="/home/rafael/repos/iot"
    )

def show_menu():
    """Mostra menu interativo."""
    print_header("IoT Network Test CLI")
    print("Opções:")
    print("  1. Iniciar Sink")
    print("  2. Iniciar Node")
    print("  3. Monitorar logs (tail -f)")
    print("  4. Ver logs recentes (50 linhas)")
    print("  5. Ver logs recentes (100 linhas)")
    print("  6. Buscar nos logs")
    print("  7. Ver status de autenticação")
    print("  8. Ver heartbeats")
    print("  9. Ver assinaturas")
    print("  0. Sair")
    print()

def interactive_mode():
    """Modo interativo."""
    while True:
        show_menu()
        choice = input("Escolha uma opção: ").strip()
        
        if choice == "1":
            run_sink()
        elif choice == "2":
            run_node()
        elif choice == "3":
            tail_logs()
        elif choice == "4":
            show_recent_logs(50)
        elif choice == "5":
            show_recent_logs(100)
        elif choice == "6":
            pattern = input("Padrão de busca: ").strip()
            if pattern:
                grep_logs(pattern)
        elif choice == "7":
            grep_logs("autenticação|authentication|Session key|certificado")
        elif choice == "8":
            grep_logs("heartbeat|💓")
        elif choice == "9":
            grep_logs("assinado|assinatura|signature")
        elif choice == "0":
            print("\n👋 Até logo!")
            break
        else:
            print("\n❌ Opção inválida!")
        
        if choice not in ["1", "2", "3"]:
            input("\nPressione Enter para continuar...")

def main():
    """Função principal."""
    parser = argparse.ArgumentParser(description="IoT Network Test CLI")
    parser.add_argument("--sink", action="store_true", help="Iniciar Sink")
    parser.add_argument("--node", action="store_true", help="Iniciar Node")
    parser.add_argument("--logs", action="store_true", help="Monitorar logs")
    parser.add_argument("--tail", type=int, metavar="N", help="Ver últimas N linhas de log")
    parser.add_argument("--grep", type=str, metavar="PATTERN", help="Buscar padrão nos logs")
    
    args = parser.parse_args()
    
    # Modo direto (argumentos)
    if args.sink:
        run_sink()
    elif args.node:
        run_node()
    elif args.logs:
        tail_logs()
    elif args.tail:
        show_recent_logs(args.tail)
    elif args.grep:
        grep_logs(args.grep)
    else:
        # Modo interativo
        interactive_mode()

if __name__ == "__main__":
    main()
