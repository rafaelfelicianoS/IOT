#!/usr/bin/env python3
"""
Cliente BLE com Autenticação X.509.

Este cliente:
1. Carrega certificado do dispositivo
2. Escaneia e conecta ao servidor BLE
3. Executa handshake de autenticação via AuthCharacteristic
4. Subscreve notificações de heartbeat após autenticação

Uso:
    python3 examples/test_ble_client_with_auth.py <client_nid> [server_address]

Exemplo:
    python3 examples/test_ble_client_with_auth.py 69f0365f-0b47-4449-8c75-558f4537cf85
    python3 examples/test_ble_client_with_auth.py 69f0365f-0b47-4449-8c75-558f4537cf85 E0:D3:62:D6:EE:A0
"""

import sys
import time
from pathlib import Path
from queue import Queue

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import simplepyble as simpleble
except ImportError:
    print(" SimpleBLE não está instalado!")
    print("   Instale com: pip install simplepyble")
    sys.exit(1)

from common.utils.nid import NID
from common.utils.logger import setup_logger
from common.utils.constants import (
    IOT_NETWORK_SERVICE_UUID,
    CHAR_AUTHENTICATION_UUID,
    CHAR_NETWORK_PACKET_UUID,
)
from common.security.certificate_manager import CertificateManager
from common.security.authentication import AuthenticationProtocol, AuthState
from common.network.packet import Packet
from common.ble.fragmentation import fragment_message, FragmentReassembler

# Setup logger
logger = setup_logger("ble_client_auth")

# Estado da autenticação
authentication_complete = False
authentication_failed = False

# Reassembler para respostas fragmentadas do servidor
server_reassembler = FragmentReassembler()

# Fila para indications recebidas
indication_queue = Queue()


def scan_for_server(timeout: int = 5) -> list:
    """
    Escaneia por servidores BLE disponíveis.

    Args:
        timeout: Tempo de scan em segundos

    Returns:
        Lista de peripherals encontrados
    """
    adapters = simpleble.Adapter.get_adapters()

    if len(adapters) == 0:
        logger.error("Nenhum adaptador Bluetooth encontrado")
        return []

    adapter = adapters[0]
    logger.info(f"Usando adaptador: {adapter.identifier()} [{adapter.address()}]")

    logger.info(f"A escanear por {timeout} segundos...")
    adapter.scan_for(timeout * 1000)  # milliseconds

    peripherals = adapter.scan_get_results()
    logger.info(f"Encontrados {len(peripherals)} dispositivos")

    return peripherals


def find_iot_server(peripherals: list, server_address: str = None):
    """
    Procura servidor IoT na lista de peripherals.

    Args:
        peripherals: Lista de peripherals
        server_address: Endereço específico do servidor (opcional)

    Returns:
        Peripheral do servidor IoT ou None
    """
    for peripheral in peripherals:
        # Se endereço específico foi fornecido
        if server_address and peripheral.address() != server_address:
            continue

        # (SimpleBLE pode não mostrar serviços antes de conectar)
        identifier = peripheral.identifier()

        # Procurar por nome "IoT-Auth-Server" ou similar
        if "IoT" in identifier or "iot" in identifier.lower():
            logger.info(f"Servidor IoT encontrado: {identifier} [{peripheral.address()}]")
            return peripheral

    return None


def notification_handler(data: bytes):
    """
    Handler para notificações de heartbeat.

    Args:
        data: Dados da notificação
    """
    logger.info(f" Notificação recebida: {len(data)} bytes")

    try:
        # Parsear pacote
        packet = Packet.from_bytes(data)
        logger.info(f"   Source: {packet.source}")
        logger.info(f"   Destination: {packet.destination}")
        logger.info(f"   Type: {packet.msg_type}")
        logger.info(f"   Sequence: {packet.sequence}")
        logger.info(f"   Payload: {len(packet.payload)} bytes")

    except Exception as e:
        logger.error(f"Erro ao parsear pacote: {e}")
        logger.debug(f"   Dados (hex): {data.hex()}")


def indication_handler(data: bytes):
    """
    Handler para indications de autenticação.

    Args:
        data: Dados da indication
    """
    logger.info(f" Indication de autenticação recebida: {len(data)} bytes")

    indication_queue.put(data)


def authenticate_with_server(
    peripheral: simpleble.Peripheral,
    auth_protocol: AuthenticationProtocol
) -> bool:
    """
    Executa handshake de autenticação com o servidor.

    Args:
        peripheral: Peripheral conectado
        auth_protocol: Protocolo de autenticação

    Returns:
        True se autenticação bem sucedida, False caso contrário
    """
    global authentication_complete, authentication_failed

    logger.info("\n" + "=" * 60)
    logger.info(" Iniciando Autenticação")
    logger.info("=" * 60)

    # Descobrir características
    services = peripheral.services()
    auth_char = None
    auth_service = None

    for service in services:
        if service.uuid() == IOT_NETWORK_SERVICE_UUID:
            auth_service = service
            for char in service.characteristics():
                if char.uuid() == CHAR_AUTHENTICATION_UUID:
                    auth_char = char
                    break
            break

    if not auth_char:
        logger.error(" AuthCharacteristic não encontrada!")
        return False

    logger.info(f" AuthCharacteristic encontrada")
    logger.info(f"   Service: {auth_service.uuid()}")
    logger.info(f"   Characteristic: {auth_char.uuid()}")

    # Subscrever indications
    logger.info("\n A subscrever indications de autenticação...")

    try:
        peripheral.indicate(
            auth_service.uuid(),
            auth_char.uuid(),
            indication_handler
        )
        logger.info(" Subscrito a indications")
    except Exception as e:
        logger.error(f" Erro ao subscrever indications: {e}")
        return False

    # Iniciar autenticação
    logger.info("\n--- Passo 1: Enviar certificado ao servidor ---")
    initial_message = auth_protocol.start_authentication()
    logger.info(f"Enviando CERT_OFFER: {len(initial_message)} bytes")

    # Fragmentar mensagem para caber no MTU
    fragments = fragment_message(initial_message)
    logger.info(f" Certificado dividido em {len(fragments)} fragmentos")

    try:
        for i, fragment in enumerate(fragments):
            logger.info(f"   Enviando fragmento {i+1}/{len(fragments)}: {len(fragment)} bytes")

            try:
                # Tentar write_command primeiro (sem resposta ACK)
                peripheral.write_command(
                    auth_service.uuid(),
                    auth_char.uuid(),
                    fragment
                )
            except (AttributeError, Exception):
                # Se write_command não existir ou falhar, usar write_request
                peripheral.write_request(
                    auth_service.uuid(),
                    auth_char.uuid(),
                    fragment
                )

            # Pequeno delay entre fragmentos para não sobrecarregar
            if i < len(fragments) - 1:
                time.sleep(0.05)

        logger.info(" Todos os fragmentos enviados")

    except Exception as e:
        logger.error(f" Erro ao enviar fragmentos: {e}")
        return False

    # Aguardar resposta e continuar handshake
    max_rounds = 5
    round_num = 0

    while round_num < max_rounds:
        round_num += 1
        time.sleep(1)  # Aguardar resposta do servidor

        if auth_protocol.state == AuthState.AUTHENTICATED:
            logger.info("\n" + "=" * 60)
            logger.info(" AUTENTICAÇÃO BEM SUCEDIDA!")
            logger.info("=" * 60)

            peer_info = auth_protocol.get_peer_info()
            logger.info(f"\nPeer autenticado:")
            logger.info(f"  NID: {peer_info['nid']}")
            logger.info(f"  Tipo: {'SINK' if peer_info['is_sink'] else 'NODE'}")
            logger.info("")

            authentication_complete = True
            return True

        elif auth_protocol.state == AuthState.FAILED:
            logger.error("\n" + "=" * 60)
            logger.error(" AUTENTICAÇÃO FALHOU!")
            logger.error("=" * 60)
            authentication_failed = True
            return False

        # Ler respostas da fila de indications
        # SimpleBLE processa indications via callback que adiciona à fila

        try:
            # Tentar obter indication da fila (timeout de 1 segundo)
            response_fragment = indication_queue.get(timeout=1.0)

            logger.debug(f"Fragmento recebido da fila: {len(response_fragment)} bytes")

            is_complete, response = server_reassembler.add_fragment(response_fragment)

            if not is_complete:
                # Aguardar mais fragmentos
                logger.debug("Aguardando mais fragmentos da resposta...")
                continue

            # Resposta completa recebida
            logger.info(f"\n--- Passo {round_num + 1}: Processar resposta do servidor ---")
            logger.info(f"Resposta completa recebida: {len(response)} bytes")

            # Processar com protocolo
            continue_auth, client_response = auth_protocol.process_message(response)

            logger.info(f"Estado atual: {auth_protocol.state.name}")

            if client_response:
                logger.info(f"Enviando resposta: {len(client_response)} bytes")

                # Fragmentar e enviar resposta
                response_fragments = fragment_message(client_response)
                logger.info(f" Resposta dividida em {len(response_fragments)} fragmentos")

                for i, fragment in enumerate(response_fragments):
                    logger.debug(f"   Enviando fragmento {i+1}/{len(response_fragments)}: {len(fragment)} bytes")

                    try:
                        peripheral.write_command(
                            auth_service.uuid(),
                            auth_char.uuid(),
                            fragment
                        )
                    except (AttributeError, Exception):
                        peripheral.write_request(
                            auth_service.uuid(),
                            auth_char.uuid(),
                            fragment
                        )

                    if i < len(response_fragments) - 1:
                        time.sleep(0.05)

            if not continue_auth:
                # Autenticação terminou (sucesso ou falha)
                break

        except Exception as e:
            logger.debug(f"Timeout aguardando indication: {e}")
            # Pode ser normal se não houver resposta ainda
            continue

    # Timeout
    if auth_protocol.state != AuthState.AUTHENTICATED:
        logger.error(" Timeout na autenticação")
        return False

    return True


def main(argv):
    """Main function."""
    if len(argv) < 2:
        logger.error("Uso: python3 test_ble_client_with_auth.py <client_nid> [server_address]")
        logger.error("Exemplo: python3 test_ble_client_with_auth.py 69f0365f-0b47-4449-8c75-558f4537cf85")
        return 1

    client_nid_str = argv[1]
    server_address = argv[2] if len(argv) > 2 else None

    try:
        client_nid = NID(client_nid_str)
    except ValueError as e:
        logger.error(f" NID inválido: {e}")
        return 1

    logger.info("=" * 60)
    logger.info("  Cliente BLE com Autenticação X.509")
    logger.info("=" * 60)
    logger.info(f"\n Client NID: {client_nid}")

    if server_address:
        logger.info(f" Servidor alvo: {server_address}")

    # Carregar certificados
    logger.info("\n Carregando certificados...")
    cert_manager = CertificateManager(client_nid)

    if not cert_manager.initialize():
        logger.error(" Erro ao carregar certificados")
        logger.error(f"\nVerifique se existem certificados para este dispositivo:")
        logger.error(f"  certs/{client_nid.to_string()}/certificate.pem")
        logger.error(f"  certs/{client_nid.to_string()}/private_key.pem")
        logger.error(f"  certs/ca_certificate.pem")
        return 1

    logger.info("\n Criando protocolo de autenticação...")
    auth_protocol = AuthenticationProtocol(cert_manager)

    # Escanear por servidores
    logger.info("\n A escanear por servidores BLE...")
    peripherals = scan_for_server(timeout=5)

    if len(peripherals) == 0:
        logger.error(" Nenhum dispositivo encontrado")
        return 1

    # Encontrar servidor IoT
    server = find_iot_server(peripherals, server_address)

    if not server:
        logger.error(" Servidor IoT não encontrado")
        logger.info("\nDispositivos disponíveis:")
        for p in peripherals:
            logger.info(f"  - {p.identifier()} [{p.address()}]")
        return 1

    # Conectar ao servidor
    logger.info(f"\n A conectar ao servidor: {server.identifier()} [{server.address()}]")

    try:
        server.connect()
        logger.info(" Conectado!")
    except Exception as e:
        logger.error(f" Erro ao conectar: {e}")
        return 1

    # Tentar negociar MTU maior (para suportar certificados grandes)
    logger.info("\n Negociando MTU...")
    try:
        # Tentar definir MTU para 512 bytes (máximo comum)
        # SimpleBLE pode não ter método set_mtu direto, mas a conexão já negocia
        # Vamos verificar o MTU atual
        logger.info("   MTU será negociado automaticamente pelo BLE")
        logger.info("   Certificados grandes podem precisar de write_command ou fragmentação")
    except Exception as e:
        logger.warning(f"  Aviso ao negociar MTU: {e}")

    # Autenticar
    if not authenticate_with_server(server, auth_protocol):
        logger.error(" Autenticação falhou")
        server.disconnect()
        return 1

    # Subscrever heartbeats
    logger.info("\n A subscrever notificações de heartbeat...")

    services = server.services()
    packet_char = None
    packet_service = None

    for service in services:
        if service.uuid() == IOT_NETWORK_SERVICE_UUID:
            packet_service = service
            for char in service.characteristics():
                if char.uuid() == CHAR_NETWORK_PACKET_UUID:
                    packet_char = char
                    break
            break

    if packet_char:
        try:
            server.notify(
                packet_service.uuid(),
                packet_char.uuid(),
                notification_handler
            )
            logger.info(" Subscrito a heartbeats")
        except Exception as e:
            logger.error(f" Erro ao subscrever heartbeats: {e}")

    # Manter conexão e receber heartbeats
    logger.info("\n" + "=" * 60)
    logger.info(" CLIENTE AUTENTICADO E A RECEBER HEARTBEATS")
    logger.info("=" * 60)
    logger.info("\nA aguardar heartbeats... (Ctrl+C para sair)\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n\nA terminar...")

    # Desconectar
    logger.info("Desconectando...")
    server.disconnect()
    logger.info(" Desconectado")

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
