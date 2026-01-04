#!/usr/bin/env python3
"""
Sink CLI - Interface de linha de comando para monitoramento e controle do Sink.

Permite:
- Monitorar status do Sink (uptime, downlinks conectados, heartbeat stats)
- Visualizar Nodes conectados com detalhes
- Controlar heartbeats (intervalo, pause/resume)
- Enviar mensagens para Nodes
- Ver logs em tempo real
- Debugging (routes, inspect nodes)
"""

import sys
import cmd
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils.logger import setup_logger

# Setup logger
logger = setup_logger("sink_cli")


class SinkCLI(cmd.Cmd):
    """CLI interativa para monitoramento e controle do Sink."""

    intro = """
================================================================
                    IoT Sink - CLI Interface                   
================================================================

Digite 'help' para ver comandos disponíveis.
Digite 'exit' ou Ctrl+D para sair.

NOTA: Este CLI está em desenvolvimento. Muitos comandos ainda não
      estão totalmente implementados.
"""
    prompt = "sink> "

    def __init__(self):
        """Inicializa a CLI."""
        super().__init__()

        # TODO: Conectar a uma instância real do Sink
        # Por enquanto, modo standalone para demonstração
        self.sink = None
        self.start_time = time.time()

        print("  CLI em modo STANDALONE - conecte a um Sink real para funcionalidade completa\n")

    # ========================================================================
    # COMANDOS DE MONITORAMENTO
    # ========================================================================

    def do_status(self, arg):
        """
        Mostra status geral do Sink.

        Uso: status

        Exibe:
        - Uptime
        - Número de downlinks conectados
        - Estatísticas de heartbeat
        - NID do Sink
        """
        print("\n STATUS DO SINK\n")

        # Uptime
        uptime_s = time.time() - self.start_time
        uptime_str = self._format_uptime(uptime_s)
        print(f"  UPTIME: {uptime_str}")
        print()

        # TODO: Obter dados reais do Sink
        print(" DOWNLINKS:")
        print("   Total conectados: 0 nodes")
        print("   Autenticados: 0 nodes")
        print("   Pendentes auth: 0 nodes")
        print()

        print(" HEARTBEATS:")
        print("   Intervalo: 5.0s")
        print("   Total enviados: 0")
        print("   Última transmissão: N/A")
        print()

        print(" REDE:")
        print("   Sink NID: <unknown>")
        print("   Adapter: hci0")
        print("   GATT Server:  Ativo")
        print("   Advertisement:  Ativo")
        print()

    def do_downlinks(self, arg):
        """
        Lista todos os Nodes conectados (downlinks).

        Uso: downlinks

        Mostra tabela com:
        - Address BLE
        - NID
        - RSSI (se disponível)
        - Hop count
        - Status de autenticação
        - Tempo de conexão
        """
        print("\n DOWNLINKS CONECTADOS\n")

        # TODO: Obter dados reais do Sink
        print("+---------------------+--------------+---------+-----+----------+----------+")
        print("| Address             | NID          | RSSI    | Hop | Auth     | Uptime   |")
        print("+---------------------+--------------+---------+-----+----------+----------+")
        print("| (nenhum)            |              |         |     |          |          |")
        print("+---------------------+--------------+---------+-----+----------+----------+")
        print("\n Total: 0 downlinks\n")

    def do_stats(self, arg):
        """
        Mostra estatísticas detalhadas do Sink.

        Uso: stats

        Exibe:
        - Pacotes enviados/recebidos
        - Heartbeats transmitidos
        - Erros de autenticação
        - Replay attacks bloqueados
        """
        print("\n ESTATÍSTICAS DETALHADAS\n")

        print(" PACOTES:")
        print("   Enviados: 0")
        print("   Recebidos: 0")
        print("   Descartados: 0")
        print()

        print(" HEARTBEATS:")
        print("   Enviados: 0")
        print("   Sequência atual: 0")
        print()

        print(" SEGURANÇA:")
        print("   Autenticações bem-sucedidas: 0")
        print("   Autenticações falhadas: 0")
        print("   Replay attacks bloqueados: 0")
        print("   MACs inválidos: 0")
        print()

        print("  ERROS:")
        print("   Erros de conexão: 0")
        print("   Timeouts: 0")
        print()

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
            print("\n Erro: argumento deve ser um número\n")
            return

        print(f"\n Últimos {n} logs:\n")
        print("  Funcionalidade não implementada ainda.\n")
        print("   Use 'tail -f logs/iot-network.log' para ver logs em tempo real.\n")

    # ========================================================================
    # COMANDOS DE CONTROLE
    # ========================================================================

    def do_heartbeat_interval(self, arg):
        """
        Mostra ou define o intervalo de heartbeat.

        Uso: heartbeat_interval [SECONDS]

        Argumentos:
            SECONDS    Novo intervalo em segundos (padrão: mostra atual)
        """
        if not arg:
            print("\n Intervalo de heartbeat: 5.0 segundos\n")
            return

        try:
            interval = float(arg)
            if interval < 1.0 or interval > 60.0:
                print("\n Erro: intervalo deve estar entre 1.0 e 60.0 segundos\n")
                return

            print(f"\n  Funcionalidade não implementada ainda.")
            print(f"   Intervalo seria alterado para {interval}s\n")
        except ValueError:
            print("\n Erro: argumento deve ser um número\n")

    def do_pause_heartbeat(self, arg):
        """
        Pausa o envio de heartbeats.

        Uso: pause_heartbeat

        AVISO: Todos os Nodes vão desconectar após 15s (3 heartbeats perdidos)!
        """
        print("\n Pausando heartbeats...")
        print("  Funcionalidade não implementada ainda.\n")

    def do_resume_heartbeat(self, arg):
        """
        Resume o envio de heartbeats.

        Uso: resume_heartbeat
        """
        print("\n Resumindo heartbeats...")
        print("  Funcionalidade não implementada ainda.\n")

    def do_disconnect(self, arg):
        """
        Desconecta um Node específico.

        Uso: disconnect <nid|address>

        Argumentos:
            nid        NID do Node (primeiros 8 caracteres)
            address    Endereço BLE do Node
        """
        if not arg:
            print("\n Erro: especifique NID ou address do Node\n")
            print("   Uso: disconnect <nid|address>\n")
            return

        print(f"\n Desconectando {arg}...")
        print("  Funcionalidade não implementada ainda.\n")

    def do_disconnect_all(self, arg):
        """
        Desconecta TODOS os Nodes.

        Uso: disconnect_all

        AVISO: Isto vai desconectar todos os downlinks!
        """
        print("\n  AVISO: Desconectar TODOS os Nodes!")
        confirm = input("   Digite 'yes' para confirmar: ")

        if confirm.lower() == 'yes':
            print("\n Desconectando todos os Nodes...")
            print("  Funcionalidade não implementada ainda.\n")
        else:
            print("\n Operação cancelada.\n")

    # ========================================================================
    # COMANDOS DE COMUNICAÇÃO
    # ========================================================================

    def do_send(self, arg):
        """
        Envia mensagem para um Node específico.

        Uso: send <nid> <message>

        Argumentos:
            nid        NID do Node destino
            message    Mensagem a enviar (texto)

        Exemplo:
            send 53a84472 Hello from Sink!
        """
        if not arg:
            print("\n Erro: argumentos insuficientes\n")
            print("   Uso: send <nid> <message>\n")
            return

        parts = arg.split(maxsplit=1)
        if len(parts) < 2:
            print("\n Erro: mensagem não especificada\n")
            print("   Uso: send <nid> <message>\n")
            return

        nid = parts[0]
        message = parts[1]

        print(f"\n Enviando mensagem para {nid}...")
        print(f"   Mensagem: {message}")
        print("  Funcionalidade não implementada ainda.\n")

    def do_broadcast(self, arg):
        """
        Envia mensagem para TODOS os Nodes conectados.

        Uso: broadcast <message>

        Argumentos:
            message    Mensagem a enviar (texto)

        Exemplo:
            broadcast Attention all nodes!
        """
        if not arg:
            print("\n Erro: mensagem não especificada\n")
            print("   Uso: broadcast <message>\n")
            return

        print(f"\n Broadcasting para todos os Nodes...")
        print(f"   Mensagem: {arg}")
        print("  Funcionalidade não implementada ainda.\n")

    # ========================================================================
    # COMANDOS DE DEBUGGING
    # ========================================================================

    def do_inspect(self, arg):
        """
        Mostra detalhes completos sobre um Node.

        Uso: inspect <nid|address>

        Mostra:
        - Certificado (NID, validade, issuer)
        - Session key (se existe)
        - Replay window
        - Estatísticas de pacotes
        """
        if not arg:
            print("\n Erro: especifique NID ou address do Node\n")
            print("   Uso: inspect <nid|address>\n")
            return

        print(f"\n DETALHES DO NODE: {arg}\n")
        print("  Funcionalidade não implementada ainda.\n")

    def do_routes(self, arg):
        """
        Mostra tabela de rotas conhecidas (forwarding table).

        Uso: routes
        """
        print("\n  TABELA DE ROTAS\n")
        print("  Funcionalidade não implementada ainda.\n")
        print("   Sink não mantém forwarding table (é o destino final).\n")

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
        print("\n Até logo!\n")
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
        SinkCLI().cmdloop()
    except KeyboardInterrupt:
        print("\n\n Até logo!\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
