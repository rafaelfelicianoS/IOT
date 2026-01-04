#!/usr/bin/env python3
"""
Interactive Sink - Sink Device com CLI interativo embutido.

Inicia o Sink Device e abre uma CLI interativa para controle e monitoramento.
"""

import sys
import cmd
import threading
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from sync.sink_device import SinkDevice
from common.utils.logger import get_logger
from common.utils.nid import NID

logger = get_logger("interactive_sink")


class InteractiveSinkCLI(cmd.Cmd):
    """CLI interativa para controle do Sink Device."""

    intro = """
╔═══════════════════════════════════════════════════════════════╗
║              IoT Sink - Interactive CLI                      ║
╚═══════════════════════════════════════════════════════════════╝

Digite 'help' para ver comandos disponíveis.
Digite 'exit' ou Ctrl+D para sair.
"""
    prompt = "sink> "

    def __init__(self, sink: SinkDevice):
        """
        Inicializa a CLI com referência ao Sink.

        Args:
            sink: Instância do SinkDevice
        """
        super().__init__()
        self.sink = sink
        self.start_time = time.time()

    # ========================================================================
    # COMANDOS DE MONITORAMENTO
    # ========================================================================

    def do_status(self, arg):
        """
        Mostra status geral do Sink.

        Uso: status
        """
        print("\n STATUS DO SINK\n")

        # Uptime
        uptime_s = time.time() - self.start_time
        uptime_str = self._format_uptime(uptime_s)
        print(f"  UPTIME: {uptime_str}")
        print()

        # Downlinks
        with self.sink.downlinks_lock:
            n_downlinks = len(self.sink.downlinks)
            print(f" DOWNLINKS: {n_downlinks} node(s) conectado(s)")
            if n_downlinks > 0:
                for nid, address in self.sink.downlinks.items():
                    nid_short = str(nid)[:8]
                    print(f"   • {address} (NID: {nid_short}...)")
        print()

        # Heartbeats
        print(" HEARTBEATS:")
        print(f"   Sequência atual: {self.sink.heartbeat_sequence}")
        blocked = self.sink.get_blocked_heartbeat_nodes()
        if blocked:
            print(f"     {len(blocked)} node(s) bloqueado(s)")
        print()

        # Rede
        print(" REDE:")
        print(f"   Sink NID: {str(self.sink.my_nid)[:8]}...")
        print(f"   Adapter: {self.sink.adapter}")
        print(f"   GATT Server: {' Ativo' if self.sink.app else ' Inativo'}")
        print(f"   Advertisement: {' Ativo' if self.sink.advertisement else ' Inativo'}")
        print()

    def do_downlinks(self, arg):
        """
        Lista todos os Nodes conectados (downlinks).

        Uso: downlinks
        """
        print("\n DOWNLINKS CONECTADOS\n")

        with self.sink.downlinks_lock:
            if not self.sink.downlinks:
                print("(nenhum node conectado)\n")
                return

            print("┌─────────────────────┬────────────────────┬──────────────┐")
            print("│ Address             │ NID                │ Has Session  │")
            print("├─────────────────────┼────────────────────┼──────────────┤")

            for nid, address in self.sink.downlinks.items():
                nid_str = str(nid)[:16] + "..."
                has_session = "" if nid in self.sink.session_keys else ""
                print(f"│ {address:19} │ {nid_str:18} │ {has_session:12} │")

            print("└─────────────────────┴────────────────────┴──────────────┘")
            print(f"\n Total: {len(self.sink.downlinks)} downlink(s)\n")

    def do_heartbeat_stats(self, arg):
        """
        Mostra estatísticas de heartbeat.

        Uso: heartbeat_stats
        """
        print("\n HEARTBEAT STATS\n")
        print(f"   Sequência atual: {self.sink.heartbeat_sequence}")
        print(f"   Intervalo: 5.0s")
        print(f"   Total enviados: ~{self.sink.heartbeat_sequence}")
        print()

    def do_inbox(self, arg):
        """
        Mostra mensagens recebidas dos Nodes (Inbox Service).

        Uso: inbox [limit]

        Argumentos:
            limit    Número máximo de mensagens a mostrar (padrão: 20)

        Exemplo:
            inbox       - Mostra últimas 20 mensagens
            inbox 50    - Mostra últimas 50 mensagens
        """
        # Determinar limite
        limit = 20
        if arg:
            try:
                limit = int(arg)
                if limit <= 0:
                    print("\n Limite deve ser um número positivo\n")
                    return
            except ValueError:
                print("\n Limite inválido (deve ser um número)\n")
                return

        print("\n INBOX - MENSAGENS RECEBIDAS\n")

        with self.sink.inbox_lock:
            if not self.sink.inbox:
                print("(nenhuma mensagem recebida)\n")
                return

            # Pegar últimas N mensagens
            messages = self.sink.inbox[-limit:]
            total = len(self.sink.inbox)

            if total > limit:
                print(f"Mostrando {len(messages)} de {total} mensagens (use 'inbox {total}' para ver todas)\n")

            # Cabeçalho da tabela
            print("┌──────────────────────┬──────────────────────┬─────────────────────────────────┐")
            print("│ Timestamp            │ Source NID           │ Message                         │")
            print("├──────────────────────┼──────────────────────┼─────────────────────────────────┤")

            for entry in messages:
                # Formatar timestamp
                ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(entry['timestamp']))
                source_nid = entry['source_nid']
                message = entry['message']

                # Truncar mensagem se for muito longa
                if len(message) > 31:
                    message = message[:28] + "..."

                print(f"│ {ts:20} │ {source_nid:20} │ {message:31} │")

            print("└──────────────────────┴──────────────────────┴─────────────────────────────────┘")
            print(f"\n Total no inbox: {total} mensagem(ns)\n")

    # ========================================================================
    # COMANDOS DE CONTROLE
    # ========================================================================

    def do_send(self, arg):
        """
        Envia mensagem para um Node específico.

        Uso: send <nid_prefix> <message>

        Argumentos:
            nid_prefix    Primeiros caracteres do NID do Node
            message       Mensagem a enviar

        Exemplo:
            send 53a84472 Hello from Sink!
        """
        if not arg:
            print("\n Erro: argumentos insuficientes\n")
            print("   Uso: send <nid_prefix> <message>\n")
            return

        parts = arg.split(maxsplit=1)
        if len(parts) < 2:
            print("\n Erro: mensagem não especificada\n")
            print("   Uso: send <nid_prefix> <message>\n")
            return

        nid_prefix = parts[0].lower()
        message = parts[1]

        # Procurar NID que começa com o prefix
        target_nid = None
        with self.sink.downlinks_lock:
            for nid in self.sink.downlinks.keys():
                if str(nid).lower().startswith(nid_prefix):
                    target_nid = nid
                    break

        if not target_nid:
            print(f"\n Node com NID começando por '{nid_prefix}' não encontrado\n")
            print("   Use 'downlinks' para ver Nodes conectados\n")
            return

        print(f"\n Enviando mensagem para {str(target_nid)[:8]}...")
        print(f"   Mensagem: {message}")
        print("\n   Em desenvolvimento\n")

    def do_broadcast(self, arg):
        """
        Envia mensagem para TODOS os Nodes conectados.

        Uso: broadcast <message>

        Exemplo:
            broadcast Attention all nodes!
        """
        if not arg:
            print("\n Erro: mensagem não especificada\n")
            print("   Uso: broadcast <message>\n")
            return

        with self.sink.downlinks_lock:
            n_downlinks = len(self.sink.downlinks)

        if n_downlinks == 0:
            print("\n  Nenhum Node conectado para broadcast\n")
            return

        print(f"\n Broadcasting para {n_downlinks} Node(s)...")
        print(f"   Mensagem: {arg}")
        print("\n   Em desenvolvimento\n")

    # ========================================================================
    # COMANDOS DE DEBUGGING
    # ========================================================================

    def do_session_keys(self, arg):
        """
        Lista session keys estabelecidas.

        Uso: session_keys
        """
        print("\n SESSION KEYS\n")

        with self.sink.session_keys_lock:
            if not self.sink.session_keys:
                print("(nenhuma session key estabelecida)\n")
                return

            for nid, key in self.sink.session_keys.items():
                nid_str = str(nid)[:16]
                key_hex = key[:8].hex()
                print(f"   {nid_str}... → {key_hex}...")

        print()

    def do_my_nid(self, arg):
        """
        Mostra o NID do Sink.

        Uso: my_nid
        """
        print(f"\n Meu NID: {self.sink.my_nid}\n")

    # ========================================================================
    # COMANDOS DE SIMULAÇÃO
    # ========================================================================

    def do_stop_heartbeat(self, arg):
        """
        [LIMITAÇÃO] Marca node para bloqueio de heartbeat (D-Bus GATT sempre faz broadcast).

        Uso: stop_heartbeat <NID ou índice>

        Nota: D-Bus GATT não suporta notificações unicast. Use 'disconnect' para simular link failure.
        """
        if not arg:
            print("\n Erro: Especifique o NID ou índice do node\n")
            print("Uso: stop_heartbeat <NID ou índice>")
            print("\nNodes conectados:")
            self._list_downlinks_with_index()
            return

        # Tentar converter para índice
        target_nid = None
        try:
            index = int(arg.strip())
            with self.sink.downlinks_lock:
                downlinks_list = list(self.sink.downlinks.keys())
                if 0 < index <= len(downlinks_list):
                    target_nid = downlinks_list[index - 1]
                else:
                    print(f"\n Erro: Índice {index} inválido (1-{len(downlinks_list)})\n")
                    return
        except ValueError:
            # Não é número, tratar como NID
            nid_str = arg.strip()

            # Procurar NID que comece com a string fornecida
            with self.sink.downlinks_lock:
                for nid in self.sink.downlinks.keys():
                    if str(nid).startswith(nid_str):
                        target_nid = nid
                        break

            if not target_nid:
                print(f"\n Erro: NID '{nid_str}' não encontrado\n")
                print("Nodes conectados:")
                self._list_downlinks_with_index()
                return

        self.sink.block_heartbeat(target_nid)
        nid_short = str(target_nid)[:16]
        print(f"\n NID {nid_short}... marcado como bloqueado")
        print(f"   Nota: D-Bus GATT envia broadcast para todos os clientes")
        print(f"   Use 'disconnect {arg}' para simular link failure\n")

    def do_resume_heartbeat(self, arg):
        """
        Resume envio de heartbeats para um node.

        Uso: resume_heartbeat <NID ou índice>

        Exemplos:
          resume_heartbeat 1                  # Resume heartbeats para o primeiro node bloqueado
          resume_heartbeat abc123...          # Resume heartbeats para node com NID específico
        """
        if not arg:
            print("\n Erro: Especifique o NID ou índice do node\n")
            print("Uso: resume_heartbeat <NID ou índice>")
            print("\nNodes com heartbeat bloqueado:")
            self._list_blocked_nodes()
            return

        # Tentar converter para índice
        target_nid = None
        try:
            index = int(arg.strip())
            blocked = self.sink.get_blocked_heartbeat_nodes()
            blocked_list = list(blocked)
            if 0 < index <= len(blocked_list):
                target_nid = blocked_list[index - 1]
            else:
                print(f"\n Erro: Índice {index} inválido (1-{len(blocked_list)})\n")
                return
        except ValueError:
            # Não é número, tratar como NID
            nid_str = arg.strip()

            # Procurar NID que comece com a string fornecida
            blocked = self.sink.get_blocked_heartbeat_nodes()
            for nid in blocked:
                if str(nid).startswith(nid_str):
                    target_nid = nid
                    break

            if not target_nid:
                print(f"\n Erro: NID '{nid_str}' não encontrado entre os bloqueados\n")
                print("Nodes com heartbeat bloqueado:")
                self._list_blocked_nodes()
                return

        # Desbloquear heartbeats para o node
        self.sink.unblock_heartbeat(target_nid)
        nid_short = str(target_nid)[:16]
        print(f"\n Heartbeats DESBLOQUEADOS para {nid_short}...")
        print(f"   O node voltará a receber heartbeats no próximo ciclo\n")

    def do_blocked_heartbeats(self, arg):
        """
        Lista nodes com heartbeat bloqueado.

        Uso: blocked_heartbeats
        """
        print("\n NODES COM HEARTBEAT BLOQUEADO\n")
        self._list_blocked_nodes()

    # ========================================================================
    # COMANDOS DE UTILIDADE
    # ========================================================================

    def do_clear(self, arg):
        """Limpa a tela."""
        import os
        os.system('clear' if os.name != 'nt' else 'cls')

    def do_exit(self, arg):
        """Sai do CLI (e para o Sink)."""
        print("\n  Parando Sink Device...")
        self.sink.stop()
        print(" Até logo!\n")
        return True

    def do_quit(self, arg):
        """Alias para exit."""
        return self.do_exit(arg)

    def do_EOF(self, arg):
        """Handle Ctrl+D."""
        print()
        return self.do_exit(arg)

    # ========================================================================
    # MÉTODOS AUXILIARES
    # ========================================================================

    def _list_downlinks_with_index(self):
        """Lista downlinks com índices para facilitar seleção."""
        with self.sink.downlinks_lock:
            if not self.sink.downlinks:
                print("   (nenhum node conectado)")
                return

            for idx, (nid, addr) in enumerate(self.sink.downlinks.items(), 1):
                nid_short = str(nid)[:16]
                print(f"   {idx}. {nid_short}... (addr: {addr})")

        print()

    def _list_blocked_nodes(self):
        """Lista nodes com heartbeat bloqueado."""
        blocked = self.sink.get_blocked_heartbeat_nodes()

        if not blocked:
            print("   (nenhum node com heartbeat bloqueado)\n")
            return

        for idx, nid in enumerate(blocked, 1):
            nid_short = str(nid)[:16]
            print(f"   {idx}. {nid_short}...")

        print()

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
        """Não faz nada quando linha vazia."""
        pass


def main():
    """Main function - inicia Sink com CLI interativo."""
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="Interactive Sink - Sink Device com CLI")
    parser.add_argument('adapter', help="BLE adapter (ex: hci0)")
    parser.add_argument('--cert', type=Path, required=True, help="Certificado do Sink")
    parser.add_argument('--key', type=Path, required=True, help="Chave privada do Sink")
    parser.add_argument('--ca-cert', type=Path, required=True, help="Certificado CA")

    args = parser.parse_args()

    try:
        sink = SinkDevice(
            adapter=args.adapter,
            cert_path=args.cert,
            key_path=args.key,
            ca_cert_path=args.ca_cert,
        )

        # Setup GATT Server e Advertising
        sink.setup_gatt_server()
        sink.setup_advertising()

        # Registar GATT application
        import dbus
        adapter_path = f"/org/bluez/{args.adapter}"
        adapter_obj = sink.bus.get_object('org.bluez', adapter_path)
        gatt_manager = dbus.Interface(adapter_obj, 'org.bluez.GattManager1')
        gatt_manager.RegisterApplication(
            sink.app.get_path(), {},
            reply_handler=lambda: logger.info(" GATT application registada!"),
            error_handler=lambda e: logger.error(f" Falha ao registar: {e}")
        )

        # Registar advertisement
        ad_manager = dbus.Interface(adapter_obj, 'org.bluez.LEAdvertisingManager1')
        ad_manager.RegisterAdvertisement(
            sink.advertisement.get_path(), {},
            reply_handler=lambda: logger.info(" Advertisement registado!"),
            error_handler=lambda e: logger.error(f" Falha ao registar advertisement: {e}")
        )

        # Iniciar heartbeat service
        sink.start_heartbeat_service()
        sink.running = True

        # Iniciar GLib mainloop em thread separada
        from gi.repository import GLib
        mainloop = GLib.MainLoop()

        def run_mainloop():
            try:
                mainloop.run()
            except Exception as e:
                logger.error(f"Erro no mainloop: {e}")

        mainloop_thread = threading.Thread(target=run_mainloop, daemon=True)
        mainloop_thread.start()

        logger.info(" Sink Device iniciado - CLI interativo pronto")

        # Iniciar CLI interativa
        cli = InteractiveSinkCLI(sink)

        def signal_handler(sig, frame):
            print(f"\nSinal {sig} recebido")
            sink.stop()
            if mainloop.is_running():
                mainloop.quit()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Run CLI
        cli.cmdloop()

        # Cleanup
        sink.stop()
        if mainloop.is_running():
            mainloop.quit()

    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
