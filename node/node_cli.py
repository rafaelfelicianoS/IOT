#!/usr/bin/env python3
"""
Node CLI - Interface de linha de comando para monitoramento e controle do Node.

Permite:
- Monitorar status do Node (uplink, downlinks, hop_count)
- Visualizar heartbeats recebidos
- Controlar conexão (connect, disconnect, reconnect)
- Enviar mensagens ao Sink
- Ver logs em tempo real
- Debugging (session keys, replay window, certificados)
"""

import sys
import cmd
import time
from pathlib import Path
from typing import Optional

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.logger import setup_logger

# Setup logger
logger = setup_logger("node_cli")


class NodeCLI(cmd.Cmd):
    """CLI interativa para monitoramento e controle do Node."""

    intro = """
╔═══════════════════════════════════════════════════════════════╗
║                    IoT Node - CLI Interface                   ║
╚═══════════════════════════════════════════════════════════════╝

Digite 'help' para ver comandos disponíveis.
Digite 'exit' ou Ctrl+D para sair.

NOTA: Este CLI está em desenvolvimento. Muitos comandos ainda não
      estão totalmente implementados.
"""
    prompt = "node> "

    def __init__(self):
        """Inicializa a CLI."""
        super().__init__()

        # TODO: Conectar a uma instância real do Node
        # Por enquanto, modo standalone para demonstração
        self.node = None
        self.start_time = time.time()

        print("⚠️  CLI em modo STANDALONE - conecte a um Node real para funcionalidade completa\n")

    # ========================================================================
    # COMANDOS DE MONITORAMENTO
    # ========================================================================

    def do_status(self, arg):
        """
        Mostra status completo do Node.

        Uso: status

        Exibe:
        - Uplink (conectado?, NID, RSSI)
        - Downlinks (quantos Nodes conectados abaixo)
        - Hop count atual
        - Status de autenticação
        - Heartbeat stats
        - Role (Server/Client/Both)
        """
        print("\n╔═══════════════════════════════════════════════════════════════╗")
        print("║                  IoT Node - Status (hop=?)                    ║")
        print("╚═══════════════════════════════════════════════════════════════╝\n")

        # Uptime
        uptime_s = time.time() - self.start_time
        uptime_str = self._format_uptime(uptime_s)
        print(f"⏱️  UPTIME: {uptime_str}\n")

        # TODO: Obter dados reais do Node
        print("🔼 UPLINK:")
        print("   Status: 🔴 Desconectado")
        print("   Tipo: N/A")
        print("   NID: N/A")
        print("   Address: N/A")
        print("   RSSI: N/A")
        print("   Meu hop: ? (desconhecido)")
        print()

        print("🔽 DOWNLINKS:")
        print("   Total: 0 nodes")
        print("   (nenhum)")
        print()

        print("🌐 PAPEL:")
        print("   GATT Server: ❓ Desconhecido")
        print("   GATT Client: ❓ Desconhecido")
        print()

        print("🔐 AUTENTICAÇÃO:")
        print("   Uplink: 🔴 Não autenticado")
        print("   Session Key: ❌ Não estabelecida")
        print()

        print("💓 HEARTBEATS:")
        print("   Recebidos (uplink): 0")
        print("   Último: N/A")
        print("   Perdidos: 0")
        print("   Enviados (downlinks): 0")
        print()

        print("📊 ROUTING:")
        print("   Pacotes roteados: 0")
        print("   Pacotes originados: 0")
        print("   Pacotes entregues: 0")
        print()

    def do_uplink(self, arg):
        """
        Mostra informações detalhadas sobre o uplink.

        Uso: uplink

        Exibe:
        - NID do uplink
        - Address BLE
        - RSSI atual
        - Hop count do uplink
        - Tipo (Sink ou Node)
        - Tempo de conexão
        - Último heartbeat recebido
        """
        print("\n🔼 UPLINK DETALHADO\n")

        # TODO: Obter dados reais
        print("Status: 🔴 Desconectado\n")
        print("⚠️  Sem uplink conectado. Use 'scan' e 'connect' para estabelecer uplink.\n")

    def do_downlinks(self, arg):
        """
        Lista todos os Nodes conectados abaixo (downlinks).

        Uso: downlinks

        Mostra tabela com:
        - Address BLE
        - NID
        - Hop count
        - Status de autenticação
        - Tempo de conexão
        """
        print("\n🔽 DOWNLINKS CONECTADOS\n")

        # TODO: Obter dados reais
        print("┌─────────────────────┬──────────────┬─────┬──────────┬──────────┐")
        print("│ Address             │ NID          │ Hop │ Auth     │ Uptime   │")
        print("├─────────────────────┼──────────────┼─────┼──────────┼──────────┤")
        print("│ (nenhum)            │              │     │          │          │")
        print("└─────────────────────┴──────────────┴─────┴──────────┴──────────┘")
        print("\n📊 Total: 0 downlinks\n")

    def do_neighbors(self, arg):
        """
        Lista vizinhos descobertos (candidates para uplink).

        Uso: neighbors

        Mostra:
        - Sinks e Nodes descobertos no último scan
        - Hop count de cada um
        - RSSI
        - Recomendação de melhor uplink
        """
        print("\n📡 VIZINHOS DESCOBERTOS\n")

        # TODO: Obter dados reais
        print("┌─────────────────────┬──────────────┬─────┬────────┬─────────┬──────────┐")
        print("│ Address             │ NID          │ Hop │ Type   │ RSSI    │ Status   │")
        print("├─────────────────────┼──────────────┼─────┼────────┼─────────┼──────────┤")
        print("│ (nenhum)            │              │     │        │         │          │")
        print("└─────────────────────┴──────────────┴─────┴────────┴─────────┴──────────┘")
        print("\n💡 Use 'scan' para descobrir vizinhos disponíveis.\n")

    def do_topology(self, arg):
        """
        Visualiza topologia conhecida da rede.

        Uso: topology

        Mostra árvore de conexões conhecidas.
        """
        print("\n🌳 TOPOLOGIA DA REDE\n")
        print("⚠️  Funcionalidade não implementada ainda.\n")

    def do_stats(self, arg):
        """
        Mostra estatísticas detalhadas do Node.

        Uso: stats

        Exibe:
        - Mensagens enviadas/recebidas
        - Heartbeats recebidos
        - Latência média
        - Pacotes roteados
        """
        print("\n📈 ESTATÍSTICAS DETALHADAS\n")

        print("📦 PACOTES:")
        print("   Enviados ao uplink: 0")
        print("   Recebidos do uplink: 0")
        print("   Recebidos de downlinks: 0")
        print("   Forwardados: 0")
        print()

        print("💓 HEARTBEATS:")
        print("   Recebidos: 0")
        print("   Perdidos: 0 (0.0%)")
        print("   Latência média: N/A")
        print()

        print("🔐 SEGURANÇA:")
        print("   Replay attacks bloqueados: 0")
        print("   MACs inválidos: 0")
        print()

    def do_heartbeats(self, arg):
        """
        Lista últimos heartbeats recebidos.

        Uso: heartbeats [N]

        Argumentos:
            N    Número de heartbeats a mostrar (padrão: 10)
        """
        try:
            n = int(arg) if arg else 10
        except ValueError:
            print("\n❌ Erro: argumento deve ser um número\n")
            return

        print(f"\n�� Últimos {n} Heartbeats Recebidos:\n")

        # TODO: Obter dados reais
        print("┌─────┬──────────────────────┬──────────┬─────────┐")
        print("│ Seq │ Timestamp            │ Latency  │ Status  │")
        print("├─────┼──────────────────────┼──────────┼─────────┤")
        print("│ (nenhum heartbeat recebido ainda)               │")
        print("└─────┴──────────────────────┴──────────┴─────────┘")
        print()

    # ========================================================================
    # COMANDOS DE CONEXÃO
    # ========================================================================

    def do_scan(self, arg):
        """
        Procura por Sinks e Nodes disponíveis.

        Uso: scan [TIMEOUT]

        Argumentos:
            TIMEOUT    Timeout em segundos (padrão: 5)

        Procura dispositivos com melhor hop_count para estabelecer uplink.
        """
        try:
            timeout = int(arg) if arg else 5
        except ValueError:
            print("\n❌ Erro: argumento deve ser um número\n")
            return

        print(f"\n🔍 A fazer scan por {timeout}s...\n")
        print("⚠️  Funcionalidade não implementada ainda.\n")

    def do_connect(self, arg):
        """
        Conecta a um uplink específico.

        Uso: connect <address>

        Argumentos:
            address    Endereço BLE do dispositivo (Sink ou Node)

        Exemplo:
            connect E0:D3:62:D6:EE:A0
        """
        if not arg:
            print("\n❌ Erro: especifique o address do uplink\n")
            print("   Uso: connect <address>\n")
            return

        address = arg.strip().upper()
        print(f"\n🔗 A conectar a {address}...\n")
        print("⚠️  Funcionalidade não implementada ainda.\n")

    def do_disconnect(self, arg):
        """
        Desconecta do uplink atual.

        Uso: disconnect

        AVISO: Isto vai desconectar TODOS os downlinks em cascata!
        """
        print("\n⚠️  AVISO: Desconectar uplink vai desconectar TODOS os downlinks!")
        confirm = input("   Digite 'yes' para confirmar: ")

        if confirm.lower() == 'yes':
            print("\n🔌 Desconectando do uplink...\n")
            print("⚠️  Funcionalidade não implementada ainda.\n")
        else:
            print("\n❌ Operação cancelada.\n")

    def do_reconnect(self, arg):
        """
        Força reconexão ao uplink.

        Uso: reconnect

        Desconecta e reconecta ao mesmo uplink.
        """
        print("\n🔄 A reconectar...\n")
        print("⚠️  Funcionalidade não implementada ainda.\n")

    # ========================================================================
    # COMANDOS DE COMUNICAÇÃO
    # ========================================================================

    def do_send(self, arg):
        """
        Envia mensagem ao Sink (via uplink).

        Uso: send <message>

        Argumentos:
            message    Mensagem a enviar (texto)

        Exemplo:
            send Hello from Node!
        """
        if not arg:
            print("\n❌ Erro: mensagem não especificada\n")
            print("   Uso: send <message>\n")
            return

        print(f"\n📤 Enviando mensagem ao Sink via uplink...")
        print(f"   Mensagem: {arg}")
        print("⚠️  Funcionalidade não implementada ainda.\n")

    def do_ping(self, arg):
        """
        Envia ping ao Sink e mede latência.

        Uso: ping [COUNT]

        Argumentos:
            COUNT    Número de pings (padrão: 4)
        """
        try:
            count = int(arg) if arg else 4
        except ValueError:
            print("\n❌ Erro: argumento deve ser um número\n")
            return

        print(f"\n🏓 Enviando {count} pings ao Sink...\n")
        print("⚠️  Funcionalidade não implementada ainda.\n")

    # ========================================================================
    # COMANDOS DE DEBUGGING
    # ========================================================================

    def do_role(self, arg):
        """
        Mostra papel atual do Node (Server/Client/Both).

        Uso: role
        """
        print("\n🌐 PAPEL DO NODE\n")
        print("   GATT Server: ❓ Desconhecido (aceita downlinks)")
        print("   GATT Client: ❓ Desconhecido (conecta a uplink)")
        print()

    def do_hop_count(self, arg):
        """
        Mostra hop_count atual (distância ao Sink).

        Uso: hop_count
        """
        print("\n📏 HOP COUNT\n")
        print("   Atual: ? (desconhecido)")
        print("   Uplink hop: N/A")
        print()
        print("💡 Hop count é calculado baseado no uplink:")
        print("   - Conectado ao Sink (hop=255) → meu hop=0")
        print("   - Conectado a Node (hop=N) → meu hop=N+1")
        print()

    def do_routes(self, arg):
        """
        Mostra tabela de rotas aprendidas (forwarding table).

        Uso: routes
        """
        print("\n🗺️  TABELA DE ROTAS\n")

        # TODO: Obter dados reais
        print("┌──────────────┬─────────────────────┬─────┬──────────┬──────────┐")
        print("│ Destino NID  │ Next Hop Address    │ Hop │ Via      │ Learned  │")
        print("├──────────────┼─────────────────────┼─────┼──────────┼──────────┤")
        print("│ (nenhuma rota aprendida ainda)                                 │")
        print("└──────────────┴─────────────────────┴─────┴──────────┴──────────┘")
        print()

    def do_inspect_uplink(self, arg):
        """
        Mostra detalhes sobre o uplink (session key, auth status).

        Uso: inspect_uplink
        """
        print("\n🔍 DETALHES DO UPLINK\n")
        print("   Status: 🔴 Desconectado")
        print()

    def do_cert_info(self, arg):
        """
        Mostra informações do certificado do Node.

        Uso: cert_info

        Exibe:
        - NID
        - Validade
        - Issuer (CA)
        - Se é certificado de Sink ou Node
        """
        print("\n📜 CERTIFICADO DO NODE\n")
        print("⚠️  Funcionalidade não implementada ainda.\n")

    def do_logs(self, arg):
        """
        Mostra últimos N logs.

        Uso: logs [N]

        Argumentos:
            N    Número de logs a mostrar (padrão: 20)
        """
        try:
            n = int(arg) if arg else 20
        except ValueError:
            print("\n❌ Erro: argumento deve ser um número\n")
            return

        print(f"\n📋 Últimos {n} logs:\n")
        print("⚠️  Funcionalidade não implementada ainda.\n")
        print("   Use 'tail -f logs/iot-network.log' para ver logs em tempo real.\n")

    # ========================================================================
    # COMANDOS DE UTILIDADE
    # ========================================================================

    def do_clear(self, arg):
        """
        Limpa a tela.

        Uso: clear
        """
        import os
        os.system('clear' if os.name != 'nt' else 'cls')

    def do_exit(self, arg):
        """
        Sai do CLI.

        Uso: exit
        """
        print("\n👋 Até logo!\n")
        return True

    def do_quit(self, arg):
        """Alias para exit."""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Handle Ctrl+D."""
        print()  # New line
        return self.do_exit(arg)

    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================

    def _format_uptime(self, seconds: float) -> str:
        """Formata uptime em formato legível."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return " ".join(parts)

    def emptyline(self):
        """Não faz nada quando linha vazia (não repete último comando)."""
        pass


def main():
    """Main function."""
    try:
        NodeCLI().cmdloop()
    except KeyboardInterrupt:
        print("\n\n👋 Até logo!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
