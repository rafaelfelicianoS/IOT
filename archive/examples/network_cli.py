#!/usr/bin/env python3
"""
Network CLI - Interface de linha de comando para controle manual da rede.

Permite controlar manualmente a rede IoT BLE:
- Fazer scan de vizinhos
- Conectar/desconectar de vizinhos manualmente
- Ver status da rede (uplink, downlinks)
- Listar vizinhos conhecidos

Uso:
    python3 examples/network_cli.py
"""

import sys
import cmd
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient, SIMPLEBLE_AVAILABLE
from common.network.neighbor_discovery import NeighborDiscovery, NeighborInfo
from common.network.link_manager import LinkManager
from common.network.packet import Packet
from common.utils.constants import (
    MessageType,
    IOT_NETWORK_SERVICE_UUID,
    CHAR_NETWORK_PACKET_UUID,
)
from common.utils.nid import NID
from common.utils.logger import setup_logger

# Setup logger
logger = setup_logger("network_cli")


class NetworkCLI(cmd.Cmd):
    """CLI interativa para controle manual da rede IoT."""

    intro = """
╔═══════════════════════════════════════════════════════════════╗
║                  IoT Network - CLI Interface                  ║
╚═══════════════════════════════════════════════════════════════╝

Digite 'help' para ver comandos disponíveis.
Digite 'exit' ou Ctrl+D para sair.
"""
    prompt = "iot-network> "

    def __init__(self):
        """Inicializa a CLI."""
        super().__init__()

        # Flag para evitar cleanup duplicado
        self._cleanup_done = False

        if not SIMPLEBLE_AVAILABLE:
            print(" ERRO: SimpleBLE não está instalado!")
            sys.exit(1)

        try:
            self.client = BLEClient(adapter_index=0)
            logger.info("BLE Client criado")
        except Exception as e:
            print(f" ERRO ao criar BLE Client: {e}")
            sys.exit(1)

        self.discovery = NeighborDiscovery(
            client=self.client,
            scan_interval=30,
            scan_duration=5000,
            neighbor_timeout=120,
        )
        logger.info("NeighborDiscovery criado")

        self.link_manager = LinkManager(client=self.client)
        logger.info("LinkManager criado")

        print(" Sistema inicializado com sucesso!\n")

    def do_scan(self, arg):
        """
        Faz scan de vizinhos BLE.

        Uso: scan

        Descobre vizinhos disponíveis e mostra informações:
        - Endereço BLE
        - NID (Network ID)
        - Hop count (distância ao Sink)
        - Tipo de dispositivo
        - RSSI (força do sinal)
        """
        print("\n A fazer scan de vizinhos...\n")

        try:
            neighbors = self.discovery.scan_once()

            if not neighbors:
                print("  Nenhum vizinho encontrado.")
                print("   Certifica-te que há dispositivos IoT a fazer advertising.\n")
                return

            print(f" Encontrados {len(neighbors)} vizinho(s):\n")
            print("┌─────────────────────┬──────────────┬─────┬────────┬─────────┐")
            print("│ Address             │ NID          │ Hop │ Type   │ RSSI    │")
            print("├─────────────────────┼──────────────┼─────┼────────┼─────────┤")

            for neighbor in neighbors:
                nid_short = str(neighbor.nid)[:8] + "..."
                print(f"│ {neighbor.address:19} │ {nid_short:12} │ {neighbor.hop_count:3} │ {neighbor.device_type:6} │ {neighbor.rssi:4}dBm │")

            print("└─────────────────────┴──────────────┴─────┴────────┴─────────┘")

            # Mostrar melhor vizinho
            best = self.discovery.get_best_neighbor()
            if best:
                print(f"\n Melhor rota: {best.address} (hop={best.hop_count}, rssi={best.rssi}dBm)")

            print()

        except Exception as e:
            print(f" Erro durante scan: {e}\n")
            logger.error(f"Erro durante scan: {e}")

    def do_neighbors(self, arg):
        """
        Lista vizinhos conhecidos (cache).

        Uso: neighbors

        Mostra todos os vizinhos descobertos anteriormente,
        incluindo há quanto tempo foram vistos pela última vez.
        """
        neighbors = self.discovery.get_neighbors()

        if not neighbors:
            print("\n  Nenhum vizinho conhecido.")
            print("   Use 'scan' para descobrir vizinhos.\n")
            return

        print(f"\n Vizinhos conhecidos ({len(neighbors)}):\n")
        print("┌─────────────────────┬──────────────┬─────┬────────┬─────────┬──────────┐")
        print("│ Address             │ NID          │ Hop │ Type   │ RSSI    │ Visto    │")
        print("├─────────────────────┼──────────────┼─────┼────────┼─────────┼──────────┤")

        for neighbor in sorted(neighbors, key=lambda n: n.hop_count):
            nid_short = str(neighbor.nid)[:8] + "..."
            age = neighbor.age()
            age_str = f"{age:.0f}s" if age < 60 else f"{age/60:.1f}m"
            conn_mark = "" if neighbor.is_connected else "  "
            print(f"│{conn_mark}{neighbor.address:19} │ {nid_short:12} │ {neighbor.hop_count:3} │ {neighbor.device_type:6} │ {neighbor.rssi:4}dBm │ {age_str:8} │")

        print("└─────────────────────┴──────────────┴─────┴────────┴─────────┴──────────┘")

        # Estatísticas
        stats = self.discovery.get_stats()
        print(f"\n Estatísticas:")
        print(f"   Total: {stats['total_neighbors']} vizinhos")
        print(f"   Conectados: {stats['connected_neighbors']}")
        print(f"   Melhor hop count: {stats['best_hop_count']}")
        print()

    def do_connect(self, arg):
        """
        Conecta a um vizinho específico.

        Uso: connect <address>

        Argumentos:
            address   Endereço BLE do vizinho (ex: E0:D3:62:D6:EE:A0)

        Exemplo:
            connect E0:D3:62:D6:EE:A0
        """
        if not arg:
            print("\n Erro: endereço não especificado.")
            print("   Uso: connect <address>\n")
            return

        address = arg.strip().upper()

        neighbor = self.discovery.get_neighbor(address)
        if not neighbor:
            print(f"\n  Vizinho {address} não encontrado.")
            print("   Use 'scan' ou 'neighbors' para ver vizinhos disponíveis.\n")
            return

        print(f"\n A conectar a {address}...")
        print(f"   NID: {neighbor.nid}")
        print(f"   Hop count: {neighbor.hop_count}")
        print(f"   RSSI: {neighbor.rssi}dBm\n")

        try:
            # Conectar via LinkManager
            link = self.link_manager.connect_to_neighbor(address, neighbor)

            if not link:
                print(f" Falha ao conectar a {address}.\n")
                return

            # Marcar como conectado no discovery
            self.discovery.mark_connected(address, True)

            print(f" Conectado com sucesso a {address}!\n")

        except Exception as e:
            print(f" Erro ao conectar: {e}\n")
            logger.error(f"Erro ao conectar a {address}: {e}")

    def do_disconnect(self, arg):
        """
        Desconecta de um vizinho específico.

        Uso: disconnect <address>

        Argumentos:
            address   Endereço BLE do vizinho (ex: E0:D3:62:D6:EE:A0)

        Exemplo:
            disconnect E0:D3:62:D6:EE:A0
        """
        if not arg:
            print("\n Erro: endereço não especificado.")
            print("   Uso: disconnect <address>\n")
            return

        address = arg.strip().upper()

        print(f"\n A desconectar de {address}...\n")

        try:
            # Desconectar via LinkManager
            self.link_manager.disconnect_neighbor(address)

            # Marcar como desconectado no discovery
            self.discovery.mark_connected(address, False)

            print(f" Desconectado de {address}!\n")

        except Exception as e:
            print(f" Erro ao desconectar: {e}\n")
            logger.error(f"Erro ao desconectar de {address}: {e}")

    def do_status(self, arg):
        """
        Mostra status atual da rede.

        Uso: status

        Mostra informações sobre:
        - Uplink atual (conexão para o Sink)
        - Downlinks ativos (conexões de vizinhos para nós)
        - Estatísticas gerais
        """
        print("\n STATUS DA REDE\n")

        # Uplink
        uplink = self.link_manager.get_uplink()
        if uplink:
            print(" UPLINK:")
            print(f"   Address: {uplink.address}")
            print(f"   NID: {uplink.device_info.nid}")
            print(f"   Hop count: {uplink.device_info.hop_count}")
            print(f"   Type: {uplink.device_info.device_type}")
            print(f"   Estado: {' Conectado' if uplink.connection.is_connected else ' Desconectado'}")
        else:
            print(" UPLINK: Nenhum")

        print()

        # Downlinks
        downlinks = self.link_manager.get_downlinks()
        if downlinks:
            print(f" DOWNLINKS ({len(downlinks)}):")
            for link in downlinks:
                status = " Conectado" if link.connection.is_connected else " Desconectado"
                print(f"   • {link.address} - hop={link.device_info.hop_count} - {status}")
        else:
            print(" DOWNLINKS: Nenhum")

        print()

        # Estatísticas do discovery
        stats = self.discovery.get_stats()
        print(" ESTATÍSTICAS:")
        print(f"   Vizinhos conhecidos: {stats['total_neighbors']}")
        print(f"   Vizinhos conectados: {stats['connected_neighbors']}")
        print(f"   Melhor hop count: {stats['best_hop_count']}")

        if stats['last_scan_age'] is not None:
            age = stats['last_scan_age']
            age_str = f"{age:.0f}s" if age < 60 else f"{age/60:.1f}m"
            print(f"   Último scan: {age_str} atrás")

        print()

    def do_send(self, arg):
        """
        Envia um pacote de dados para um vizinho.

        Uso: send <address> <message>

        Argumentos:
            address   Endereço BLE do destino (ex: E0:D3:62:D6:EE:A0)
            message   Mensagem a enviar (texto)

        Exemplo:
            send E0:D3:62:D6:EE:A0 Hello World!
        """
        if not arg:
            print("\n Erro: argumentos insuficientes.")
            print("   Uso: send <address> <message>\n")
            return

        parts = arg.split(maxsplit=1)
        if len(parts) < 2:
            print("\n Erro: mensagem não especificada.")
            print("   Uso: send <address> <message>\n")
            return

        address = parts[0].strip().upper()
        message = parts[1].strip()

        neighbor = self.discovery.get_neighbor(address)
        if not neighbor:
            print(f"\n  Vizinho {address} não encontrado.")
            print("   Use 'scan' para descobrir vizinhos.\n")
            return

        if not neighbor.is_connected:
            print(f"\n  Não estás conectado a {address}.")
            print(f"   Use 'connect {address}' primeiro.\n")
            return

        # Obter link (pode ser uplink ou downlink)
        link = None
        uplink = self.link_manager.get_uplink()
        if uplink and uplink.address == address:
            link = uplink
        else:
            link = self.link_manager.get_downlink(address)

        if not link:
            print(f"\n Erro: link para {address} não encontrado.\n")
            return

        print(f"\n A enviar mensagem para {address}...")
        print(f"   Mensagem: {message}")
        print(f"   Tamanho: {len(message)} caracteres\n")

        try:
            # Obter nosso NID (do LinkManager)
            source_nid = self.link_manager.my_nid

            packet = Packet.create(
                source=source_nid,
                destination=neighbor.nid,
                msg_type=MessageType.DATA,
                payload=message.encode('utf-8'),
                sequence=1,  # TODO: incrementar sequence number
                ttl=5
            )

            # Rotear o pacote usando o LinkManager (isso vai aprender rotas)
            success = self.link_manager.route_packet(packet, from_link=None)

            if success:
                print(f" Pacote roteado com sucesso!")
                print(f"   Origem NID: {source_nid}")
                print(f"   Destino NID: {neighbor.nid}")
                print(f"   Mensagem: {message}\n")
            else:
                print(f" Falha ao rotear pacote.\n")

        except Exception as e:
            print(f" Erro ao enviar: {e}\n")
            logger.error(f"Erro ao enviar pacote para {address}: {e}")

    def do_clear(self, arg):
        """
        Limpa a tela.

        Uso: clear
        """
        import os
        os.system('clear' if os.name != 'nt' else 'cls')

    def do_stop_heartbeat(self, arg):
        """
        Para o envio de heartbeats do servidor (para testes de timeout).

        Uso: stop_heartbeat

        Este comando cria um arquivo de controlo que o GATT Server verifica
        periodicamente para desabilitar o envio de heartbeats.
        Útil para testar detecção de link failure.
        """
        from pathlib import Path

        control_file = Path(__file__).parent.parent / "logs" / "heartbeat_control"

        try:
            control_file.parent.mkdir(parents=True, exist_ok=True)
            with open(control_file, 'w') as f:
                f.write("stop")

            print("\n Comando enviado para PARAR heartbeats do servidor")
            print("   O servidor vai detetar o comando em ~1 segundo")
            print("   Use 'resume_heartbeat' para retomar.\n")
            logger.info("Comando stop_heartbeat enviado")

        except Exception as e:
            print(f"\n Erro ao enviar comando: {e}\n")
            logger.error(f"Erro em stop_heartbeat: {e}")

    def do_resume_heartbeat(self, arg):
        """
        Retoma o envio de heartbeats do servidor.

        Uso: resume_heartbeat

        Cancela o comando 'stop_heartbeat' e permite que o servidor
        volte a enviar heartbeats normalmente.
        """
        from pathlib import Path

        control_file = Path(__file__).parent.parent / "logs" / "heartbeat_control"

        try:
            with open(control_file, 'w') as f:
                f.write("start")

            print("\n▶  Comando enviado para RETOMAR heartbeats do servidor")
            print("   O servidor vai detetar o comando em ~1 segundo\n")
            logger.info("Comando resume_heartbeat enviado")

        except Exception as e:
            print(f"\n Erro ao enviar comando: {e}\n")
            logger.error(f"Erro em resume_heartbeat: {e}")

    def do_heartbeat_status(self, arg):
        """
        Verifica o estado dos heartbeats do servidor.

        Uso: heartbeat_status

        Lê o log do servidor para mostrar se os heartbeats estão ativos
        e quando foi o último heartbeat enviado.
        """
        from pathlib import Path
        import time

        server_log = Path(__file__).parent.parent / "logs" / "test_gatt_server.log"

        try:
            if not server_log.exists():
                print("\n  Log do servidor não encontrado.")
                print("   O servidor está a correr?\n")
                return

            # Ler últimas 200 linhas do log
            with open(server_log, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-200:] if len(lines) > 200 else lines

            # Procurar última linha de heartbeat e estado
            last_heartbeat = None
            last_heartbeat_time = None
            heartbeat_disabled = False
            heartbeat_enabled = False

            for line in reversed(last_lines):
                # Procurar heartbeat enviado
                if " Heartbeat enviado" in line and last_heartbeat is None:
                    # Extrair timestamp da linha de log
                    parts = line.split("|")
                    if len(parts) >= 2:
                        timestamp_str = parts[0].strip()
                        last_heartbeat = timestamp_str
                        last_heartbeat_time = timestamp_str

                # Procurar estado de controlo
                if " Heartbeats DESABILITADOS" in line:
                    heartbeat_disabled = True
                elif "▶  Heartbeats HABILITADOS" in line:
                    heartbeat_enabled = True

            print("\n Estado dos Heartbeats do Servidor:\n")
            print(f"   Log: {server_log.name}")
            print(f"   Linhas analisadas: {len(last_lines)}\n")

            # Determinar estado atual
            if heartbeat_disabled and not heartbeat_enabled:
                print("   Status:  PARADOS")
                if last_heartbeat:
                    print(f"   Último heartbeat: {last_heartbeat}")
                else:
                    print("   Último heartbeat: N/A")
                print("\n   Use 'resume_heartbeat' para retomar.\n")
            elif last_heartbeat:
                print("   Status:  ATIVOS")
                print(f"   Último heartbeat: {last_heartbeat}")
                print("\n   Use 'stop_heartbeat' para parar.\n")
            else:
                print("   Status:   Desconhecido")
                print("   Nenhum heartbeat encontrado no log.")
                print("   O servidor está a correr?\n")

        except Exception as e:
            print(f"\n Erro ao verificar status: {e}\n")
            logger.error(f"Erro em heartbeat_status: {e}")

    def do_heartbeat_info(self, arg):
        """
        Mostra informações sobre monitoramento de heartbeat (lado cliente).

        Uso: heartbeat_info

        Mostra:
        - Se está a monitorar heartbeats do uplink
        - Número de heartbeats perdidos
        - Tempo desde último heartbeat
        """
        try:
            status = self.link_manager.get_heartbeat_status()

            print("\n Monitoramento de Heartbeat (Cliente):\n")

            if not status['monitoring']:
                print("   Status:   NÃO MONITORANDO")
                print("   Motivo: Sem uplink ativo\n")
                return

            print("   Status:  MONITORANDO")
            print(f"   Heartbeats perdidos: {status['missed_count']}/3")

            if status['time_since_last'] is not None:
                print(f"   Tempo desde último: {status['time_since_last']:.1f}s")
            else:
                print("   Tempo desde último: N/A (nenhum recebido ainda)")

            # Status visual baseado em heartbeats perdidos
            if status['missed_count'] == 0:
                print("\n    Uplink saudável\n")
            elif status['missed_count'] == 1:
                print("\n    Atenção: 1 heartbeat perdido\n")
            elif status['missed_count'] == 2:
                print("\n    Aviso: 2 heartbeats perdidos!\n")
            else:
                print("\n     CRÍTICO: 3+ heartbeats perdidos - timeout iminente!\n")

        except Exception as e:
            print(f"\n Erro ao obter info de heartbeat: {e}\n")
            logger.error(f"Erro em heartbeat_info: {e}")

    def do_routes(self, arg):
        """
        Mostra a tabela de rotas (forwarding table).

        Uso: routes

        Mostra todos os NIDs conhecidos e por qual link devemos
        enviar pacotes para alcançá-los.
        """
        try:
            routes = self.link_manager.get_forwarding_table()

            if not routes:
                print("\n Tabela de Rotas: VAZIA\n")
                print("   Nenhuma rota aprendida ainda.")
                print("   Rotas são aprendidas automaticamente quando pacotes são recebidos.\n")
                return

            print(f"\n Tabela de Rotas ({len(routes)} entradas):\n")
            print(f"   {'NID':<40} → Link")
            print(f"   {'-'*40}   {'-'*17}")

            for nid, link_address in routes.items():
                print(f"   {str(nid):<40} → {link_address}")

            print()

        except Exception as e:
            print(f"\n Erro ao obter tabela de rotas: {e}\n")
            logger.error(f"Erro em routes: {e}")

    def cleanup(self):
        """Limpa recursos antes de sair."""
        if self._cleanup_done:
            return

        try:
            # Desconectar de todos os dispositivos
            logger.info("A limpar recursos...")

            # Desconectar uplink
            uplink = self.link_manager.get_uplink()
            if uplink:
                logger.info(f"A desconectar uplink {uplink.address}...")
                self.link_manager.disconnect_neighbor(uplink.address)

            # Desconectar downlinks
            downlinks = self.link_manager.get_downlinks()
            for link in downlinks:
                logger.info(f"A desconectar downlink {link.address}...")
                self.link_manager.disconnect_neighbor(link.address)

            # Cleanup do client BLE
            self.client.disconnect_all()

            logger.info(" Recursos limpos")
            self._cleanup_done = True
        except Exception as e:
            logger.error(f"Erro durante cleanup: {e}")

    def do_exit(self, arg):
        """
        Sai da CLI.

        Uso: exit
        """
        print("\n A terminar...")
        self.cleanup()
        print()
        return True

    def do_EOF(self, arg):
        """Handle Ctrl+D."""
        print()  # Nova linha após Ctrl+D
        return self.do_exit(arg)

    def emptyline(self):
        """Não faz nada quando linha vazia."""
        pass

    def default(self, line):
        """Comando desconhecido."""
        print(f"\n Comando desconhecido: {line}")
        print("   Digite 'help' para ver comandos disponíveis.\n")


def main():
    """Main function."""
    cli = None
    try:
        cli = NetworkCLI()
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\n A terminar...")
        if cli:
            cli.cleanup()
        print()
        return 0
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        print(f"\n Erro fatal: {e}\n")
        return 1
    finally:
        # Garantir cleanup mesmo em caso de exceção
        if cli:
            try:
                cli.cleanup()
            except:
                pass

    return 0


if __name__ == '__main__':
    sys.exit(main())
