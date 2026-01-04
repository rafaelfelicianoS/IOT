#!/usr/bin/env python3
"""
Interactive Node - Node Device com CLI interativo embutido.

Inicia o Node Device e abre uma CLI interativa para controle e monitoramento.
Permite comandos como scan, connect, disconnect, send, etc.
"""

import sys
import cmd
import threading
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from node.iot_node import IoTNode
from common.utils.logger import get_logger
from common.utils.nid import NID

logger = get_logger("interactive_node")


class InteractiveNodeCLI(cmd.Cmd):
    """CLI interativa para controle do Node Device."""

    intro = """
===================================================================
              IoT Node - Interactive CLI                      
===================================================================

Digite 'help' para ver comandos disponíveis.
Digite 'exit' ou Ctrl+D para sair.

Comandos principais:
  scan          - Procurar Sinks/Nodes disponíveis
  connect       - Conectar a um uplink
  disconnect    - Desconectar do uplink
  send          - Enviar mensagem ao Sink
  status        - Ver status da conexão
"""
    prompt = "node> "

    def __init__(self, node: IoTNode):
        """
        Inicializa a CLI com referência ao Node.

        Args:
            node: Instância do IoTNode
        """
        super().__init__()
        self.node = node
        self.start_time = time.time()
        self.discovered_devices = []  # Lista de dispositivos encontrados no scan

    # ========================================================================
    # COMANDOS DE MONITORAMENTO
    # ========================================================================

    def do_status(self, arg):
        """
        Mostra status completo do Node.

        Uso: status
        """
        print("\n===================================================================")
        hop_str = str(self.node.hop_count) if self.node.hop_count >= 0 else "?"
        print(f"              IoT Node - Status (hop={hop_str})                    ")
        print("===================================================================\n")

        # Uptime
        uptime_s = time.time() - self.start_time
        uptime_str = self._format_uptime(uptime_s)
        print(f"  UPTIME: {uptime_str}\n")

        # Uplink
        print(" UPLINK:")
        if self.node.uplink_connection and self.node.uplink_connection.is_connected:
            print(f"   Status:  Conectado")
            if self.node.uplink_nid:
                print(f"   NID: {str(self.node.uplink_nid)[:16]}...")
            if self.node.uplink_device:
                print(f"   Address: {self.node.uplink_device.address}")
            print(f"   Authenticated: {'Sim' if self.node.authenticated else 'Nao'}")
            with self.node.hop_count_lock:
                print(f"   Meu hop: {self.node.hop_count}")
        else:
            print("   Status:  Desconectado")
            print("    Use 'scan' e 'connect' para estabelecer uplink")
        print()

        # Downlinks
        with self.node.downlinks_lock:
            n_downlinks = len(self.node.downlinks)
            print(f" DOWNLINKS: {n_downlinks} node(s)")
            if n_downlinks > 0:
                for address, nid in self.node.downlinks.items():
                    nid_short = str(nid)[:8]
                    print(f"   • {address} (NID: {nid_short}...)")
        print()

        # Autenticação
        print(" AUTENTICAÇÃO:")
        print(f"   Uplink: {'Autenticado' if self.node.authenticated else 'Nao autenticado'}")
        with self.node.uplink_session_key_lock:
            has_key = self.node.uplink_session_key is not None
            print(f"   Session Key: {'Estabelecida' if has_key else 'Nao estabelecida'}")
        print()

        # Heartbeats
        print(" HEARTBEATS:")
        if self.node.last_heartbeat_time > 0:
            time_since = time.time() - self.node.last_heartbeat_time
            print(f"   Último recebido: {time_since:.1f}s atrás")
            print(f"   Sequência: {self.node.heartbeat_sequence}")
        else:
            print("   Nenhum heartbeat recebido ainda")
        print()

        # Rede
        print(" REDE:")
        print(f"   Meu NID: {str(self.node.my_nid)[:16]}...")
        print(f"   Adapter: hci{self.node.adapter_index}")
        print(f"   GATT Server: {'Ativo' if self.node.app else 'Inativo'}")
        print(f"   GATT Client: Ativo")
        print()

    def do_uplink(self, arg):
        """
        Mostra informações detalhadas sobre o uplink.

        Uso: uplink
        """
        print("\n UPLINK DETALHADO\n")

        if not self.node.uplink_connection or not self.node.uplink_connection.is_connected:
            print("Status:  Desconectado\n")
            print("  Sem uplink conectado. Use 'scan' e 'connect' para estabelecer uplink.\n")
            return

        print("Status:  Conectado\n")

        if self.node.uplink_device:
            print(f"Address: {self.node.uplink_device.address}")
            if hasattr(self.node.uplink_device, 'rssi'):
                print(f"RSSI: {self.node.uplink_device.rssi} dBm")

        if self.node.uplink_nid:
            print(f"NID: {self.node.uplink_nid}")

        print(f"Authenticated: {'Sim' if self.node.authenticated else 'Nao'}")

        with self.node.hop_count_lock:
            print(f"Meu hop count: {self.node.hop_count}")

        if self.node.last_heartbeat_time > 0:
            time_since = time.time() - self.node.last_heartbeat_time
            print(f"Último heartbeat: {time_since:.1f}s atrás (seq={self.node.heartbeat_sequence})")

        print()

    def do_downlinks(self, arg):
        """
        Lista todos os Nodes conectados abaixo (downlinks).

        Uso: downlinks
        """
        print("\n DOWNLINKS CONECTADOS\n")

        with self.node.downlinks_lock:
            if not self.node.downlinks:
                print("(nenhum node conectado)\n")
                return

            print("+---------------------+--------------------+--------------+")
            print("| Address             | NID                | Has Session  |")
            print("+---------------------+--------------------+--------------+")

            for address, nid in self.node.downlinks.items():
                nid_str = str(nid)[:16] + "..."
                with self.node.downlink_session_keys_lock:
                    has_session = "Sim" if nid in self.node.downlink_session_keys else "Nao"
                print(f"| {address:19} | {nid_str:18} | {has_session:12} |")

            print("+---------------------+--------------------+--------------+")
            print(f"\n Total: {len(self.node.downlinks)} downlink(s)\n")

    def do_my_nid(self, arg):
        """
        Mostra o NID do Node.

        Uso: my_nid
        """
        print(f"\n Meu NID: {self.node.my_nid}\n")

    # ========================================================================
    # COMANDOS DE CONEXÃO
    # ========================================================================

    def do_scan(self, arg):
        """
        Procura por Sinks e Nodes disponíveis.

        Uso: scan [TIMEOUT]

        Argumentos:
            TIMEOUT    Timeout em segundos (padrão: 10)
        """
        try:
            timeout = int(arg) if arg else 10
        except ValueError:
            print("\n Erro: argumento deve ser um número\n")
            return

        print(f"\n A fazer scan por {timeout}s...\n")

        # Fazer scan usando o ble_client diretamente para obter todos os dispositivos
        import time
        self.discovered_devices = []
        end_time = time.time() + timeout

        while time.time() < end_time:
            devices = self.node.ble_client.scan_iot_devices(duration_ms=5000)

            for device in devices:
                if not any(d.address == device.address for d in self.discovered_devices):
                    self.discovered_devices.append(device)

        if not self.discovered_devices:
            print("  Nenhum Sink/Node encontrado\n")
            print(" Certifique-se que há um Sink ou Node a fazer advertising\n")
            return

        # Mostrar lista de dispositivos encontrados
        print(f" Encontrados {len(self.discovered_devices)} dispositivo(s):\n")

        for i, device in enumerate(self.discovered_devices, 1):
            device_type = "?"
            hop_count = "?"

            if device.manufacturer_data and 0xFFFF in device.manufacturer_data:
                data = device.manufacturer_data[0xFFFF]
                if len(data) >= 2:
                    device_type = "Sink" if data[0] == 0 else "Node"
                    hop_count = data[1] if data[1] != 255 else -1

            rssi_str = f"{device.rssi} dBm" if hasattr(device, 'rssi') else "?"

            print(f"  {i}. {device.address:20} | Type: {device_type:4} | Hop: {str(hop_count):3} | RSSI: {rssi_str}")

        print()
        print(f" Use 'connect <número>' ou 'connect <endereço>' para conectar\n")

    def do_connect(self, arg):
        """
        Conecta ao uplink descoberto.

        Uso: connect [NÚMERO|ENDEREÇO]

        Argumentos:
            NÚMERO     Índice do dispositivo (1, 2, 3...)
            ENDEREÇO   Endereço BLE (ex: E0:D3:62:D6:EE:A0)

        Nota: Primeiro execute 'scan' para descobrir dispositivos.
        """
        if not self.discovered_devices:
            print("\n  Nenhum dispositivo descoberto\n")
            print("   Use 'scan' primeiro para descobrir dispositivos\n")
            return

        # Se não foi fornecido argumento, conectar ao primeiro
        device_to_connect = None

        if not arg:
            device_to_connect = self.discovered_devices[0]
            print(f"\n Nenhum dispositivo especificado, conectando ao primeiro...\n")
        else:
            # Tentar interpretar como número (índice)
            try:
                index = int(arg) - 1  # Converter para 0-based
                if 0 <= index < len(self.discovered_devices):
                    device_to_connect = self.discovered_devices[index]
                else:
                    print(f"\n Índice inválido. Use um número entre 1 e {len(self.discovered_devices)}\n")
                    return
            except ValueError:
                # Não é um número, tentar como endereço
                for device in self.discovered_devices:
                    if device.address.upper() == arg.upper():
                        device_to_connect = device
                        break

                if not device_to_connect:
                    print(f"\n Dispositivo {arg} não encontrado na lista\n")
                    print("   Use 'scan' para atualizar a lista\n")
                    return

        # Armazenar o dispositivo escolhido no node
        self.node.sink_device = device_to_connect

        print(f" A conectar a {device_to_connect.address}...\n")

        # Conectar
        if not self.node.connect_to_sink():
            print(" Falha ao conectar\n")
            return

        print(" Conectado via GATT\n")

        # Atualizar hop count
        self.node._update_hop_count_from_uplink()

        # Autenticar
        print(" A autenticar...\n")
        if not self.node.authenticate_with_sink():
            print(" Falha na autenticação\n")
            return

        print(" Autenticado com sucesso!\n")
        print(f" Hop count: {self.node.hop_count}\n")

    def do_disconnect(self, arg):
        """
        Desconecta do uplink atual.

        Uso: disconnect
        """
        if not self.node.uplink_connection or not self.node.uplink_connection.is_connected:
            print("\n  Não conectado a nenhum uplink\n")
            return

        print("\n A desconectar do uplink...\n")

        self.node.uplink_connection.disconnect()
        self.node.authenticated = False
        with self.node.uplink_session_key_lock:
            self.node.uplink_session_key = None

        print(" Desconectado\n")

    def do_reconnect(self, arg):
        """
        Força reconexão ao uplink.

        Uso: reconnect
        """
        print("\n A reconectar...\n")

        # Desconectar
        if self.node.uplink_connection and self.node.uplink_connection.is_connected:
            self.node.uplink_connection.disconnect()
            time.sleep(1)

        # Reconectar
        if hasattr(self.node, 'sink_device') and self.node.sink_device:
            self.do_connect("")
        else:
            print("  Nenhum dispositivo salvo. Use 'scan' e 'connect' primeiro\n")

    # ========================================================================
    # COMANDOS DE COMUNICAÇÃO
    # ========================================================================

    def do_send(self, arg):
        """
        Envia mensagem ao Sink (via uplink).

        Uso: send <message>

        Exemplo:
            send Hello from Node!
        """
        if not arg:
            print("\n Erro: mensagem não especificada\n")
            print("   Uso: send <message>\n")
            return

        if not self.node.uplink_connection or not self.node.uplink_connection.is_connected:
            print("\n  Não conectado ao uplink\n")
            print("   Use 'connect' primeiro\n")
            return

        if not self.node.authenticated:
            print("\n  Não autenticado\n")
            return

        print(f"\n Enviando mensagem ao Sink...")
        print(f"   Mensagem: {arg}\n")

        # Enviar
        success = self.node.send_message(arg.encode('utf-8'))

        if success:
            print(" Mensagem enviada com sucesso!\n")
        else:
            print(" Falha ao enviar mensagem\n")

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
            print("\n Erro: argumento deve ser um número\n")
            return

        if not self.node.uplink_connection or not self.node.uplink_connection.is_connected:
            print("\n  Não conectado ao uplink\n")
            return

        print(f"\n Enviando {count} pings ao Sink...\n")

        for i in range(count):
            start = time.time()
            success = self.node.send_message(f"PING {i+1}".encode('utf-8'))
            latency = (time.time() - start) * 1000  # ms

            if success:
                print(f"  {i+1}.  {latency:.1f}ms")
            else:
                print(f"  {i+1}.  Falhou")

            if i < count - 1:
                time.sleep(1)

        print()

    # ========================================================================
    # COMANDOS DE UTILIDADE
    # ========================================================================

    def do_clear(self, arg):
        """Limpa a tela."""
        import os
        os.system('clear' if os.name != 'nt' else 'cls')

    def do_exit(self, arg):
        """Sai do CLI (e para o Node)."""
        print("\n  Parando Node Device...")
        self.node.stop()
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
    """Main function - inicia Node com CLI interativo."""
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="Interactive Node - Node Device com CLI")
    parser.add_argument('--cert', required=True, help="Certificado do Node")
    parser.add_argument('--key', required=True, help="Chave privada do Node")
    parser.add_argument('--ca-cert', required=True, help="Certificado CA")
    parser.add_argument('--adapter', type=int, default=0, help="Índice do adaptador BLE")
    parser.add_argument('--peripheral-only', action='store_true',
                        help="Modo peripheral-only: não procura uplink, apenas aceita conexões")

    args = parser.parse_args()

    try:
        node = IoTNode(
            cert_path=args.cert,
            key_path=args.key,
            ca_cert_path=args.ca_cert,
            adapter_index=args.adapter,
            peripheral_only=args.peripheral_only,
        )

        # Setup GATT Server
        node.setup_gatt_server()
        node.start_gatt_server()

        node.running = True

        logger.info(" Node Device iniciado - CLI interativo pronto")

        # Iniciar CLI interativa
        cli = InteractiveNodeCLI(node)

        def signal_handler(signum, frame):
            print(f"\nSinal {signum} recebido")
            node.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Iniciar thread de monitorização de heartbeat timeout em background
        import threading
        import time

        # Flag para rastrear se já mostramos a mensagem de desconexão
        disconnect_message_shown = [False]  # Usar lista para permitir modificação em closure

        def monitor_heartbeat():
            """Thread que monitora timeout de heartbeat."""
            last_connection_state = None

            while node.running:
                time.sleep(1)

                current_connected = node.uplink_connection and node.uplink_connection.is_connected

                # Detectar mudança de estado (conectado -> desconectado)
                if last_connection_state and not current_connected:
                    # Mudou de conectado para desconectado - mostrar mensagem UMA VEZ
                    if not disconnect_message_shown[0]:
                        logger.warning("  Conexão perdida com Sink")
                        print("\n  Conexão perdida com Sink - desconectado do uplink\n")
                        disconnect_message_shown[0] = True
                        # Limpar estado de uplink
                        node.authenticated = False
                        node.uplink_nid = None
                        # Chain Reaction Disconnect: desconectar todos os downlinks
                        node.disconnect_all_downlinks()
                elif current_connected:
                    # Conectado - resetar flag para próxima desconexão
                    disconnect_message_shown[0] = False

                last_connection_state = current_connected

                if node.uplink_connection and node.uplink_connection.is_connected and node.last_heartbeat_time > 0:
                    time_since_heartbeat = time.time() - node.last_heartbeat_time
                    if time_since_heartbeat > 15:
                        logger.error(
                            f" Timeout de heartbeat! Sem heartbeat há {time_since_heartbeat:.1f}s "
                            f"(último seq={node.heartbeat_sequence})"
                        )
                        logger.warning("  Desconectando do uplink devido a timeout de heartbeat...")
                        print(f"\n Timeout de heartbeat! Sem heartbeat há {time_since_heartbeat:.1f}s")
                        print("  Desconectado do uplink automaticamente\n")
                        # Desconectar
                        if node.uplink_connection:
                            node.uplink_connection.disconnect()
                        node.authenticated = False
                        node.uplink_nid = None
                        # Chain Reaction Disconnect: desconectar todos os downlinks
                        node.disconnect_all_downlinks()
                    elif time_since_heartbeat > 10:
                        logger.warning(
                            f"  Sem heartbeat há {time_since_heartbeat:.1f}s "
                            f"(último seq={node.heartbeat_sequence})"
                        )

        heartbeat_monitor_thread = threading.Thread(target=monitor_heartbeat, daemon=True, name="HeartbeatMonitor")
        heartbeat_monitor_thread.start()

        # Run CLI
        cli.cmdloop()

        # Cleanup
        node.stop()

    except Exception as e:
        logger.error(f"Erro: {e}", exc_info=True)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
