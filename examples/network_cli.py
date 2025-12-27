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

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.ble.gatt_client import BLEClient, SIMPLEBLE_AVAILABLE
from common.network.neighbor_discovery import NeighborDiscovery, NeighborInfo
from common.network.link_manager import LinkManager
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

        # Verificar se SimpleBLE está disponível
        if not SIMPLEBLE_AVAILABLE:
            print("❌ ERRO: SimpleBLE não está instalado!")
            sys.exit(1)

        # Criar cliente BLE
        try:
            self.client = BLEClient(adapter_index=0)
            logger.info("BLE Client criado")
        except Exception as e:
            print(f"❌ ERRO ao criar BLE Client: {e}")
            sys.exit(1)

        # Criar NeighborDiscovery
        self.discovery = NeighborDiscovery(
            client=self.client,
            scan_interval=30,
            scan_duration=5000,
            neighbor_timeout=120,
        )
        logger.info("NeighborDiscovery criado")

        # Criar LinkManager
        self.link_manager = LinkManager(client=self.client)
        logger.info("LinkManager criado")

        print("✅ Sistema inicializado com sucesso!\n")

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
        print("\n🔍 A fazer scan de vizinhos...\n")

        try:
            neighbors = self.discovery.scan_once()

            if not neighbors:
                print("⚠️  Nenhum vizinho encontrado.")
                print("   Certifica-te que há dispositivos IoT a fazer advertising.\n")
                return

            print(f"✅ Encontrados {len(neighbors)} vizinho(s):\n")
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
                print(f"\n🏆 Melhor rota: {best.address} (hop={best.hop_count}, rssi={best.rssi}dBm)")

            print()

        except Exception as e:
            print(f"❌ Erro durante scan: {e}\n")
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
            print("\n⚠️  Nenhum vizinho conhecido.")
            print("   Use 'scan' para descobrir vizinhos.\n")
            return

        print(f"\n📋 Vizinhos conhecidos ({len(neighbors)}):\n")
        print("┌─────────────────────┬──────────────┬─────┬────────┬─────────┬──────────┐")
        print("│ Address             │ NID          │ Hop │ Type   │ RSSI    │ Visto    │")
        print("├─────────────────────┼──────────────┼─────┼────────┼─────────┼──────────┤")

        for neighbor in sorted(neighbors, key=lambda n: n.hop_count):
            nid_short = str(neighbor.nid)[:8] + "..."
            age = neighbor.age()
            age_str = f"{age:.0f}s" if age < 60 else f"{age/60:.1f}m"
            conn_mark = "🔗" if neighbor.is_connected else "  "
            print(f"│{conn_mark}{neighbor.address:19} │ {nid_short:12} │ {neighbor.hop_count:3} │ {neighbor.device_type:6} │ {neighbor.rssi:4}dBm │ {age_str:8} │")

        print("└─────────────────────┴──────────────┴─────┴────────┴─────────┴──────────┘")

        # Estatísticas
        stats = self.discovery.get_stats()
        print(f"\n📊 Estatísticas:")
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
            print("\n❌ Erro: endereço não especificado.")
            print("   Uso: connect <address>\n")
            return

        address = arg.strip().upper()

        # Verificar se vizinho existe
        neighbor = self.discovery.get_neighbor(address)
        if not neighbor:
            print(f"\n⚠️  Vizinho {address} não encontrado.")
            print("   Use 'scan' ou 'neighbors' para ver vizinhos disponíveis.\n")
            return

        print(f"\n🔗 A conectar a {address}...")
        print(f"   NID: {neighbor.nid}")
        print(f"   Hop count: {neighbor.hop_count}")
        print(f"   RSSI: {neighbor.rssi}dBm\n")

        try:
            # Conectar via LinkManager
            link = self.link_manager.connect_to_neighbor(address, neighbor)

            if not link:
                print(f"❌ Falha ao conectar a {address}.\n")
                return

            # Marcar como conectado no discovery
            self.discovery.mark_connected(address, True)

            print(f"✅ Conectado com sucesso a {address}!\n")

        except Exception as e:
            print(f"❌ Erro ao conectar: {e}\n")
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
            print("\n❌ Erro: endereço não especificado.")
            print("   Uso: disconnect <address>\n")
            return

        address = arg.strip().upper()

        print(f"\n🔌 A desconectar de {address}...\n")

        try:
            # Desconectar via LinkManager
            self.link_manager.disconnect_neighbor(address)

            # Marcar como desconectado no discovery
            self.discovery.mark_connected(address, False)

            print(f"✅ Desconectado de {address}!\n")

        except Exception as e:
            print(f"❌ Erro ao desconectar: {e}\n")
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
        print("\n📊 STATUS DA REDE\n")

        # Uplink
        uplink = self.link_manager.get_uplink()
        if uplink:
            print("🔼 UPLINK:")
            print(f"   Address: {uplink.address}")
            print(f"   NID: {uplink.device_info.nid}")
            print(f"   Hop count: {uplink.device_info.hop_count}")
            print(f"   Type: {uplink.device_info.device_type}")
            print(f"   Estado: {'🟢 Conectado' if uplink.is_connected else '🔴 Desconectado'}")
        else:
            print("🔼 UPLINK: Nenhum")

        print()

        # Downlinks
        downlinks = self.link_manager.get_downlinks()
        if downlinks:
            print(f"🔽 DOWNLINKS ({len(downlinks)}):")
            for link in downlinks:
                status = "🟢 Conectado" if link.is_connected else "🔴 Desconectado"
                print(f"   • {link.address} - hop={link.device_info.hop_count} - {status}")
        else:
            print("🔽 DOWNLINKS: Nenhum")

        print()

        # Estatísticas do discovery
        stats = self.discovery.get_stats()
        print("📈 ESTATÍSTICAS:")
        print(f"   Vizinhos conhecidos: {stats['total_neighbors']}")
        print(f"   Vizinhos conectados: {stats['connected_neighbors']}")
        print(f"   Melhor hop count: {stats['best_hop_count']}")

        if stats['last_scan_age'] is not None:
            age = stats['last_scan_age']
            age_str = f"{age:.0f}s" if age < 60 else f"{age/60:.1f}m"
            print(f"   Último scan: {age_str} atrás")

        print()

    def do_clear(self, arg):
        """
        Limpa a tela.

        Uso: clear
        """
        import os
        os.system('clear' if os.name != 'nt' else 'cls')

    def do_exit(self, arg):
        """
        Sai da CLI.

        Uso: exit
        """
        print("\n👋 A terminar...\n")
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
        print(f"\n❌ Comando desconhecido: {line}")
        print("   Digite 'help' para ver comandos disponíveis.\n")


def main():
    """Main function."""
    try:
        cli = NetworkCLI()
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\n\n👋 A terminar...\n")
        return 0
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        print(f"\n❌ Erro fatal: {e}\n")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
